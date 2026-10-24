# Copyright (c) 2026, PostgreSQL Global Development Group

# Stop a releaser after it publishes completion, but before it sets latches.
# Reuse a completed backend's PGPROC for an unconfirmed wait in that gap.
use strict;
use warnings FATAL => 'all';
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

plan skip_all => 'test requires Unix signals' if $windows_os;
plan skip_all => 'Injection points not supported by this build'
  unless $ENV{enable_injection_points} eq 'yes';

my $primary = PostgreSQL::Test::Cluster->new('primary');
$primary->init(allows_streaming => 1);
$primary->append_conf('postgresql.conf',
	"max_connections = 12\nautovacuum = off\nsync_rep_waker = on");
$primary->start;
plan skip_all => 'Extension injection_points not installed'
  unless $primary->check_extension('injection_points');
$primary->safe_psql('postgres',
	'CREATE EXTENSION injection_points; CREATE TABLE wake_after_unlock (a int)');
$primary->backup('backup');
my $standby = PostgreSQL::Test::Cluster->new('standby');
$standby->init_from_backup($primary, 'backup', has_streaming => 1);
$standby->start;
$primary->wait_for_replay_catchup($standby);
$primary->safe_psql('postgres',
	"ALTER SYSTEM SET synchronous_standby_names = 'standby'");
$primary->reload;

my $point = 'sync-rep-before-latch-wake';
my $point_active = 0;
my %stopped;
END
{
	kill 'CONT', $_ for keys %stopped;
	if ($point_active)
	{
		eval {
			$primary->safe_psql('postgres',
				"SELECT injection_points_detach('$point'); SELECT injection_points_wakeup('$point')");
		};
	}
}

sub suspend_process
{
	my ($node, $kind) = @_;
	my $pid = $node->safe_psql('postgres',
		"SELECT pid FROM pg_stat_activity WHERE backend_type = '$kind'");
	die "no $kind process" unless $pid =~ /^\d+$/;
	$stopped{$pid} = 1;
	die "cannot suspend $kind" unless kill 'STOP', $pid;
	return $pid;
}

sub resume_process
{
	my ($pid) = @_;
	die "cannot resume $pid" unless kill 'CONT', $pid;
	delete $stopped{$pid};
}

sub proc_number
{
	my ($session) = @_;
	return $session->query_safe(
		'SELECT n FROM pg_stat_get_backend_idset() AS n WHERE pg_stat_get_backend_pid(n) = pg_backend_pid()');
}

sub queue_waiter
{
	my ($session) = @_;
	$session->set_query_timer_restart;
	$session->query_safe('SET synchronous_commit_cancelation = on');
	my $pid = $session->query_safe('SELECT pg_backend_pid()');
	$session->query_until(qr/committing/,
		"BEGIN; INSERT INTO wake_after_unlock VALUES (1);\n"
		  . "\\echo committing\nCOMMIT;\n");
	ok($primary->poll_query_until('postgres',
		"SELECT wait_event_type = 'IPC' AND wait_event = 'SyncRep' FROM pg_stat_activity WHERE pid = $pid"),
		'backend queued after acquiring SyncRepLock');
	return $pid;
}

for my $case (['waker', 'on', 0], ['hybrid', 'on', 4], ['direct', 'off', 0])
{
	my ($name, $enabled, $limit) = @$case;
	$primary->append_conf('postgresql.conf',
		"sync_rep_waker = $enabled\nsync_rep_waker_direct_limit = $limit");
	$primary->restart;
	$primary->wait_for_replay_catchup($standby);
	my $sender = suspend_process($primary, 'walsender');
	my $session = $primary->background_psql('postgres');
	my $slot = proc_number($session);
	my $pid = queue_waiter($session);
	$primary->safe_psql('postgres',
		"SELECT injection_points_attach('$point', 'wait')");
	$point_active = 1;
	resume_process($sender);
	my $releaser = $name eq 'waker' ? 'sync rep waker' : 'walsender';
	$primary->wait_for_event($releaser, $point);

	# An unrelated wake observes completion before the deferred SetLatch.
	ok(kill('USR1', $pid), "$name: send unrelated backend wakeup");
	is($session->query_safe('SELECT 1'), '1',
		"$name: completed backend continues while releaser is paused");
	$session->quit;

	# No feedback may cover the new transaction while the slot is reused.
	my $receiver = suspend_process($standby, 'walreceiver');
	my $reused;
	for (1 .. 24)
	{
		my $candidate = $primary->background_psql('postgres');
		if (proc_number($candidate) eq $slot)
		{
			$reused = $candidate;
			last;
		}
		$candidate->quit;
	}
	ok(defined($reused), "$name: completed backend's PGPROC slot reused");
	die 'could not reuse PGPROC slot' unless defined($reused);
	my $new_pid = queue_waiter($reused);

	$primary->safe_psql('postgres',
		"SELECT injection_points_detach('$point'); SELECT injection_points_wakeup('$point')");
	$point_active = 0;
	ok($primary->poll_query_until('postgres',
		"SELECT count(*) = 0 FROM pg_stat_activity WHERE wait_event = '$point'"),
		"$name: releaser finished its deferred latch loop");
	is($primary->safe_psql('postgres',
		"SELECT wait_event_type || '/' || wait_event FROM pg_stat_activity WHERE pid = $new_pid"),
		'IPC/SyncRep', "$name: old latch does not complete the new unconfirmed wait");
	$primary->safe_psql('postgres', "SELECT pg_cancel_backend($new_pid)");
	is($reused->query('SELECT 1'), '1',
		"$name: reused backend cancels its wait normally");
	like($reused->{stderr},
		qr/canceling wait for synchronous replication due to user request/,
		"$name: cancellation reports the locally committed transaction");
	$reused->quit;
	resume_process($receiver);
	$primary->safe_psql('postgres', 'INSERT INTO wake_after_unlock VALUES (1)');
	$primary->wait_for_replay_catchup($standby);
}

is($standby->safe_psql('postgres', 'SELECT count(*) FROM wake_after_unlock'),
	'9', 'all committed transactions reached the standby');
$standby->stop;
$primary->stop;
done_testing();
