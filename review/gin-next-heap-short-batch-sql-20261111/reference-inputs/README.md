# Short-query SQL batch of 100 actual rescans

LOCAL PREPARATION ONLY. This is a new fixed work-unit experiment, not a retry,
replacement or normalization of the completed 384-command natural-OR screen.
No source/build/threshold changes: old B/T/Heap exact ELFs and qualified seed
remain bound in ORIGIN.json. The previous natural run must be PASS/stopped.

Cases: exact original width 1/2/7/8 predicates and one-scan ordered row oracles.
Each short measured command is the literal fixed SQL:

```sql
SELECT sum(q.n),sum(q.s) FROM generate_series(1,100) p(i)
CROSS JOIN LATERAL
(SELECT count(*) n,sum(id) s FROM g1.docs
 WHERE d @@ '<exact>'::tsquery OFFSET(p.i%1)) q
```

Each batch has probes=100, unchanged per_scan_rows/per_scan_sum and independent
output_count/output_sum multiplied by 100. The original ID-range control has
probes=1 and its old answer. See cases.json/WORKLOAD.json for exact bytes.
Untimed EXPLAIN ANALYZE in every oracle gate must show the actual docs scan
and every selected index executing100 loops (control 1), with original rows
per loop and top aggregate 1 row / 1 loop. Decorrelated, Materialize or Memoize
shortcuts producing scan 1 are rejected; failures are preserved without retry.
This executed gate precedes any smoke/sample. The single-scan forced Seq/GIN
ordered oracles remain independent of this gate. Natural paths are accepted;
no cross-role plan equality or GIN-choice requirement is imposed.

All five scan switches on, memoize/parallel/JIT off, work_mem 64MB, buffers 512MB,
system clock, nice 10, server/client CPU 0/4 then 4/0. Per-row settings and full
backend planner context remain. Same fixed B/T/Heap schedule: all six orders,
two warm + six retained rounds, two fresh cohorts = 240 raw / 180 retained / 60 warm.
Smoke 15 / 0; nine numeric clones fully hashed/fsynced before assignment, three
smoke and six accepted unused. No auto-promotion, tuning, filtering or repeat.

Root-reviewed stage commands (new namespace and unused ports):

```sh
N=/home/reshke/allfuzz/gin-heap-short-batch-20261111
B=/home/reshke/allfuzz/gin-next-c11-bitmap-20261110/or-build
Q=/home/reshke/allfuzz/gin-next-c11-bitmap-20261110/oq-r2
P=/home/reshke/allfuzz/gin-heap-selective-natural-20261110/run-r1
python3 -B "$N/inputs/campaign.py" --stage prepare --build "$B" --qualified "$Q" \
 --previous-heap-run "$P" --output "$N/run-r1" --first-port 46840 \
 --cpu-pairs 0:4,4:0 --environment-label FRESH_HOST_CLEAN_SCREEN
python3 -B "$N/inputs/campaign.py" --stage smoke --build "$B" --qualified "$Q" \
 --previous-heap-run "$P" --output "$N/run-r1" --first-port 46840 \
 --cpu-pairs 0:4,4:0 --environment-label FRESH_HOST_CLEAN_SCREEN
# STOP: root must inspect 15 raw/literal records, untimed actual100-loop gate,
# single-scan ordered digests, settings,6 unused copies and all 3 stops first.
# Only with a separate PASS_SMOKE_REVIEW_FOR_FIXED_RUN receipt:
python3 -B "$N/inputs/campaign.py" --stage run --build "$B" --qualified "$Q" \
 --previous-heap-run "$P" --output "$N/run-r1" --first-port 46840 \
 --cpu-pairs 0:4,4:0 --environment-label FRESH_HOST_CLEAN_SCREEN \
 --review "$N/ROOT-SMOKE-REVIEW-r1.json"
```

Use SHARED_LOAD_DIAGNOSTIC if the fresh host window is not quiet. Smoke ports
46840..42, accepted46850..55. Always stop all owned clients/clusters in finally
and independently rehash full held source/installs/seed/inputs. Root supplies
a final live shutdown proof. No unrelated process is changed.

All measured metrics are for the COMPLETE COMMAND: backend CPU, client wall
and SQL executor ms separately. Do not silently divide by 100 or compare raw
batch ms with old one-scan ms. Literal command immediately before EXPLAIN is
explicit extra warming; all raw observations fsync before validation. Keep all
five cells, three metrics/pairs, both cohorts, negatives and controls. Each
cohort has 45 absolute/45 pair groups / 270 direct pairs. Analyze locally only
complete PASS; independent auditor imports no benchmark code. No new SQL
performance, noise reduction or regression fix is claimed by this static prep.
