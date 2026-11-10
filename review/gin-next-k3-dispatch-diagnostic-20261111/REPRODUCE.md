# Fresh Linux reproduction and offline recount

Use Linux x86-64 with GCC, GNU make, binutils (`objdump`, `nm`), Git, Python 3.10+
with ctypes, Perl, Bison, Flex, pkg-config and OpenSSL development headers.
ICU and readline are disabled. The actual host used Ubuntu GCC 13.3.0; different
compiler/platform output has separate provenance and need not have identical
machine-code hashes. Provide several GiB of free disk and a short new output
root. The portable frontdoor and all its children inherit a 3,000,000,000-byte address-space cap. Build uses nice 10,
make -j1, `CFLAGS=-O2 -g -fno-lto`, `LDFLAGS=-fno-lto`, `CC=gcc`.

The unchanged builder installs pageinspect, intarray, amcheck and pg_trgm for the
frozen 200,002-row fixture. Ordinary setup is `inputs/qualification/inputs/setup.sql`;
the 25 original SQL cases/answers, added ordinary comparisons, native oracles,
budget boundaries and forwarding opclass probes are all included unchanged.
No package installation, external database or mailing-list archive is used.

Start from a local Git repository already containing exact raw B72
`72b9498df9a369e747f8d96efb5a6cd33c2451e2`. No fetch is performed. The builder
archives that exact object, verifies all 7,726 source file hashes, then applies
the frozen fixed-B, K3 and observer patches with strict checks and full inventories.
The original gzip is deliberately omitted; `--git` is the portable alternative.

From this packet directory, first check the immutable inputs:

```sh
python3 -B portable-replay-r1.py --static-check
```

On a machine where these ports are free, execute one finite fresh replay:

```sh
python3 -B portable-replay-r1.py \
  --git /path/to/existing/postgresql-repository \
  --output /tmp/k3diag-r1 \
  --core-port 46640 --qual-port 46700 --capture-port 46710
```

The root must not exist. Core uses 46640 and posting-list tests use core+30.
Runtime uses qual-port and qual-port+1 for seed/ordinary gate, and capture-port
for the 18 captures. Unix sockets live below the owned output/s directory; the
original wrapper preflights the q-DIAG socket and each unchanged controller also
checks its actual socket length. Keep the output short as shown. Servers listen
only on their owned Unix sockets, with autovacuum/JIT/parallel workers off and
128 MB shared buffers. Client identity uses the current OS user; no PG* connection
environment is inherited.

The frontdoor invokes the original unchanged scripts in this order:

```sh
python3 -B inputs/build-harness/build.py --git /path/to/existing/postgresql-repository \
  --source-plan inputs/source/SOURCE.json --output /tmp/k3diag-r1/build-r1 \
  --core-port 46640 --jobs 1
python3 -B inputs/qualification/qualify.py --build /tmp/k3diag-r1/build-r1 \
  --output /tmp/k3diag-r1/qualification-r1 --first-port 46700
python3 -B inputs/capture.py --build /tmp/k3diag-r1/build-r1 \
  --qualified /tmp/k3diag-r1/qualification-r1 \
  --output /tmp/k3diag-r1/captures-r1 --port 46710
```

These direct commands document the stage arguments. Use the frontdoor for the
matching inherited resource limit, or supply that exact parent limit yourself
before direct invocation; the qualifier alone does not cap its Session child.
Do not run both against the same output. All stages reject existing attempt
directories. Qualification is a
prerequisite for capture. The same supplied expected data is used; never update
expected values from the new executable. A different build has new absolute
paths, ELF/module hashes and runtime receipts even if source hashes match.
The new portable frontdoor has only local AST/help/input checks, not a Linux run.
The exact original controllers did execute successfully on VM84.

Commands and partial failure receipts are retained. Controllers install their
SIGTERM handler through common.nice10(), allowing their finally blocks to close
clients and verify/stop owned clusters. Before signalling they verify ownUID,
actual backend ELF and exact data directory. A timeout first requests orderly
termination and waits for cleanup; forced termination can still leave a failed
attempt requiring inspection. Preserve it and do not silently retry. No command
targets other namespaces or alters system settings.

## Counts, not latency

`captures-r1/raw.jsonl` contains 18 complete records and one individual JSON per
record, written/fsynced before acceptance assertions. SQL literals, ordered row
hashes and AM tuple totals are independent checks. There are 17 GIN predicates
and one ID-only Seq control among the 18 ordered comparisons.

For each key, dispatches = cached + direct; cached = hits + misses;
native = misses + direct; dispatches = native + hits. `maximum_misses` counts
consecutive dispatcher misses, not TIDs. `miss_run_hist` has exact bins 0..64 and
its weighted sum is misses. Vector-run bins are 1,2,3,4,5..8,9..16,17..32,33..63,
64,65..127,128..255,256+. `equal_adjacent_after_disable` describes potential
immediate vector repetition in the direct stream, not saved callbacks or hits.
The stream checksum is noncryptographic; ordered SQL results use SHA256.
AM three-rescan reports must have three new generations and matching one-scan
counters. Overflow, changed bindings, bad literal, tuple count, counter identity
or generation fails the preserved attempt. No CPU, wall or executor samples
are produced or accepted; timestamp fields describe provenance only.

## Independently recount the recorded evidence locally

The included auditors do not import executed counter-check or metric code.
They use fixed-B reference values and their own arithmetic. To preserve their
reviewed script bytes, create a temporary read-only view containing input links
and the selected build proof directory, then run both auditors:

```sh
python3 -B review-recorded-r1.py --output /tmp/k3diag-recorded-review
```

This offline helper only reads the packet and writes a new local review root;
it does not compile, open a database or use the network. It reproduces the
recorded 47 gate digests/183,972 native checks/12,936 boundary calls and the
18-capture/244-generation/4,574,271-dispatch recount. Timestamps of new audit
receipts can differ. It does not constitute a new Linux build/runtime replay.

Review `evidence/ROOT-FINAL-LIVE-DIAG-r2.json` for actual original shutdown and
source/install/seed/ASM verification. The helper under review-tools is pinned to
the original owned namespace and is historical provenance; it is not a portable
remote command. No remote final proof or new measurement is performed offline.
