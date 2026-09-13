/* contrib/pg_target_promote/pg_target_promote.c */

#include "postgres.h"

#include "access/xlog.h"
#include "fmgr.h"

/*
 * pg_target_promote() is implemented in the core backend
 * (src/backend/access/transam/xlogfuncs.c).  This extension provides
 * a thin proxy so that the SQL function is only available after
 * CREATE EXTENSION, without modifying the core pg_proc catalog.
 */

PG_MODULE_MAGIC;

PG_FUNCTION_INFO_V1(pg_target_promote_proxy);

Datum
pg_target_promote_proxy(PG_FUNCTION_ARGS)
{
	return DirectFunctionCall3(pg_target_promote,
							   PG_GETARG_DATUM(0),
							   PG_GETARG_DATUM(1),
							   PG_GETARG_DATUM(2));
}
