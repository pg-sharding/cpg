# Isolated instrumented K3 diagnostic build

This input capsule builds one fresh backend only. It cannot produce a latency
comparison or reproduce the measured K3 executable. Runtime qualification and
18 untimed captures are a separate overlay and must wait for build PASS.

Source chain: authentic raw B72 72b9498df9a369e747f8d96efb5a6cd33c2451e2,
identical supplied fixed B 8a8c475037bfde101da23cc9b0364c9c020eca93,
exact K3 ec32d586cf3bb6cfa76eb672db70160b436ce47c, then the six observation
hooks and diagnostic include. Full inventories are checked after every patch:
7726/7726/7727 files. Only ginlogic-probe.inc is a new source path. The
instrumented artifact has no Git commit identity; ec32 is its production parent.

VM84 has foreign load around11 on8 logical CPUs. Use nice10, make-j1, a3GB
address-space limit inherited by each child, no compiler/threshold tuning and
no latency claims. Source/build/DESTDIR/prefix/PGDATA all live in the new owned
/home/reshke/allfuzz/gin-cache-k3-dispatch-probe-20261110 namespace.
The existing read-only B72 archive at
/home/reshke/allfuzz/btree-ios-v14-campaign-20261109/inputs/baseline.tar.gz
was independently read/hash-verified as
8c074fcf94a17d381e2df4a2b0554b925d76a777acb7e2f8a508abe7dfd2bbc4.

GCC uses -O2 -g -fno-lto; LDFLAGS=-fno-lto, ICU/readline off, OpenSSL on.
Existing VM dependencies suffice; no package installation is authorized.
Build/install pageinspect,intarray,amcheck,pg_trgm for the unchanged fixture.
Core239 and posting-list expectations remain unchanged, normal full-TU ASM
and all backend object hashes/907 installed headers/ELF/full install inventories
are recorded. nm-D must expose gin_k3_diag_begin/end/report before PASS.
Cleanup verifies ownUID, actual backend ELF and resolved -D datadir before any
signal; it never targets foreign clusters or arbitrary PIDs.

Root must review/import this capsule before the concrete build-only command:

```sh
R=/home/reshke/allfuzz/gin-cache-k3-dispatch-probe-20261110
python3 -B "$R/inputs/build-harness/build.py" --source-archive \
 /home/reshke/allfuzz/btree-ios-v14-campaign-20261109/inputs/baseline.tar.gz \
 --source-plan "$R/inputs/source/SOURCE.json" --output "$R/build-r1" \
 --core-port 46640 --jobs 1
```

Use --git /existing/B72/repository as an alternative to the omitted archive;
all7726 baseline bytes are verified in either case. Local BUILD-STATIC-r1.json
is source replay/AST/help evidence only. No C compiler/backend/core tests ran
while preparing this capsule. Preserve any failed attempt; no automatic retry.
