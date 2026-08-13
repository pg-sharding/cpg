# Permission checks around mdb_replication and MDB-reserved ("mdb"-prefixed)
# replication slots.
#
# mdb_replication is meant to be the "narrow half" of the REPLICATION
# attribute: it lets a tenant drive logical decoding, while the slots of the
# control plane -- which carry the reserved "mdb" prefix -- stay reachable only
# for roles holding the real REPLICATION attribute.  The prefix is enforced by
# CheckRoleUseMDBReservedName() (src/backend/replication/slot.c), which keys off
# role_has_rolreplication only, so mdb_replication membership never helps.
#
# This test exercises the full matrix from §3.2 of MDB-ROLES.md:
#   * Operations that mdb_replication allows (logical slot lifecycle).
#   * Operations that mdb_replication does NOT allow (physical slots, base
#     backup, copy, sync).
#   * The reserved "mdb" prefix enforcement on both SQL and protocol paths.
#   * Two known gaps in walsender.c (ALTER_REPLICATION_SLOT and physical
#     START_REPLICATION) documented as "KNOWN GAP" assertions.
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
	q[SELECT pg_create_logical_replication_slot('mdb_logical_slot', 'test_decoding')],
	extra_params => [ '-U', 'regress_mdb_cp' ]);

# Create a publication and a table with data for logical decoding tests.
$node->safe_psql(
	'postgres', qq[
	CREATE TABLE dec_test(data text);
	INSERT INTO dec_test VALUES ('init');
]);

my ($ret, $stdout, $stderr);

# =============================================================================
# Part 1: What mdb_replication ALLOWS (the "yes" column of the matrix)
# =============================================================================

# --- walsender connection --------------------------------------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres', q[IDENTIFY_SYSTEM],
	replication => 'true',
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
is($ret, 0, 'mdb_replication member may open a replication connection');

# --- pg_create_logical_replication_slot (SQL) ------------------------------
$node->safe_psql(
	'postgres',
	q[SELECT pg_create_logical_replication_slot('tenant_slot', 'test_decoding')],
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
is( $node->safe_psql(
		'postgres',
		q[SELECT count(*) FROM pg_replication_slots WHERE slot_name = 'tenant_slot']
	),
	1,
	'mdb_replication member may create a logical slot of its own');

# --- pg_drop_replication_slot (SQL, own slot) ------------------------------
$node->safe_psql(
	'postgres',
	q[SELECT pg_drop_replication_slot('tenant_slot')],
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
is( $node->safe_psql(
		'postgres',
		q[SELECT count(*) FROM pg_replication_slots WHERE slot_name = 'tenant_slot']
	),
	0,
	'mdb_replication member may drop a logical slot of its own');

# --- pg_replication_slot_advance (SQL, own slot) ---------------------------
# Recreate the slot, advance it, verify it moved forward.
$node->safe_psql(
	'postgres',
	q[SELECT pg_create_logical_replication_slot('tenant_slot2', 'test_decoding')],
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
$node->safe_psql('postgres', q[INSERT INTO dec_test VALUES ('advance_test')]);

# --- pg_logical_slot_get_changes (SQL, own slot) ---------------------------
# Call get_changes BEFORE advancing, so there is something to decode.
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT * FROM pg_logical_slot_get_changes('tenant_slot2', NULL, NULL)],
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
is($ret, 0, 'mdb_replication member may pg_logical_slot_get_changes on own slot');
like(
	$stdout,
	qr/begin|INSERT|COMMIT/,
	'pg_logical_slot_get_changes returned decode output');

# --- pg_logical_slot_peek_changes (SQL, own slot) --------------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT * FROM pg_logical_slot_peek_changes('tenant_slot2', NULL, NULL)],
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
is($ret, 0, 'mdb_replication member may pg_logical_slot_peek_changes on own slot');

my $target_lsn =
  $node->safe_psql('postgres', q[SELECT pg_current_wal_lsn()]);
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	qq[SELECT pg_replication_slot_advance('tenant_slot2', '$target_lsn')],
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
is($ret, 0, 'mdb_replication member may advance a slot of its own');
like(
	$stdout,
	qr/0\/[0-9A-F]+/,
	'pg_replication_slot_advance returned a LSN');

# --- CREATE_REPLICATION_SLOT ... LOGICAL (protocol) ------------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[CREATE_REPLICATION_SLOT tenant_proto LOGICAL test_decoding],
	replication => 'database',
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
is($ret, 0,
	'protocol: mdb_replication member may CREATE_REPLICATION_SLOT LOGICAL');

# Clean up the protocol-created slot.
$node->safe_psql(
	'postgres',
	q[SELECT pg_drop_replication_slot('tenant_proto')],
	extra_params => [ '-U', 'regress_mdb_cp' ]);

# =============================================================================
# Part 2: What mdb_replication does NOT allow (the "no" column)
# =============================================================================

# --- pg_create_physical_replication_slot (SQL) ----------------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT pg_create_physical_replication_slot('tenant_phys', true)],
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
isnt($ret, 0, 'SQL: mdb_replication may not create a physical slot');
like(
	$stderr,
	qr/permission denied to use replication slots/,
	'SQL: ... with the permission error');
like(
	$stderr,
	qr/Only roles with the REPLICATION attribute/,
	'SQL: ... mentioning the REPLICATION attribute');

# --- CREATE_REPLICATION_SLOT ... PHYSICAL (protocol) -----------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[CREATE_REPLICATION_SLOT tenant_phys2 PHYSICAL],
	replication => 'true',
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
isnt($ret, 0, 'protocol: mdb_replication may not create a physical slot');
like(
	$stderr,
	qr/must be superuser or replication role to use replication slots/,
	'protocol: ... with the rolreplication error');

# --- pg_copy_logical_replication_slot (SQL) --------------------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT pg_copy_logical_replication_slot('tenant_slot2', 'tenant_copy')],
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
isnt($ret, 0, 'SQL: mdb_replication may not copy a logical slot');
like(
	$stderr,
	qr/permission denied to use replication slots/,
	'SQL: ... copy_logical rejected with permission error');

# --- pg_copy_physical_replication_slot (SQL) ------------------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT pg_copy_physical_replication_slot('mdb_phys_slot', 'tenant_phys_copy')],
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
isnt($ret, 0, 'SQL: mdb_replication may not copy a physical slot');
like(
	$stderr,
	qr/permission denied to use replication slots/,
	'SQL: ... copy_physical rejected with permission error');

# --- pg_sync_replication_slots (SQL) --------------------------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT pg_sync_replication_slots()],
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
isnt($ret, 0, 'SQL: mdb_replication may not sync replication slots');
like(
	$stderr,
	qr/permission denied to use replication slots/,
	'SQL: ... sync_slots rejected with permission error');

# --- BASE_BACKUP (protocol) -----------------------------------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[BASE_BACKUP],
	replication => 'true',
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
isnt($ret, 0, 'protocol: mdb_replication may not BASE_BACKUP');
like(
	$stderr,
	qr/must be superuser or replication role to use replication slots/,
	'protocol: ... BASE_BACKUP rejected with rolreplication error');

# --- pg_basebackup (external tool) -----------------------------------------
command_fails(
	[
		'pg_basebackup',
		'-D', PostgreSQL::Test::Utils::tempdir,
		'-X', 'none',
		'-c', 'fast',
		'-d', $node->connstr('postgres') . ' user=regress_mdb_tenant',
	],
	'pg_basebackup: mdb_replication may not take a base backup');

# =============================================================================
# Part 3: Reserved "mdb" prefix enforcement
# =============================================================================

# --- SQL path: create with reserved name -----------------------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT pg_create_logical_replication_slot('mdb_tenant_slot', 'test_decoding')],
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
isnt($ret, 0, 'SQL: tenant may not create a slot with the reserved prefix');
like(
	$stderr,
	qr/slot name "mdb_tenant_slot" is reserved/,
	'SQL: ... with the reserved-name error');

# --- SQL path: create physical slot with reserved name ---------------------
# This fails at CheckSlotPermissions (before the reserved-name check) because
# mdb_replication can't create physical slots at all.
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT pg_create_physical_replication_slot('mdb_tenant_phys', true)],
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
isnt($ret, 0,
	'SQL: tenant may not create a physical slot with the reserved prefix');

# --- SQL path: drop reserved slot ------------------------------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT pg_drop_replication_slot('mdb_logical_slot')],
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
isnt($ret, 0, 'SQL: tenant may not drop a reserved slot');
like(
	$stderr,
	qr/Slot names starting with "mdb" are reserved/,
	'SQL: ... with the reserved-name detail');

# --- SQL path: advance reserved slot --------------------------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT pg_replication_slot_advance('mdb_logical_slot', pg_current_wal_lsn())],
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
isnt($ret, 0, 'SQL: tenant may not advance a reserved slot');
like(
	$stderr,
	qr/Slot names starting with "mdb" are reserved/,
	'SQL: ... advance reserved rejected with reserved-name detail');

# --- SQL path: pg_logical_slot_get_changes on reserved slot ---------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT * FROM pg_logical_slot_get_changes('mdb_logical_slot', NULL, NULL)],
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
isnt($ret, 0, 'SQL: tenant may not get changes from a reserved slot');
like(
	$stderr,
	qr/Slot names starting with "mdb" are reserved/,
	'SQL: ... get_changes reserved rejected with reserved-name detail');

# --- SQL path: copy from reserved slot -------------------------------------
# copy_logical uses CheckSlotPermissions (no mdb_replication), so this fails
# with the permission error, not the reserved-name error.
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT pg_copy_logical_replication_slot('mdb_logical_slot', 'tenant_copy2')],
	extra_params => [ '-U', 'regress_mdb_tenant' ]);
isnt($ret, 0, 'SQL: tenant may not copy from a reserved slot');

# --- Protocol path: START_REPLICATION SLOT ... LOGICAL (reserved) -----------
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

# --- Protocol path: DROP_REPLICATION_SLOT (reserved) -----------------------
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

# =============================================================================
# Part 4: KNOWN GAPs — missing checks in walsender.c
# =============================================================================

# --- KNOWN GAP 1: ALTER_REPLICATION_SLOT -----------------------------------
# AlterReplicationSlot() (walsender.c) has neither a permission check nor a
# CheckRoleUseMDBReservedName() call, so the tenant can reconfigure a
# control-plane slot it may not read, drop or advance.
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

# --- KNOWN GAP 2: physical START_REPLICATION -------------------------------
# The physical branch of START_REPLICATION (StartReplication(), same file)
# calls neither check_permissions() nor CheckRoleUseMDBReservedName(), so the
# tenant can attach to a control-plane physical slot and stream WAL from it.
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

# Cleanup: reset the failover flag we changed via the KNOWN GAP.
$node->safe_psql(
	'postgres',
	q[ALTER_REPLICATION_SLOT mdb_logical_slot (failover false)],
	replication => 'database',
	extra_params => [ '-U', 'regress_mdb_cp' ]);

$node->stop;

done_testing();
