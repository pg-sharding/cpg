# New matched IOS V14 SQL campaign

This is a new source-bound campaign adapted from the actually executed V13 protocol. At preparation the new scripts are STATIC ONLY (AST/help/source/schedule checks); no new build/SQL result or Linux replay is claimed here. Parent root owns VM84 live checks, leases, transfer, launch and later actual receipts. Existing frozen V13/V14/source packets are unchanged.

Use Linux x86_64, GCC13.3, GNU make, Python3, Bison/Flex, OpenSSL/zlib development headers, binutils objdump, GDB, taskset and readable procfs. A normal OS user owns all new paths. Reserve CPUs4/6 and ports40640..43 core,40649 qualification,40750..53 measurement,40759 setup,40760..63 smoke after checking live host availability. No perf/sudo/sysctl or foreign process changes. Allow about20GB for build plus40GB for freshSQL8copies+4smoke copies; actual fixture size and runtime are recorded by receipts.

Pinned source B72 72b9498df9a369e747f8d96efb5a6cd33c2451e2. V13/V14 are alternatives, not a series. source/SOURCE.json and all7726 base files are authoritative; exact patches/snapshots included. Recreate a baseline archive from an existing local exact public Git repository with git archive B72 (optionally gzip); the script checks contents rather than relying on archive compression bytes. No source from network is fetched.

Run from the transferred campaign inputs, with new nonexistent output roots:

```sh
nice -n10 python3 build-harness/build.py --source-archive baseline.tar.gz --source-plan source/SOURCE.json --output /home/reshke/allfuzz/btree-ios-v14-campaign-20261109/build --core-port 40640
# Parent review actual build receipt and four core239 logs first.
nice -n10 python3 qualification/gate.py --build /home/reshke/allfuzz/btree-ios-v14-campaign-20261109/build --correctness-seed /home/reshke/allfuzz/index-optimizations-20261107-ios-v8/data-correctness-v9 --output /home/reshke/allfuzz/btree-ios-v14-campaign-20261109/qualification --port 40649
# Parent review actual finite gate, zero timing and cleanup first.
python3 prepare-sql.py --build /home/reshke/allfuzz/btree-ios-v14-campaign-20261109/build --qualification /home/reshke/allfuzz/btree-ios-v14-campaign-20261109/qualification --output /home/reshke/allfuzz/btree-ios-v14-campaign-20261109/sql
nice -n10 python3 /home/reshke/allfuzz/btree-ios-v14-campaign-20261109/sql/sql-controller.py prepare
nice -n10 python3 /home/reshke/allfuzz/btree-ios-v14-campaign-20261109/sql/sql-controller.py smoke
```

The qualification seed is an existing stopped B72 seed, only read/hashed/copied. The historical independently documented replacement recipe is200000 rows in wide, i=repeat((g%10000)::text,8) COLLATE C,j=repeat((g%10000)::text,9) COLLATE C,index(i,j),amcheck extension,VACUUM(FREEZE,ANALYZE),cleanstop. That recipe has not been re-executed by this preparation. Do not regenerate SQL expected outputs from V14 if a new fixture differs; diagnose any negative honestly. The measured SQL seed has no historical PGDATA dependency: exact setup.sql creates it afresh.

prepare-sql.py only writes a new runtime/template manifest; it starts no server or samples. Then prepare creates/stops/verifies seed and copies/hashes/fsyncs all8measurementdatasets before assignment. smoke creates4extra copies and executes all19 plans with all4roles and128validationstatementsperbackend,0accepted. Root independently reviews smoke/status.json, raw76plans, actual backend/PID/ELF/affinity/GUCs, identical128histories and all cleanup/unchanged-copy proofs. Keep failures. Only after PASS freeze runtime/input/plan bytes and a separate root-written TIMING-APPROVAL.json containing status APPROVED_FIXED_IOS_V14_SQL, smoke_status_sha256 and input_sha256 exact current hashes. This is a concrete artifact review, not an automated approval from this harness.

After that independent review, run exactly these fixed actions once:

```sh
nice -n10 python3 /home/reshke/allfuzz/btree-ios-v14-campaign-20261109/sql/sql-controller.py 0
nice -n10 python3 /home/reshke/allfuzz/btree-ios-v14-campaign-20261109/sql/sql-controller.py 1
python3 analyze-sql.py /home/reshke/allfuzz/btree-ios-v14-campaign-20261109/sql --output /home/reshke/allfuzz/btree-ios-v14-campaign-20261109/summary.json
```

19cases×4roles×(2warm+12retained)×2cohorts=2128raw/1824retained/304warm, all6directpairs, all5metrics. Negative percentages mean faster for numerator; paired ratio medians are not ratios of displayed medians. Backend CPU/runqueue from schedstat, EXPLAIN execution, client wall and psql CPU are separate metrics. Raw plans/host samples are appended+fsynced before acceptance, no trimming/control subtraction/pooling/repeat. All ranges and negative short/mixed/heap/Seq controls remain. The two guest CPU placements on sharedVM84 are not independent hardware proof or a source-causal layout diagnosis. CREATE INDEX is fixture creation only; native oracles are correctness checks, not a new native timing benchmark.

Keep compact source/header/ELF/core/native/ownership/smoke/SQL/PID proof, all raw/absolute/directpair tables, English UNSENT draft and reproduction scripts in the final packet. Exclude PGDATA, binaries, secrets and full runner logs. Source code/expected files stay frozen.
