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

my $node = PostgreSQL::Test::Cluster->new('wal_rate_lim');
$node->init;
$node->append_conf(
	'postgresql.conf', qq(
shared_preload_libraries = 'injection_points'
synchronous_commit = off
ycmdb.wal_write_rate_lim = '1kB'
));
$node->start;

if (!$node->check_extension('injection_points'))
{
	plan skip_all => 'Extension injection_points not installed';
}
$node->safe_psql('postgres', 'CREATE EXTENSION injection_points;');

$node->safe_psql('postgres', 'CREATE TABLE wal_rate_test(a text);');

# Generate a data file for COPY.
my $copyfile = $node->data_dir . '/rate_test.csv';
$node->safe_psql('postgres',
	"COPY (SELECT i::text FROM generate_series(1, 10000) i) TO '$copyfile';");

# --- Test 1: WAL_WRITE_RATE_LIMIT wait event visible during throttle loop ---

$node->safe_psql('postgres',
	"SELECT injection_points_attach('wal_writer_rate_limit_wait_loop', 'wait');");

my $psql = $node->background_psql('postgres', on_error_stop => 0);
my $pid = $psql->query_safe('SELECT pg_backend_pid()');

$psql->{stdin} .= qq(COPY wal_rate_test FROM '$copyfile';\n);
$psql->{run}->pump_nb();

# Wake up the injection point so the backend enters the throttle loop.
$node->safe_psql('postgres',
	"SELECT injection_points_wakeup('wal_writer_rate_limit_wait_loop');");

# The backend cycles through the throttle loop with pg_usleep reporting
# WAL_WRITE_RATE_LIMIT.
my $seen = $node->poll_query_until(
	'postgres',
	qq(SELECT wait_event FROM pg_stat_activity WHERE pid = $pid),
	'WAL_WRITE_RATE_LIMIT');
ok($seen, 'backend shows WAL_WRITE_RATE_LIMIT wait event while throttled');

$node->safe_psql('postgres',
	"SELECT injection_points_detach('wal_writer_rate_limit_wait_loop');");

$psql->query_until(qr/^$/, undef);
$psql->quit;

# --- Test 2: wal_writer_rate_limit_before_exit injection point ---

$node->safe_psql('postgres', 'TRUNCATE wal_rate_test;');

$node->safe_psql('postgres',
	"SELECT injection_points_attach('wal_writer_rate_limit_before_exit', 'wait');");

$psql = $node->background_psql('postgres', on_error_stop => 0);
$pid = $psql->query_safe('SELECT pg_backend_pid()');

$psql->{stdin} .= qq(COPY wal_rate_test FROM '$copyfile';\n);
$psql->{run}->pump_nb();

# The backend will block at the before_exit injection point.
ok($node->poll_query_until(
		'postgres',
		qq(SELECT wait_event IS NOT NULL FROM pg_stat_activity WHERE pid = $pid),
		't'),
   'backend is blocked at before_exit injection point');

$node->safe_psql('postgres',
	"SELECT injection_points_detach('wal_writer_rate_limit_before_exit');");
$psql->query_until(qr/^$/, undef);
$psql->quit;

# Cleanup.
$node->safe_psql('postgres', 'DROP TABLE wal_rate_test;');
$node->stop;
done_testing();
