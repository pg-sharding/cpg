# Copyright (c) 2026, MDB
#
# Test the actual walsender replication permission matrix of the
# MDB_15_19_prestable line (MDB-48544).
#
# The gate in postinit.c allows a walsender session for superusers, roles
# with the REPLICATION attribute, and members of the "mdb_replication"
# role.  On top of that, check_permissions() in walsender.c denies
# streaming replication (both slotless and with a physical slot),
# BASE_BACKUP and physical CREATE_REPLICATION_SLOT to everyone but
# superusers and REPLICATION roles -- so a pure mdb_replication member can
# connect, but can do nothing but logical CREATE_REPLICATION_SLOT, which
# goes through check_mdb_replication() instead.
#
# This test documents the actual behavior; it is a regression test for the
# permission matrix, not a specification of a desired one.

use strict;
use warnings;
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

# Set up node with wal_level = logical so that both physical and logical
# commands can be exercised in one pass.
my $node = PostgreSQL::Test::Cluster->new('main');
$node->init(allows_streaming => 1);
$node->append_conf('postgresql.conf', 'wal_level = logical');
$node->start;

# Roles:
#  r_repl - REPLICATION attribute
#  r_mdb  - plain role granted membership in "mdb_replication"
#  r_plain- plain role, nothing special
#  r_su   - superuser without the REPLICATION attribute
$node->safe_psql('postgres', "CREATE ROLE r_repl REPLICATION LOGIN;");
$node->safe_psql('postgres', "CREATE ROLE r_plain LOGIN;");
$node->safe_psql('postgres', "CREATE ROLE r_su SUPERUSER LOGIN;");
$node->safe_psql('postgres', "CREATE ROLE mdb_replication NOLOGIN;");
$node->safe_psql('postgres', "CREATE ROLE r_mdb LOGIN;");
$node->safe_psql('postgres', "GRANT mdb_replication TO r_mdb;");

$node->safe_psql('postgres',
	"SELECT pg_create_physical_replication_slot('s1');");

# Streaming start position: the current flush position.  Starting from
# 0/0 would fail server-side on this line ("requested WAL segment ...
# has already been removed"), before the copy stream even begins.
my $start_lsn = $node->safe_psql('postgres', 'SELECT pg_current_wal_lsn()');

# Run one low-level walsender command as the given role.  By default this
# uses a db-less physical replication connection (replication=true, no
# dbname); pass 'database' as the third argument to use a logical
# (replication=database) connection instead.  Returns ($ret, $stdout,
# $stderr, $timed_out): $ret is the psql exit code, $timed_out tells
# whether the command ran until the timeout.
#
# Note that psql is not a real replication client: once the server accepts
# a command that opens a copy stream (START_REPLICATION, BASE_BACKUP), how
# psql copes with the stream is its own business, and its exit code is not
# a reliable signal.  What is reliable is the server response: a command
# refused by check_permissions() comes back with a distinct ERROR, which
# is what the assertions below look at.
sub walsender_command
{
	my ($role, $cmd, $mode, $timeout) = @_;
	$mode   ||= 'physical';
	$timeout ||= 30;

	my $connstr = $node->connstr . " user=$role";
	# Logical connections need a database.
	$connstr .= " dbname=postgres" if $mode eq 'database';

	my ($stdout, $stderr, $timed_out);
	my $ret = $node->psql(
		'postgres', $cmd,
		connstr => $connstr,
		replication => ($mode eq 'database' ? 'database' : 'true'),
		stdout => \$stdout,
		stderr => \$stderr,
		timed_out => \$timed_out,
		timeout => $timeout);

	return ($ret, $stdout, $stderr, $timed_out);
}

# A command that must fail with the given error.
sub expect_error
{
	my ($role, $cmd, $error_re, $name, $mode) = @_;
	my ($ret, $stdout, $stderr, $timed_out)
		= walsender_command($role, $cmd, $mode);

	isnt($ret, 0, "$name: nonzero psql exit code");
	is($timed_out, 0, "$name: did not time out");
	like($stderr, $error_re, "$name: expected error");
}

# A command that must be accepted by the server (IDENTIFY_SYSTEM,
# CREATE_REPLICATION_SLOT): it completes and psql exits cleanly.
sub expect_ok
{
	my ($role, $cmd, $name, $mode) = @_;
	my ($ret, $stdout, $stderr, $timed_out)
		= walsender_command($role, $cmd, $mode);

	is($ret, 0, "$name: psql exit code 0");
	is($timed_out, 0, "$name: did not time out");
	unlike($stderr, qr/FATAL|ERROR/, "$name: no error in stderr");
	unlike($stderr, qr/must be superuser or replication role/,
		"$name: no permission error");
}

# A START_REPLICATION command that the server must accept: the command
# succeeds and the server switches to copy-both mode, which plain psql
# cannot cope with.  psql's "unexpected PQresultStatus: 8" diagnostic (the
# CopyBoth response) is the reliable marker that the command was accepted
# and streaming actually started -- the psql exit code is not.
sub expect_streaming_ok
{
	my ($role, $cmd, $name, $mode) = @_;
	my ($ret, $stdout, $stderr, $timed_out)
		= walsender_command($role, $cmd, $mode);

	is($timed_out, 0, "$name: psql did not hang");
	like($stderr, qr/unexpected PQresultStatus: 8/,
		"$name: psql entered copy-both mode (streaming started)");
	unlike($stderr, qr/FATAL:|ERROR:/, "$name: no server-side error");
	unlike($stderr, qr/must be superuser or replication role/,
		"$name: no permission error");
}

# BASE_BACKUP that the server must accept: exercise it with a real backup
# client run as the tested role and require a successful completion.
sub expect_basebackup_ok
{
	my ($role, $name) = @_;
	my $backup_path = $node->backup_dir . "/backup_$role";

	my $ret = system('pg_basebackup', '-D', $backup_path,
		'-d', $node->connstr('postgres') . " user=$role",
		'--checkpoint', 'fast', '--no-sync');
	is($ret, 0, "$name: pg_basebackup exit code 0");
}

my $perm_err = qr/must be superuser or replication role to use replication slots/;

# --- r_plain: not even allowed to start a walsender session.
{
	my ($ret, $stdout, $stderr, $timed_out)
		= walsender_command('r_plain', 'IDENTIFY_SYSTEM');

	isnt($ret, 0, 'r_plain: walsender session refused');
	like($stderr,
		qr/must be superuser, replication role or mdb_replication to start walsender/,
		'r_plain: refusal message');
}

# --- r_repl (REPLICATION attribute): everything allowed.
{
	expect_ok('r_repl', 'IDENTIFY_SYSTEM', 'r_repl: IDENTIFY_SYSTEM');
	expect_streaming_ok('r_repl', "START_REPLICATION $start_lsn",
		'r_repl: slotless START_REPLICATION');
	expect_streaming_ok('r_repl', "START_REPLICATION SLOT \"s1\" $start_lsn",
		'r_repl: START_REPLICATION with physical slot');
	expect_ok('r_repl', 'CREATE_REPLICATION_SLOT r_repl_ps TEMPORARY PHYSICAL',
		'r_repl: physical CREATE_REPLICATION_SLOT');
	expect_basebackup_ok('r_repl', 'r_repl: BASE_BACKUP');
	# Logical slot creation requires a database (replication=database)
	# connection, both for the catalog access of logical decoding and
	# because a db-less walsender has no MyDatabaseId.
	expect_ok('r_repl',
		'CREATE_REPLICATION_SLOT r_repl_ls TEMPORARY LOGICAL "test_decoding"',
		'r_repl: logical CREATE_REPLICATION_SLOT', 'database');
}

# --- r_mdb (member of mdb_replication): allowed through the connection
# gate, but denied everything except logical slot creation.
{
	expect_ok('r_mdb', 'IDENTIFY_SYSTEM', 'r_mdb: IDENTIFY_SYSTEM');
	expect_error('r_mdb', "START_REPLICATION $start_lsn", $perm_err,
		'r_mdb: slotless START_REPLICATION denied');
	expect_error('r_mdb', "START_REPLICATION SLOT \"s1\" $start_lsn", $perm_err,
		'r_mdb: START_REPLICATION with physical slot denied');
	expect_error('r_mdb', 'BASE_BACKUP', $perm_err,
		'r_mdb: BASE_BACKUP denied');
	expect_error('r_mdb', 'CREATE_REPLICATION_SLOT r_mdb_ps TEMPORARY PHYSICAL',
		$perm_err, 'r_mdb: physical CREATE_REPLICATION_SLOT denied');
	expect_ok('r_mdb',
		'CREATE_REPLICATION_SLOT r_mdb_ls TEMPORARY LOGICAL "test_decoding"',
		'r_mdb: logical CREATE_REPLICATION_SLOT allowed', 'database');
}

# --- r_su (superuser without REPLICATION): the superuser allowance covers
# the whole command path on this line.
{
	expect_ok('r_su', 'IDENTIFY_SYSTEM', 'r_su: IDENTIFY_SYSTEM');
	expect_streaming_ok('r_su', "START_REPLICATION $start_lsn",
		'r_su: slotless START_REPLICATION');
	expect_streaming_ok('r_su', "START_REPLICATION SLOT \"s1\" $start_lsn",
		'r_su: START_REPLICATION with physical slot');
}

# The server must have survived all of the above.
ok($node->safe_psql('postgres', 'SELECT 1') eq '1',
	'server still alive after permission probes');

$node->stop('fast');
done_testing();
