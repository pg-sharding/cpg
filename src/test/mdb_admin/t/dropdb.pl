
# Copyright (c) 2024-2024, MDB, Mother Russia

# Minimal test testing drop database restrictions
use strict;
use warnings;
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

# Initialize primary node
my $node_primary = PostgreSQL::Test::Cluster->new('primary');
$node_primary->init();
$node_primary->start;

# Create some content on primary and check its presence in standby nodes
$node_primary->safe_psql('postgres',
	"
    CREATE ROLE mdb_admin;
    CREATE ROLE mdb_superuser;
    CREATE ROLE mdb_reg_lh_1;
    GRANT mdb_admin TO mdb_reg_lh_1;
    GRANT mdb_superuser TO mdb_reg_lh_1;
    ALTER ROLE mdb_reg_lh_1 CREATEDB;
");

# Create some content on primary
$node_primary->safe_psql('postgres',
	"
    SET ROLE mdb_reg_lh_1;
    CREATE DATABASE regress_db1;
");


my ($res_reg_lh_1, $stdout_reg_lh_1, $stderr_reg_lh_1)  = $node_primary->psql('postgres',
	"
    SET ROLE mdb_reg_lh_1;
    DROP DATABASE regress_db1;
");

# print ($res_reg_lh_1, $stdout_reg_lh_1, $stderr_reg_lh_1, "\n");

ok($res_reg_lh_1 != 0, "should fail for non-superuser");
like($stderr_reg_lh_1, qr/ERROR:  permission denied for database regress_db1/, "matches");

my ($res_reg_lh_2, $stdout_reg_lh_2, $stderr_reg_lh_2) = $node_primary->psql('postgres',
	"
    DROP DATABASE regress_db1;
");

ok($res_reg_lh_2 == 0, "should success for superuser");

# print ($res_reg_lh_2, $stdout_reg_lh_2, $stderr_reg_lh_2, "\n");

done_testing();
