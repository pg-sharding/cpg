# Wide-OR SQL follow-up: observed gains and controls

Two cohorts completed384 raw /288 retained /96 warm observations. All eight cases, three metrics and three pairs are retained. Source/ELFs/seed are unchanged from the earlier heap experiment. These seven positive SQL cases force GIN and return all200000 ordinary rows; they do not demonstrate a default-planner application speedup.

Executor gains versus B grow from about5.7–5.9% at width8 to16.6–17.4% at32 and24.5–26.4% at128–512. Mandatory widths1/2/7 show little benefit, and the unchanged Seq control costs more. Cohort0 OR512 exact twins differ8.46%; both cohorts remain without normalization or source-causal claims.

Absolute values below are executor milliseconds per complete count/sum query. Percentages are medians of same-round ratios, not ratios of absolute medians. All CPU/client/executor spreads and raw arrays are in BENCHMARKS-r1.md and analysis/.

## Cohort0

| Case | B ms | T ms | Heap ms | Heap/B % | Heap/B range % | Heap/T % | T/B % |
|---|---:|---:|---:|---:|---|---:|---:|
| sql_or_dense1 | 30.511 | 29.576 | 30.230 | -1.012 | -1.558 .. -0.119 | 1.770 | -2.393 |
| sql_or_dense2 | 31.648 | 30.543 | 31.531 | 0.112 | -0.991 .. 0.833 | 2.851 | -2.515 |
| sql_or_dense7 | 39.819 | 39.294 | 40.053 | 0.731 | -2.551 .. 2.007 | 2.503 | -1.904 |
| sql_or_dense8 | 41.492 | 41.114 | 39.220 | -5.657 | -7.138 .. -4.711 | -4.606 | -1.109 |
| sql_or_dense32 | 90.446 | 89.898 | 75.578 | -16.643 | -17.498 .. -15.310 | -15.977 | -0.802 |
| sql_or_dense128 | 283.459 | 281.938 | 211.108 | -25.582 | -26.350 .. -24.806 | -25.176 | -0.485 |
| sql_or_dense512 | 1120.671 | 1216.234 | 831.913 | -25.788 | -26.215 .. -24.869 | -31.684 | 8.457 |
| seq_control | 19.451 | 19.806 | 20.893 | 7.398 | 2.827 .. 10.202 | 5.911 | 2.870 |

## Cohort1

| Case | B ms | T ms | Heap ms | Heap/B % | Heap/B range % | Heap/T % | T/B % |
|---|---:|---:|---:|---:|---|---:|---:|
| sql_or_dense1 | 29.515 | 29.304 | 29.525 | -0.259 | -0.951 .. 0.765 | 0.625 | -0.721 |
| sql_or_dense2 | 30.689 | 30.593 | 30.815 | 0.463 | -0.189 .. 2.853 | 0.851 | -0.308 |
| sql_or_dense7 | 39.257 | 39.199 | 39.341 | 0.066 | -0.125 .. 0.933 | 0.451 | -0.050 |
| sql_or_dense8 | 40.686 | 40.559 | 38.272 | -5.900 | -7.303 .. -5.423 | -5.755 | -0.145 |
| sql_or_dense32 | 88.959 | 89.303 | 73.556 | -17.411 | -17.811 .. -17.235 | -17.654 | 0.413 |
| sql_or_dense128 | 273.647 | 276.356 | 206.683 | -24.496 | -25.028 .. -23.286 | -25.172 | 0.882 |
| sql_or_dense512 | 1129.476 | 1136.940 | 832.355 | -26.444 | -29.165 .. -25.420 | -26.389 | 0.836 |
| seq_control | 19.524 | 19.782 | 20.498 | 5.031 | 3.208 .. 6.303 | 3.982 | 1.146 |

The independent reconstruction and root rerun checked8208 numerical fields:144 absolute groups,144 pair groups,864 direct pairs and48 ordered Seq/GIN oracles. All9 new cluster lifetimes stopped; complete prefixes/source/two seeds/inputs were unchanged. Retained backend reads/writes and faults were zero; runqueue totals14.462/11.187ms are diagnostics. This valid serial fixture is not concurrency or broad merge coverage.

Heikki's2014 heap-selection discussion is direct prior art. The concrete contribution is the prototype's shared-entry-safe lower bounds, checked fallback/invariants and reproducible SQL/AM positives and negatives, not a new heap algorithm. Selective OR without forced planner settings remains unmeasured.
