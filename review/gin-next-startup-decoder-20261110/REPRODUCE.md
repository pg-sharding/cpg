# Replay the completed result locally

This replay executes the supplied frozen analyzer over already measured data;
it performs no PostgreSQL work and creates no new performance observations.
From the packet root, choose new output paths:

```sh
python3 -B restore-raw.py --out-new /new/restored-collection
python3 -B screen/analyze.py /new/restored-collection/screen-r1/cohort0 /new/analysis0
python3 -B screen/analyze.py /new/restored-collection/screen-r1/cohort1 /new/analysis1
python3 -B audit-screen-independent-r1.py \
  --run-root /new/restored-collection/screen-r1 \
  --analysis0 /new/analysis0 --analysis1 /new/analysis1 \
  --out-new /new/independent-audit.json
```

The restored collection is byte-exact to the completed actual collection.
Compare the new analysis JSON byte-for-byte with `analysis/cohort{0,1}/`.
All warm rows must pass before output is accepted. The independent audit imports
no benchmark modules and recomputes decoder checksums, metric extraction,
Williams order, means/medians/sample stdev/MAD and every direct ratio/difference.
It was actually executed locally on the completed 4920 observations.

# A new independent Linux campaign

The original controller paths/ELFs in measured evidence are historical bindings.
Do not replace them to label a new build as the old result. The supplied builder
creates fresh dynamic receipts in a new namespace; qualifier and controller read
those receipts and bind the new ELFs/headers/installs/source inventory. Keep
source snapshots, fixture/answers, counts and order unchanged. This front door
has not been independently replayed on a second Linux host; the original build,
qualification and screen scripts did execute on VM84 as described.

Use Linux x86-64, Python 3, GCC/make, Perl, bison/flex, OpenSSL development files,
and taskset/lscpu/objdump. Each of six serial builds is clean with the same source,
build and compiled-prefix path, separate DESTDIR installs, nice 10, make -j2 and
RLIMIT_AS 3000000000. Flags: `CFLAGS=-O2 -g -fno-lto`, `LDFLAGS=-fno-lto`, empty
CPPFLAGS; `--without-icu --without-readline --with-openssl`, release cassert off,
S1_assert/D1_assert on. Core239 uses MAX_CONNECTIONS=2; posting-list tests and
907 installed-header/source/ELF/object/complete-prefix checks are mandatory.
Expected files are never regenerated. No compilation/profiling overlaps timing.

Copy this packet's script/input tree into a new own namespace, without old
results or PGDATA, and run from its root. Obtain public B72 source (or a local
verified archive with all 7726 files). For example, the published S1 branch has
B72 and the common fixed B as ancestors:

```sh
git clone --single-branch \
  --branch experiments/gin-next-startup-empty-v1-root-20261110 \
  https://github.com/pg-sharding/cpg.git /new/public-source
python3 -B bounded-exec.py python3 -B build-harness/build.py \
  --git /new/public-source --source-plan build-source/SOURCE.json \
  --output /new/owned/build-r1 --core-port 45540
python3 -B bounded-exec.py python3 -B qualification/qualify.py \
  --build /new/owned/build-r1 --output /new/owned/qualification-r1 --first-port 45600
python3 -B bounded-exec.py python3 -B cache-untimed-evidence/probe-r2/probe.py \
  --startup-root "$PWD" --build /new/owned/build-r1 \
  --qualified /new/owned/qualification-r1 --output /new/owned/cache-probe-r2 \
  --first-port 45620
```

B72 is `72b9498df9a369e747f8d96efb5a6cd33c2451e2`; fixed B is
`8a8c475037bfde101da23cc9b0364c9c020eca93`. The source archive used in the actual
run has SHA256 `8c074fcf94a17d381e2df4a2b0554b925d76a777acb7e2f8a508abe7dfd2bbc4`.
The builder verifies every extracted file against the supplied base manifest,
then the exact frozen variant snapshots. The historical source-plan commit
identity fields stay unchanged; SOURCE-IDENTITY-CORRECTION-r1.json maps S1/D1 to
the same-tree root-authored canonical commits. Overlay replay is not a new port.

Review all three statuses and clean shutdowns before preparing timing. Use
unused ports and allowed server/client CPUs, record actual topology/load and
freeze the environmental label honestly. The actual run used 0:4 then 4:0,
512MB shared buffers, 64MB work_mem, system clock, JIT/parallel/memoize off.
Guest CPU IDs do not prove independent physical resources. On a shared host
use SHARED_LOAD_DIAGNOSTIC, leave foreign work untouched, and make no clean-host
claim. Full commands for the independent stages are in SCREEN-REPRODUCE.md:

```sh
python3 -B bounded-exec.py python3 -B screen/campaign.py --stage prepare \
  --build /new/owned/build-r1 --qualified /new/owned/qualification-r1 \
  --callback-probe /new/owned/cache-probe-r2 --output /new/owned/screen-r1 \
  --first-port 45640 --cpu-pairs 0:4,4:0 --environment-label SHARED_LOAD_DIAGNOSTIC
python3 -B bounded-exec.py python3 -B screen/campaign.py --stage smoke \
  --build /new/owned/build-r1 --qualified /new/owned/qualification-r1 \
  --callback-probe /new/owned/cache-probe-r2 --output /new/owned/screen-r1 \
  --first-port 45640 --cpu-pairs 0:4,4:0 --environment-label SHARED_LOAD_DIAGNOSTIC
```

All 15 numeric PGDATA copies are hashed/fsynced before assignments: five smoke
copies, ten accepted copies. The complete 205-row smoke accepts zero timing and
must stop all clients/clusters, prove unused accepted copies equal the seed,
retain every plan/count/checksum and receive a separate external human/root
review. The harness never generates approval automatically. The reviewer JSON
must contain status PASS_SMOKE_REVIEW_FOR_FIXED_RUN and exact smoke_status_sha256,
freeze_sha256 and environment_label. Only after that explicit review:

```sh
python3 -B bounded-exec.py python3 -B screen/campaign.py --stage run \
  --build /new/owned/build-r1 --qualified /new/owned/qualification-r1 \
  --callback-probe /new/owned/cache-probe-r2 --output /new/owned/screen-r1 \
  --first-port 45640 --cpu-pairs 0:4,4:0 --environment-label SHARED_LOAD_DIAGNOSTIC \
  --review /new/external-smoke-review.json
```

The fixed 41-cell matrix is 16 SQL +7 actual AM +18 actual decoder cases, five
roles, two warm +ten retained balanced rounds and two fresh cohorts: 4920 raw /
4100 retained /820 warm. Exact B/T same ELF/entrypoint, reverse physical births
and case order in cohort 1, all ten pairs, no trim/no normalization/no pooling.
Literal queries execute separately before every measure and are extra warming.
SQL metrics are full EXPLAIN execution, whole-command backend CPU and client
wall. AM metrics add actual inner scan/rescan/bitmap materialization/free CPU and
wall. Decoder inner CPU includes actual decode allocation/materialization/free;
compression and full output oracle are outside that inner clock and inside the
whole-command boundary. Positive/negative differences must be reported separately
for every metric; no decoder effect on an unmeasured C9 combination is implied.

After full PASS, verify every own cluster/client/PID/socket stopped, original
seed/source7726/six installs/modules/input freezes unchanged; preserve any failed
attempt without retry. Then analyze locally into new outputs using the commands
above and the frozen raw. Publication excludes binaries, PGDATA and full runner
logs. Original actual evidence and new independent results stay separate.
