# Reproduce the logical TID key experiment

Use a non-root Linux account with Python 3, GCC, GNU make, Perl, flex, bison, binutils, patch, taskset and zlib/OpenSSL development packages. Allow at least 8 GB available memory and 25 GB disk. CPU 0 and 4 must be available distinct physical cores; inspect `lscpu -e=CPU,CORE,SOCKET,ONLINE`. Software profiles additionally need an already working perf installation. The harness changes no perf permissions or foreign workloads. Do not benchmark on the archive host.

The source is PostgreSQL B72 `72b9498df9a369e747f8d96efb5a6cd33c2451e2`, plus the same supplied prerequisite in every build (fixed baseline `8a8c475037bfde101da23cc9b0364c9c020eca93`). This is not current master. A fully materialized local repository containing B72 is required by the `--git` route. The recorded run instead used a local authentic `git archive` of B72; both routes use the same 7,726-file manifest and source plan.

Variants:

- B is the fixed baseline. T uses the exact same installed executable.
- P10 is the shared logical TID key change on B, commit `ca701de010d76b469d9fbfa09f4cad2fdb996e64`.
- C9 is the earlier combined lazy/adaptive candidate, commit `0ab3bd65c8957ea5e25f9ef8981401f0616d99de`. U uses its exact executable.
- C10 adds the same key construction to C9, commit `cf6df20681101bc58dcb5cf47d3fafd738aaa458`.
- C10_assert independently qualifies the combined source with assertions; it is not timed.

P10 and C10 are alternative applications of one source change, authored on C9 and actually cherry-picked to B. They are not a two-patch series. `P10-incremental.diff` applies after fixed B; `C10-over-C9.diff` applies after C9. Complete source-plan diffs instead apply to raw B72. Do not apply both forms. The source does not change six-byte TID storage or its two-byte alignment. Actual execution is x86-64 little-endian; other-platform performance is unmeasured.

From the packet directory, use short absolute paths and unused ports. Each output path must be new; preserve failures and use a new directory for retries.

```sh
python3 -B build-harness/build.py \
  --git /absolute/local/postgres-repository \
  --source-plan /absolute/packet/build-source/SOURCE.json \
  --output /absolute/new-run/build --core-port 44740

python3 -B campaign.py --build /absolute/new-run/build \
  --output /absolute/new-run/screen-r1 --mode screen --profiles --first-port 44800

python3 -B harness/analyze-repair.py \
  /absolute/new-run/screen-r1/cohort0 /absolute/new-analysis/cohort0
python3 -B harness/analyze-repair.py \
  /absolute/new-run/screen-r1/cohort1 /absolute/new-analysis/cohort1
python3 -B render-results.py /absolute/new-analysis/cohort0 /absolute/new-tables/cohort0
python3 -B render-results.py /absolute/new-analysis/cohort1 /absolute/new-tables/cohort1
```

The build script clean-builds all five variants serially at identical common source, build and compiled-prefix paths, with separate DESTDIR installs. Flags are `-O2 -g -fno-lto`, OpenSSL, no ICU/readline, make -j2, nice 10. Each build must pass the original 239 core tests and `test_ginpostinglist`. Release backend objects outside `access/gin/` must remain byte-identical to B. Source, original expected outputs, all headers and installed files are checked. The standalone property preflight is separate: it uses actual PostgreSQL headers and the exact old comparator as an oracle, checking 1,009,216 pairs per new variant including extreme values and both possible modulo-four alignments. It is a correctness check, not a timing result. `preflight.py` records the original run's old-build paths; adjust those paths for a separate preflight replay. The normal build/qualification route above does not depend on them.

Data setup is automatic from unchanged `harness/inputs/setup.sql`: 200,000 generated documents plus NULL/empty rows; FTS, JSONB and array indexes; a 256-row inline fixture; frozen/analyzed heaps. All five builds first qualify 25 ordered Seq/GIN row multisets, scalar answers, expected paths, eight prepared comparisons and repeated cached rescans, plus seven actual-AM answers. All 25 row multisets repeat for every timed role/cohort. Timings use JIT, parallelism, memoize and autovacuum off, 512 MB shared buffers and warm cache.

The screen uses 13 SQL queries and seven actual-AM loops. Six roles, two warm and 12 retained balanced Williams rounds, two cohorts with reversed CPU/slot/session/case order: 3,360 raw, 2,880 retained and 480 warm observations. B/T and C9/U twins stay visible; no normalization, pooling, trimming or discarded negative cases. SQL executor time, whole-command backend CPU and client wall are separate metrics. Main incremental comparisons are P10/B and C10/C9. C10/B includes the pre-existing C9 changes and cannot measure the new helper alone.

The native C adapter loops over actual `index_rescan/index_getbitmap/tbm_free`, with `F_TS_MATCH_VQ` and installed public headers. Cases are inline 10,000 scans × 4 TIDs, absent 5,000 × 0, skew1000 100 × 200, full/OR 10 × 200,000, dense AND 10 × 33,333, rare 1,000 × 200. Its internal process CPU/wall exclude index open, begin/end and JSON creation. They are not SQL throughput or CREATE INDEX. Optional profiles run original inline/OR SQL separately before timing, with cpu-clock:u at 199 Hz and DWARF for 3 seconds. They are diagnostic, not hardware-cycle attribution.

The following are conditional follow-ups, not evidence that they executed. Consult RESULTS.md for the actual completed phases. Full SQL uses all 25 unchanged queries, the same six roles/cohorts and rounds: 4,200 raw / 3,600 retained / 600 warm.

```sh
python3 -B campaign.py --build /absolute/new-run/build \
  --output /absolute/new-run/full-r1 --mode full --first-port 44900

python3 -B create-index.py --build /absolute/new-run/build \
  --seed /absolute/new-run/screen-r1/seed \
  --output /absolute/new-run/create-index-r1 --first-port 45000
```

CREATE INDEX has its own protocol and raw observations. It copies the unchanged seed, drops the existing FTS index, obtains ordered Seq Scan row-digest references and installs amcheck outside timing. Six fresh roles per cohort each perform two warm plus 12 retained builds of `CREATE INDEX bench_idx ON g1.docs USING gin(d) WITH(fastupdate=off)`, with 128 MB maintenance_work_mem and parallel maintenance disabled. Only CREATE INDEX CPU/client wall is timed. amcheck, ordered row-digest comparisons and expected new-index paths, index size and DROP occur afterward. No cache flush or durability relaxation is used. Preserve all 168 observations, including 24 warmups. This small build fixture does not represent external sorting or large-memory-pressure builds.

Raw JSONL and complete absolute/pair distributions remain authoritative. Keep phases separate. Final collection verifies installed/source/runtime/module/seed identities, clean shutdown of every owned cluster, and absence of their processes/sockets. Public exports exclude PGDATA, binaries, perf.data, full runner/build/server logs and private full-message archive copies. The portable instructions are supplied with the executed harness; an additional clean-machine replay is not implied.
