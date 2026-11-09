# Reproduce the hash composition screen

The measured campaign used VM158, GCC 13.3, Python 3, GNU make/binutils,
Bison, Flex, Perl, zlib and OpenSSL development libraries. Linux x86_64,
approximately 8 GB free RAM and 20 GB free disk are suitable. All builds
use `-O2 -g -fno-lto`, `LDFLAGS=-fno-lto`, no ICU/readline, OpenSSL,
nice 10 and two compile jobs. Each of five fullclean builds runs the
unchanged 239 core tests at maximum two connections. No sudo, perf, sysctl,
production service or archive database is required.

The existing VM measurement executed the build, fresh fixture, gate and
two-stage SQL scripts shipped here. The portable `review-smoke.py` was added
afterward and checked against the completed original receipts offline;
the actual launch used the equivalent recorded inline review. This offline
check did not start another cluster or produce new timings. A new work path
will produce new ELFs/data/times, not the historical byte identity or exact
percentages. Child static-preparation reports retain their original stage
labels; actual execution is attested by collected/ receipts.

## Fresh source, builds and data

`PG_GIT` must be a local complete repository containing all B72 source blobs.
For example, use a full clone of PostgreSQL/cpg, with the source commits
listed in source/SOURCE.json. These scripts do not fetch data implicitly.
Only the B72 archive is read from Git; the alternative patches and complete
edited-file snapshots are verified against all 7726 baseline file hashes.
Use new directories and paths without spaces. Ports below must be unused.

```sh
PACKET=/absolute/path/to/this-packet
PG_GIT=/absolute/path/to/complete/postgresql-repository
WORK=/tmp/hash-combo-new
mkdir "$WORK"
python3 -B "$PACKET/build-harness/build.py" \
  --git "$PG_GIT" --source-plan "$PACKET/source/SOURCE.json" \
  --output "$WORK/build" --core-port 40540
python3 -B "$PACKET/prepare-and-check.py" \
  --work "$WORK" --source-plan "$PACKET/source/SOURCE.json"
```

Alternatively pass `--source-archive /new/B72.tar.gz` to build.py, using
`git archive 72b9498df9a369e747f8d96efb5a6cd33c2451e2` and gzip. All original
file hashes still have to match. No old PGDATA or module is an input.

The fixture starts from B, builds the supplied synthetic hash support module,
loads the exact setup formulas, and discovers an actual overflow holdout on
the new physical layout before timing. It verifies 19 full row multisets,
independent fixed answers and plans, then stops/fsyncs the seed and creates
ten complete numeric copies before assigning code. Qualification uses five
additional copies and each build's own installed headers. It performs normal
and UBSan complete-TU valid-page oracles, all 19 SQL cases and the original
logged/unlogged/TEMP insert/delete/VACUUM/REINDEX/TRUNCATE/refill and SCROLL
checks. Serial checks are not a concurrency or buffer-replacement proof.

On failure, retain that attempt. Correct a harness problem only in a new named
attempt, keep failed evidence, and do not regenerate expected answers from C.

## Smoke and the two finite cohorts

Inspect allowed guest CPUs and topology before selecting placement. Within
each cohort, use different guest cores for backend and client. Defaults below
were allowed on the original VM: backend 6/client 4, then backend 7/client 5.
Here 6/7 and 4/5 are sibling thread pairs, so the cohorts are not independent
hardware placements. The controller/postmasters/background workers retain
the full initial allowed set; the runner pins its own client and measured
backends. All processes use nice 10. Shared load remains recorded and is
never used to discard an observation.

```sh
python3 -B "$PACKET/harness/run-local.py" --smoke-only \
  --runtime "$WORK/runtime.json" --fixture "$WORK/fixture/fixture-receipt.json" \
  --output "$WORK/smoke" --server-cpus 6 7 --client-cpus 4 5
python3 -B "$PACKET/review-smoke.py" --work "$WORK" \
  --output "$WORK/SMOKE-REVIEW.json"
python3 -B "$PACKET/harness/run-local.py" --run-only \
  --runtime "$WORK/runtime.json" --fixture "$WORK/fixture/fixture-receipt.json" \
  --output "$WORK/run" --smoke-root "$WORK/smoke" \
  --review "$WORK/SMOKE-REVIEW.json" --server-cpus 6 7 --client-cpus 4 5
python3 -B "$PACKET/harness/analyze.py" \
  --input "$WORK/run/cohort0/raw.jsonl" --input "$WORK/run/cohort1/raw.jsonl" \
  --output "$WORK/analysis"
```

The separate smoke uses five extra copies and accepts zero performance
observations. The review checks answers/plans, closure and unchanged ten
copies, with no timing-magnitude criterion. The accepted command independently
rechecks live prefix/source/seed/unused-copy guards. The 19 cases have two warm
and ten retained rounds per role/cohort, all ten balanced Williams orders,
2280 raw/1900 retained/380 warm observations. Birth and case orders reverse
in cohort 1. Every negative and all ten direct pairs are retained.

Each EXPLAIN is immediately preceded by the same literal-answer SELECT:
this is an explicit extra warm access. Server shared_buffers=512MB,
autovacuum/JIT/parallel query off, system timing clock; session work_mem=64MB,
statement timeout=180s, lock timeout=10s. These are warmed persistent sessions,
not a cold-cache, network-latency or connection benchmark. Retained root plans
must have zero shared reads. Actual query/index-loop/Memoize/recheck controls
are in harness/inputs/cases.json and harness/runner.py.

SQL execution time is EXPLAIN's elapsed `Execution Time` with TIMING OFF.
Backend CPU is schedstat CPU around the whole command, including planning
and EXPLAIN/protocol work. Client wall is monotonic time around that command.
The three boundaries are reported separately, in milliseconds. Differences
and percentages use direct same-round observations, not aggregate medians.
All raw responses/counters are flushed/fsynced before parsing and acceptance.

The native callback in build-harness/gate-inputs/page-oracle.c is an **untimed
correctness oracle**. This composition study supplies no new timed native
kernel or CREATE INDEX result. The SQL rescan micro/workload commands actually
perform 3000 probes and can be rerun directly from the supplied case catalog.
No speedup in an isolated comparator or buffer mock is substituted for SQL.

## Check the published evidence without PostgreSQL

The S3 packet splits only the two large raw files at complete line boundaries.
Restore a new complete collection, preserving the frozen publication:

```sh
python3 -B "$PACKET/restore-raw.py" --output /tmp/hash-combo-evidence-new
python3 -B "$PACKET/harness/analyze.py" \
  --input /tmp/hash-combo-evidence-new/run/cohort0/raw.jsonl \
  --input /tmp/hash-combo-evidence-new/run/cohort1/raw.jsonl \
  --output /tmp/hash-combo-analysis-new
python3 -B "$PACKET/independent-audit/audit-independent.py" \
  --collection /tmp/hash-combo-evidence-new/run \
  --analysis /tmp/hash-combo-analysis-new \
  --runtime /tmp/hash-combo-evidence-new/runtime.json \
  --fixture /tmp/hash-combo-evidence-new/fixture/fixture-receipt.json \
  --build-receipt /tmp/hash-combo-evidence-new/build/build-receipt.json \
  --gate-status /tmp/hash-combo-evidence-new/gates/status.json \
  --holdout /tmp/hash-combo-evidence-new/fixture/holdout/holdout-discovery.json \
  --harness "$PACKET/harness" --source-plan "$PACKET/source/SOURCE.json" \
  --output /tmp/hash-combo-independent-review-new
```

This is numerical/raw/recorded-binding replay. It does not reread old installed
binaries, headers or PGDATA and does not constitute a new Linux SQL run.
The separately implemented auditor recomputes the schedule and all 85,500
JSON/CSV numerical comparisons and validates all answers/plans/recorded
source/runtime bindings. Its tolerances cover floating-point evaluation
differences, not performance acceptance.
