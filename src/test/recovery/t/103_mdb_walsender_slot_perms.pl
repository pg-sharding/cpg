# MDB-48544: physical WAL streaming (slotless or with a physical slot)
# requires the REPLICATION attribute; mdb_replication members are only
# allowed on the logical path.  Permission checks key off the
# session-cached globals set in the postinit.c transactional start block
# (role_has_rolreplication, member_of_mdb_replication); no uncached
# superuser()/syscache lookup may run in the walsender startup path.
#
# When a physical or logical START_REPLICATION command is accepted, the
# server switches to copy-both mode and plain psql reports
# "unexpected PQresultStatus: 8" on stderr and exits; that diagnostic is
# the marker used below for "replication actually started streaming".

use strict;
use warnings FATAL => 'all';

use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

my $node = PostgreSQL::Test::Cluster->new('primary');
$node->init(allows_streaming => 'physical');
$node->append_conf('postgresql.conf', "wal_level = logical\n");
$node->start;

$node->safe_psql(
	'postgres', qq[
	CREATE ROLE mdb_replication NOLOGIN;
	CREATE ROLE r_repl LOGIN REPLICATION;
	CREATE ROLE r_mdb LOGIN;
	CREATE ROLE r_plain LOGIN;
	GRANT mdb_replication TO r_mdb;
]);

$node->safe_psql(
	'postgres',
	q[SELECT pg_create_physical_replication_slot('s1', true)]);

# Run one walsender-protocol command as the given role over a physical
# (db-less) replication connection.  Returns ($ret, $stdout, $stderr).
sub repl_psql
{
	my ($role, $cmd) = @_;
	return $node->psql(
		'postgres', $cmd,
		replication  => 'true',
		extra_params => [ '-U', $role ]);
}

# Run one walsender-protocol command over a database-attached replication
# connection (required for logical decoding commands with a plugin).
# Returns ($ret, $stdout, $stderr).
sub repl_psql_db
{
	my ($role, $cmd) = @_;
	return $node->psql(
		'postgres', $cmd,
		replication  => 'database',
		extra_params => [ '-U', $role ]);
}

my ($ret, $stdout, $stderr);

# The error the permission checks in walsender.c raise for roles without
# the REPLICATION attribute (and without a superuser/mdb_replication
# allowance, depending on the code path).
my $perm_err = qr/must be superuser or replication role/;

# psql's diagnostic upon entering copy-both mode (accepted
# START_REPLICATION, i.e. replication actually started streaming).
my $stream_started = qr/unexpected PQresultStatus: 8/;

# a) plain role cannot even start a WAL sender
($ret, $stdout, $stderr) = repl_psql('r_plain', 'SHOW wal_level');
isnt($ret, 0, 'plain role refused at walsender start: nonzero exit');
like($stderr, qr/permission denied to start WAL sender/,
	'plain role refused at walsender start');

# b) REPLICATION role may stream physically, slotless and with a slot
($ret, $stdout, $stderr) =
  repl_psql('r_repl', 'START_REPLICATION 0/0 TIMELINE 1');
isnt($ret, 0, 'REPLICATION role slotless stream: psql exits on CopyBoth');
like($stderr, $stream_started,
	'REPLICATION role started slotless streaming (CopyBoth)');
unlike($stderr, qr/ERROR/, 'REPLICATION role slotless stream has no error');

($ret, $stdout, $stderr) =
  repl_psql('r_repl', 'START_REPLICATION SLOT "s1" 0/0 TIMELINE 1');
isnt($ret, 0, 'REPLICATION role slot stream: psql exits on CopyBoth');
like($stderr, $stream_started,
	'REPLICATION role started slot streaming (CopyBoth)');
unlike($stderr, qr/ERROR/, 'REPLICATION role slot stream has no error');

# c) mdb_replication member cannot stream physically, neither slotless...
($ret, $stdout, $stderr) =
  repl_psql('r_mdb', 'START_REPLICATION 0/0 TIMELINE 1');
isnt($ret, 0, 'mdb_replication member cannot stream slotless (physical)');
like($stderr, $perm_err,
	'mdb_replication member cannot stream slotless (physical)');

# ...nor with a physical slot...
($ret, $stdout, $stderr) =
  repl_psql('r_mdb', 'START_REPLICATION SLOT "s1" 0/0 TIMELINE 1');
isnt($ret, 0, 'mdb_replication member cannot stream from a physical slot');
like($stderr, $perm_err,
	'mdb_replication member cannot stream from a physical slot');

# ...nor create physical slots
($ret, $stdout, $stderr) =
  repl_psql('r_mdb', 'CREATE_REPLICATION_SLOT tmpphys PHYSICAL');
isnt($ret, 0, 'mdb_replication member cannot create physical slots');
like($stderr, $perm_err,
	'mdb_replication member cannot create physical slots');

# d) mdb_replication member may use logical slots
($ret, $stdout, $stderr) = repl_psql_db(
	'r_mdb',
	'CREATE_REPLICATION_SLOT lslot LOGICAL test_decoding');
is($ret, 0, 'mdb_replication member can create a logical slot');
like($stdout, qr/lslot/, 'logical CREATE_REPLICATION_SLOT returned the slot');

($ret, $stdout, $stderr) =
  repl_psql_db('r_mdb', 'START_REPLICATION SLOT "lslot" LOGICAL 0/0');
isnt($ret, 0, 'mdb_replication member logical stream: psql exits on CopyBoth');
like($stderr, $stream_started,
	'mdb_replication member started logical streaming (CopyBoth)');
unlike($stderr, qr/ERROR/,
	'mdb_replication member logical stream has no error');

done_testing();
