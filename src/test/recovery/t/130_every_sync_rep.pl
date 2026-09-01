
# Copyright (c) 2025, PostgreSQL Global Development Group

# Test forced (EVERY) standbys in synchronous replication.  The EVERY
# block names standbys that must always acknowledge a commit, in
# addition to the quorum standbys selected from the ANY list.  Forced
# standbys are required to be part of ANY() as well.

use strict;
use warnings FATAL => 'all';
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

# Query checking sync_priority and sync_state of each standby
my $check_sql =
  "SELECT application_name, sync_priority, sync_state FROM pg_stat_replication ORDER BY application_name;";

# Check that sync_state of each standby is expected (waiting till it is).
# If $setting is given, synchronous_standby_names is set to it and
# the configuration file is reloaded before the test.
sub test_sync_state
{
	local $Test::Builder::Level = $Test::Builder::Level + 1;

	my ($self, $expected, $msg, $setting) = @_;

	if (defined($setting))
	{
		$self->safe_psql('postgres',
			"ALTER SYSTEM SET synchronous_standby_names = '$setting';");
		$self->reload;
	}

	ok($self->poll_query_until('postgres', $check_sql, $expected), $msg);
	return;
}

# Start a standby and wait until it is registered on the primary.
sub start_standby_and_wait
{
	my ($primary, $standby) = @_;
	my $primary_name = $primary->name;
	my $standby_name = $standby->name;
	my $query =
	  "SELECT count(1) = 1 FROM pg_stat_replication WHERE application_name = '$standby_name'";

	$standby->start;

	print("### Waiting for standby \"$standby_name\" on \"$primary_name\"\n");
	$primary->poll_query_until('postgres', $query);
	return;
}

# Wait until the given background psql session is waiting on SyncRep,
# proving that a commit is blocked on synchronous replication.
sub wait_blocked_on_syncrep
{
	local $Test::Builder::Level = $Test::Builder::Level + 1;
	my ($primary, $bgpid) = @_;

	# The background session's backend should report wait_event = 'SyncRep'.
	ok($primary->poll_query_until(
		'postgres',
		qq[SELECT (wait_event = 'SyncRep') FROM pg_stat_activity
		  WHERE pid = $bgpid],
		't'),
		'INSERT is blocked waiting on SyncRep');
	return;
}

# Initialize primary node
my $node_primary = PostgreSQL::Test::Cluster->new('primary');
$node_primary->init(allows_streaming => 1);
$node_primary->start;
my $backup_name = 'primary_backup';

# Take backup
$node_primary->backup($backup_name);

# Create three standbys linking to primary
my $node_standby_1 = PostgreSQL::Test::Cluster->new('standby1');
$node_standby_1->init_from_backup($node_primary, $backup_name,
	has_streaming => 1);
start_standby_and_wait($node_primary, $node_standby_1);

my $node_standby_2 = PostgreSQL::Test::Cluster->new('standby2');
$node_standby_2->init_from_backup($node_primary, $backup_name,
	has_streaming => 1);
start_standby_and_wait($node_primary, $node_standby_2);

my $node_standby_3 = PostgreSQL::Test::Cluster->new('standby3');
$node_standby_3->init_from_backup($node_primary, $backup_name,
	has_streaming => 1);
start_standby_and_wait($node_primary, $node_standby_3);

# ---------------------------------------------------------------
# Scenario 1: EVERY(standby1), ANY 2(standby1, standby2, standby3)
# standby1 is forced (priority -1, sync-quorum).  The ANY quorum needs
# 2 acks: standby1 (forced) plus at least one of standby2/standby3.
# This exercises the actual interaction between forced and quorum
# standbys, unlike ANY 1 where the forced standby alone would suffice.
# ---------------------------------------------------------------
test_sync_state(
	$node_primary, qq(standby1|-1|sync-quorum
standby2|1|sync-quorum
standby3|1|sync-quorum),
	'EVERY standby1 plus ANY 2 quorum',
	'EVERY(standby1), ANY 2(standby1, standby2, standby3)');

# Create a table for subsequent INSERT tests (all standbys are up here).
$node_primary->safe_psql('postgres',
	"CREATE TABLE tab_every AS SELECT generate_series(1, 10) AS a;");

# ---------------------------------------------------------------
# Scenario 2a: forced standby down -> commit must block.
# Stop standby1 (the forced one).  A commit on the primary must block
# because the forced standby is unavailable, even though other quorum
# standbys are up and could satisfy ANY 2 on their own (need 2 acks,
# but forced is mandatory).
# ---------------------------------------------------------------
$node_standby_1->stop;

# Start a background session and issue an INSERT that should block.
my $psql_timeout_secs = $PostgreSQL::Test::Utils::timeout_default;
my $bgpsql = $node_primary->background_psql('postgres',
	on_error_stop => 0,
	timeout => $psql_timeout_secs);
$bgpsql->set_query_timer_restart;
my $bgpid = $bgpsql->query('SELECT pg_backend_pid()');

# Send the INSERT; it should hang waiting for the forced standby.
$bgpsql->query_until(qr//,
	"INSERT INTO tab_every VALUES (generate_series(11, 20));SELECT 'done';\n");

# Wait until the primary notices standby1 is gone.
ok($node_primary->poll_query_until(
	'postgres',
	"SELECT count(*) = 0 FROM pg_stat_replication WHERE application_name = 'standby1'"),
	'forced standby1 disconnected from primary');

# Confirm the INSERT is actually blocked on SyncRep before restarting.
wait_blocked_on_syncrep($node_primary, $bgpid);

# ---------------------------------------------------------------
# Scenario 2b: forced standby up but quorum insufficient -> still blocks.
# Stop both standby2 and standby3 first, so that there is no window in
# which the quorum could be satisfied, then restart standby1 (forced).
# With ANY 2, we need standby1 plus at least one of standby2/standby3,
# so the INSERT should remain blocked.
# ---------------------------------------------------------------
$node_standby_2->stop;
$node_standby_3->stop;

# Wait until the primary notices both quorum standbys are gone.
ok($node_primary->poll_query_until(
	'postgres',
	"SELECT count(*) = 0 FROM pg_stat_replication WHERE application_name IN ('standby2','standby3')"),
	'quorum standbys 2 and 3 disconnected from primary');

# Now restart the forced standby.  The quorum is still unsatisfied
# (only standby1 is up, but ANY 2 needs one more), so the INSERT must
# remain blocked.
start_standby_and_wait($node_primary, $node_standby_1);

# The INSERT should still be blocked because the ANY 2 quorum is
# unsatisfied (only standby1 is up).
wait_blocked_on_syncrep($node_primary, $bgpid);

# ---------------------------------------------------------------
# Scenario 2c: forced standby up plus one quorum standby -> completes.
# Restart either standby2 or standby3.  With standby1 (forced) plus
# one quorum standby, the ANY 2 requirement is met and the blocked
# INSERT should now complete.
# ---------------------------------------------------------------
start_standby_and_wait($node_primary, $node_standby_2);

# Pump to collect the INSERT output now that the quorum is satisfied.
ok(pump_until($bgpsql->{run}, $bgpsql->{timeout}, \$bgpsql->{stdout}, qr/done/),
	'blocked INSERT completed once forced + quorum standby are up');
$bgpsql->{stdout} = '';
$bgpsql->quit;

# Confirm the rows were inserted.
is($node_primary->safe_psql('postgres',
	"SELECT count(*) FROM tab_every;"),
	'20',
	'rows inserted once forced + quorum standby rejoined');

# Restart standby3 for the remaining scenarios.
start_standby_and_wait($node_primary, $node_standby_3);

# ---------------------------------------------------------------
# Scenario 5: invalid configurations are rejected by the GUC check,
# and existing configurations (without EVERY) are not broken.
#   - A forced standby not listed in ANY must be rejected.
#   - ANY without EVERY must still be accepted (regression guard).
# ---------------------------------------------------------------

# A forced standby not present in the ANY list must be rejected.
my $err_out;
my $rc = $node_primary->psql('postgres',
	"ALTER SYSTEM SET synchronous_standby_names = 'EVERY(standby1), ANY 2(standby2, standby3)';",
	on_error_stop => 0,
	stderr => \$err_out);
like($err_out, qr/ERROR:  forced standby standby1 should be listed in sync standbys/,
	'forced standby not in ANY list rejected by GUC check');

# Wildcard * in EVERY must be rejected.
$rc = $node_primary->psql('postgres',
	"ALTER SYSTEM SET synchronous_standby_names = 'EVERY(*), ANY 1(standby1, standby2, standby3)';",
	on_error_stop => 0,
	stderr => \$err_out);
like($err_out, qr/ERROR:  wildcard "\*" is not allowed in EVERY standby list/,
	'wildcard in EVERY rejected by GUC check');

# ANY without EVERY must still be accepted (regression guard).
test_sync_state(
	$node_primary, qq(standby1|1|quorum
standby2|1|quorum
standby3|1|quorum),
	'ANY quorum without EVERY still works (regression)',
	'ANY 1(standby1, standby2, standby3)');

# ---------------------------------------------------------------
# Scenario 6: existing (non-EVERY) configurations are not broken.
# Plain priority, FIRST and ANY syntaxes must continue to work and
# report the same sync_state as before the EVERY feature was added.
# ---------------------------------------------------------------
test_sync_state(
	$node_primary, qq(standby1|1|sync
standby2|2|potential
standby3|0|async),
	'priority-based old syntax still works',
	'standby1,standby2');

test_sync_state(
	$node_primary, qq(standby1|1|sync
standby2|2|sync
standby3|3|potential),
	'FIRST syntax still works',
	'FIRST 2(standby1, standby2, standby3)');

test_sync_state(
	$node_primary, qq(standby1|1|quorum
standby2|1|quorum
standby3|1|quorum),
	'ANY syntax still works',
	'ANY 2(standby1, standby2, standby3)');

done_testing();
