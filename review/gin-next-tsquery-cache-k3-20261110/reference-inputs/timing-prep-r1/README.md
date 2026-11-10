# K3 four-role finite timing preparation

Status: local AST/help/static protocol checks only. No new runtime or timing
execution is claimed. Root must review this capsule and the completed four
build/qualification receipts before importing or launching it. All earlier
K1/K2/S1/D1 artifacts remain unchanged.

Install these inputs under the existing namespace's `inputs/timing-prep-r1/`,
next to its byte-bound `build-harness/`, `qualification/` and `source/` inputs.
The namespace is `/home/reshke/allfuzz/gin-cache-k3-20261110`; root owns its lease,
all artifact transfers and process launches. Build output is `build-r1`, gate
output `qualification-r1`; use a new nonexistent `timing-r1` output.

Roles are B and exact same B ELF/entrypoint twin T, K1 and K3. Source commits
are fixed B `8a8c475037bfde101da23cc9b0364c9c020eca93`, K1
`9e0d6e84c5bd538e58a534c99cb39ca669c567b7` and K3
`ec32d586cf3bb6cfa76eb672db70160b436ce47c`. The common prerequisite is identical
and opaque. No decoder candidate, decoder combination or new source tuning is
part of this campaign.

The exact original 16 SQL and 7 actual-AM cells, answers, literals, fixture,
query settings, validator, session metric boundaries and native C are retained.
All 25 ordered SQL oracle queries are checked in every role before samples.
The actual-AM inner loop includes bitmap creation, index_rescan, AM consumption
and bitmap free. It reports CPU and wall separately from whole-command backend
CPU and client wall. SQL reports whole-command backend CPU, client wall and
EXPLAIN Execution Time separately. Literal execution immediately before each
measured command is an explicit extra warm execution. Every literal journal
and full measured raw record is flushed/fsynced before validation; bad rows
are preserved and fail the attempt. No filters, trimming, pooling, twin
normalization, significance or causal attribution are introduced.

Retained orders are this Williams block repeated three times:

1. B, T, K3, K1
2. T, K1, B, K3
3. K1, K3, T, B
4. K3, B, K1, T

The first two block orders are warmups; retained rounds restart at block zero.
Every retained role-position and ordered adjacency occurs three times. There
are 2 warm + 12 retained rounds per cell, 2 separate cohorts: 2576 raw,
2208 retained, 368 warm. Each cohort has 304 absolute groups, 456 pair groups
and 5472 direct pairs; all six role pairs and all metric boundaries remain.
Cohort1 reverses cell order and numeric-copy role births. All negative cells
remain: dense/no-reuse, phrase, NOT, absent, inline, rare, prefix, JSONB,
lossy/recheck and unchanged Seq.

Preparation compiles the unchanged actual-AM helper once against actual B
headers, then creates/fsyncs all 12 numeric clones before assigning any role.
The first four are smoke-only; the remaining eight are untouched accepted
copies. Smoke executes all 23 cells ×4 roles =92 raw rows with zero accepted
samples, stops every owned smoke cluster, verifies all eight accepted copies
still equal the seed, and exits. It never starts accepted samples. An external
root-authored PASS_SMOKE_REVIEW_FOR_FIXED_RUN receipt binding smoke status,
freeze and environment label is mandatory for the separate run stage.

Default ports are 46340..46343 for smoke and 46350..46357 for the two cohorts.
All processes use nice10. Server/client affinity defaults to 0:4 then 4:0;
root may choose a different allowed pair before preparation and freezing.
The topology, affinity, load and memory state are recorded; guest logical
CPUs must not be described as independent physical cores without evidence.
512MB shared buffers, 64MB work_mem, system timing clock, parallel/JIT/memoize
and autovacuum off are retained. There may be no own compiler/profile overlap
with timing. Root must freshly confirm the VM lease and competing work before
using FRESH_HOST_CLEAN_SCREEN; otherwise retain SHARED_LOAD_DIAGNOSTIC.

After root review/import and all four builds/gate PASS, the concrete separate
commands are:

```sh
R=/home/reshke/allfuzz/gin-cache-k3-20261110
python3 -B "$R/inputs/timing-prep-r1/campaign.py" --stage prepare \
  --build "$R/build-r1" --qualified "$R/qualification-r1" \
  --output "$R/timing-r1" --first-port 46340 --cpu-pairs 0:4,4:0 \
  --environment-label FRESH_HOST_CLEAN_SCREEN
python3 -B "$R/inputs/timing-prep-r1/campaign.py" --stage smoke \
  --build "$R/build-r1" --qualified "$R/qualification-r1" \
  --output "$R/timing-r1" --first-port 46340 --cpu-pairs 0:4,4:0 \
  --environment-label FRESH_HOST_CLEAN_SCREEN
```

Stop for root's independent actual smoke/literal/plan/loop/source/ELF/copy/
shutdown review. Only after its explicit reviewed receipt:

```sh
python3 -B "$R/inputs/timing-prep-r1/campaign.py" --stage run \
  --build "$R/build-r1" --qualified "$R/qualification-r1" \
  --output "$R/timing-r1" --first-port 46340 --cpu-pairs 0:4,4:0 \
  --environment-label FRESH_HOST_CLEAN_SCREEN \
  --review "$R/ROOT-SMOKE-REVIEW-K3-r1.json"
```

Each stage independently checks full install/source inventories, fixed source
identities, build and gate input manifests/receipts, declared untimed gate
counts, stopped gate clusters/PIDs, seed and AM binding. The outer finally
attempts every owned cluster stop even after another cleanup failure. Runner
client cleanup is separate and bounded. No unrelated PID is signaled.
Preserve failed attempts; no implicit retry or automatic accepted run exists.

Only after complete PASS, root collects bounded raw/journals/plans/meta and
runs the frozen analyzer locally into new paths:

```sh
python3 -B inputs/timing-prep-r1/analyze.py collected/timing-r1/cohort0 analysis-cohort0
python3 -B inputs/timing-prep-r1/analyze.py collected/timing-r1/cohort1 analysis-cohort1
```

The analyzer validates every warm and retained row, full schedule, literals,
plan loops and raw hashes before producing all absolutes and same-round pairs.
It uses the declared retained count12. K1's historical stale-count analyzer
failure and accepted minimal r2 correction are preserved separately; this
new analyzer is a prospective four-role adaptation of that corrected analyzer.
No independent Linux replay or clean-host result is claimed from local checks.
