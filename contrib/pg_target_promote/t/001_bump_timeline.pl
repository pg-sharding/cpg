
# Copyright (c) 2026, PostgreSQL Global Development Group

# Test pg_bump_timeline(): force a timeline switch on a running primary
# (not in recovery) and verify that a streaming standby follows the
# primary across the timeline switch.
use strict;
use warnings FATAL => 'all';
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

# Initialize primary node
my $node_primary = PostgreSQL::Test::Cluster->new('primary');
$node_primary->init(allows_streaming => 1);
$node_primary->start;

# Create the extension
$node_primary->safe_psql('postgres', 'CREATE EXTENSION pg_target_promote');

# Take backup
my $backup_name = 'my_backup';
$node_primary->backup($backup_name);

# Create a standby
my $node_standby = PostgreSQL::Test::Cluster->new('standby');
$node_standby->init_from_backup($node_primary, $backup_name,
	has_streaming => 1);
$node_standby->start;

# Wait for standby to connect
$node_primary->poll_query_until('postgres',
	"SELECT count(1) = 1 FROM pg_stat_replication");

# Create some initial data
$node_primary->safe_psql('postgres',
	"CREATE TABLE tab_int AS SELECT generate_series(1,1000) AS a");
$node_primary->wait_for_catchup($node_standby);

# Record the current timeline
my $tli_before = $node_primary->safe_psql('postgres',
	"SELECT timeline_id FROM pg_control_checkpoint()");
ok($tli_before > 0, "initial timeline is $tli_before");

# Bump the timeline on the primary while it is running (not in recovery)
$node_primary->safe_psql('postgres', 'SELECT pg_bump_timeline()');

# Verify that the timeline has increased
my $tli_after = $node_primary->safe_psql('postgres',
	"SELECT timeline_id FROM pg_control_checkpoint()");
is($tli_after, $tli_before + 1,
	"timeline bumped from $tli_before to $tli_after");

# Verify that a history file was written
my $history_file = sprintf("%s/%08X.history", $node_primary->data_dir, $tli_after);
ok(-f $history_file, "timeline history file exists");

# Insert more data and check that the standby follows across the timeline switch
$node_primary->safe_psql('postgres',
	"INSERT INTO tab_int VALUES (generate_series(1001,2000))");
$node_primary->wait_for_catchup($node_standby);

my $result = $node_standby->safe_psql('postgres',
	"SELECT count(*) FROM tab_int");
is($result, '2000', 'standby replicated data after timeline bump');

# The standby should now be on the same timeline as the primary
my $standby_tli = $node_standby->safe_psql('postgres',
	"SELECT timeline_id FROM pg_control_checkpoint()");
is($standby_tli, $tli_after,
	"standby followed primary to timeline $tli_after");

# Bump again to make sure repeated calls work
$node_primary->safe_psql('postgres', 'SELECT pg_bump_timeline()');
my $tli_after2 = $node_primary->safe_psql('postgres',
	"SELECT timeline_id FROM pg_control_checkpoint()");
is($tli_after2, $tli_after + 1, "second timeline bump works");

$node_primary->safe_psql('postgres',
	"INSERT INTO tab_int VALUES (generate_series(2001,3000))");
$node_primary->wait_for_catchup($node_standby);

$result = $node_standby->safe_psql('postgres',
	"SELECT count(*) FROM tab_int");
is($result, '3000', 'standby replicated data after second timeline bump');

# pg_bump_timeline() should fail on a standby (in recovery)
$node_standby->safe_psql('postgres', 'CREATE EXTENSION pg_target_promote');
my ($ret, $stdout, $stderr) = $node_standby->psql('postgres',
	'SELECT pg_bump_timeline()');
isnt($ret, 0, 'pg_bump_timeline fails on standby');
like($stderr, qr/recovery is in progress/,
	'pg_bump_timeline error message on standby');

done_testing();
