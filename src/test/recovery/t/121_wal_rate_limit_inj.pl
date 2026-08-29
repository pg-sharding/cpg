# Copyright (c) 2026, PostgreSQL Global Development Group

# Test that ycmdb.wal_write_rate_lim correctly reports its wait event
# via the injection points "wal_writer_rate_limit_wait_loop" and
# "wal_writer_rate_limit_before_exit".

use strict;
use warnings FATAL => 'all';

use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

if ($ENV{enable_injection_points} ne 'yes')
{
	plan skip_all => 'Injection points not supported by this build';
}

sub wait_for_injection_point
{
	my ($node, $point_name, $timeout) = @_;
	$timeout //= $PostgreSQL::Test::Utils::timeout_default / 2;

	for (my $elapsed = 0; $elapsed < $timeout * 10; $elapsed++)
	{
		my $pid = $node->safe_psql(
			'postgres', qq[
			SELECT pid FROM pg_stat_activity
			WHERE wait_event_type = 'InjectionPoint'
			  AND wait_event = '$point_name'
			LIMIT 1;
		]);
		return 1 if $pid ne '';
		sleep(1);
	}

	my $activity = $node->safe_psql(
		'postgres', q[
		SELECT format('pid=%s, state=%s, wait_event_type=%s, wait_event=%s, query=%s',
			pid, state, wait_event_type, wait_event, left(query, 100))
		FROM pg_stat_activity
		ORDER BY pid;
	]);
	diag(   "wait_for_injection_point timeout waiting for: $point_name\n"
		  . "Current queries in pg_stat_activity:\n$activity");

	return 0;
}

my $node = PostgreSQL::Test::Cluster->new('wal_rate_lim');
$node->init;
$node->append_conf(
	'postgresql.conf', qq(
shared_preload_libraries = 'injection_points'
synchronous_commit = off
ycmdb.wal_write_rate_lim = '1MB'
));
$node->start;

if (!$node->check_extension('injection_points'))
{
	plan skip_all => 'Extension injection_points not installed';
}
$node->safe_psql('postgres', 'CREATE EXTENSION injection_points;');

# --- Test 1: WAL_WRITE_RATE_LIMIT wait event visible during throttle loop ---

$node->safe_psql('postgres',
	"SELECT injection_points_attach('wal_writer_rate_limit_wait_loop', 'wait');");

# Generate a WAL record
my $psql = $node->background_psql('postgres', on_error_stop => 0);

# The backend cycles through the throttle loop with pg_usleep reporting
# WAL_WRITE_RATE_LIMIT.
my $pid = $psql->query_safe('SELECT pg_backend_pid()');

$psql->{stdin} .= qq(SELECT txid_current();\n);

$psql->{run}->pump_nb();

ok(wait_for_injection_point($node, 'wal_writer_rate_limit_wait_loop'),
   'backend reached wal_writer_rate_limit_wait_loop injection point');

# Wake up the injection point so the backend enters the throttle loop.
$node->safe_psql('postgres',
	"SELECT injection_points_wakeup('wal_writer_rate_limit_wait_loop');");

$node->safe_psql('postgres',
	"SELECT injection_points_detach('wal_writer_rate_limit_wait_loop');");

$psql->quit;

$node->stop;

done_testing();
