# Fixed uint16 offset-fragment micro

This separate harness measures the exact baseline linear offset loop and the
frozen bitmap prototype's short path, galloping search and upper bound. It
uses actual PostgreSQL `GinScanEntryData` and `OffsetNumber` headers. It is
an extracted-fragment experiment, not a full GIN AM benchmark. The separate
SQL and real-AM screens retain their own results and negative controls.

The prototype is unchanged: `cc5c47d525e01a7eb6af7b6d6fed66fcbde5d7f9`,
independent over fixed B `8a8c475037bfde101da23cc9b0364c9c020eca93`.
The opaque common prerequisite is identical in both sources. This harness
does not investigate that prerequisite. Exact source SHA checks and fragment
anchors are in `prepare-fragments.py`; original source snapshots are in
`inputs/`. The previously completed valid-offset normal/UBSan oracle and
ordinary AM/SQL qualifications are separate prerequisites, not new runs here.

The fixed 15 cells are n=8/64/291 crossed with skip=0/1/2/4/(n-1), using
sorted dense valid uint16 offsets and 250,000 calls per command. Each child
executes one oracle check before its kernel clocks and verifies its checksum
afterward. Both wrappers are `pg_noinline`; a common volatile function
pointer is loaded and called on every iteration. Its overhead remains in
all roles. B and exact twin T select the same baseline function and arguments
in the same executable; Bitmap selects the candidate function in that same
executable. No production binary is replaced or instrumented.

Kernel clocks are process CPU and monotonic wall, excluding child startup,
array initialization, validation and JSON output. Outer child CPU and elapsed
wall include startup. These clock scopes remain separate. The command starts
a new child each time; there are no database clusters in this micro. Normal
ASM must be independently checked for the indirect call inside the actual
250,000-iteration loop before a timing run is allowed.

The smoke has one warm command per cell/role: 45 raw and zero retained.
Only after a separate review may the fixed screen run two fresh placements,
two warm and six retained rounds, with all six role permutations once per
retained cycle: 720 raw / 540 retained / 180 warm. CPU 0 runs the kernel while
CPU 4 controls cohort 0; cohort 1 swaps them and reverses cell order. There
is no automatic promotion, repeat, trimming, pooling or twin normalization.
No compiler or other timing workload may overlap either phase.

Preparation and timing require Linux, GCC/binutils, Python 3 and `taskset`.
Use the exact previously qualified immutable bitmap build. Compilation reads
its `pg_config` flags and installed headers; all 907 B/Bitmap release headers
must match. No full backend rebuild is done by this frontdoor.

```sh
ROOT=/home/reshke/allfuzz/gin-next-c11-bitmap-20261110
INPUTS="$ROOT/offset-micro-inputs-r2"
nice -n 10 python3 -B "$INPUTS/prepare-build.py" \
  --build "$ROOT/bitmap-build" --qualified-from "$ROOT/bq-r1" \
  --output-new "$ROOT/offset-micro-build-r2"
# Stop here. Independently inspect normal-ASM.txt, including main's loop.
```

The independent review JSON must have status
`PASS_INDEPENDENT_OFFSET_MICRO_CODEGEN_REVIEW`, exact `executable_sha256`,
`asm_sha256`, `source_sha256`, and `indirect_call_each_kernel_iteration=true`.
That receipt is a separate provenance artifact, not generated as a PASS by
the build script.

```sh
nice -n 10 python3 -B "$INPUTS/run.py" --build "$ROOT/bitmap-build" \
  --micro-build "$ROOT/offset-micro-build-r2" \
  --codegen-review "$ROOT/OFFSET-MICRO-CODEGEN-REVIEW-r2.json" \
  --output-new "$ROOT/offset-micro-smoke-r2" --mode smoke
# Review the zero-retained smoke and quiet host, then separately approve:
nice -n 10 python3 -B "$INPUTS/run.py" --build "$ROOT/bitmap-build" \
  --micro-build "$ROOT/offset-micro-build-r2" \
  --codegen-review "$ROOT/OFFSET-MICRO-CODEGEN-REVIEW-r2.json" \
  --output-new "$ROOT/offset-micro-screen-r2" --mode screen
```

Current state: local AST/help and exact fragment replay only. No compiler,
micro smoke or micro screen has executed. The earlier extension-style local
draft was replaced before any compilation; only this standalone source is
submitted for the frozen compile gate. Performance findings from an extracted
fragment cannot establish a full-AM or SQL improvement, concurrency safety,
or a general merge recommendation. Preserve skip-0/1/2/4 negatives as well
as large-skip gains.

The r1 importer failed before compilation because it assumed include/server.
This r2 resolves the actual staged server header paths with each pg_config,
requires both paths inside their corresponding prefixes, and still requires
exactly 907 identical server headers. Production and fragment C bytes, cases,
loops, roles and timing protocol are unchanged. See ERRATUM-r1.json.
