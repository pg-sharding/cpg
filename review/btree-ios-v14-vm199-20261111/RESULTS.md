# B-tree IOS V14 on the new VM199

Fresh measurements of unchanged V13/V14 alternatives on AMD EPYC Genoa,
8 vCPUs, 64 GB RAM, Linux/GCC 13.3. All remote work is under
`/home/reshke/wpgpg/ios14-199-1111`, after GIN C9 finished. This is an
independent VM repeat, with no patch tuning or timing-dependent repeats.

Wide-key SQL gains repeat: execution time falls by 17–22% for the eight-key
cases, 35% for the fixed-width 32-key case and 49–50% for the wide 32-key
tail query. Most of this is already present in V13. V14 versus V13 changes
CPU medians by only -0.04% to -3.00% across these four cases/cohorts.

LIMIT remains a regression: V14/B execution is +3.28% / +2.09% for LIMIT 1
and +2.43% / +3.90% for LIMIT 2. The backward short-posting case is
+2.09% / +0.88%; every one of its 24 execution-time pairs is slower than B
and than the exact baseline twin. V14 does not finish the regression repair.

Baseline: 72b9498df9a369e747f8d96efb5a6cd33c2451e2. V14 exact source:
113e61347b43d2ae4afb187944ede9e9f6108c24. Historical SOURCE manifests keep
their null V13/V14 commit fields; new V14 byte identity is recorded separately.
T uses the exact baseline installation and executable. V13 is essential for
distinguishing the inherited posting-cache effect from the V14 eligibility gate.

## All 19 SQL cases

Absolute executor medians are milliseconds for the supplied statement;
LIMIT cases batch 20000 parameterized scans. Percentages are medians of
12 same-round paired changes, not ratios of displayed medians. Negative
means less time. Cohorts 0 / 1 stay separate. Complete absolute ranges,
means, SD, MAD, all five metrics and all six pairs are in
[BENCHMARKS.md](analysis-r1/BENCHMARKS.md), CSV, raw JSONL and all-statistics.json.

| Case | B executor ms (0 / 1) | V14 executor ms (0 / 1) | V14/B executor % | V14/B CPU % | V14/T CPU % | V14/V13 CPU % |
|---|---:|---:|---:|---:|---:|---:|
| f2_p2_count | 59.938 / 51.215 | 64.171 / 50.335 | -0.64 / -1.69 | -0.62 / -1.62 | -2.09 / +0.09 | +1.78 / -0.11 |
| f3_p2_count | 52.500 / 52.424 | 51.865 / 51.947 | -0.56 / -0.92 | -0.49 / -0.88 | -2.31 / +1.08 | +0.44 / +0.62 |
| f4_p2_count | 53.535 / 53.439 | 53.091 / 52.013 | -1.73 / -2.68 | -1.66 / -2.64 | -3.47 / -0.70 | -0.07 / -0.31 |
| limit1_from_long | 28.165 / 27.239 | 28.981 / 27.778 | +3.28 / +2.09 | +3.40 / +2.18 | +4.08 / +2.96 | +3.05 / -0.02 |
| limit2_from_long | 52.194 / 28.603 | 53.793 / 29.489 | +2.43 / +3.90 | +2.46 / +4.11 | +2.40 / +4.50 | +2.47 / +2.25 |
| heap_f4_count | 154.146 / 145.781 | 141.179 / 141.237 | -8.58 / -3.11 | -8.57 / -3.10 | -4.88 / -1.58 | -0.21 / +2.27 |
| w8_long_count | 64.636 / 60.228 | 50.166 / 49.240 | -22.08 / -18.18 | -22.00 / -18.11 | -17.59 / -16.30 | -0.70 / -0.14 |
| w8_long_tail | 64.233 / 63.538 | 53.778 / 52.897 | -16.75 / -16.73 | -16.66 / -16.62 | -18.29 / -15.20 | -0.84 / -0.04 |
| f32_long_count | 15.840 / 14.992 | 10.262 / 9.709 | -34.76 / -35.27 | -34.17 / -34.76 | -36.74 / -33.94 | -0.90 / -3.00 |
| w32_long_tail | 23.245 / 23.231 | 12.018 / 11.735 | -48.81 / -49.58 | -48.39 / -49.13 | -49.44 / -48.11 | -1.61 / -1.77 |
| one_bigint_long_count | 78.020 / 47.293 | 78.132 / 46.634 | +0.18 / -1.37 | +0.21 / -1.32 | +0.01 / +0.89 | +0.26 / +0.20 |
| one_bigint_singleton_count | 58.343 / 58.586 | 60.894 / 57.148 | +3.80 / -2.42 | +3.79 / -2.39 | +2.90 / -0.84 | +5.18 / -0.04 |
| seq_control | 42.445 / 43.272 | 42.427 / 42.713 | +0.44 / -1.36 | +0.46 / -1.27 | -0.68 / +1.12 | +0.73 / +0.92 |
| regular_heap_index_control | 37.644 / 36.294 | 37.132 / 34.889 | -1.97 / -4.03 | -1.86 / -3.97 | +1.31 / -4.12 | -0.60 / +0.22 |
| mixed2_count | 51.605 / 30.101 | 52.014 / 29.683 | +0.59 / -1.44 | +0.61 / -1.29 | +0.13 / +0.35 | -0.93 / -1.34 |
| mixed64_count | 42.903 / 40.861 | 50.955 / 39.597 | -1.85 / -3.06 | -1.73 / -3.01 | -2.88 / -1.18 | -0.89 / -0.65 |
| backward_mixed2_sum | 32.683 / 32.487 | 33.483 / 32.556 | +2.19 / +0.21 | +2.24 / +0.32 | +3.22 / +0.90 | +0.37 / -1.21 |
| backward_mixed64_sum | 31.361 / 30.840 | 31.737 / 30.442 | +0.56 / -1.39 | +0.57 / -1.22 | +1.12 / -0.74 | +0.65 / -0.80 |
| backward_f2_p2_sum | 58.701 / 58.728 | 59.962 / 59.227 | +2.09 / +0.88 | +2.13 / +0.83 | +3.05 / +1.37 | +0.72 / +0.01 |

## Regression and control evidence

V14 CPU has positive medians versus B or its exact twin in at least one cohort for: `f2_p2_count`, `f3_p2_count`, `limit1_from_long`, `limit2_from_long`, `one_bigint_long_count`, `one_bigint_singleton_count`, `seq_control`, `regular_heap_index_control`, `mixed2_count`, `backward_mixed2_sum`, `backward_mixed64_sum`, `backward_f2_p2_sum`.

V14/V13 CPU is higher in both cohorts for: `f3_p2_count`, `limit2_from_long`, `one_bigint_long_count`, `seq_control`, `backward_f2_p2_sum`.

V14/V13 CPU is lower in both cohorts for: `f4_p2_count`, `w8_long_count`, `w8_long_tail`, `f32_long_count`, `w32_long_tail`, `mixed2_count`, `mixed64_count`. These are descriptive point estimates; their full per-round ranges remain visible.

Controls and exact-twin movement are not subtracted. Execution and
backend CPU are distinct metrics; a positive executor result is not replaced
by a more favorable CPU result. Neither finite checks nor a positive wide
scan establish universal regression freedom or merge readiness.

The first cohort has broad ranges in several cases; even identical baseline
executables differ (for example T/B CPU is -5.22% / -2.20% for w8_long_count).
Small V14/V13 medians should therefore not be read as established source
effects. No observations were removed. In particular, f2_p2_count has a
higher unpaired V14 execution median in cohort 0 despite a negative median
of same-round paired changes; both statistics are deliberately retained.

## Previous VM84 comparison

| Case | Previous V14/B CPU % | New V14/B CPU % | Previous V14/V13 CPU % | New V14/V13 CPU % |
|---|---:|---:|---:|---:|
| w8_long_count | -27.06 / -30.38 | -22.00 / -18.11 | +0.67 / +1.49 | -0.70 / -0.14 |
| w8_long_tail | -25.36 / -23.70 | -16.66 / -16.62 | +0.59 / +2.39 | -0.84 / -0.04 |
| f32_long_count | -45.43 / -44.84 | -34.17 / -34.76 | +0.74 / -0.15 | -0.90 / -3.00 |
| w32_long_tail | -55.43 / -54.98 | -48.39 / -49.13 | +0.46 / +0.07 | -1.61 / -1.77 |
| f2_p2_count | -3.97 / -2.49 | -0.62 / -1.62 | +0.55 / +1.68 | +1.78 / -0.11 |
| limit1_from_long | -0.28 / +1.62 | +3.40 / +2.18 | -0.45 / +2.09 | +3.05 / -0.02 |
| limit2_from_long | +1.25 / +1.43 | +2.46 / +4.11 | +0.66 / +3.14 | +2.47 / +2.25 |
| mixed2_count | -2.83 / +0.14 | +0.61 / -1.29 | -1.06 / -1.36 | -0.93 / -1.34 |
| backward_mixed2_sum | +0.68 / -0.15 | +2.24 / +0.32 | -1.09 / -1.97 | +0.37 / -1.21 |
| regular_heap_index_control | -2.21 / +5.57 | -1.86 / -3.97 | -0.12 / +2.11 | -0.60 / +0.22 |
| seq_control | -0.64 / +0.75 | +0.46 / -1.27 | -0.89 / +0.64 | +0.73 / +0.92 |

Earlier observations are copied from the frozen 2026-11-09 packet and
are never pooled with this VM. No source/layout/scheduler causal conclusion
is inferred from changes between hosts.

## Validation, inputs and reproduction

Four full clean matched common-path builds, B/V13/V14 release and V14_assert,
each passed core239 with the original expected files. The documented
baseline correctness-seed replacement was actually executed here; all three
original target outputs matched on all four roles without updating expected
files. Native dispatch/cache/slot-ownership checks and actual header/backend
layouts passed. Those native helpers are correctness gates, not new timing data.

The unchanged SQL setup made eight measurement copies before assigning
roles and four extra smoke copies. All 76 smoke plans and 128-statement
validation histories passed, followed by independent receipt review and live
source/install/seed/PID checks before timing. Both fixed cohorts completed
2128 raw / 1824 retained / 304 warm observations, with zero retained root
shared reads and unchanged expected plans. All negative cases are retained.

The independent audit reconstructed 760 absolute groups, 1140 pair groups and 13680 direct pairs. It compared 49140 values, maximum absolute discrepancy 0.0. Undefined zero-denominator ratios: 1736; all absolute/difference/raw pairs remain. Psql CPU is recounted as recorded because client schedstat endpoints were not retained.

Final live checks verified all 17 operational clusters stopped, plus the
new baseline correctness seed (18 including that seed), no owned socket or
binary process, and unchanged source, installs and canonical seed. GCC flags
are -O2 -g -fno-lto, OpenSSL on, ICU/readline off, nice10/j2. SQL uses 1GB
shared_buffers, 128MB work_mem, system clock, JIT/parallel/memoize/autovacuum
off, fsync on. Backend/client CPUs are 6/4 then 4/6; role slots and case order
change according to the frozen protocol. This measures warm SQL on historical
B72; CREATE INDEX is setup, not a measured target.

[Reproduction](REPRODUCE.md) provides dependencies, source identities,
data setup, build/gate/smoke/SQL commands and metric definitions.
[V14 standalone diff](patches/ios-v14-over-b72.diff),
[V13 alternative](patches/ios-v13-over-b72.diff) and
[optional V13-to-V14 diff](patches/ios-v13-to-v14.diff) are labeled as
alternative forms. This run adds evidence, not a new algorithm. The earlier
prototype and unsent 2026-11-09 note are the discussion context; no existing
mailing-list thread or fresh exhaustive novelty search is claimed.
