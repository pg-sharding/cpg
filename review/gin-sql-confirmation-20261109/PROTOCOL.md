# GIN full SQL confirmation, 9 November 2026

This is a new ordinary performance campaign on B72
`72b9498df9a369e747f8d96efb5a6cd33c2451e2`, not a current-master claim.
All three trees include the same previously supplied prerequisite. Its
identity is recorded in `build-source/SOURCE.json`; this campaign treats it
as an opaque common input. The advance and lazy candidates are independent
alternatives, not a patch series. No combined candidate is measured.

Four serial clean builds: B, lazy V4, advance V4 release, and advance V4 with
assertions. Common source/build/compiled-prefix paths, fresh build directories
per variant, GCC, `-O2 -g -fno-lto`, no ICU/readline, OpenSSL, nice 10, make -j2.
Original 239 core regression tests must pass in every build; original source
and expected files must remain unchanged. Runtime installations use distinct
DESTDIR trees. Exact B executable is also used by an independent twin cluster.

Only VM158 is selected: the read-only archive host is untouched; VM84's initial
load is about 11 on 8 logical CPUs. No foreign workload is stopped. VM158 is
also shared, with an existing unrelated write workload. Host load, CPU
topology, own process affinity, command runqueue and exact-twin movement are
retained; no noisy result is discarded or normalized.

Use byte-identical historical setup, all 17 discovery and 8 holdout queries,
and frozen scalar answers. The 200000-row fixture includes FTS, intarray,
JSONB, builtin arrays, NULL/empty and a 256-row inline table. Its ordinary
5000-row writes table is created by the frozen setup and is not exercised.
Create indexes once with B, shut down, hash all seed files, copy and fsync
physical data before assigning candidates. No candidate-specific index build,
write/concurrent workload, native microbenchmark or new CREATE INDEX timing
is included in this finite SQL-only comparison.

Before timing, each of B/L4/A4/A4-assert must match ordered forced-Seq and
forced-GIN row multisets for all 25 cases, cross-role row hashes, frozen scalar
answers and expected aggregate plans. Eight parameter values also check
generic prepared executions; explicitly discard cached plans when switching
Seq/GIN planner settings, inspect both paths, then repeat the cached GIN
execution. These untimed checks do not validate any unrelated defect.

Two new independent cohorts, four fresh clusters each, roles B/T/L4/A4.
Create numeric data slots 0..3 before role assignment. Cohort 0 assigns
B/T/L4/A4 to 0/1/2/3; cohort 1 assigns 3/2/1/0. Postmaster and persistent
session births follow slot order. Server/client physical CPU 0/4 becomes
4/0; case order reverses. All four backends use the same server CPU, with
only one command in flight. JIT, parallel query, memoize and autovacuum off;
512MB shared_buffers, 64MB work_mem (original lossy case uses 64kB), explicit
PostgreSQL system timing clock. Linux schedstat counts whole backend command
CPU; client monotonic wall and EXPLAIN Execution Time are separate metrics.

Each case has 2 warm-up plus 12 retained rounds. Williams4 role orders are
rotations of [B,T,A4,L4], each retained role occupies every position 3 times.
Every measured EXPLAIN follows the frozen literal answer, deliberately adding
warming. All complete EXPLAIN JSON, command CPU/runqueue/fault/IO counters,
client wall, warmups and negative values are retained. Raw responses are
fsynced before parsing or acceptance. Total 2800 raw, 2400 retained, 400 warm.
The runner also repeats Seq/GIN and cross-role multiset checks in each cohort.

Analyze every case, all six direct same-round role pairs, separately per
cohort and metric: absolute min/median/max/mean/sample deviation/MAD and all
12 paired values. No trimming, pooling, twin normalization, endpoint or source
tuning. In particular retain OR, full consumption, dense array, inline, absent,
empty, lossy and off-path Seq controls. Do not add historical timings to the
new observations. Repeated negatives remain open issues, not excluded cases.

All own clusters are registered before start, stopped in finally blocks, and
checked for clean control state, absent PID files/processes/sockets. Final
checks require unchanged installed trees, frozen runtime inputs and seed.
Any failed attempt remains immutable and separate from a later namespace.
