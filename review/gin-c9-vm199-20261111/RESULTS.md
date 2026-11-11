# GIN C9: independent VM199 measurements

The unchanged C9 prototype was measured on the new AMD EPYC Genoa VM,
51.250.5.199, entirely under `/home/reshke/wpgpg/c9-199-1111`.
This is a new host replication of the published R3 protocol, not a new
optimization or a current-master result. All 25 full SQL cases and the
separate 12-SQL/four-real-AM screen completed without timing-dependent repeats.

Raw B72: 72b9498df9a369e747f8d96efb5a6cd33c2451e2; common baseline:
8a8c475037bfde101da23cc9b0364c9c020eca93; C9:
0ab3bd65c8957ea5e25f9ef8981401f0616d99de; Lazy V4:
aee770c6ed58bf352fd3c086418b6c0dda93ae42. T is the exact B executable.

## Full SQL, both cohorts

Executor columns are absolute medians in milliseconds per supplied SQL
statement. Several cases batch 100 rescans; these are not single-lookup
latencies. Percentage columns are medians of 12 same-round paired changes,
not ratios of displayed medians. Negative means less time. Cohorts are kept
separate. Every min/max, mean, SD, MAD, raw value and pair remains in
[the full tables](analysis-r1/BENCHMARKS.md), CSV and evidence JSONL.

| Case | B executor ms (0 / 1) | C9 executor ms (0 / 1) | C9/B executor % | C9/B CPU % | C9/T CPU % | C9/L4 CPU % |
|---|---:|---:|---:|---:|---:|---:|
| skew1000 | 76.4580 / 78.8500 | 19.2960 / 19.8125 | -74.77 / -74.88 | -74.54 / -74.64 | -74.53 / -74.64 | -29.78 / -29.87 |
| skew127 | 135.8125 / 138.9505 | 100.0125 / 102.2220 | -26.33 / -26.53 | -26.27 / -26.47 | -26.46 / -26.48 | -26.87 / -26.91 |
| skew17 | 93.0610 / 94.7275 | 85.2030 / 86.8395 | -8.48 / -8.39 | -8.42 / -8.37 | -8.94 / -8.54 | -9.36 / -10.02 |
| separate_keys | 76.2870 / 79.3195 | 20.3250 / 20.9915 | -73.37 / -73.56 | -73.14 / -73.33 | -73.10 / -73.37 | -30.80 / -30.43 |
| dense_and | 78.0975 / 79.2310 | 76.1065 / 77.1330 | -2.56 / -2.63 | -2.53 / -2.64 | -3.72 / -2.81 | -3.10 / -4.37 |
| or_forced | 134.2855 / 135.3925 | 166.6490 / 133.0470 | +23.37 / -1.82 | +23.23 / -1.85 | +19.08 / -2.75 | +21.81 / -4.45 |
| single_forced | 127.2590 / 125.5255 | 153.8465 / 124.9900 | +20.89 / -1.19 | +20.82 / -1.20 | +16.69 / -2.53 | +20.56 / -4.41 |
| single_rare | 5.9505 / 5.9035 | 6.3795 / 5.8935 | +7.23 / -0.16 | +7.29 / +0.09 | +5.98 / -0.30 | +7.44 / -1.88 |
| inline | 0.4610 / 0.4435 | 0.4100 / 0.4040 | -8.75 / -7.72 | -6.02 / -3.06 | -6.54 / -5.63 | -8.30 / -7.68 |
| prefix | 91.4315 / 93.0445 | 91.6205 / 91.4485 | +0.15 / -1.71 | +0.17 / -1.69 | +0.03 / -0.19 | -0.14 / +0.51 |
| phrase | 76.5250 / 77.3150 | 19.9750 / 19.7700 | -74.03 / -74.42 | -73.80 / -74.20 | -73.58 / -74.19 | -27.91 / -29.16 |
| not | 36.8765 / 37.1440 | 11.3810 / 11.3985 | -69.12 / -69.32 | -68.73 / -68.91 | -68.69 / -68.89 | -40.57 / -40.77 |
| intarray | 75.6160 / 76.4395 | 18.8185 / 18.7550 | -75.13 / -75.49 | -74.97 / -75.26 | -75.00 / -75.31 | -30.40 / -30.97 |
| builtin_array | 74.9065 / 75.2905 | 18.1105 / 17.9965 | -75.86 / -76.08 | -75.64 / -75.85 | -75.67 / -75.91 | -32.49 / -32.81 |
| jsonb | 153.4335 / 149.5210 | 35.6850 / 35.4315 | -76.74 / -76.30 | -76.59 / -76.18 | -76.60 / -76.18 | -33.01 / -31.96 |
| lossy_and | 227.9485 / 118.2320 | 224.4065 / 118.7955 | -1.33 / +0.52 | -1.36 / +0.53 | -1.54 / -1.80 | -1.05 / -1.74 |
| seq_control | 55.3985 / 38.0925 | 55.6480 / 38.3245 | +6.96 / +0.62 | +6.87 / +0.55 | -3.32 / -4.72 | +1.91 / -8.50 |
| phrase_positive | 47.9830 / 44.2060 | 25.3710 / 18.4435 | -56.26 / -58.30 | -55.79 / -57.99 | -55.54 / -57.94 | -28.77 / -29.92 |
| not_positive | 40.5330 / 39.8800 | 14.1710 / 14.0690 | -65.03 / -64.71 | -64.66 / -64.36 | -64.64 / -64.30 | -35.45 / -35.80 |
| skew_group4096 | 57.6345 / 57.1160 | 6.3540 / 6.4060 | -89.00 / -88.78 | -88.65 / -88.46 | -88.64 / -88.47 | -39.94 / -39.70 |
| array_dense | 1516.3570 / 1476.8990 | 1426.1475 / 1428.3475 | -5.17 / -3.21 | -5.17 / -3.21 | -5.42 / -3.75 | -3.86 / -4.57 |
| inline_single | 2.8405 / 2.8110 | 2.7785 / 2.7980 | -2.21 / -0.32 | -1.59 / -0.33 | -2.54 / -0.34 | -1.02 / -2.78 |
| absent | 1.2655 / 1.1960 | 0.2980 / 0.3230 | -76.34 / -73.04 | -66.17 / -63.24 | -66.17 / -63.35 | -65.98 / -64.83 |
| not_only | 151.4890 / 151.1255 | 153.0165 / 149.5255 | +0.76 / -1.29 | +0.74 / -1.31 | -1.32 / -0.81 | -0.57 / -2.71 |
| empty_array | 156.1600 / 154.7685 | 153.9450 / 153.5580 | -1.20 / -1.13 | -1.20 / -1.13 | -4.28 / -2.20 | -0.58 / -2.65 |

## Negative/control observations

Cases with a positive CPU median versus B or its exact twin in at least one cohort: `or_forced`, `single_forced`, `single_rare`, `prefix`, `lossy_and`, `seq_control`, `not_only`. These observations are retained, not normalized away.

- cohort 0, or_forced: T/B +3.15%, C9/B +23.23%, C9/T +19.08%
- cohort 0, dense_and: T/B +1.10%, C9/B -2.53%, C9/T -3.72%
- cohort 0, single_forced: T/B +3.24%, C9/B +20.82%, C9/T +16.69%
- cohort 0, seq_control: T/B +9.18%, C9/B +6.87%, C9/T -3.32%
- cohort 1, or_forced: T/B +1.16%, C9/B -1.85%, C9/T -2.75%
- cohort 1, dense_and: T/B +0.15%, C9/B -2.64%, C9/T -2.81%
- cohort 1, single_forced: T/B +1.39%, C9/B -1.20%, C9/T -2.53%
- cohort 1, seq_control: T/B +6.15%, C9/B +0.55%, C9/T -4.72%

SeqScan does not exercise the intended GIN optimization. Its movement
and exact-twin differences limit attribution of small effects; they do not
establish a cause or justify removing negative observations. No universal
absence of regressions, merge readiness or statistical significance is claimed.

## Actual-AM screen

Internal process CPU per fixed batch: 10000 inline, 5000 absent, 100 skew,
10 full scans. These call the real rescan/getbitmap/free path, excluding
relation open/scan construction and JSON return. They are separate from SQL.

| Real-AM batch | B CPU ms (0 / 1) | C9 CPU ms (0 / 1) | C9/B CPU % |
|---|---:|---:|---:|
| am_inline | 18.3154 / 17.9692 | 14.9841 / 14.6572 | -18.16 / -18.40 |
| am_absent | 55.5334 / 54.7287 | 7.0967 / 6.9331 | -87.22 / -87.26 |
| am_skew1000 | 71.3478 / 71.9487 | 13.2520 / 13.0759 | -81.54 / -81.85 |
| am_full | 98.3094 / 98.2289 | 94.9385 / 93.7304 | -3.41 / -3.73 |

## Previous host, kept separate

| Case | Previous VM158 C9/B CPU % | New VM199 C9/B CPU % |
|---|---:|---:|
| skew1000 | -72.94 / -74.20 | -74.54 / -74.64 |
| jsonb | -76.29 / -76.36 | -76.59 / -76.18 |
| intarray | -74.95 / -75.72 | -74.97 / -75.26 |
| builtin_array | -73.42 / -75.85 | -75.64 / -75.85 |
| skew_group4096 | -88.21 / -87.69 | -88.65 / -88.46 |
| phrase_positive | -60.04 / -57.34 | -55.79 / -57.99 |
| inline | +1.79 / -4.94 | -6.02 / -3.06 |
| absent | -66.99 / -62.97 | -66.17 / -63.24 |
| or_forced | +10.73 / +1.75 | +23.23 / -1.85 |
| single_rare | +3.49 / +2.34 | +7.29 / +0.09 |
| dense_and | +7.75 / -2.53 | -2.53 / -2.64 |
| seq_control | -5.42 / -0.29 | +6.87 / +0.55 |

The earlier observations come from the frozen 2026-11-10 packet. They
are not pooled with this host. Source and workload are unchanged; absolute
host speed differences are not attributed to the candidate.

## Completed checks and scope

- Six builds, original core239 each, including C9 with assertions.
- Both campaigns' ordered Seq/GIN, prepared/cached-rescan, literal/path and
  AM-answer checks passed; original expected/input files stayed unchanged.
- Screen: 2688 raw / 2304 retained / 384 warm. Full SQL: 2800 raw /
  2400 retained / 400 warm. Every retained SQL root has zero shared reads.
- Independent recount: 5488 raw observations, 1224 absolute groups and
  2460 pair groups matched the original analyzer within the stated floating
  tolerance. CPU deltas are checked as recorded, not re-derived from
  unrecorded endpoints.
- Final reread verified source/install/seed identities, all 34 owned cluster
  shutdowns and 20 measured backend PIDs absent. No owned executable remained.

GCC 13.3, -O2 -g -fno-lto, OpenSSL, no ICU/readline; release timings, 512 MB
shared buffers, JIT/parallel/memoize/autovacuum off, system clock. Two fixed
warm-cache cohorts swap CPU0/4, slot/session order and case order. CREATE INDEX
is setup, not a measured target. No profiling run is mixed into these timings.

Host sampler: 281 samples, maximum gap 5.03s; load1 1.00..6.41; aggregate reported steal 0.0389%. This sampling includes preparation and cannot prove isolation or detect all short activity.

[Reproduction](REPRODUCE.md) includes exact inputs, commands and timing
boundaries. [Source diff](patches/gin-lazy-adaptive-v9-over-fixed-b72.diff)
applies to the stated common baseline. [Earlier discussion](PRIOR-ART-CARRIED-FORWARD.md)
is carried forward from the previous bounded review; no fresh exhaustive
novelty search was performed. The contribution here is independent host
measurement and preservation of both gains and negative results.
