# Reproduce the new BOX experiment

Use a clean Linux x86-64 machine, an unprivileged user, Python 3, GCC 13.3,
GNU make/binutils, Bison, Flex, Perl, pkg-config, OpenSSL and zlib development
headers. Allow about 20 GB of free space for six clean builds, installations
and private seed copies. Guest CPUs 0 and 4 must be available and belong to
different reported cores. Record shared load; hardware isolation is not claimed.

Obtain a PostgreSQL/cpg Git repository containing exact public B72
`72b9498df9a369e747f8d96efb5a6cd33c2451e2`. The source plan and complete
7,726-file baseline manifest verify source contents; no remote code is fetched
or executed by the build controller. Run from this artifact directory:

```sh
python3 build-harness/build.py \
  --git /path/to/postgres-repository \
  --source-plan source/SOURCE.json \
  --output "$PWD/builds" --core-port 40900

python3 runtime/layout.py
python3 runtime/gate.py
python3 runtime/benchmark.py --prepare-smoke
python3 runtime/benchmark.py --matrix
python3 runtime/analyze.py --input bench-r2 --out-new analysis-r2
```

An authentic local `git archive` can replace --git using --source-archive.
Archive compression identity can differ; the complete source manifest still
has to match. `prepare.py` is the historical source generator with explicit
local input pins, not a required step for a downloaded self-contained packet.
Do not replace the B72 inputs with another master revision or existing prefix.

Builds use one source path, one build path and one compiled prefix, separate
DESTDIR installations, j2/nice10, -O2 -g -fno-lto, OpenSSL, no ICU/readline.
Four release roles B/R/C/D plus C/D assert run original core239 unchanged.
Runtime verifies full installations and executable hashes against receipts.
The T role is the exact B executable, not a separately compiled baseline.

gate.py creates the only canonical seed using the original deterministic
setup.sql, builds the explicit forwarding/native module and records literal
baseline answers. Complete ordered multisets use a forced sequential B
reference. Six full backends are compared before timings. The microbenchmark
uses actual index_rescan/index_getbitmap, with four fixed query distributions
and literal SQL TID-count references. It is not a CREATE INDEX optimization.
CREATE INDEX is fixture preparation; no build-time speedup is claimed.

The smoke creates/hashes/fsyncs all ten accepted cohort copies and five smoke
copies before assigning code roles. It checks all 100 role/case commands.
The matrix verifies its frozen scripts, cases, module, gate and seed, then
collects 2,400 observations: two warm plus ten retained rounds for 20 cases,
five roles and two cohorts. The ten-row Williams cycle balances positions and
ordered adjacencies. Cohort two reverses code-slot assignment, case order and
server/client CPU placement. Every timed backend has identical validation
history. Natural and forced-index plans remain separate.

Primary micro time is kernel process CPU, in milliseconds, including rescan,
page traversal/callbacks and bitmap construction/free. Primary SQL time is
EXPLAIN Execution Time with TIMING OFF. Whole-command schedstat CPU and client
round-trip time are additional wider intervals. Literal SQL answers follow
the EXPLAIN outside its clock; JSON parsing/journaling occurs after the clock.
Report absolute times/ranges, MAD/stdev, all direct pairs and all negatives;
do not normalize by unchanged controls or pool cohorts. Scripts stop only
their own private clusters in finally and verify PID/socket absence.

Output roots deliberately refuse reuse. Preserve failed attempts separately.
A prior r1 harness attempt stopped on its first warm observation because the
native-result JSON was overwritten by a same-named Boolean metadata field.
It has one preserved raw warm record and zero accepted observations. r2 uses
`is_native` metadata, fresh namespaces and a separate smoke; production code,
cases, timing boundaries and planned sample counts are unchanged.
A fresh rerun needs a new copy of this artifact directory, free ports/socket
names and new provenance. Original Linux observations, later local numeric
replay and any future independent Linux run must be identified separately.
