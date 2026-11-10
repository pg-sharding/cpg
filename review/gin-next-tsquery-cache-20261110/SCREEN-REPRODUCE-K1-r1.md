# Frozen K1 screen: staged commands and metric contract

The runtime source is frozen by SCREEN-INPUTS-K1-r1.json. This document is outside
that frozen directory and records instructions; it creates no observation.
Current roles are B/T/K1, exact old 16 SQL +7 actual-AM cases. No decoder metric,
C9 combination or generic-opclass cache result is part of this matrix.

Full B/K1/K1_assert builds and core239/posting-list checks must PASS, followed by
`PASS_ORDINARY_SQL_NATIVE_CACHE_AND_GENERIC_FALLBACK`, timing_samples=0,
remaining_owned=0 and cleanup_errors=[]. That full gate compiles the dispatcher
oracle against actual installed headers, calls the real installed function,
checks every ternary/recheck combination and the nine-entry/hidden fallback,
compares ordered Seq/GIN data and old literals, repeated prepared queries,
single-session lifecycle, and exact forwarding VOLATILE custom-opclass counts.
Review original build/qualification receipts. Stop all own compilers/gate jobs
before smoke; preserve source/prefix/seed state and any failed attempts.

For a new independent Linux replay, run the supplied full-build-harness-r1 and
full-qualification-r1 first in a NEW owned namespace as described in
FULL-BACKEND-REPRODUCE-r1.md. Do not change historical ELFs or relabel new outputs
as existing measurements. The controller reads fresh source/header/prefix/ELF
receipts and creates fresh copies; no old PGDATA or .so dependency is required.
Use exact source snapshots, case/answer data and fixed orders. The source
commit is K1 9e0d6e84c5bd538e58a534c99cb39ca669c567b7 over fixed B
8a8c475037bfde101da23cc9b0364c9c020eca93; the supplied prerequisite is identical.

Concrete VM84 namespace is `/home/reshke/allfuzz/gin-next-tsquery-cache-20261110`.
Root alone performs current trusted-context transfers/launches, using the exact
reviewed importer; these generic commands document the independent stage entry
points. nice 10 and a 3GB address-space limit must be inherited; make-j2 is for
builds only. Select unused ports and allowed guest CPUs before prepare; the
actual frozen importer uses port 45840, server/client 0:4 then 4:0, environment
SHARED_LOAD_DIAGNOSTIC. Shared load is retained honestly, with actual lscpu/load
records. Guest labels do not prove independent physical resources.

```sh
python3 -B screen/campaign.py --stage prepare \
  --build /owned/build-r1 --qualified /owned/qualification-r1 \
  --output /owned/screen-r1 --first-port 45840 --cpu-pairs 0:4,4:0 \
  --environment-label SHARED_LOAD_DIAGNOSTIC
python3 -B screen/campaign.py --stage smoke \
  --build /owned/build-r1 --qualified /owned/qualification-r1 \
  --output /owned/screen-r1 --first-port 45840 --cpu-pairs 0:4,4:0 \
  --environment-label SHARED_LOAD_DIAGNOSTIC
```

Prepare compiles the byte-identical public-AM helper with the new build's actual
headers/flags and verifies all nine numeric copies against the new immutable
seed, hashing/fsyncing them before assignments. Smoke consumes three separate
copies, runs every 23 cells x3 roles =69 observations, accepts zero timing,
stops all clients/clusters and verifies all six accepted copies remain unused
and equal the seed. No accepted run follows automatically. An external root
review must bind the exact smoke status, freeze SHA and environment label with
status PASS_SMOKE_REVIEW_FOR_FIXED_RUN before the following separate command:

```sh
python3 -B screen/campaign.py --stage run \
  --build /owned/build-r1 --qualified /owned/qualification-r1 \
  --output /owned/screen-r1 --first-port 45840 --cpu-pairs 0:4,4:0 \
  --environment-label SHARED_LOAD_DIAGNOSTIC --review /owned/ROOT-SMOKE-REVIEW.json
```

Each cohort runs two warm rounds, then six retained fixed orders:
B/T/K1; T/K1/B; K1/B/T; K1/T/B; B/K1/T; T/B/K1. Every role occupies each position
twice and each directed adjacent pair occurs twice in the retained schedule.
Cohort 1 reverses case order and physical birth assignments. B and T use exactly
the same prefix/ELF/entrypoint. Counts are 1104 raw /828 retained /276 warm,
552/414/138 per fresh cohort. Keep all three direct role pairs, all controls,
six retained values per group and separate cohorts, with min/median/max/mean,
sample stdev/MAD plus raw ratios/differences. There is no trimming, pooling,
control normalization, significance or causal additive claim.

Literal-answer commands execute separately before every measurement as extra
warming. Raw journals are fsynced before parse/assertion. SQL metrics are full
EXPLAIN executor time, whole-command backend CPU and client wall. The actual-AM
inner CPU/wall include scan/rescan, bitmap materialization and free; no timed C
code was changed. The whole-command reply ends client wall before parse/journal,
then backend CPU is sampled. These boundaries are distinct; all negative,
short/inline/absent/dense/NOT/phrase/OR/full-read and Seq cells remain.

After complete PASS and all own clusters/clients/PIDs/sockets stopped, unchanged
7726 source files/three installs/modules/seed/input hashes, collect only raw and
small receipts. Never publish PGDATA/binaries/full runner logs. Run locally into
new paths:

```sh
python3 -B analysis-tools-K1-r2/analyze.py /collected/screen-r1/cohort0 /new/analysis0
python3 -B analysis-tools-K1-r2/analyze.py /collected/screen-r1/cohort1 /new/analysis1
python3 -B audit-screen-independent-K1-r1.py \
  --run-root /collected/screen-r1 --analysis0 /new/analysis0 --analysis1 /new/analysis1 \
  --out-new /new/independent-audit.json
python3 -B render-screen-results-K1-r1.py \
  --run-root /collected/screen-r1 --analysis0 /new/analysis0 --analysis1 /new/analysis1 \
  --audit /new/independent-audit.json --out-new /new/BENCHMARKS.md
```

Each cohort yields 228 absolute groups, 228 pair groups and 1368 direct pairs;
totals 456/456/2736. The frozen analyzer validates every warm and retained row,
full plans/index loops, literal journals and actual-AM counts. The independent
local auditor imports no benchmark code. Those result stages are NOTRUN until
actual completed data exist. Heikki 2014 is explicit caching prior art; no
novelty or latency benefit is inferred from the earlier repetition counts.

The frozen original analyzer stopped locally at a stale n==10 guard. The new local analysis-tools-K1-r2/analyze.py changes only that guard to the registered six values; failure and original source are preserved, no samples or timings rerun.
