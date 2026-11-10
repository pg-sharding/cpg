/* Untimed valid-vector checks of the installed GIN consistent dispatcher. */
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

#ifndef EXPECT_TRI_CACHE
#error EXPECT_TRI_CACHE must identify the exact installed source variant
#endif
#ifndef EXPECT_CONSECUTIVE_BUDGET
#error EXPECT_CONSECUTIVE_BUDGET must be zero or 64 for the installed variant
#endif
#if EXPECT_CONSECUTIVE_BUDGET != 0 && EXPECT_CONSECUTIVE_BUDGET != 64
#error Unsupported diagnostic budget
#endif

PG_MODULE_MAGIC;
PG_FUNCTION_INFO_V1(gin_cache_budget_oracle);

typedef GinTernaryValue (*TriFunction) (GinScanKey key);

typedef struct BudgetKey
{
	GinScanKeyData key;
	MemoryContext context;
	TriFunction initial;
	TriFunction fallback;
	bool		allocated;
	bool		budget_eligible;
} BudgetKey;

typedef struct BudgetStats
{
	uint64		calls;
	uint64		transitions;
	uint64		initializations;
	uint64		context_resets;
	uint64		returns[3];
} BudgetStats;

static void
initialize_key(BudgetKey *test, GinState *state, TSQuery query, bool hidden,
			   BudgetStats *stats)
{
	MemoryContext old = MemoryContextSwitchTo(test->context);
	GinScanKey key = &test->key;
	int32		nquery = 0;
	bool	   *partial = NULL;
	bool	   *nulls = NULL;
	Pointer    *extra = NULL;
	int32		mode = GIN_SEARCH_MODE_DEFAULT;

	MemSet(key, 0, sizeof(*key));
	key->query = PointerGetDatum(query);
	key->queryValues = (Datum *) DatumGetPointer(FunctionCall7Coll(&state->extractQueryFn[0],
		state->supportCollation[0], key->query, PointerGetDatum(&nquery), UInt16GetDatum(1),
		PointerGetDatum(&partial), PointerGetDatum(&extra), PointerGetDatum(&nulls),
		PointerGetDatum(&mode)));
	if (nquery < 1 || nquery + (hidden ? 1 : 0) > 9)
		elog(ERROR, "budget oracle requires one to nine valid extracted entries");
	key->nuserentries = nquery;
	key->nentries = nquery;
	key->attnum = 1;
	key->strategy = 1;
	key->searchMode = mode;
	key->extra_data = extra;
	key->queryCategories = palloc0_array(GinNullCategory, nquery);
	key->entryRes = palloc0_array(GinTernaryValue, nquery + (hidden ? 1 : 0));
	ginInitConsistentFunction(state, key);
	if (hidden)
		key->nentries++;
#if EXPECT_TRI_CACHE
	test->allocated = (key->triCache != NULL);
#else
	test->allocated = false;
#endif
	if (test->allocated != (EXPECT_TRI_CACHE && nquery <= 8))
		elog(ERROR, "unexpected builtin cache eligibility in budget oracle");
	test->initial = key->triConsistentFn;
	test->fallback = NULL;
	test->budget_eligible = test->allocated && key->nentries <= 8 &&
		EXPECT_CONSECUTIVE_BUDGET == 64;
	stats->initializations++;
	MemoryContextSwitchTo(old);
}

static void
create_key(BudgetKey *test, GinState *state, TSQuery query, bool hidden,
		   BudgetStats *stats)
{
	MemSet(test, 0, sizeof(*test));
	test->context = AllocSetContextCreate(CurrentMemoryContext,
										 "valid budget key", ALLOCSET_DEFAULT_SIZES);
	initialize_key(test, state, query, hidden, stats);
}

static void
step(BudgetKey *test, GinState *state, int input, bool sentinel,
	 bool disabled, BudgetStats *stats)
{
	GinScanKey key = &test->key;
	GinTernaryValue expected;
	GinTernaryValue actual;

	for (uint32 i = 0; i < key->nentries; i++)
		key->entryRes[i] = (GinTernaryValue) input;
	expected = DatumGetGinTernaryValue(FunctionCall7Coll(&state->triConsistentFn[0],
		state->supportCollation[0], PointerGetDatum(key->entryRes), UInt16GetDatum(key->strategy),
		key->query, Int32GetDatum(key->nuserentries), PointerGetDatum(key->extra_data),
		PointerGetDatum(key->queryValues), PointerGetDatum(key->queryCategories)));
	key->recheckCurItem = sentinel;
	actual = key->triConsistentFn(key);
	if (actual != expected || key->recheckCurItem != sentinel)
		elog(ERROR, "installed budget dispatch changed native result or recheck");
	if (actual != GIN_FALSE && actual != GIN_TRUE && actual != GIN_MAYBE)
		elog(ERROR, "native callback returned an invalid ternary value");
	if (disabled && test->budget_eligible)
	{
		if (key->triConsistentFn == test->initial)
			elog(ERROR, "memo dispatch did not switch on consecutive miss 64");
		if (test->fallback == NULL)
		{
			test->fallback = key->triConsistentFn;
			stats->transitions++;
		}
		else if (key->triConsistentFn != test->fallback)
			elog(ERROR, "disabled memo dispatch was not permanent for this key");
	}
	else if (key->triConsistentFn != test->initial)
		elog(ERROR, "memo dispatch switched before its declared boundary");
	stats->calls++;
	stats->returns[(int) actual]++;
	CHECK_FOR_INTERRUPTS();
}

Datum
gin_cache_budget_oracle(PG_FUNCTION_ARGS)
{
	Relation index = index_open(PG_GETARG_OID(0), AccessShareLock);
	TSQuery query = PG_GETARG_TSQUERY(1);
	bool		hidden = PG_GETARG_BOOL(2);
	GinState state;
	BudgetStats stats;
	BudgetKey a;
	BudgetKey b;
	int			nuserentries = 0;
	uint32		nentries = 0;
	bool		allocated = false;
	bool		eligible = false;
	StringInfoData report;

	if (index->rd_rel->relam != GIN_AM_OID)
		elog(ERROR, "budget oracle expects an ordinary builtin tsvector GIN index");
	initGinState(&state, index);
	MemSet(&stats, 0, sizeof(stats));
	for (int sentinel = 0; sentinel < 2; sentinel++)
	{
		/* Calls 1..63 remain memoized; 64 switches; repeat after 65. */
		create_key(&a, &state, query, hidden, &stats);
		nuserentries = a.key.nuserentries;
		nentries = a.key.nentries;
		allocated = a.allocated;
		eligible = a.budget_eligible;
		for (int i = 0; i < 65; i++)
			step(&a, &state, i % 3, sentinel, i >= 63, &stats);
		for (int i = 0; i < 8; i++)
			step(&a, &state, 1, sentinel, true, &stats);
		MemoryContextDelete(a.context);

		/* A hit after miss 63 resets the next full run of 63/64 misses. */
		create_key(&a, &state, query, hidden, &stats);
		for (int i = 0; i < 63; i++)
			step(&a, &state, i % 3, sentinel, false, &stats);
		step(&a, &state, 2, sentinel, false, &stats);
		for (int i = 0; i < 63; i++)
			step(&a, &state, i % 3, sentinel, false, &stats);
		step(&a, &state, 0, sentinel, true, &stats);
		step(&a, &state, 0, sentinel, true, &stats);
		step(&a, &state, 1, sentinel, true, &stats);
		MemoryContextDelete(a.context);

		/* Cumulative misses exceed 64, but every miss is followed by a hit. */
		create_key(&a, &state, query, hidden, &stats);
		for (int i = 0; i < 96; i++)
		{
			step(&a, &state, i % 3, sentinel, false, &stats);
			step(&a, &state, i % 3, sentinel, false, &stats);
		}
		MemoryContextDelete(a.context);

		/* One disabled key cannot change a live independent key's budget. */
		create_key(&a, &state, query, hidden, &stats);
		for (int i = 0; i < 64; i++)
			step(&a, &state, i % 3, sentinel, i >= 63, &stats);
		create_key(&b, &state, query, hidden, &stats);
		step(&b, &state, 0, sentinel, false, &stats);
		step(&a, &state, 0, sentinel, true, &stats);
		for (int i = 1; i < 64; i++)
			step(&b, &state, i % 3, sentinel, i >= 63, &stats);

		/* Match keyCtx reset/rebuild lifetime, without claiming index_rescan. */
		MemoryContextReset(b.context);
		stats.context_resets++;
		initialize_key(&b, &state, query, hidden, &stats);
		for (int i = 0; i < 64; i++)
			step(&b, &state, i % 3, sentinel, i >= 63, &stats);
		MemoryContextDelete(b.context);
		MemoryContextDelete(a.context);
	}
	if (stats.calls != 1176 || stats.initializations != 12 || stats.context_resets != 2 ||
		stats.transitions != (eligible ? 10 : 0))
		elog(ERROR, "budget oracle finite protocol count mismatch");
	index_close(index, AccessShareLock);
	PG_FREE_IF_COPY(query, 1);
	initStringInfo(&report);
	appendStringInfo(&report, "{\"status\":\"PASS_INSTALLED_CONSECUTIVE_BUDGET\","
		"\"nuserentries\":%d,\"nentries\":%u,\"cache_allocated\":%s,"
		"\"declared_budget\":%d,\"budget_eligible\":%s,\"calls\":" UINT64_FORMAT ","
		"\"dispatch_transitions\":" UINT64_FORMAT ",\"initializations\":" UINT64_FORMAT ","
		"\"context_resets\":" UINT64_FORMAT ",\"return_counts\":{\"false\":" UINT64_FORMAT ","
		"\"true\":" UINT64_FORMAT ",\"maybe\":" UINT64_FORMAT "},"
		"\"phase_calls\":{\"continuous\":146,\"hit_after_63\":260,"
		"\"interleaved\":384,\"independence_and_context_reset\":386},\"timing_samples\":0}",
		nuserentries, nentries, allocated ? "true" : "false", EXPECT_CONSECUTIVE_BUDGET,
		eligible ? "true" : "false", stats.calls, stats.transitions, stats.initializations,
		stats.context_resets, stats.returns[(int) GIN_FALSE], stats.returns[(int) GIN_TRUE],
		stats.returns[(int) GIN_MAYBE]);
	PG_RETURN_TEXT_P(cstring_to_text(report.data));
}
