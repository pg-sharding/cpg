# Test the parallel base backup protocol: START_BACKUP, SEND_FILE_LIST,
# SEND_FILE, and STOP_BACKUP replication commands.

use strict;
use warnings;
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

# Initialize primary node
my $node = PostgreSQL::Test::Cluster->new('primary');
$node->init(allows_streaming => 1);
$node->start;

# Create a test table with some data
$node->safe_psql('postgres',
	"CREATE TABLE test_parallel_backup (id int, data text);");
$node->safe_psql('postgres',
	"INSERT INTO test_parallel_backup SELECT i, repeat('x', 100) FROM generate_series(1, 1000) i;");

# Test 1: START_BACKUP returns a result set with backup_label, start_lsn, start_tli
my $result = $node->safe_psql('postgres',
	"SELECT pg_backup_start('test');");
ok($result =~ /^[0-9A-F]+\/[0-9A-F]{8}$/,
	'pg_backup_start returns an LSN');
$node->safe_psql('postgres', "SELECT pg_backup_stop();");

# Test 2: Use the replication protocol to call START_BACKUP
my $connstr = $node->connstr();
my $tempdir = PostgreSQL::Test::Utils::tempdir;

# We'll use psql with replication=database to test the protocol
my $psql_out = '';
my $psql_err = '';

# Start a replication connection and test START_BACKUP
my ($stdout, $stderr);
$result = $node->psql('postgres',
	"START_BACKUP (LABEL 'test_parallel')",
	{
		replication => 'database',
		stdout => \$stdout,
		stderr => \$stderr,
	});

# START_BACKUP should return a result set
is($result, 0, 'START_BACKUP succeeds');
like($stdout, qr/backup_label/, 'START_BACKUP returns backup_label');

# Test SEND_FILE_LIST
$stdout = '';
$stderr = '';
$result = $node->psql('postgres',
	"SEND_FILE_LIST",
	{
		replication => 'database',
		stdout => \$stdout,
		stderr => \$stderr,
	});

is($result, 0, 'SEND_FILE_LIST succeeds');
# Should contain PG_VERSION file and postgresql.conf
like($stdout, qr/PG_VERSION/, 'SEND_FILE_LIST includes PG_VERSION');
like($stdout, qr/postgresql\.conf/, 'SEND_FILE_LIST includes postgresql.conf');

# Test SEND_FILE for a small file
$stdout = '';
$stderr = '';
$result = $node->psql('postgres',
	"SEND_FILE './PG_VERSION'",
	{
		replication => 'database',
		stdout => \$stdout,
		stderr => \$stderr,
	});

is($result, 0, 'SEND_FILE succeeds for PG_VERSION');
# PG_VERSION contains the major version number
like($stdout, qr/^\d+/, 'SEND_FILE returns file contents');

# Test STOP_BACKUP
$stdout = '';
$stderr = '';
$result = $node->psql('postgres',
	"STOP_BACKUP",
	{
		replication => 'database',
		stdout => \$stdout,
		stderr => \$stderr,
	});

is($result, 0, 'STOP_BACKUP succeeds');
like($stdout, qr/backup_label/, 'STOP_BACKUP returns backup_label');

$node->stop();
done_testing();
