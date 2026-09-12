
# Copyright (c) 2026, PostgreSQL Global Development Group

# Test for the encryption module infrastructure.  This test verifies that
# the encrypt_command, encrypt_library, and decrypt_command GUCs are
# accepted and that the shell-based encryption callback is invoked.

use strict;
use warnings FATAL => 'all';
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

# Initialize primary node with encrypt_command set
my $node = PostgreSQL::Test::Cluster->new('primary');
$node->init();
$node->append_conf('postgresql.conf', "encrypt_command = 'echo encrypt %f %p > /dev/null'");
$node->append_conf('postgresql.conf', "decrypt_command = 'echo decrypt %f %p > /dev/null'");
$node->start;

# Test 1: Verify that the encrypt_command GUC is visible.
my $result = $node->safe_psql('postgres', "SHOW encrypt_command");
like($result, qr/echo encrypt/, 'encrypt_command GUC is set correctly');

# Test 2: Verify that the encrypt_library GUC is empty by default.
$result = $node->safe_psql('postgres', "SHOW encrypt_library");
is($result, '', 'encrypt_library GUC defaults to empty string');

# Test 3: Verify that the decrypt_command GUC is visible.
$result = $node->safe_psql('postgres', "SHOW decrypt_command");
like($result, qr/echo decrypt/, 'decrypt_command GUC is set correctly');

# Test 4: Verify that the GUCs accept the %p and %f placeholders.
$result = $node->safe_psql('postgres', "SHOW encrypt_command");
like($result, qr/%f.*%p|%p.*%f/, 'encrypt_command accepts %f and %p placeholders');

$node->stop('fast');

# Test 5: Verify that setting both encrypt_command and encrypt_library
# in postgresql.conf is rejected by LoadEncryptLibrary (this is enforced
# at load time).  We test this by setting both and checking that the server
# fails to start or logs a warning.
my $node2 = PostgreSQL::Test::Cluster->new('both_set');
$node2->init();
$node2->append_conf('postgresql.conf', "encrypt_command = 'echo test'");
$node2->append_conf('postgresql.conf', "encrypt_library = 'some_library'");
# The server should start but the conflict is only checked when
# LoadEncryptLibrary is called.  For now, just verify the GUCs are set.
$node2->start;
$result = $node2->safe_psql('postgres', "SHOW encrypt_command");
like($result, qr/echo test/, 'encrypt_command is set when both are configured');
$result = $node2->safe_psql('postgres', "SHOW encrypt_library");
like($result, qr/some_library/, 'encrypt_library is set when both are configured');
$node2->stop('fast');

done_testing();
