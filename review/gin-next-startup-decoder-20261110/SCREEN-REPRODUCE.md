Historical prospective instructions, retained below. The six builds/gate and full screen subsequently completed; current measured status and limitations are in FINDINGS-shared84-r1.md and REPRODUCE.md.

The frozen `screen/` scripts have passed local AST/help and protocol-balance checks. They have not run yet. The first allowed VM84 campaign is explicitly a shared-load diagnostic. All source candidates, fixture definitions, original SQL answers and fixed round orders are immutable before this campaign. No combinations are added to the five-role matrix.

The protocol contains 16 SQL, 7 actual-AM and 18 actual-decoder cases. Roles B/T/S1/D1/C9 run two warm and ten retained rounds in ten predeclared five-role Williams orders, on two fresh cohorts. Counts are 4920 raw, 4100 retained and 820 warm. All ten same-round role pairs are retained, with raw values, min/median/max, mean, sample standard deviation and MAD. Cohorts remain separate; there is no filtering, pooling, normalization to the twin, significance claim or causal attribution.

SQL reports full EXPLAIN executor time, whole-command backend CPU and client wall separately. The actual-AM loop reports its own process CPU and monotonic wall plus whole-command CPU/client wall. The decoder loop reports allocation/materialization/pfree process CPU plus whole-command CPU/client wall. Decoder compression and the full valid-output oracle are outside its inner timer, and are included in the whole-command metrics. These boundaries must not be treated as interchangeable. Literal commands execute separately before each measurement and serve as extra warming, identically for every role. Both literal journals and raw measured replies are fsynced before acceptance/parsing; all warm and retained observations must validate.

Use the same qualified build root and seed that the current ordinary SQL/decoder gate checked, plus the successful untimed callback-probe r2 receipt. On a new host, build and qualify again in a new namespace; never substitute new ELF hashes into old measured receipts. Stage the screen input files under the same parent as `build-harness`, `build-source` and `qualification`, then use fresh output/ports:

```sh
python3 -B screen/campaign.py --stage prepare \
  --build /owned/build-r1 --qualified /owned/qualification-r1 \
  --callback-probe /owned/cache-probe-r2 --output /owned/screen-r1 \
  --first-port 45640 --cpu-pairs 0:4,4:0 \
  --environment-label SHARED_LOAD_DIAGNOSTIC

python3 -B screen/campaign.py --stage smoke \
  --build /owned/build-r1 --qualified /owned/qualification-r1 \
  --callback-probe /owned/cache-probe-r2 --output /owned/screen-r1 \
  --first-port 45640 --cpu-pairs 0:4,4:0 \
  --environment-label SHARED_LOAD_DIAGNOSTIC
```

Prepare creates and fsyncs all fifteen numeric copies before any assignment: five separate smoke copies and ten accepted copies. Smoke runs all 205 role/case observations, accepts zero performance samples, stops every own cluster/client, and checks that all ten accepted copies still equal the frozen seed inventory. Its full observations remain available. An external root review must check the smoke evidence, unused copies, cleanup and source/ELF freeze before the fixed run. The review JSON must say `PASS_SMOKE_REVIEW_FOR_FIXED_RUN` and bind `smoke_status_sha256`, `freeze_sha256` and `environment_label`. It is never generated automatically by this harness.

```sh
python3 -B screen/campaign.py --stage run \
  --build /owned/build-r1 --qualified /owned/qualification-r1 \
  --callback-probe /owned/cache-probe-r2 --output /owned/screen-r1 \
  --first-port 45640 --cpu-pairs 0:4,4:0 \
  --environment-label SHARED_LOAD_DIAGNOSTIC --review /owned/PARENT-SMOKE-REVIEW.json

# Only after the complete outer stage and both cohorts PASS/stopped:
python3 -B screen/analyze.py /owned/screen-r1/cohort0 /new/local/analysis0
python3 -B screen/analyze.py /owned/screen-r1/cohort1 /new/local/analysis1
```

The controller retains its original allowed CPU set. Each postmaster and its inherited background workers run on that cohort's server CPU; each runner/client runs on the client CPU. All selected CPUs must be allowed. Actual guest topology and host load are recorded before stages/cohorts and afterwards. Guest CPU labels do not establish independent physical resources. VM84's foreign load is left untouched, and no own compiler or software profiler may overlap smoke or the fixed run. A future clean host campaign needs a fresh explicit lease and separate provenance.

The strict analyzer verifies the entire row order, all literals/plans/index loops, native counts/checksums and every warm/retained observation before emitting statistics. Per cohort it emits 650 absolute groups and 1300 pair groups (13000 direct pairs), with three SQL/decoder metrics and four actual-AM metrics. Raw JSONL may be split only at whole-line boundaries for publication, with an ordered concatenation/hash receipt; retain original raw hashes and a restore script. Do not publish binaries, PGDATA or full runner logs.
