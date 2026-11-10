# Reference campaign and independent SQL replay

reference-inputs/README.md gives the exact held-artifact staged prepare/smoke/review/run commands.
ORIGIN.json intentionally rejects other prefixes, ELFs or receipts. Do not
edit it or copy old PASS receipts to approve a fresh build. The independent fresh-build frontdoor below was generated and locally
checked only; it has not been executed on a second Linux installation. The
original held-build campaign did execute and its actual receipts/raw results
are in evidence/. These two validation scopes remain separate.

For a fresh independent source build, use the unchanged historical Heap packet's
REPRODUCE.md and complete replay/build-harness, replay/build-source,
replay/oracle and replay/runtime-r2 sources. Build from exact B72 plus each
standalone overlay with the same prerequisite, GCC13.3,-O2 -g -fno-lto,
LDFLAGS=-fno-lto,--without-icu --without-readline --with-openssl,nice 10,j2.
Python3,GNU make/binutils,bison,flex,Perl,pkg-config,OpenSSL/zlib headers and
ordinary non-root Linux are required. That frontdoor builds B/Heap/assert,
core239 each, actual-header valid stream checks and full ordinary qualification;
its setup creates the200002-row stopped seed. A fresh build needs its own
receipts; it is not covered by the held original run identities.

```sh
PACKET=/absolute/path/to/this/short-batch-packet
PARENT="$PACKET/historical-parent"
PGGIT=/absolute/path/to/local/PostgreSQL-Git
RUN=/home/youruser/gin-short-batch-independent-r1
mkdir "$RUN"
python3 -B "$PARENT/replay/build-harness/build.py" --git "$PGGIT" \
 --source-plan "$PARENT/replay/build-source/SOURCE.json" --output "$RUN/build" --core-port 45640
python3 -B "$PARENT/replay/oracle/run-property.py" --build "$RUN/build" --output-new "$RUN/property"
python3 -B "$PARENT/replay/runtime-r2/campaign.py" --build "$RUN/build" \
 --output "$RUN/qualify" --first-port 45600 --mode qualify
python3 -B "$PACKET/tools/generate-sql-replay.py" --cases "$PACKET/reference-inputs/cases.json" \
 --workload "$PACKET/reference-inputs/WORKLOAD.json" --out-new "$RUN/batch100.sql"
```

The generated plain psql script verifies fixed scalar answers and emits every
natural-plan100-rescan aggregate (control 1) and complete EXPLAIN. On fresh copies of the
stopped seed, use each freshly built B/Heap prefix (T is another B copy):

```sh
PREFIX=/absolute/path/from/new/build-receipt/variants/B/prefix
DATA="$RUN/sql-B"
SOCK="$RUN/socket-B"
cp -a "$RUN/qualify/seed" "$DATA"
mkdir "$SOCK"
LD_LIBRARY_PATH="$PREFIX/lib" "$PREFIX/bin/pg_ctl" -D "$DATA" -l "$RUN/sql-B.log" \
 -o "-p 46580 -k $SOCK -c listen_addresses= -c shared_buffers=512MB -c timing_clock_source=system -c autovacuum=off -c jit=off -c max_parallel_workers_per_gather=0" -w start
# Always execute the stop below, including when psql fails.
LD_LIBRARY_PATH="$PREFIX/lib" "$PREFIX/bin/psql" -X -v ON_ERROR_STOP=1 \
 -d "host=$SOCK port=46580 dbname=postgres" -f "$RUN/batch100.sql" > "$RUN/sql-B.txt"
LD_LIBRARY_PATH="$PREFIX/lib" "$PREFIX/bin/pg_ctl" -D "$DATA" -m fast -w stop
LD_LIBRARY_PATH="$PREFIX/lib" "$PREFIX/bin/pg_ctl" -D "$DATA" status
# Expected status return3; pg_controldata must say shut down.
```

Use only your new owned copies/unused ports, never the seed or an unrelated
cluster. Clear inherited PG* and LD_PRELOAD values as the retained Session does.
Repeat on distinct new copies for T/Heap and record new build/source/ELF/header
identities and all plans, including Seq. The plain SQL illustration is not the
balanced240-command campaign: psql\timing reports client elapsed, while
EXPLAIN Execution Time reports executor time, and it measures no backend CPU.
It has not been executed here. The exact campaign separately retains backend
CPU, per-row settings proofs, ordered independent Seq/GIN digests, all balanced
pairs and final shutdown/source proofs. Do not relabel new data as old results.

This new work unit requires the actual full EXPLAIN to show docs and selected
index loops 100 for each batch (control 1); reject cached/decorrelated scan 1.
Ordered row oracles remain single-scan; output totals multiply per-scan frozen
scalars by 100. All reported timings cover the entire command. The plain SQL
frontdoor has only local generation/static checks here, no new Linux replay.
