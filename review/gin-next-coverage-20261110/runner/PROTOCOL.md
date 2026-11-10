# Separate build/write controls

Prospective protocol; `STATIC-PREFLIGHT.json` proves syntax and CLI parsing only.
It does not establish that this new runner executes successfully. Runtime
qualification and results, if obtained, are stored in new output directories.

Each invocation measures exactly one of CREATE INDEX, INSERT and VACUUM.
The four roles B/T/C9/C11 use the C11 worker's checked five-build receipt;
B and T run the exact same installed baseline executable. No candidate source
is modified by this harness. B72 is the pinned historical source, not current
upstream master. The common supplied prerequisite is identical in all variants.

There are two CPU/slot cohorts, each with two warm rounds and twelve retained
rounds in a balanced four-role Williams order. Cohort 1 swaps server/client
CPUs 0/4 and reverses the physical clone assignments and session birth order.
Each operation retains 96 of 112 observations (16 warm); all three operations
would yield 288 retained/336 raw/48 warm. Qualification commands on each new
backend are recorded separately and are not benchmark observations.

The stopped, hash-checked qualification seed has 200002 docs rows. Setup,
cloning, TRUNCATE, data preparation, index checks and answer validation are
outside command timing. Normal durability remains enabled; autovacuum, JIT
and parallel work are disabled in these private clusters. Shared buffers are
512MB, work_mem 64MB, maintenance_work_mem 128MB. This is a warm, single-client
small-fixture control, not a cold-cache or external-sort build test.

- CREATE INDEX builds one tsvector GIN index over all 200002 docs rows with
  fastupdate=off, then checks and drops it outside timing. Existing array and
  JSONB indexes are unrelated and remain in the fixture.
- INSERT starts from an explicitly TRUNCATEd heap and empty GIN index and
  inserts docs IDs 1..5000, ordered by ID, with fastupdate=off. It includes
  INSERT SELECT source access and normal heap/WAL work. It is not an isolated
  GIN insertion CPU microbenchmark.
- VACUUM starts from 20000 inserted rows and deletion of all even IDs outside
  timing. It times `VACUUM (INDEX_CLEANUP ON, TRUNCATE FALSE, PARALLEL 0)`.
  Every round creates real dead entries afresh; neither rollback nor repeated
  vacuuming of an already clean index stands in for preparation.

Each operation is validated by amcheck, table row count and ordered Seq/GIN
row digests for `common`, `common & rare0` and `dense3`, with forced GIN plans.
Expected counts are declared in protocol.py. The measured metrics are whole
backend-command CPU from schedstat, client wall, backend run queue, faults,
process I/O, and WAL insert-LSN difference. WAL is sampled before and after
the command in its own otherwise idle cluster. Process write_bytes is not a
complete measure of later asynchronous writeback; WAL bytes and physical I/O
must be read as different metrics. Validation effects warm the next round.

All absolute values and their min/median/max, SD and MAD are retained. Every
role pair is reported. Zero-denominator I/O percentage comparisons are null
and absolute deltas remain available. Do not pool cohorts, trim samples,
normalize by twin drift, or treat negative controls as speedups. C9 changes
the scan path; write controls can expose code-layout/noise effects without
demonstrating an improvement to insertion or vacuum algorithms.

Nine private clusters per operation (seed plus eight clones) must stop
cleanly, with recorded absent PIDs and sockets. Original seed, source, helper
scripts and installed trees are rehashed at completion. No benchmark launch
is authorized while another worker holds the target VM timing lease.
