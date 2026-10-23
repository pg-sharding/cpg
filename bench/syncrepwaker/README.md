# Synchronous replication waker experiment

`sync_rep_waker = on` (default, requires restart) moves queue traversal and
backend latch wakeups into the `sync rep waker` auxiliary process. WAL senders
still calculate and publish confirmed write/flush/apply LSNs under `SyncRepLock`.
They notify the waker only when a queue contains an eligible waiter. Multiple
standby replies can be covered by one queue pass.

`sync_rep_waker = off` uses direct WAL sender wakeups in the same binary. Direct
wakeups also cover startup, fork failures, and the interval between a clean
waker exit and its replacement. On clean exit the waker unregisters under the
lock and drains already confirmed waiters. Clearing `synchronous_standby_names`
continues to release all queues in the checkpointer, even if the waker is stuck.
An unclean waker exit triggers cluster crash recovery, as for other auxiliary
processes modifying shared memory.

The waker still takes `SyncRepLock` while traversing queues and setting backend
latches. This experiment removes that work from the sender, but does not remove
lock contention or the wakeup CPU cost. The extra handoff may hurt commit
latency, particularly at low concurrency.

Build with assertions for correctness testing:

```sh
mkdir build
cd build
../configure --prefix="$PWD/../install" \
  --libdir="$PWD/../install/lib/postgresql" \
  --without-mdblocales --with-openssl \
  --enable-debug --enable-cassert --enable-depend --enable-tap-tests
make -j8
make install
make -C src/test/recovery check \
  PROVE_TESTS='t/007_sync_rep.pl t/130_every_sync_rep.pl t/131_sync_rep_waker.pl'
```

`--without-mdblocales` is needed only if the MDB locale library is unavailable.
Use a clean rebuild when first switching to this branch: process enums and
shared-memory structures have changed. For benchmarks, build without assertions
(`--disable-cassert`), since assertion-only queue validation changes their cost.

The Linux benchmark creates and stops its own primary and synchronous standby
in a **new** output directory. It uses durable INSERT-only transactions,
alternates on/off order, and saves pgbench output, process CPU time, configuration,
and JSON results. Both servers and the client run on the same host; this is a
controlled smoke benchmark, not a substitute for the original workload.

```sh
python3 bench/syncrepwaker/run_bench.py \
  --bindir "$PWD/install/bin" --output /tmp/syncrepwaker-results \
  --clients 1 32 128 --seconds 10 --repeats 3
```

Add `--perf` to sample the sender and waker at 199 Hz and save flat symbol
profiles. This requires permission to run `sudo -n perf`; it does not change
system profiling settings. The default ports are 56432/56433; use `--port` to
choose another pair. No results directory is overwritten.

## Run on 2026-10-23

Base: `MDB_18_6_prestable` at `dc9f4918121`. Host: `158.160.212.50`,
8 vCPUs (AMD EPYC Genoa, 4 cores with SMT), Linux 6.8.0-147-generic.
Source and artifacts are in `/home/reshke/pgpg2` on that host.
Release build: `-O2 -g -fno-omit-frame-pointer`, OpenSSL enabled, assertions and
MDB locales disabled. Primary, standby, and clients shared this host; SSL was
not enabled for the connections. Default durable commit and fsync settings were
preserved. Each cell below is the median of three 10-second runs, with a
2-second warmup and alternating off/on order. All runs had zero failed
transactions. Raw measurements: [results-2026-10-23.json](results-2026-10-23.json).

| Clients | TPS off | TPS on | TPS change | Mean latency off/on, ms |
| --- | ---: | ---: | ---: | ---: |
| 1 | 250 | 248 | -0.8% | 3.999 / 4.031 |
| 32 | 5,448 | 5,500 | +1.0% | 5.873 / 5.818 |
| 128 | 16,473 | 15,044 | -8.7% | 7.770 / 8.508 |

| Clients | Sender CPU off/on, microseconds per transaction | Sender + waker CPU off/on, microseconds per transaction |
| --- | ---: | ---: |
| 1 | 122.23 / 124.97 | 122.23 / 149.16 |
| 32 | 14.40 / 10.07 | 14.40 / 18.20 |
| 128 | 7.60 / 2.81 | 7.60 / 8.61 |

The CPU figures use `/proc/PID/stat`, divided by pgbench TPS times the requested
10-second measurement interval. They cover only the sender and waker, not the
whole cluster. Flat perf profiles place `SyncRepWakeQueue` in the sender with
the feature disabled and in the waker with it enabled. The sender is relieved
of work at higher concurrency, but the combined process CPU cost increases.
This short, disk-sensitive local run does **not** show a throughput win; the
128-client result regressed and individual runs vary substantially. The original
workload, including its WAL volume, network, and TLS, still needs measurement.

On-server artifacts:

- `build/regress-waker.log`: all 236 SQL regression tests passed.
- `build/recovery-waker.log`: SyncRep and EVERY tests plus the initial waker test
  passed (57 assertions).
- `build/recovery-waker-extended.log`: final waker test passed (36 assertions),
  including all three wait modes, cancellation, config reload, clean worker
  restart, worker crash recovery, disabled mode, and promotion.
- `build/recovery-lifecycle.log`: streaming, crash restart, promotion pages, and
  shared-memory tests passed (86 assertions).
- `bench-results/`: pgbench logs, per-run PID profiles, raw perf data, server
  logs, and stopped test clusters.
- `install/`: assertion-enabled binaries; `install-release/`: benchmark binaries.

## Latency comparison against the parent binary

`compare_bench.py` accepts two installations built with matching compiler
options: the unmodified parent and the feature commit. `base`, `off`, and `on`
mean the parent binary, feature binary with direct wakeups, and feature binary
with delegated wakeups, respectively. All variants use the same baseline
pgbench executable and the same baseline standby. The primary is restarted
between variants. Run order rotates between repetitions.
The current harness creates a persistent physical replication slot with
`pg_basebackup -C -S bench_standby -R`, so the primary retains WAL needed by
the standby across restarts and bursts of WAL generation.

```sh
python3 -m unittest discover -s bench/syncrepwaker -p test_compare_bench.py -v
python3 bench/syncrepwaker/compare_bench.py \
  --baseline-bindir "$PWD/install-baseline/bin" \
  --feature-bindir "$PWD/install-release/bin" \
  --output "$PWD/compare-confirm-ram" \
  --data-root /dev/shm/pgpg2-confirm-ram-data \
  --log-root /dev/shm/pgpg2-confirm-ram-logs \
  --cases bench/syncrepwaker/ram-confirm-cases.json \
  --variants base off on --seconds 60 --warmup 10 --repeats 3 --discard-data
python3 bench/syncrepwaker/analyze_compare.py compare-confirm-ram/results.json
```

Use a new output/data/log directory for every invocation. Without `--data-root`,
data are stored below the output directory. The benchmark always enables
`fsync` and `full_page_writes`. A tmpfs data directory removes physical disk
latency to diagnose CPU and wakeup effects; it does not provide durability
across host failure. It complements the tests on the server's persistent disk.
`--discard-data` removes only this invocation's temporary clusters after a
successful run. Failed runs retain their clusters for inspection.

Every transaction is logged, with no sampling, into the separate log directory.
Putting that directory in tmpfs avoids competing disk writes from the client.
After each run, logs are compressed into the output directory and removed from
the temporary log directory. The measurement covers a full interval after
warmup, while the same pgbench sessions remain connected; four extra seconds
at the end keep processes alive for the final CPU snapshot. Quantiles use
transactions completed inside the measurement window and the exact nearest-rank
definition, with microsecond resolution. The results include five-second
subwindows to expose stalls and run instability.

In rate-limited cases, the main latency includes delay from the transaction's
scheduled arrival. `execution` subtracts pgbench's scheduling lag, which is
reported separately. A low server execution percentile alone must not hide
an overloaded client queue. No latency limit or transaction dropping is used.
Compare achieved TPS with the requested rate before interpreting percentiles.

CPU snapshots include primary and standby postmasters, their live children,
and the pgbench process. They count process CPU time, not all kernel interrupt
work; host busy, I/O wait, and steal percentages are also recorded. Missing
processes are flagged. Context-switch fields are Linux process-leader counters,
so the pgbench counters do not include every client thread. The timed runs do
not run perf. The comparison script
reports the median of per-run quantiles and their range, rather than treating
millions of correlated transactions as millions of independent experiments.

The JSON case files cover small INSERTs, 1 KiB INSERT payloads, fixed arrival
rates, and WAL-only messages. The message workload uses transactional
`pg_logical_emit_message` to generate replication traffic without growing a
heap, so it is a diagnostic for sender work rather than a typical application
transaction. Add `--tls` to encrypt both pgbench and replication connections.

### Saturated fast-storage result, 2026-10-23

On the same 8-vCPU host, three 60-second measurement windows per variant
(10-second warmup each) compared `dc9f4918121` with `9b0f51c718c` using 128
clients and tiny INSERTs. The primary and the common baseline standby stored
their data in tmpfs; pgbench logs also went to tmpfs. This is the CPU/wakeup
diagnostic, not a durable-storage result. Run order was base/off/on, off/on/base,
on/base/off. The table shows medians across runs, not pooled quantiles.

| Primary variant | TPS | p50 ms | p95 ms | p99 ms | p99.9 ms | Process CPU, us/tx |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Parent | 60,883 | 0.817 | 6.302 | 11.040 | 16.734 | 107.30 |
| Feature, waker off | 61,456 | 0.850 | 6.200 | 10.798 | 16.283 | 106.68 |
| Feature, waker on | 61,917 | 1.968 | 3.150 | 3.800 | 5.471 | 99.75 |

Delegation reduced median p99 by 65.6% and p99.9 by 67.3%, with similar TPS
(+1.7%). It worsened p50 by 141%. Process CPU includes primary, standby, and
client. The p99 ranges were 10.703–17.962 ms for the parent,
10.422–19.858 ms with the waker off, and 3.606–10.299 ms with it on. Thus the
size of the benefit varied considerably, even though the on/off distinction
was visible. This supports a use case for tail latency near CPU saturation;
it does not establish that delegation improves latency at lower offered loads.

### Fixed arrival rates and TLS diagnostics

The fixed-rate runs used the same one synchronous standby and
`synchronous_commit=on`. These are medians across three runs. Latency includes
pgbench scheduling lag, so these figures describe response time relative to
the requested arrival rather than just time executing a query. Disk means
the host's persistent block volume; its physical storage medium was not
established.

| Workload | Measured seconds/run | Parent TPS | Waker TPS | Parent p50 ms | Waker p50 ms | Parent p99 ms | Waker p99 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Tiny INSERT, tmpfs, 128 clients, 15k/s | 30 | 14,970 | 14,970 | 0.325 | 0.365 | 0.738 | 1.054 |
| 1 KiB INSERT, disk, 128 clients, 10k/s | 45 | 9,984 | 9,973 | 8.644 | 9.879 | 270.862 | 212.660 |

At 15k/s, p99 worsened by 42.8% and process CPU per transaction increased
from 253.13 to 263.60 us. Disk p99 varied from 96.137 to 828.563 ms for
the parent and from 150.769 to 668.150 ms with the waker. The median disk
execution-only p99 was 33.094 versus 35.748 ms. Given the overlapping
response-time ranges and large scheduling queues, the lower median disk
response p99 is not convincing evidence of a benefit.

At 30k/s on tmpfs, both variants had severe intermittent queues. The p99
response times for repetitions 1/2/3 were 0.901/14.184/908.397 ms for the
parent and 0.971/3854.701/0.954 ms with the waker. In the 3854.701 ms run,
scheduling-lag p99 was 3850.923 ms and execution-only p99 was 11.479 ms.
All these observations are retained in the results. A median alone hides
these stalls and cannot establish a reliable improvement at this rate.

WAL-message workloads were exploratory: one 15-second measurement per
variant after five seconds of warmup, with 128 clients, tmpfs data and TLS
on both client and replication connections. They exercise different WAL
volumes without growing a table. They are not substitutes for an application
workload, and their small sample does not establish a reproducible gain.

| WAL message per transaction | Parent TPS | Waker TPS | Parent p50 ms | Waker p50 ms | Parent p99 ms | Waker p99 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 KiB | 43,480 | 38,532 | 2.621 | 3.183 | 7.722 | 5.583 |
| 32 KiB, persistent replication slot | 20,508 | 22,062 | 6.244 | 5.701 | 8.303 | 9.398 |

The first 32 KiB attempt timed out on the unmodified parent: the standby
requested a WAL segment that the primary had already removed. That attempt
had no persistent physical replication slot; the feature variant was never
started. It has no completed result row. Adding the slot to the harness
allowed both variants to complete in a fresh run. The earlier successful
datasets used no persistent slot, so the 32 KiB result is kept as a separate
diagnostic. At this WAL volume, `max_wal_size=512MB` caused frequent
checkpoints in both variants; this is another limit of the short diagnostic.

These results support retaining delegation as a workload-dependent option
for tail latency near CPU saturation. They do not justify enabling it by
default for every workload: median latency and light-load latency regressed,
and a general throughput gain was not established. The feature commit
currently defaults `sync_rep_waker` to `on`; these measurements do not change
that setting. A default change needs a separate implementation decision.

### Saved evidence and reproduction

`comparison-results-2026-10-23.json` contains all 47 completed runs, covering
54,224,304 transactions in their measurement windows. It preserves per-run
quantiles, five-second subwindows, scheduling lag, execution time, WAL volume,
CPU time by role, host CPU counters, and missing CPU snapshot counts. There
were no failed or skipped transactions in these completed measurement windows.
The one incomplete 32 KiB attempt is recorded separately in
`comparison-environment-2026-10-23.json`, together with configurations, build
options, binary hashes and run arguments. Eight initial disk-screen runs
flagged a short-lived monitor connection in CPU accounting; later runs
exclude that connection. Do not use those initial CPU totals for conclusions.

```sh
python3 bench/syncrepwaker/analyze_compare.py \
  bench/syncrepwaker/comparison-results-2026-10-23.json
```

The eight datasets and corresponding case files are:

| Dataset | Cases | Variants | Seconds | Warmup | Repeats | Data | TLS |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| compare-screen-ssd | screen-cases.json | base on | 10 | 4 | 1 | disk | no |
| compare-screen-ram | screen-cases.json | base on | 10 | 4 | 1 | tmpfs | no |
| compare-confirm-ram | ram-confirm-cases.json | base off on | 60 | 10 | 3 | tmpfs | no |
| compare-rate-ram | ram-rate-cases.json | base on | 60 | 10 | 3 | tmpfs | no |
| compare-light-ram | ram-light-cases.json | base on | 30 | 10 | 3 | tmpfs | no |
| compare-rate-disk | disk-rate-cases.json | base on | 45 | 10 | 3 | disk | no |
| compare-message-tls | message-cases.json | base on | 15 | 5 | 1 | tmpfs | yes |
| compare-message32k-tls-slot | message32k-cases.json | base on | 15 | 5 | 1 | tmpfs | yes |

The first two datasets are short screens; use the longer repeated runs for
conclusions. `compare-message-tls` completed only the 8 KiB pair before its
32 KiB attempt failed. The current slot-enabled harness avoids that retention
failure when rerunning `message-cases.json`.

On the benchmark host, each `/home/reshke/pgpg2/<dataset>/` retains the full
metadata, individual JSON rows, pgbench output, primary/standby logs and gzip
transaction logs. Both servers and the client ran on one 8-vCPU host without
CPU pinning or host isolation, which limits attribution of stalls and transfer
to a production deployment. No original application workload was available.

## Hybrid wakeup experiment

`sync_rep_waker_direct_limit` permits the sender to release a small confirmed
batch directly. The limit is a total across the write, flush and apply queues;
unconfirmed waiters do not count. If the total exceeds the limit, the entire
batch is delegated. Counting stops at the first limit+1 confirmed entries, so
the sender does not traverse a large ready batch. The range is 0–1024 and the
setting can be reloaded. Its default is 0, preserving fully delegated wakeups
until a useful threshold has been established.

The harness accepts `hybrid4`, `hybrid8`, `hybrid16`, `hybrid32` and
`hybrid64` variants. They enable
the waker and set the corresponding direct limit on the primary command line.
`on` uses the feature binary's default limit of 0. The parent binary still
uses no feature-specific parameters. `hybrid-cases.json` tests both a fixed
15k/s arrival rate and unlimited tiny INSERTs at 128 clients. Use the same
invocation as the latency comparison above with
`--cases bench/syncrepwaker/hybrid-cases.json`,
`--variants base on hybrid4 hybrid8 hybrid16`,
`--seconds 20 --warmup 5 --repeats 1` and new output/data/log directories.

Recovery testing with assertions passed all 84 assertions across
`007_sync_rep`, `130_every_sync_rep`, `131_sync_rep_waker` and
`132_sync_rep_waker_hybrid`. The hybrid test suspends the waker and sender to
check direct wakeups in all three modes, the exact threshold, delegation above
the threshold, and exclusion of an unconfirmed apply backlog. The existing
test explicitly uses limit 0 to continue testing fully delegated wakeups,
cancellation and worker lifecycle behavior.

### Hybrid measurements, 2026-10-23

The parent remains `dc9f4918121`. The hybrid algorithm measured here is
`73b816456c0`, built with the same release flags as the previous comparison.
All feature controls use that same new binary: `on` means direct limit 0,
and `hybrid8` means direct limit 8. The common standby and pgbench use the
parent binaries. Data and transaction logs are in tmpfs, one synchronous
standby uses a persistent physical slot, and synchronous commit waits for
remote flush. All participants share the same 8-vCPU host; these are CPU and
wakeup diagnostics rather than durable-storage or network-separated results.

The first screen measured 20 seconds after five seconds of warmup per
variant, once each, at both 15k/s and unlimited load with 128 clients.
Limits 4/8/16 all brought light-load p50 close to the parent, while saturated
p50 remained around 2 ms and p99 around 3.7–3.8 ms.

A separate 20-second saturated screen checked larger limits:

| Variant | TPS | p50 ms | p99 ms | p99.9 ms |
| --- | ---: | ---: | ---: | ---: |
| Parent | 59,581 | 0.849 | 11.195 | 16.561 |
| Fully delegated | 60,486 | 2.027 | 3.736 | 5.288 |
| Direct limit 32 | 61,698 | 1.875 | 6.212 | 11.120 |
| Direct limit 64 | 59,435 | 1.069 | 10.912 | 16.252 |

The larger limits traded away the tail benefit as median latency decreased.
These single runs do not establish an optimal threshold. Limit 8 was selected
for repeated testing as a small-batch compromise.

At 15k/s, three 30-second windows after ten seconds of warmup produced the
following medians of per-run metrics. Run order rotated base/on/hybrid8,
on/hybrid8/base, hybrid8/base/on.

| Variant | TPS | p50 ms | p95 ms | p99 ms | p99.9 ms | Process CPU, us/tx |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Parent | 14,970 | 0.317 | 0.425 | 0.531 | 1.116 | 252.24 |
| Fully delegated | 14,970 | 0.348 | 0.484 | 0.596 | 1.861 | 263.32 |
| Direct limit 8 | 14,970 | 0.326 | 0.462 | 0.579 | 1.573 | 252.44 |

The hybrid removed 71% of the extra median latency in this case: the gap
relative to the parent fell from 31 to 9 microseconds. Process CPU, including
both servers and the client, returned close to the parent level. Response p99
still exceeded the parent's median; its ranges were 0.506–0.552 ms for the
parent, 0.583–0.930 ms for fully delegated wakeups and 0.547–0.947 ms for
limit 8. This is a reduction in the small-load median regression, not a
general latency improvement.

The saturated confirmation used three 60-second measurement windows per
variant after ten seconds of warmup, with the same rotating order:

| Variant | TPS | p50 ms | p95 ms | p99 ms | p99.9 ms | Process CPU, us/tx |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Parent | 62,070 | 0.835 | 5.969 | 10.620 | 15.865 | 107.16 |
| Fully delegated | 63,770 | 1.923 | 3.020 | 3.569 | 4.796 | 99.33 |
| Direct limit 8 | 63,745 | 1.913 | 3.038 | 3.638 | 4.848 | 98.72 |

Limit 8 did not resolve the saturated median regression. It retained most of
the tail benefit relative to the parent: p99 fell by 65.7%. Per-run p99 ranges
were 10.617–11.314 ms for the parent, 3.536–3.725 ms for fully delegated wakeups
and 3.487–4.208 ms for limit 8. Relative to full delegation, the hybrid's
median p99 was 1.9% higher, with nearly identical throughput and p50.

The medians of mean transaction latency were 2.043 ms for the parent,
1.966 ms for full delegation and 1.967 ms for limit 8. Thus a higher
transaction p50 coexists with a lower mean and shorter tail. Transaction
quantiles alone cannot isolate the time spent handing work to the waker;
timing the confirmed-LSN-to-backend-wakeup path would be needed for that.

To try the small-batch path, configure:

```conf
sync_rep_waker = on
sync_rep_waker_direct_limit = 8
```

The direct limit is reloadable. Its default remains 0; a globally optimal
threshold was not established. The tested hybrid improves the small-load
median tradeoff, while larger tested limits reduce the saturated median at
the cost of the tail benefit.

`hybrid-results-2026-10-23.json` preserves all 32 new runs and 50,290,747
measured transactions, including all screen thresholds. There were no failed
or skipped transactions in the measured windows and no missing CPU snapshots.
`hybrid-environment-2026-10-23.json` records the build, binary hashes,
variant settings, configurations and run arguments. Raw transaction gzip logs,
individual rows, pgbench output and server logs remain on the benchmark host.
The temporary clusters from successful runs were stopped and removed.

| Dataset | Cases | Variants | Seconds | Warmup | Repeats |
| --- | --- | --- | ---: | ---: | ---: |
| compare-hybrid-screen | hybrid-cases.json | base on hybrid4 hybrid8 hybrid16 | 20 | 5 | 1 |
| compare-hybrid-large-screen | ram-confirm-cases.json | base on hybrid32 hybrid64 | 20 | 5 | 1 |
| compare-hybrid-light | ram-light-cases.json | base on hybrid8 | 30 | 10 | 3 |
| compare-hybrid-saturated | ram-confirm-cases.json | base on hybrid8 | 60 | 10 | 3 |

```sh
python3 bench/syncrepwaker/analyze_compare.py \
  bench/syncrepwaker/hybrid-results-2026-10-23.json
```

## Expanded workload matrix

`run_matrix.py` runs nine workload families from `workload-cases.json`:
pgbench simple-update, TPC-B-like, read/write mixes 90/10 and 50/50, batch
INSERTs with 10/100/1000 rows, and 8/32 KiB INSERT payloads with TLS on both
client and replication connections. Payload compression is disabled with
STORAGE EXTERNAL. SQL generates the payload on the server; the client sends
small protocol messages and the resulting WAL carries the large values over
TLS. Batch INSERTs use one `INSERT ... SELECT
generate_series(...)` statement per transaction, into a table without indexes.
This suite uses persistent-disk data, one synchronous
standby, 128 clients, remote-flush commit, 4 GiB max_wal_size and 256 MiB
shared_buffers. All seven plain families initialize pgbench at scale 10;
the batch cases do not access those pgbench tables. The TLS families omit
pgbench initialization.

Each family is first calibrated with the parent binary for ten measured
seconds after three seconds of warmup. A fixed arrival rate of approximately
60% of that TPS is then used unchanged for all variants. Each family tests
that rate and unlimited load, with base/on/hybrid8 in rotating order and three
20-second measurement windows after five seconds of warmup: 162 main runs
plus nine calibration runs. Small transaction counts limit interpretation of
p99.9; keep the reported per-window counts visible.

Both clusters are stopped and restored from a common clean snapshot before
every calibration or main run. Only the copied cluster files are fsynced
before startup, outside the timed window. This resets pgbench history,
balances and update bloat. The harness checks that restored pgbench history
is empty. Per-script statistics retain read and write quantiles separately,
including scheduling lag and failures. Whole-process CPU cannot be attributed
to just the writer class and is reported only for the complete workload.

```sh
python3 bench/syncrepwaker/run_matrix.py \
  --baseline-bindir "$PWD/install-baseline/bin" \
  --feature-bindir "$PWD/install-release/bin" \
  --output "$PWD/compare-workloads" \
  --log-root /dev/shm/pgpg2-workloads-logs
```

Use new directories for the initial invocation. The state file and completed
phase outputs allow resuming the same command with `--resume`; a failed
phase gets a new attempt directory, retaining its earlier evidence. Runs are
sequential. Successful temporary clusters and their snapshots are removed,
while compressed raw logs, server logs, metadata and JSON rows remain.
Use `analyze_compare.py --by-script` to inspect writer latency in mixed
workloads without hiding it behind the more numerous reads.

Validation: four latency-accounting unit tests pass, including mixed-script
classification, plus six short integration runs across all three variants.
The integration runs checked empty restored history and separate read/write
counts before starting the full matrix.

After the matrix completes, collect its main rows and environment with:

```sh
python3 bench/syncrepwaker/collect_matrix.py compare-workloads \
  --baseline-commit dc9f4918121638e93b8813cc411247e2dbdb3b10 \
  --feature-commit 73b816456c0061ed747424c6339eb52bcb164428 \
  --harness-commit 35a02718145bad1a0c1bf7d0b70e44df9b839c77
```

The collector verifies row counts, binary hashes, transaction accounting and
snapshot restoration before writing `workload-results-<date>.json` and
`workload-environment-<date>.json`. It also counts checkpoint/restartpoint log
events within each measured window. Those event counts do not measure how
long an ongoing checkpoint overlaps the window. Original per-transaction
logs remain in the phase directories on the benchmark host.

### Workload matrix results, 2026-10-23 UTC

All 162 main runs and nine calibrations completed on the VM. The main windows
contain 40,460,989 transactions without failed/skipped transactions or missing
CPU snapshots. Successful clusters and snapshots were removed; raw logs remain
on the host. Four accounting unit tests and six integration smoke runs also
passed before the full matrix.

The persistent-disk results do not establish a general improvement. At unlimited
load, hybrid8 reduces simple-update p99 by 18.3% with approximately unchanged
TPS, but batch10 TPS falls 7.8% and batch1000 TPS falls 7.3%. Full delegation
loses 15.2% TPS on batch10 while gaining 5.4% on batch100. Transaction p50 does
not improve consistently. Sender CPU decreases, while total process CPU is
usually close to the baseline. The fixed 32 KiB TLS case accumulates a backlog
in every variant and has large run-to-run tail variability.

See [the full report](workload-report-2026-10-23.md) for both load modes,
separate read/write metrics, per-run p99 ranges, counts, execution latency,
scheduling lag and CPU/WAL measurements. [Main results](workload-results-2026-10-23.json)
and [environment/calibration data](workload-environment-2026-10-23.json)
preserve the measured rows and configurations.
