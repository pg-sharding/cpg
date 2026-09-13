# Bypassing cursors in postgres_fdw: benchmark results

## Patch info

- **Patch ID:** 6233
- **Title:** Bypassing cursors in postgres_fdw to enable parallel plans
- **Author:** Rafia Sabih
- **Version:** v17 (2 patches, +2421 -131 lines)
- **URL:** https://commitfest.postgresql.org/patch/6233/

## What it does

Adds `streaming_fetch` option (foreign table/server level). When enabled,
postgres_fdw bypasses cursors and uses `PQsetChunkedRowsMode` + chunked
fetching. This allows the remote server to use parallel query plans
(cursors disable parallelism because partial execution is incompatible
with parallel mode).

When multiple scans share a connection (e.g. joins), results are buffered
in a tuplestore to avoid losing data when switching between queries.

## Setup

- 1 machine, 2 PostgreSQL instances (source:5532 with fdw, target:5533)
- 1M rows in target table t
- Remote configured for parallelism: min_parallel_table_scan_size=0,
  parallel_tuple_cost=0, parallel_setup_cost=0, max_parallel_workers=4

## Results: simple scan (count(*) WHERE id > 1000)

```
 Mode             Execution Time (5 runs, ms)
──────────────────────────────────────────────
 cursor (default)  89, 99, 91, 97, 97    avg: 94.6
 streaming_fetch   49, 31, 48, 32, 32    avg: 38.4

 Speedup: 2.5x faster (94.6ms -> 38.4ms)
```

The streaming mode is faster because the remote server uses a parallel
seq scan (2+ workers) instead of a single seq scan forced by cursor mode.

## Results: join with rescan (count(*) FROM ft JOIN ft2)

```
 Mode             Execution Time (ms)
──────────────────────────────────────────────
 cursor           2648
 streaming_fetch   2524

 Speedup: ~5% faster
```

On localhost the join speedup is modest. The author reported 290x speedup
on a specific join query where cursors were repeatedly abandoned and
recreated (postgresReScanForeignScan). Our test case with 10K qualifying
rows doesn't trigger that pattern as severely.

## Existing benchmarks from the thread

### Rafia Sabih (author)
- count(*) on 990K rows: 62.7ms (cursor) vs 24.9ms (streaming) = **2.5x**
- Join with rescan: 112,825ms (cursor) vs 389ms (streaming) = **290x**
- Spill-to-disk sort: 4,662ms (cursor) vs 3,527ms (streaming) = **1.3x**

### Kenan Yilmaz (reviewer)
- 20M rows scan: 18,997ms (cursor, no parallel) vs 24,963ms (streaming,
  parallel + tuplestore overhead) = **regression -31%** on very large
  tables where tuplestore overhead exceeds parallel benefit

## Analysis

- **Simple scans**: 2.5x faster (parallel plan on remote)
- **Joins with rescan**: up to 290x faster (avoids cursor recreation)
- **Very large scans**: may regress due to tuplestore overhead
- **Real-world use case**: Jelte Fennema-Nio confirmed it works with
  MotherDuck (DuckDB doesn't support cursors at all)

The feature is opt-in via `streaming_fetch = true` on foreign table/server.
Users can enable it per-table where parallelism helps and keep cursor
mode where tuplestore overhead hurts.
