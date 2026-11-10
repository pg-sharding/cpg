# Held-build selective natural-plan OR SQL

Preparation only. No new SQL, EXPLAIN, smoke or timing has executed. This
independent capsule preserves the old B/T/Heap sources, exact ELF bindings and
qualified seed in ORIGIN.json. It omits common from seven fixed OR expressions
and permits natural scan choices, including Seq and any role-specific plan
variation. No source, threshold or cost/statistics tuning is part of this wave.
WORKLOAD.json is the byte-exact prospective workload; cases.json adds explicit
natural settings, separate forced oracle settings and independent scalar/digest
answers. N1/2/7 remain negatives; the eighth cell is the natural ID-range control.

The fixed plan is eight cells, B/T/Heap, two fresh cohorts, all six role orders,
two warm + six retained rounds: 384 raw / 288 retained / 96 warm. Smoke has
24 raw / zero accepted. Each cohort keeps 72 absolute and 72 pair groups and
432 direct pairs, separately for backend CPU, client wall and SQL executor
milliseconds. No pooling, filtering, twin normalization or plan selection.

Root-only staged commands after source/capsule/host review:

```sh
N=/home/reshke/allfuzz/gin-heap-selective-natural-20261110
B=/home/reshke/allfuzz/gin-next-c11-bitmap-20261110/or-build
Q=/home/reshke/allfuzz/gin-next-c11-bitmap-20261110/oq-r2
P=/home/reshke/allfuzz/gin-heap-wide-sql-followup-20261110/run-r1
python3 -B "$N/inputs/campaign.py" --stage prepare --build "$B" --qualified "$Q" \
  --previous-heap-run "$P" --output "$N/run-r1" --first-port 46540 \
  --cpu-pairs 0:4,4:0 --environment-label FRESH_HOST_CLEAN_SCREEN
python3 -B "$N/inputs/campaign.py" --stage smoke --build "$B" --qualified "$Q" \
  --previous-heap-run "$P" --output "$N/run-r1" --first-port 46540 \
  --cpu-pairs 0:4,4:0 --environment-label FRESH_HOST_CLEAN_SCREEN
```

Use SHARED_LOAD_DIAGNOSTIC if a fresh host check does not establish a quiet
window. Prepare and smoke never promote automatically. Root must inspect all
24 rows, full plans, literal/ordered answers, all-on timed settings, exact twin,
unused six accepted copies and stopped clusters; write a separately SHA-bound
PASS_SMOKE_REVIEW_FOR_FIXED_RUN receipt. Only after explicit root review:

```sh
python3 -B "$N/inputs/campaign.py" --stage run --build "$B" --qualified "$Q" \
  --previous-heap-run "$P" --output "$N/run-r1" --first-port 46540 \
  --cpu-pairs 0:4,4:0 --environment-label FRESH_HOST_CLEAN_SCREEN \
  --review "$N/ROOT-SMOKE-REVIEW-r1.json"
```

Ports46540..42 smoke,46550..55 accepted. Nine numeric clones are fully hashed
and fsynced before assignment; smoke uses three and verifies the accepted six
unused. Cohort1 reverses births/case order. Nice10, server/client CPU0/4 then4/0,
512MB buffers,64MB work_mem,system clock,parallel/JIT/memoize/autovacuum off.
Natural scan settings are all on; complete pg_settings planner context is
recorded once per backend, and a per-case snapshot is bound into every raw row.
Forced Seq/GIN applies only inside separate untimed oracle transactions, then
ROLLBACK restores state. Full natural plans/settings are preserved separately.

Each measured EXPLAIN has an immediately preceding independent literal command
as explicit extra warming. Client wall stops at reply before JSON parse;
whole-backend schedstat CPU is separate; EXPLAIN Execution Time covers the
executor. Every raw record is flushed/fsynced before validation. Stop all owned
clients/clusters independently in finally; no unrelated process is signalled.
Full held installs/source/qualified seed, copied seed and frozen inputs are
verified; root performs a separate final live proof. Failure is preserved, not
retried or tuned. Natural plan differences and Seq choices are observations,
not acceptance failures. Runtime/reference commands bind original artifacts;
REPRODUCE.md describes an independent fresh-build SQL illustration separately.

Offline after complete PASS, with nonexistent analysis outputs:

```sh
python3 -B inputs/analyze.py collected/run-r1/cohort0 analysis-cohort0-r1
python3 -B inputs/analyze.py collected/run-r1/cohort1 analysis-cohort1-r1
python3 -B audit-independent-r1.py --inputs inputs --workload inputs/WORKLOAD.json \
  --results collected/run-r1 --mode screen \
  --analysis0 analysis-cohort0-r1 --analysis1 analysis-cohort1-r1 \
  --out-new SCREEN-INDEPENDENT-AUDIT-r1.json
```

Collect only explicit text proofs/raw journals/plans; exclude PGDATA, binaries,
shared libraries and full runner logs. Historical common-superset forced-GIN
results and old native-AM timings remain different experiments.
