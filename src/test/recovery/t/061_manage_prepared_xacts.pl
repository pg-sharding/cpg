# Copyright (c) 2026, PostgreSQL Global Development Group

# A dedicated transaction manager can resolve another user's prepared
# transactions after recovery, but must connect to the preparing database.
use strict;
use warnings FATAL => 'all';

use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

my $node = PostgreSQL::Test::Cluster->new('node');
$node->init;
$node->append_conf('postgresql.conf', 'max_prepared_transactions = 2');
$node->start;
$node->safe_psql(
	'postgres', qq(
	CREATE ROLE prepare_owner LOGIN;
	CREATE ROLE prepare_manager LOGIN IN ROLE pg_manage_prepared_xacts;
	CREATE TABLE prepared_data (a int);
	GRANT INSERT ON prepared_data TO prepare_owner;
	CREATE DATABASE otherdb;
));

for my $mode ('restart', 'crash recovery')
{
	$node->safe_psql(
		'postgres', qq(
		BEGIN;
		INSERT INTO prepared_data VALUES (1);
		PREPARE TRANSACTION 'manage_commit';
		BEGIN;
		INSERT INTO prepared_data VALUES (2);
		PREPARE TRANSACTION 'manage_rollback';
	),
		extra_params => [ '-U', 'prepare_owner' ]);

	if ($mode eq 'restart')
	{
		# Recover the transactions from the two-phase state files.
		$node->safe_psql('postgres', 'CHECKPOINT');
		$node->restart;
	}
	else
	{
		# Recover the transactions from WAL without a preceding checkpoint.
		$node->stop('immediate');
		$node->start;
	}

	for my $command ('COMMIT', 'ROLLBACK')
	{
		my $gid = 'manage_' . lc($command);
		my ($ret, $stdout, $stderr) = $node->psql(
			'otherdb', "$command PREPARED '$gid'",
			extra_params => [ '-U', 'prepare_manager' ]);
		is($ret, 3, "$mode: manager cannot $command in another database");
		like(
			$stderr,
			qr/prepared transaction belongs to another database/,
			"$mode: $command reports the database restriction");

		($ret, $stdout, $stderr) = $node->psql(
			'postgres', "$command PREPARED '$gid'",
			extra_params => [ '-U', 'prepare_manager' ]);
		is($ret, 0, "$mode: manager can $command another user's transaction");
	}

	is($node->safe_psql('postgres', 'SELECT count(*) FROM pg_prepared_xacts'),
		'0', "$mode: both transactions resolved");
}

is($node->safe_psql('postgres', 'SELECT a FROM prepared_data ORDER BY a'),
	"1\n1", 'only committed transactions are visible');
$node->stop;
done_testing();
