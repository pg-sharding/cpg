# Exact local replay

Restore the already measured collection into a NEW local directory. This makes
no PostgreSQL call and creates no new performance observation:

```sh
python3 -B restore-raw.py --out-new /new/collected
python3 -B analysis-tools-K1-r2/analyze.py /new/collected/screen-r1/cohort0 /new/analysis0
python3 -B analysis-tools-K1-r2/analyze.py /new/collected/screen-r1/cohort1 /new/analysis1
python3 -B audit-screen-independent-K1-r1.py \
  --run-root /new/collected/screen-r1 --analysis0 /new/analysis0 --analysis1 /new/analysis1 \
  --out-new /new/independent-audit.json
```

Compare all six JSON outputs with analysis/cohort0 and analysis/cohort1. The
independent auditor imports no benchmark modules and independently reconstructs
schedule/literals/full plans/loops/AM totals, CPU/wall boundaries and all ratios,
differences, min/median/max/mean/sample stdev/MAD. The complete original analyzer
and its n==10 guard failure are retained; r2 only corrects that guard to the
six rounds already fixed in the protocol. It is a local postprocessing repair,
not a new timing attempt or changed sample selection. Every warm row must pass.

# A fresh independent Linux run

Use a NEW owned namespace and new output paths/unused ports. Do not substitute
new ELFs into historical receipts or call a new run these measurements. The
builder dynamically binds newly built source/headers/compiler/ELFs/install
inventories; qualifier and controller consume those new receipts. The frozen
source/fixture/answers/orders are unchanged. No old PGDATA or support library is
needed. Current scripts were executed on VM84; an independent Linux replay of
this front door has not been performed.

Dependencies: Linux x86-64, Python 3, GCC/make, Perl, bison/flex, OpenSSL development
files and taskset/lscpu/objdump. Source is raw B72
72b9498df9a369e747f8d96efb5a6cd33c2451e2, fixed B
8a8c475037bfde101da23cc9b0364c9c020eca93, K1
9e0d6e84c5bd538e58a534c99cb39ca669c567b7. The supplied common prerequisite is
identical and opaque. The actual raw archive SHA256 was
8c074fcf94a17d381e2df4a2b0554b925d76a777acb7e2f8a508abe7dfd2bbc4;
all 7726 files are independently checked against the base manifest before the
exact source overlays. Alternatively obtain B72 through the published branch:

```sh
git clone --single-branch --branch experiments/gin-next-tsquery-cache-v1-20261110 \
  https://github.com/pg-sharding/cpg.git /new/public-source
python3 -B bounded-exec.py python3 -B full-build-harness-r1/build.py \
  --git /new/public-source --source-plan full-build-source-r1/SOURCE.json \
  --output /new/owned/build-r1 --core-port 45740
python3 -B bounded-exec.py python3 -B full-qualification-r1/qualify.py \
  --build /new/owned/build-r1 --output /new/owned/qualification-r1 --first-port 45800
```

The three serial builds are fully clean B/K1/K1_assert using the same source,
build and compiled-prefix paths with separate DESTDIR installs. GCC flags are
CFLAGS=-O2 -g -fno-lto, LDFLAGS=-fno-lto, empty CPPFLAGS; configure without ICU/
readline, with OpenSSL, cassert off for release and on for K1_assert. nice 10,
make -j2, RLIMIT_AS 3000000000 (bounded-exec sets priority/limit). Core239 uses
MAX_CONNECTIONS=2, unchanged expected files, plus test_ginpostinglist. Each actual
907-header inventory, complete prefix/ELF, 7726-source manifest, compiler/version/
flags and non-GIN release object identity are bound by the build receipt.

The full gate compiles native helpers against installed production headers and
calls actual installed ginInitConsistentFunction. It checks full ternary vectors,
two recheck sentinels/repeats, hidden/nine-entry fallback, complete ordered Seq/
GIN SQL, old literals, repeated prepared queries, lifecycle and VOLATILE custom
operator classes. No malformed input/concurrent actors or latency sampling is
part of that gate. Require full PASS, zero timing, no cleanup errors/all own
PIDs gone and no compiler/profile overlap before prepare.

Use the separate prepare/smoke/run commands and complete metric contract in
SCREEN-REPRODUCE-K1-r1.md, with your new namespace. The actual campaign used
port 45840 smoke and 45850..45855 accepted, allowed guest server/client 0:4 then 4:0,
512MB shared_buffers, 64MB work_mem, system clock, JIT/parallel/memoize off,
nice 10. Host topology/load is recorded. Select/freeze allowed pairs and honest
environment label before prepare; SHARED_LOAD_DIAGNOSTIC is required for shared
load. Guest labels do not prove independent physical resources. No own compiler
or profiler overlaps smoke/run; foreign work is left untouched.

Prepare hashes/fsyncs all nine numeric copies before roles: three smoke and six
accepted. Complete smoke is 69 rows/zero accepted timings; all clients/clusters
must stop and all six accepted copies remain unused/equal to seed. An external
root/human review must independently check raw/plans/loops/answers, source/ELF/
seed/helper/copies/PIDs and bind smoke_status_sha256/freeze_sha256/environment
with status PASS_SMOKE_REVIEW_FOR_FIXED_RUN. No automatic acceptance follows.
Only then run the separately reviewed fixed command.

The fixed matrix is exactly 16 SQL +7 actual-AM cells x3 roles x(2 warm +6 retained)
x2 fresh cohorts =1104 raw /828 retained /276 warm. Six balanced orders are fixed
by protocol.py; cohort1 reverses case and physical birth order. B/T use the same
prefix/ELF/entrypoint. Every literal is an extra separate warm command before
measurement; raw/journal fsync precedes parse/assert. SQL complete EXPLAIN time,
whole-command backend CPU/client wall and actual-AM inner scan/rescan/bitmap
materialization/free CPU/wall are separate. There is no decoder metric/claim.

After full PASS and all source/three prefixes/ELFs/two seeds/AM module/frozen
inputs unchanged, all own PIDs/sockets gone, collect text/raw only and analyze
locally into NEW paths with the corrected analyzer above. Keep every negative,
all three direct pairs, cohorts separate and no trim/pooling/control
normalization/significance/causal attribution. Preserve failures. Publication
excludes binaries, PGDATA and full logs. New results retain separate provenance.
