
# Copyright (c) 2021-2023, PostgreSQL Global Development Group

use strict;
use warnings;

use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

# Initialize primary node. Force UTF-8 encoding, so that we can use non-ASCII
# characters in the passwords below.
my $node = PostgreSQL::Test::Cluster->new('primary');
$node->init(extra => [ '--locale=C', '--encoding=UTF8' ]);
$node->start;


# Create test roles.
$node->safe_psql(
	'postgres',
	"
CREATE ROLE sup LOGIN SUPERUSER;
");


# Test access for a single role, useful to wrap all tests into one.
sub test_login
{
	local $Test::Builder::Level = $Test::Builder::Level + 1;

	my $node          = shift;
	my $expected_res  = shift;
	my $opts          = shift;
	my $status_string = 'failed';

	$status_string = 'success' if ($expected_res eq 0);

	my $connstr = "user=sup $opts";
	my $testname =
	  "authentication with opts $opts";


	if ($expected_res eq 0)
	{
		$node->connect_ok($connstr, $testname);
	}
	else
	{
		# No checks of the error message, only the status code.
		$node->connect_fails($connstr, $testname);
	}
}


test_login($node, 1, "_pq_.proto_ext=x");

test_login($node, 0, "_pq_.ycmdb.probe=67");
ok(1);
done_testing();

