# Repeat the unchanged C9 comparison

This directory records the independent run on VM `51.250.5.199`. Completion
and measured values are established by `evidence-r1/` and `analysis-r1/`,
when present; source preparation alone is not a benchmark result.

Linux x86_64, GCC 13.3, GNU make, Bison, Flex, Python 3, OpenSSL/zlib
development headers, binutils, `taskset` and readable `/proc` are required.
The measured VM has 8 vCPUs (four guest cores, two threads each), AMD EPYC
Genoa and 64 GB RAM. Exact versions/topology are saved in HOST evidence.
Use a normal OS user and an otherwise idle machine with sufficient disk.

Source is B72 `72b9498df9a369e747f8d96efb5a6cd33c2451e2`; all GIN roles
share baseline `8a8c475037bfde101da23cc9b0364c9c020eca93`. C9 is
`0ab3bd65c8957ea5e25f9ef8981401f0616d99de`. The source plan provides
complete pinned file inventories, exact deltas and changed-file snapshots.
The candidate-only diff applies after the common baseline. L4/L8/L9 are
alternative comparison trees, not steps to apply after C9.

Create the parent directory first (the build driver creates only its new
output leaf). From a local PostgreSQL repository containing B72:

```sh
mkdir -p /home/reshke/wpgpg/new-c9
git -C /path/to/postgres archive 72b9498df9a369e747f8d96efb5a6cd33c2451e2 > baseline-B72.tar
python3 -B inputs-r1/followup-r3/build-harness/build.py \
  --source-archive baseline-B72.tar \
  --source-plan inputs-r1/followup-r3/build-source/SOURCE.json \
  --output /home/reshke/wpgpg/new-c9/build --core-port 44740
```

Use a new nonexistent output directory. The driver verifies all 7726
source files, builds B/L4/L8/L9/C9 release and C9 with assertions, installs
pageinspect/intarray/amcheck/pg_trgm, and runs the 239 original core tests
for every role. Flags are `-O2 -g -fno-lto`, OpenSSL enabled, ICU/readline
disabled, `make -j2`, nice 10. Header/object/install bindings remain in
the build receipt. Proceed only after `PASS_GIN_REPAIR_R3_BUILDS` and
empty cleanup errors.

Confirm CPUs 0 and 4 exist and belong to different guest cores; check the
ports below are unused. Execute the unchanged screen and full campaigns
serially, with no concurrent build or other benchmark:

```sh
python3 -B inputs-r1/followup-r3/campaign.py \
  --build /home/reshke/wpgpg/new-c9/build \
  --output /home/reshke/wpgpg/new-c9/screen-r1 --mode screen --first-port 44800
python3 -B inputs-r1/followup-r3/campaign.py \
  --build /home/reshke/wpgpg/new-c9/build \
  --output /home/reshke/wpgpg/new-c9/full-r1 --mode full --first-port 44900
```

Reserve 44740..44745, 44800..44830 and 44900..44930. Servers use private
Unix sockets, empty `listen_addresses`, 512 MB shared buffers, 64 MB work
memory (64 kB in designated lossy cases), system timing clock, durability
on, JIT/parallel/memoize/autovacuum off. CPU placements are server/client
0/4 then 4/0. A fresh baseline seed is copied and fsynced before role
assignment; no preexisting PGDATA is required. Exact data/index definitions
are in `inputs-r1/followup-r3/harness/inputs/setup.sql` (200002 documents
including NULL/empty rows, plus inline fixtures).

The screen has 12 SQL and four actual-AM cases, six roles, two warm and
12 retained balanced rounds in each cohort: 2688 raw / 2304 retained.
Full SQL has all 25 cases and B/T/L4/C9: 2800 raw / 2400 retained.
T executes the exact B binary. The second cohort reverses CPU, physical
slot/session order and case order. Every campaign first verifies ordered
Seq/GIN results, prepared/cached rescans, literal answers and actual-AM
answers, including the assertion build. No observations are trimmed.

SQL metrics distinguish EXPLAIN executor milliseconds, whole-command
backend CPU and client wall time. Times are per supplied SQL statement:
several selective cases batch 100 rescans, while OR/single/Seq controls
batch five. Consult the exact query JSON rather than interpreting these
times as latency of one lookup. The C module times the real
`index_rescan/index_getbitmap/tbm_free` loop, including interrupt checks,
excluding relation open/scan construction and result serialization. Native
times are per batch: 10000 inline, 5000 absent, 100 skew or 10 full scans.
They are not SQL throughput. CREATE INDEX is unmeasured fixture setup.

Each campaign writes raw JSONL, absolute spreads and all same-round pairs
under `analysis0/analysis1`. Negative percentages mean less time. Pair
medians are not ratios of displayed absolute medians. Keep controls,
cohorts and metrics separate, including negative results and B/T movement.
This is historical B72 warm-cache testing, not current-master or cold I/O.

For this run the remote orchestration scripts use the concrete wpgpg paths.
`collect-remote.py` checks live source/install/seed identities and shutdowns
and exports only synthetic evidence. After restoring the exported files:

```sh
python3 -B audit-and-render.py --evidence evidence-r1 --output analysis-r1
```

The audit computes its own statistics and checks every original group and
pair. An earlier run of this utility against historical saved observations
is explicitly separate from the new VM measurements. `PATH-AMENDMENT.md`
records a user-requested directory change and rebuild before any timing;
`INPUT-PACKAGING-NOTE.md` records restoration of an exact missing module
copy. Neither changed the candidate or workload.
