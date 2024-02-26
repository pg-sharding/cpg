# Copyright (c) 2024-2024, PostgreSQL Global Development Group

# Minimal test testing pg_signal_autovacuum role.
use strict;
use warnings;
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

# Initialize primary node
my $node_primary = PostgreSQL::Test::Cluster->new('primary');
$node_primary->init();
$node_primary->start;

$node_primary->safe_psql('postgres',
	"
    CREATE DATABASE regress;
    CREATE ROLE psa_reg_role_1;
    CREATE ROLE psa_reg_role_2;
    GRANT pg_signal_backend TO psa_reg_role_1;
    GRANT pg_signal_autovacuum TO psa_reg_role_2;
");

# Create some content on primary and set autovacuum setting such that
# it would be triggered.
$node_primary->safe_psql('regress',
	"
    CREATE TABLE tab_int(i int);
    INSERT INTO tab_int SELECT * FROM generate_series(1, 1000000);
    ALTER SYSTEM SET autovacuum_vacuum_cost_limit TO 1;
    ALTER SYSTEM SET autovacuum_vacuum_cost_delay TO 100;
    ALTER SYSTEM SET autovacuum_naptime TO 1;    
");

$node_primary->restart;

#wait for autovac to start.

sleep 1;

my $res_pid = $node_primary->safe_psql('regress',
	"
    SELECT pid FROM pg_stat_activity WHERE backend_type = 'autovacuum worker' and datname = 'regress';;
");


my ($res_reg_psa_1, $stdout_reg_psa_1, $stderr_reg_psa_1)  = $node_primary->psql('regress',
	"
    SET ROLE psa_reg_role_1;
    SELECT pg_terminate_backend($res_pid);
");

ok($res_reg_psa_1 != 0, "should fail for non pg_signal_autovacuum");
like($stderr_reg_psa_1, qr/Only roles with the SUPERUSER attribute may terminate processes of roles with the SUPERUSER attribute./, "matches");

my ($res_reg_psa_2, $stdout_reg_psa_2, $stderr_reg_psa_2) = $node_primary->psql('regress', "
    SET ROLE psa_reg_role_2;
    SELECT pg_terminate_backend($res_pid);
");

ok($res_reg_psa_2 == 0, "should success for pg_signal_autovacuum");

done_testing();
