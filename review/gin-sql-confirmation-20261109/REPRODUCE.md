# Repeating the ordinary SQL comparison

This packet runs a finite full-backend SQL comparison, not a native-body or
CREATE INDEX campaign. The older native measurements are separate historical
evidence and must not be labelled results of these fixed trees.

Linux requirements: Python 3 standard library, GCC (executed version is recorded
in build provenance), GNU make, patch, binutils/objdump, util-linux/taskset,
Perl, flex, bison, zlib and OpenSSL development files. Examples for Debian-like
systems are `build-essential flex bison libssl-dev zlib1g-dev`; install required
dependencies separately using the host's normal administration procedure.
Use a non-root account, at least 8GB available memory and 15GB free disk. CPU 0
and CPU 4 must be available and represent different physical cores; confirm
with `lscpu -e=CPU,CORE,SOCKET,ONLINE`. The executed controller uses these exact
CPU numbers and reverses them for its second cohort. It never stops foreign
workloads. The archive server is not a benchmark host.

Place the entire packet in a new, writable path without spaces and choose
unused local ports. Builds and cluster paths below must not exist. No source,
threshold or SQL changes are needed between runs.

```sh
python3 -B build-harness/build.py \
  --source-archive /absolute/path/to/baseline.tar.gz \
  --source-plan /absolute/path/to/packet/build-source/SOURCE.json \
  --output /absolute/new-run/build --core-port 41740

python3 -B campaign.py \
  --build /absolute/new-run/build \
  --output /absolute/new-run/sql-r1 --first-port 41800

python3 -B summarize.py /absolute/new-run /absolute/new-results
```

`baseline.tar.gz` is the exact B72 source archive with SHA256
`8c074fcf94a17d381e2df4a2b0554b925d76a777acb7e2f8a508abe7dfd2bbc4`.
The complete 7726-file identity manifest is `build-source/base-source-files.json`.
Alternatively, use an existing local Git repository containing
`72b9498df9a369e747f8d96efb5a6cd33c2451e2` by replacing `--source-archive ...`
with `--git /absolute/local/repository`; the adapter performs `git archive`
locally, verifies every source file and does not access the network. An
independently compressed archive may differ in archive hash while containing
the same verified files. The source plan pins complete fixed trees and patches.
The distributable packet does not duplicate the full baseline archive. A plain
clone of `https://github.com/pg-sharding/cpg.git` containing the published fixed
baseline branch supplies its B72 ancestor; use `--git /absolute/clone` above.
Avoid an incompletely materialized partial clone: the build adapter deliberately
disables lazy network fetching and verifies all 7726 archived source files.

The build adapter performs four fresh serial builds, records actual commands,
compiler/configuration/headers/source identities, compiles four extensions and
requires all original 239 core tests in each variant. Source and expected
outputs are never regenerated. It uses common compiled source/build/prefix
paths plus distinct DESTDIR installations to reduce avoidable layout changes.
Flags are `-O2 -g -fno-lto`, release except the explicit A4 assertion control,
OpenSSL enabled, ICU/readline disabled, nice 10 and make -j2.

The campaign creates its own baseline seed using the unchanged
`harness/inputs/setup.sql`, freezes it, then verifies/fsyncs physical copies.
All row counts, data formulas, NULL/empty cases, index operator classes and
frozen expected answers are in `harness/inputs/`. It qualifies ordinary Seq/GIN
and prepared results on all four builds, then performs two fresh SQL cohorts.
B/T use the exact same executable; L4 and A4 are independent alternatives.
The first cohort uses server/client CPU 0/4 and numeric role slots 0/1/2/3;
the second reverses CPU assignment, role slots, session births and case order.
All own clusters are stopped in finally blocks and checked for clean shutdown.

Every query has 2 warm-up and 12 retained Williams4 rounds: 2800 raw, 2400
retained and 400 warm-up observations. Each measured EXPLAIN follows an
untimed execution checked against a frozen literal answer. This adds warming
and is part of the protocol. EXPLAIN Execution Time measures executor time;
Linux backend schedstat measures whole-command CPU including planning/output;
client monotonic wall includes command/protocol/output. Do not mix these
boundaries. All six direct role pairs, every per-round value, negative cases,
absolute min/median/max, sample deviation and MAD are retained. No trimming,
pooling or exact-twin normalization is performed.

On failure, preserve the entire run directory and choose new paths for any
subsequent attempt. Do not retry into an existing directory or mix partial
observations. Raw `postgres` server/build/runner logs and PGDATA stay private;
the distributable result packet contains compact receipts, ordinary raw SQL
EXPLAIN observations and source/harness inputs, not complete runtime trees.

The shown adapters are the same sources used by this campaign. Actual execution
receipts are authoritative about completed scopes. A separate clean-machine
replay of these front-door commands is not implied by local syntax checks.
