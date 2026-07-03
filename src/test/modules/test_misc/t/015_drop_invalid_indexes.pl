
# Copyright (c) 2026, PostgreSQL Global Development Group

# Tests for pg_drop_invalid_indexes().
#
# An invalid index is produced by interrupting REINDEX TABLE CONCURRENTLY
# while it is paused on the 'index-build-after-am-callback' injection point.
# We then verify that pg_drop_invalid_indexes() reports and drops exactly the
# invalid indexes, while leaving valid ones untouched.

use strict;
use warnings FATAL => 'all';

use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use PostgreSQL::Test::BackgroundPsql;
use Test::More;
use Time::HiRes qw(usleep);

plan skip_all => 'Injection points not supported by this build'
  unless $ENV{enable_injection_points} eq 'yes';

my $node = PostgreSQL::Test::Cluster->new('drop_invalid_index');
$node->init;
$node->start;

# Check if the extension injection_points is available, as it may be
# possible that this script is run with installcheck, where the module
# would not be installed by default.
plan skip_all => 'Extension injection_points not installed'
  unless $node->check_extension('injection_points');

$node->safe_psql('postgres', 'CREATE EXTENSION injection_points;');

# Produce an invalid index on table $table by cancelling an in-progress
# REINDEX TABLE CONCURRENTLY that is paused on the injection point.  The
# application_name is used to locate and cancel the backend.
sub make_invalid_index
{
	my ($table, $appname) = @_;

	$node->safe_psql('postgres',
		"SELECT injection_points_attach('index-build-after-am-callback', 'wait');"
	);

	my $bgpsql = $node->background_psql('postgres', wait => 0);
	$bgpsql->query_safe("SET application_name TO $appname;");

	# Kick off REINDEX; it will block on the injection point.
	$bgpsql->query_until(
		qr/starting_bg_psql/, qq(
   \\echo starting_bg_psql
   REINDEX TABLE CONCURRENTLY $table;
));

	# Wait until the backend actually reaches the injection point.
	wait_for_injection_point('index-build-after-am-callback');

	# Cancel the paused backend.  injection_wait() polls with
	# CHECK_FOR_INTERRUPTS(), so the cancel interrupt aborts the wait on its
	# own (no wakeup needed); REINDEX CONCURRENTLY then rolls back, leaving an
	# invalid index behind.
	$node->safe_psql('postgres',
		"SELECT pg_cancel_backend(pid) FROM pg_stat_activity WHERE application_name = '$appname';"
	);

	# The background REINDEX exits with an error; drain the session.
	$bgpsql->quit;

	# Detach the injection point so the next invocation can re-attach it.
	$node->safe_psql('postgres',
		"SELECT injection_points_detach('index-build-after-am-callback');");

	# Make sure the aborted REINDEX has actually produced an invalid index
	# before returning to the caller.
	$node->poll_query_until('postgres',
		"SELECT count(*) > 0 FROM pg_index WHERE indrelid = '$table'::regclass AND NOT indisvalid;",
		't')
	  or die "timed out waiting for invalid index on $table";
}

sub wait_for_injection_point
{
	my ($point_name) = @_;
	my $timeout = $PostgreSQL::Test::Utils::timeout_default;

	for (my $elapsed = 0; $elapsed < $timeout * 10; $elapsed++)
	{
		my $pid = $node->safe_psql(
			'postgres', qq[
			SELECT pid FROM pg_stat_activity
			WHERE wait_event_type = 'InjectionPoint'
			  AND wait_event = '$point_name'
			LIMIT 1;
		]);
		return if $pid ne '';
		usleep(100_000);
	}
	die "timed out waiting for injection point $point_name";
}

sub count_invalid_indexes
{
	my ($table) = @_;
	return $node->safe_psql('postgres',
		"SELECT count(*) FROM pg_index WHERE indrelid = '$table'::regclass AND NOT indisvalid;"
	);
}

####################################################################
note('Test: pg_drop_invalid_indexes drops a single invalid index');

$node->safe_psql('postgres', 'CREATE TABLE tt (i INT PRIMARY KEY);');
$node->safe_psql('postgres', 'INSERT INTO tt SELECT generate_series(1, 10);');

make_invalid_index('tt', 'drop_invalid_index');

is(count_invalid_indexes('tt'), '1', 'one invalid index created');

# The function must report the dropped index: a non-empty name and a valid
# oid.  REINDEX CONCURRENTLY leaves the transient copy invalid, so its name
# carries a "_ccnew" suffix rather than matching the original index name.
my $result = $node->safe_psql('postgres',
	q{SELECT count(*), bool_and(index_name <> '' AND index_oid IS NOT NULL) FROM pg_drop_invalid_indexes('tt');}
);
is($result, "1|t", 'reports dropped invalid index name and oid');

is(count_invalid_indexes('tt'), '0', 'invalid index dropped');

# Valid index must remain in place.
is( $node->safe_psql(
		'postgres',
		"SELECT count(*) FROM pg_index WHERE indrelid = 'tt'::regclass;"),
	'1',
	'valid index left untouched');

####################################################################
note('Test: pg_drop_invalid_indexes on a table with no invalid indexes');

$result = $node->safe_psql('postgres',
	q{SELECT count(*) FROM pg_drop_invalid_indexes('tt');});
is($result, '0', 'returns empty set when nothing to drop');

is( $node->safe_psql(
		'postgres',
		"SELECT count(*) FROM pg_index WHERE indrelid = 'tt'::regclass;"),
	'1',
	'valid index still present');

####################################################################
note('Test: pg_drop_invalid_indexes acts only on the given table');

# Build an invalid index on a second table and make sure dropping invalid
# indexes on one table does not affect the other.
$node->safe_psql('postgres', 'CREATE TABLE tt2 (i INT PRIMARY KEY);');
$node->safe_psql('postgres', 'INSERT INTO tt2 SELECT generate_series(1, 10);');

make_invalid_index('tt', 'drop_invalid_index_tt');
make_invalid_index('tt2', 'drop_invalid_index_tt2');

is(count_invalid_indexes('tt'), '1', 'invalid index on tt created');
is(count_invalid_indexes('tt2'), '1', 'invalid index on tt2 created');

# Dropping on tt must not touch tt2.
my $dropped = $node->safe_psql('postgres',
	q{SELECT count(*) FROM pg_drop_invalid_indexes('tt');});
is($dropped, '1', 'drops invalid index on tt');

is(count_invalid_indexes('tt'), '0', 'invalid index on tt dropped');
is(count_invalid_indexes('tt2'), '1', 'invalid index on tt2 preserved');

# Now clean up tt2 as well.
$dropped = $node->safe_psql('postgres',
	q{SELECT count(*) FROM pg_drop_invalid_indexes('tt2');});
is($dropped, '1', 'drops invalid index on tt2');
is(count_invalid_indexes('tt2'), '0', 'invalid index on tt2 dropped');

done_testing();
