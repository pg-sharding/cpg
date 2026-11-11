/* Correctness only: compare the real old protocol with the new V12 primitive. */
#include "postgres.h"
#include "fmgr.h"
#include "access/htup_details.h"
#include "access/itup.h"
#include "access/tableam_indexscan.h"
#include "catalog/pg_type_d.h"
#include "executor/tuptable.h"
#include "utils/builtins.h"
#include "utils/memutils.h"

PG_MODULE_MAGIC;
PG_FUNCTION_INFO_V1(ios_v12_ownership_oracle);
static uint64 checks, positive, materialized, custom, fullhelper, heappriority, names;
static int custom_clears;
#define CHECK(c) do { checks++; if (!(c)) elog(ERROR, "V12 ownership check failed at line %d: %s", __LINE__, #c); } while (0)

static void
old_replace(TupleTableSlot *slot, const Datum *values, const bool *nulls, int n)
{
    ExecClearTuple(slot);
    memcpy(slot->tts_values, values, n * sizeof(Datum));
    memcpy(slot->tts_isnull, nulls, n * sizeof(bool));
    ExecStoreVirtualTuple(slot);
}

static void
compare(TupleTableSlot *a, TupleTableSlot *b, const Datum *values, const bool *nulls, int n)
{
    CHECK(a->tts_ops == b->tts_ops);
    CHECK(a->tts_flags == b->tts_flags);
    CHECK(a->tts_nvalid == b->tts_nvalid && a->tts_nvalid == n);
    CHECK(a->tts_tupleDescriptor == b->tts_tupleDescriptor);
    CHECK(a->tts_first_nonguaranteed == b->tts_first_nonguaranteed);
    CHECK(a->tts_mcxt == b->tts_mcxt);
    CHECK(a->tts_tableOid == b->tts_tableOid);
    CHECK(memcmp(&a->tts_tid, &b->tts_tid, sizeof(ItemPointerData)) == 0);
    CHECK(memcmp(a->tts_values, b->tts_values, n * sizeof(Datum)) == 0);
    CHECK(memcmp(a->tts_isnull, b->tts_isnull, n * sizeof(bool)) == 0);
    CHECK(memcmp(a->tts_values, values, n * sizeof(Datum)) == 0);
    CHECK(memcmp(a->tts_isnull, nulls, n * sizeof(bool)) == 0);
    CHECK(a->tts_values != values && b->tts_values != values);
    CHECK(a->tts_isnull != nulls && b->tts_isnull != nulls);
}

static TupleDesc
descriptor(int n, Oid type)
{
    TupleDesc d = CreateTemplateTupleDesc(n);
    for (int i = 0; i < n; i++)
        TupleDescInitEntry(d, i + 1, "v", type, -1, 0);
    TupleDescFinalize(d);
    return d;
}

static void
custom_clear(TupleTableSlot *slot)
{
    custom_clears++;
    TTSOpsVirtual.clear(slot);
}

/* Exact custom ops pointer must be rejected, even with virtual behavior. */
static void custom_init(TupleTableSlot *slot) { (void) slot; }
static void custom_release(TupleTableSlot *slot) { (void) slot; }

static void
snapshot_rejection(TupleTableSlot *slot, const Datum *values, const bool *nulls, int n)
{
    TupleTableSlot saved;
    Datum before[32];
    bool bn[32];
    char *data = NULL;
    int clears = custom_clears;
    memcpy(&saved, slot, sizeof(saved));
    memcpy(before, slot->tts_values, n * sizeof(Datum));
    memcpy(bn, slot->tts_isnull, n * sizeof(bool));
    if (TTS_IS_VIRTUAL(slot)) data = ((VirtualTupleTableSlot *) slot)->data;
    CHECK(!ExecTryReplaceVirtualTupleFromArrays(slot, values, nulls, n));
    CHECK(memcmp(&saved, slot, sizeof(saved)) == 0);
    CHECK(memcmp(before, slot->tts_values, n * sizeof(Datum)) == 0);
    CHECK(memcmp(bn, slot->tts_isnull, n * sizeof(bool)) == 0);
    CHECK(custom_clears == clears);
    if (TTS_IS_VIRTUAL(slot)) CHECK(((VirtualTupleTableSlot *) slot)->data == data);
}

static void
primitive_cells(int n, bool use_text)
{
    TupleDesc d = descriptor(n, use_text ? TEXTOID : INT4OID);
    TupleTableSlot *a = MakeSingleTupleTableSlot(d, &TTSOpsVirtual);
    TupleTableSlot *b = MakeSingleTupleTableSlot(d, &TTSOpsVirtual);
    Datum values[32], saved[32];
    bool nulls[32], sn[32];
    for (int rep = 0; rep < 12; rep++)
    {
        uint16 flags = (rep & 1 ? TTS_FLAG_FIXED : 0) |
                       (rep & 2 ? TTS_FLAG_OBEYS_NOT_NULL_CONSTRAINTS : 0);
        for (int i = 0; i < n; i++)
        {
            nulls[i] = (rep + i) % 4 == 0;
            /* Raw NULL Datums initialized too; never dereferenced. */
            values[i] = nulls[i] ? (Datum) (0xfedcba00UL + i + rep) :
                (use_text ? CStringGetTextDatum(psprintf("source-%d-%d", rep, i)) : Int32GetDatum(1000 + rep * n + i));
        }
        memcpy(saved, values, n * sizeof(Datum)); memcpy(sn, nulls, n * sizeof(bool));
        if (rep % 3 == 0) { ExecClearTuple(a); ExecClearTuple(b); }
        a->tts_flags = (a->tts_flags & ~TTS_FLAGS_TRANSIENT & ~TTS_FLAG_FIXED & ~TTS_FLAG_OBEYS_NOT_NULL_CONSTRAINTS) | flags | (rep % 3 == 0 ? TTS_FLAG_EMPTY : 0);
        b->tts_flags = a->tts_flags;
        a->tts_first_nonguaranteed = b->tts_first_nonguaranteed = rep % (n + 1);
        a->tts_tableOid = b->tts_tableOid = 70000 + rep;
        ItemPointerSet(&a->tts_tid, 33 + rep, 7); b->tts_tid = a->tts_tid;
        a->tts_nvalid = b->tts_nvalid = rep % (n + 1);
        for (int i = 0; i < n; i++)
        {
            a->tts_values[i] = b->tts_values[i] = Int32GetDatum(-333);
            a->tts_isnull[i] = b->tts_isnull[i] = !nulls[i];
        }
        old_replace(a, values, nulls, n);
        CHECK(ExecTryReplaceVirtualTupleFromArrays(b, values, nulls, n));
        compare(a, b, values, nulls, n); positive++;
        CHECK(memcmp(saved, values, n * sizeof(Datum)) == 0 && memcmp(sn, nulls, n * sizeof(bool)) == 0);
        /* Consumer mutates arrays and private byref copies, never the cache. */
        for (int i = 0; i < n; i++)
        {
            a->tts_values[i] = b->tts_values[i] = Int32GetDatum(-99);
            a->tts_isnull[i] = b->tts_isnull[i] = !nulls[i];
        }
        if (use_text)
        {
            old_replace(a, values, nulls, n); old_replace(b, values, nulls, n);
            ExecMaterializeSlot(a); ExecMaterializeSlot(b);
            CHECK(TTS_SHOULDFREE(a) && TTS_SHOULDFREE(b));
            for (int i = 0; i < n; i++) if (!nulls[i])
            {
                CHECK(a->tts_values[i] != values[i] && b->tts_values[i] != values[i]);
                VARDATA(DatumGetTextP(a->tts_values[i]))[0] = 'A';
                VARDATA(DatumGetTextP(b->tts_values[i]))[0] = 'B';
                CHECK(VARDATA(DatumGetTextP(values[i]))[0] == 's');
            }
            snapshot_rejection(b, values, nulls, n);
            old_replace(a, values, nulls, n);
            /* This is precisely the actual fallback on rejected primitive. */
            old_replace(b, values, nulls, n);
            CHECK(!TTS_SHOULDFREE(a) && !TTS_SHOULDFREE(b));
            CHECK(((VirtualTupleTableSlot *) a)->data == NULL && ((VirtualTupleTableSlot *) b)->data == NULL);
            compare(a, b, values, nulls, n); materialized++;
            /* Real copy/materialization callbacks must remain usable. */
            ExecCopySlot(b, a); CHECK(TTS_SHOULDFREE(b));
            snapshot_rejection(b, values, nulls, n);
            old_replace(b, values, nulls, n); compare(a, b, values, nulls, n);
        }
    }
    ExecDropSingleTupleTableSlot(a); ExecDropSingleTupleTableSlot(b); FreeTupleDesc(d);
}

static void
full_helper_cells(int n)
{
    TupleDesc d = descriptor(n, INT4OID);
    TupleTableSlotOps ops = TTSOpsVirtual;
    TupleTableSlot *a = MakeSingleTupleTableSlot(d, &TTSOpsVirtual);
    TupleTableSlot *b;
    Datum values[32], cv[32]; bool nulls[32], cn[32];
    IndexScanDescData scan; IndexTupleDeformCache cache;
    ops.init = custom_init; ops.release = custom_release; ops.clear = custom_clear;
    b = MakeSingleTupleTableSlot(d, &ops);
    for (int i = 0; i < n; i++) { values[i] = Int32GetDatum(i + 700); nulls[i] = i % 3 == 1; }
    memset(&scan, 0, sizeof(scan)); memset(&cache, 0, sizeof(cache));
    scan.xs_itup = index_form_tuple(d, values, nulls); scan.xs_itupdesc = d;
    scan.xs_itupcache = &cache; cache.values = cv; cache.isnull = cn; cache.natts = n;
    for (int rep = 0; rep < 8; rep++)
    {
        int before;
        snapshot_rejection(b, values, nulls, n); custom++;
        before = custom_clears;
        tableam_index_fill_ios_slot(&scan, b);
        CHECK(custom_clears == before + 1);
        CHECK(b->tts_nvalid == n && !TTS_EMPTY(b));
        for (int i = 0; i < n; i++)
        {
            CHECK(b->tts_isnull[i] == nulls[i]);
            if (!nulls[i]) CHECK(b->tts_values[i] == values[i]);
        }
        CHECK(cache.itup == scan.xs_itup); fullhelper++;
        tableam_index_fill_ios_slot(&scan, a); /* Real qualified hit. */
        for (int i = 0; i < n; i++) CHECK(a->tts_isnull[i] == b->tts_isnull[i]);
    }
    {
        HeapTuple heap;
        TupleTableSlot *heap_slot = MakeSingleTupleTableSlot(d, &TTSOpsHeapTuple);
        for (int i = 0; i < n; i++) { values[i] = Int32GetDatum(i + 9000); nulls[i] = false; }
        heap = heap_form_tuple(d, values, nulls); scan.xs_hitup = heap; scan.xs_hitupdesc = d;
        snapshot_rejection(heap_slot, values, nulls, n);
        ExecStoreHeapTuple(heap, heap_slot, false);
        snapshot_rejection(heap_slot, values, nulls, n);
        tableam_index_fill_ios_slot(&scan, a);
        for (int i = 0; i < n; i++) CHECK(a->tts_values[i] == values[i] && !a->tts_isnull[i]);
        heappriority++; ExecDropSingleTupleTableSlot(heap_slot); heap_freetuple(heap);
    }
    pfree(scan.xs_itup); ExecDropSingleTupleTableSlot(a); ExecDropSingleTupleTableSlot(b); FreeTupleDesc(d);
}

static void
name_cell(void)
{
    TupleDesc ind = descriptor(2, CSTRINGOID), out = descriptor(2, NAMEOID);
    TupleTableSlot *slot = MakeSingleTupleTableSlot(out, &TTSOpsVirtual);
    Datum v[2] = {CStringGetDatum("alpha"), CStringGetDatum("beta")}, cv[2];
    bool nulls[2] = {false, false}, cn[2];
    AttrNumber attnums[2] = {0, 1}; char buf[2 * NAMEDATALEN];
    IndexScanDescData scan; IndexTupleDeformCache cache;
    memset(&scan, 0, sizeof(scan)); memset(&cache, 0, sizeof(cache));
    scan.xs_itup = index_form_tuple(ind, v, nulls); scan.xs_itupdesc = ind; scan.xs_itupcache = &cache;
    cache.values = cv; cache.isnull = cn; cache.natts = 2;
    scan.xs_name_cstring_attnums = attnums; scan.xs_name_cstring_count = 2; scan.xs_name_cstring_buf = buf;
    for (int rep = 0; rep < 8; rep++)
    {
        memset(buf, 0x7f, sizeof(buf));
        tableam_index_fill_ios_slot(&scan, slot);
        CHECK(strcmp(NameStr(*DatumGetName(slot->tts_values[0])), "alpha") == 0);
        CHECK(strcmp(NameStr(*DatumGetName(slot->tts_values[1])), "beta") == 0);
        CHECK(strcmp(DatumGetCString(cv[0]), "alpha") == 0 && strcmp(DatumGetCString(cv[1]), "beta") == 0);
        CHECK(slot->tts_values[0] != cv[0] && slot->tts_values[1] != cv[1]);
        CHECK(buf[6] == 0 && buf[NAMEDATALEN + 5] == 0); names++;
    }
    pfree(scan.xs_itup); ExecDropSingleTupleTableSlot(slot); FreeTupleDesc(ind); FreeTupleDesc(out);
}

Datum
ios_v12_ownership_oracle(PG_FUNCTION_ARGS)
{
    MemoryContext old = CurrentMemoryContext;
    MemoryContext work = AllocSetContextCreate(old, "V12 ownership oracle", ALLOCSET_DEFAULT_SIZES);
    char *result;
    const int widths[] = {2, 3, 4, 8, 32};
    (void) fcinfo;
    checks = positive = materialized = custom = fullhelper = heappriority = names = 0;
    custom_clears = 0;
    MemoryContextSwitchTo(work);
    for (int k = 0; k < (int) lengthof(widths); k++)
    {
        primitive_cells(widths[k], false); primitive_cells(widths[k], true); full_helper_cells(widths[k]);
    }
    name_cell();
    MemoryContextSwitchTo(old);
    result = psprintf("{\"status\":\"PASS\",\"checks\":%llu,\"positive\":%llu,\"materialized\":%llu,\"custom\":%llu,\"fullhelper\":%llu,\"heappriority\":%llu,\"names\":%llu,\"custom_clears\":%d}",
        (unsigned long long) checks, (unsigned long long) positive, (unsigned long long) materialized,
        (unsigned long long) custom, (unsigned long long) fullhelper, (unsigned long long) heappriority,
        (unsigned long long) names, custom_clears);
    MemoryContextDelete(work);
    PG_RETURN_TEXT_P(cstring_to_text(result));
}
