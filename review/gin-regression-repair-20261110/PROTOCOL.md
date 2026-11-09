# GIN regression repair, 10 November 2026

Inputs are exact B72 plus the same supplied prerequisite in every tree.
Unchanged controls are B, advance V4 and lazy V4. The sole new source candidate
is lazy V7: move the two compressed-suffix cursor pointers into the private
allocation, leaving one pointer in every scan entry. No cursor, decode policy,
pin lifetime or format change is intended. Actual-header compile preflight
passed for both production units; sizes are B824/L4 848/L7 832 bytes and all
21 original field offsets are unchanged. This is not a performance result.

The prior B/A4 gingetbitmap objects have the same instruction shape after
normalizing code addresses/RIP displacements. The new decoded-list body is
outside that function. No code-level explanation of absent or off-path Seq
movements is inferred merely from the previous timing tables.

All old frozen packets stay unchanged. Five new fullclean builds use common
source/build/compiled-prefix paths and separate DESTDIR installs: B/L4/A4/L7
release, plus L7 assertions. GCC13.3, -O2 -g -fno-lto, OpenSSL, no ICU/readline,
nice10, make-j2; original239 core tests in every build. Ordinary qualification
keeps all25 original Seq/GIN multisets/scalars/plans, eight prepared parameter
values and actual-AM answer checks on every build. No expected is regenerated.

Before timing, freeze all sources, modules, SQL, orders, identities and counts.
Use separate owned clusters only on VM158. Foreign workloads are untouched;
the archive host is read-only and is not used here. Every campaign creates a
baseline seed from the unchanged fixture and verifies/fsyncs all physical
copies before assigning roles. Source/install/seed/runtime hashes and own
cluster shutdown are checked afterward. Failed attempts remain separate.

## Prospective finite stages

1. **Null calibration:** five independent processes B/T/N2/N3/N4 use the exact
   same B executable, source and fixture. Original inline, Seq and absent
   commands only; two warm+20 retained Williams5 rounds, two fresh cohorts.
   660 raw/600 retained/60 warm. This measures process/cohort variability with
   no source difference; it is a new three-case diagnostic, not a replay of
   the original 25-case chronology. Do not normalize candidate data by it.
2. **Repair screen:** B/T/A4/L4/L7, ten unchanged SQL cases (common/rare, OR,
   full single, tiny inline, JSONB, lossy AND immediately before Seq, grouped
   skew, inline single, absent) and four actual-AM loop cases. Two warm+20
   retained rounds, two fresh cohorts:3080 raw/2800 retained/280 warm. All ten
   role pairs and every negative remain; no threshold/source/end-point tuning.
   The lazy repair needs repeatable direct L7/L4 gains in the target paths,
   retained selective gains and no newly repeated material cost before it can
   be selected. A failed repair is preserved as a negative experiment.
3. **Full confirmation after reviewing the screen:** B/T/L4/L7 and all25
   unchanged SQL commands, two warm+12 retained Williams4 rounds, two fresh
   cohorts:2800 raw/2400 retained/400 warm. This retains dense-array, empty,
   absent, inline, OR, NOT, lossy and Seq controls. No native result is promoted
   to full SQL and no improvement on current master is claimed.

For five roles, Williams orders are the five rotations of [0,1,4,2,3] and
their reverses; twenty retained rows give every role every position four times.
For four roles use rotations of [0,1,3,2]. Cohort1 reverses case order and role
slots/session births; server/client physical cores0/4 become4/0. Every measured
command follows a literal-answer execution, deliberate extra warming. Keep
SQL executor, whole-command CPU and client wall separate; no trimming, pooling,
control correction or claims of independent-host confidence.

The AM module calls real index_rescan/index_getbitmap/tbm_free with the actual
server and headers. It uses no extracted entry body or modeled buffer services.
Cases: inline10000 scans with4 TIDs each, absent5000 with0, common/rare100 with200,
full10 with200000. It also reports process CPU and monotonic time for that loop;
relation open, scan begin/end and JSON creation are outside that kernel interval.
Both the untimed literal and measured command run the same complete loop. These
are actual-AM loop timings, not heap visibility, SQL throughput or CREATE INDEX.

Separate optional diagnostics profile the original absent, inline and Seq
queries on each B/A4/L4/L7 qualification backend. User-only cpu-clock,199Hz,
DWARF stacks, a3-second perf window with the final query allowed to finish.
Record actual intervals/calls/CPU/queue/ELF/answers and exported stacks/symbols.
They are not accepted paired latency samples or hardware PMU evidence. If perf
is unavailable, preserve the failure and continue ordinary checks; no global
host configuration is changed. Profiled clusters are stopped before fresh
unprofiled benchmark cohorts start.
