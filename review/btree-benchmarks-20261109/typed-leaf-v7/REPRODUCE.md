# Reproduce or inspect the typed-leaf V7 experiment

Recorded evidence and independent replay are different scopes. The R5 SQL
campaign and four full builds actually ran. The portable fresh-build adapter
has AST/help review only; no independent Linux build, gate or timing replay
has been executed with it. Original controllers under `runtime/` remain exact
copies with historical paths/ELFs; do not run them unchanged in a new prefix.

Use Linux x86_64, Python3.12+, GCC, GNU make, Bison, Flex, Perl, OpenSSL/zlib
and glibc development files. The recorded host had GCC13.3.0, make4.3,
Bison3.8.2, Flex2.6.4, Perl5.38.2 and Python3.12.3. Allow at least8logical
CPUs,8GBfree RAM and15GBfree disk. Free original ports13420–13423 (core),
13430–13434 (gate),13440–13443 (bench),13449 (seed) on your own machine.
No sudo, sysctl, perf or unrelated-cluster action is required.

The source is B72 `72b9498df9a369e747f8d96efb5a6cd33c2451e2` plus one
independent nbtsearch.c overlay for each alternative. V6 and V7 patches each
apply to B72; do not apply one after the other. `SOURCES.json` binds full
normal source/patch/recorded ELF identities. V7 publication commit
`48cf00b7cdf70f26f4f431486871eaf50adfbbf8` is a posthoc byte-exact mapping
of the already-built source, not a new build or timing run.

Obtain that public commit/tree in a local cpg Git checkout, then create the
exact archive. This archive command was verified locally against the pinned
31,099,274-byte source archive; it does not build or execute PostgreSQL:

```sh
git -C /path/to/cpg archive 72b9498df9a369e747f8d96efb5a6cd33c2451e2 | gzip -n > /path/to/base72.tar.gz
sha256sum /path/to/base72.tar.gz
# 32a396e875b17122dc05dad59ecd11a3cb5a78f5b229bb5ce11fb769feaddb64
```

Choose a NEW absolute namespace without whitespace/quotes. The adapter refuses
an existing directory and verifies the original six-script template hashes,
all 20 frozen inputs via the pinned input manifest, source archive and cases.
It copies everything locally and changes only root/archive paths:

```sh
python3 portable/replay.py prepare --root /home/me/typed-v7-replay --archive /path/to/base72.tar.gz
python3 /home/me/typed-v7-replay/build.py
```

The build controller uses nice10/j2, one common source/build path and compiled
prefix for all four clean builds, separate DESTDIR installs, original core239
for each, and original `CFLAGS='-O2 -g'` without an added fno-lto flag.
Configure: `--without-icu --without-readline --with-openssl`, release
`--disable-cassert`, final V7assert `--enable-cassert`. Compiler/configure/
header/source7726/install/ELF receipts are generated from these NEW builds.
Original source/SQL expected files are not regenerated from candidate output.

After `PASS_MATCHED4_BUILD_CORE239`, bind new identities before any runtime
cluster exists. This operation checks all three actual source7726 inventories,
four complete installs/unchanged core logs/configuration and source SHA pins;
then replaces only the new session's exact ELF map and the new gate/session
hash references in analyzer/checker. Old recorded results are never relabeled.

```sh
python3 portable/replay.py bind-built --root /home/me/typed-v7-replay
cd /home/me/typed-v7-replay
python3 check-static-protocol.py --cases inputs/cases-prospective.json
python3 gate.py
# Proceed only after PASS_MATCHED_SQL_ORACLE_LIFECYCLE_STANDBY and clean stops:
python3 benchmark.py seed
python3 benchmark.py smoke
```

Seed uses the exact supplied setup.sql and setup-v5-write-holdout.sql:2M
permanent int8,1M UNLOGGED int8,500K text and100K initial rows in each of four
write tables. Index creation is untimed. Persistent TEMP rows are copied per
backend from UNLOGGED. Eight numeric accepted copies are fully hashed/fsynced
before role assignment; smoke uses four different copies and all 76 commands.
Shared buffers512MB, work_mem/temp_buffers128MB, parallel/JIT/autovacuum off,
synchronous_commit off, statement_timeout60s and system timing clock are
preserved and recorded. The baseline client always uses its own staged libpq;
all server/control binaries use their selected install's lib directory.

Review actual smoke answers, all 19plans/loops per role,16complete write-key
multisets, source/install checks and cleanup; separately verify seed/eight
accepted copies remain untouched. Do not automatically accept timing because
a script exists. Write `sql-r5/PARENT-SMOKE-REVIEW.json` with approved:true and
the exact SHA256 of the new `sql-r5/smoke.json`, only after manual review:

```sh
python3 - <<'PY'
import hashlib,json,pathlib
p=pathlib.Path('sql-r5/smoke.json')
# Run ONLY after the described human review of this independent smoke.
r={'approved':True,'smoke_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
with p.with_name('PARENT-SMOKE-REVIEW.json').open('x') as f:f.write(json.dumps(r,indent=2)+'\n')
PY
python3 benchmark.py freeze
python3 benchmark.py run
# Only after complete PASS; choose a new output path:
python3 analyze.py sql-r5 --cases inputs/cases-prospective.json --output independent-analysis
```

The protocol keeps B/T/V6/L7,19cases,two cohorts,2720raw/2112retained/608warm,
continuous Williams ordering, original fixed diagnostic selection and reverse
numeric births/CPU0↔4 placement. Each read's literal answer follows measured
EXPLAIN. Fresh opens a new backend after settings/metadata; connection startup
is excluded. EXPLAIN executor milliseconds, whole-command backend CPU
nanoseconds and client reply wall nanoseconds remain separate. Wall ends before
JSON parsing/journaling; literal verification is outside all intervals. Do not
trim, normalize by twin/seqscan, pool cohorts or infer host isolation.

The archived helper-offset/native checks are historical, not new microtiming.
This wave repeats SQL only; diagnostic full-TU modules are excluded from release
timing. Preserve any new failure as a separate attempt; never regenerate old
expected output or rerun in the same data namespace after accepted samples.

## Restore and independently inspect the recorded evidence

All raw/warm/retained/diagnostic JSONL is split on whole lines and gzip-compressed
with each uncompressed chunk≤4MiB. No observations are removed. Restoration
verifies each chunk and exact original concatenated bytes/SHA:

```sh
python3 restore-evidence.py --manifest evidence/runtime/RAW-RESTORE.json --output /tmp/typed-r5-recorded
python3 runtime/analyze.py /tmp/typed-r5-recorded/sql-r5 --cases inputs/cases-prospective.json --output /tmp/typed-r5-analysis-new
python3 evidence/audit-independent.py --results /tmp/typed-r5-recorded/sql-r5 --cases inputs/cases-prospective.json --smoke-dir /tmp/typed-r5-recorded/sql-r5 --live-proof /tmp/typed-r5-recorded/root-final-release-r5.json --output /tmp/typed-r5-independent-new.json
```

Archived VM summary.json is authoritative. The exact frozen analyzer was also
run locally on a fresh merged copy; audit.json/BENCHMARKS.md are byte-identical,
while summary.json has 662 Python3.9/3.12 roundoff differences (max 3.73e−9).
This is disclosed in the replay receipt; it is not another benchmark run.
