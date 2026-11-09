/* Actual GiST AM rescan + bitmap scan benchmark, no extracted page model. */
#include "postgres.h"
#include <time.h>
#include "access/genam.h"
#include "access/relscan.h"
#include "access/stratnum.h"
#include "catalog/pg_type_d.h"
#include "fmgr.h"
#include "miscadmin.h"
#include "nodes/tidbitmap.h"
#include "utils/array.h"
#include "utils/builtins.h"
#include "utils/fmgroids.h"
#include "utils/fmgrprotos.h"
#include "utils/lsyscache.h"
#include "utils/snapmgr.h"

PG_MODULE_MAGIC;
PG_FUNCTION_INFO_V1(box_am_micro);
PG_FUNCTION_INFO_V1(gist_batch_forward_consistent);

Datum
gist_batch_forward_consistent(PG_FUNCTION_ARGS)
{
	return gist_box_consistent(fcinfo);
}

Datum
box_am_micro(PG_FUNCTION_ARGS)
{
	Relation index = index_open(PG_GETARG_OID(0), AccessShareLock);
	ArrayType *queries = PG_GETARG_ARRAYTYPE_P(1);
	int repeats = PG_GETARG_INT32(2);
	Datum *values;
	bool *nulls;
	int nvalues;
	int16 typlen;
	bool typbyval;
	char typalign;
	IndexScanDesc scan;
	ScanKeyData key;
	struct timespec before, after;
	uint64 tids = 0;
	uint64 calls = 0;
	uint64 elapsed;

	if (repeats < 1 || repeats > 4096)
		elog(ERROR, "repeat count outside benchmark bound");
	get_typlenbyvalalign(BOXOID, &typlen, &typbyval, &typalign);
	deconstruct_array(queries, BOXOID, typlen, typbyval, typalign,
					  &values, &nulls, &nvalues);
	if (nvalues < 1 || nvalues > 512)
		elog(ERROR, "query count outside benchmark bound");
	for (int i = 0; i < nvalues; i++)
		if (nulls[i])
			elog(ERROR, "microbenchmark queries must be non-NULL");
	scan = index_beginscan_bitmap(index, GetActiveSnapshot(), 1);
	ScanKeyInit(&key, 1, RTOverlapStrategyNumber, F_BOX_OVERLAP, values[0]);
	if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &before) != 0)
		elog(ERROR, "cannot read process CPU clock");
	for (int repeat = 0; repeat < repeats; repeat++)
	{
		for (int i = 0; i < nvalues; i++)
		{
			TIDBitmap *bitmap;

			CHECK_FOR_INTERRUPTS();
			key.sk_argument = values[i];
			index_rescan(scan, &key, 1, NULL, 0);
			bitmap = tbm_create(4 * 1024 * 1024, NULL);
			tids += index_getbitmap(scan, bitmap);
			tbm_free(bitmap);
			calls++;
		}
	}
	if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &after) != 0)
		elog(ERROR, "cannot read process CPU clock");
	elapsed = (uint64) after.tv_sec * UINT64CONST(1000000000) + after.tv_nsec -
		((uint64) before.tv_sec * UINT64CONST(1000000000) + before.tv_nsec);
	index_endscan(scan);
	index_close(index, AccessShareLock);
	pfree(values);
	pfree(nulls);
	PG_RETURN_TEXT_P(cstring_to_text(psprintf("{\"cpu_ns\":" UINT64_FORMAT
										 ",\"tids\":" UINT64_FORMAT
										 ",\"scans\":" UINT64_FORMAT "}",
										 elapsed, tids, calls)));
}
