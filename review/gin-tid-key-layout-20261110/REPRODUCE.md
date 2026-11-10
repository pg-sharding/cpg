# Reproduce the preserved-layout follow-up

This is a separate fresh screen, not a subtraction of R1 measurements. R1 is preserved at https://github.com/pg-sharding/cpg/tree/experiments/gin-logical-tid-key-results-b72-20261110/review/gin-tid-key-20261110 . It found a repeated P10 absent cost and did not promote full SQL/CREATE INDEX.

Use a non-root Linux account, Python3, GCC, GNU make, Perl, flex, bison, binutils, patch, taskset, zlib/OpenSSL development files, 8GB available memory and at least25GB disk. CPU0/4 must be available distinct physical cores; inspect `lscpu -e=CPU,CORE,SOCKET,ONLINE`. Optional software profiles need working perf permissions; the harness changes no host permissions or foreign jobs. Do not use the archive host. Use new short paths and unused ports; preserve every failed attempt and use a new directory for retries.

Source is PostgreSQL B72 `72b9498df9a369e747f8d96efb5a6cd33c2451e2`, plus the same supplied prerequisite in every tree: fixed baseline B `8a8c475037bfde101da23cc9b0364c9c020eca93`. No current-master result is implied. The actual source route uses an authentic local `git archive` of B72. The equivalent `--git` route needs a fully materialized local repository containing B72; lazy network fetch is disabled. The supplied 7,726-file manifest and source plan pin either route.

P10 is `ca701de010d76b469d9fbfa09f4cad2fdb996e64`; P11 is `a5e258877d0fcebc417c020351919a7e2706a7fe`. P11 retains the same bounded four-byte memcpy and endian-dependent halfword reorder, but restores `block <<32 | offset`. It preserves the original transient key values, six-byte storage and two-byte alignment. C11 `ca6ad39111cd67f20ff2dd3a8f619239d0360a10` is the same incremental source change on C10; it was authored once there and actually cherry-picked to P10. C11 has only production-unit/property preflight in this wave, no complete C11 build or timing.

```sh
python3 -B build-harness/build.py \
  --git /absolute/local/postgres-repository \
  --source-plan /absolute/packet/build-source/SOURCE.json \
  --output /absolute/new-run/build --core-port 45140

python3 -B campaign.py --build /absolute/new-run/build \
  --output /absolute/new-run/screen-r1 --mode screen --profiles --first-port 45200

mkdir -p /absolute/new-analysis /absolute/new-tables
python3 -B harness/analyze-repair.py \
  /absolute/new-run/screen-r1/cohort0 /absolute/new-analysis/cohort0
python3 -B harness/analyze-repair.py \
  /absolute/new-run/screen-r1/cohort1 /absolute/new-analysis/cohort1
python3 -B render-results.py /absolute/new-analysis/cohort0 /absolute/new-tables/cohort0
python3 -B render-results.py /absolute/new-analysis/cohort1 /absolute/new-tables/cohort1
```

The analysis/table parent directories must exist, and their output subdirectories must not exist. The `mkdir` command above also supplies the missing parent-directory preparation for the optional manual-analysis commands in the historical R1 instructions; the automatic campaigns already create their own parents. The build script makes four clean builds B/P10/P11/P11_assert at identical common source/build/compiled-prefix paths, with separate DESTDIR installs. GCC flags are `-O2 -g -fno-lto`, OpenSSL, no ICU/readline, make-j2/nice10. Each must pass original239 core tests and test_ginpostinglist, preserve original expected outputs and installed/source/header identities. Every changed release backend object versus B must be under access/gin. Execution is x86-64 little-endian; other-platform performance is unmeasured.

The standalone preflight uses actual installed R1 headers. It compiles P11 and C11 ginget.c with release/assert flags and checks1,009,216 extreme/random/alignment pairs per release helper against the exact old comparator and original key expression. `preflight.py --reference-build ...` expects the R1 B/C10/C10_assert installations from that packet; a fresh replay must first build R1 or adjust the reference map. The ordinary fresh-build/qualification commands above do not require the old preflight installs. This preflight is correctness evidence, not a standalone comparator timing benchmark.

Data setup automatically uses unchanged `harness/inputs/setup.sql`:200,000 generated documents plus NULL/empty rows, frozen/analyzed heaps, FTS/JSONB/array indexes,256-row inline fixture. JIT/parallel/memoize/autovacuum off,512MB shared_buffers and warm cache. Four builds first qualify25 ordered Seq/GIN multisets, scalar answers and expected paths, eight prepared comparisons/cached rescans and seven actual-AM answers. All25 multisets repeat per measured role/cohort.

Four roles B/T/P10/P11, exact B/T executable twins,13 SQL plus seven real-AM cases, two warm and12 retained Williams4 rounds and two reversed CPU/slot/session/case-order cohorts:2,240raw/1,920retained/320warm observations. Keep all six pairs, metrics and negative controls, without trimming,pooling,twin normalization or cross-wave ratio subtraction. Main incremental comparison P11/P10 isolates the preserved layout; P11/B measures the complete load change; P10/B is its fresh regression reference.

SQL records EXPLAIN executor, whole-command backend CPU and client wall separately. The real-AM module uses installed public headers, F_TS_MATCH_VQ and actual index_rescan/index_getbitmap/tbm_free. Its internal process CPU/wall exclude index open,begin/end and JSON creation. Loop cases are inline10,000×4TIDs,absent5,000×0,skew1000 100×200,full/OR10×200,000,dense10×33,333,rare1,000×200. These are native loop times, not SQL throughput or CREATE INDEX. Divide a loop median by its loop count only when explicitly describing native per-scan cost.

With `--profiles`, B/P10/P11 each separately profile original inline/OR/absent SQL and the actual-AM absent loop, wrapped to return only its stable total-TID count. Twelve diagnostics use cpu-clock:u199Hz,DWARF,3sec each, before fresh timing clusters; no hardware-cycle or latency claim. Without perf, omit `--profiles`. Final collection checks the exact executed inputs, builds, seeds, modules, clean shutdowns and absent owned PIDs/sockets. Export contains compact JSON/raw/profile text, not PGDATA,binaries,perf.data,full logs or private archive bodies.

`patches/P11-over-parent-candidate.diff` is the complete P11 change after fixed B; the C11 equivalent applies after C9. Incremental `.diff`/`.patch` files instead apply after P10/C10. They are alternative forms/branches, not a series to apply twice. Complete source-plan diffs alternatively apply to raw B72. Consult RESULTS.md for phases actually executed; this wave does not automatically promote full SQL or CREATE INDEX. No additional clean-machine replay of this portable front door is implied.
