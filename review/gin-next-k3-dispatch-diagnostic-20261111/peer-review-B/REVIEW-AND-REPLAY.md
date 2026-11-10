# Independent portable observer replay review

Status: **PASS static review; no blocking fresh-namespace defect found**. This
review executed only Python AST/help, frozen-member hashes and --static-check.
It did not compile, start PostgreSQL, access a VM/network or execute the new
Linux frontdoor. Existing historical observer evidence remains separate.

Use the existing portable-replay-r1.py; no duplicate frontdoor was written.
Workspace/publication copies are byte-identical SHA256 `7c9d5148ab4e2fdfa1d934f286686ba97e2f960e44cc42c06658ad0e5287c7bf`.
The two exact input manifests bind 48 members and source plan 58b7e6177b1e5c2cfffe2893e7f93aeec027ef28d55890109b767a9211acc80d.
BINDINGS.json records every reviewed helper/source/reference SHA.

## Source and build route

The caller supplies a local Git repository already containing raw B72
72b9498df9a369e747f8d96efb5a6cd33c2451e2. No fetch or caller worktree/HEAD
mutation is needed. Included overlays produce fixed B 8a8c475037bfde101da23cc9b0364c9c020eca93,
K3 ec32d586cf3bb6cfa76eb672db70160b436ce47c and the observer, with full
inventories after each step (7726/7726/7727 files). Historical instrumented_commit:null
is retained; canonical observer b267e8808ad9d9c3574eb89d047761704266a757
is the later same-source identity, not the measured production K3 executable.

An alternative --source-archive accepts ONLY the original authentic gzip SHA
8c074fcf94a17d381e2df4a2b0554b925d76a777acb7e2f8a508abe7dfd2bbc4.
A newly recompressed archive can differ even with identical files; use --git
rather than loosening the archive/source pins.

Dependencies: ordinary non-root Linux, Python 3.10+, local Git, GCC (historical
GCC 13.3), GNU make/binutils (objdump,nm), bison, flex, Perl,pkg-config and OpenSSL/
zlib development headers. Build flags are -O2 -g -fno-lto, LDFLAGS=-fno-lto,
--without-icu --without-readline --with-openssl, release/no assertions, nice 10,
make-j1 and a 3GB child address-space cap. Core 239/posting-list tests and the
pageinspect/intarray/amcheck/pg_trgm fixture extensions are built. New receipts
record actual compiler/flags/source/full-install/ELF/object inventories.

## Fresh replay commands (NOT executed by this review)

From the standalone observer packet, select a short nonexistent owned root,
unused ports and an existing local B72 repository:

```sh
PACKET=/absolute/path/to/observer/packet
PGGIT=/absolute/path/to/existing/PostgreSQL-Git
RUN=/tmp/k3diag-r1
python3 -B "$PACKET/portable-replay-r1.py" --inputs "$PACKET/inputs" --static-check
python3 -B "$PACKET/portable-replay-r1.py" --inputs "$PACKET/inputs" \
 --git "$PGGIT" --output "$RUN" --core-port 46640 --qual-port 46700 --capture-port 46710
```

The frontdoor sequentially calls unchanged build-harness/build.py →
qualification/qualify.py → capture.py, each with newly produced receipt paths.
Historical run.py deliberately hard-binds its old namespace/build PID and is
not used. There is no reason to rewrite its source, old expected outputs,
reference-B-result.json or historical PASS receipts for a fresh run.

Qualification retains its observer-disabled 40 ordered / 7 prepared / 12 lifecycle / 
11 native / 11 budget / 11 generic-fallback checks. Capture builds the diagnostic
module using the NEW prefix's pg_config cflags/cppflags and actual 907 installed
headers; header inventory and backend/source identities are asserted. It
verifies/fsyncs a fresh qualified seed copy, then produces exactly 18 reports:
six SQL plus six actual-AM queries at 1 and 3 rescans. Source/headers/prefix,
module and seed checks remain active. Reports are counts only: no measured()
call, latency sample, production speedup or timing comparison. Equality after
disable is a potential repeat opportunity, not an actual cache hit.

## Cleanup and bounded limitations

All three original stages already acquire SIGTERM→KeyboardInterrupt through
build-harness/common.py:nice10(), called before owning clusters. The helper
installs signal.signal(SIGTERM,terminate); its terminate raises KeyboardInterrupt.
Build main calls nice10(), qualification calls bc.nice10(), and capture calls
bc.nice10(). Their existing try/finally paths attempt owned process/client/core/
cluster cleanup with own UID, actual executable and datadir checks. The absence
of a direct signal import in qualify.py/build.py does not remove that handler.
A new runpy bridge or duplicate cleanup framework is unnecessary.

Wrapper timeouts are build 10800s / qualification 3600s / capture 1800s. On interruption
it signals its own child group and waits 480s before an emergency SIGKILL. If
that final forced kill is required, shutdown is **not proven**; retain the
FAILED_PRESERVED_NO_RETRY attempt and inspect its own recorded clusters/PIDs
separately. A timeout/failed receipt must never be relabelled PASS. This static
review does not claim runtime injection/failure-path testing.

Minor nonblocking preflight limit: the wrapper tests s/q-DIAG socket length;
s/capture is 1 byte longer. A boundary-length output can therefore fail later
at capture's actual socket_directory check. Use the documented short /tmp root;
actual socket checks remain fail-closed. Original frozen inputs are unchanged.

## Portable-only update and recorded evidence replay

The parent RLIMIT fix changes only the unexecuted portable frontdoor: it imports
resource and sets RLIMIT_AS=(3000000000,3000000000) before out.mkdir/stages. This
restores the original wrapper cap for direct Session/psql children as well as
compiler/pg_ctl children. Static mode returns before changing limits. All 48
frozen inputs remain byte-identical; the previous frontdoor SHA is retained
in BINDINGS-initial.json and A's PORTABLE-ADAPTATION-r2.json.

The separate review-recorded-r1.py was inspected and executed locally into
replay-review-B/recorded-replay-r1/. It creates only a new output/input-view
with links to retained evidence, runs the pinned static check and unchanged
auditors, then compares all audit fields except the two provenance timestamps.
Actual local PASS reproduced 47 gate digests, 183972 mixed native checks, 12936
boundary calls and 18 reports / 244 generations/4574271 dispatches. This is a
recorded-data recount, not a new Linux build, SQL run or latency measurement.
No duplicate frontdoor, signal bridge, production source or frozen input was
written or changed by this review.
