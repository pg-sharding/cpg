/* Untimed inspection after an ordinary real two-key builtin-array GIN scan. */
#include "postgres.h"
#include "fmgr.h"
#include "access/genam.h"
#include "access/gin_private.h"
#include "access/relscan.h"
#include "access/skey.h"
#include "catalog/pg_am_d.h"
#include "catalog/pg_type_d.h"
#include "nodes/tidbitmap.h"
#include "storage/lockdefs.h"
#include "utils/builtins.h"
#include "utils/fmgroids.h"
#include "utils/jsonb.h"
#include "utils/rel.h"
#include "utils/snapmgr.h"

PG_MODULE_MAGIC;
PG_FUNCTION_INFO_V1(gin_shared_probe);

Datum
gin_shared_probe(PG_FUNCTION_ARGS)
{
	Relation index = index_open(PG_GETARG_OID(0), AccessShareLock);
	IndexScanDesc scan;
	ScanKeyData keys[2];
	TIDBitmap *bitmap;
	GinScanOpaque so;
	int64 tids;
	uint32 sum = 0;
	uint32 shared = 0;
	uint32 null_extra = 0;
	int heap_keys = 0;
	char *result;

	if (index->rd_rel->relam != GIN_AM_OID)
		elog(ERROR, "expected fixture GIN index");
	for (int i = 0; i < 2; i++)
	{
		ScanKeyInit(&keys[i], 1, 1, F_ARRAYOVERLAP, PG_GETARG_DATUM(i + 1));
		keys[i].sk_subtype = INT4ARRAYOID;
	}
	scan = index_beginscan_bitmap(index, GetActiveSnapshot(), NULL, 2);
	index_rescan(scan, keys, 2, NULL, 0);
	bitmap = tbm_create(64 * 1024 * 1024, NULL);
	tids = index_getbitmap(scan, bitmap);
	so = (GinScanOpaque) scan->opaque;
	if (so->nkeys != 2)
		elog(ERROR, "expected two fixture keys");
	for (uint32 k = 0; k < so->nkeys; k++)
	{
		sum += so->keys[k].nentries;
		for (uint32 i = 0; i < so->keys[k].nentries; i++)
			if (so->keys[k].scanEntry[i]->extra_data == NULL)
				null_extra++;
#ifdef OR_HEAP_VARIANT
		if (so->keys[k].requiredHeap != NULL)
			heap_keys++;
#endif
	}
	for (uint32 i = 0; i < so->keys[0].nentries; i++)
		for (uint32 j = 0; j < so->keys[1].nentries; j++)
			if (so->keys[0].scanEntry[i] == so->keys[1].scanEntry[j])
				shared++;
	result = psprintf("{\"nkeys\":%u,\"sum_key_entries\":%u,\"unique_entries\":%u,"
					  "\"shared_pointer_pairs\":%u,\"null_extra_entries\":%u,"
					  "\"required_heap_keys\":%d,\"required\":[%d,%d],\"tids\":" INT64_FORMAT "}",
					  so->nkeys, sum, so->totalentries, shared, null_extra,
					  heap_keys, so->keys[0].nrequired, so->keys[1].nrequired, tids);
	tbm_free(bitmap);
	index_endscan(scan);
	index_close(index, AccessShareLock);
	PG_RETURN_DATUM(DirectFunctionCall1(jsonb_in, CStringGetDatum(result)));
}
