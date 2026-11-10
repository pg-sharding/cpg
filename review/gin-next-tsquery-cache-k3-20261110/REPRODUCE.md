# K3 independent replay instructions — new frontdoor not executed

`reference-inputs/` contains the exact 63 text files required by the original
build, qualification and timing manifests. `replay.py` is a new portable stage
frontdoor: it copies those bytes into a new owned namespace, runs the unchanged
controllers with new paths, and uses their newly produced prefix/ELF/header/
source/seed receipts. It does not rewrite an original controller, lower a source
pin, reuse the old PGDATA/ELF or label new output as old evidence. Only local
AST/help and input-source verification have been run for this new frontdoor;
no independent Linux build, gate, replay or timings have been performed with it.

The original controllers did execute on VM158. Their build/gate/smoke evidence
is separate in actual-compact-evidence/. The source input README files still
contain their historical prelaunch wording and original example paths; the
current instructions here use a fresh root and receipts instead.

Requirements: an owned Linux x86_64 host, Python3, GNU make, GCC (actual run was
Ubuntu GCC13.3), binutils/objdump, Perl, Bison/Flex, OpenSSL and zlib development
headers, ordinary PostgreSQL test prerequisites, roughly 12GiB free disk plus
space for fresh synthetic copies, and enough memory for the 3 GB address-space
cap per child. Actual flags: `-O2 -g -fno-lto`, `LDFLAGS=-fno-lto`, empty
CPPFLAGS, `--without-icu --without-readline --with-openssl`, release assertions
off / K3_assert on. All4 builds are clean common-path builds, make -j2,nice 10,
unchanged core239 and test_ginpostinglist each. The real toolchain/configure/
flags are saved in each new build receipt; other compilers are new evidence.

Obtain exact B72 locally, either an authentic source archive or an existing
local repository containing 72b9498df9a369e747f8d96efb5a6cd33c2451e2. The known
archive SHA256 is 8c074fcf94a17d381e2df4a2b0554b925d76a777acb7e2f8a508abe7dfd2bbc4,
30,740,147 bytes. The build script can create git archive from a local repository
with network disabled, and validates all 7726 source entries against the bundled
manifest before applying the complete byte-bound B/K1/K3 overlays. The same
opaque published prerequisite is included in every variant; do not substitute
an unbound tree. Canonical K3 and K1 patches are independent alternatives over
fixed B, not a series. No K2/D2/Heap/C9 combination is part of this replay.

Choose unused ports, guest CPU pairs and a new path without whitespace before
any stage. The examples below use the original prospective ports and role
protocol, but **a fresh namespace**, not the old VM path:

```sh
R=/tmp/gin-k3-independent-replay
python3 -B replay.py init --root "$R"
python3 -B replay.py build --root "$R" --source-archive /absolute/path/baseline.tar.gz --core-port 46140
# Alternative origin for the preceding build stage: --git /absolute/path/local-cpg
python3 -B replay.py qualify --root "$R" --gate-port 46200
```

The input copy stage requires a nonexistent R. Build creates B/K1/K3/K3_assert
fresh output; qualification creates a new seed from the exact setup.sql,
ordinary tables/indexes plus unchanged holdout data, and compiles each oracle
against its actual installed 907 private headers. No old support.so or PGDATA
is needed. It checks 40 ordered SQL cases, 7 prepared, 12 lifecycle, 11 exhaustive
native, 11 budget-native and11 generic fallback cases per variant and stops all
five clusters. Actual execution must PASS before any measurement stage.

```sh
python3 -B replay.py prepare --root "$R" --first-port 46340 --cpu-pairs 0:4,4:0 --environment-label SHARED_LOAD_DIAGNOSTIC
python3 -B replay.py smoke --root "$R" --first-port 46340 --cpu-pairs 0:4,4:0 --environment-label SHARED_LOAD_DIAGNOSTIC
```

Preparation compiles the unchanged actual-AM helper and creates/fsyncs all 12
numeric copies before roles. Smoke uses 4 only and emits 92 raw observations,
zero accepted samples, and stops; 8 accepted copies remain untouched. Independently
review the complete smoke records/plans/literals/AM totals,100 ordered oracles,
exact B/T ELF, source/header/install bindings, seed and 8 unused inventories,
physical births, CPUs, host state and all owned PID/socket/control shutdowns.
The frontdoor never manufactures an approval. Only after that actual review,
write an external JSON receipt with status PASS_SMOKE_REVIEW_FOR_FIXED_RUN,
smoke_status_sha256,freeze_sha256 and the same environment_label. Compute hashes
from this new namespace, never copy the old PASS receipt.

A fresh host without competing work may be labelled FRESH_HOST_CLEAN_SCREEN
only after real load/topology/lease checks; use that same label in all prepare,
smoke,review and run commands. The original CPU pairs 0:4 then4:0 are recorded
logical guest CPUs, not a claim about isolated physical CPUs.

```sh
python3 -B replay.py run --root "$R" --first-port 46340 --cpu-pairs 0:4,4:0 \
  --environment-label SHARED_LOAD_DIAGNOSTIC --review /absolute/path/new-smoke-review.json
python3 -B replay.py analyze --root "$R"
```

Commands use separate stages and cannot automatically promote smoke. Only run
has the 2576 raw/2208 retained/368 warm matrix, with 23 exact cells, 4 roles, 2 warm
+ 12 retained rounds, 2 fresh cohorts and all 6 pairs. SQL reports whole backend
CPU,client wall and EXPLAIN Execution Time; actual-AM reports whole CPU/client
and inner AM-loop CPU/wall. The inner clock includes bitmap create,actual
index_rescan/AM consumption/bitmap free. Literal commands immediately before
measurements are explicit extra warming. Every raw row is durable before
validation. No trimming,pooling,normalization,significance or causal claim.

After full PASS, each analyzer creates 304 absolute groups, 456 pair groups and
5472 direct pairs per cohort. Keep all dense/short/NOT/phrase/rare/absent/Seq/
lossy controls and all IO/runqueue/fault diagnostics. Fresh replay results must
remain separately labelled even if they resemble original observations.

The completed original build/qualification and screen evidence is included.
Offline numerical replay needs Python3 only, with no server or new frontdoor:

```sh
python3 -B restore-raw.py --out-new /tmp/gin-k3-restored-original
python3 -B reference-inputs/timing-prep-r1/analyze.py /tmp/gin-k3-restored-original/screen/timing-r1/cohort0 /tmp/gin-k3-analysis0
python3 -B reference-inputs/timing-prep-r1/analyze.py /tmp/gin-k3-restored-original/screen/timing-r1/cohort1 /tmp/gin-k3-analysis1
python3 -B reference-inputs/audit-screen-independent-K3-r1.py --run-root /tmp/gin-k3-restored-original/screen/timing-r1 --analysis0 /tmp/gin-k3-analysis0 --analysis1 /tmp/gin-k3-analysis1 --out-new /tmp/gin-k3-independent.json
python3 -B reference-inputs/audit-qualification-r1.py --collection /tmp/gin-k3-restored-original/build-qualification --output-new /tmp/gin-k3-qualification-audit
```

Use new nonexistent output paths. restore-raw.py checks all503 original remote
collection bindings, including exact whole-line chunks and concatenated stream
hashes. The complete frozen analyses in analysis/cohort0 and analysis/cohort1
must reproduce byte-for-byte. Root executed this restore/reanalysis locally;
that verifies the published observations and arithmetic, not a fresh PostgreSQL
runtime. ROOT-PACKET-RESTORE-REPLAY-r1.json records the actual checks.
