
# Copyright (c) 2026-2026, PostgreSQL Global Development Group

# Test that crash recovery does not recover a prepared transaction twice
# when a checkpoint had already flushed its two-phase state file to disk
# before the crash.  This reproduces the bug fixed by commit 442749100d3:
# without the fix, restoreTwoPhaseData() at the beginning of recovery loads
# the on-disk 2PC state file, and replaying the PREPARE WAL record then adds
# the same transaction a second time, leading to a FATAL "lock ExclusiveLock
# on object ... is already held" in the startup process.
#
# The race requires the 2PC state file to be on disk while the last completed
# checkpoint's redo pointer is before the PREPARE record.  CheckPointTwoPhase
# (which flushes 2PC state files) runs near the end of a checkpoint, after the
# create-checkpoint-run injection point, so pausing the checkpoint mid-flight
# cannot by itself put the 2PC file on disk.  Instead, a completed checkpoint
# is allowed to flush the 2PC state file, and the control file is then
# regressed to an earlier checkpoint (taken before the PREPARE) so that crash
# recovery starts before the PREPARE record and replays it.  The prepared
# transaction is held open across that earlier checkpoint so that its XID is
# older than the checkpoint's nextXid, otherwise restoreTwoPhaseData() would
# discard the on-disk 2PC file as "too new".

use strict;
use warnings FATAL => 'all';
use File::Copy qw(copy);
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

if ($ENV{enable_injection_points} ne 'yes')
{
	plan skip_all => 'Injection points not supported by this build';
}

my $node = PostgreSQL::Test::Cluster->new('twophase_crash');
$node->init;
$node->append_conf('postgresql.conf',
	"shared_preload_libraries = 'injection_points'");
$node->append_conf('postgresql.conf', 'max_prepared_transactions = 10');
$node->append_conf('postgresql.conf', 'log_checkpoints = on');
$node->start;

# Check if the extension injection_points is available, as it may be
# possible that this script is run with installcheck, where the module
# would not be installed by default.
if (!$node->check_extension('injection_points'))
{
	plan skip_all => 'Extension injection_points not installed';
}
$node->safe_psql('postgres', q(CREATE EXTENSION injection_points));

$node->safe_psql('postgres',
	q{CREATE TABLE t056_tbl(id int, msg text);});

# Hold a transaction open across the checkpoint below so that its XID is
# older than the checkpoint's nextXid while its PREPARE record will be newer
# than the checkpoint's redo pointer.
my $prepare = $node->background_psql('postgres', on_error_die => 1);
$prepare->query_until(
	qr/after_insert/,
	q(\echo after_insert
BEGIN;
INSERT INTO t056_tbl VALUES(1, 'prepared before crash');
));

# C0: a completed checkpoint whose redo pointer is before the upcoming
# PREPARE record and whose nextXid is past the transaction's XID.
$node->safe_psql('postgres', 'CHECKPOINT');

# Snapshot the control file as of C0.  It is restored later so that crash
# recovery starts from C0 (redo before the PREPARE) while the 2PC state file
# flushed by the next checkpoint remains on disk.
my $ctrl_backup = $node->data_dir . "/pg_control.c0";
copy($node->data_dir . '/global/pg_control', $ctrl_backup)
  or BAIL_OUT("could not copy pg_control: $!");

# Now prepare the transaction.  Its PREPARE WAL record lands after C0's redo.
$prepare->query_until(
	qr/after_prepare/,
	q(\echo after_prepare
PREPARE TRANSACTION 't056_xact';
));
ok($prepare->quit, "close prepare session");

# Attach the two checkpoint injection points based on waits.  The first
# ("create-checkpoint-initial") is run outside the critical section and
# initializes the shared memory required for the wait machinery with its DSM
# registry.  The second ("create-checkpoint-run") is loaded outside the
# critical section and its callback is run inside it; pausing there confirms
# the checkpoint is in flight before letting it complete and flush the 2PC
# state file via CheckPointTwoPhase.
$node->safe_psql('postgres',
	q{select injection_points_attach('create-checkpoint-initial', 'wait')});
$node->safe_psql('postgres',
	q{select injection_points_attach('create-checkpoint-run', 'wait')});

# Start a checkpoint (C1) in the background and pause it inside its critical
# section.
my $checkpoint = $node->background_psql('postgres');
$checkpoint->query_until(
	qr/starting_checkpoint/,
	q(\echo starting_checkpoint
checkpoint;
));

$node->wait_for_event('checkpointer', 'create-checkpoint-initial');
$node->safe_psql('postgres',
	q{select injection_points_wakeup('create-checkpoint-initial')});

# Wait until the checkpoint has reached the second injection point: it is
# now paused inside the critical section, before CheckPointTwoPhase has
# flushed the 2PC state file.
$node->wait_for_event('checkpointer', 'create-checkpoint-run');

# Let C1 complete.  CheckPointTwoPhase flushes the 2PC state file to
# pg_twophase/, then the checkpoint WAL record is written and the control
# file is updated.
my $log_offset = -s $node->logfile;
$node->safe_psql('postgres',
	q{select injection_points_wakeup('create-checkpoint-run')});
$node->wait_for_log(qr/checkpoint complete/, $log_offset);
$checkpoint->quit;

# Crash the server without writing a checkpoint (immediate stop), then
# regress the control file to C0 so that crash recovery starts before the
# PREPARE record while the 2PC state file remains on disk.
$node->stop('immediate');
copy($ctrl_backup, $node->data_dir . '/global/pg_control')
  or BAIL_OUT("could not restore pg_control: $!");

$log_offset = -s $node->logfile;
$node->start;

# Wait for crash recovery to finish and the node to accept connections.
$node->poll_query_until('postgres', "SELECT pg_is_in_recovery() = 'f'")
  or die "timed out while waiting for recovery to finish";

# With the fix, the duplicate 2PC state coming from the PREPARE WAL record is
# skipped with a WARNING, and recovery succeeds.
$node->wait_for_log(
	qr/WARNING:.*could not recover two-phase state file for transaction/,
	$log_offset);

my $log = slurp_file($node->logfile, $log_offset);
unlike(
	$log,
	qr/lock ExclusiveLock on object .* is already held/,
	'no duplicate recovery of prepared transaction');

# The prepared transaction is restored exactly once from disk and can be
# committed, proving the 2PC state was not lost nor duplicated.
is($node->safe_psql('postgres', "SELECT count(*) FROM pg_prepared_xacts"),
	'1', 'one prepared transaction restored from disk');
$node->safe_psql('postgres', "COMMIT PREPARED 't056_xact'");
is(
	$node->safe_psql('postgres',
		"SELECT count(*) FROM t056_tbl WHERE msg = 'prepared before crash'"),
	'1',
	'committed prepared transaction data is visible');

done_testing();
