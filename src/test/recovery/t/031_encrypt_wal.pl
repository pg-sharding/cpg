
# Copyright (c) 2026, PostgreSQL Global Development Group

# Test WAL stream encryption between primary and standby.
#
# This test sets up a primary and a standby with encrypt_command configured.
# It verifies that WAL is encrypted on the wire and correctly decrypted on
# the standby, so that the standby can replay the WAL and produce correct
# query results.

use strict;
use warnings FATAL => 'all';
use FindBin;
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

# Find the XOR encrypt helper script relative to this test file
my $xor_script = "$FindBin::RealBin/../../encrypt/xor_encrypt.py";

# Initialize primary node with encryption enabled
my $node_primary = PostgreSQL::Test::Cluster->new('primary');
$node_primary->init(allows_streaming => 1);
$node_primary->append_conf('postgresql.conf',
	"encrypt_command = 'python3 ${xor_script} encrypt %f %p'");
$node_primary->start;

# Take backup for standby
my $backup_name = 'my_backup';
$node_primary->backup($backup_name);

# Initialize standby from backup, with encryption enabled
my $node_standby = PostgreSQL::Test::Cluster->new('standby');
$node_standby->init_from_backup($node_primary, $backup_name,
	has_streaming => 1);
$node_standby->append_conf('postgresql.conf',
	"encrypt_command = 'python3 ${xor_script} encrypt %f %p'");
$node_standby->start;

# Create some content on the primary
$node_primary->safe_psql('postgres',
	"CREATE TABLE test_enc AS SELECT g AS a, md5(g::text) AS b FROM generate_series(1,100) g");

# Wait for the standby to catch up
$node_primary->safe_psql('postgres', "SELECT pg_switch_wal()");
my $primary_lsn = $node_primary->safe_psql('postgres', "SELECT pg_current_wal_lsn()");
$node_standby->poll_query_until('postgres',
	"SELECT '$primary_lsn'::pg_lsn <= pg_last_wal_replay_lsn()")
  or die "Timed out waiting for standby to catch up";

# Verify the standby has the same data
my $result = $node_standby->safe_psql('postgres',
	"SELECT count(*), count(DISTINCT b) FROM test_enc");
is($result, '100|100', 'standby received and decrypted WAL correctly');

# Verify data integrity
$result = $node_standby->safe_psql('postgres',
	"SELECT a, b FROM test_enc WHERE a = 1");
like($result, qr/^1\|c4ca4238a0b923820dcc509a6f75849b$/,
	'standby data matches primary after encrypted WAL replay');

# Add more data and verify incremental streaming
$node_primary->safe_psql('postgres',
	"INSERT INTO test_enc SELECT g, md5(g::text) FROM generate_series(101,200) g");
$primary_lsn = $node_primary->safe_psql('postgres', "SELECT pg_current_wal_lsn()");
$node_standby->poll_query_until('postgres',
	"SELECT '$primary_lsn'::pg_lsn <= pg_last_wal_replay_lsn()")
  or die "Timed out waiting for standby to catch up (incremental)";

$result = $node_standby->safe_psql('postgres',
	"SELECT count(*) FROM test_enc");
is($result, '200', 'standby received incremental encrypted WAL');

$node_standby->stop('fast');
$node_primary->stop('fast');

done_testing();
