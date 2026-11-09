# Bounded prospective V7 gate — not executed

This is a source/protocol proposal, not an accepted runtime freeze. A new root
review and explicit VM lease precede any transfer, build, PG start or timing.
No perf/sudo/sysctl is needed or permitted by this protocol. All old source,
ELFs, results, protocols and packets remain immutable.

## 1. Normal production-TU codegen first

In a NEW isolated owned namespace, serial nice10 compile B72/V6/V7
`nbtsearch.c` through the normal configured PostgreSQL full-TU build command,
with the same actual installed/generated headers, GCC13.3 and `-O2 -g` flags.
Hash headers and any borrowed immutable backend before/after. No extracted
binary-search micro is a substitute. Record full command, source hash,
compiler/flags, object/symbol/relocation SHA and explicit private object
omissions. Do not run PG for this preliminary gate.

Check the actual ordinary and serializable-retry calls in `_bt_first`, the
noinline leaf entry, absence of the private typed descent clone, generic
`_bt_search`/`_bt_binsrch` and actual outlined `.part` bodies. Compare caller
frame, spills, control-flow and instruction extent with both controls, without
requiring a guessed size threshold or claiming layout causes percentages.
If dispatch has migrated back into `_bt_first`, the proposed codegen contract
is not met. Preserve the negative and review before any new revision.

The objective is to establish what the compiler emitted. It is not a speed
measurement or runtime correctness test.

## 2. Full matched backends and bounded correctness

Preferred fresh builds: B72 release, V6 release, V7 release, V7 assertion,
serial at nice10/j2 with one source/build pathname and compiled prefix,
full clean between variants and separate immutable DESTDIRs. Normal flags:
`-O2 -g`, `--without-icu --without-readline --with-openssl`, and
`--enable-cassert` only in the separate assertion build. Compile amcheck and
pageinspect. Record source-wide overlay manifest (only nbtsearch.c differs),
compiler/configure/CFLAGS/LDFLAGS, actual include path/complete header inventory,
ELF and extension hashes. Exact twin uses the SAME baseline ELF/install, not a
second rebuild. Reuse old B/V6 only if equally complete source/ABI/common-path
provenance exists; do not silently mix old artifacts with new common-path claims.

Run the original 239 core tests for the new assertion build and matched golden
SQL targets against B/V6/V7/assert. If ordinary build checks are required by
the actual build policy, run them once; no green repetition. Do not regenerate
expected from a candidate.

Copied correctness inputs are byte-equal old artifacts, listed in
`inputs-provenance.json`: `targets.sql`, `correctness-null-pivots.sql`,
`correctness-unique.sql`, `recovery-targets.sql`. The selected offset assertion
runs on the same pinned/read-locked page. Coverage must include signed extrema,
NULLS FIRST/LAST, duplicates/posting tuples, true internal pivots and truncated
pivots, all five comparison strategies, forward/backward LIMIT/cursor/rescan,
SAOP, empty/high-key-only pages, unique insertion/conflict, DESC, INCLUDE,
multicolumn, cross-type int4/int2, domain, a real new comparator OID/wrapper,
TEMP, UNLOGGED, REINDEX, VACUUM, TRUNCATE/reload and permanent physical standby.
Do not claim a NULL/standby/etc fast-path exercise merely from equal answers;
record selected-path coverage with diagnostic-only normal SQL-accessible
counters or actual locked-page oracle evidence. No privileged debugger needed.

`correctness-lifecycle-extra.sql` adds bounded local empty-root serializable,
TRUNCATE/REINDEX/reload, domain and cursor transitions. It is also NOT RUN.
The unchanged serializable empty-tree race handling must be source-reviewed;
a two-session barrier check can exercise insertion between the two descents
if the existing core/injection fixture supports it. Do not invent a success
claim from a single-session query. Keep generic/write byte-source identity and
compare actual generated code, without calling the whole linked write path
identical.

Full SQL multisets and fixed expected aggregates must match independent
seqscan/golden baseline; amcheck must pass before/after. Stop on any answer,
ABI/source drift, crash/assert or lifecycle failure. Slow results are retained.
All own servers stop in finally, with pg_ctl status3/PID absence and fsync.

## 3. Matched SQL matrix

Run only after source/codegen/correctness and NEW Linux lifecycle smoke pass.
Freeze the final controller, every transitive script/input, actual runtime
manifest and all hashes BEFORE accepted samples; root reviews the smoke.
Do not execute the historical confirm script: it includes profiles and is not
this prospective controller. No full INSERT/CREATE INDEX speed claim: index
creation in this protocol is untimed setup.

Roles B/T/V6/L7: baseline, exact baseline-ELF twin, V6, leaf-only V7. Two fresh
cohorts use all eight independently copied numeric PGDATA slots, every file
hash and tree fsync BEFORE any role assignment. Baseline initializes one new
C-locale UTF8 seed with the two copied setup scripts. Actual row counts:
2M permanent int8, 1M UNLOGGED int8, 500K text, 100K initial rows per append and
permuted unique-write table; TEMP table copies the 1M UNLOGGED rows per measured
persistent session. Preserve fixed key generation and indexes from the inputs.

Server configuration explicitly reproduces shared_buffers=512MB,
autovacuum=off, max_parallel_workers_per_gather=0, jit=off,
checkpoint_timeout=1h, log_checkpoints=off, listen_addresses=''. Session:
work_mem=128MB, temp_buffers=128MB before TEMP creation,
statement_timeout=60s, synchronous_commit=off, jit/parallel off,
**timing_clock_source=system** (record SHOW actual setting and `pg_test_timing`
sanity outside measured interval). Fresh and heated exact1 sessions use
`enable_seqscan=off; enable_bitmapscan=off` identically; other plans retain the
historical planner defaults. Record all changed GUCs and actual plans, loop
counts, index names, shared/local/temp/WAL counters. Inactive controls must
really use the intended comparator/plan. Inspect actual loops/Memoize, not
just SQL text.

New cohort0: B/T/V6/L7 numeric slot0/1/2/3, server guest CPU4/client0.
New cohort1: B/T/V6/L7 numeric slot3/2/1/0, server guest CPU0/client4.
Verify actual guest CPU/core/sibling topology; do not call this proved physical
host isolation. Both server and runner nice10 in both cohorts, if inherited
from the build/runtime policy. New postmasters and sessions are always born
in NUMERIC slot order, independently of role/query order. Fresh rounds create
all four new sessions/settings/metadata in numeric order before query order.
A fresh measured backend has not yet executed its measured query; warm shared
buffers, settings/metadata and any prior page warming are explicit. Connection
startup is outside executor timing. It is not cold disk or end-user latency.

The fixed cases are in `cases-prospective.json`: 14 persistent (the retained
13 main cases plus heated_exact1), 2 independent randomized-unique INSERT
holdouts, 3 fresh exact1/exact2/small_range. All 19 remain in every result.
Heated_exact1 executes the identical SQL/planner settings as fresh exact1 but
reuses its session. It isolates lifecycle as a separate measured case; do not
pool fresh and heated samples or the old V6 cohorts.

Each of 16 persistent/holdout cases: 4 warm +12 retained rounds, four roles.
Each fresh case: 4 warm +24 retained rounds, four NEW sessions per round.
Per cohort: 1360 raw commands,1056 retained,304 warm. Across two:2720/2112/608.
Warm rows are retained in raw. Reverse complete case/class order in cohort1.
Use a continuous four-role Williams schedule over every warm/retained/case/
class boundary: (B,T,L7,V6), (T,V6,B,L7), (V6,L7,T,B), (L7,B,V6,T).
No self-repeat across boundaries; roles have all positions and predecessor
orders. The static schedule checker and actual event chronology must agree.
Counts/role births/copy ordering are hard gates, not inferred from CLI flags.

Answers are validated on every read; aggregate constants are independently
computed from setup formulas. Capture full result multisets outside intervals.
For writes, derive row counts/complete key multiset from sequence call count
and generation formula, compare four roles and baseline, and check WAL/buffer
behavior and indexes. All warm write calls count toward expected state; fixed
bounds stay well below the 10M permutation period. Do not reset sequences or
regenerate expected from V7. No concurrent application writes in this campaign.

## 4. Metrics, analysis, and stop/collection

Primary executor metric: `EXPLAIN (ANALYZE,BUFFERS,TIMING OFF,WAL,FORMAT JSON)`
Execution Time in ms (also report short-query us explicitly). Raw retain
Planning Time, the complete JSON plan and counters. Record client monotonic
command wall ns and own backend schedstat CPU/queue ns, minor/major faults and
I/O before/after each command. Those CPU/wall boundaries include planning,
EXPLAIN JSON, protocol and scheduling, and are NOT exact executor CPU. Proc
reads occur outside measured command interval. Timer quantization is visible
in short queries. No perf or privileged settings; PROFILE NOT RUN.

Compute within-round direct L7/B,L7/T,L7/V6,V6/B,V6/T,T/B for executor elapsed,
command CPU and client wall independently. Retain queue/fault/IO separately.
For each role/case/cohort, show absolute min/median/max, all raw warm/retained,
paired spread and descriptive within-cohort CI; no quotient-of-medians,
normalization by twin/Seq Scan, pooling unrelated cohorts, or discarded negatives.
Keep per-order and predecessor/recency diagnostics.

After primary samples and before closing retained slow/fixed fresh exact1
PIDs, capture maps/stat/schedstat/smaps_rollup/io/exeSHA and 24 bounded unprofiled
same-PID repeats for all four roles. Do this for fresh exact1 (fixed) and at
most one additional persistent negative (>1.03 against BOTH B and T, selected
in declared case order). Repeat metrics are diagnostics, not new ranking
samples; warmed exact1 is not an explanation of a fresh gap. No causal claim
from code layout alone.

Stop own four servers, verify all own controller/backend/PID/socket absence,
fsync all result/copy trees; rehash canonical seed and frozen source/runtime.
Losslessly collect compact results/proofs/plans, gzip big raw with mtime0 and
original SHA. Public omit ELF/.o/.so/PGDATA/control nonce/full server logs;
retain recorded omission hashes. Parent independently recounts answers,
chronology, units and all six pairs before interpretation or a second revision.

Selection requires actual new evidence. Smaller cold penalty without a retained
hot/negative benefit is not automatically a useful replacement; report the
tradeoff, retain V6 and mark V7 NONSELECTED if appropriate. No source tuning
between cohorts. VM is released promptly after full stop/verified download.
