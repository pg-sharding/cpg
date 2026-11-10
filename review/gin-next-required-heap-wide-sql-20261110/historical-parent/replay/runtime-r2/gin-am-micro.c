/* Actual GIN AM consumption: no extracted entry loop or modeled loader. */
#include "postgres.h"
#include "fmgr.h"
#include "access/genam.h"
#include "access/skey.h"
#include "catalog/pg_am_d.h"
#include "catalog/pg_type_d.h"
#include "miscadmin.h"
#include "nodes/tidbitmap.h"
#include "storage/lockdefs.h"
#include "utils/builtins.h"
#include "utils/fmgroids.h"
#include "utils/jsonb.h"
#include "utils/rel.h"
#include "utils/snapmgr.h"
#include <time.h>

PG_MODULE_MAGIC;
PG_FUNCTION_INFO_V1(gin_am_micro);

static uint64
nanoseconds(clockid_t clock)
{
	struct timespec ts;

	if (clock_gettime(clock, &ts) != 0)
		elog(ERROR, "clock_gettime failed");
	return (uint64) ts.tv_sec * UINT64CONST(1000000000) + ts.tv_nsec;
}

Datum
gin_am_micro(PG_FUNCTION_ARGS)
{
	Oid			indexoid = PG_GETARG_OID(0);
	Datum		query = PG_GETARG_DATUM(1);
	int32		loops = PG_GETARG_INT32(2);
	Relation	index;
	IndexScanDesc scan;
	ScanKeyData key;
	int64		total = 0;
	uint64		cpu_start;
	uint64		wall_start;
	uint64		cpu;
	uint64		wall;
	char	   *result;

	if (loops < 1 || loops > 100000)
		elog(ERROR, "loop count out of range");
	index = index_open(indexoid, AccessShareLock);
	if (index->rd_rel->relam != GIN_AM_OID)
		elog(ERROR, "expected GIN index");
	ScanKeyInit(&key, 1, 1, F_TS_MATCH_VQ, query);
	key.sk_subtype = TSQUERYOID;
	scan = index_beginscan_bitmap(index, GetActiveSnapshot(), NULL, 1);
	cpu_start = nanoseconds(CLOCK_PROCESS_CPUTIME_ID);
	wall_start = nanoseconds(CLOCK_MONOTONIC);
	for (int i = 0; i < loops; i++)
	{
		TIDBitmap  *bitmap = tbm_create(64 * 1024 * 1024, NULL);

		CHECK_FOR_INTERRUPTS();
		index_rescan(scan, &key, 1, NULL, 0);
		total += index_getbitmap(scan, bitmap);
		tbm_free(bitmap);
	}
	wall = nanoseconds(CLOCK_MONOTONIC) - wall_start;
	cpu = nanoseconds(CLOCK_PROCESS_CPUTIME_ID) - cpu_start;
	index_endscan(scan);
	index_close(index, AccessShareLock);
	result = psprintf("{\"loops\":%d,\"total_tids\":" INT64_FORMAT
					 ",\"cpu_ns\":" UINT64_FORMAT ",\"wall_ns\":" UINT64_FORMAT "}",
					 loops, total, cpu, wall);
	PG_RETURN_DATUM(DirectFunctionCall1(jsonb_in, CStringGetDatum(result)));
}
