# Copyright (c) 2026, PostgreSQL Global Development Group

# Check the handoff from WAL senders to the synchronous replication waker,
# including cancellation, config reload, worker restart, and direct fallback.
use strict;
use warnings FATAL => 'all';
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

plan skip_all => 'test requires Unix signals' if $windows_os;

my $primary = PostgreSQL::Test::Cluster->new('primary');
$primary->init(allows_streaming => 1);
$primary->append_conf('postgresql.conf',
	"sync_rep_waker = on\nsync_rep_waker_direct_limit = 0\nrestart_after_crash = on");
$primary->start;
$primary->safe_psql('postgres', 'CREATE TABLE waker_test (a text)');
$primary->backup('backup');

my $standby = PostgreSQL::Test::Cluster->new('standby');
$standby->init_from_backup($primary, 'backup', has_streaming => 1);
$standby->append_conf('postgresql.conf', 'wal_receiver_status_interval = 1');
$standby->start;
$primary->wait_for_replay_catchup($standby);

is($standby->safe_psql('postgres',
	"SELECT count(*) FROM pg_stat_activity WHERE backend_type = 'sync rep waker'"),
	'0', 'no waker during recovery');

$primary->safe_psql('postgres',
	"ALTER SYSTEM SET synchronous_standby_names = 'standby'");
$primary->reload;

sub waker_pid
{
	return $primary->safe_psql('postgres',
		"SELECT pid FROM pg_stat_activity WHERE backend_type = 'sync rep waker'");
}

ok($primary->poll_query_until('postgres',
	"SELECT count(*) = 1 FROM pg_stat_activity WHERE backend_type = 'sync rep waker'"),
	'waker is running');

my $stopped_waker;
END
{
	# Do not leave a stopped child behind if an assertion or query fails.
	kill 'CONT', $stopped_waker if defined $stopped_waker;
}

sub start_waiter
{
	my ($mode, $value) = @_;
	my $session = $primary->background_psql('postgres');
	$session->set_query_timer_restart;
	$session->query_safe("SET synchronous_commit = '$mode'");
	$session->query_safe('SET synchronous_commit_cancelation = on');
	my $pid = $session->query_safe('SELECT pg_backend_pid()');
	$session->query_until(qr/committing/,
		"BEGIN; INSERT INTO waker_test VALUES ('$value');\n"
		  . "\\echo committing\nCOMMIT;\n");
	ok($primary->poll_query_until('postgres',
		"SELECT wait_event = 'SyncRep' FROM pg_stat_activity WHERE pid = $pid"),
		"$value is queued for synchronous replication");
	return ($session, $pid);
}

# Suspend only the waker.  The standby must still acknowledge the commit,
# and the sender must leave the queued backend for the waker to release.
for my $mode ('remote_write', 'on', 'remote_apply')
{
	$stopped_waker = waker_pid();
	ok(kill('STOP', $stopped_waker), "stop waker for $mode");
	my ($session, $pid) = start_waiter($mode, $mode);
	my $lsn = $primary->safe_psql('postgres', 'SELECT pg_current_wal_insert_lsn()');
	my $position = $mode eq 'remote_write' ? 'write_lsn'
	  : $mode eq 'on' ? 'flush_lsn' : 'replay_lsn';
	ok($primary->poll_query_until('postgres',
		"SELECT $position >= '$lsn'::pg_lsn FROM pg_stat_replication WHERE application_name = 'standby'"),
		"standby acknowledged $mode position while waker is stopped");
	is($primary->safe_psql('postgres',
		"SELECT wait_event FROM pg_stat_activity WHERE pid = $pid"),
		'SyncRep', "$mode waiter remains queued until waker runs");
	ok(kill('CONT', $stopped_waker), "resume waker for $mode");
	undef $stopped_waker;
	is($session->query_safe('SELECT 1'), '1', "$mode waiter released");
	$session->quit;
}

# Cancellation removes the backend from its queue while the waker is idle.
$stopped_waker = waker_pid();
kill 'STOP', $stopped_waker;
my ($cancel_session, $cancel_pid) = start_waiter('on', 'cancel');
$primary->safe_psql('postgres', "SELECT pg_cancel_backend($cancel_pid)");
is($cancel_session->query('SELECT 1'), '1',
	'canceled waiter can continue while waker is stopped');
like($cancel_session->{stderr},
	qr/canceling wait for synchronous replication due to user request/,
	'cancellation reports locally committed transaction');
$cancel_session->quit;
kill 'CONT', $stopped_waker;
undef $stopped_waker;
$primary->safe_psql('postgres', "INSERT INTO waker_test VALUES ('after_cancel')");
pass('waker continues after waiter cancellation');

# Clearing the synchronous standby list must release waiters even when the
# waker cannot run.  This remains the checkpointer's responsibility.
$standby->stop;
$stopped_waker = waker_pid();
kill 'STOP', $stopped_waker;
my ($reload_session, $reload_pid) = start_waiter('on', 'reload');
$primary->safe_psql('postgres',
	"ALTER SYSTEM SET synchronous_standby_names = ''");
$primary->reload;
is($reload_session->query_safe('SELECT 1'), '1',
	'clearing standby names releases waiter without the waker');
$reload_session->quit;
kill 'CONT', $stopped_waker;
undef $stopped_waker;

# Clean worker exit is followed by a restart without restarting the primary.
my $old_pid = waker_pid();
kill 'TERM', $old_pid;
ok($primary->poll_query_until('postgres',
	"SELECT count(*) = 1 FROM pg_stat_activity WHERE backend_type = 'sync rep waker' AND pid <> $old_pid"),
	'cleanly terminated waker is restarted');

$standby->start;
$primary->safe_psql('postgres',
	"ALTER SYSTEM SET synchronous_standby_names = 'standby'");
$primary->reload;
$primary->safe_psql('postgres', "INSERT INTO waker_test VALUES ('after_restart')");
pass('synchronous commit works after waker restart');

# An unclean exit must go through crash recovery, recreating shared queues
# and the waker's registration before synchronous commits can resume.
$old_pid = waker_pid();
my $log_offset = -s $primary->logfile;
kill 'QUIT', $old_pid;
$primary->wait_for_log(qr/terminating any other active server processes/,
	$log_offset);
ok($primary->poll_query_until('postgres',
	"SELECT count(*) = 1 FROM pg_stat_activity WHERE backend_type = 'sync rep waker' AND pid <> $old_pid"),
	'waker is recreated after crash recovery');
$primary->safe_psql('postgres', "INSERT INTO waker_test VALUES ('after_crash')");
pass('synchronous commit works after waker crash');

# Disabling the process preserves the direct WAL sender wakeup path for all
# three queues, including with the branch-specific EVERY quorum syntax.
$primary->append_conf('postgresql.conf', 'sync_rep_waker = off');
$primary->restart;
is(waker_pid(), '', 'no waker when disabled');
$primary->safe_psql('postgres',
	"ALTER SYSTEM SET synchronous_standby_names = 'EVERY(standby), ANY 1(standby)'");
$primary->reload;
for my $mode ('remote_write', 'on', 'remote_apply')
{
	$primary->safe_psql('postgres',
		"SET synchronous_commit = '$mode'; INSERT INTO waker_test VALUES ('direct_$mode')");
	pass("direct wakeup works for $mode");
}
$primary->wait_for_replay_catchup($standby);
is($standby->safe_psql('postgres', 'SELECT count(*) FROM waker_test'),
	'11', 'all committed rows reached the standby');

# A standby needs its own waker as soon as promotion enables local writes.
$standby->promote;
ok($standby->poll_query_until('postgres',
	"SELECT count(*) = 1 FROM pg_stat_activity WHERE backend_type = 'sync rep waker'"),
	'promotion starts the waker');

$standby->stop;
$primary->stop;
done_testing();
