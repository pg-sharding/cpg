# Copyright (c) 2026, PostgreSQL Global Development Group

# Small confirmed batches bypass a stopped waker, while larger batches must
# wait for it.  Hold the sender while assembling a batch so that its WAL fits
# in one replication message, rather than testing timing between commits.
use strict;
use warnings FATAL => 'all';
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

plan skip_all => 'test requires Unix signals' if $windows_os;

my $primary = PostgreSQL::Test::Cluster->new('primary');
$primary->init(allows_streaming => 1);
$primary->append_conf('postgresql.conf',
	"sync_rep_waker = on\nsync_rep_waker_direct_limit = 4");
$primary->start;
$primary->safe_psql('postgres', 'CREATE TABLE hybrid_test (a int)');
$primary->backup('backup');
my $standby = PostgreSQL::Test::Cluster->new('standby');
$standby->init_from_backup($primary, 'backup', has_streaming => 1);
$standby->start;
$primary->wait_for_replay_catchup($standby);
$primary->safe_psql('postgres',
	"ALTER SYSTEM SET synchronous_standby_names = 'standby'");
$primary->reload;

my %stopped;
END
{
	# Let the test framework shut down even if a query or assertion fails.
	kill 'CONT', $_ for keys %stopped;
}

sub suspend_process
{
	my ($kind) = @_;
	my $pid = $primary->safe_psql('postgres',
		"SELECT pid FROM pg_stat_activity WHERE backend_type = '$kind'");
	die "no $kind process" unless $pid =~ /^\d+$/;
	$stopped{$pid} = 1;
	die "cannot suspend $kind" unless kill 'STOP', $pid;
	return $pid;
}

sub resume_process
{
	my ($pid) = @_;
	die "cannot resume process $pid" unless kill 'CONT', $pid;
	delete $stopped{$pid};
}

sub queue_waiter
{
	my ($mode) = @_;
	my $session = $primary->background_psql('postgres');
	$session->set_query_timer_restart;
	$session->query_safe("SET synchronous_commit = '$mode'");
	my $pid = $session->query_safe('SELECT pg_backend_pid()');
	$session->query_until(qr/committing/,
		"BEGIN; INSERT INTO hybrid_test VALUES (1);\n"
		  . "\\echo committing\nCOMMIT;\n");
	die 'waiter did not enter SyncRep' unless $primary->poll_query_until(
		'postgres',
		"SELECT wait_event = 'SyncRep' FROM pg_stat_activity WHERE pid = $pid");
	return ($session, $pid);
}

sub finish_waiter
{
	my ($session) = @_;
	is($session->query_safe('SELECT 1'), '1', 'confirmed waiter released');
	$session->quit;
}

sub wait_for_ack
{
	my ($position) = @_;
	my $lsn = $primary->safe_psql('postgres', 'SELECT pg_current_wal_insert_lsn()');
	ok($primary->poll_query_until('postgres',
		"SELECT $position >= '$lsn'::pg_lsn FROM pg_stat_replication WHERE application_name = 'standby'"),
		"standby confirmed $position");
}

# A single ready waiter bypasses the waker in every wait mode.
for my $mode ('remote_write', 'on', 'remote_apply')
{
	my $waker = suspend_process('sync rep waker');
	my $sender = suspend_process('walsender');
	my ($session) = queue_waiter($mode);
	resume_process($sender);
	finish_waiter($session);
	resume_process($waker);
}

# The exact boundary takes the direct path; one more ready waiter delegates
# the whole batch.  Stop the sender before queueing so one reply confirms it.
for my $size (4, 5)
{
	my $waker = suspend_process('sync rep waker');
	my $sender = suspend_process('walsender');
	my (@sessions, @pids);
	for (1 .. $size)
	{
		my ($session, $pid) = queue_waiter('on');
		push @sessions, $session;
		push @pids, $pid;
	}
	resume_process($sender);
	wait_for_ack('flush_lsn');
	if ($size > 4)
	{
		is($primary->safe_psql('postgres',
			"SELECT count(*) FROM pg_stat_activity WHERE wait_event = 'SyncRep' AND pid IN ("
			  . join(',', @pids) . ')'),
			'5', 'oversized confirmed batch waits for the waker');
		resume_process($waker);
	}
	finish_waiter($_) for @sessions;
	resume_process($waker) if $size <= 4;
}

# A long unconfirmed apply queue must not prevent one ready flush waiter
# from taking the direct path.  It must not be released by the flush reply.
$standby->safe_psql('postgres', 'SELECT pg_wal_replay_pause()');
ok($standby->poll_query_until('postgres',
	"SELECT pg_get_wal_replay_pause_state() = 'paused'"),
	'replay is paused before assembling unconfirmed apply waiters');
my $waker = suspend_process('sync rep waker');
my $sender = suspend_process('walsender');
my (@apply_sessions, @apply_pids);
for (1 .. 5)
{
	my ($session, $pid) = queue_waiter('remote_apply');
	push @apply_sessions, $session;
	push @apply_pids, $pid;
}
my ($flush_session) = queue_waiter('on');
resume_process($sender);
finish_waiter($flush_session);
is($primary->safe_psql('postgres',
	"SELECT count(*) FROM pg_stat_activity WHERE wait_event = 'SyncRep' AND pid IN ("
	  . join(',', @apply_pids) . ')'),
	'5', 'unconfirmed apply waiters remain queued');
resume_process($waker);
$standby->safe_psql('postgres', 'SELECT pg_wal_replay_resume()');
finish_waiter($_) for @apply_sessions;

$primary->wait_for_replay_catchup($standby);
is($standby->safe_psql('postgres', 'SELECT count(*) FROM hybrid_test'),
	'18', 'all hybrid-path transactions reached the standby');
$standby->stop;
$primary->stop;
done_testing();
