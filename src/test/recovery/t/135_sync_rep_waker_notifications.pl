# Copyright (c) 2026, PostgreSQL Global Development Group

# An ACK coalesced before a drain and an ACK arriving after the pending flag
# is cleared must both release their waiters without requiring another ACK.
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
	"sync_rep_waker = on\nsync_rep_waker_direct_limit = 0");
$primary->start;
plan skip_all => 'Extension injection_points not installed'
  unless $primary->check_extension('injection_points');
$primary->safe_psql('postgres',
	'CREATE EXTENSION injection_points; CREATE TABLE notification_test (a int)');
$primary->backup('backup');
my $standby = PostgreSQL::Test::Cluster->new('standby');
$standby->init_from_backup($primary, 'backup', has_streaming => 1);
$standby->start;
$primary->wait_for_replay_catchup($standby);
$primary->safe_psql('postgres',
	"ALTER SYSTEM SET synchronous_standby_names = 'standby'");
$primary->reload;

my %stopped;
my $active_point;
END
{
	kill 'CONT', $_ for keys %stopped;
	if (defined $active_point)
	{
		eval {
			$primary->safe_psql('postgres',
				"SELECT injection_points_detach('$active_point'); SELECT injection_points_wakeup('$active_point')");
		};
	}
}

sub stop_sender
{
	my $pid = $primary->safe_psql('postgres',
		"SELECT pid FROM pg_stat_activity WHERE backend_type = 'walsender'");
	die 'no sender' unless $pid =~ /^\d+$/;
	$stopped{$pid} = 1;
	die 'cannot stop sender' unless kill 'STOP', $pid;
	return $pid;
}

sub resume_sender
{
	my ($pid) = @_;
	die 'cannot resume sender' unless kill 'CONT', $pid;
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
		"BEGIN; INSERT INTO notification_test VALUES (1);\n\\echo committing\nCOMMIT;\n");
	die 'waiter did not enter SyncRep' unless $primary->poll_query_until(
		'postgres',
		"SELECT wait_event = 'SyncRep' FROM pg_stat_activity WHERE pid = $pid");
	return $session;
}

for my $point ('sync-rep-waker-before-drain', 'sync-rep-before-latch-wake')
{
	for my $mode ('remote_write', 'on', 'remote_apply')
	{
		my $sender = stop_sender();
		my $first = queue_waiter($mode);
		$primary->safe_psql('postgres',
			"SELECT injection_points_attach('$point', 'wait')");
		$active_point = $point;
		resume_sender($sender);
		$primary->wait_for_event('sync rep waker', $point);
		my $second = queue_waiter($mode);
		my $lsn = $primary->safe_psql('postgres', 'SELECT pg_current_wal_insert_lsn()');
		my $position = $mode eq 'remote_write' ? 'write_lsn'
		  : $mode eq 'on' ? 'flush_lsn' : 'replay_lsn';
		ok($primary->poll_query_until('postgres',
			"SELECT $position >= '$lsn'::pg_lsn FROM pg_stat_replication WHERE application_name = 'standby'"),
			"$mode: second ACK published while waker paused at $point");
		# Prevent periodic feedback from repairing a missed notification.
		$sender = stop_sender();
		$primary->safe_psql('postgres',
			"SELECT injection_points_detach('$point'); SELECT injection_points_wakeup('$point')");
		undef $active_point;
		for my $session ($first, $second)
		{
			is($session->query_safe('SELECT 1'), '1',
				"$mode: waiter completes without another sender ACK");
			$session->quit;
		}
		resume_sender($sender);
	}
}

$primary->wait_for_replay_catchup($standby);
is($standby->safe_psql('postgres', 'SELECT count(*) FROM notification_test'),
	'12', 'all notification-race transactions reached the standby');
$standby->stop;
$primary->stop;
done_testing();
