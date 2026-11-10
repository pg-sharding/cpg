/* Untimed vector-repetition diagnostic for the exact builtin tsvector callbacks. */
#include "postgres.h"
#include "fmgr.h"
#include "access/gin_private.h"
#include "lib/stringinfo.h"
#include "utils/builtins.h"
#include "utils/fmgrprotos.h"
#include "utils/memutils.h"

PG_MODULE_MAGIC;
PG_FUNCTION_INFO_V1(gin_vector_probe_bool);
PG_FUNCTION_INFO_V1(gin_vector_probe_tri);
PG_FUNCTION_INFO_V1(gin_vector_probe_reset);
PG_FUNCTION_INFO_V1(gin_vector_probe_report);

#define PROBE_MAX_ENTRIES 8

typedef struct ProbeState
{
	uint64 epoch;
	bool valid;
	int n;
	Datum query;
	Pointer extra;
	StrategyNumber strategy;
	Oid collation;
	GinTernaryValue previous[PROBE_MAX_ENTRIES];
} ProbeState;

typedef struct ProbeCounts
{
	uint64 calls;
	uint64 eligible;
	uint64 context_changes;
	uint64 consecutive_same_vector;
	uint64 returned[3];
	uint64 recheck_true;
} ProbeCounts;

static uint64 epoch = 1;
static ProbeCounts counters[2];

static void
observe(FunctionCallInfo fcinfo, int which)
{
	ProbeCounts *count = &counters[which];
	ProbeState *state = (ProbeState *) fcinfo->flinfo->fn_extra;
	GinTernaryValue *check = (GinTernaryValue *) PG_GETARG_POINTER(0);
	int n = PG_GETARG_INT32(3);
	Datum query = PG_GETARG_DATUM(2);
	Pointer extra = PG_GETARG_POINTER(4);
	StrategyNumber strategy = PG_GETARG_UINT16(1);
	Oid collation = PG_GET_COLLATION();
	bool same_context;

	count->calls++;
	if (!state)
	{
		state = MemoryContextAllocZero(fcinfo->flinfo->fn_mcxt, sizeof(ProbeState));
		fcinfo->flinfo->fn_extra = state;
	}
	if (n < 0 || n > PROBE_MAX_ENTRIES)
	{
		state->valid = false;
		return;
	}
	count->eligible++;
	same_context = (state->valid && state->epoch == epoch && state->n == n &&
		state->query == query && state->extra == extra &&
		state->strategy == strategy && state->collation == collation);
	if (same_context)
	{
		if (memcmp(state->previous, check, n * sizeof(GinTernaryValue)) == 0)
			count->consecutive_same_vector++;
	}
	else
		count->context_changes++;
	state->valid = true;
	state->epoch = epoch;
	state->n = n;
	state->query = query;
	state->extra = extra;
	state->strategy = strategy;
	state->collation = collation;
	memcpy(state->previous, check, n * sizeof(GinTernaryValue));
}

Datum
gin_vector_probe_bool(PG_FUNCTION_ARGS)
{
	Datum result;

	observe(fcinfo, 0);
	/* The builtin does not consult flinfo->fn_extra; source reviewed separately. */
	result = gin_tsquery_consistent(fcinfo);
	counters[0].returned[DatumGetBool(result) ? 1 : 0]++;
	if (*(bool *) PG_GETARG_POINTER(5))
		counters[0].recheck_true++;
	return result;
}

Datum
gin_vector_probe_tri(PG_FUNCTION_ARGS)
{
	Datum result;
	GinTernaryValue value;

	observe(fcinfo, 1);
	result = gin_tsquery_triconsistent(fcinfo);
	value = DatumGetGinTernaryValue(result);
	if (value > GIN_MAYBE)
		elog(ERROR, "unexpected builtin ternary value");
	counters[1].returned[(int) value]++;
	return result;
}

Datum
gin_vector_probe_reset(PG_FUNCTION_ARGS)
{
	MemSet(counters, 0, sizeof(counters));
	epoch++;
	PG_RETURN_VOID();
}

Datum
gin_vector_probe_report(PG_FUNCTION_ARGS)
{
	StringInfoData result;

	initStringInfo(&result);
	appendStringInfoString(&result, "{\"scope\":\"untimed known-builtin callback counts; no cached results\",\"max_entries\":8,\"callbacks\":{");
	for (int i = 0; i < 2; i++)
	{
		ProbeCounts *c = &counters[i];

		appendStringInfo(&result,
			"%s\"%s\":{\"calls\":" UINT64_FORMAT ",\"eligible\":" UINT64_FORMAT
			",\"context_changes\":" UINT64_FORMAT ",\"consecutive_same_vector\":" UINT64_FORMAT
			",\"false\":" UINT64_FORMAT ",\"true\":" UINT64_FORMAT ",\"maybe\":" UINT64_FORMAT
			",\"recheck_true\":" UINT64_FORMAT "}",
			i ? "," : "", i ? "tri" : "bool", c->calls, c->eligible,
			c->context_changes, c->consecutive_same_vector,
			c->returned[0], c->returned[1], c->returned[2], c->recheck_true);
	}
	appendStringInfoString(&result, "}}");
	PG_RETURN_TEXT_P(cstring_to_text(result.data));
}
