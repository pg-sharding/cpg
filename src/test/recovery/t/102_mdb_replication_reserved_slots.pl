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
use strict;
use warnings FATAL => 'all';

use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

my $node = PostgreSQL::Test::Cluster->new('primary');
$node->init(allows_streaming => 'logical');
$node->start;

# regress_mdb_cp emulates the control plane: it has REPLICATION
# attribute.  regress_mdb_mdbrepl emulates the cluster user: mdb_replication only.
$node->safe_psql(
	'postgres', qq[
	CREATE ROLE regress_mdb_cp LOGIN REPLICATION;
	CREATE ROLE mdb_replication NOLOGIN;
	CREATE ROLE regress_mdb_mdbrepl LOGIN;
	GRANT mdb_replication TO regress_mdb_mdbrepl;
]);

# Control-plane slots, using the reserved prefix.
$node->safe_psql(
	'postgres',
	q[SELECT pg_create_physical_replication_slot('mdb_phys_slot', true)],
	extra_params => [ '-U', 'regress_mdb_cp' ]);

$node->safe_psql(
	'postgres',
	q[SELECT pg_create_physical_replication_slot('phys_slot', true)],
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

my $backup_name = 'my_backup';

# Take backup
$node->backup($backup_name);

# Create streaming standby linking to primary
my $node_standby = PostgreSQL::Test::Cluster->new('standby_1');
$node_standby->init_from_backup($node, $backup_name,
	has_streaming => 1);
$node_standby->start;
$node_standby->promote;


my ($ret, $stdout, $stderr);

# =============================================================================
# What mdb_replication allows
# =============================================================================

# --- walsender connection --------------------------------------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres', q[IDENTIFY_SYSTEM],
	replication => 'true',
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
is($ret, 0, 'mdb_replication member may do IDENTIFY_SYSTEM in repl connection');


($ret, $stdout, $stderr) = $node_standby->psql(
	'postgres', q[TIMELINE_HISTORY 2],
	replication => 'true',
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
is($ret, 0, 'mdb_replication member may open a replication connection');


# --- pg_create_logical_replication_slot (SQL) ------------------------------
$node->safe_psql(
	'postgres',
	q[SELECT pg_create_logical_replication_slot('regress_slot', 'test_decoding')],
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
is( $node->safe_psql(
		'postgres',
		q[SELECT count(*) FROM pg_replication_slots WHERE slot_name = 'regress_slot']
	),
	1,
	'mdb_replication member may create a logical slot of its own');

# --- pg_drop_replication_slot (SQL, own slot) ------------------------------
$node->safe_psql(
	'postgres',
	q[SELECT pg_drop_replication_slot('regress_slot')],
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
is( $node->safe_psql(
		'postgres',
		q[SELECT count(*) FROM pg_replication_slots WHERE slot_name = 'regress_slot']
	),
	0,
	'mdb_replication member may drop a logical slot of its own');

# --- pg_replication_slot_advance (SQL, own slot) ---------------------------
# Recreate the slot, advance it, verify it moved forward.
$node->safe_psql(
	'postgres',
	q[SELECT pg_create_logical_replication_slot('regress_slot2', 'test_decoding')],
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
$node->safe_psql('postgres', q[INSERT INTO dec_test VALUES ('advance_test')]);

# --- pg_logical_slot_get_changes (SQL, own slot) ---------------------------
# Call get_changes BEFORE advancing, so there is something to decode.
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT * FROM pg_logical_slot_get_changes('regress_slot2', NULL, NULL)],
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
is($ret, 0, 'mdb_replication member may pg_logical_slot_get_changes on own slot');
like(
	$stdout,
	qr/begin|INSERT|COMMIT/,
	'pg_logical_slot_get_changes returned decode output');

# --- pg_logical_slot_peek_changes (SQL, own slot) --------------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT * FROM pg_logical_slot_peek_changes('regress_slot2', NULL, NULL)],
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
is($ret, 0, 'mdb_replication member may pg_logical_slot_peek_changes on own slot');

my $target_lsn =
  $node->safe_psql('postgres', q[SELECT pg_current_wal_lsn()]);
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	qq[SELECT pg_replication_slot_advance('regress_slot2', '$target_lsn')],
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
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
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
is($ret, 0,
	'protocol: mdb_replication member may CREATE_REPLICATION_SLOT LOGICAL');

# Clean up the protocol-created slot.
$node->safe_psql(
	'postgres',
	q[SELECT pg_drop_replication_slot('tenant_proto')],
	extra_params => [ '-U', 'regress_mdb_cp' ]);

# =============================================================================
# What mdb_replication does not allow
# =============================================================================

# --- pg_create_physical_replication_slot (SQL) ----------------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT pg_create_physical_replication_slot('tenant_phys', true)],
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
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
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
isnt($ret, 0, 'protocol: mdb_replication may not create a physical slot');
like(
	$stderr,
	qr/must be superuser or replication role to use replication slots/,
	'protocol: ... with the rolreplication error');


# --- START_REPLICATION SLOT ... PHYSICAL (protocol) -----------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[START_REPLICATION SLOT mdb_phys_slot PHYSICAL 0/0],
	replication => 'true',
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
isnt($ret, 0, 'protocol: mdb_replication may not create a physical slot');
like(
	$stderr,
	qr/Slot names starting with "mdb" are reserved/,
	'protocol: ... with the rolreplication error');

($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[START_REPLICATION SLOT phys_slot PHYSICAL 0/0],
	replication => 'true',
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
isnt($ret, 0, 'protocol: mdb_replication may not create a physical slot');
like(
	$stderr,
	qr/must be superuser or replication role to use replication slots/,
	'protocol: ... with the rolreplication error');


# --- ALTER_REPLICATION_SLOT -----------------------------------
is( $node->safe_psql(
		'postgres',
		q[SELECT failover FROM pg_replication_slots WHERE slot_name = 'mdb_logical_slot']
	),
	'f',
	'reserved logical slot starts out with failover disabled');

($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[ALTER_REPLICATION_SLOT phys_slot (failover true)],
	replication => 'database',
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);

isnt($ret, 0, 'SQL: mdb_replication may not ALTER_REPLICATION_SLOT a phys slot');
like(
	$stderr,
	qr/must be superuser or replication role to use replication slots/,
	'ALTER_REPLICATION_SLOT rejected with permission error');

is( $node->safe_psql(
		'postgres',
		q[SELECT failover FROM pg_replication_slots WHERE slot_name = 'phys_slot']
	),
	'f',
	'... and the does not take effect');


# --- pg_copy_logical_replication_slot (SQL) --------------------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT pg_copy_logical_replication_slot('regress_slot2', 'tenant_copy')],
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
isnt($ret, 0, 'SQL: mdb_replication may not copy a logical slot');
like(
	$stderr,
	qr/permission denied to use replication slots/,
	'SQL: ... copy_logical rejected with permission error');

# --- pg_copy_physical_replication_slot (SQL) ------------------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT pg_copy_physical_replication_slot('mdb_phys_slot', 'tenant_phys_copy')],
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
isnt($ret, 0, 'SQL: mdb_replication may not copy a physical slot');
like(
	$stderr,
	qr/permission denied to use replication slots/,
	'SQL: ... copy_physical rejected with permission error');

# --- pg_sync_replication_slots (SQL) --------------------------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT pg_sync_replication_slots()],
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
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
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
isnt($ret, 0, 'protocol: mdb_replication may not BASE_BACKUP');
like(
	$stderr,
	qr/must be superuser or replication role to use replication slots/,
	'protocol: ... BASE_BACKUP rejected with rolreplication error');


# =============================================================================
# Reserved "mdb" prefix enforcement
# =============================================================================

# --- SQL path: create with reserved name -----------------------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT pg_create_logical_replication_slot('mdb_regress_slot', 'test_decoding')],
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
isnt($ret, 0, 'SQL: tenant may not create a slot with the reserved prefix');
like(
	$stderr,
	qr/slot name "mdb_regress_slot" is reserved/,
	'SQL: ... with the reserved-name error');


# --- SQL path: drop reserved slot ------------------------------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT pg_drop_replication_slot('mdb_logical_slot')],
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
isnt($ret, 0, 'SQL: tenant may not drop a reserved slot');
like(
	$stderr,
	qr/Slot names starting with "mdb" are reserved/,
	'SQL: ... with the reserved-name detail');

# --- SQL path: advance reserved slot --------------------------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT pg_replication_slot_advance('mdb_logical_slot', pg_current_wal_lsn())],
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
isnt($ret, 0, 'SQL: tenant may not advance a reserved slot');
like(
	$stderr,
	qr/Slot names starting with "mdb" are reserved/,
	'SQL: ... advance reserved rejected with reserved-name detail');

# --- SQL path: pg_logical_slot_get_changes on reserved slot ---------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[SELECT * FROM pg_logical_slot_get_changes('mdb_logical_slot', NULL, NULL)],
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
isnt($ret, 0, 'SQL: tenant may not get changes from a reserved slot');
like(
	$stderr,
	qr/Slot names starting with "mdb" are reserved/,
	'SQL: ... get_changes reserved rejected with reserved-name detail');


# --- Protocol path: START_REPLICATION SLOT ... LOGICAL (reserved) -----------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[START_REPLICATION SLOT mdb_logical_slot LOGICAL 0/0],
	replication => 'database',
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
isnt($ret, 0,
	'protocol: tenant may not start logical replication from a reserved slot');
like(
	$stderr,
	qr/slot name "mdb_logical_slot" is reserved/,
	'protocol: ... with the reserved-name error');

# --- Protocol path: DROP_REPLICATION_SLOT -----------------------
($ret, $stdout, $stderr) = $node->psql(
	'postgres',
	q[DROP_REPLICATION_SLOT mdb_logical_slot],
	replication => 'database',
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
isnt($ret, 0, 'protocol: tenant may not drop a reserved slot');
like(
	$stderr,
	qr/slot name "mdb_logical_slot" is reserved/,
	'protocol: ... with the reserved-name error');


# --- ALTER_REPLICATION_SLOT -----------------------------------
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
	extra_params => [ '-U', 'regress_mdb_mdbrepl' ]);
isnt($ret, 0,
	'tenant not allowed to ALTER_REPLICATION_SLOT a reserved slot');
is( $node->safe_psql(
		'postgres',
		q[SELECT failover FROM pg_replication_slots WHERE slot_name = 'mdb_logical_slot']
	),
	'f',
	'... and the does not take effect');
like(
	$stderr,
	qr/slot name "mdb_logical_slot" is reserved/,
	'protocol: ... with the reserved-name error');

$node->stop;

done_testing();
