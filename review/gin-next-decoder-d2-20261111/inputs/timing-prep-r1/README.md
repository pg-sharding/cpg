# Fixed D2 decoder timing input protocol — not executed

This separate prospective capsule compares B/T/D1/D2 after all four clean
B/D1/D2/D2_assert builds and ordinary gates pass and their clusters stop.
It contains no source change, threshold selection or outcome-dependent loop
selection. D1/D2 remain independent alternatives over the same fixed B.
The question is whether D2 removes D1's long-delta CPU regression while retaining
the dense128 gain. Every multibyte/tiny/segment/growth control remains included.

Exactly 25 cells are fixed: the original 18 native decoder cases and loops,
plus old SQL skew1000,dense_and,or_forced,single_forced,single_rare,prefix,seq_control.
The actual native module is the unchanged qualification/decoder-native.c,
compiled during qualification separately against each variant's actual installed
907 headers/flags. Timing prepare reuses those hash-bound modules read-only;
it cannot compile or replace them. The helper calls the actual backend decoder,
not an extracted fragment. Its inner process-CPU clock includes decode allocation,
materialization and free; compression and full generated-TID oracle are outside
that inner clock. Whole-command backend schedstat CPU and client wall include
function/protocol overhead separately. SQL also reports EXPLAIN Execution Time.
No metrics are pooled across those boundaries.

Roles B/T use exactly the same B prefix, postgres ELF and decoder module but
fresh different data copies. Four-role Williams orders are the previously used
12 orders: base [0,1,3,2], four cyclic role shifts, repeated three times. Every
role occupies each position three times and every directed adjacent pair occurs
three times among retained rounds. Two warm rounds precede the 12 retained
rounds. Two fresh cohorts use reversed case and physical placement order.
Totals: 2,800 raw commands / 2,400 retained / 400 warm; smoke 100 commands / zero
accepted. There are three metrics per cell, 600 absolute groups and 900 paired
groups across cohorts, with 10,800 direct round pairs. All six role pairs and
min/median/max/mean/stdev/MAD/individual values are retained. No trimming,
control normalization, repeated grid or causal attribution is authorized.

Preparation verifies full source/install/build/gate/capsule bindings and all
five stopped ordinary gate lifetimes. It copies/fsyncs the immutable qualified
seed and all 12 numeric copies before role assignment. Four copies are smoke
only; eight remain unused until external root approval. Smoke starts four
servers, checks all 25 old SQL ordered Seq/index comparisons per role (100),
then executes one four-role round per cell. Literal results are a separate
identical extra-warm command in each role; each measured command/raw/literal is
fsynced before assertions. Native scalar/checksum/consumption and SQL literal,
index/loops/rows, full semantic plan/cardinality/rechecks and actual per-case
settings are checked. Timings are not accepted during smoke.

After root's independent actual smoke review and live source/prefix/unused-copy/
PID/socket checks, a separate run stage consumes exactly the reviewed freeze
and an external PASS_SMOKE_REVIEW_FOR_FIXED_RUN receipt. It performs the fixed
two cohorts once. Every cluster is owned, Unix-socket-only, shared_buffers 512MB,
JIT/parallel/autovacuum off, max_connections 8; settings are common across roles.
The controller and children inherit nice10 and a 3 GB address-space cap. Actual
backend/server/client CPU affinity is pinned and verified. Default CPU pairs
0:4 then 4:0 reproduce the old controller's parameter default; root must verify
available topology/window before preparation and freeze explicit pairs. These
cohorts are placements on one host, not independent hardware. Do not run builds,
profilers or another timed job concurrently.

After reviewed import to ROOT/inputs/timing-prep-r1, root runs these stages
separately (no auto-run):

```sh
R=/home/reshke/allfuzz/gin-dec-d2-20261111
P="$R/inputs/timing-prep-r1/campaign.py"
python3 -B "$P" --stage prepare --build "$R/build-r1" \
 --qualified "$R/qualification-r1" --output "$R/timing-r1" \
 --first-port 47000 --cpu-pairs 0:4,4:0 --environment-label FRESH_HOST_CLEAN_SCREEN
python3 -B "$P" --stage smoke --build "$R/build-r1" \
 --qualified "$R/qualification-r1" --output "$R/timing-r1" \
 --first-port 47000 --cpu-pairs 0:4,4:0 --environment-label FRESH_HOST_CLEAN_SCREEN
# STOP: actual 100-smoke independent review and root live approval required.
python3 -B "$P" --stage run --build "$R/build-r1" \
 --qualified "$R/qualification-r1" --output "$R/timing-r1" \
 --first-port 47000 --cpu-pairs 0:4,4:0 --environment-label FRESH_HOST_CLEAN_SCREEN \
 --review "$R/ROOT-SMOKE-REVIEW-D2-r1.json"
```

Options must be separated: `--first-port 47000` and `--cpu-pairs 0:4,4:0`.
Smoke ports 47000..47003; cohort ports 47010..47017. Short sockets live in ROOT/s.
Failures preserve raw/status and attempt all owned cleanup; no retries. Before
signals the owned PID/UID/ELF/datadir must match. Shared-load observations must
be labelled SHARED_LOAD_DIAGNOSTIC before freeze; a clean label alone does not
prove the absence of foreign load. Root snapshots and exact-twin evidence are
reported with the result. The source and threshold stay frozen.

For completed collected output, run analyze.py once per cohort, then the independent
auditor (which imports no benchmark/analyzer/validator code and reconstructs its
own schedule, valid decoder expected values, metrics and statistics):

```sh
python3 -B analyze.py COLLECTED/timing-r1/cohort0 analysis0
python3 -B analyze.py COLLECTED/timing-r1/cohort1 analysis1
python3 -B audit-independent-r1.py --run-root COLLECTED/timing-r1 \
 --analysis0 analysis0 --analysis1 analysis1 --answers ../qualification/inputs/answers.json \
 --out-new independent-audit.json
python3 -B review-smoke-r1.py --timing-root COLLECTED/timing-r1 \
 --output smoke-independent.json
```

The independent auditor checks every raw/literal row, all statistics and direct
pairs, chronology, full semantic SQL plans/settings, ordered row references and
B/T identity. Buffer/I/O/fault/runqueue observations remain visible; they are
not a reason to silently discard data. Parent owns collection, root approval and
publication. All current evidence for this new timing capsule is local AST/help,
protocol and unchanged-source/formula checking only; no smoke, accepted timing
or performance result has executed during preparation.
