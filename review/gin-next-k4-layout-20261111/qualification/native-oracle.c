/* Installed full-backend dispatcher, real index support metadata, valid ternary vectors. */
#include "postgres.h"
#include "fmgr.h"
#include "access/genam.h"
#include "access/gin_private.h"
#include "catalog/pg_am_d.h"
#include "lib/stringinfo.h"
#include "miscadmin.h"
#include "storage/lockdefs.h"
#include "tsearch/ts_type.h"
#include "utils/builtins.h"
#include "utils/memutils.h"
#include "utils/rel.h"

PG_MODULE_MAGIC;
PG_FUNCTION_INFO_V1(gin_cache_native_oracle);

/* B predates the appended cache field. The compiler selects the installed ABI. */
#ifndef EXPECT_TRI_CACHE
#error EXPECT_TRI_CACHE must identify the exact installed source variant
#endif

Datum
gin_cache_native_oracle(PG_FUNCTION_ARGS)
{
	Relation index = index_open(PG_GETARG_OID(0), AccessShareLock);
	MemoryContext context;
	MemoryContext old;
	GinState state;
	GinScanKeyData key;
	TSQuery query;
	int32 nquery = 0;
	bool *partial = NULL;
	bool *nulls = NULL;
	Pointer *extra = NULL;
	int32 mode = GIN_SEARCH_MODE_DEFAULT;
	bool hidden = PG_GETARG_BOOL(2);
	uint64 vectors = 1, checks = 0;
	bool enabled;
	StringInfoData report;

	if (index->rd_rel->relam != GIN_AM_OID)
		elog(ERROR, "ordinary cache oracle expects a GIN index");
	initGinState(&state, index);
	context = AllocSetContextCreate(CurrentMemoryContext, "valid cache vectors", ALLOCSET_DEFAULT_SIZES);
	old = MemoryContextSwitchTo(context);
	query = PG_GETARG_TSQUERY(1);
	MemSet(&key, 0, sizeof(key));
	key.query = PointerGetDatum(query);
	key.queryValues = (Datum *) DatumGetPointer(FunctionCall7Coll(&state.extractQueryFn[0], state.supportCollation[0],
		key.query, PointerGetDatum(&nquery), UInt16GetDatum(1), PointerGetDatum(&partial),
		PointerGetDatum(&extra), PointerGetDatum(&nulls), PointerGetDatum(&mode)));
	if (nquery < 1 || nquery > 9)
		elog(ERROR, "ordinary cache oracle query must have 1..9 entries");
	key.nuserentries = nquery;
	key.nentries = nquery;
	if (key.nentries + (hidden ? 1 : 0) > 9)
		elog(ERROR, "ordinary cache oracle vector exceeds fixed bound");
	key.attnum = 1;
	key.strategy = 1;
	key.searchMode = mode;
	key.extra_data = extra;
	key.queryCategories = palloc0_array(GinNullCategory, nquery);
	key.entryRes = palloc0_array(GinTernaryValue, key.nentries + (hidden ? 1 : 0));
	ginInitConsistentFunction(&state, &key);
	if (hidden)
		key.nentries++;
	#if EXPECT_TRI_CACHE
	enabled = (key.triCache != NULL);
#else
	enabled = false;
#endif
	if (enabled != (EXPECT_TRI_CACHE && nquery <= 8))
		elog(ERROR, "unexpected builtin cache eligibility");
	for (uint32 i = 0; i < key.nentries; i++)
		vectors *= 3;
	for (uint64 code = 0; code < vectors; code++)
	{
		uint64 digits = code;
		GinTernaryValue expected;

		for (uint32 i = 0; i < key.nentries; i++)
		{
			key.entryRes[i] = digits % 3;
			digits /= 3;
		}
		expected = DatumGetGinTernaryValue(FunctionCall7Coll(&state.triConsistentFn[0], state.supportCollation[0],
			PointerGetDatum(key.entryRes), UInt16GetDatum(key.strategy), key.query,
			Int32GetDatum(key.nuserentries), PointerGetDatum(key.extra_data),
			PointerGetDatum(key.queryValues), PointerGetDatum(key.queryCategories)));
		for (int sentinel = 0; sentinel < 2; sentinel++)
		{
			for (int repeat = 0; repeat < 2; repeat++)
			{
				GinTernaryValue actual;

				key.recheckCurItem = sentinel;
				actual = key.triConsistentFn(&key);
				if (actual != expected || key.recheckCurItem != sentinel)
					elog(ERROR, "production tri memo differs from builtin or changes recheck state");
				checks++;
			}
		}
		CHECK_FOR_INTERRUPTS();
	}
	PG_FREE_IF_COPY(query, 1);
	MemoryContextSwitchTo(old);
	MemoryContextDelete(context);
	index_close(index, AccessShareLock);
	initStringInfo(&report);
	appendStringInfo(&report, "{\"status\":\"PASS_VALID_NATIVE_TRI_DISPATCH\",\"nuserentries\":%d,\"nentries\":%u,\"cache_allocated\":%s,\"vectors\":" UINT64_FORMAT ",\"checks\":" UINT64_FORMAT ",\"timing_samples\":0}",
		nquery, key.nentries, enabled ? "true" : "false", vectors, checks);
	PG_RETURN_TEXT_P(cstring_to_text(report.data));
}
