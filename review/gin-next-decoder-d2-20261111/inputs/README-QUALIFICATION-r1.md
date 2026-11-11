# Finite D2 ordinary qualification overlay

This is a new ordinary valid-input gate, not a benchmark. It consumes only the
new B/D1/D2/D2_assert build receipt and stops on any failed build. It never runs
against the old measured prefixes or changes old frozen inputs.

The old executed decoder-native.c, session.py, setup.sql, 25 original SQL cases,
answers and holdout bytes are copied unchanged. The helper invokes the actual
installed ginPostingListDecodeAllSegments callback with real PostgreSQL types,
valid compressed posting lists and independently generated ordered ItemPointers.
Its 18 cases cover singleton/tails/batch boundaries, dense128/dense4096, ordinary
multi-segment/growth paths and delta2..7. The normal timing export remains in the
unchanged module but is never called by this gate. No malformed/corrupted inputs,
failure injection or unrelated correctness investigation is included.

The fixed-B prior result supplies 18 expected decoder/checksum records, 47 ordered
SQL/prepared digests and 12 lifecycle digests, in reference-B.json. Fresh B is
also checked against that evidence. No expected is resnapshotted from D1/D2.
For each of four builds the original gate keeps 40 ordered SQL cases (25 original
plus 15 additional ordinary cases), seven prepared comparisons, 12 ordinary serial
INSERT/DELETE/VACUUM comparisons and 18 valid decoder cases. Totals are 160 SQL,
28 prepared, 48 lifecycle, 72 decoder cases and 52,608 item checks. These cover
inline/absent/OR/full/dense/lossy/Seq and other opclasses. The Seq ID-only control
has no GIN predicate. This finite one-session gate is not a concurrency proof.

A fresh B seed and four private copies use owned sockets below ROOT/s, ports
46960 (seed), 46961..46964. All modules compile against their actual installed
907 headers/flags and their result receipts bind source/ELF/module hashes.
Decoder raw JSON is fsynced before acceptance assertions; ordered proof/literal
plans are saved before assertions. Nice10 and a 3 GB parent/child address-space cap
apply before Session children start. Cleanup verifies live PID/ownUID/backend
ELF and resolved -D data directory before signaling, then proves each owned
cluster stopped/PIDs/socket absent. Source/install/seed/input hashes are checked.

After root review, the intended finite chain command is:

```sh
R=/home/reshke/allfuzz/gin-dec-d2-20261111
python3 -B "$R/inputs/run-qualification-r1.py" --root "$R" \
 --wait-build-pid ACTUAL_OWN_BUILD_PID --wait-seconds 3600
```

It waits only for the
PID recorded by BUILD-LAUNCH-D2-r1.json, fails on early exit/failed build/timeout,
then runs the gate exactly once. Each output path must be new; failed attempts
are preserved and not retried. Qualification runs for at most 3600 seconds with
owned cleanup on termination. No timing launch is included. Root must review
actual gate, normal ASM, source/header/ELF bindings and a later timing smoke
before accepting any measurements.

Preparation status is local AST/help/byte-check/source replay only. No compile,
core/native/SQL execution or D2 performance result has occurred in preparation.
The later allocation/materialization/free native and complete SQL measurements
must keep all controls, exact B/T, multibyte negatives and dense128. Their design
is separate and must not be selected or trimmed based on this correctness gate.
