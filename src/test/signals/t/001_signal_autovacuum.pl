# Copyright (c) 2024-2024, PostgreSQL Global Development Group

# Minimal test testing pg_signal_autovacuum role.
use strict;
use warnings;
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

# Initialize primary node
my $node = PostgreSQL::Test::Cluster->new('primary');
$node->init();

# set autovacuum setting such that it would be triggered.
$node->append_conf('postgresql.conf', 'autovacuum_vacuum_cost_limit = 1');
$node->append_conf('postgresql.conf', 'autovacuum_vacuum_cost_delay = 100');
$node->append_conf('postgresql.conf', 'autovacuum_naptime = 1');

$node->start;

$node->safe_psql('postgres',
	"
    CREATE DATABASE regress;
    CREATE ROLE psa_reg_role_1;
    CREATE ROLE psa_reg_role_2;
    GRANT pg_signal_backend TO psa_reg_role_1;
    GRANT pg_signal_autovacuum TO psa_reg_role_2;
");

# Create some content
$node->safe_psql('regress',
	"
    CREATE TABLE tab_int(i int);
    INSERT INTO tab_int SELECT * FROM generate_series(1, 1000000);
");

#wait for autovac to start.
sleep 2;

my $res_pid = $node->safe_psql('regress',
	"
    SELECT pid FROM pg_stat_activity WHERE backend_type = 'autovacuum worker' and datname = 'regress';;
");


my ($res_reg_psa_1, $stdout_reg_psa_1, $stderr_reg_psa_1)  = $node->psql('regress',
	"
    SET ROLE psa_reg_role_1;
    SELECT pg_terminate_backend($res_pid);
");

ok($res_reg_psa_1 != 0, "should fail for non pg_signal_autovacuum");
like($stderr_reg_psa_1, qr/Only roles with the SUPERUSER attribute may terminate processes of roles with the SUPERUSER attribute./, "matches");

my ($res_reg_psa_2, $stdout_reg_psa_2, $stderr_reg_psa_2) = $node->psql('regress', "
    SET ROLE psa_reg_role_2;
    SELECT pg_terminate_backend($res_pid);
");

ok($res_reg_psa_2 == 0, "should success for pg_signal_autovacuum");

done_testing();
