# Synchronous replication waker: expanded workload matrix

The persistent-disk matrix on this VM does not establish a general performance
win for delegated wakeups. Sender CPU decreases, but throughput and latency
can worsen. Direct limit 8 does not consistently improve transaction p50.
The earlier large tail gain on tiny tmpfs INSERTs remains specific to that
experiment; these disk workloads do not reproduce it across the board.

All 162 main runs and nine calibrations completed, covering 40,460,989 measured
main-run transactions without failed/skipped transactions or missing CPU
snapshots. There were no failed attempts. The matrix took about 124 minutes.
No checkpoint/restartpoint starts or completions were logged inside the main
measurement windows. Temporary clusters and snapshots were removed.
Dates in the artifact filenames use the matrix's UTC start date, 2026-10-23.

The main observations, using medians of three repeats, are:

- At unlimited load, simple-update (pgbench -N) p99 falls from 34.778 ms to
  30.710 ms with full delegation and 28.413 ms with hybrid8. Hybrid8 improves
  p99 by 18.3% while its p50 rises from 8.803 to 8.992 ms. TPS is essentially
  unchanged. The p99 ranges overlap.
- Batch10 loses throughput in every repeat: baseline 17,122–18,329 TPS,
  full delegation 14,432–16,010, hybrid8 16,611–16,989. Median losses are
  15.2% and 7.8%; hybrid8 p99 rises 22.7%. Batch1000 median TPS also falls,
  by 6.6% with full delegation and 7.3% with hybrid8.
- Batch100 moves in the other direction for full delegation: median TPS
  rises 5.4% and p50 falls 5.6%. Hybrid8 has approximately baseline TPS and
  p50. These cases do not establish a useful universal batch-size rule.
- TPC-B-like and the saturated mixed workloads show small or noisy changes.
  At the fixed mixed90 rate, hybrid8 writer p99 falls from 45.765 to
  41.030 ms, while read p99 falls from 22.013 to 16.785 ms. At the fixed
  mixed50 rate, writer p99 instead rises from 46.115 to 53.094 ms. Read
  and write metrics are kept separate in the detailed table below.
- TLS 8 KiB has no clear saturated gain. TLS 32 KiB with hybrid8 reduces
  median p50 from 56.435 to 51.836 ms, with nearly identical p99 and broadly
  overlapping p99 ranges. Full delegation reduces that case's median p99
  from 592.803 to 553.048 ms; its ranges also overlap the baseline.
- Fixed TLS 32 KiB at 1100 offered TPS accumulates a backlog in all variants.
  Median achieved TPS is only 1032–1035 and response p99 is about 2.6 seconds,
  with baseline per-run p99 ranging from 235 ms to 2.7 seconds. Median
  scheduling-lag p99 is about 2.5 seconds. Treat this case as a backlog
  measurement; its small differences between variants do not establish
  improved wakeup latency. Execution p99, computed per transaction before
  taking quantiles, is 586 / 671 / 708 ms for base / on / hybrid8.
- Sender CPU savings do not translate directly into lower total CPU. For
  unlimited simple-update, sender CPU is 7.74 / 2.84 / 2.89 us per transaction,
  while total primary+standby+client CPU is 406.91 / 408.24 / 406.99 us.

These are short repeated windows on one shared VM with both servers and the
client on the same volume. They support keeping this as a workload-specific
experiment. The data does not establish a general improvement or an optimal
direct threshold. No server algorithm or default was changed during this matrix.

Here, base uses parent dc9f4918121; on and hybrid8 share the feature binary at
73b816456c0 with direct limits 0 and 8 respectively. All configurations use
synchronous commit with remote flush. Full methodology follows the comparison.

## Main comparisons

Each cell lists base / on / hybrid8. TPS counts transactions, including all
scripts in mixed workloads; p50 and p99 describe the writer class only.
Latency values are milliseconds. For batches, one transaction inserts the
named number of rows. Fixed-rate response quantiles include scheduling lag.

### Unlimited offered load

| Workload | Offered TPS | Achieved TPS | Write p50 ms | Write p99 ms |
| --- | ---: | --- | --- | --- |
| simple-update | unlimited | 12,465 / 12,399 / 12,475 | 8.803 / 8.953 / 8.992 | 34.778 / 30.710 / 28.413 |
| tpcb | unlimited | 1,423 / 1,403 / 1,412 | 43.352 / 45.347 / 43.506 | 612.503 / 599.082 / 639.302 |
| mixed90 | unlimited | 76,492 / 75,524 / 76,022 | 9.569 / 9.983 / 9.846 | 33.132 / 36.038 / 31.472 |
| mixed50 | unlimited | 23,264 / 23,217 / 23,286 | 8.769 / 8.675 / 8.573 | 34.735 / 32.651 / 34.742 |
| batch10 | unlimited | 18,170 / 15,410 / 16,752 | 5.921 / 6.842 / 6.264 | 23.321 / 32.603 / 28.607 |
| batch100 | unlimited | 7,038 / 7,420 / 7,079 | 14.417 / 13.603 / 14.491 | 87.186 / 85.172 / 89.944 |
| batch1000 | unlimited | 1,079 / 1,008 / 1,001 | 79.117 / 83.845 / 87.434 | 792.530 / 839.635 / 842.476 |
| insert8k-tls | unlimited | 4,254 / 4,234 / 4,170 | 21.145 / 20.680 / 20.732 | 144.197 / 145.325 / 148.227 |
| insert32k-tls | unlimited | 1,430 / 1,417 / 1,454 | 56.435 / 56.379 / 51.836 | 592.803 / 553.048 / 592.733 |

### Fixed offered load

| Workload | Offered TPS | Achieved TPS | Write p50 ms | Write p99 ms |
| --- | ---: | --- | --- | --- |
| simple-update | 7000 | 6,978 / 6,948 / 6,974 | 7.357 / 6.621 / 6.675 | 103.032 / 75.328 / 76.068 |
| tpcb | 720 | 723 / 722 / 723 | 8.033 / 8.177 / 7.759 | 116.961 / 101.153 / 64.024 |
| mixed90 | 41700 | 41,646 / 41,647 / 41,648 | 7.929 / 7.235 / 7.141 | 45.765 / 47.186 / 41.030 |
| mixed50 | 13100 | 13,068 / 13,075 / 13,078 | 6.727 / 6.443 / 6.777 | 46.115 / 63.149 / 53.094 |
| batch10 | 10200 | 10,177 / 10,188 / 10,179 | 7.018 / 6.287 / 6.341 | 91.698 / 94.643 / 101.818 |
| batch100 | 3700 | 3,696 / 3,697 / 3,690 | 6.823 / 6.418 / 6.985 | 76.806 / 81.522 / 99.348 |
| batch1000 | 760 | 763 / 763 / 762 | 11.165 / 11.666 / 10.841 | 108.513 / 113.074 / 111.816 |
| insert8k-tls | 3000 | 2,989 / 2,984 / 2,977 | 8.528 / 8.364 / 8.861 | 95.296 / 97.860 / 112.673 |
| insert32k-tls | 1100 | 1,035 / 1,032 / 1,035 | 19.346 / 22.455 / 21.944 | 2626.944 / 2602.029 / 2562.379 |

## Changes relative to baseline

Percent change = 100 × (variant median / baseline median − 1), calculated
from unrounded medians of the same three repeats. Positive TPS is better;
negative latency is better. These deltas do not account for run-to-run
variability; the p99 ranges remain in the detailed table below.

TPS covers the whole workload, including reads in mixed cases. The latency
columns below describe writes. Baseline rows have zero change by definition.

### Unlimited offered load

| Workload | Offered TPS | Variant | Achieved TPS | Δ TPS | Write p50 ms | Δ p50 | Write p99 ms | Δ p99 | Write p99.9 ms | Δ p99.9 |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| simple-update | unlimited | base | 12,465 | 0.0% | 8.803 | 0.0% | 34.778 | 0.0% | 80.672 | 0.0% |
| simple-update | unlimited | on | 12,399 | -0.5% | 8.953 | +1.7% | 30.710 | -11.7% | 82.597 | +2.4% |
| simple-update | unlimited | hybrid8 | 12,475 | +0.1% | 8.992 | +2.1% | 28.413 | -18.3% | 76.493 | -5.2% |
| tpcb | unlimited | base | 1,423 | 0.0% | 43.352 | 0.0% | 612.503 | 0.0% | 1116.887 | 0.0% |
| tpcb | unlimited | on | 1,403 | -1.4% | 45.347 | +4.6% | 599.082 | -2.2% | 1158.580 | +3.7% |
| tpcb | unlimited | hybrid8 | 1,412 | -0.8% | 43.506 | +0.4% | 639.302 | +4.4% | 1095.704 | -1.9% |
| mixed90 | unlimited | base | 76,492 | 0.0% | 9.569 | 0.0% | 33.132 | 0.0% | 75.247 | 0.0% |
| mixed90 | unlimited | on | 75,524 | -1.3% | 9.983 | +4.3% | 36.038 | +8.8% | 75.667 | +0.6% |
| mixed90 | unlimited | hybrid8 | 76,022 | -0.6% | 9.846 | +2.9% | 31.472 | -5.0% | 72.419 | -3.8% |
| mixed50 | unlimited | base | 23,264 | 0.0% | 8.769 | 0.0% | 34.735 | 0.0% | 72.743 | 0.0% |
| mixed50 | unlimited | on | 23,217 | -0.2% | 8.675 | -1.1% | 32.651 | -6.0% | 73.716 | +1.3% |
| mixed50 | unlimited | hybrid8 | 23,286 | +0.1% | 8.573 | -2.2% | 34.742 | 0.0% | 71.270 | -2.0% |
| batch10 | unlimited | base | 18,170 | 0.0% | 5.921 | 0.0% | 23.321 | 0.0% | 65.828 | 0.0% |
| batch10 | unlimited | on | 15,410 | -15.2% | 6.842 | +15.6% | 32.603 | +39.8% | 67.766 | +2.9% |
| batch10 | unlimited | hybrid8 | 16,752 | -7.8% | 6.264 | +5.8% | 28.607 | +22.7% | 69.962 | +6.3% |
| batch100 | unlimited | base | 7,038 | 0.0% | 14.417 | 0.0% | 87.186 | 0.0% | 107.297 | 0.0% |
| batch100 | unlimited | on | 7,420 | +5.4% | 13.603 | -5.6% | 85.172 | -2.3% | 109.523 | +2.1% |
| batch100 | unlimited | hybrid8 | 7,079 | +0.6% | 14.491 | +0.5% | 89.944 | +3.2% | 116.665 | +8.7% |
| batch1000 | unlimited | base | 1,079 | 0.0% | 79.117 | 0.0% | 792.530 | 0.0% | 984.642 | 0.0% |
| batch1000 | unlimited | on | 1,008 | -6.6% | 83.845 | +6.0% | 839.635 | +5.9% | 959.665 | -2.5% |
| batch1000 | unlimited | hybrid8 | 1,001 | -7.3% | 87.434 | +10.5% | 842.476 | +6.3% | 920.202 | -6.5% |
| insert8k-tls | unlimited | base | 4,254 | 0.0% | 21.145 | 0.0% | 144.197 | 0.0% | 447.423 | 0.0% |
| insert8k-tls | unlimited | on | 4,234 | -0.5% | 20.680 | -2.2% | 145.325 | +0.8% | 615.585 | +37.6% |
| insert8k-tls | unlimited | hybrid8 | 4,170 | -2.0% | 20.732 | -2.0% | 148.227 | +2.8% | 421.182 | -5.9% |
| insert32k-tls | unlimited | base | 1,430 | 0.0% | 56.435 | 0.0% | 592.803 | 0.0% | 769.553 | 0.0% |
| insert32k-tls | unlimited | on | 1,417 | -0.9% | 56.379 | -0.1% | 553.048 | -6.7% | 705.179 | -8.4% |
| insert32k-tls | unlimited | hybrid8 | 1,454 | +1.7% | 51.836 | -8.1% | 592.733 | 0.0% | 749.775 | -2.6% |

### Fixed offered load

| Workload | Offered TPS | Variant | Achieved TPS | Δ TPS | Write p50 ms | Δ p50 | Write p99 ms | Δ p99 | Write p99.9 ms | Δ p99.9 |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| simple-update | 7000 | base | 6,978 | 0.0% | 7.357 | 0.0% | 103.032 | 0.0% | 122.316 | 0.0% |
| simple-update | 7000 | on | 6,948 | -0.4% | 6.621 | -10.0% | 75.328 | -26.9% | 125.112 | +2.3% |
| simple-update | 7000 | hybrid8 | 6,974 | -0.1% | 6.675 | -9.3% | 76.068 | -26.2% | 106.190 | -13.2% |
| tpcb | 720 | base | 723 | 0.0% | 8.033 | 0.0% | 116.961 | 0.0% | 351.437 | 0.0% |
| tpcb | 720 | on | 722 | -0.1% | 8.177 | +1.8% | 101.153 | -13.5% | 270.989 | -22.9% |
| tpcb | 720 | hybrid8 | 723 | -0.1% | 7.759 | -3.4% | 64.024 | -45.3% | 134.818 | -61.6% |
| mixed90 | 41700 | base | 41,646 | 0.0% | 7.929 | 0.0% | 45.765 | 0.0% | 84.708 | 0.0% |
| mixed90 | 41700 | on | 41,647 | 0.0% | 7.235 | -8.8% | 47.186 | +3.1% | 94.154 | +11.2% |
| mixed90 | 41700 | hybrid8 | 41,648 | 0.0% | 7.141 | -9.9% | 41.030 | -10.3% | 62.940 | -25.7% |
| mixed50 | 13100 | base | 13,068 | 0.0% | 6.727 | 0.0% | 46.115 | 0.0% | 71.878 | 0.0% |
| mixed50 | 13100 | on | 13,075 | +0.1% | 6.443 | -4.2% | 63.149 | +36.9% | 105.637 | +47.0% |
| mixed50 | 13100 | hybrid8 | 13,078 | +0.1% | 6.777 | +0.7% | 53.094 | +15.1% | 80.064 | +11.4% |
| batch10 | 10200 | base | 10,177 | 0.0% | 7.018 | 0.0% | 91.698 | 0.0% | 129.209 | 0.0% |
| batch10 | 10200 | on | 10,188 | +0.1% | 6.287 | -10.4% | 94.643 | +3.2% | 117.730 | -8.9% |
| batch10 | 10200 | hybrid8 | 10,179 | 0.0% | 6.341 | -9.6% | 101.818 | +11.0% | 142.777 | +10.5% |
| batch100 | 3700 | base | 3,696 | 0.0% | 6.823 | 0.0% | 76.806 | 0.0% | 92.008 | 0.0% |
| batch100 | 3700 | on | 3,697 | 0.0% | 6.418 | -5.9% | 81.522 | +6.1% | 100.803 | +9.6% |
| batch100 | 3700 | hybrid8 | 3,690 | -0.2% | 6.985 | +2.4% | 99.348 | +29.3% | 147.440 | +60.2% |
| batch1000 | 760 | base | 763 | 0.0% | 11.165 | 0.0% | 108.513 | 0.0% | 146.103 | 0.0% |
| batch1000 | 760 | on | 763 | 0.0% | 11.666 | +4.5% | 113.074 | +4.2% | 148.509 | +1.6% |
| batch1000 | 760 | hybrid8 | 762 | -0.2% | 10.841 | -2.9% | 111.816 | +3.0% | 156.874 | +7.4% |
| insert8k-tls | 3000 | base | 2,989 | 0.0% | 8.528 | 0.0% | 95.296 | 0.0% | 130.074 | 0.0% |
| insert8k-tls | 3000 | on | 2,984 | -0.2% | 8.364 | -1.9% | 97.860 | +2.7% | 127.950 | -1.6% |
| insert8k-tls | 3000 | hybrid8 | 2,977 | -0.4% | 8.861 | +3.9% | 112.673 | +18.2% | 150.323 | +15.6% |
| insert32k-tls | 1100 | base | 1,035 | 0.0% | 19.346 | 0.0% | 2626.944 | 0.0% | 2789.241 | 0.0% |
| insert32k-tls | 1100 | on | 1,032 | -0.3% | 22.455 | +16.1% | 2602.029 | -0.9% | 2697.250 | -3.3% |
| insert32k-tls | 1100 | hybrid8 | 1,035 | 0.0% | 21.944 | +13.4% | 2562.379 | -2.5% | 2727.494 | -2.2% |

### Read latency in mixed workloads

The following deltas use the read class only. Read-only latency includes
scheduling lag at fixed offered rates, as in the absolute metrics.

| Workload | Load | Variant | Read p50 ms | Δ p50 | Read p99 ms | Δ p99 | Read p99.9 ms | Δ p99.9 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| mixed90 | saturation | base | 0.363 | 0.0% | 2.457 | 0.0% | 3.987 | 0.0% |
| mixed90 | saturation | on | 0.354 | -2.5% | 2.421 | -1.5% | 3.935 | -1.3% |
| mixed90 | saturation | hybrid8 | 0.365 | +0.6% | 2.425 | -1.3% | 3.949 | -1.0% |
| mixed90 | fixed_rate | base | 0.248 | 0.0% | 22.013 | 0.0% | 60.974 | 0.0% |
| mixed90 | fixed_rate | on | 0.246 | -0.8% | 24.664 | +12.0% | 70.474 | +15.6% |
| mixed90 | fixed_rate | hybrid8 | 0.247 | -0.4% | 16.785 | -23.7% | 40.448 | -33.7% |
| mixed50 | saturation | base | 0.408 | 0.0% | 2.439 | 0.0% | 3.518 | 0.0% |
| mixed50 | saturation | on | 0.405 | -0.7% | 2.376 | -2.6% | 3.388 | -3.7% |
| mixed50 | saturation | hybrid8 | 0.411 | +0.7% | 2.399 | -1.6% | 3.515 | -0.1% |
| mixed50 | fixed_rate | base | 0.208 | 0.0% | 27.863 | 0.0% | 56.357 | 0.0% |
| mixed50 | fixed_rate | on | 0.206 | -1.0% | 45.590 | +63.6% | 90.373 | +60.4% |
| mixed50 | fixed_rate | hybrid8 | 0.206 | -1.0% | 35.462 | +27.3% | 61.785 | +9.6% |

The fixed 32 KiB TLS case accumulates a backlog in all variants. Its small
response-p99 percentage differences should be read alongside achieved TPS,
scheduling lag and the large per-run p99 ranges.

## Method

The comparison uses parent `dc9f4918121`, the waker/hybrid algorithm at
`73b816456c0`, and harness `35a02718145`. `base` uses the parent binary; `on`
and `hybrid8` share one feature binary and select direct limits 0 and 8.
Both builds use `-O2 -g -fno-omit-frame-pointer`, OpenSSL, and disabled
assertions. The standby and pgbench use the parent binaries for every variant.

Primary, synchronous standby and pgbench share one 8-vCPU AMD EPYC Genoa VM
with about 15 GiB RAM and one persistent storage volume. Data is on disk;
transaction logs are initially written to tmpfs and then compressed. CPUs
are not pinned and the host is not isolated. Storage media and independent
network/storage deployments were not tested.

All cases use 128 clients, eight pgbench threads, prepared queries and
`synchronous_commit=on` (remote flush). The configuration keeps fsync and
full-page writes enabled, uses 256 MiB shared buffers, 64 MiB WAL buffers,
4 GiB max WAL size, a 30-minute checkpoint timeout and disabled autovacuum.
One persistent physical replication slot retains WAL for the standby.

Each run restores both stopped clusters from common clean snapshots and
fsyncs the copied files before startup. All seven plain families include
pgbench scale-10 data; batch cases do not access those tables. TLS families
omit pgbench initialization. Each run with pgbench data starts with empty
history. Snapshots reset balances, history and update bloat; filesystem caches
and VM storage state are not reset.

Each of nine families has a baseline-only 10-second calibration, followed by
both unlimited load and a fixed arrival rate near 60% of its calibration TPS.
That fixed rate is identical for every variant. Main measurements last
20 seconds after five seconds of warmup, with three repeats. Variant order
rotates base/on/hybrid8, on/hybrid8/base, hybrid8/base/on. Runs are sequential.
An additional four seconds of client runtime permits the final CPU snapshot;
transactions outside the measured interval are excluded.
Only transactions completed inside the interval contribute to its quantiles;
transactions still running at the boundary are excluded.

The two TLS workloads encrypt both client connections and the replication
stream. SQL generates the 8/32 KiB INSERT values on the server, with TOAST
compression disabled using STORAGE EXTERNAL. The client sends small protocol
messages and the resulting WAL carries the large values over TLS. Batch
workloads execute one `INSERT ... SELECT generate_series(...)` per transaction, inserting
10/100/1000 empty-payload rows into a table without indexes.

Reported values are medians of three per-run metrics, not quantiles of a
pooled transaction distribution. Ranges show the smallest and largest per-run
p99. Mixed-workload latency is reported separately for writes and reads;
the main comparison uses writer latency and total workload TPS. Fixed-rate
response times include pgbench scheduling lag. Execution latency is computed
by subtracting that lag from each transaction before computing quantiles.
Three repeats establish neither statistical significance nor a universal
setting. Low transaction counts make p99.9 exploratory in the slower cases.

The result JSON retains per-run quantiles, execution times, scheduling lag,
per-script counts, five-second block statistics, CPU totals and checkpoint
events. A checkpoint log event within a measurement is an observation, not
proof that it caused a tail stall. A checkpoint may also start before the
window and continue within it.

## Run variability and transaction counts

Medians of per-window metrics; N/window is the median transaction count for
that class. The p99 range contains all three measured runs. Writer lag
and execution quantiles are computed from the same class as response latency.

| Workload / load | Variant | Class | N/window | p50 ms | p99 ms | p99 range ms | p99.9 ms | Execution p99 ms | Lag p99 ms |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| simple-update / saturation | base | write | 249,315 | 8.803 | 34.778 | 28.547–36.523 | 80.672 | 34.778 | 0.000 |
| simple-update / saturation | on | write | 247,989 | 8.953 | 30.710 | 28.455–31.196 | 82.597 | 30.710 | 0.000 |
| simple-update / saturation | hybrid8 | write | 249,502 | 8.992 | 28.413 | 26.736–28.960 | 76.493 | 28.413 | 0.000 |
| simple-update / fixed_rate | base | write | 139,558 | 7.357 | 103.032 | 56.519–1033.184 | 122.316 | 37.542 | 85.438 |
| simple-update / fixed_rate | on | write | 138,973 | 6.621 | 75.328 | 63.124–172.825 | 125.112 | 30.351 | 58.125 |
| simple-update / fixed_rate | hybrid8 | write | 139,477 | 6.675 | 76.068 | 72.817–81.414 | 106.190 | 31.859 | 58.629 |
| tpcb / saturation | base | write | 28,466 | 43.352 | 612.503 | 610.453–646.700 | 1116.887 | 612.503 | 0.000 |
| tpcb / saturation | on | write | 28,059 | 45.347 | 599.082 | 583.589–623.486 | 1158.580 | 599.082 | 0.000 |
| tpcb / saturation | hybrid8 | write | 28,236 | 43.506 | 639.302 | 617.450–657.256 | 1095.704 | 639.302 | 0.000 |
| tpcb / fixed_rate | base | write | 14,464 | 8.033 | 116.961 | 106.482–127.249 | 351.437 | 116.879 | 0.103 |
| tpcb / fixed_rate | on | write | 14,444 | 8.177 | 101.153 | 71.100–104.109 | 270.989 | 101.079 | 0.101 |
| tpcb / fixed_rate | hybrid8 | write | 14,452 | 7.759 | 64.024 | 63.049–135.979 | 134.818 | 63.943 | 0.099 |
| mixed90 / saturation | base | read | 1,376,647 | 0.363 | 2.457 | 2.428–2.484 | 3.987 | 2.457 | 0.000 |
| mixed90 / saturation | base | write | 153,192 | 9.569 | 33.132 | 29.104–33.837 | 75.247 | 33.132 | 0.000 |
| mixed90 / saturation | on | read | 1,359,307 | 0.354 | 2.421 | 2.395–2.458 | 3.935 | 2.421 | 0.000 |
| mixed90 / saturation | on | write | 151,197 | 9.983 | 36.038 | 32.689–36.524 | 75.667 | 36.038 | 0.000 |
| mixed90 / saturation | hybrid8 | read | 1,368,222 | 0.365 | 2.425 | 2.374–2.447 | 3.949 | 2.425 | 0.000 |
| mixed90 / saturation | hybrid8 | write | 152,226 | 9.846 | 31.472 | 30.796–41.014 | 72.419 | 31.472 | 0.000 |
| mixed90 / fixed_rate | base | read | 749,843 | 0.248 | 22.013 | 20.907–30.244 | 60.974 | 0.851 | 21.433 |
| mixed90 / fixed_rate | base | write | 83,279 | 7.929 | 45.765 | 44.721–55.813 | 84.708 | 37.487 | 21.134 |
| mixed90 / fixed_rate | on | read | 749,850 | 0.246 | 24.664 | 16.611–26.197 | 70.474 | 0.807 | 24.121 |
| mixed90 / fixed_rate | on | write | 83,241 | 7.235 | 47.186 | 42.123–52.065 | 94.154 | 35.000 | 23.937 |
| mixed90 / fixed_rate | hybrid8 | read | 749,894 | 0.247 | 16.785 | 15.768–19.610 | 40.448 | 0.863 | 16.307 |
| mixed90 / fixed_rate | hybrid8 | write | 83,237 | 7.141 | 41.030 | 40.586–44.601 | 62.940 | 36.209 | 16.590 |
| mixed50 / saturation | base | read | 232,850 | 0.408 | 2.439 | 2.326–2.567 | 3.518 | 2.439 | 0.000 |
| mixed50 / saturation | base | write | 232,440 | 8.769 | 34.735 | 29.357–41.032 | 72.743 | 34.735 | 0.000 |
| mixed50 / saturation | on | read | 232,535 | 0.405 | 2.376 | 2.333–2.397 | 3.388 | 2.376 | 0.000 |
| mixed50 / saturation | on | write | 231,814 | 8.675 | 32.651 | 28.310–37.335 | 73.716 | 32.651 | 0.000 |
| mixed50 / saturation | hybrid8 | read | 233,228 | 0.411 | 2.399 | 2.387–2.411 | 3.515 | 2.399 | 0.000 |
| mixed50 / saturation | hybrid8 | write | 232,497 | 8.573 | 34.742 | 26.077–37.238 | 71.270 | 34.742 | 0.000 |
| mixed50 / fixed_rate | base | read | 130,752 | 0.208 | 27.863 | 21.390–115.315 | 56.357 | 1.179 | 27.242 |
| mixed50 / fixed_rate | base | write | 130,645 | 6.727 | 46.115 | 38.045–136.418 | 71.878 | 28.766 | 26.911 |
| mixed50 / fixed_rate | on | read | 130,771 | 0.206 | 45.590 | 23.812–48.535 | 90.373 | 1.129 | 44.738 |
| mixed50 / fixed_rate | on | write | 130,640 | 6.443 | 63.149 | 41.437–64.960 | 105.637 | 26.899 | 44.568 |
| mixed50 / fixed_rate | hybrid8 | read | 130,799 | 0.206 | 35.462 | 25.622–50.293 | 61.785 | 1.208 | 34.819 |
| mixed50 / fixed_rate | hybrid8 | write | 130,770 | 6.777 | 53.094 | 42.405–67.428 | 80.064 | 29.983 | 34.491 |
| batch10 / saturation | base | write | 363,412 | 5.921 | 23.321 | 22.995–32.914 | 65.828 | 23.321 | 0.000 |
| batch10 / saturation | on | write | 308,204 | 6.842 | 32.603 | 31.809–34.340 | 67.766 | 32.603 | 0.000 |
| batch10 / saturation | hybrid8 | write | 335,035 | 6.264 | 28.607 | 25.312–30.524 | 69.962 | 28.607 | 0.000 |
| batch10 / fixed_rate | base | write | 203,546 | 7.018 | 91.698 | 83.139–158.908 | 129.209 | 29.298 | 79.102 |
| batch10 / fixed_rate | on | write | 203,767 | 6.287 | 94.643 | 83.259–153.467 | 117.730 | 30.441 | 82.250 |
| batch10 / fixed_rate | hybrid8 | write | 203,576 | 6.341 | 101.818 | 51.779–211.528 | 142.777 | 27.804 | 89.359 |
| batch100 / saturation | base | write | 140,768 | 14.417 | 87.186 | 86.819–94.784 | 107.297 | 87.186 | 0.000 |
| batch100 / saturation | on | write | 148,402 | 13.603 | 85.172 | 83.136–87.909 | 109.523 | 85.172 | 0.000 |
| batch100 / saturation | hybrid8 | write | 141,584 | 14.491 | 89.944 | 84.320–96.942 | 116.665 | 89.944 | 0.000 |
| batch100 / fixed_rate | base | write | 73,914 | 6.823 | 76.806 | 73.210–90.081 | 92.008 | 73.100 | 43.732 |
| batch100 / fixed_rate | on | write | 73,932 | 6.418 | 81.522 | 73.446–94.298 | 100.803 | 77.047 | 48.415 |
| batch100 / fixed_rate | hybrid8 | write | 73,800 | 6.985 | 99.348 | 85.272–105.840 | 147.440 | 77.726 | 59.230 |
| batch1000 / saturation | base | write | 21,590 | 79.117 | 792.530 | 724.137–879.346 | 984.642 | 792.530 | 0.000 |
| batch1000 / saturation | on | write | 20,157 | 83.845 | 839.635 | 800.855–912.819 | 959.665 | 839.635 | 0.000 |
| batch1000 / saturation | hybrid8 | write | 20,013 | 87.434 | 842.476 | 828.858–851.798 | 920.202 | 842.476 | 0.000 |
| batch1000 / fixed_rate | base | write | 15,258 | 11.165 | 108.513 | 107.914–114.954 | 146.103 | 108.437 | 0.108 |
| batch1000 / fixed_rate | on | write | 15,262 | 11.666 | 113.074 | 105.731–115.355 | 148.509 | 112.997 | 0.108 |
| batch1000 / fixed_rate | hybrid8 | write | 15,235 | 10.841 | 111.816 | 101.450–125.064 | 156.874 | 111.739 | 0.110 |
| insert8k-tls / saturation | base | write | 85,073 | 21.145 | 144.197 | 132.909–165.744 | 447.423 | 144.197 | 0.000 |
| insert8k-tls / saturation | on | write | 84,671 | 20.680 | 145.325 | 135.540–149.876 | 615.585 | 145.325 | 0.000 |
| insert8k-tls / saturation | hybrid8 | write | 83,394 | 20.732 | 148.227 | 148.103–152.111 | 421.182 | 148.227 | 0.000 |
| insert8k-tls / fixed_rate | base | write | 59,771 | 8.528 | 95.296 | 87.680–120.677 | 130.074 | 88.403 | 55.546 |
| insert8k-tls / fixed_rate | on | write | 59,681 | 8.364 | 97.860 | 93.822–103.247 | 127.950 | 88.626 | 57.019 |
| insert8k-tls / fixed_rate | hybrid8 | write | 59,538 | 8.861 | 112.673 | 103.977–117.135 | 150.323 | 94.222 | 70.671 |
| insert32k-tls / saturation | base | write | 28,600 | 56.435 | 592.803 | 531.705–599.697 | 769.553 | 592.803 | 0.000 |
| insert32k-tls / saturation | on | write | 28,340 | 56.379 | 553.048 | 545.808–568.986 | 705.179 | 553.048 | 0.000 |
| insert32k-tls / saturation | hybrid8 | write | 29,085 | 51.836 | 592.733 | 542.049–613.315 | 749.775 | 592.733 | 0.000 |
| insert32k-tls / fixed_rate | base | write | 20,703 | 19.346 | 2626.944 | 234.760–2705.374 | 2789.241 | 585.518 | 2513.998 |
| insert32k-tls / fixed_rate | on | write | 20,643 | 22.455 | 2602.029 | 1426.161–2607.762 | 2697.250 | 670.573 | 2474.301 |
| insert32k-tls / fixed_rate | hybrid8 | write | 20,697 | 21.944 | 2562.379 | 2498.436–2632.865 | 2727.494 | 707.788 | 2446.129 |

## CPU and WAL at unlimited offered load

Each cell lists base / on / hybrid8. Process CPU includes the primary,
standby and client, divided by total workload transactions. Host iowait is
a VM-wide observation, not attribution to an individual PostgreSQL process.

| Workload | Process CPU us/tx | Sender CPU us/tx | VM iowait % | WAL MiB/s |
| --- | --- | --- | --- | --- |
| simple-update | 406.91 / 408.24 / 406.99 | 7.74 / 2.84 / 2.89 | 12.46 / 12.82 / 12.59 | 3.57 / 3.51 / 3.60 |
| tpcb | 1217.32 / 1223.99 / 1161.28 | 37.59 / 33.16 / 37.19 | 15.33 / 15.21 / 15.65 | 4.27 / 4.24 / 4.16 |
| mixed90 | 95.09 / 95.58 / 95.47 | 0.87 / 0.38 / 0.43 | 1.74 / 1.79 / 1.77 | 2.97 / 2.89 / 2.98 |
| mixed50 | 237.77 / 237.23 / 237.21 | 3.87 / 1.46 / 1.50 | 5.97 / 6.05 / 5.74 | 3.55 / 3.36 / 3.37 |
| batch10 | 160.38 / 160.93 / 160.46 | 7.61 / 2.70 / 2.80 | 12.82 / 13.55 / 12.91 | 10.47 / 8.86 / 9.64 |
| batch100 | 394.60 / 393.26 / 393.90 | 10.02 / 4.68 / 4.83 | 10.47 / 10.14 / 10.49 | 38.13 / 40.25 / 38.35 |
| batch1000 | 2299.17 / 2316.51 / 2291.44 | 31.09 / 23.49 / 24.80 | 13.53 / 14.72 / 14.65 | 58.24 / 54.37 / 54.26 |
| insert8k-tls | 439.15 / 432.50 / 435.52 | 18.57 / 13.05 / 12.87 | 16.09 / 16.27 / 16.78 | 36.71 / 36.51 / 36.18 |
| insert32k-tls | 988.65 / 971.45 / 984.00 | 42.28 / 37.40 / 37.13 | 19.29 / 18.40 / 18.59 | 48.75 / 48.28 / 49.48 |

## Artifacts and validation

All 162 main runs completed, covering 40,460,989 measured transactions,
plus nine calibration runs. There were no failed or skipped transactions
and no missing process CPU snapshots in the measured windows. The collector
verified counts, binary hashes, clock consistency and restored history.

- [Main per-run results](workload-results-2026-10-23.json)
- [Environment, configurations and calibration results](workload-environment-2026-10-23.json)
- [Harness and reproduction instructions](README.md#expanded-workload-matrix)

Raw gzip transaction logs, per-run JSON, pgbench output and server logs remain
under /home/reshke/pgpg2/compare-workloads on the VM. Successful temporary
clusters and their snapshots were stopped and removed.
