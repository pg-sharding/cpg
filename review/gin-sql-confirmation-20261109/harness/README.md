# Fixed-source ordinary GIN performance preparation

LOCAL AST/static preparation only. No build, server, SQL, native module or new
timing has run. This directory does not contain or run concurrency reproducers,
and does not analyze the published fix. Fix0001 is an opaque common prerequisite;
its exact published identity and all fixed source/build qualifications must be
supplied by the parent before a runtime manifest can be accepted.

The useful first comparison is four full-backend roles: B=B72+fix0001;
T=the exact B executable in another fresh owned cluster; L4=the independent
lazy V4 alternative+the same fix; A4=the independent advance V4 alternative+the
same fix. Alternatives are not a patch series and are never stacked. Separate
L5/L6 native results remain experimental negatives, not selected SQL upgrades.
Applying the common fix, resolving source context, building and qualifying
these trees belong to the parent/source agent. No performance result here
validates the fix itself.

The initial SQL matrix keeps all original 17 discovery+8 holdout queries,
byte-identical setup/queries/answers. Data are deterministic 200000 FTS/intarray/
jsonb/builtin-array rows, NULL/empty rows and a256-row inline fixture. The
original setup also creates an ordinary5000-row writes fixture; this runner
does not modify it or start writer/concurrency workloads. Explicit builtin
array operator qualification remains unchanged. No old expected answer is
regenerated. Full row-multiset Seq/GIN and cross-role comparisons are untimed.

Each fresh cohort uses2warm+12retained rounds with Williams4 orders;25×4×14
=1400raw/1200retained/200warm. Run two independent fresh cohorts, reverse case
order and swap server/client physical cores for cohort1:2800raw/2400retained/
400warm total. Keep OR and single full-consumption negatives, dense/inline/
absent/empty/lossy/Seq controls and every exact-twin observation. Freeze the
chosen trees, runtime, fixture identities and full order before samples.
Do not pool new fixed-source cohorts with historical pre-fix observations.

Requirements are Linux/proc, Python3 standard library, own matched PostgreSQL
release builds, intarray installed, system timing clock,512MB shared_buffers,
64MB work_mem, JIT/parallel/memoize off, and dedicated empty fixture databases
reached over local Unix sockets. Use the same compiler/flags/configuration,
common compiled prefix, independent build/DESTDIR trees, `-O2 -g`, no LTO,
nice10 and make-j2. Pin own backends/client to distinct physical cores with
reversed assignments in the second cohort. Do not alter other services.
This minimal adapter does not build PostgreSQL or create/stop postmasters;
the owning outer controller must create all fresh copies, bind their births,
record load/topology and stop/check every own cluster in its finally block.

The runtime file is a NEW parent-qualified receipt. Required top-level keys:
`status=QUALIFIED_FIXED_PERFORMANCE_INPUTS`, `base_commit`=B72,
`fix0001_sha256`=the published patch digest, and `roles` in B,T,L4,A4 order.
Each role supplies absolute `prefix`, local Unix-socket `dsn`, actual
`backend_sha256`, exact fixed `source_commit`, the same `fix0001_sha256`,
`correctness_status=PASS`, and `qualification_receipt_sha256`. The digest is
identity metadata, not a claim that this harness inspected or tested the fix.
Verify source/full-tree/header/compiler/config/ELF bindings and ordinary AM
correctness outside this minimal runner. No ready-to-launch runtime is included.

From a new owned local Linux namespace, once those prerequisites are reviewed:

```sh
nice -n 10 python3 -B run-sql.py --runtime /abs/fixed-cohort0.json \
  --cohort 0 --setup --out-new /abs/new-c0
python3 -B analyze.py /abs/new-c0 /abs/new-c0-analysis
nice -n 10 python3 -B run-sql.py --runtime /abs/fixed-cohort1.json \
  --cohort 1 --setup --out-new /abs/new-c1
python3 -B analyze.py /abs/new-c1 /abs/new-c1-analysis
```

Each role's DSN must name a distinct owned empty database/backend; B/T share
an ELF, candidates use actual separate full backends. `--setup` creates the
fixture and never drops/replaces an existing schema. Sessions are persistent
and close best-effort independently. Failure preserves the attempt and raw;
do not retry, trim or overwrite it. The outer owner retains cluster lifecycle
responsibility. The runner reads only its own backend `/proc` counters/exe.

Every measured EXPLAIN follows its frozen literal aggregate answer: this is
deliberate extra warming. Complete EXPLAIN(ANALYZE,BUFFERS,WAL,TIMING OFF) JSON,
Linux whole-command schedstat CPU/runqueue/IO/faults and monotonic client wall
are retained. Raw is fsynced before parsing/checking the measured response.
SQL Execution Time, whole-command CPU and client wall are separate boundaries.
The analyzer retains absolute min/median/max/mean/sample-stdev/MAD and all six
direct same-round role pairs with every value. No filtering, normalization,
cohort pooling or timing-driven source/threshold changes.

`MICRO-PLAN.json` describes the bounded native follow-up and exact historical
front doors. These generators contain pre-fix source snapshots; their modules
must not be relabelled as fixed-source results. New extraction/header/layout/
release+UBSan qualification and new source receipts are still required. This
packet supplies the SQL adapter and native preparation plan, not a working
fixed-source native build or an independent Linux replay claim.
