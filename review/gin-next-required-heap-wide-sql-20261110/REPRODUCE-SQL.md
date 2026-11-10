# Reproduce the wide-OR SQL experiment

The exact source is historical B72
72b9498df9a369e747f8d96efb5a6cd33c2451e2 with fixed B
8a8c475037bfde101da23cc9b0364c9c020eca93 or the independent heap alternative
03dff8bfa5075e5838c7fbffc712d0b79d03f13d. The top-level .diff/.patch applies
over fixed B. Do not apply both alternative sources or compose this with K3.

The complete earlier frozen packet is in historical-parent/. Its REPRODUCE.md
and replay/ contain source manifests/overlays, clean-build controller, exact
synthetic setup, original native/AM micro-harness and all original controls.
They document how to obtain an authentic local B72 source archive or local
repository, build release and assertions variants, initialize fixtures and
run gates. Earlier measurements stay separate from the new SQL screen.

Actual toolchain: Ubuntu GCC13.3, Python3, GNU make, binutils, Perl, Bison/Flex,
OpenSSL/zlib development dependencies; -O2 -g -fno-lto, LDFLAGS=-fno-lto,
empty CPPFLAGS, --without-icu --without-readline --with-openssl, make-j2,
nice10. Source/header/install/configure/ELF receipts are in historical-parent/.
The new reference campaign reused those exact qualified builds and seed;
it compiled no backend or module. Source/seed hard pins in reference-inputs/
describe that actual held-build campaign and are not fresh-build identities.

Fresh source/setup instructions are complete in historical-parent/; use new
owned Linux paths, prefixes, clusters and unused ports. The exact setup has
200002 docs including two special rows. The positive queries and Seq control
here return precisely IDs1..200000, count200000 and sum20000100000. Expected
ordered digest is01b59173dc3205893607560d9f6caca711aa6c0f3303db7bbccb99552a9fc33a.
No old PGDATA, executable or support library is required for a fresh setup.

After creating the exact fixture in independently built B/Heap clusters, emit
the convenience SQL from the stored expressions:

```sh
python3 -B tools/generate-sql-replay.py --cases reference-inputs/cases.json --out-new /tmp/heap-wide.sql
/absolute/B/bin/psql -X -v ON_ERROR_STOP=1 -h /new/B/socket -p 5541 -d postgres -f /tmp/heap-wide.sql
/absolute/Heap/bin/psql -X -v ON_ERROR_STOP=1 -h /new/Heap/socket -p 5542 -d postgres -f /tmp/heap-wide.sql
```

This new convenience generator was AST checked locally; it was not executed
against PostgreSQL. It emits the exact literals and EXPLAIN statements, without
rewriting query bytes. psql timing is a convenience wall metric; EXPLAIN
Execution Time is executor time. Neither is the reference harness's whole
backend schedstat CPU. Do not combine these metric boundaries or label this
simple two-run command as a matched reproduction of the published statistics.

The actual matched protocol was B/T/Heap, eight cases, all six role permutations,
two warm plus six retained rounds, two fresh cohorts:384 raw /288 retained /
96 warm. All9 numeric seed copies were hashed/fsynced before role assignment;
three smoke copies were used for24 zero-accepted observations and independently
reviewed before the six accepted copies ran. Cohort1 reverses cases and births.
Server/client affinity0:4 then4:0, 512MB shared buffers,64MB work_mem, system
timing clock, parallel/JIT/memoize/autovacuum off. This records guest CPU labels,
not isolated physical hardware. A separate literal before every EXPLAIN adds
warming. No own compiler/profile overlap, global cache drop or foreign-job stop.

All raw observations are already in evidence/run-r1/. Offline replay needs
only Python3, no PostgreSQL or VM, and new nonexistent output directories:

```sh
python3 -B reference-inputs/analyze.py evidence/run-r1/cohort0 /tmp/heap-analysis0
python3 -B reference-inputs/analyze.py evidence/run-r1/cohort1 /tmp/heap-analysis1
python3 -B tools/audit-independent-r1.py --inputs reference-inputs --old-am-inputs historical-parent/replay/timing-r1/harness/inputs/timing-cases.json --results evidence/run-r1 --mode screen --analysis0 /tmp/heap-analysis0 --analysis1 /tmp/heap-analysis1 --out-new /tmp/heap-audit.json
```

Each cohort must reproduce72 absolute and72 pair groups with432 direct pairs,
including full ranges, means, sample SD and MAD. The complete384 raw, all warm
and negative widths, Seq controls and IO/runqueue/faults remain. All three
metric boundaries and three pairs are retained without pooling, trimming,
normalization or significance/causal claims. Root executed this relocated
offline replay and byte comparison; ROOT-PACKET-REPLAY-r1.json records it.
Fresh SQL measurements on another host remain separate new evidence.
