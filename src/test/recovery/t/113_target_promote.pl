
# Copyright (c) 2025, PostgreSQL Global Development Group

# Test for pg_target_promote(), which is like pg_promote() but allows
# specifying the target timeline ID to switch to upon promotion.
use strict;
use warnings FATAL => 'all';
use File::Copy qw(copy);
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

# Helper: get the current timeline of a node by looking at the WAL
# segment filename.  Works both during recovery and after promotion.
sub get_timeline_from_wal
{
	my ($node) = @_;
	my $wal_dir = $node->data_dir . '/pg_wal';
	opendir(my $dh, $wal_dir) or die "cannot open $wal_dir: $!";
	my @files = grep { /^\d{24}$/ } readdir($dh);
	closedir($dh);
	# Sort descending to get the newest segment
	@files = sort { $b cmp $a } @files;
	return substr($files[0], 0, 8) if @files;
	return undef;
}

# Initialize primary node
my $node_primary = PostgreSQL::Test::Cluster->new('primary');
$node_primary->init(allows_streaming => 1);
$node_primary->start;

# Take backup
my $backup_name = 'my_backup';
$node_primary->backup($backup_name);

# Create standby linking to primary
my $node_standby = PostgreSQL::Test::Cluster->new('standby');
$node_standby->init_from_backup($node_primary, $backup_name,
	has_streaming => 1);
$node_standby->start;

# Load the extension that provides pg_target_promote()
$node_standby->safe_psql('postgres',
	"CREATE EXTENSION pg_target_promote");

# Wait for standby to connect to primary
$node_primary->poll_query_until('postgres',
	"SELECT count(1) = 1 FROM pg_stat_replication");

# Create some content on primary and wait for standby to catch up
$node_primary->safe_psql('postgres',
	"CREATE TABLE tab_int AS SELECT generate_series(1,1000) AS a");
$node_primary->wait_for_catchup($node_standby);

# Stop primary cleanly so standby has all WAL
$node_primary->stop;

# Verify the standby is on timeline 1
my $standby_tli = get_timeline_from_wal($node_standby);
is($standby_tli, '00000001', "standby initially on timeline 1");

# Promote the standby to timeline 5 using pg_target_promote()
my $psql_out = '';
$node_standby->psql(
	'postgres',
	"SELECT pg_target_promote(5, true, 300)",
	stdout => \$psql_out);
is($psql_out, 't', "pg_target_promote returns true");

# Wait for promotion to complete
$node_standby->poll_query_until('postgres',
	"SELECT NOT pg_is_in_recovery()")
  or die "Timed out while waiting for promotion";

# Verify that the standby is no longer in recovery
is($node_standby->safe_psql('postgres', "SELECT pg_is_in_recovery()"),
	'f', "standby promoted out of recovery");

# Verify the timeline is now 5 by checking the WAL filename
$node_standby->safe_psql('postgres', "SELECT pg_switch_wal()");
my $walfile = $node_standby->safe_psql('postgres',
	"SELECT pg_walfile_name(pg_current_wal_lsn())");
my $promoted_tli = substr($walfile, 0, 8);
is($promoted_tli, '00000005', "promoted standby is on timeline 5");

# Verify we can write to the promoted primary
$node_standby->safe_psql('postgres',
	"INSERT INTO tab_int VALUES (generate_series(1001,2000))");
my $count = $node_standby->safe_psql('postgres',
	"SELECT count(*) FROM tab_int");
is($count, '2000', "data present on promoted standby");

# Verify the timeline history file was created
my $pg_wal = $node_standby->data_dir . "/pg_wal";
ok(-f "$pg_wal/00000005.history", "timeline history file for TLI 5 exists");

# ---
# Test: pg_target_promote fails when not in recovery
# ---
my $ret = $node_standby->psql('postgres',
	"SELECT pg_target_promote(6, true, 60)",
	stdout => \$psql_out);
isnt($ret, 0, "pg_target_promote fails when not in recovery");

# Stop the promoted standby, so we can set up a fresh standby
$node_standby->stop;

# ---
# Test: pg_target_promote with an already-existing timeline should fail
# ---
# Set up a fresh standby from the original primary backup
my $node_standby2 = PostgreSQL::Test::Cluster->new('standby2');
$node_standby2->init_from_backup($node_primary, $backup_name,
	has_streaming => 1);
$node_standby2->start;

# Load the extension on standby2 as well
$node_standby2->safe_psql('postgres',
	"CREATE EXTENSION pg_target_promote");

# Wait for it to be in recovery
ok($node_standby2->safe_psql('postgres', "SELECT pg_is_in_recovery()"),
	"standby2 is in recovery");

# Copy the history file from the promoted standby to standby2's pg_wal
# so that existsTimeLineHistory() will find timeline 5 as existing.
my $standby_pg_wal = $node_standby->data_dir . "/pg_wal";
my $standby2_pg_wal = $node_standby2->data_dir . "/pg_wal";
copy("$standby_pg_wal/00000005.history", "$standby2_pg_wal/00000005.history")
	or die "copy failed: $!";

# Now try to promote standby2 to timeline 5, which already exists
$ret = $node_standby2->psql('postgres',
	"SELECT pg_target_promote(5, true, 60)",
	stdout => \$psql_out);
isnt($ret, 0, "pg_target_promote fails with already-existing timeline");

# Verify standby2 is still in recovery
ok($node_standby2->safe_psql('postgres', "SELECT pg_is_in_recovery()"),
	"standby2 still in recovery after failed promotion");

# ---
# Test: pg_target_promote with target_timeline = 0 should fail
# ---
$ret = $node_standby2->psql('postgres',
	"SELECT pg_target_promote(0, true, 60)",
	stdout => \$psql_out);
isnt($ret, 0, "pg_target_promote fails with timeline 0");

# Verify standby2 is still in recovery
ok($node_standby2->safe_psql('postgres', "SELECT pg_is_in_recovery()"),
	"standby2 still in recovery after invalid timeline");

# Remove the history file so timeline 5 no longer appears to exist
# for standby2, then promote it to a valid unused timeline (6)
unlink("$standby2_pg_wal/00000005.history");

# ---
# Test: promote standby2 to a different valid timeline (6)
# ---
$ret = $node_standby2->psql('postgres',
	"SELECT pg_target_promote(6, true, 300)",
	stdout => \$psql_out);
is($psql_out, 't', "pg_target_promote succeeds with timeline 6");

# Wait for promotion to complete
$node_standby2->poll_query_until('postgres',
	"SELECT NOT pg_is_in_recovery()")
  or die "Timed out while waiting for promotion of standby2";

# Verify that the standby is no longer in recovery
is($node_standby2->safe_psql('postgres', "SELECT pg_is_in_recovery()"),
	'f', "standby2 promoted out of recovery");

# Verify the timeline is now 6
$node_standby2->safe_psql('postgres', "SELECT pg_switch_wal()");
$walfile = $node_standby2->safe_psql('postgres',
	"SELECT pg_walfile_name(pg_current_wal_lsn())");
my $promoted2_tli = substr($walfile, 0, 8);
is($promoted2_tli, '00000006', "standby2 promoted to timeline 6");

# Clean up
$node_standby2->stop;

done_testing();
