# Permission checks around MDB-reserved ("mdb"-prefixed) replication slots.
#
# mdb_replication is meant to be the "narrow half" of the REPLICATION
# attribute: it lets a tenant drive logical decoding, while the slots of the
# control plane -- which carry the reserved "mdb" prefix -- stay reachable only
# for roles holding the real REPLICATION attribute.  The prefix is enforced by
# CheckRoleUseMDBReservedName() (src/backend/replication/slot.c), which keys off
# role_has_rolreplication only, so mdb_replication membership never helps.
#
# That check is, however, wired into walsender.c inconsistently.  This file
# pins down both the enforced paths and the two paths where the check is
# missing today, so that plugging the holes makes this test fail loudly rather
# than silently changing behaviour.  Assertions describing the holes are
# labelled "KNOWN GAP".
use strict;
use warnings FATAL => 'all';

use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

my $node = PostgreSQL::Test::Cluster->new('primary');
$node->init(allows_streaming => 'logical');
$node->start;

# regress_mdb_cp plays the control plane: it holds the real REPLICATION
# attribute.  regress_mdb_tenant plays the cluster user: mdb_replication only.
$node->safe_psql(
	'postgres', qq[
	CREATE ROLE regress_mdb_cp LOGIN REPLICATION;
	CREATE ROLE mdb_replication NOLOGIN;
	CREATE ROLE regress_mdb_tenant LOGIN;
	GRANT mdb_replication TO regress_mdb_tenant;
]);

# Control-plane slots, using the reserved prefix.
$node->safe_psql(
	'postgres',
	q[SELECT pg_create_physical_replication_slot('mdb_phys_slot', true)],
	extra_params => [ '-U', 'regress_mdb_cp' ]);
$node->safe_psql(
	'postgres',
	q[SELECT pg_create_logical_replication_slot('mdb_logical_slot', 'pgoutput')],
	extra_params => [ '-U', 'regress_mdb_cp' ]);

my ($ret, $stdout, $stderr);

# The tenant is a walsender-capable role: this is what mdb_replication buys,
# and it is the precondition for everything below.
($ret, $stdout, $stderr) = $node->psql(
	'postgres', q[IDENTIFY_SYSTEM],
	replication => 'true',
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
is($ret, 0, 'mdb_replication member may open a replication connection');

# It can also drive logical decoding on its own slots ...
$node->safe_psql(
	'postgres',
	q[SELECT pg_create_logical_replication_slot('tenant_slot', 'pgoutput')],
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
is( $node->safe_psql(
		'postgres',
		q[SELECT count(*) FROM pg_replication_slots WHERE slot_name = 'tenant_slot']
	),
	1,
	'mdb_replication member may create a logical slot of its own');

#
# Enforced paths: the reserved prefix keeps the tenant away from the
# control-plane slots.
#

($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT pg_create_logical_replication_slot('mdb_tenant_slot', 'pgoutput')],
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
isnt($ret, 0, 'SQL: tenant may not create a slot with the reserved prefix');
like(
	$stderr,
	qr/slot name "mdb_tenant_slot" is reserved/,
	'SQL: ... with the reserved-name error');

($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT pg_drop_replication_slot('mdb_logical_slot')],
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
isnt($ret, 0, 'SQL: tenant may not drop a reserved slot');
like(
	$stderr,
	qr/Slot names starting with "mdb" are reserved/,
	'SQL: ... with the reserved-name detail');

($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT pg_replication_slot_advance('mdb_logical_slot', pg_current_wal_lsn())],
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
isnt($ret, 0, 'SQL: tenant may not advance a reserved slot');

# Physical slots are out of reach for mdb_replication entirely: this path uses
# the re-introduced check_permissions(), which only honours rolreplication.
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[CREATE_REPLICATION_SLOT mdb_tenant_phys PHYSICAL],
	replication => 'true',
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
isnt($ret, 0, 'protocol: tenant may not create a physical slot');
like(
	$stderr,
	qr/must be superuser or replication role to use replication slots/,
	'protocol: ... with the rolreplication error');

($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[START_REPLICATION SLOT mdb_logical_slot LOGICAL 0/0],
	replication => 'database',
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
isnt($ret, 0,
	'protocol: tenant may not start logical replication from a reserved slot');
like(
	$stderr,
	qr/slot name "mdb_logical_slot" is reserved/,
	'protocol: ... with the reserved-name error');

($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[DROP_REPLICATION_SLOT mdb_logical_slot],
	replication => 'database',
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
isnt($ret, 0, 'protocol: tenant may not drop a reserved slot');
like(
	$stderr,
	qr/slot name "mdb_logical_slot" is reserved/,
	'protocol: ... with the reserved-name error');

#
# KNOWN GAP 1: AlterReplicationSlot() (src/backend/replication/walsender.c) has
# neither a permission check nor a CheckRoleUseMDBReservedName() call, so the
# tenant can reconfigure a control-plane slot it may not read, drop or advance.
#

is( $node->safe_psql(
		'postgres',
		q[SELECT failover FROM pg_replication_slots WHERE slot_name = 'mdb_logical_slot']
	),
	'f',
	'reserved logical slot starts out with failover disabled');

($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[ALTER_REPLICATION_SLOT mdb_logical_slot (failover true)],
	replication => 'database',
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
is($ret, 0,
	'KNOWN GAP: tenant may ALTER_REPLICATION_SLOT a reserved slot');
is( $node->safe_psql(
		'postgres',
		q[SELECT failover FROM pg_replication_slots WHERE slot_name = 'mdb_logical_slot']
	),
	't',
	'KNOWN GAP: ... and the change takes effect');

#
# KNOWN GAP 2: the physical branch of START_REPLICATION (StartReplication(),
# same file) calls neither check_permissions() nor
# CheckRoleUseMDBReservedName(), so the tenant can attach to a control-plane
# physical slot and stream WAL from it -- even though it could not have created
# that slot in the first place.
#

# Produce some WAL and a deterministic stopping point for the stream.
$node->safe_psql(
	'postgres', qq[
	CREATE TABLE wal_filler(i int);
	INSERT INTO wal_filler SELECT generate_series(1, 10000);
	SELECT pg_switch_wal();
]);
my $endpos = $node->safe_psql('postgres', q[SELECT pg_current_wal_lsn()]);

# pg_receivewal issues START_REPLICATION SLOT ... PHYSICAL under the hood.
# --no-loop makes a rejected connection an immediate failure instead of a retry.
my $stream_dir = PostgreSQL::Test::Utils::tempdir;
command_ok(
	[
		'pg_receivewal', '--no-sync', '--no-loop',
		'-D', $stream_dir,
		'-S', 'mdb_phys_slot',
		'--endpos', $endpos,
		'-d', $node->connstr('postgres') . ' user=regress_mdb_tenant'
	],
	'KNOWN GAP: tenant may START_REPLICATION from a reserved physical slot');

$node->stop;

done_testing();
