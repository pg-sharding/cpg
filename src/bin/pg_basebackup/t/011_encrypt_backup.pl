
# Copyright (c) 2026, PostgreSQL Global Development Group

# Test pg_basebackup with encrypted backup data.

use strict;
use warnings FATAL => 'all';
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

# Initialize primary node with encryption enabled
my $node = PostgreSQL::Test::Cluster->new('primary');
$node->init(allows_streaming => 1);

# The shell encrypt module uses encrypt_command as XOR key.
my $encrypt_password = "mysecretkey123456";
my $hex_key = unpack("H*", $encrypt_password);

# Set encrypt_command before starting
$node->append_conf('postgresql.conf', "encrypt_command = '$encrypt_password'");
$node->start;

# Create some test data
$node->safe_psql('postgres',
	"CREATE TABLE test_tbl AS SELECT g AS a, md5(g::text) AS b FROM generate_series(1,50) g");

# Take backup with --encrypt-key
my $backup_dir = $node->backup_dir . '/enc_backup';
$node->command_ok(
	['pg_basebackup', '--no-sync', '-D', $backup_dir,
	 '-h', $node->host, '-p', $node->port,
	 '--checkpoint', 'fast',
	 '--encrypt-key', $hex_key],
	'encrypted base backup completed');

# Verify the backup contains valid data files
ok(-f "$backup_dir/PG_VERSION", 'PG_VERSION exists in decrypted backup');

# Verify we can start from the backup
my $node2 = PostgreSQL::Test::Cluster->new('standby');
$node2->init_from_backup($node, 'enc_backup', has_streaming => 1);
$node2->start;

# Verify the data is correct
my $result = $node2->safe_psql('postgres',
	"SELECT count(*), count(DISTINCT b) FROM test_tbl");
is($result, '50|50', 'decrypted backup has correct data');

# Verify a specific row
$result = $node2->safe_psql('postgres',
	"SELECT a, b FROM test_tbl WHERE a = 1");
like($result, qr/^1\|c4ca4238a0b923820dcc509a6f75849b$/,
	'specific row matches in decrypted backup');

$node2->stop('fast');
$node->stop('fast');

done_testing();
