/* contrib/pg_target_promote/pg_target_promote.c */

#include "postgres.h"

#include "access/xlog.h"
#include "fmgr.h"

PG_MODULE_MAGIC;

PG_FUNCTION_INFO_V1(pg_bump_timeline);

Datum
pg_bump_timeline(PG_FUNCTION_ARGS)
{
	if (RecoveryInProgress())
		ereport(ERROR,
				(errcode(ERRCODE_OBJECT_NOT_IN_PREREQUISITE_STATE),
				 errmsg("recovery is in progress"),
				 errhint("pg_bump_timeline() can only be executed on a primary, not during recovery.")));

	BumpTimeLine();

	PG_RETURN_VOID();
}
