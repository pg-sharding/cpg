D2 fresh Linux replay

The historical four clean builds, ordinary qualification, 100-command smoke and
fixed 2,800-command screen ran on VM158. The small `replay.py` frontdoor in this
directory has only passed local Python AST, `--help` and frozen-file checks. It
has not itself run a new Linux build, server, qualification or benchmark.

Use a Linux x86-64 host with Python 3.9 or newer, GCC, GNU make, binutils, Git,
Perl, Bison/Flex and OpenSSL development files already installed. GCC 13.3.0 was
used historically. The builder disables ICU/readline, enables OpenSSL, uses
`-O2 -g -fno-lto` and `LDFLAGS=-fno-lto`, and builds pageinspect, intarray,
amcheck and pg_trgm. It performs four serial clean builds with make `-j2` and
nice 10. The frontdoor imposes a 3,000,000,000-byte address-space cap before
starting children, including psql. No package installation or network access is
part of replay. Run as an ordinary unprivileged user with local trust sockets.

The input directory must contain the three unchanged manifests and all 39
members they list. The baseline archive is intentionally omitted. An existing
Git repository containing exact raw B72
`72b9498df9a369e747f8d96efb5a6cd33c2451e2` is sufficient. Git archive output is
validated against all 7,726 source hashes, not against a gzip representation.
Alternatively use an existing authentic B72 archive with those exact files.
The original gzip was SHA256
`8c074fcf94a17d381e2df4a2b0554b925d76a777acb7e2f8a508abe7dfd2bbc4`.

```sh
I=/absolute/path/to/packet/inputs
F=/absolute/path/to/packet/fresh-replay-r1/replay.py
python3 -B "$F" --inputs "$I" --static-check
python3 -B "$F" --inputs "$I" --git /existing/postgresql/repository \
  --output /tmp/dec-d2-r1 --core-port 46900 --qual-port 46960
# Alternative origin: replace --git ... with --source-archive /existing/B72.tar.gz
```

The output must not exist. Use a short output root and 13 unused ports:
46900..46903 for core regression, 46930..46933 for posting-list tests and
46960..46964 for qualification. The builder extracts exact B72, applies the
source snapshots, and builds B/D1/D2/D2_assert in the same configured source,
build and prefix paths with separate DESTDIR installations. The source plan
pins fixed B `8a8c475037bfde101da23cc9b0364c9c020eca93`, canonical D1
`c2b5dd6f9012cc4a27628c9d6c507ac467795ac5`, and D2
`a85a9242f455b12c93528f3ace33eb69b6cd1008`. D1 and D2 are alternatives over B,
not consecutive patches. The common prerequisite is identical in all trees.

Every build must pass unchanged core239 and the posting-list test. Release
backend objects may differ only in ginpostinglist.o; the assertion build is
excluded from release object equality. Actual source inventories, 907 installed
headers per build, flags, ELF hashes and normal full-TU assembly are saved.
The unchanged native helper exercises 18 valid decoder cases, 13,152 items per
build. Ordinary qualification checks 40 ordered SQL cases, seven prepared
comparisons and 12 serial lifecycle comparisons per build against historical
fixed-B references and freshly executed Seq/index paths. No expected files are
regenerated. This finite serial scope is not a concurrency or general merge
qualification. Failure paths retain evidence and attempt only owned cleanup;
there is no automatic retry. The frontdoor bypasses the historical
`run-qualification-r1.py` wait wrapper, whose namespace and build PID are fixed.

Timing remains a separate reviewed operation. After a quiet-host/CPU-topology
inspection and all builds/gates/stops passing, use the unchanged campaign:

```sh
R=/tmp/dec-d2-r1
P="$I/timing-prep-r1/campaign.py"
python3 -B "$P" --stage prepare --build "$R/build-r1" \
  --qualified "$R/qualification-r1" --output "$R/timing-r1" \
  --first-port 47000 --cpu-pairs 0:4,4:0 --environment-label FRESH_HOST_CLEAN_SCREEN
python3 -B "$P" --stage smoke --build "$R/build-r1" \
  --qualified "$R/qualification-r1" --output "$R/timing-r1" \
  --first-port 47000 --cpu-pairs 0:4,4:0 --environment-label FRESH_HOST_CLEAN_SCREEN
python3 -B "$I/timing-prep-r1/review-smoke-r1.py" \
  --timing-root "$R/timing-r1" --output "$R/independent-smoke.json"
# Stop here for independent semantic review and live source/prefix/PID/socket/
# untouched-eight-copy checks. The offline smoke receipt is not run approval.
# REVIEW must be that independent reviewer's actual, newly generated approval.
python3 -B "$P" --stage run --build "$R/build-r1" \
  --qualified "$R/qualification-r1" --output "$R/timing-r1" \
  --first-port 47000 --cpu-pairs 0:4,4:0 --environment-label FRESH_HOST_CLEAN_SCREEN \
  --review "$REVIEW"
python3 -B "$I/timing-prep-r1/analyze.py" "$R/timing-r1/cohort0" "$R/analysis0"
python3 -B "$I/timing-prep-r1/analyze.py" "$R/timing-r1/cohort1" "$R/analysis1"
python3 -B "$I/timing-prep-r1/audit-independent-r1.py" --run-root "$R/timing-r1" \
  --analysis0 "$R/analysis0" --analysis1 "$R/analysis1" \
  --answers "$I/qualification/inputs/answers.json" --out-new "$R/independent.json"
```

The external approval has exactly these required fields:
`status` = `PASS_SMOKE_REVIEW_FOR_FIXED_RUN`, `freeze_sha256`,
`smoke_status_sha256`, and `environment_label`. It must be newly written by the
reviewer after inspecting the actual 100 smoke/literal records, all native
checksums, seven full SQL signatures/cardinalities and 25 per-case settings,
100 ordered Seq/index comparisons, B/T prefix/ELF/module identity, the four
smoke stops/PIDs/sockets, unchanged source/four installs/seed/modules/frozen
inputs, and all eight still-unused accepted copies against the seed inventory.
The reviewer must also inspect the host/topology and compiler/benchmark overlap.
The offline smoke auditor is one input to that review; it cannot create approval.
After those checks, this local command records hashes of the actual files
without changing the controller or inventing historical approval:

```sh
# Run only after the independent actual checks above have passed.
python3 -B - "$R" <<'PYAPPROVE'
import hashlib,json,pathlib,sys
r=pathlib.Path(sys.argv[1]); s=json.loads((r/'timing-r1/smoke-status.json').read_text())
f=json.loads((r/'timing-r1/freeze.json').read_text())
assert s['status']=='PASS_SMOKE_NEEDS_ROOT_REVIEW' and not s['cleanup_errors']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a={'status':'PASS_SMOKE_REVIEW_FOR_FIXED_RUN',
   'freeze_sha256':sha(r/'timing-r1/freeze.json'),
   'smoke_status_sha256':sha(r/'timing-r1/smoke-status.json'),
   'environment_label':f['environment_label']}
with (r/'review-approved.json').open('x') as output:
    json.dump(a,output,indent=2); output.write('\n')
PYAPPROVE
REVIEW="$R/review-approved.json"
```

Choose CPU pairs available on the new host and record physical topology before
prepare; retain those exact pairs through smoke/run. The historical 0:4 and
4:0 placements were different physical guest cores on one host. They are not a
second host. Timing requires another 12 fresh seed copies, four smoke-only and
eight accepted, all hashed/fsynced before assignment. Ports 47000..47003 and
47010..47017 must also be unused. Do not overlap compilation, profiling or other
timed jobs. A shared-load run requires that explicit label before freeze.

The 18 native cases use the old fixed loop counts. Their inner process CPU
includes allocation, materialization and free in the actual backend decoder;
compression and the full generated-TID oracle are outside that clock. Whole
backend command CPU and client wall are separate metrics. The seven SQL cells
also report EXPLAIN Execution Time for the complete repeated-probe command.
All 25 cells retain two warm and 12 measured rounds per role, with two fresh
cohorts: 2,800 raw / 2,400 retained / 400 warm. Smoke has 100 commands and zero
accepted samples. Preserve every negative and exact B/T control. Do not change
loops, source, thresholds or cases after observing results.
