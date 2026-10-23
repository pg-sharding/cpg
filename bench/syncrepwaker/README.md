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
