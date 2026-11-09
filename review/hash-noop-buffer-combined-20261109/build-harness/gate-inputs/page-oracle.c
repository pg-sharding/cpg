/* Test-only wrapper appended to the complete, unchanged hashsearch TU.
 * No timings; the independent oracle is a linear walk over generated keys.
 */
#include "production-hashsearch.c"
#include "catalog/pg_type_d.h"
#include "fmgr.h"
#include "utils/builtins.h"
#include <sys/mman.h>
PG_MODULE_MAGIC;

static int
keycmp(const void *a, const void *b)
{
    uint32 x = *(const uint32 *) a, y = *(const uint32 *) b;
    return (x > y) - (x < y);
}

PG_FUNCTION_INFO_V1(hash_noop_page_oracle);
Datum
hash_noop_page_oracle(PG_FUNCTION_ARGS)
{
    const int sizes[] = {0, 1, 8, 32, 128, 400};
    uint32 keys[400], targets[1208];
    char *mapping = mmap(NULL, 3 * BLCKSZ, PROT_NONE,
                         MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    Page page;
    char saved[BLCKSZ];
    TupleDesc desc;
    HashScanOpaque so, expected;
    IndexScanDescData scan;
    uint64 checks = 0, saved_items = 0;
    int z, shape, flags, mask, q, dir, n, i, ntargets;
    if (mapping == MAP_FAILED ||
        mprotect(mapping + BLCKSZ, BLCKSZ, PROT_READ | PROT_WRITE))
        elog(ERROR, "oracle page guard mapping failed");
    page = mapping + BLCKSZ;
    desc = CreateTemplateTupleDesc(1);
    TupleDescInitEntry(desc, 1, "key", INT4OID, -1, 0);
    so = palloc(sizeof(HashScanOpaqueData));
    expected = palloc(sizeof(HashScanOpaqueData));
    memset(&scan, 0, sizeof(scan));
    scan.opaque = so;
    for (z = 0; z < lengthof(sizes); z++)
    for (shape = 0; shape < 8; shape++)
    {
        n = sizes[z];
        for (i = 0; i < n; i++)
        {
            switch (shape)
            {
                case 0: keys[i] = (uint32) i * (UINT_MAX / Max(n, 1)); break;
                case 1: keys[i] = (uint32) (i / 7); break;
                case 2: keys[i] = 0; break;
                case 3: keys[i] = UINT_MAX; break;
                case 4: keys[i] = 0x7fffffffU; break;
                case 5: keys[i] = 0x80000000U; break;
                case 6: keys[i] = 0x7fffffe0U + (i % 64); break;
                default: keys[i] = (uint32) i * 2654435761U; break;
            }
        }
        qsort(keys, n, sizeof(uint32), keycmp);
        ntargets = 0;
        targets[ntargets++] = 0; targets[ntargets++] = UINT_MAX;
        targets[ntargets++] = 0x7fffffffU; targets[ntargets++] = 0x80000000U;
        for (i = 0; i < n; i++)
        {
            targets[ntargets++] = keys[i];
            targets[ntargets++] = keys[i] - 1;
            targets[ntargets++] = keys[i] + 1;
        }
        for (mask = 0; mask < 4; mask++)
        {
            PageInit(page, BLCKSZ, MAXALIGN(sizeof(HashPageOpaqueData)));
            for (i = 0; i < n; i++)
            {
                Datum val = UInt32GetDatum(keys[i]);
                bool isnull = false;
                IndexTuple tup = index_form_tuple(desc, &val, &isnull);
                ItemPointerSet(&tup->t_tid, (BlockNumber) (i + 1), (i % 37) + 1);
                if ((mask & 1) && i % 3 == 0)
                    tup->t_info |= INDEX_MOVED_BY_SPLIT_MASK;
                if (PageAddItemExtended(page, tup, IndexTupleSize(tup),
                                        InvalidOffsetNumber, 0) != i + 1)
                    elog(ERROR, "oracle page insertion failed");
                if ((mask & 2) && i % 5 == 0)
                    ItemIdMarkDead(PageGetItemId(page, i + 1));
                pfree(tup);
            }
            memcpy(saved, page, BLCKSZ);
            for (flags = 0; flags < 8; flags++)
            for (q = 0; q < ntargets; q++)
            for (dir = 0; dir < 2; dir++)
            {
                int start, cursor, out, want, got;
                uint32 target = targets[q];
                CHECK_FOR_INTERRUPTS();
                memset(so, 0x5a, sizeof(HashScanOpaqueData));
                so->hashso_sk_hash = target;
                so->hashso_buc_populated = (flags & 1) != 0;
                so->hashso_buc_split = (flags & 2) != 0;
                scan.ignore_killed_tuples = (flags & 4) != 0;
                memcpy(expected, so, sizeof(HashScanOpaqueData));
                /* Start at the independent linear directional bound. */
                if (dir == 0)
                {
                    for (start = 0; start < n && keys[start] < target; start++);
                    start++;
                }
                else
                {
                    for (start = n; start > 0 && keys[start - 1] > target; start--);
                }
                out = dir == 0 ? 0 : MaxIndexTuplesPerPage;
                for (cursor = start; cursor >= 1 && cursor <= n;
                     cursor += dir == 0 ? 1 : -1)
                {
                    int k = cursor - 1;
                    bool moved = (mask & 1) && k % 3 == 0;
                    bool dead = (mask & 2) && k % 5 == 0;
                    HashScanPosItem *item;
                    if (((flags & 1) && !(flags & 2) && moved) ||
                        ((flags & 4) && dead))
                        continue;
                    if (keys[k] != target)
                        break;
                    if (dir != 0) out--;
                    item = &expected->currPos.items[out];
                    ItemPointerSet(&item->heapTid, (BlockNumber) (k + 1), (k % 37) + 1);
                    item->indexOffset = cursor;
                    if (dir == 0) out++;
                    saved_items++;
                }
                want = out;
                got = _hash_load_qualified_items(&scan, page, start,
                         dir == 0 ? ForwardScanDirection : BackwardScanDirection);
                if (got != want || memcmp(so, expected, sizeof(HashScanOpaqueData)) ||
                    memcmp(page, saved, BLCKSZ))
                    elog(ERROR, "loader oracle mismatch n=%d shape=%d mask=%d flags=%d key=%u dir=%d got=%d want=%d",
                         n, shape, mask, flags, target, dir, got, want);
                checks++;
            }
        }
    }
    munmap(mapping, 3 * BLCKSZ); FreeTupleDesc(desc); pfree(so); pfree(expected);
    PG_RETURN_TEXT_P(cstring_to_text(psprintf("{\"status\":\"PASS\",\"page_cases\":%llu,\"saved_items_checked\":%llu,\"complete_TU\":true,\"timing\":false}",
                (unsigned long long) checks, (unsigned long long) saved_items)));
}
