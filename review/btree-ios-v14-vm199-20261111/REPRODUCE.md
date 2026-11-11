# Repeat IOS V14 on a fresh machine

This packet repeats the published 19-case comparison on VM199. The original
input files retain their historical labels (including VM84 and STATIC ONLY).
Those describe their origin; the new host and actual run are identified by
`HOST-r1.json` and the new receipts in `evidence-r1/`. Only those new receipts
and raw observations establish completion here.

Use Linux x86_64, GCC 13.3, make, Bison/Flex, OpenSSL/zlib development
headers, binutils, GDB, Python 3, taskset and readable procfs. Work as a
normal OS user, with over 60 GB free disk. All remote files for this run
live in `/home/reshke/wpgpg/ios14-199-1111`. GIN and IOS run serially.

B72 is `72b9498df9a369e747f8d96efb5a6cd33c2451e2`; V14 source identity is
`113e61347b43d2ae4afb187944ede9e9f6108c24`. Source snapshots and standalone
V13/V14 diffs are in `inputs-r1/source/`; they are alternatives, not a series.
An optional V13-to-V14 diff is included separately. Canonical V14 byte
identity is independently recorded in `SOURCE-IDENTITY-r1.json` without
rewriting the original SOURCE manifest.

Reserve CPUs 4 and 6 on distinct guest cores and ports 40640..40643, 40648,
40649, 40750..40753, 40759 and 40760..40763. Use NEW output directories.

```sh
mkdir -p /home/reshke/wpgpg/new-ios
git -C /path/to/postgres archive 72b9498df9a369e747f8d96efb5a6cd33c2451e2 > baseline-B72.tar
nice -n 10 python3 -B inputs-r1/build-harness/build.py \
  --source-archive baseline-B72.tar --source-plan inputs-r1/source/SOURCE.json \
  --output /home/reshke/wpgpg/new-ios/build --core-port 40640
```

The unchanged driver performs four serial full clean builds, B/V13/V14
release and V14_assert, in common source/build/prefix paths with separate
DESTDIR installs. Flags: `-O2 -g -fno-lto`, OpenSSL, no ICU/readline, j2,
nice 10. amcheck/pageinspect/pg_visibility are installed. All 239 original
regressions per build must pass; expected files are not regenerated.

A stopped baseline seed is required only for the finite correctness gate.
On this new VM it is recreated using the previously documented recipe,
executed by `run-prepare.py`: private baseline initdb, amcheck, `wide` with
200000 rows, `i=repeat((g%10000)::text,8) COLLATE "C"`,
`j=repeat((g%10000)::text,9) COLLATE "C"`, `wide_idx(i,j)`,
VACUUM(FREEZE,ANALYZE), CHECKPOINT and clean stop. The exact executed SQL
is exported as `create-correctness-seed.sql`. The original expected outputs
remain unchanged and must match; a differing seed must be investigated.

Equivalent explicit commands for the replacement seed, from the packet root
(the actual run used `run-prepare.py` and saved its command receipts):

```sh
ios_root=/home/reshke/wpgpg/new-ios
ios_prefix=$(python3 -c 'import json; print(json.load(open("/home/reshke/wpgpg/new-ios/build/build-receipt.json"))["variants"]["B"]["prefix"])')
export LD_LIBRARY_PATH="$ios_prefix/lib"
mkdir -m 700 "$ios_root/seed-socket"
"$ios_prefix/bin/initdb" -D "$ios_root/correctness-seed" --no-locale -E UTF8 -A trust
(
  set -e
  trap '"$ios_prefix/bin/pg_ctl" -D "$ios_root/correctness-seed" -m fast -w stop' EXIT
  "$ios_prefix/bin/pg_ctl" -D "$ios_root/correctness-seed" \
    -l "$ios_root/seed-server.log" \
    -o "-k $ios_root/seed-socket -p 40648 -c listen_addresses= -c autovacuum=off" -w start
  "$ios_prefix/bin/psql" -X -h "$ios_root/seed-socket" -p 40648 -d postgres \
    -v ON_ERROR_STOP=1 -f evidence-r1/create-correctness-seed.sql
)
```

```sh
nice -n 10 python3 -B inputs-r1/qualification/gate.py \
  --build /home/reshke/wpgpg/new-ios/build \
  --correctness-seed /home/reshke/wpgpg/new-ios/correctness-seed \
  --output /home/reshke/wpgpg/new-ios/qualification --port 40649
python3 -B inputs-r1/prepare-sql.py \
  --build /home/reshke/wpgpg/new-ios/build \
  --qualification /home/reshke/wpgpg/new-ios/qualification \
  --output /home/reshke/wpgpg/new-ios/sql
nice -n 10 python3 -B /home/reshke/wpgpg/new-ios/sql/sql-controller.py prepare
nice -n 10 python3 -B /home/reshke/wpgpg/new-ios/sql/sql-controller.py smoke
python3 -B inputs-r1/review-smoke.py --collection /home/reshke/wpgpg/new-ios \
  --inputs inputs-r1 --output /home/reshke/wpgpg/new-ios/SMOKE-REVIEW.json
```

The gate checks original target SQL outputs, native dispatch/cache/slot
ownership and actual backend/module layouts. These native helpers are
correctness checks, not timed microbenchmarks. SQL data are created
independently by the exact `sql-template/setup.sql`; all eight measurement
copies are hashed and fsynced before roles are assigned. Four extra copies
provide 76 smoke plans, zero accepted timing observations. Independently
review those plans, finite check receipts, actual binary identities and
stopped processes before writing `sql/TIMING-APPROVAL.json` with status
`APPROVED_FIXED_IOS_V14_SQL`, `smoke_status_sha256` and `input_sha256`.
The latter hashes refer to `sql/smoke/status.json` and `sql/INPUTS.json`.

```sh
nice -n 10 python3 -B /home/reshke/wpgpg/new-ios/sql/sql-controller.py 0
nice -n 10 python3 -B /home/reshke/wpgpg/new-ios/sql/sql-controller.py 1
python3 -B inputs-r1/analyze-sql.py /home/reshke/wpgpg/new-ios/sql \
  --output /home/reshke/wpgpg/new-ios/summary.json
```

All 19 cases, B/T/V13/V14, two warm and 12 retained rounds in each cohort:
2128 raw / 1824 retained / 304 warm. Backend/client CPU placement is 6/4
then 4/6, cases reverse and physical role slots rotate. Shared buffers 1 GB,
work_mem 128 MB, JIT/parallel/memoize/autovacuum off, system timing clock,
fsync on, sockets only. Keep every short/LIMIT/mixed/heap/single-attribute
and off-path control. CREATE INDEX is unmeasured setup.

Metrics are executor time, backend CPU, backend runqueue, client wall and
psql CPU, per supplied SQL statement. The LIMIT cases contain 20000
parameterized scans; they are not single-lookup latency measurements.
Ratios use paired same-round observations; zero denominators are
undefined ratios only, with all raw values and absolute differences kept.
No trimming, pooling, twin subtraction or timing-dependent repetition.

`collect-remote.py` rereads source/install/seed identities, verifies shutdown
and exports synthetic evidence without PGDATA/binaries/full runner logs.
The original `audit-results.py` independently recounts every cell and pair;
`render-results.py` renders complete tables from its all-statistics JSON.
The published seed replacement is newly executed here; historical values
remain a separate comparison and are never treated as new observations.

To independently recount the already published observations from the packet
root, without starting PostgreSQL, use new output directories:

```sh
python3 -B inputs-r1/audit-results.py --collection evidence-r1 \
  --inputs inputs-r1 --output /home/reshke/wpgpg/new-ios/recount
python3 -B inputs-r1/render-results.py \
  --statistics /home/reshke/wpgpg/new-ios/recount/all-statistics.json \
  --output /home/reshke/wpgpg/new-ios/recount/tables \
  --markdown /home/reshke/wpgpg/new-ios/recount/BENCHMARKS.md
```

`historical-comparison-r1.json` carries the 44 historical medians used in
the comparison, with the original compressed file's hash and path. This
keeps `write-results.py` self-contained when rendering this packet's report;
the original history is not remeasured or reinterpreted by that script.
