# Held-build Heap wide-OR SQL follow-up

This capsule is LOCAL PREPARATION ONLY: AST/help/static checks are not runtime
qualification or results. It adds the missing SQL equivalents of seven old
Heap actual-AM cells, preserving widths 1/2/7 negatives, and one new Seq control.
All source/ELFs and the already qualified seed remain exact old artifacts.
Read ARCHITECTURE-SOURCE-AUDIT.md and ORIGIN.json for source/provenance/scope.

The finite plan is B/T/Heap, all 6 role orders,2 warm + 6 retained rounds,2 fresh
cohorts: 384 raw/288 retained/96 warm. Smoke has24 raw/0 accepted. Every cohort
reports whole-command backend CPU, client wall and complete SQL EXPLAIN
Execution Time separately. All3 pairs, all8 cells and both cohorts remain.
Expected count/sum and ordered digests are frozen independently before data.

The proposed new namespace is
/home/reshke/allfuzz/gin-heap-wide-sql-followup-20261110, with these files under
inputs/ and new output run-r1/. Default ports46440..46442 smoke,
46450..46455 cohorts; CPU server/client0:4 then4:0, recorded topology. Root
must approve these choices and freshly confirm load/lease after K3 stops.
Use SHARED_LOAD_DIAGNOSTIC if clean-host conditions are not established.
Nice10,512MB shared buffers,64MB work_mem, system timing clock, parallel/JIT/
memoize/autovacuum off. No source build or native helper is part of this task.

Root-only staged commands after separate capsule/lease review:

```sh
N=/home/reshke/allfuzz/gin-heap-wide-sql-followup-20261110
B=/home/reshke/allfuzz/gin-next-c11-bitmap-20261110/or-build
Q=/home/reshke/allfuzz/gin-next-c11-bitmap-20261110/oq-r2
K=/home/reshke/allfuzz/gin-cache-k3-20261110/timing-r1
python3 -B "$N/inputs/campaign.py" --stage prepare --build "$B" --qualified "$Q" \
  --previous-k3-run "$K" --output "$N/run-r1" --first-port 46440 \
  --cpu-pairs 0:4,4:0 --environment-label FRESH_HOST_CLEAN_SCREEN
python3 -B "$N/inputs/campaign.py" --stage smoke --build "$B" --qualified "$Q" \
  --previous-k3-run "$K" --output "$N/run-r1" --first-port 46440 \
  --cpu-pairs 0:4,4:0 --environment-label FRESH_HOST_CLEAN_SCREEN
```

Root reviews all smoke evidence before writing external
PASS_SMOKE_REVIEW_FOR_FIXED_RUN, binding freeze SHA, smoke-status SHA and the
environment label. Only then:

```sh
python3 -B "$N/inputs/campaign.py" --stage run --build "$B" --qualified "$Q" \
  --previous-k3-run "$K" --output "$N/run-r1" --first-port 46440 \
  --cpu-pairs 0:4,4:0 --environment-label FRESH_HOST_CLEAN_SCREEN \
  --review "$N/ROOT-SMOKE-REVIEW-r1.json"
```

Preparation creates/fsyncs 9 numeric copies before roles are assigned; smoke
uses 3 and leaves 6 accepted copies unused. Cohort0 births B/T/Heap, cohort1
Heap/T/B. Every stage verifies exact old build and qualification receipts,
full prefixes/source/seed and previous K3 shutdown. No unrelated PID is
signaled. Owned-cluster and client cleanup are separate and best-effort all.
Do not retry a failed runtime attempt or adjust cases after observations.

After complete PASS, collect only raw.jsonl/literal.jsonl,oracles.json,status,
backend/runtime/freeze/birth/cleanup/host metadata and finite receipts. Exclude
PGDATA,binaries and full runner logs. Analyzer commands run locally in a tree
with these exact frozen inputs and new nonexistent output directories:

```sh
python3 -B inputs/analyze.py collected/run-r1/cohort0 analysis0
python3 -B inputs/analyze.py collected/run-r1/cohort1 analysis1
```

Each cohort produces 72 absolute groups, 72 pair groups and 432 direct pairs,
including min/median/max,mean/sample stdev/MAD and every value. Retained IO/
runqueue totals are diagnostics, never filters. The full raw records retain
all deltas and warm observations. Old AM and SQL results remain separate;
there is no SQL speedup claim until this new screen and independent recount.
