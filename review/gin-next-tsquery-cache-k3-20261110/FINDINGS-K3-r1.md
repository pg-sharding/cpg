# K3: dense penalty reduced, remaining regressions retained

The fixed B/T/K1/K3 comparison completed 2576 raw observations: 2208 retained and 368 warm, in two fresh cohorts. All 23 cells and all six pairs remain. Independent arithmetic matched all 79,040 numerical values (largest absolute difference 2.84e-14); ordered Seq/GIN results and checked plan trees/rows/loops agree. Each group has 12 retained observations.

K3 is a mixed result, rather than a general repair of K1. Dense SQL executor time fell 5.71%/5.63% against K1 but remained 2.62%/3.02% above B. Dense actual-AM inner CPU fell 4.80%/4.19% against K1; against the exact B twin T it remained 7.79%/9.17% higher. Full/OR actual-AM gains largely remained, with small increases against K1.

The rare-single SQL executor case rose 7.99%/5.10% against K1, with all 12 direct pair differences positive in both cohorts. Prefix rose 0.15%/6.01%; cohort1 direct percentages were 4.06% to 7.72%. The unchanged Seq control rose 0.23%/2.01% against B and was -0.23%/+0.99% against K1. These observations do not establish a source-level cause.

Cohort0 has material exact-twin variation: T/B actual-AM inner CPU is -9.50% for OR, -6.61% for dense, and -2.79% for full. Corresponding cohort1 differences are +0.21%, +0.29%, and +0.62%. Neither cohort is dropped or normalized by the twin. Retained backend reads/writes and minor/major faults were zero; total runqueue deltas were 34.31ms and 26.00ms. A quiet launch does not eliminate control variation.

The following absolute medians use SQL executor milliseconds or actual-AM inner CPU milliseconds for each complete work unit. Percentages are medians of same-round right/left ratios; they need not equal ratios of absolute medians. Full backend CPU, client wall, SQL executor and AM inner CPU/wall, all ranges, means, sample SD, MAD, raw vectors and all direct pairs are retained in `RESULTS-ALL-GROUPS-K3-r1.md` and analysis JSON.

## Cohort 0

| Case | Metric | B ms | T ms | K1 ms | K3 ms | T/B % | K1/B % | K3/B % | K3/T % | K3/K1 % | K3/K1 range % |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| skew1000 | sql_execution_ms | 76.632 | 76.519 | 76.442 | 76.507 | 0.056 | -0.336 | -0.269 | -0.026 | 0.039 | -1.617 .. 1.953 |
| skew127 | sql_execution_ms | 138.545 | 138.981 | 137.048 | 139.521 | 0.502 | -0.922 | 0.379 | 0.141 | 1.480 | -0.021 .. 3.513 |
| dense_and | sql_execution_ms | 82.767 | 83.131 | 90.076 | 84.365 | 0.834 | 7.944 | 2.616 | 1.473 | -5.706 | -8.518 .. 3.329 |
| or_forced | sql_execution_ms | 151.071 | 151.924 | 144.792 | 143.999 | 0.582 | -4.380 | -4.246 | -5.072 | 0.317 | -2.755 .. 2.057 |
| single_forced | sql_execution_ms | 144.123 | 145.151 | 141.256 | 140.971 | 0.401 | -2.312 | -2.242 | -2.975 | 0.116 | -0.828 .. 0.892 |
| single_rare | sql_execution_ms | 5.950 | 6.027 | 5.928 | 6.380 | 1.380 | -0.353 | 7.399 | 5.350 | 7.987 | 5.046 .. 10.688 |
| inline | sql_execution_ms | 0.445 | 0.458 | 0.431 | 0.443 | -1.271 | -1.968 | 0.815 | 0.277 | 2.113 | -9.979 .. 13.333 |
| prefix | sql_execution_ms | 91.916 | 92.045 | 91.757 | 91.743 | 0.096 | -0.429 | -0.358 | -0.397 | 0.152 | -2.392 .. 2.080 |
| phrase | sql_execution_ms | 76.885 | 76.917 | 76.981 | 77.608 | -0.119 | -0.047 | 0.304 | 0.080 | 0.206 | -3.056 .. 2.051 |
| not | sql_execution_ms | 37.001 | 37.019 | 36.906 | 36.809 | -0.018 | -0.432 | -0.700 | -0.615 | -0.218 | -0.890 .. 0.881 |
| jsonb | sql_execution_ms | 151.251 | 150.948 | 151.810 | 151.092 | -0.026 | 0.214 | -0.179 | 0.026 | -0.367 | -1.277 .. 1.027 |
| lossy_and | sql_execution_ms | 130.394 | 130.024 | 133.541 | 131.690 | -0.526 | 2.657 | 1.072 | 1.338 | -1.426 | -4.842 .. 0.657 |
| seq_control | sql_execution_ms | 56.105 | 57.380 | 55.630 | 56.343 | 2.783 | 0.482 | 0.227 | -3.015 | -0.225 | -5.491 .. 6.988 |
| skew_group4096 | sql_execution_ms | 57.776 | 57.821 | 57.757 | 57.750 | 0.152 | -0.093 | -0.117 | -0.178 | 0.003 | -1.654 .. 0.899 |
| inline_single | sql_execution_ms | 2.857 | 2.834 | 2.803 | 2.833 | -0.742 | -1.871 | -0.770 | 0.176 | 1.199 | -1.291 .. 3.631 |
| absent | sql_execution_ms | 1.288 | 1.312 | 1.292 | 1.290 | 1.290 | 0.508 | -0.115 | -1.905 | -0.390 | -2.914 .. 2.069 |
| am_inline | am_loop_cpu_ms | 18.417 | 17.972 | 17.690 | 17.766 | -2.369 | -3.828 | -3.524 | -1.284 | 0.430 | -2.117 .. 1.385 |
| am_absent | am_loop_cpu_ms | 55.339 | 54.703 | 55.115 | 55.265 | -1.085 | -0.377 | -0.151 | 1.028 | 0.269 | -1.625 .. 0.432 |
| am_skew1000 | am_loop_cpu_ms | 71.486 | 71.167 | 71.107 | 71.017 | -0.390 | -0.382 | -0.474 | -0.252 | -0.115 | -1.078 .. 3.504 |
| am_full | am_loop_cpu_ms | 107.338 | 104.300 | 91.529 | 90.932 | -2.790 | -15.201 | -15.296 | -12.680 | 0.055 | -1.287 .. 1.611 |
| am_or | am_loop_cpu_ms | 122.298 | 110.655 | 95.444 | 95.653 | -9.500 | -21.968 | -21.825 | -13.460 | 0.190 | -1.015 .. 1.383 |
| am_dense | am_loop_cpu_ms | 46.930 | 43.846 | 49.652 | 47.276 | -6.609 | 5.784 | 0.701 | 7.786 | -4.801 | -5.281 .. -4.446 |
| am_rare | am_loop_cpu_ms | 11.715 | 11.746 | 10.056 | 10.214 | 0.579 | -14.192 | -12.580 | -13.083 | 1.469 | -7.331 .. 2.387 |

## Cohort 1

| Case | Metric | B ms | T ms | K1 ms | K3 ms | T/B % | K1/B % | K3/B % | K3/T % | K3/K1 % | K3/K1 range % |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| skew1000 | sql_execution_ms | 76.234 | 76.184 | 76.095 | 76.244 | -0.065 | -0.209 | 0.011 | 0.054 | 0.180 | 0.064 .. 0.573 |
| skew127 | sql_execution_ms | 136.710 | 136.189 | 135.517 | 137.707 | -0.449 | -0.971 | 0.728 | 1.134 | 1.725 | 0.442 .. 2.692 |
| dense_and | sql_execution_ms | 81.534 | 81.025 | 89.735 | 84.260 | -0.414 | 9.779 | 3.023 | 3.194 | -5.634 | -15.255 .. -2.183 |
| or_forced | sql_execution_ms | 150.154 | 150.601 | 144.345 | 146.062 | 0.498 | -3.697 | -3.008 | -2.524 | 1.271 | -1.499 .. 4.070 |
| single_forced | sql_execution_ms | 144.831 | 144.540 | 143.904 | 145.825 | -0.497 | -1.061 | 0.648 | 0.418 | 0.988 | -0.990 .. 2.825 |
| single_rare | sql_execution_ms | 6.176 | 6.106 | 5.976 | 6.286 | -1.233 | -3.039 | 2.177 | 2.917 | 5.104 | 3.152 .. 7.698 |
| inline | sql_execution_ms | 0.444 | 0.432 | 0.453 | 0.435 | -0.453 | 3.941 | 0.472 | 0.115 | -3.047 | -10.230 .. 2.576 |
| prefix | sql_execution_ms | 93.523 | 94.975 | 93.092 | 98.592 | 1.697 | -0.478 | 5.604 | 3.830 | 6.006 | 4.062 .. 7.717 |
| phrase | sql_execution_ms | 76.234 | 76.335 | 75.828 | 76.244 | 0.075 | -0.547 | -0.061 | -0.122 | 0.501 | -0.130 .. 0.899 |
| not | sql_execution_ms | 36.466 | 36.484 | 36.211 | 36.281 | 0.063 | -0.741 | -0.461 | -0.508 | 0.177 | -0.097 .. 0.583 |
| jsonb | sql_execution_ms | 147.912 | 147.839 | 148.028 | 147.397 | -0.002 | 0.044 | 0.084 | 0.064 | -0.067 | -1.378 .. 0.399 |
| lossy_and | sql_execution_ms | 131.925 | 131.462 | 133.958 | 132.702 | -0.022 | 1.314 | 0.531 | 0.902 | -0.780 | -2.815 .. 0.562 |
| seq_control | sql_execution_ms | 54.993 | 55.652 | 56.403 | 57.239 | 0.192 | 1.520 | 2.012 | -0.292 | 0.991 | -6.193 .. 4.204 |
| skew_group4096 | sql_execution_ms | 55.980 | 56.151 | 55.971 | 56.028 | 0.279 | -0.059 | 0.102 | -0.285 | 0.065 | -0.216 .. 0.653 |
| inline_single | sql_execution_ms | 2.827 | 2.824 | 2.784 | 2.816 | -0.228 | -1.710 | -0.649 | -0.440 | 1.062 | -0.395 .. 3.048 |
| absent | sql_execution_ms | 1.173 | 1.167 | 1.159 | 1.157 | -0.172 | -1.365 | -1.406 | -1.112 | -0.304 | -1.295 .. 1.215 |
| am_inline | am_loop_cpu_ms | 17.994 | 18.029 | 17.739 | 17.736 | 0.230 | -1.393 | -1.432 | -1.637 | -0.097 | -0.799 .. 1.179 |
| am_absent | am_loop_cpu_ms | 54.133 | 54.806 | 54.485 | 54.205 | 1.282 | 0.688 | 0.172 | -1.096 | -0.450 | -1.427 .. -0.023 |
| am_skew1000 | am_loop_cpu_ms | 71.290 | 71.263 | 71.091 | 71.001 | -0.055 | -0.275 | -0.361 | -0.262 | -0.083 | -0.474 .. 0.551 |
| am_full | am_loop_cpu_ms | 96.943 | 97.622 | 90.318 | 90.594 | 0.616 | -6.815 | -6.539 | -7.167 | 0.317 | -0.858 .. 0.689 |
| am_or | am_loop_cpu_ms | 110.328 | 110.718 | 95.168 | 95.416 | 0.207 | -13.762 | -13.530 | -13.694 | 0.267 | 0.023 .. 0.383 |
| am_dense | am_loop_cpu_ms | 44.088 | 44.066 | 50.113 | 48.118 | 0.290 | 14.141 | 9.175 | 9.172 | -4.188 | -4.686 .. -2.987 |
| am_rare | am_loop_cpu_ms | 10.807 | 10.951 | 10.266 | 10.259 | 1.213 | -4.909 | -4.839 | -6.100 | 0.127 | -0.374 .. 0.992 |

## Scope

Four fresh B/K1/K3/K3_assert builds passed 239 unchanged core tests and posting-list checks each. The finite gate retained 160 ordered SQL cases, 28 prepared cases, 48 lifecycle comparisons, the original exhaustive mixed-vector/native and generic fallback oracles, and 51,744 new dispatcher boundary checks. Boundaries include 63/64/65 misses, hit reset, permanent direct dispatch, independent keys and context reset. Context reset is not index_rescan; the preserved actual-AM workload exercises real rescans separately.

K3 uses 64 consecutive dispatcher misses, resets on memo hit, and keeps the original builtin OID/address and hidden-entry fallback guards. This is a dispatcher-call budget, including startup calls, rather than a TID budget. A long initial no-reuse run may still disable later reuse. Actual normal ASM contains two mutually exclusive native callback call sites: ordinary miss and over-eight-entry fallback.

The completed measured sources, flags, thresholds, cases and schedule remain unchanged. No repeat, filtering, pooling, significance test, twin normalization or general concurrency/merge claim is introduced. A later untimed diagnostic must have its own namespace and provenance; it cannot be presented as instrumentation of these existing executables.
