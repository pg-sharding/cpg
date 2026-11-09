# Reproduce source, finite checks and the fixed SQL comparison

The source-bound build/gate/controller ran on VM84 and passed the recorded finite checks and both fixed SQL cohorts. Exact deployed input copies retain their preparation-time STATIC ONLY wording; ACTUAL-STATUS.json and collected receipts establish the subsequent actual run. The new local packing/restoration and numerical replay also ran and restored all55files with byte-identical summary. No additional Linux portability rerun or benchmark was performed.

Revision72b9498df9a369e747f8d96efb5a6cd33c2451e2, Linux x86_64/GCC13.3/GNUmake/Python3/Bison/Flex/OpenSSL+zlib development headers/binutils/GDB/taskset/procfs. The source alternatives and full7726-file baseline inventory are in source/. No network fetch or source archive is required: --git points to an existing local repository that already contains exact B72. All source bytes are verified, expected files never regenerated. Native correctness modules compile from the frozen C bytes against each real installed header set and resolve the matching backend's actual helper.

Choose NEW nonexistent output directories, normal user ownership, about20GB for build plus40GB forSQL seed/eightmeasurement/four smoke copies, free ports40640..43,40649,40750..53,40759,40760..63 and guestCPUs4/6 after live checks/host lease. No sudo/perf/sysctl/foreign process changes.

```sh
nice -n10 python3 build-harness/build.py --git /absolute/local/postgres-git --source-plan source/SOURCE.json --output /absolute/new-ios/build --core-port 40640
nice -n10 python3 qualification/gate.py --build /absolute/new-ios/build --correctness-seed /absolute/stopped-baseline-correctness-seed --output /absolute/new-ios/qualification --port 40649
python3 prepare-sql.py --build /absolute/new-ios/build --qualification /absolute/new-ios/qualification --output /absolute/new-ios/sql
nice -n10 python3 /absolute/new-ios/sql/sql-controller.py prepare
nice -n10 python3 /absolute/new-ios/sql/sql-controller.py smoke
```

Each mode has fresh empty build objects in the same common-source/common-build/compiled-prefix paths and a distinct DESTDIR. Modes B/V13/V14 release and V14_assert are serial, make-j2, nice10, CFLAGS=-O2 -g -fno-lto/LDFLAGS=-fno-lto; ICU/readline off/OpenSSL on, assertions off except the final correctness build. Build/install amcheck/pageinspect/pg_visibility. Core239 each (MAX_CONNECTIONS=2) must pass before the separate finite gate.

The historical correctness seed used by the executed qualification is /home/reshke/allfuzz/index-optimizations-20261107-ios-v8/data-correctness-v9, PG20, only read/hashed/copied. Its independently documented replacement recipe: private baseline initdb; create amcheck; wide table with200000rows,i=repeat((g%10000)::text,8) COLLATE C,j=repeat((g%10000)::text,9) COLLATE C,index(i,j),VACUUM(FREEZE,ANALYZE),cleanstop. That replacement recipe was not rerun in this wave. Do not resnapshot expected output if a replacement differs; investigate first. SQL benchmark setup is independent of that historical PGDATA: exact sql-template/setup.sql builds all deterministic measured data afresh and VACUUM FREEZE. The qualification runs all3immutable target outputs on each new copy,751812dispatch checks per4roles,640cache contracts/6941ownership checks on V13/V14/assert, and actual backend/module layouts. Those are finite correctness checks, not new native timings.

prepare-sql.py only materializes checked runtime/template input files. prepare creates8numeric measurement copies/hash/fsyncs all before role assignment, preserving the original heap_f4 VM recipe. smoke uses4EXTRA copies and verifies76actual plans,128uniform validation statements per backend, actual ELFs/CPU/GUCs/stops, seed/eightunusedcopies unchanged,0accepted. review-smoke.py is an offline independent receipt/raw checker, not automatic timing approval. Collect its34explicit paths first, or run it on a root containing those paths:

```sh
python3 review-smoke.py --list-files
python3 review-smoke.py --collection /absolute/new-ios --output /absolute/new-ios-smoke-review.json
```

Independently review actual smoke and live stopped-prefix/PID state. Then write /absolute/new-ios/sql/TIMING-APPROVAL.json containing status APPROVED_FIXED_IOS_V14_SQL, smoke_status_sha256=SHA256(sql/smoke/status.json), input_sha256=SHA256(sql/INPUTS.json). This is an explicit reviewed artifact, not synthesized by the scripts. Then run both fixed cohorts exactly once without trimming or repeats:

```sh
nice -n10 python3 /absolute/new-ios/sql/sql-controller.py 0
nice -n10 python3 /absolute/new-ios/sql/sql-controller.py 1
python3 analyze-sql.py /absolute/new-ios/sql --output /absolute/new-ios/summary.json
```

The two cohorts use backend/client6/4 then4/6, reversed cases and two-slot role rotation. T is exactBinstallation/ELF. 19×4×(2warm+12retained)×2=2128raw/1824retained/304warm. Statement timeout60s, reply deadline75s, all raw append/flush/fsync before acceptance; whole-tree structural/loop/HF/direction/filter plan checks and0retainedsharedreads. Every timed backend follows128identical reference/index/checksum/GUC statements. There is no extra literal query before every EXPLAIN in this inherited protocol.

Metrics: EXPLAIN execution ms; ownbackend schedstat CPU/runqueue; clientwall; psqlCPU. Display absolute min/median/max and every six direct pairs per metric/case/cohort. Percentages are medians of same-round ratios, not ratios of absolute medians; negative is faster. Keep all LIMIT/oneattr/mixed/heap/Seq/regular-index regressions and full raw/host/plan data. SharedhostguestCPUplacements are not independent hardware or source-causal scheduler/layout proof. CREATE INDEX is setup only.

Restore the exact collection without SQL:

```sh
python3 restore-raw.py --output /absolute/new-restored-collection
python3 analyze-sql.py /absolute/new-restored-collection/sql --output /absolute/new-restored-summary.json
```

Restoration verifies compressed chunks, decompressed whole-line bytes and every original collection SHA. RAW-CHUNKS.json and COLLECTION-MANIFEST.json document all samples; no observations are dropped. Source/build/gate/smoke inputs and historical original expected bytes stay unchanged. No PGDATA, ELF, archive or full runner log is included.

Recount and render every statistic without a server:

```sh
python3 audit-results.py --collection /absolute/new-restored-collection --output /absolute/new-independent-audit
python3 render-results.py --statistics analysis/all-statistics.json.gz --output /absolute/new-rendered-analysis --markdown /absolute/new-BENCHMARKS.md
```

audit-results.py uses its own median/mean/sample-stdev/MAD formulas without importing analyze-sql; it reuses only the separate smoke reviewer's finite source/gate/plan/history helpers. The executed analyzer's zero-denominator rule is unchanged; undefined ratios are counted explicitly and all absolute/difference/raw pairs are retained. analysis/STATISTICS-COMPRESSION.json binds the lossless4,447,671-byte all-statistics.json to its gzip transport; no statistics or observations are dropped.

Posthoc source commit113e61347b43d2ae4afb187944ede9e9f6108c24 on experiments/btree-ios-v14-b72-20261109 is source-byte identity only. Historical SOURCE/build receipts keep null commit fields and their original hashes. It did not trigger a new build or sample.
