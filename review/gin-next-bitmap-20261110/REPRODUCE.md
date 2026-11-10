# Repeat the independent Bitmap experiment

Use an ordinary non-root Linux account with an existing local PostgreSQL Git
repository containing exact B72
`72b9498df9a369e747f8d96efb5a6cd33c2451e2`. No baseline archive or network clone
is included or required. Both independent variants include the same opaque
common prerequisite; its handling is outside this performance experiment.
The `replay/build-source/SOURCE.json` plan and 7726-file baseline manifest
bind every source byte and the per-variant standalone overlays.

Dependencies are Python 3, GCC 13.3, GNU make/binutils, bison, flex, Perl,
`pkg-config`, `taskset`, OpenSSL and zlib development headers. The historical
builds used `-O2 -g -fno-lto`, `--without-icu --without-readline --with-openssl`,
release builds plus a candidate assert build, nice 10 and at most two build
jobs. Exact configure, compiler flags, versions, headers, source manifests,
ELFs, core tests and command receipts are retained under evidence/qualification.
All three builds are fresh and use the same source/build/configured-prefix
paths in turn, with distinct DESTDIR installations. Each runs 239 core tests
and the posting-list test without refreshing expected output.

Choose a short, nonexistent output directory without whitespace, unused ports
and CPU 0/4 availability. The fixed controllers intentionally reject another
CPU layout. A port/CPU adaptation on another machine needs a new reviewed
protocol and provenance, rather than silently changing the historical inputs.
Never point an output at a live or unrelated cluster.

```sh
PACKET=/absolute/path/to/this/packet
PGGIT=/absolute/path/to/existing/postgresql-git
RUN=/home/youruser/gin-bitmap-replay-r1
mkdir "$RUN"
python3 -B "$PACKET/replay/build-harness/build.py" --git "$PGGIT" \
  --source-plan "$PACKET/replay/build-source/SOURCE.json" \
  --output "$RUN/build" --core-port 45540
python3 -B "$PACKET/replay/oracle/run-property.py" --build "$RUN/build" \
  --output-new "$RUN/property-r1"
python3 -B "$PACKET/replay/campaign.py" --build "$RUN/build" \
  --output "$RUN/qualify-r1" --first-port 45500 --mode qualify
```

The build script alternatively accepts `--source-archive` for a local authentic
Git archive of exact B72. `--git` runs local `git archive` with network access
disabled. It does not change that repository's HEAD or worktree. No rebuild,
server or new Linux replay is performed by reading this packet.

The valid offset oracle checked all lengths 1..291, every cursor, every threshold 0..2048 and four dense/gapped/max-offset patterns. Normal and UBSan agreed on 350,600,292 caller cases and 268,681,332 helper cases. The ordinary gate checked 75 ordered Seq/GIN multisets and frozen scalar answers, 24 prepared comparisons, 27 real-AM calls and six extra low-memory prefix checks. Actual broad-prefix LossyHeapBlocks was 3624 in each variant.

The qualification frontdoor creates the exact 200,002-row synthetic fixture
from retained setup.sql, verifies frozen scalar answers and ordered row
multisets, then stops its owned clusters. The real-AM module invokes ordinary
index_rescan/index_getbitmap/tbm_free and compares counts with an independent
SQL oracle. No property-fragment result substitutes for those actual AM checks.

After all finite correctness gates PASS, inspect the quiet host, exact source,
installed trees and stopped seed. Preserve a new external binding receipt for
this new build/qualification. The historical timing-r1/EXTERNAL-BINDINGS.json
continues to describe the original VM158 run; it cannot approve a new runtime.
The controller accepts the newly qualified paths as explicit arguments and
records their new hashes. It never replaces historical receipts.

```sh
python3 -B "$PACKET/replay/timing-r1/campaign.py" --build "$RUN/build" \
  --qualified-from "$RUN/qualify-r1" --output "$RUN/smoke-r1" \
  --first-port 45500 --mode smoke
# Offline inspect all 36 warm commands, answers/plans, stops and bindings:
python3 -B "$PACKET/replay/timing-r1/review-smoke.py" \
  --collection "$RUN/smoke-r1" --output-new "$RUN/smoke-review-r1"
# Stop here until a separate quiet-window/zero-retained smoke review approves:
python3 -B "$PACKET/replay/timing-r1/campaign.py" --build "$RUN/build" \
  --qualified-from "$RUN/qualify-r1" --output "$RUN/screen-r1" \
  --first-port 45500 --mode screen
```

The screen has exactly 12 cases, B/T/Bitmap, two fresh numeric-clone
placements, two warm and six retained rounds, all six role permutations and
CPU 0/4 swaps: 576 raw / 432 retained / 144 warm. B/T share the exact same
baseline prefix/ELF. All clones are copied, fully hashed and fsynced before
role assignment. Every measured result/full plan is durably appended before
post-measurement acceptance checks. Fixed scalar/row answers precede timing.
All clusters are stopped in finally, and source/install/module/seed/input
identity is checked afterward. No compiler, profiler or another benchmark
may overlap. There is no automatic full-matrix promotion or repeat.

Kernel AM CPU/wall include startup and consumption. Whole-backend process
CPU, client elapsed wall and SQL executor time are separate columns. Six
same-round direct pairs per case/cohort give percentages as
`100*(right/left-1)`, with positive slower. Tables retain absolute min, median,
max, mean, sample SD and median absolute deviation, all role pairs and every
direct pair. Cohorts are not pooled, trimmed, corrected by the twin, or rerun.

For the archived original run, locally recount and rerender without any VM:

```sh
python3 -B "$PACKET/audit/audit-bitmap-or-screen.py" \
  --collection "$PACKET/evidence/screen-evidence-r1/bt-r1" \
  --harness "$PACKET/replay/timing-r1" \
  --build-receipt "$PACKET/evidence/qualification/bitmap-build/build-receipt.json" \
  --output-new /tmp/gin-bitmap-independent-new
python3 -B "$PACKET/audit/render-bitmap-or-screen.py" \
  --collection "$PACKET/evidence/screen-evidence-r1/bt-r1" \
  --candidate Bitmap --audit /tmp/gin-bitmap-independent-new/status.json \
  --output-new /tmp/gin-bitmap-tables-new
```

Historical source-freeze status labels are retained byte-for-byte as provenance;
actual later build/gate/smoke/screen results are under evidence and audit. The
packet contains no PGDATA, executables, shared libraries, private source
archive or full runner logs. Its portable command frontdoor has not been run
on a second Linux host. Finite serial correctness and this screen do not prove
concurrency behavior or general merge readiness. Independent candidates are
alternatives, not a series and not composed with C11.
