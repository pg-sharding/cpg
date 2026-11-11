/*-------------------------------------------------------------------------
 *
 * tableam_indexscan.c
 *	  Helpers for table AM index scan callbacks.
 *
 *
 * Table AMs can use these functions to implement xs_getnext_slot callbacks.
 * See access/tableam.h.
 *
 * Portions Copyright (c) 1996-2026, PostgreSQL Global Development Group
 * Portions Copyright (c) 1994, Regents of the University of California
 *
 *
 * IDENTIFICATION
 *	  src/backend/access/table/tableam_indexscan.c
 *
 *-------------------------------------------------------------------------
 */

#include "postgres.h"

#include "access/tableam_indexscan.h"
#include "utils/builtins.h"

/*
 * Handle an attached optional deformation cache out of line.  Keeping this
 * independent of the ordinary fill path avoids exposing cache-copy state to
 * the caller when the index AM did not attach a cache.
 *
 * The caller has already selected IndexTuple format over any HeapTuple,
 * checked xs_itup, and supplied the current non-NULL xs_itupcache.  Cache
 * identity, invalidation and independently owned raw arrays retain the same
 * contract as the inline fill helper.
 */
pg_noinline void
tableam_index_fill_ios_cached_slot(IndexScanDesc scan, TupleTableSlot *slot,
				  IndexTupleDeformCache *cache)
{
	bool		cache_hit = cache->itup == scan->xs_itup;

	Assert(scan->xs_hitup == NULL);
	Assert(scan->xs_itup != NULL);
	Assert(cache != NULL && cache == scan->xs_itupcache);
	Assert(slot->tts_tupleDescriptor->natts == scan->xs_itupdesc->natts);

	/* A cached identity was qualified before and remains immutable. */
	if (likely(cache_hit) ||
		(scan->xs_itup->t_info & cache->required_flags) == cache->required_flags)
	{
		int			natts = cache->natts;

		Assert(natts == scan->xs_itupdesc->natts);

		/* Heap representation and name conversion retain their full path. */
		if (cache_hit && scan->xs_name_cstring_attnums == NULL &&
			ExecTryReplaceVirtualTupleFromArrays(slot, cache->values,
											cache->isnull, natts))
			return;

		ExecClearTuple(slot);
		if (!cache_hit)
		{
			index_deform_tuple(scan->xs_itup, scan->xs_itupdesc,
							   cache->values, cache->isnull);
			cache->itup = scan->xs_itup;
		}
		/* Use constant sizes for common short tuple descriptors. */
		switch (natts)
		{
			case 2:
				memcpy(slot->tts_values, cache->values, sizeof(Datum) * 2);
				memcpy(slot->tts_isnull, cache->isnull, sizeof(bool) * 2);
				break;
			case 3:
				memcpy(slot->tts_values, cache->values, sizeof(Datum) * 3);
				memcpy(slot->tts_isnull, cache->isnull, sizeof(bool) * 3);
				break;
			case 4:
				memcpy(slot->tts_values, cache->values, sizeof(Datum) * 4);
				memcpy(slot->tts_isnull, cache->isnull, sizeof(bool) * 4);
				break;
			default:
				memcpy(slot->tts_values, cache->values, sizeof(Datum) * natts);
				memcpy(slot->tts_isnull, cache->isnull, sizeof(bool) * natts);
				break;
		}
	}
	else
	{
		ExecClearTuple(slot);
		index_deform_tuple(scan->xs_itup, scan->xs_itupdesc,
						   slot->tts_values, slot->tts_isnull);
	}

	/* Name conversion and non-builtin slot protocols keep their full path. */
	if (unlikely(scan->xs_name_cstring_attnums != NULL))
		tableam_index_fill_ios_names(scan, slot);

	ExecStoreVirtualTuple(slot);
}

/*
 * Copy all name columns stored as cstrings back into NAMEDATALEN bytes of
 * xs_name_cstring_buf.
 *
 * Called by tableam_index_fill_ios_slot (kept out of line, since it's needed
 * only by index-only scans of indexes on "name" columns).
 */
pg_attribute_cold void
tableam_index_fill_ios_names(IndexScanDesc scan, TupleTableSlot *slot)
{
	for (int idx = 0; idx < scan->xs_name_cstring_count; idx++)
	{
		int			attnum = scan->xs_name_cstring_attnums[idx];
		Name		name;

		/* skip null Datums */
		if (slot->tts_isnull[attnum])
			continue;

		/* use namestrcpy to zero-pad all trailing bytes */
		name = (Name) (scan->xs_name_cstring_buf + idx * NAMEDATALEN);
		namestrcpy(name, DatumGetCString(slot->tts_values[attnum]));
		slot->tts_values[attnum] = NameGetDatum(name);
	}
}
