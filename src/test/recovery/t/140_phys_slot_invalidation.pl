# Copyright (c) 2026, PostgreSQL Global Development Group

# Test that a physical replication slot is invalidated when the WAL it needs
# has been removed, and that the standby using the slot can no longer stream.
use strict;
use warnings FATAL => 'all';

use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

# Initialize the primary node with 1MB WAL segments, so that a few WAL
# switches are enough to make the required segment old.
my $node_primary = PostgreSQL::Test::Cluster->new('primary');
$node_primary->init(
	allows_streaming => 1,
	extra           => ['--wal-segsize=1']);

# Configure the node so that the WAL required by the replication slot is only
# retained for a short time, so that the slot can be invalidated due to
# "wal_removed".
$node_primary->append_conf(
	'postgresql.conf', qq{
wal_keep_size = 0
min_wal_size = 2MB
max_wal_size = 4MB
max_slot_wal_keep_size = 64kB
});
$node_primary->start;

# Create a physical replication slot and a standby that uses it
$node_primary->safe_psql('postgres',
	"SELECT pg_create_physical_replication_slot('phys_slot');");

my $backup_name = 'backup1';
$node_primary->backup($backup_name);

my $node_standby = PostgreSQL::Test::Cluster->new('standby');
$node_standby->init_from_backup($node_primary, $backup_name,
	has_streaming => 1);
$node_standby->append_conf('postgresql.conf', "primary_slot_name = 'phys_slot'");
$node_standby->start;

$node_primary->wait_for_catchup($node_standby);

# Stop the standby, so that the physical replication slot becomes inactive
# and its restart_lsn is no longer advanced.
$node_standby->stop;

# Wait until the slot is not active anymore
$node_primary->poll_query_until('postgres', q{
	SELECT NOT active FROM pg_replication_slots WHERE slot_name = 'phys_slot';
})
  or die "physical slot is still active on the primary server";

# Advance WAL so that the segment containing the slot's restart_lsn is no
# longer retained.  Each iteration forces at least one WAL record via
# txid_current() and then switches to a new WAL segment.
my $log_offset = -s $node_primary->logfile;
for my $i (1 .. 10)
{
	$node_primary->safe_psql('postgres', "SELECT txid_current();");
	$node_primary->safe_psql('postgres', "SELECT pg_switch_wal();");
}

# Perform a checkpoint to remove the obsolete WAL segments and invalidate the
# physical replication slot.
$node_primary->safe_psql('postgres', 'CHECKPOINT');

# Check that the slot invalidation has been logged
$node_primary->wait_for_log(
	qr/invalidating obsolete replication slot "phys_slot"/, $log_offset);

# Wait for the slot to be invalidated due to "wal_removed"
$node_primary->poll_query_until('postgres', q{
	SELECT invalidation_reason = 'wal_removed'
	FROM pg_replication_slots WHERE slot_name = 'phys_slot';
})
  or die "timed out waiting for the physical slot to be invalidated";

# Restart the standby: it will try to start streaming replication using the
# invalidated slot and fail to do so.
my $standby_log_offset = -s $node_standby->logfile;
$node_standby->start;

# The standby cannot start streaming since the slot has been invalidated
my $standby_failed = 0;
for (my $i = 0; $i < 10 * $PostgreSQL::Test::Utils::timeout_default; $i++)
{
	if (
		$node_standby->log_contains(
			qr/can no longer access replication slot "phys_slot".*invalidated due to "wal_removed"/s,
			$standby_log_offset))
	{
		$standby_failed = 1;
		last;
	}
	usleep(100_000);
}
ok($standby_failed, 'check that replication has been broken');

done_testing();