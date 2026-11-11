# C9 on VM 51.250.5.199: fixed replication plan

Declared before new build or timing observations, 2026-11-11.

Purpose: measure the unchanged C9 candidate on the newly supplied AMD EPYC
Genoa VM, separately from the previous VM158 results. Use the published R3
source, fixture, queries, timing boundaries, warmups, rounds and analyzers.
No source/threshold/cost changes or selection of favorable queries.

Raw B72: `72b9498df9a369e747f8d96efb5a6cd33c2451e2`.
Common baseline: `8a8c475037bfde101da23cc9b0364c9c020eca93`.
C9: `0ab3bd65c8957ea5e25f9ef8981401f0616d99de`.
Lazy V4 control: `aee770c6ed58bf352fd3c086418b6c0dda93ae42`.

The existing R3 build driver retains its six variants: B/L4/L8/L9/C9 release
and C9_assert. L8/L9 are retained historical controls for the unchanged real-AM
screen, not newly developed candidates. B and assert are full clean builds;
the intervening release snapshots reuse the same build paths and check changed
object identities. All six must pass the original 239 regression tests and
source/header/install verification. GCC release flags: -O2 -g -fno-lto,
LDFLAGS=-fno-lto, OpenSSL, no ICU/readline, nice 10, make -j2.

New output namespaces only, under `/home/reshke/c9-199-1111`. Socket-only
servers; local ports 44740..44745 (core), 44800..44830 (screen), and
44900..44930 (full SQL), checked unused before launch. No archive machine,
foreign service or global PostgreSQL configuration is used.

First run the fixed R3 screen: 12 SQL + four actual-AM cases, six roles,
two warm + 12 retained balanced rounds, two reversed CPU/process placements;
2688 raw / 2304 retained / 384 warm observations. Review successful execution,
answers, order and cleanup. C9 is already selected by the prior source review;
the full SQL comparison is planned regardless of the signs of screen timings.

Then run all 25 SQL cases on B / exact-executable twin T / L4 / C9, two warm
+ 12 retained rounds in each of two fresh cohorts: 2800 raw / 2400 retained /
400 warm observations. Keep OR, dense, full read, rare, absent, inline, lossy,
phrase, NOT and sequential controls. No extra timing repeats based on results.
CPU 0 and 4 must be separate guest cores; confirm topology before execution.

Every campaign creates its own deterministic baseline seed and performs the
unchanged full Seq/GIN ordered-result, prepared-rescan and AM-answer gates.
The measured workload is warm-cache SQL/AM. CREATE INDEX is fixture setup,
not a measured target. Do not call this a cold-storage or current-master test.

Record host/toolchain/topology, startup and shutdown, source/build/input hashes
and bounded host load/CPU-steal observations. Retain all warm samples and
negative results; do not pool cohorts or subtract twin movements. Independently
recompute exported absolute and paired statistics from the new raw records.

Deliver exact source diff/format-patch, English UNSENT draft, new absolute
times/spreads/direct comparisons, comparison with the prior VM, and commands
to reproduce. Publish only synthetic evidence/source/metadata, without PGDATA,
executables, secrets or full runner logs. Stop every owned server after use.
