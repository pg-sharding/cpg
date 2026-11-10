# Completed K1 screen: target gains and material dense regression

The complete fixed matrix passed: 1104 raw /828 retained /276 warm, two separate fresh cohorts. Independent local reconstruction checked all raw semantics/schedules, 456 absolute groups, 456 pair groups and 2736 direct same-round pairs (25992 numerical comparisons, max floating-point difference 5.68e-14). No rows or controls were filtered.

K1 has promising full-read/OR observations, but a material no-reuse dense regression. It is not a general adoption recommendation. The exact same B executable is used by T; all three pairs and all 23 SQL/actual-AM cells remain in the complete BENCHMARKS-K1-r1.md tables. There is no decoder case or claimed decoder/C9-combination benefit.

Actual-AM full inner CPU changed −16.79% /−17.13% vs B: B medians 157.542 /160.270 ms, K1 129.568/132.563ms for 10 complete scans. OR inner CPU changed −19.56% /−18.56%: B 187.365/186.223ms, K1 148.637/149.135ms. SQL full whole-command CPU changed −7.23% /−7.06%, OR −6.74% /−6.82%; full SQL executor −4.72% /−9.28%, OR −6.62% /−4.77%. These are distinct metric boundaries.

The no-reuse dense negative is large: actual-AM inner CPU +13.63% /+13.94%, direct ranges +9.64..+14.56% /+8.09..+17.76%; B 70.464/70.434ms, K1 79.138/80.106ms. T/B inner CPU medians are about +0.15% /+0.03% there. SQL dense whole CPU is+13.08% /+7.43%, executor+10.17% /+2.84%. The earlier untimed probe showed zero consecutive repeated vectors in dense; it motivated this negative, but is not a profile-proved cause of latency.

Other limits remain: phrase SQL executor+0.95% /−1.62%, NOT+1.61% /+5.83%, lossy whole CPU−0.19% /+0.11%, absent whole CPU+0.41% /−1.47%. Tiny inline client-wall ratios have broad shared-load ranges, including approximately−69.7..+179.5% in cohort 0. All values remain in the raw analysis. The lossy control exercised actual lossiness and heap recheck in every role.

The host is explicitly SHARED_LOAD_DIAGNOSTIC: load about 11.15 before /12.38 after on eight guest CPUs. Server/client CPUs 0:4 then 4:0 are recorded guest topology, not proof of independent physical resources. Retained I/O bytes were zero, queue time 2.491/2.493s total and major faults zero. Unchanged Seq whole CPU K1/B−1.14% /+5.25%, T/B+2.97% /+2.79% demonstrates control movement. No twin normalization, pooling, trimming, significance or causal attribution is used. A clean-host confirmation is a separate future stage.

Numbers below are absolute medians in milliseconds per fixed command and median direct same-round percentages over six retained rounds. Median ratios need not equal ratios of absolute medians. Every metric min/median/max/mean/sample stdev/MAD, raw value and direct difference is in the analysis JSON.

## Cohort 0: every cell, whole-command CPU

| Cell | B median ms | T median ms | K1 median ms | K1/B median % | min % | max % | K1/T median % | T/B median % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| skew1000 | 117.328 | 119.829 | 120.480 | -0.821 | -3.163 | 5.423 | 1.554 | -0.043 |
| skew127 | 221.231 | 221.375 | 215.522 | -2.678 | -4.633 | 2.263 | -2.355 | -0.523 |
| dense_and | 138.526 | 137.785 | 154.235 | 13.080 | 2.164 | 38.772 | 14.476 | -0.307 |
| or_forced | 241.194 | 239.393 | 222.602 | -6.740 | -9.939 | -4.093 | -7.383 | -0.762 |
| single_forced | 224.372 | 224.609 | 208.285 | -7.234 | -10.049 | -3.803 | -7.134 | 0.460 |
| single_rare | 10.426 | 10.428 | 9.970 | -4.612 | -6.274 | 0.083 | -4.776 | -0.317 |
| inline | 0.923 | 0.929 | 0.924 | -0.157 | -6.125 | 6.209 | -0.555 | -0.993 |
| prefix | 159.416 | 161.673 | 158.874 | -0.301 | -1.100 | 3.487 | -1.009 | 1.322 |
| phrase | 119.968 | 119.324 | 117.678 | -0.591 | -3.458 | 2.586 | -0.750 | 0.000 |
| not | 56.333 | 56.419 | 56.045 | -0.678 | -4.508 | 5.509 | -0.504 | 0.184 |
| jsonb | 229.412 | 229.131 | 229.074 | -1.235 | -2.718 | -0.003 | 0.036 | -1.398 |
| lossy_and | 237.150 | 224.302 | 236.428 | -0.187 | -7.810 | 5.678 | 2.804 | -2.469 |
| seq_control | 77.817 | 79.581 | 78.022 | -1.143 | -7.218 | 11.126 | 1.297 | 2.972 |
| skew_group4096 | 87.557 | 87.887 | 86.062 | -1.477 | -3.974 | 6.462 | -2.053 | 1.810 |
| inline_single | 5.071 | 5.020 | 4.689 | -6.658 | -8.904 | -2.670 | -6.480 | -1.041 |
| absent | 2.612 | 2.619 | 2.613 | 0.408 | -2.460 | 3.796 | 0.492 | 0.046 |
| am_inline | 30.253 | 30.887 | 29.667 | -2.015 | -2.333 | -1.216 | -2.287 | 0.517 |
| am_absent | 102.781 | 97.915 | 100.000 | -2.027 | -10.088 | 1.774 | 1.099 | -4.831 |
| am_skew1000 | 106.139 | 109.228 | 104.054 | -2.376 | -3.180 | 3.957 | -4.326 | 2.474 |
| am_full | 157.775 | 160.836 | 129.801 | -16.763 | -20.743 | -15.054 | -18.882 | 0.909 |
| am_or | 187.621 | 181.542 | 148.871 | -19.556 | -23.163 | -17.456 | -18.713 | -1.779 |
| am_dense | 70.698 | 71.031 | 79.378 | 13.559 | 9.622 | 14.459 | 11.431 | 0.111 |
| am_rare | 17.651 | 17.537 | 14.941 | -14.962 | -15.852 | -12.209 | -14.788 | -0.589 |

## Cohort 0: all actual-AM inner CPU cases

| Cell | B median ms | K1 median ms | K1/B median % | min % | max % | T/B median % |
|---|---:|---:|---:|---:|---:|---:|
| am_inline | 30.098 | 29.500 | -2.068 | -2.406 | -1.196 | 0.562 |
| am_absent | 102.549 | 99.765 | -2.045 | -10.126 | 1.714 | -4.857 |
| am_skew1000 | 105.900 | 103.826 | -2.347 | -3.185 | 3.966 | 2.510 |
| am_full | 157.542 | 129.568 | -16.792 | -20.765 | -15.081 | 0.902 |
| am_or | 187.365 | 148.637 | -19.563 | -23.182 | -17.465 | -1.783 |
| am_dense | 70.464 | 79.138 | 13.633 | 9.645 | 14.562 | 0.152 |
| am_rare | 17.528 | 14.828 | -15.123 | -15.844 | -12.247 | -0.576 |

## Cohort 1: every cell, whole-command CPU

| Cell | B median ms | T median ms | K1 median ms | K1/B median % | min % | max % | K1/T median % | T/B median % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| skew1000 | 120.493 | 118.844 | 115.760 | -3.426 | -7.218 | -0.424 | -2.787 | -1.104 |
| skew127 | 218.397 | 218.936 | 213.231 | -2.380 | -4.087 | -2.203 | -2.619 | 0.247 |
| dense_and | 138.208 | 136.377 | 150.209 | 7.428 | 2.149 | 21.291 | 7.762 | -1.575 |
| or_forced | 237.354 | 246.109 | 224.024 | -6.822 | -7.970 | -3.542 | -8.974 | 3.688 |
| single_forced | 223.107 | 226.513 | 208.948 | -7.056 | -12.304 | -4.333 | -5.913 | 0.654 |
| single_rare | 10.703 | 10.754 | 9.850 | -6.575 | -9.157 | -5.287 | -7.790 | 0.328 |
| inline | 0.929 | 0.937 | 0.936 | 0.462 | -4.121 | 2.331 | 0.656 | -1.793 |
| prefix | 159.127 | 158.246 | 156.187 | -0.739 | -6.216 | 2.873 | -2.134 | -0.627 |
| phrase | 120.508 | 125.882 | 118.628 | -0.984 | -4.920 | 2.309 | -3.908 | 2.230 |
| not | 57.360 | 57.642 | 55.289 | -2.985 | -8.374 | 0.760 | -3.260 | 0.040 |
| jsonb | 225.745 | 237.743 | 230.953 | 1.003 | -4.701 | 4.279 | -1.761 | -0.010 |
| lossy_and | 235.983 | 238.259 | 236.774 | 0.112 | -4.348 | 9.541 | -0.190 | 1.342 |
| seq_control | 75.538 | 77.420 | 77.709 | 5.255 | -2.120 | 14.867 | -0.972 | 2.788 |
| skew_group4096 | 84.945 | 88.108 | 85.570 | 1.247 | -3.756 | 6.096 | -3.752 | 3.394 |
| inline_single | 5.010 | 4.970 | 4.551 | -8.884 | -9.832 | -7.552 | -8.134 | -0.876 |
| absent | 2.249 | 2.242 | 2.228 | -1.466 | -1.609 | 2.357 | -0.557 | -0.581 |
| am_inline | 31.159 | 30.511 | 29.678 | -4.762 | -6.734 | -2.795 | -2.074 | -2.197 |
| am_absent | 98.263 | 98.118 | 97.205 | 0.221 | -2.969 | 3.454 | 0.688 | -1.386 |
| am_skew1000 | 109.601 | 111.765 | 108.793 | -0.559 | -2.207 | 5.498 | -0.956 | 0.005 |
| am_full | 160.518 | 160.555 | 132.833 | -17.099 | -21.017 | -12.749 | -17.301 | 0.449 |
| am_or | 186.474 | 188.250 | 149.413 | -18.532 | -22.159 | -15.959 | -19.485 | 3.336 |
| am_dense | 70.657 | 70.268 | 80.332 | 13.864 | 8.036 | 17.707 | 13.861 | 0.018 |
| am_rare | 18.441 | 17.747 | 15.365 | -16.436 | -17.845 | -15.012 | -15.964 | -0.207 |

## Cohort 1: all actual-AM inner CPU cases

| Cell | B median ms | K1 median ms | K1/B median % | min % | max % | T/B median % |
|---|---:|---:|---:|---:|---:|---:|
| am_inline | 30.992 | 29.521 | -4.720 | -6.739 | -2.791 | -2.167 |
| am_absent | 98.030 | 96.979 | 0.200 | -2.956 | 3.440 | -1.415 |
| am_skew1000 | 109.349 | 108.540 | -0.571 | -2.219 | 5.521 | 0.017 |
| am_full | 160.270 | 132.563 | -17.128 | -21.043 | -12.768 | 0.454 |
| am_or | 186.223 | 149.135 | -18.563 | -22.182 | -15.972 | 3.323 |
| am_dense | 70.434 | 80.106 | 13.937 | 8.087 | 17.764 | 0.034 |
| am_rare | 18.296 | 15.224 | -16.498 | -17.881 | -15.181 | -0.037 |

## Qualification, local analyzer repair and provenance

Three clean B/K1/K1_assert builds passed unchanged core239/posting-list tests. The installed-backend gate passed 40 ordered ordinary SQL cases, 7 repeated prepared cases, 12 lifecycle comparisons,11 valid native ternary-dispatch cases and 11 VOLATILE generic-fallback cases per variant. The separate 69-row smoke passed with zero accepted timings, 75 ordered oracles and six unused accepted copies checked before root review. All raw/journals were durable before parse/assert. Source, seed, three prefixes, modules and frozen input checks passed; root final live proof is separate.

The original frozen analyzer had one stale acceptance guard n==10, although protocol/orders/raw validation were six retained rounds. It failed locally before creating output. Its failure and unchanged original source are preserved. A new local r2 changes only that guard to the preregistered 6; extraction/statistics/pairing are unchanged. Both r2 outputs passed independent reconstruction. This is not a benchmark rerun or an outcome-dependent filtering/metric change.

K1 source is canonical root-authored 9e0d6e84c5bd538e58a534c99cb39ca669c567b7 over fixed B 8a8c475037bfde101da23cc9b0364c9c020eca93. Exact builtin OIDs and function addresses guard the per-scan-key memo; no generic callback purity is assumed. Native tri leaves recheck unchanged and the cached result includes MAYBE. Query/strategy/categories/map lifetime is fixed to that key, and hidden/nine-entry bounds fall back normally. All new builds share the same opaque prerequisite.

Heikki 2014 is direct prior art for result caching; there is no novelty claim for the idea. The measured wrapper repetition counts are motivation only, not K1 dynamic hit counters or latency evidence. D2 decoder and a possible miss-budget K2 remain separately identified source-only future attempts; no new build/timing is included or merged into K1 results.
