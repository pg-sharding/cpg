# Copyright (c) 2026, PostgreSQL Global Development Group

# Pause a sender after its bounded direct wakeups, before notifying the waker.
# Further ACKs cannot obscure whether the direct budget was respected.
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
	"sync_rep_waker = on\nsync_rep_waker_direct_limit = 4");
$primary->start;
plan skip_all => 'Extension injection_points not installed'
  unless $primary->check_extension('injection_points');
$primary->safe_psql('postgres',
	'CREATE EXTENSION injection_points; CREATE TABLE handoff_test (a int)');
$primary->backup('backup');
my $standby = PostgreSQL::Test::Cluster->new('standby');
$standby->init_from_backup($primary, 'backup', has_streaming => 1);
$standby->start;
$primary->wait_for_replay_catchup($standby);
$primary->safe_psql('postgres',
	"ALTER SYSTEM SET synchronous_standby_names = 'standby'");
$primary->reload;

my %stopped;
my $point = 'sync-rep-after-direct-wake';
my $point_active = 0;
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
		"BEGIN; INSERT INTO handoff_test VALUES (1);\n\\echo committing\nCOMMIT;\n");
	die 'waiter did not enter SyncRep' unless $primary->poll_query_until(
		'postgres',
		"SELECT wait_event = 'SyncRep' FROM pg_stat_activity WHERE pid = $pid");
	return ($session, $pid);
}

my $transactions = 0;
# Use one mode at a time: write, flush and apply need not be confirmed by
# the same ACK. In each case a single ACK confirms the assembled prefix.
for my $modes ([qw(remote_write remote_write remote_write remote_write remote_write remote_write)],
	[qw(on on on on on on)],
	[qw(remote_apply remote_apply remote_apply remote_apply remote_apply remote_apply)])
{
	my $waker = suspend_process('sync rep waker');
	my $sender = suspend_process('walsender');
	my (@sessions, @pids);
	for my $mode (@$modes)
	{
		my ($session, $pid) = queue_waiter($mode);
		push @sessions, $session;
		push @pids, $pid;
		$transactions++;
	}
	$primary->safe_psql('postgres',
		"SELECT injection_points_attach('$point', 'wait')");
	$point_active = 1;
	resume_process($sender);
	$primary->wait_for_event('walsender', $point);
	my $pids = join(',', @pids);
	ok($primary->poll_query_until('postgres',
		"SELECT count(*) = 2 FROM pg_stat_activity WHERE wait_event = 'SyncRep' AND pid IN ($pids)"),
		'exactly four waiters released directly');
	for my $i (0 .. 3)
	{
		is($sessions[$i]->query_safe('SELECT 1'), '1',
			'direct prefix completes while sender and waker are paused');
	}
	$primary->safe_psql('postgres',
		"SELECT injection_points_detach('$point'); SELECT injection_points_wakeup('$point')");
	$point_active = 0;
	resume_process($waker);
	for my $session (@sessions)
	{
		is($session->query_safe('SELECT 1'), '1', 'confirmed remainder completes');
		$session->quit;
	}
}

$primary->wait_for_replay_catchup($standby);
is($standby->safe_psql('postgres', 'SELECT count(*) FROM handoff_test'),
	"$transactions", 'all handoff transactions reached the standby');
$standby->stop;
$primary->stop;
done_testing();
