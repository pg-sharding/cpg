# Hash no-op + recent-buffer composition: ordinary SQL harness

Stage: LOCAL STATIC PREPARATION ONLY. No new source build, Linux fixture,
server, SQL, smoke or performance run has been executed by this packet.
Source/runtime identities and actual qualification are supplied by root.
Old frozen experiments remain unchanged. The old no-op and hint alternatives
are now deliberately composed only in this new, explicitly named experiment.

Five roles are B/T/N/H/C: B72 baseline; exact B executable twin; no-op source
`3fc5ad43e3f932374ad4eb1fa7e2da041e5ffc3b`; buffer-hint source rooted at
`989ba16d` (root fills full identity); and root's exact no-op cherry-pick onto
that hint source. B72 is `72b9498df9a369e747f8d96efb5a6cd33c2451e2`.
This harness creates no production source, builds or Git commits. The four
real release installs must have distinct ELFs; T maps exactly to B.

`inputs/cases.json` preserves all18 latest no-op case definitions and appends
the historical H2 `uniform_hot_varying_residual`, without changing data.
`inputs/confirmation-answers.json` preserves all18 expected answers and adds
`3000|1545|190739520`. Original files are separately retained under
`*-original18.json`. `inputs/setup.sql` is byte-identical to latest no-op.
See FIXTURE-RECIPE.md. No old expected output is regenerated from a candidate.

The fixed Williams design is in schedule.py and PROTOCOL.json: base indices
`[0,1,4,2,3]`, five cyclic labels followed by their five reversals. Warm rounds
use its first two orders. Every retained case uses all ten orders once, so
each role occupies each position twice and each ordered adjacent pair occurs
twice. There is no immediate same-role measured command across warm/retained/
case edges. Cohort1 reverses the19cases and numeric birth-role assignment.
Counts are19×5×(2warm+10retained)×2freshcohorts=2280raw,1900retained,380warm.
All ten direct same-round pairs are retained, including C/N,C/H,N/H,T/B.
No additive benefit is assumed; this is what the new measurements will test.

The build/cluster owner is external. It provides B/N/H/C release and C assert
fullclean source/build/common-prefix proofs, unchanged core/AM qualification,
same support module, frozen baseline seed and ten copied/fsynced numeric data
directories before assigning code. It starts/postgreSQL-stops all own servers,
checks unused accepted copies before timing, and checks final installed files,
910 runtime files as applicable, support, all own PIDs/states and source/freeze.
The runner owns only its five persistent psql clients. Do not use an old VM
service or old PGDATA as its fixture. The build/fixture front door is the new
adjacent `../build-harness/` packet; static preparation is not an executed gate.

Runtime schema is `runtime.example.json`, intentionally nonlaunchable until
root fills it and changes status to APPROVED after actual qualification.
Runtime and fixture receipt paths/SHAs are bound. Each variant supplies prefix,
source_commit and actual postgres_sha256; optional source/header inventories
remain root-qualified metadata. Fixture receipt schema is agreed with the
build owner: PASS_NEW_SEED_AND_TEN_COPIES, build_receipt_sha256,
support/support_sha256, cases_sha256/answers_sha256, holdout_receipt and SHA,
copies[{cohort,slot,path,full_tree_equal,hash_fsync_end_ns}], plus
all_copy_fsync_done_ns. Root correctness review is opaque SHA-bound metadata;
the runner does not invent a qualification result.

All five DSNs are Unix sockets on this Linux host, owned by this account and
on different postmasters. Server CPUs and client CPUs must be allowed and
belong to distinct guest physical cores. The owner starts postmasters nice10;
the runner pins only its own measured backends and its own client. Example
CPUs6/4 then7/5 require actual topology confirmation. This does not establish
host isolation or causal layout effects. Source/data/clock/priority/settings
and cases are frozen before any sample; shared load is not a filter.

After root source/build/gates/fixture review, example future commands are:

```sh
python3 -B runner.py --runtime /abs/runtime.json --fixture /abs/fixture-receipt.json \
  --cohort 0 --server-cpu 6 --client-cpu 4 --output /abs/smoke95 --smoke \
  --dsn 'B=host=/abs/smoke-s0 port=40010 dbname=postgres' \
  --dsn 'T=host=/abs/smoke-s1 port=40011 dbname=postgres' \
  --dsn 'N=host=/abs/smoke-s2 port=40012 dbname=postgres' \
  --dsn 'H=host=/abs/smoke-s3 port=40013 dbname=postgres' \
  --dsn 'C=host=/abs/smoke-s4 port=40014 dbname=postgres'
```

Smoke is95commands (all19×5), zero accepted timings, on five EXTRA owned
copies; accepted ten paths are rejected in smoke mode. It uses the same
literal/EXPLAIN/plan acceptance path. Root reviews smoke and unchanged unused
ten-copy proofs before separately launching the finite run. Never convert
smoke observations into accepted timing or automatically retry a failure.

For each accepted cohort invoke the same runner without `--smoke`, with a
new output, five accepted-copy DSNs and that cohort's CPU assignment. Numeric
slot mapping must be B/T/N/H/C for0, C/H/N/T/B for1. The runner verifies actual
data_directory against the corresponding fixture receipt. After BOTH PASS:

```sh
python3 -B analyze.py --input /abs/c0/raw.jsonl --input /abs/c1/raw.jsonl \
  --output /abs/new-analysis
```

Every EXPLAIN is preceded by the identical literal-answer SELECT, an explicit
extra warm access outside timing. EXPLAIN uses ANALYZE,BUFFERS,WAL,TIMING OFF,
JSON. Server shared_buffers512MB, autovacuum/JIT/parallel off, system timing
clock; session work_mem64MB, statement180s and lock10s; each case resets scan/
Memoize settings before its fixed settings. Retained plans must have zero
shared reads: this is a warmed resident screen, not an IO/cold-cache test.

All full raw responses, literal answers, plan rows/loops/rechecks/cache/buffer/
WAL, monotonic client wall and whole-command schedstat CPU/runqueue/fault/IO
deltas are retained. Complete raw is flushed/fsynced BEFORE JSON parsing,
plan/counter assertions or acceptance, including a counter-read error record.
SQL Execution Time, whole-command backend CPU and whole-command client wall
are three distinct boundaries. No native-kernel or CREATE INDEX claim follows.

The analyzer rejects smoke/partial/failed/duplicate-cohort input; verifies the
complete1140-row order per cohort, all literals, plan signatures, counters,
Memoize and index-loop controls, source-input freeze and ELF identities; then
emits570absolute groups,1140pair groups and11400direct pair observations.
Each absolute/difference/percent summary retains all ten values plus
min/median/max/mean/sample-stdev/MAD, separately by cohort/case/metric.
JSON and full CSV retain every negative/control. No trimming, normalization,
pooled cohorts, ratio of aggregate medians or timing-driven repetitions.

The19cases do not repeat the earlier H2 TEMP/unlogged performance submatrix,
write contention or rank native matrix. Those earlier negative results remain
historical, not newly repaired by this finite composition screen. Every own
client cleanup is attempted independently; external cluster cleanup remains
mandatory even on errors. Preserve failed stages; change harness only in a
new named attempt and never tune source/thresholds after observing timings.
