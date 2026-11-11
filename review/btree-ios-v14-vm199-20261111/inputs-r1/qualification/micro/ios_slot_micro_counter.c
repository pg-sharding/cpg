/* Actual slot-fill helper micro; this is not the AM or a whole SQL scan. */
#include "postgres.h"

#include "access/itup.h"
#include "access/tableam_indexscan.h"
#include "catalog/pg_type_d.h"
#include "fmgr.h"
#include "utils/builtins.h"

PG_MODULE_MAGIC;
PG_FUNCTION_INFO_V1(ios_slot_micro);

/* Retain the actual inline helper without specializing it for this fixture. */
static pg_noinline void
micro_fill(IndexScanDesc scan, TupleTableSlot *slot)
{
	tableam_index_fill_ios_slot(scan, slot);
	/* All roles retain the real call/return cost of the production caller. */
	__asm__ __volatile__("" ::: "memory");
}

Datum
ios_slot_micro(PG_FUNCTION_ARGS)
{
	int natts = PG_GETARG_INT32(0);
	int64 loops = PG_GETARG_INT64(1);
	int reuse = PG_GETARG_INT32(2);
	bool enable_cache = PG_GETARG_BOOL(3);
	bool varlen = PG_GETARG_BOOL(4);
	bool with_nulls = PG_GETARG_BOOL(5);
	TupleDesc desc;
	TupleTableSlot *slot;
	IndexScanDescData scan;
	Datum values[32];
	bool nulls[32];
	int remaining = 0;
	uint64 checksum = 0;
#ifdef MICRO_WITH_CACHE
	IndexTupleDeformCache cache;
#endif

	if (natts < 1 || natts > 32 || loops < 1 || loops > 20000000 ||
		reuse < 1 || reuse > 100000)
		ereport(ERROR, (errmsg("out-of-range slot micro argument")));
	desc = CreateTemplateTupleDesc(natts);
	for (int i = 0; i < natts; i++)
	{
		TupleDescInitEntry(desc, i + 1, NULL,
						  varlen ? TEXTOID : INT4OID, -1, 0);
		values[i] = varlen ?
			CStringGetTextDatum("abcdefghijklmnopqrstuvwxyz012345") :
			Int32GetDatum(i + 42);
		nulls[i] = with_nulls && i % 7 == 3;
	}
	TupleDescFinalize(desc);
	memset(&scan, 0, sizeof(scan));
	scan.xs_itupdesc = desc;
	scan.xs_itup = index_form_tuple(desc, values, nulls);
	slot = MakeSingleTupleTableSlot(desc, &TTSOpsVirtual);
#ifdef MICRO_WITH_CACHE
	memset(&cache, 0, sizeof(cache));
	cache.values = palloc(sizeof(Datum) * natts);
	cache.isnull = palloc(sizeof(bool) * natts);
#ifdef MICRO_CACHED_NATTS
	cache.natts = natts;
#endif
#ifdef MICRO_PAGE_CACHE
	/* B-tree's preserved AM bit is the actual post-visibility applicability. */
	cache.required_flags = INDEX_AM_RESERVED_BIT;
	scan.xs_itup->t_info |= INDEX_AM_RESERVED_BIT;
#endif
	/* Match v3 descriptor eligibility; attachment itself is a separate input. */
	scan.xs_itupcache = enable_cache && natts > 1 ? &cache : NULL;
#else
	(void) enable_cache;
#endif
	for (int64 i = 0; i < loops; i++)
	{
		if (remaining == 0)
		{
			remaining = reuse;
#ifdef MICRO_WITH_CACHE
			if (scan.xs_itupcache != NULL)
#ifdef MICRO_PAGE_CACHE
				cache.itup = NULL;
#else
				cache.valid = false;
#endif
#endif
		}
		remaining--;
		micro_fill(&scan, slot);
		/* Keep group bookkeeping in baseline builds, too. */
		__asm__ __volatile__("" : : "g"(slot->tts_values),
							 "g"(slot->tts_isnull), "g"(remaining) : "memory");
		if (slot->tts_isnull[natts - 1])
			checksum++;
		else if (varlen)
			checksum += VARSIZE_ANY_EXHDR(DatumGetPointer(slot->tts_values[natts - 1]));
		else
			checksum += DatumGetInt32(slot->tts_values[natts - 1]);
	}
	ExecDropSingleTupleTableSlot(slot);
	PG_RETURN_INT64((int64) checksum);
}
