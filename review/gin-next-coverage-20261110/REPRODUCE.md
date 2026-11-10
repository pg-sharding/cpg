# Replay recorded coverage and repeat independently

The evidence records the actual completed VM158 campaign. Offline replay below
creates no timing samples. The new Linux front door is supplied for repetition;
it has static/help checks and uses the actual build/qualification/measurement
scripts, but has not itself been replayed independently on a second Linux host.

From this publication packet's root, with Python 3 and fresh output directories:

```sh
python3 -B audit-results-r1.py --evidence evidence --out-new /tmp/gcv-audit-new
python3 -B render-results-r1.py --analysis /tmp/gcv-audit-new --out-new /tmp/gcv-tables-new
cmp /tmp/gcv-tables-new/BENCHMARKS.md report/BENCHMARKS.md
```

The auditor reads no benchmark modules. It verifies every collection SHA,
schedules, warm/retained counts, integer-set reference digests, every saved
large-query scalar answer/plan, durable write observations, all spread/paired
vectors and stopped-cluster receipts. Its 624 absolute and 936 pair groups must
match the recorded outputs. No PostgreSQL service is required for this replay.

For a fresh campaign use Linux x86-64, Python 3, GCC (actual: GCC13.3), GNU make,
Perl, Bison/Flex, OpenSSL/zlib development headers, binutils, util-linux taskset/
lscpu and procfs. Run as an ordinary owner in a short new namespace with at
least 40GB free disk and preferably 16GB RAM. CPUs0/4 must be allowed and on
different physical cores as in the actual topology; a different placement needs
its own declared adaptation. Guest placement alone is no isolation guarantee.
Do not overlap compilation/profiling with timing or alter foreign processes.

Obtain public source containing historical B72, for example:

```sh
git clone --single-branch --branch experiments/gin-logical-tid-key-c11-b72-20261110 \
  https://github.com/pg-sharding/cpg.git /tmp/gcv-public-source-new
gin_cover_packet=$(pwd)
gin_cover_run=/tmp/gcv-new
mkdir "$gin_cover_run"
nice -n 10 python3 -B "$gin_cover_packet/source-support/c11/build-harness/build.py" \
  --git /tmp/gcv-public-source-new \
  --source-plan "$gin_cover_packet/source-support/c11/build-source/SOURCE.json" \
  --output "$gin_cover_run/build" --core-port 45340
nice -n 10 python3 -B "$gin_cover_packet/source-support/c11/campaign.py" \
  --build "$gin_cover_run/build" --output "$gin_cover_run/qualify" \
  --first-port 45400 --mode qualify
```

Five serial full clean builds use the same source/build/compiled-prefix path,
separate DESTDIR installs, make-j2, nice10, `CFLAGS=-O2 -g -fno-lto`,
`LDFLAGS=-fno-lto`, empty CPPFLAGS; ICU/readline off, OpenSSL on. B/C9/C10/C11
are release builds; C11_assert enables assertions. Require all unchanged
core239 and posting-list tests and `PASS_GIN_C11_BUILDS`. Ordinary qualification
must pass all frozen ordered/scalar/prepared/AM answers and clean shutdown.
Source overlays, all7726 base hashes and installed headers are included. The
original actual build used a B72 archive SHA256
`8c074fcf94a17d381e2df4a2b0554b925d76a777acb7e2f8a508abe7dfd2bbc4`.
No old binaries or PGDATA are needed. C9/C11 diffs are alternative complete
changes over fixedB; do not apply both. The original common prerequisite is
already represented identically in every source snapshot.

Review actual statuses, host load, topology, free ports and clean shutdowns,
then run these five commands sequentially. Use new output directories:

```sh
nice -n 10 python3 -B "$gin_cover_packet/runner/operations.py" --operation create-index \
  --build "$gin_cover_run/build" --qualified-from "$gin_cover_run/qualify" \
  --output "$gin_cover_run/ci1" --first-port 45700
nice -n 10 python3 -B "$gin_cover_packet/runner/operations.py" --operation insert \
  --build "$gin_cover_run/build" --qualified-from "$gin_cover_run/qualify" \
  --output "$gin_cover_run/in1" --first-port 45700
nice -n 10 python3 -B "$gin_cover_packet/runner/operations.py" --operation vacuum \
  --build "$gin_cover_run/build" --qualified-from "$gin_cover_run/qualify" \
  --output "$gin_cover_run/va1" --first-port 45700
nice -n 10 python3 -B "$gin_cover_packet/runner/scale.py" --mode warm \
  --build "$gin_cover_run/build" --qualified-from "$gin_cover_run/qualify" \
  --output "$gin_cover_run/lg1" --first-port 45740
nice -n 10 python3 -B "$gin_cover_packet/runner/scale.py" --mode restart \
  --build "$gin_cover_run/build" --qualified-from "$gin_cover_run/qualify" \
  --large-from "$gin_cover_run/lg1" --output "$gin_cover_run/rs1" --first-port 45740
```

Fixture creation is explicit in source-support/c11/harness/inputs/setup.sql
and runner/scale.py. Write operations reset data outside timing. Fastupdate is
off, normal durability stays enabled; JIT/autovacuum/parallelism are off. Write
campaigns use512MB shared buffers and128MB maintenance_work_mem, scale64MB
shared buffers; work_mem64MB. Read runner/PROTOCOL.md and SCALE-PROTOCOL.md for
the frozen commands/counts. Their preparation-time status is historical; actual
PASS evidence is under evidence/. Every new run has new dynamic ELF/source/
header/seed bindings and must never be labelled as the historical result.

Keep warm and retained rows, both cohorts and all six role pairs. CPU, client
wall, executor, buffer counters, run queue, WAL and process I/O have distinct
boundaries. Restart mode excludes startup and is warm OS cache, empty shared
buffers; do not relabel it cold disk. There is no standalone new microtest in
this coverage: source-support includes the previously measured C11 AM harness,
whose original result/commands are in the separate C11 packet. Stop every own
cluster/client and preserve failures before packaging only selected text data.
