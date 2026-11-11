# Reproduce the fixed K4 comparison

The publication packet keeps the proven layout at its root: build-harness/, build-source/, qualification/, timing-prep-r1/, both frozen manifests, root auxiliary scripts, source/, evidence-r1/, evidence-r2/ and separate analysis directories. Runtime inputs are staged into a new run root's inputs/ from the exact manifest union. Auxiliary scripts stay outside those inputs and are invoked from the packet root. Do not move frozen directories beneath tools/ or rename the evidence to fit a script.

R1 completed its gates but remains a complete shared-load diagnostic after foreign CPU work was observed at the tail. ROOT-R1-SHARED-LOAD-DECISION.json was saved before reading accepted-run timing values; smoke correctness outputs had already been reviewed. It requires a complete unchanged r2 repeat, with all r1 data preserved. This document does not establish a final speed result or require recreating that historical host interference.

Use a separate Linux x86-64 workspace. Prerequisites are Python 3.9+, Git, GCC, make, Perl, flex, bison, pkg-config, OpenSSL development files and the normal PostgreSQL build dependencies; the exact historical source revision determines its configured dependencies. Runtime needs Linux /proc, taskset, lscpu and two eligible CPUs. The monitor additionally needs an eligible spare CPU. No harness stage fetches or installs software. Actual pg_config/compiler receipts record all build flags.

Set K4_PACKET to the extracted, manifest-verified packet root and K4_ROOT to a new nonexistent run root. The supplied helper verifies and copies exactly the 45 manifest-listed files plus the two manifests, excluding auxiliary scripts, evidence and analyses. It refuses an existing destination. Source bytes and headers are already supplied as hash-bound canonical snapshots; do not regenerate commits or run MAKE-C-SOURCE-r1.py/prepare-runtime.py on the replay host.

```sh
K4_PACKET=/absolute/extracted/k4-publication
K4_ROOT=/absolute/new/gin-cache-k4-20261111
K4_B72_REPO=/absolute/existing/postgresql-repository
python3 -B "$K4_PACKET/stage-frozen-inputs.py" \
  --packet "$K4_PACKET" --destination "$K4_ROOT"
python3 -B "$K4_ROOT/inputs/build-harness/build.py" \
  --git "$K4_B72_REPO" \
  --source-plan "$K4_ROOT/inputs/build-source/SOURCE.json" \
  --output "$K4_ROOT/build-r1" --core-port 47100
```

The source repository must already contain B72 72b9498df9a369e747f8d96efb5a6cd33c2451e2. Alternatively replace --git with --source-archive /absolute/path/to/your-B72.tar.gz. Direct build.py validates all 7726 extracted source-file bytes and paths against the authentic manifest, without requiring the historical gzip representation. Later variant bytes come from canonical snapshots. Do not use the historical run-stages.py wrapper for fresh-host replay.

Build flags are -O2 -g -fno-lto, LDFLAGS=-fno-lto, OpenSSL, without ICU/readline. B/C/K3/K4 disable assertions; K4_assert enables them. All five builds are clean at the same source/build/compiled-prefix paths, with nice 10 and make -j2. GCC is required for backend and native modules because the runtime module commands invoke gcc. Preserve failed outputs instead of retrying over them. After PASS_GIN_K4_LAYOUT_BUILDS and successful cleanup:

```sh
python3 -B "$K4_ROOT/inputs/qualification/qualify.py" \
  --build "$K4_ROOT/build-r1" --output "$K4_ROOT/qualification-r1" \
  --first-port 47160
```

Qualification creates the deterministic setup.sql recipe using B, checks ordered Seq/GIN answers, prepared queries, write/delete/vacuum lifecycles, valid ternary vectors, exact budget boundaries and guarded generic fallback. Native modules use each variant's installed headers. Source/install/seed checks and shutdown proofs must pass before timing. These calls are correctness checks, not timing samples.

Choose two CPUs from actual topology and affinity. The recorded placement is server/client 0:4, then 4:0; substitute a valid fixed pair on another host before preparing its first attempt, then keep it fixed. Cohorts are placements on one host, not independent hosts. No build, profiler or other timed work should run alongside accepted measurements. Use SHARED_LOAD_DIAGNOSTIC unless an actual reviewed host window supports FRESH_HOST_CLEAN_SCREEN; the label itself proves no host condition.

```sh
K4_ENV=SHARED_LOAD_DIAGNOSTIC
K4_CPUS=0:4,4:0
python3 -B "$K4_ROOT/inputs/timing-prep-r1/campaign.py" \
  --stage prepare --build "$K4_ROOT/build-r1" \
  --qualified "$K4_ROOT/qualification-r1" --output "$K4_ROOT/timing-r1" \
  --first-port 47200 --cpu-pairs "$K4_CPUS" --environment-label "$K4_ENV"
python3 -B "$K4_ROOT/inputs/timing-prep-r1/campaign.py" \
  --stage smoke --build "$K4_ROOT/build-r1" \
  --qualified "$K4_ROOT/qualification-r1" --output "$K4_ROOT/timing-r1" \
  --first-port 47200 --cpu-pairs "$K4_CPUS" --environment-label "$K4_ENV"
```

Prepare makes/fsyncs 15 identical numeric copies before assignment: five smoke-only and ten untouched accepted copies. Smoke has 120 measured commands and zero accepted observations. Independently review its answers, complete plans/actual rows/loops/rechecks, expected GUCs, B/T identity, source/install/module/seed bindings, unused copies, CPU/host context and shutdown proofs. Create an actual external review receipt only after those checks pass. The required JSON is:

```json
{
  "status": "PASS_SMOKE_REVIEW_FOR_FIXED_RUN",
  "smoke_status_sha256": "SHA256 of this attempt's smoke-status.json",
  "freeze_sha256": "SHA256 of this attempt's freeze.json",
  "environment_label": "the identical value used at prepare and smoke"
}
```

Only after that actual review passes:

```sh
python3 -B "$K4_ROOT/inputs/timing-prep-r1/campaign.py" \
  --stage run --build "$K4_ROOT/build-r1" \
  --qualified "$K4_ROOT/qualification-r1" --output "$K4_ROOT/timing-r1" \
  --first-port 47200 --cpu-pairs "$K4_CPUS" --environment-label "$K4_ENV" \
  --review "$K4_ROOT/ROOT-SMOKE-REVIEW-K4-r1.json"
```

The first attempt uses core ports 47100..47104, posting 47130..47134, qualification 47160..47165, smoke 47200..47204 and accepted 47210..47219. Sockets are under K4_ROOT/s. Every path must be short enough for the existing 104-byte socket bound and contain no whitespace. All output roots are new; failures and partial evidence remain intact. The original run-stages.py and run-repeat-r2.py are historical VM controllers, with additional historical receipt/preflight assumptions. The direct portable route above does not depend on them.

A full unchanged repeat needs a fresh parent, not just a different timing basename. The frozen campaign creates socket directories under output.parent/s and refuses to reuse them. The actual r2 route is K4_ROOT/r2/timing-r2 and K4_ROOT/r2/s, with ports 47300..47304 for smoke and 47310..47319 for accepted cohorts. Never remove/reuse K4_ROOT/s or r1 directories. First verify all owned earlier lifetimes are stopped, source/build/qualification bindings still match, the new ports are free and competing work plus all builds/gates have ended. Keep all 24 cases, five roles, loops, orders, warm/retained rounds, flags and CPU pairs unchanged.

```sh
mkdir "$K4_ROOT/r2"
K4_TIMING_OUTPUT="$K4_ROOT/r2/timing-r2"
# Keep K4_CPUS fixed; set K4_ENV from the reviewed actual host window.
python3 -B "$K4_ROOT/inputs/timing-prep-r1/campaign.py" \
  --stage prepare --build "$K4_ROOT/build-r1" \
  --qualified "$K4_ROOT/qualification-r1" --output "$K4_TIMING_OUTPUT" \
  --first-port 47300 --cpu-pairs "$K4_CPUS" --environment-label "$K4_ENV"
python3 -B "$K4_ROOT/inputs/timing-prep-r1/campaign.py" \
  --stage smoke --build "$K4_ROOT/build-r1" \
  --qualified "$K4_ROOT/qualification-r1" --output "$K4_TIMING_OUTPUT" \
  --first-port 47300 --cpu-pairs "$K4_CPUS" --environment-label "$K4_ENV"
# Independently review actual r2 smoke, then create its own review JSON.
python3 -B "$K4_ROOT/inputs/timing-prep-r1/campaign.py" \
  --stage run --build "$K4_ROOT/build-r1" \
  --qualified "$K4_ROOT/qualification-r1" --output "$K4_TIMING_OUTPUT" \
  --first-port 47300 --cpu-pairs "$K4_CPUS" --environment-label "$K4_ENV" \
  --review "$K4_ROOT/ROOT-SMOKE-REVIEW-K4-r2.json"
```

The review hashes must bind r2/timing-r2/smoke-status.json and r2/timing-r2/freeze.json, not the r1 files. Preserve later interpretation changes separately from frozen intent labels. The actual repeat controller observes CPU consumers with host-load-monitor.py on CPU 6 every five seconds, bounded at 3600 seconds, without inspecting arguments or signalling foreign processes. Include that record and its review with the reported r2 attempt. Its endpoint/top-20 sampling cannot prove absence of short-lived CPU work or exact command overlap; it is no basis for trimming/normalizing individual observations. Root's reviewed run-repeat-r2.py contains its original launch/monitor/cleanup command details.

For a finished attempt, perform final owned-source/install/seed/module bindings and shutdown/socket checks before collecting. The adopted generic auxiliary tools are at packet root, outside frozen runtime:

```sh
python3 -B "$K4_PACKET/live-proof-r2.py" --root "$K4_ROOT" \
  --timing-name r2/timing-r2 --full \
  --output "$K4_ROOT/ROOT-LIVE-FINAL-replay-r2.json"
python3 -B "$K4_PACKET/collect-r2.py" --root "$K4_ROOT" \
  --timing-name r2/timing-r2 --output "$K4_ROOT/K4-text-evidence-r2.tar.gz"
```

For r1 use --timing-name timing-r1 and distinct r1 receipt/archive filenames. Collection preserves namespace-relative paths, excludes PGDATA/binaries and bounds selected text. Keep external decision/review/live/monitor receipts at K4_ROOT level so the collector includes them. Transfer the archive to a separate local review workspace. Preserve packet ROOT and its bundled analyses unchanged; write a new evidence/analysis tree with --analysis-root for the new review:

```sh
K4_REVIEW=/absolute/new/k4-local-review
mkdir "$K4_REVIEW"
mkdir "$K4_REVIEW/evidence-r2"
tar -xzf /absolute/path/to/K4-text-evidence-r2.tar.gz -C "$K4_REVIEW/evidence-r2"
python3 -B "$K4_PACKET/timing-prep-r1/analyze.py"   "$K4_REVIEW/evidence-r2/r2/timing-r2/cohort0" "$K4_REVIEW/analysis-cohort0-r2"
python3 -B "$K4_PACKET/timing-prep-r1/analyze.py"   "$K4_REVIEW/evidence-r2/r2/timing-r2/cohort1" "$K4_REVIEW/analysis-cohort1-r2"
python3 -B "$K4_PACKET/audit-results-r2.py" \
  --evidence "$K4_REVIEW/evidence-r2" --timing-name r2/timing-r2 \
  --analysis-root "$K4_REVIEW" --full --output "$K4_REVIEW/K4-audit-r2.json"
```

For r1, use evidence-r1/timing-r1, analysis-cohort0-r1 / analysis-cohort1-r1 and --timing-name timing-r1, preserving separate outputs. The root auxiliary audit reconstructs all spread/difference/direct arrays and requires exact 395-absolute/790-pair group keys per cohort; it shares the frozen protocol and raw validator. Independent r1 peer review additionally reconstructed all 114550 fields directly from raw JSON without importing those modules and checked all semantic/actual plans and expected settings. Name audit coverage and script hashes accurately.

Each complete attempt has 2880 measured raw observations, 2400 retained and 480 warm, with ten values per retained role/case and all ten role pairs preserved. Backend schedstat CPU/client monotonic wall cover whole commands. SQL Execution Time covers the complete executor command with its fixed probe loop; AM inner CPU/wall cover the actual rescan/getbitmap/tbm batch. Do not call whole batched SQL times single-probe latency. Preserve absolute times, arrays, min/max/mean/stdev/MAD, all direct pairs, regressions, exact-twin drift and host context. Keep r1 and r2 separate, without pooling, trimming or control normalization. Final interpretation requires the repeat and its own reviews.

To regenerate both supplied attempts without a PostgreSQL build or server, use the deterministic offline helper. It verifies frozen inputs and collections, regenerates each cohort separately, checks JSON equality against all bundled analysis files, then runs the adopted root auditor, direct-raw peer recount and all-metric renderer into a new directory outside the packet. It also works on an assembled, reviewed-but-unfrozen packet before the final MANIFEST is created:

```sh
python3 -B "$K4_PACKET/replay-offline.py" --packet "$K4_PACKET" \
  --out-new /absolute/new/k4-offline-replay
```

This performs no network, compiler, backend or benchmark calls. Its receipt records numerical reproduction only; host/monitor interpretation and publication review remain separate. Earlier readers and bundled evidence/analysis are never overwritten.
