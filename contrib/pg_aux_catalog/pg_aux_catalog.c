/*-------------------------------------------------------------------------
 *
 * pg_aux_catalog.c
 *    Extension for auxiliary catalog management
 *
 *    contrib/pg_aux_catalog/pg_aux_catalog.c
 *
 *-------------------------------------------------------------------------
 */
#include "postgres.h"

#include "access/htup_details.h"
#include "access/table.h"
#include "catalog/binary_upgrade.h"
#include "catalog/indexing.h"
#include "catalog/pg_authid.h"
#include "catalog/pg_authid_d.h"
#include "commands/user.h"
#include "fmgr.h"
#include "nodes/makefuncs.h"
#include "nodes/parsenodes.h"
#include "utils/builtins.h"
#include "utils/fmgroids.h"
#include "utils/rel.h"
#include "utils/syscache.h"

PG_MODULE_MAGIC;

PG_FUNCTION_INFO_V1(pg_create_mdb_admin_role);

/*
 * Create the mdb_admin role with a fixed OID (8067).
 *
 * This function creates a role with:
 *   - No login
 *   - No superuser
 *   - No CREATEROLE/CREATEDB
 *   - CONNECTION LIMIT = 0
 *   - INHERIT = true (default)
 *   - No password
 */
Datum
pg_create_mdb_admin_role(PG_FUNCTION_ARGS)
{
	CreateRoleStmt stmt;
	List	   *options = NIL;
	Oid			roleid;

	/* Check if role with OID 8067 already exists */
	if (SearchSysCacheExists1(AUTHOID, ObjectIdGetDatum(8067)))
		ereport(ERROR,
				(errcode(ERRCODE_DUPLICATE_OBJECT),
				 errmsg("role with OID %u already exists", 8067)));

	/* Check if role with name "mdb_admin" already exists */
	if (SearchSysCacheExists1(AUTHNAME, CStringGetDatum("mdb_admin")))
		ereport(ERROR,
				(errcode(ERRCODE_DUPLICATE_OBJECT),
				 errmsg("role \"mdb_admin\" already exists")));

	/* Build options for CreateRole: connection limit = 0 */
	options = list_make1(makeDefElem("connectionlimit",
									 (Node *) makeInteger(0), -1));

	/* Prepare the CreateRoleStmt */
	memset(&stmt, 0, sizeof(stmt));
	stmt.type = T_CreateRoleStmt;
	stmt.stmt_type = ROLESTMT_ROLE;
	stmt.role = "mdb_admin";
	stmt.options = options;

	/* Set the binary-upgrade override so that CreateRole uses OID 8067 */
	binary_upgrade_next_pg_authid_oid = 8067;

	/* Create the role using the kernel function */
	roleid = CreateRole(NULL, &stmt);

	PG_RETURN_OID(roleid);
}