
# Copyright (c) 2024-2024, MDB, Mother Russia

# Minimal test testing streaming replication
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
    CREATE DATABASE regress;
    CREATE ROLE mdb_admin;
    CREATE ROLE mdb_reg_lh_app_name;
    GRANT mdb_admin to mdb_reg_lh_app_name;
    GRANT pg_signal_backend to mdb_reg_lh_app_name;
    CREATE TABLE mdb_app_name_t(i int);
");

my $main_sess = $node_primary->background_psql('postgres');

$main_sess->query_safe(
	q(
SET application_name TO 'SU';
BEGIN;
INSERT INTO mdb_app_name_t VALUES(0);
));


my $res_pid = $node_primary->safe_psql('regress',
	"
    SELECT pid FROM pg_stat_activity WHERE application_name = 'SU';
");

print "pid is $res_pid\n";

ok(1);


my ($res_reg_lh_1, $stdout_reg_lh_1, $stderr_reg_lh_1)  = $node_primary->psql('regress',
	"
    SET ROLE mdb_reg_lh_app_name;
    SELECT pg_terminate_backend($res_pid);
");

# print ($res_reg_lh_1, $stdout_reg_lh_1, $stderr_reg_lh_1, "\n");

ok($res_reg_lh_1 != 0, "should fail for non-MDB");
like($stderr_reg_lh_1, qr/Only roles with the SUPERUSER attribute may terminate processes of roles with the SUPERUSER attribute./, "matches");

# should succeed
$main_sess->query_safe(qq[COMMIT]);

$main_sess->query_safe(
	q(
SET application_name TO 'MDB';
BEGIN;
INSERT INTO mdb_app_name_t VALUES(1);
));


my ($res_reg_lh_2, $stdout_reg_lh_2, $stderr_reg_lh_2) = $node_primary->psql('regress',
	"
    SET ROLE mdb_reg_lh_app_name;
    SELECT pg_terminate_backend($res_pid);
");

ok($res_reg_lh_2 == 0, "should success for MDB");

done_testing();
