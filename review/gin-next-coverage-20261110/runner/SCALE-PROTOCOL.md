# Larger fixture and restart-only cache scope

Prepared, not executed at protocol creation. The runner requires the same
five checked C11 builds and successful ordinary qualification as operations.py.
Candidate sources are unchanged. These are separate campaigns, not extensions
of the historical 200k scan observations or of the write/build measurements.

`scale.py --mode warm` creates a static 1,000,000-row tsvector table, using a
literal generate_series recipe in the runner, plus a fastupdate=off GIN index.
It records relation sizes and refuses to proceed unless the heap plus GIN
index is larger than the configured 64MB shared_buffers. There is no claim
that the working set exceeds host RAM. Copying, hashing, qualification and
earlier queries warm the OS cache. work_mem is 64MB; JIT, parallel workers
and autovacuum are disabled in these owned clusters, normal durability stays
enabled. Baseline seed preparation and its index creation are not benchmarks.

Seven SQL count/sum queries cover skew1000, skew127, missing-key intersection,
full read, dense intersection, OR and a forced Seq Scan control. Each is
checked by exact ordered Seq/GIN rows before timing on every new backend,
with literal expected count/sum and intended plan checks. Timed commands use
EXPLAIN(ANALYZE,BUFFERS,WAL,TIMING OFF,FORMAT JSON); executor time, whole
backend-command CPU, client wall, run queue and buffer hits/reads stay separate.
One-million ordered IDs fit the Session's bounded output limit.

The four roles B/T/C9/C11 use exact B/T executable twins. Two cohorts reverse
clone assignment and swap server/client CPUs 0/4; case order also reverses.
Each case has two warm and twelve retained balanced Williams rounds:
784 raw, 672 retained and 112 warm observations total. Correctness and answer
queries are outside timing and intentionally warm the fixture.

`scale.py --mode restart --large-from <PASS-warm-output>` reuses only the
stopped, hash-checked larger seed. Before EVERY target query, including every
warm sample, its own postmaster is restarted. No target answer query runs
between restart and the measured EXPLAIN. After measurement, the scalar
answer and intended plan are verified. The scope is **empty shared buffers
with OS cache warmed**, not cold disk or cold OS cache. No global cache drops,
system tuning or foreign-cluster restarts occur.

Restart mode contains skew1000, full read and Seq controls, two warm and four
retained rounds per role/cohort: 144 raw, 96 retained and 48 warm observations.
The smaller repeat count is declared in advance; all ranges, SD, MAD, raw
values and paired comparisons remain visible. Postmaster startup/shutdown is
outside query latency. Buffer reads mean misses in shared buffers and do not
prove physical storage reads; process I/O is recorded separately in raw data.

Every measurement is written and fsynced to raw JSONL before acceptance
assertions. All pairings are reported without trimming, cohort pooling or
twin normalization. Reports must discuss control drift and negative results.
Every owned postmaster/backend/socket must be absent at completion; original
sources, helper scripts, installed trees and seeds are rehashed. Restart mode
has many short owned cluster lifetimes; this is intentional and bounded.

Example, after the C11 build and qualify stages pass, on an explicitly leased
test VM with short output paths and free Unix-only ports:

```sh
python3 -B /absolute/coverage/scale.py --mode warm \
  --build /absolute/build-r1 --qualified-from /absolute/qualify-r1 \
  --output /absolute/new-lg-r1 --first-port 45740
python3 -B /absolute/coverage/scale.py --mode restart \
  --build /absolute/build-r1 --qualified-from /absolute/qualify-r1 \
  --large-from /absolute/new-lg-r1 \
  --output /absolute/new-rs-r1 --first-port 45740
```

For second-host confirmation, rebuild/requalify source on the other test VM;
do not reuse executable identities or observations across hosts. Apply the
same frozen protocol. Run it only in a suitable host-load window, otherwise
label it shared-load diagnostic evidence. Identical source and a passing
correctness suite alone are not confirmation of the measured speedup.
