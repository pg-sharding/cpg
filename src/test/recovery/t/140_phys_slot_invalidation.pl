# Copyright (c) 2026, PostgreSQL Global Development Group

# Test for physical replication slot invalidation and for the walsender
# restoring missing WAL segments from the archive.
use strict;
use warnings FATAL => 'all';

use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;
use Time::HiRes qw(usleep);

##################################################
# Part A: WAL removal invalidates an inactive physical replication slot and
# the standby using it can no longer stream.
##################################################

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

##################################################
# Part B: with ycmdb.restore_missing_wal_phys_slots enabled, the walsender
# restores a missing WAL segment from the archive, as long as the slot has
# not been invalidated.
##################################################

# Initialize a new primary with archiving enabled and a restore_command that
# retrieves segments from the same archive.
my $node_arch_primary = PostgreSQL::Test::Cluster->new('arch_primary');
$node_arch_primary->init(
	allows_streaming => 1,
	has_archiving    => 1,
	extra            => ['--wal-segsize=1']);

my $archive_path = $node_arch_primary->archive_dir;
my $restore_cmd  =
  $PostgreSQL::Test::Utils::windows_os
  ? qq{copy "$archive_path\\\\%f" "%p"}
  : qq{cp "$archive_path/%f" "%p"};
$node_arch_primary->append_conf('postgresql.conf', qq{
wal_keep_size = 0
min_wal_size = 2MB
max_wal_size = 4MB
restore_command = '$restore_cmd'
});
$node_arch_primary->start;

# Create a physical replication slot and a standby that uses it
$node_arch_primary->safe_psql('postgres',
	"SELECT pg_create_physical_replication_slot('arch_slot');");

my $backup_name2 = 'backup2';
$node_arch_primary->backup($backup_name2);

my $node_arch_standby = PostgreSQL::Test::Cluster->new('arch_standby');
$node_arch_standby->init_from_backup($node_arch_primary, $backup_name2,
	has_streaming => 1);
$node_arch_standby->append_conf('postgresql.conf',
	"primary_slot_name = 'arch_slot'\nwal_retrieve_retry_interval = 500ms");
$node_arch_standby->start;

$node_arch_primary->wait_for_catchup($node_arch_standby);

# Stop the standby and figure out which WAL segment the slot points to.
$node_arch_standby->stop;

my $restart_lsn = $node_arch_primary->safe_psql('postgres',
	"SELECT restart_lsn FROM pg_replication_slots WHERE slot_name = 'arch_slot'");
chomp $restart_lsn;
my $needed_fname = $node_arch_primary->safe_psql('postgres',
	"SELECT pg_walfile_name('$restart_lsn'::pg_lsn)");
chomp $needed_fname;

# Advance WAL so that the needed segment is switched away and archived.
for my $i (1 .. 5)
{
	$node_arch_primary->safe_psql('postgres', "SELECT txid_current();");
	$node_arch_primary->safe_psql('postgres', "SELECT pg_switch_wal();");
}

my $arch_pg_wal = $node_arch_primary->data_dir . '/pg_wal';

# Wait until the needed segment has been archived
my $needed_archived = 0;
for (my $i = 0; $i < 10 * $PostgreSQL::Test::Utils::timeout_default; $i++)
{
	if (-f "$archive_path/$needed_fname")
	{
		$needed_archived = 1;
		last;
	}
	usleep(100_000);
}
ok($needed_archived, "the needed WAL segment $needed_fname has been archived");

# The segment should still be present in pg_wal since the slot retains it.
ok( -f "$arch_pg_wal/$needed_fname",
	"the needed WAL segment is still present in pg_wal");

# Remove the segment from pg_wal, leaving only its archived copy.  The slot
# has not been invalidated, since no checkpoint has removed the segment.
unlink "$arch_pg_wal/$needed_fname"
  or die "could not remove WAL segment $needed_fname from pg_wal";

# With the GUC disabled (default), the standby cannot stream since the WAL
# segment is missing from pg_wal.
my $arch_standby_log_offset = -s $node_arch_standby->logfile;
$node_arch_standby->start;

my $arch_stream_failed = 0;
for (my $i = 0; $i < 10 * $PostgreSQL::Test::Utils::timeout_default; $i++)
{
	if (
		$node_arch_standby->log_contains(
			qr/requested WAL segment $needed_fname has already been removed/,
			$arch_standby_log_offset))
	{
		$arch_stream_failed = 1;
		last;
	}
	usleep(100_000);
}
ok($arch_stream_failed,
	'primary fails to serve the missing WAL segment when the GUC is off');

$node_arch_standby->stop;

# Enable the GUC on the primary and restart the standby: the walsender should
# now restore the missing segment from the archive and resume streaming.
$node_arch_primary->safe_psql('postgres',
	"ALTER SYSTEM SET ycmdb.restore_missing_wal_phys_slots = on; SELECT pg_reload_conf();");

$node_arch_standby->start;
$node_arch_primary->wait_for_catchup($node_arch_standby);

ok( -f "$arch_pg_wal/$needed_fname",
	'the missing WAL segment has been restored from the archive');

done_testing();