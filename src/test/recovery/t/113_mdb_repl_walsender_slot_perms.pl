# MDB-48544: physical WAL streaming (slotless or with a physical slot)
# requires the REPLICATION attribute; mdb_replication members are only
# allowed on the logical path.  Permission checks key off the
# session-cached globals set in the postinit.c transactional start block
# (role_has_rolreplication, member_of_mdb_replication); no uncached
# superuser()/syscache lookup may run in the walsender startup path.
#
# A START_REPLICATION that is accepted makes the server switch to
# copy-both mode; plain psql then reports "unexpected PQresultStatus: 8"
# on stderr and exits.  That diagnostic is the marker used below to tell
# "streaming actually started" apart from the permission errors, so no
# timeouts are needed: psql never hangs.
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

# The error check_permissions() raises for anything without the
# REPLICATION attribute.
my $perm_err = qr/must be superuser or replication role to use replication slots/;

# psql's diagnostic upon entering copy-both mode (accepted
# START_REPLICATION, i.e. streaming actually started).
my $stream_started = qr/unexpected PQresultStatus: 8/;

my ($ret, $stdout, $stderr);

# a) plain role cannot even start a WAL sender
($ret, $stdout, $stderr) = $node->psql(
	'postgres', 'SHOW wal_level',
	replication => 'true',
	extra_params => [ '-U', 'r_plain' ]);
isnt($ret, 0, 'plain role refused at walsender start');
like(
	$stderr,
	qr/permission denied to start WAL sender/,
	'plain role gets the walsender startup error');

# b) REPLICATION role may stream physically, slotless and with a slot
($ret, $stdout, $stderr) = $node->psql(
	'postgres', 'START_REPLICATION 0/0 TIMELINE 1',
	replication => 'true',
	extra_params => [ '-U', 'r_repl' ]);
like(
	$stderr,
	$stream_started,
	'REPLICATION role can stream slotless');
unlike($stderr, qr/ERROR/, '... and streaming began without error');

($ret, $stdout, $stderr) = $node->psql(
	'postgres', 'START_REPLICATION SLOT "s1" 0/0 TIMELINE 1',
	replication => 'true',
	extra_params => [ '-U', 'r_repl' ]);
like(
	$stderr,
	$stream_started,
	'REPLICATION role can stream from a slot');
unlike($stderr, qr/ERROR/, '... and streaming began without error');

# c) mdb_replication member cannot stream physically, neither slotless...
($ret, $stdout, $stderr) = $node->psql(
	'postgres', 'START_REPLICATION 0/0 TIMELINE 1',
	replication => 'true',
	extra_params => [ '-U', 'r_mdb' ]);
isnt($ret, 0, 'mdb_replication member cannot stream slotless (physical)');
like($stderr, $perm_err, '... with the rolreplication error');

# ...nor with a physical slot...
($ret, $stdout, $stderr) = $node->psql(
	'postgres', 'START_REPLICATION SLOT "s1" 0/0 TIMELINE 1',
	replication => 'true',
	extra_params => [ '-U', 'r_mdb' ]);
isnt($ret, 0, 'mdb_replication member cannot stream from a physical slot');
like($stderr, $perm_err, '... with the rolreplication error');

# ...nor create physical slots
($ret, $stdout, $stderr) = $node->psql(
	'postgres', 'CREATE_REPLICATION_SLOT tmpphys PHYSICAL',
	replication => 'true',
	extra_params => [ '-U', 'r_mdb' ]);
isnt($ret, 0, 'mdb_replication member cannot create physical slots');
like($stderr, $perm_err, '... with the rolreplication error');

# d) mdb_replication member may use logical slots, over a database
# walsender connection ('dbname=... replication=database', which logical
# decoding requires anyway).
($ret, $stdout, $stderr) = $node->psql(
	'postgres', 'CREATE_REPLICATION_SLOT lslot LOGICAL test_decoding',
	replication => 'database',
	extra_params => [ '-U', 'r_mdb' ]);
is($ret, 0, 'mdb_replication member can create a logical slot');

($ret, $stdout, $stderr) = $node->psql(
	'postgres', 'START_REPLICATION SLOT "lslot" LOGICAL 0/0',
	replication => 'database',
	extra_params => [ '-U', 'r_mdb' ]);
like(
	$stderr,
	$stream_started,
	'mdb_replication member can stream from a logical slot');
unlike($stderr, qr/ERROR/, '... and streaming began without error');

$node->stop('fast');

done_testing();
