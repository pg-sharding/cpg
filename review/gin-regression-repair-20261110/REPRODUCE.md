# Reproduce GIN regression repairs

This packet contains two separate finite experiments: R2 diagnosis/V7, and R3 boolean advancement/first-page deferral/combination. They use fixed B72, not current master. Alternative candidates must not be installed as one unconditional patch series. Exact incremental parents are in CODE-COMMIT.json and followup-r3/CODE-COMMITS.json. Over-fixed-base diffs are complete independent alternatives after common baseline 8a8c475037bfde101da23cc9b0364c9c020eca93; build-source/*/code-B72.diff also includes the same supplied prerequisite to reproduce the complete trees from B72. Do not apply both forms.

## Linux setup and immutable inputs

Requirements: non-root account, Python 3 standard library, GCC, GNU make, patch, binutils/objdump, util-linux/taskset, Perl, flex, bison, zlib/OpenSSL development files. Executed compiler/configure details are in each build provenance receipt. Allow at least 8 GB available memory and 25 GB disk per wave. CPU 0 and CPU 4 must be available and correspond to distinct physical cores; check `lscpu -e=CPU,CORE,SOCKET,ONLINE`. Choose unused local ports. Use a fresh short absolute path without spaces, because Unix socket paths have a length limit. All output paths must be new. The harness only starts/stops its own clusters and must not run on the mailing-list archive server.

The source is 72b9498df9a369e747f8d96efb5a6cd33c2451e2. Get it from an existing fully materialized local PostgreSQL/cpg repository or a regular full clone containing the published experiments/gin-fixed-base-b72-20261109 branch in git@github.com:pg-sharding/cpg.git. Partial clones may fail because the adapter deliberately disables lazy fetching. The exact 7726-file source manifest is pinned in each build-source/base-source-files.json. The archived source used here has SHA256 8c074fcf94a17d381e2df4a2b0554b925d76a777acb7e2f8a508abe7dfd2bbc4. A locally regenerated compressed archive may differ in archive hash but must match every source file; the `--git` path verifies this.

## R3 production fixes and screen

From the packet root (replace absolute paths):

```sh
python3 -B followup-r3/build-harness/build.py \
  --git /absolute/local/postgres-repository \
  --source-plan /absolute/packet/followup-r3/build-source/SOURCE.json \
  --output /absolute/new-run/build --core-port 43740

python3 -B followup-r3/campaign.py \
  --build /absolute/new-run/build \
  --output /absolute/new-run/screen-r1 --mode screen --profiles --first-port 43800

python3 -B followup-r3/harness/analyze-repair.py \
  /absolute/new-run/screen-r1/cohort0 /absolute/new-results/cohort0
python3 -B followup-r3/harness/analyze-repair.py \
  /absolute/new-run/screen-r1/cohort1 /absolute/new-results/cohort1
```

Alternatively replace `--git ...` with `--source-archive /absolute/baseline.tar.gz`. The build adapter implements the executed method: clean B and C9_assert builds, incremental L4/L8/L9/C9 release snapshots at the same source/build/compiled-prefix paths, -O2 -g -fno-lto, OpenSSL, no ICU/readline, nice 10, make -j2. Complete source and header inventories are checked for each variant. L8/L9/C9 transitions must change exactly access/gin/ginget.o among backend objects. All six variants must pass the original 239 core tests; expected outputs are never regenerated. C9_assert is correctness-only.

The unchanged fixture and all data formulas/indexes are in followup-r3/harness/inputs/setup.sql. There are 200002 docs rows plus a tiny inline table. Default corpus size/probe counts, NULL/empty values, scalar answers and the 25 query definitions are frozen in adjacent JSON. The screen uses 12 SQL cases and four real AM cases on B/T/L4/L8/L9/C9: two warm +12 retained balanced rounds, two reversed cohorts, 2688 raw/2304 retained/384 warm observations. Both B/T processes use the exact same binary. No twin normalization, pooling or trimming. Every build first passes 25 ordered Seq/GIN multiset comparisons, scalar answers and index paths, eight prepared-query tests and repeated rescans; all row multisets repeat on every measured role/cohort. Each timing follows an extra untimed literal-answer execution, deliberately warming the path.

`--profiles` optionally runs separate original-query cpu-clock:u profiles during qualification. It requires the perf executable and permission for user software events; no sysctl or global host change is made. Failed profiling is retained but does not replace ordinary SQL checks. Profiled clusters stop before fresh timing clusters start. Omit this option to reproduce only latency/CPU observations. The collectors export software-profile text but exclude perf.data and full runner logs.

The frozen `full` mode is a conditional B/T/L4/C9 comparison of all 25 SQL commands, two warm+12 retained rounds and two reversed cohorts, 2800 raw/2400 retained/400 warm observations. Run it only after independently reviewing the screen and recording the candidate selection:

```sh
python3 -B followup-r3/campaign.py \
  --build /absolute/new-run/build \
  --output /absolute/new-run/full-r1 --mode full --first-port 43900
```

## Real AM microbenchmark boundary

The campaign compiles gin-am-micro.c against the actual installed baseline public headers, records module/source/header hashes and loads that same module into all owned servers. It calls real index_rescan/index_getbitmap/tbm_free in a native loop; it does not model a loader, extract a private body, or read private GinScanEntry fields. The corrected scan key uses F_TS_MATCH_VQ. The original R1 adapter error is separately preserved and yielded zero samples. SQL registration and direct invocations are created automatically from protocol.py:

```sql
SELECT public.gin_am_micro('g1.inline_d_gin', 'common & token17', 10000);
SELECT public.gin_am_micro('g1.docs_d_gin', 'common & missing', 5000);
SELECT public.gin_am_micro('g1.docs_d_gin', 'common & rare0', 100);
SELECT public.gin_am_micro('g1.docs_d_gin', 'common', 10);
```

The outputs must contain 40000/0/20000/2000000 total TIDs respectively. The internal process CPU and monotonic wall timers include rescan/getbitmap/bitmap destruction plus interrupts, but exclude index open/scan begin/end/JSON construction. These are actual AM scan costs, not heap visibility, CREATE INDEX, or SQL throughput. The full SQL queries include normal executor and heap work. No new CREATE INDEX timing is claimed by this scan-repair wave.

## R2 negative experiment and calibration

Use the outer build-harness/build.py with outer build-source/SOURCE.json in a separate new build directory (core-port 42740). It performs five clean full builds: B/A4/L4/L7 release and L7_assert. Run runtime-r2/campaign.py with --mode null --first-port 42800 and a fresh output, then --mode screen --profiles --first-port 42900 in another output. The corrected runtime is mandatory; the outer original campaign/module is retained only as a failed-attempt record. Null is 660 raw; R2 screen is 3080 raw. Do not pool these observations with R3. R2-RESULTS.md records why V7 was rejected.

## Metrics, export, and failure handling

EXPLAIN Execution Time is executor ms. Whole-command backend schedstat CPU includes planning/output. Client monotonic wall includes command/protocol/output. The internal actual-AM loop CPU/wall is a separate boundary. Keep both reversed cohorts separate, and report per-round paired percent medians plus absolute min/median/max, sample SD and MAD. Ratios of aggregate medians are not paired medians. The tables and JSON retain every role pair and negative control, including Seq, full singleton, OR, dense/lossy, absent and tiny inline queries.

render-results.py exports absolute and direct-pair CSV/Markdown from an analysis directory into a new output. Raw observations are fsynced before parsing; hashes, order, roles, paths, answers, sample counts and cleanup are verified. On any failure preserve the attempt, choose a fresh namespace for a retry, and do not combine partial samples. Final collectors check installed trees, final common sources, seeds, frozen scripts, AM modules, all owned postmasters/backends and sockets. Export only selected synthetic observations/source/metadata: no PGDATA, binaries, perf.data, secrets or full runner logs. Actual receipts distinguish executed remote checks from standalone replay; a clean-machine replay of these instructions is not implied.
