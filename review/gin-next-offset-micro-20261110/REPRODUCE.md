# Repeat the separate fragment micro

First use the main bitmap packet's REPRODUCE.md to build and qualify exact
B/Bitmap release plus Bitmap assert from an existing local B72 Git repository.
That main frontdoor supplies the full source manifest, flags/dependencies,
239 core tests per build, normal/UBSan valid-offset oracle, ordinary real-AM
and prefix/lossy SQL checks. It supports --git without shipping a baseline
archive. The micro supplement does not replace those prerequisites.

Linux, GCC/binutils, Python 3.9+ and taskset are required. Use the matching
build's pg_config flags and actual 907 identical B/Bitmap server headers.
Historical compilation used GCC13.3, -O2 -g -fno-lto and normal platform
Fortify/stack protection. Do not disable those protections. No compiler or
other benchmark may overlap accepted timing. CPU0/4 must be available;
a different CPU/port protocol needs a separately frozen adaptation.

Historical replay capsules bind historical build and gate SHA values. A new
build naturally has different provenance. Create a new capsule with the helper
below rather than rewriting any frozen source, result or original receipt:

```sh
SUPPLEMENT=/absolute/path/to/this/supplement
RUN=/home/youruser/gin-bitmap-replay-r1
python3 -B "$SUPPLEMENT/bind-offset-replay.py" \
  --capsule "$SUPPLEMENT/replay/offset-micro-r2" --build "$RUN/build" \
  --qualified-from "$RUN/qualify-r1" --output-new "$RUN/micro-inputs-new"
python3 -B "$RUN/micro-inputs-new/prepare-build.py" --build "$RUN/build" \
  --qualified-from "$RUN/qualify-r1" --output-new "$RUN/micro-build-new"
```

The helper only verifies source/commit/status and receipt chains, copies new
inputs and updates their explicit external binding. It does not compile,
qualify a database, run a micro, or manufacture a PASS. The copied source,
fragments, cases and loops remain exact. prepare-build checks installed
binaries/trees and headers, compiles normally and stops before any micro run.

Independently inspect micro-build-new/normal-ASM.txt. In main, verify the
250,000-count loop resets entry.offset, reloads the volatile function pointer,
executes its indirect call, consumes the result and takes a loop backedge.
Check both wrappers and source fragment SHA bindings. Only after that actual
review write a new review JSON with these exact fields, from actual receipts:

```json
{
  "status": "PASS_INDEPENDENT_OFFSET_MICRO_CODEGEN_REVIEW",
  "executable_sha256": "actual value from micro-build-new/status.json",
  "asm_sha256": "actual value from that receipt",
  "source_sha256": "actual value from that receipt",
  "indirect_call_each_kernel_iteration": true
}
```

This is a human review attestation, not a template claiming a new PASS.
Do not reuse the original VM's executable/ASM review hashes for a new build.
Then run only the zero-retained smoke, review all 45 commands and source/host
bindings, and stop before any fixed screen approval:

```sh
python3 -B "$RUN/micro-inputs-new/run.py" --build "$RUN/build" \
  --micro-build "$RUN/micro-build-new" --codegen-review "$RUN/micro-review-new.json" \
  --output-new "$RUN/micro-smoke-new" --mode smoke
python3 -B "$SUPPLEMENT/audit/audit-offset-micro.py" \
  --collection "$RUN/micro-smoke-new" --output-new "$RUN/micro-smoke-audit-new"
# Separately approve the quiet host and fixed protocol, then:
python3 -B "$RUN/micro-inputs-new/run.py" --build "$RUN/build" \
  --micro-build "$RUN/micro-build-new" --codegen-review "$RUN/micro-review-new.json" \
  --output-new "$RUN/micro-screen-new" --mode screen
python3 -B "$SUPPLEMENT/audit/audit-offset-micro.py" \
  --collection "$RUN/micro-screen-new" --output-new "$RUN/micro-audit-new"
```

The fixed run is 720 raw / 540 retained / 180 warm commands across two CPU
placements. Each command uses a new child with actual PG types and exact
fragments. B and T have identical executable and arguments; Bitmap differs
only by selector1. All six role permutations occur per retained cycle.
Cohort1 reverses cell order and swaps CPU0/4. There is no automatic promotion,
repeat, retune, trim, pooling or control normalization. Raw stdout/status and
outer clocks are written/fsynced before post-run acceptance checks.

The kernel clock is process CPU and monotonic wall around 250,000 indirect
calls, excluding startup, array initialization, validation and JSON. Outer
CPU/wall include child startup. Reports never combine those clock scopes.
Absolute min/median/max/mean/sample SD/MAD and six same-round direct pairs
are retained per cohort/cell/role/metric. Percent is 100*(right/left-1), with
positive slower. The experiment is a fragment diagnostic, not a SQL proxy.

To repeat only the original offline calculation, without any Linux job:

```sh
python3 -B "$SUPPLEMENT/audit/audit-offset-micro.py" \
  --collection "$SUPPLEMENT/evidence/screen-r2/offset-micro-screen-r2" \
  --output-new /tmp/gin-offset-independent-new
python3 -B "$SUPPLEMENT/audit/render-offset-micro.py" \
  --audit /tmp/gin-offset-independent-new \
  --collection "$SUPPLEMENT/evidence/screen-r2/offset-micro-screen-r2" \
  --output-new /tmp/gin-offset-report-new
```

The original smoke/screen and their normal-codegen gate ran on VM158. The
new replay helper was checked only by AST/help and an offline metadata-only
exercise using original actual receipts. No fresh Linux replay or second-host
performance is claimed. Original failed r1 and corrected r2 capsules remain
immutable. The supplement contains no executable, PGDATA or full runner log.
