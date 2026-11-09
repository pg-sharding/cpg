# Reproduce the OR/rare real-AM diagnostic

No PostgreSQL source change was made after C9. Actual runs reuse the six R3 installed trees and repeat ordinary qualification on all six; no new core/build execution is claimed. Their complete checked receipt is BUILD-RECEIPT.json in evidence/. The prior complete source/build wave is preserved at https://github.com/pg-sharding/cpg/tree/experiments/gin-regression-repair-results-b72-20261110/review/gin-regression-repair-20261110 .

For a new machine: use a non-root Linux account, Python3/GCC/GNU make/Perl/flex/bison/binutils/patch/taskset and zlib/OpenSSL development files, 8GB available memory and at least25GB disk. CPU0/4 must be different available physical cores (lscpu -e=CPU,CORE,SOCKET,ONLINE). Use new short output paths and unused ports; never run builds/tests on the archive host. This packet includes the same complete source plan pinned to B72 72b9498df9a369e747f8d96efb5a6cd33c2451e2 with the common prerequisite, not current master. Use a fully materialized local repository containing that ancestor; partial lazy-fetch clones are deliberately unsupported.

```sh
python3 -B build-harness/build.py \
  --git /absolute/local/postgres-repository \
  --source-plan /absolute/packet/build-source/SOURCE.json \
  --output /absolute/new-run/build --core-port 44540

python3 -B campaign.py \
  --build /absolute/new-run/build \
  --output /absolute/new-run/run-r1 --mode diagnostic --profiles --first-port 44600

python3 -B harness/analyze-repair.py \
  /absolute/new-run/run-r1/cohort0 /absolute/new-results/cohort0
python3 -B harness/analyze-repair.py \
  /absolute/new-run/run-r1/cohort1 /absolute/new-results/cohort1
```

The executed method reused /home/reshke/allfuzz/gin-repair-r3-20261110/build, rather than rebuilding. A fresh replay would run the R3 method: clean B/C9_assert, incremental release L4/L8/L9/C9, -O2 -g -fno-lto, OpenSSL, no ICU/readline, make-j2,nice10, all original239 core tests each, same common paths/flags and backend object guard. That is distinct from the newly executed diagnostic. The distributed front-door scripts are the actual used sources, but no additional clean-machine replay of these instructions is claimed.

Always pass --mode diagnostic. This snapshot retains unused inherited mode definitions; they are not the new diagnostic protocol and are not validated as alternatives here. The source/harness inputs are frozen in RUNTIME-INPUTS.json. Setup is automatic from unchanged harness/inputs/setup.sql:200000 generated docs plus NULL/empty and inline fixture, FTS/array/JSONB indexes and the same data formulas/scalar answers. All25 ordered Seq/GIN multisets and scalar/path checks plus eight prepared-query comparisons/cached rescans qualify every six variants. Seven actual-AM answer checks per variant must also pass, including33333 TIDs per dense AND scan. All25 multisets repeat per measured role/cohort.

Four roles B/T/L4/C9; identical B/T executable. Eleven cases: unchanged OR,single_rare,inline,Seq SQL controls plus seven actual-AM loops. Two warm+12 retained balanced Williams4 rounds per case, two fresh reversed CPU/slot/session/case-order cohorts:1232raw/1056retained/176warm. All data stays separate from prior screen/full measurements; no trimming,pooling or twin correction. Each measured call follows an additional untimed literal-answer execution.

The native module calls real index_rescan/index_getbitmap/tbm_free, with correct F_TS_MATCH_VQ scan key, actual installed public headers and no private GIN structure/model. Existing cases: tiny inline10000scans×4TIDs;absent5000×0;selective100×200;full10×200000. Added cases:OR10×200000,dense AND10×33333,single rare1000×200. See protocol.py for exact function SQL and loop counts. CPU/wall measured inside that loop exclude index open,scan begin/end and JSON creation. Whole-command backend CPU and client wall are separate; SQL additionally records EXPLAIN executor time. Do not call the native timings SQL throughput,heap visibility or CREATE INDEX.

Optional --profiles runs B/C9 original OR,rare,Seq queries in separate qualification backends using software cpu-clock:u199Hz/DWARF,3s each with final query allowed to complete. It changes no host settings. Profiled clusters stop before fresh timing clusters; stack text is diagnostic,not PMU cycle attribution or latency samples. Omit --profiles to reproduce only ordinary timing. Final collector verifies original reference builds/final source inventory, own seeds/frozen runtime/module, clean cluster shutdowns and absent own processes/sockets. Export excludes PGDATA,binaries,perf.data,secrets and full runner logs. Preserve failed attempts and use a new directory for a retry.

patches/gin-lazy-adaptive-v9-over-fixed-b72.diff is the same candidate already measured in R3. It is included for a self-contained artifact bundle, not as a new patch to stack. It applies after fixed base8a8c475037bfde101da23cc9b0364c9c020eca93; complete source-plan diffs alternatively apply to B72. Do not apply both forms. Prior-art scope is unchanged and bounded; no priority/current-master/universal-speedup claim.
