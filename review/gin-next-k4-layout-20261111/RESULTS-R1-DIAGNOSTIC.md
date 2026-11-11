# K4 r1 results — retained shared-load diagnostic

**R1 does not establish a scan-key layout speedup or a fix for dense overhead.** Both cohorts passed their runtime gates, but a foreign Go pool.test task was observed at the run tail using about 171% CPU, with sampled host load 2.56. Its exact overlap with measured commands is unknown. Before reading accepted-run timing values, root recorded ROOT-R1-SHARED-LOAD-DECISION.json: retain every r1 sample, classify the whole attempt as SHARED_LOAD_DIAGNOSTIC, and repeat the entire unchanged protocol in fresh r2 copies after foreign work and all builds/gates stop. Smoke correctness outputs had already been reviewed. R2 is reported separately; no case, cohort or round is trimmed, no control normalization is applied and no r1/r2 pooling is permitted.

The raw FRESH_HOST_CLEAN_SCREEN field is preserved as the pre-freeze intent. It is not the final interpretation of r1. The end-of-run foreign task is an uncertainty about the whole attempt, not proof that any particular observed difference was caused by that task. The two cohorts are separate placements on one host. None is retrospectively promoted to a clean result.

The fixed source controls are B/T (152 bytes, no memo), C (144 bytes, identical field reorder without memo), K3 (160 bytes, original layout with memo) and K4 (152 bytes, reordered K3). Five clean builds, including K4_assert, passed core239, posting-list checks and installed ABI assertions. Qualification passed 40 ordinary ordered cases per source variant, seven prepared cases, 12 lifecycle comparisons, 11 native cases, 11 budget cases and 11 generic fallback cases per variant. Across five variants the budget oracle made 64680 calls. Those are correctness gates, not timing observations.

All 2880 measured raw observations are retained as evidence: 2400 retained and 480 preceding warm observations. Each cohort has 24 cases × five roles × 12 rounds; ten rounds enter its statistics. Separate literal warming commands precede every measured command. The comparison uses the frozen odd-size Williams orders, then reverses case and physical placement order in cohort 1 with the server/client CPUs swapped from 0/4 to 4/0. No source, loops, case list, retained count or schedule is changed for r2.

Independent local review rehashed 836 collection-bound files plus COLLECTION.json, reconstructed all 114550 numerical fields directly from raw JSON without importing the runtime validator/protocol, and required every expected absolute/pair key exactly once. All 2040 full-run SQL plans and 840 AM results passed their answers, settings, actual rows/loops, index searches, recheck/lossy conditions and monotonic chronology checks. All 17 expanded semantic/actual plan signatures match across smoke and both full cohorts. The stored final live receipt reports 21 stopped lifetimes, unchanged source/prefix/seed/input bindings and no cleanup errors; this review did not perform a new live VM inspection. Command counters record zero major faults and disk read/write bytes, which does not resolve CPU interference.

The control evidence prevents a simple causal reading. The seq_control plan uses no GIN, yet K4/B SQL executor differences are −3.668% / −4.824%. C/B on the same control changes from +3.284% to −3.313%. Exact-twin T/B on skew127 is +1.894% / −7.216%, with a cohort-1 range of −23.180% to +6.679%. These observations cannot be explained as a memo algorithm benefit. They are preserved rather than subtracted from candidate results.

Dense results remain mixed. Dense-and SQL K4/B is −0.622% / +6.470%, with direct-pair ranges [−9.816%, +2.914%] and [−14.835%, +53.749%]. K4/K3 on that SQL case changes from −3.093% to +5.457%, while T/B is +1.911% / +3.629%. The actual-AM dense inner CPU comparison K4/K3 is −2.288% / −6.301%, but K4/B is +0.069% / −0.364%. This does not demonstrate that the source reorder removes a specific cost or that the inner-AM difference transfers to whole SQL.

Some diagnostic reductions are sizable: forced-OR SQL K4/B is −4.660% / −7.126%, and actual-AM OR inner CPU is −13.009% / −13.574%. The corresponding K4/K3 values are −1.507% / +0.025% for SQL and −1.351% / −0.527% for AM CPU. K3/B itself is already negative in those cases. These are observations retained alongside the separately reported predecided full repeat, not proof of a new layout mechanism. In particular, C/B varies between contexts and cohorts, so K4/C alone cannot isolate a general memo benefit.

Skew1000 SQL K4/B is +0.153% / −0.359%, while C/B is +2.200% / +6.348% and K4/C is −1.731% / −2.795%. Separate_keys is −0.443% / +0.317% for K4/B; the cohort-1 T/B range extends to +48.757%. Absent SQL is −0.312% / +0.510% for K4/B, while C/B is +5.687% / +5.938%; actual-AM absent inner CPU K4/B is +0.329% / −0.226%, even though K4/C is −5.115% / −4.732%. These baselines show why a favorable comparison to C cannot be reported as an equal improvement over B.

All cases, signs and metrics appear below and in [the complete absolute/spread tables](RESULTS-R1-DIAGNOSTIC-TABLES.md). The latter include all 79 metrics per role/cohort, all five absolute role distributions, backend CPU/client wall/SQL executor metrics, AM inner CPU/wall and whole-command metrics, and six displayed role pairs. Original analyzer JSON preserves every sample, mean/stdev/MAD, differences and all ten role pairs. Historical K3 results are separate evidence and are not pooled with this attempt.

Every percentage below is the median of the ten direct round percentages, 100 × (candidate/reference − 1), not a ratio of absolute medians. Each cell is cohort 0 / cohort 1; negative is lower elapsed/CPU time. SQL tables refer to the complete executor command including its fixed probes, and AM tables refer to the fixed inner rescan/getbitmap/tbm batch. They are distinct work boundaries and are not per-probe latency.

## All whole-SQL cases — SQL executor %

| Case | C/B c0 / c1 | K4/K3 c0 / c1 | K4/C c0 / c1 | K3/B c0 / c1 | K4/B c0 / c1 | T/B c0 / c1 |
|---|---:|---:|---:|---:|---:|---:|
| skew1000 | +2.200 / +6.348 | +0.386 / -1.081 | -1.731 / -2.795 | -0.172 / +0.956 | +0.153 / -0.359 | +0.090 / +0.366 |
| skew127 | +2.780 / -4.966 | -2.986 / +0.102 | -4.349 / -2.880 | +1.158 / -7.444 | -1.560 / -4.503 | +1.894 / -7.216 |
| separate_keys | +1.715 / +7.418 | -0.068 / -0.767 | -2.069 / -4.569 | -0.164 / +1.215 | -0.443 / +0.317 | +0.162 / +0.694 |
| dense_and | +2.383 / +6.033 | -3.093 / +5.457 | -2.761 / -1.802 | +1.348 / +1.650 | -0.622 / +6.470 | +1.911 / +3.629 |
| or_forced | +2.170 / -1.445 | -1.507 / +0.025 | -7.467 / -5.784 | -3.399 / -5.743 | -4.660 / -7.126 | +0.970 / +0.554 |
| single_forced | +2.185 / -1.087 | -1.478 / -0.027 | -3.648 / -2.756 | -0.220 / -3.361 | -1.498 / -3.533 | +1.630 / -0.663 |
| single_rare | -0.374 / -1.115 | -3.773 / -1.284 | -1.006 / -0.118 | +2.733 / +0.216 | -1.206 / -1.116 | +1.075 / -0.266 |
| inline | -0.976 / -1.554 | +0.000 / -1.791 | +0.000 / +0.585 | -4.531 / +0.334 | -1.652 / -5.187 | -0.106 / +1.479 |
| prefix | +0.352 / -0.209 | +0.296 / +0.640 | -0.224 / +0.239 | +0.000 / -0.372 | +0.288 / +0.274 | +0.376 / +0.364 |
| phrase | +1.864 / +1.960 | -0.080 / +0.307 | -2.436 / -2.078 | -0.500 / -0.748 | -0.525 / -0.562 | -0.119 / +0.160 |
| not | +2.390 / +2.260 | +0.325 / -0.060 | -2.411 / -2.466 | -0.407 / +0.074 | -0.108 / -0.181 | +0.176 / -0.059 |
| jsonb | +2.021 / +1.788 | -0.138 / -0.021 | -1.855 / -1.491 | +0.266 / +0.204 | +0.078 / +0.151 | +0.154 / -0.044 |
| lossy_and | +1.049 / +2.324 | -0.252 / -1.324 | -1.181 / -2.296 | +0.325 / +0.764 | -0.228 / +0.067 | +2.030 / +0.407 |
| seq_control | +3.284 / -3.313 | -6.490 / -1.976 | -7.544 / -1.433 | +1.555 / -3.580 | -3.668 / -4.824 | -0.705 / -1.329 |
| skew_group4096 | +2.196 / +2.125 | +0.313 / +0.364 | -1.814 / -1.734 | +0.062 / -0.158 | +0.319 / +0.118 | +0.169 / -0.083 |
| inline_single | +1.267 / +0.388 | -1.247 / +0.181 | -3.180 / -0.267 | -0.070 / +0.250 | -1.544 / +0.070 | +0.672 / +0.995 |
| absent | +5.687 / +5.938 | -0.388 / +0.861 | -5.091 / -5.133 | +0.350 / -0.430 | -0.312 / +0.510 | +1.808 / -0.424 |

## All actual-AM cases — inner loop CPU %

| Case | C/B c0 / c1 | K4/K3 c0 / c1 | K4/C c0 / c1 | K3/B c0 / c1 | K4/B c0 / c1 | T/B c0 / c1 |
|---|---:|---:|---:|---:|---:|---:|
| am_inline | +1.023 / -0.206 | -0.926 / -0.434 | -2.883 / -1.391 | -0.837 / -1.268 | -1.759 / -1.612 | -0.644 / -0.115 |
| am_absent | +5.680 / +4.506 | +0.057 / -0.075 | -5.115 / -4.732 | +0.280 / -0.087 | +0.329 / -0.226 | +0.008 / -0.574 |
| am_skew1000 | +2.018 / +2.056 | -0.112 / -0.024 | -2.264 / -2.187 | -0.238 / -0.339 | -0.223 / -0.353 | -0.134 / -0.272 |
| am_full | +0.347 / +0.409 | -0.356 / -0.707 | -6.918 / -7.409 | -6.318 / -6.437 | -6.559 / -7.061 | -0.003 / +0.402 |
| am_or | +0.524 / +1.077 | -1.351 / -0.527 | -13.832 / -14.366 | -11.842 / -13.067 | -13.009 / -13.574 | +0.266 / +1.727 |
| am_dense | +0.609 / +0.579 | -2.288 / -6.301 | -0.497 / -0.965 | +2.416 / +6.359 | +0.069 / -0.364 | +0.021 / +0.192 |
| am_rare | -0.556 / -2.084 | -0.272 / -0.260 | -5.736 / -5.331 | -6.027 / -7.392 | -6.303 / -7.646 | +0.190 / -1.422 |

## Absolute examples with full retained range

These examples retain the same metric boundaries used above. The complete tables supply every other absolute role/metric distribution. Each value is median [min, max] in milliseconds.

| Case / metric | Cohort | B ms | K4 ms |
|---|---:|---:|---:|
| dense_and / sql_execution_ms | 0 | 86.2650 [83.0790, 96.1290] | 84.7925 [82.8620, 90.4730] |
| dense_and / sql_execution_ms | 1 | 108.7460 [88.3870, 115.5020] | 112.7675 [86.9190, 166.4530] |
| seq_control / sql_execution_ms | 0 | 61.3065 [58.9770, 62.5370] | 58.5350 [54.8040, 60.3700] |
| seq_control / sql_execution_ms | 1 | 62.9915 [61.7490, 64.8720] | 59.5445 [58.1260, 61.4530] |
| skew127 / sql_execution_ms | 0 | 139.1260 [138.6620, 140.0630] | 136.8465 [136.4320, 138.0050] |
| skew127 / sql_execution_ms | 1 | 164.7825 [141.4080, 197.4640] | 144.3560 [138.2130, 195.6160] |
| or_forced / sql_execution_ms | 0 | 153.2770 [151.8400, 154.7230] | 145.5720 [143.8400, 149.6000] |
| or_forced / sql_execution_ms | 1 | 166.2555 [154.2990, 195.4650] | 151.0440 [144.1520, 176.9520] |
| skew1000 / sql_execution_ms | 0 | 76.6315 [76.2290, 76.9480] | 76.7885 [76.4270, 77.7480] |
| skew1000 / sql_execution_ms | 1 | 79.4715 [76.2990, 89.5130] | 78.3100 [76.2610, 93.6420] |
| separate_keys / sql_execution_ms | 0 | 77.8300 [76.4040, 78.4120] | 77.4815 [76.1770, 78.5600] |
| separate_keys / sql_execution_ms | 1 | 80.2605 [76.6330, 91.6230] | 78.9475 [76.8590, 94.2890] |
| absent / sql_execution_ms | 0 | 1.2825 [1.2620, 1.3460] | 1.2780 [1.2630, 1.3420] |
| absent / sql_execution_ms | 1 | 1.1755 [1.1580, 1.2240] | 1.1775 [1.1670, 1.1900] |
| am_or / am_loop_cpu_ms | 0 | 110.9499 [110.3932, 112.2176] | 96.8059 [95.6351, 97.8878] |
| am_or / am_loop_cpu_ms | 1 | 110.1563 [110.0990, 110.6445] | 95.2387 [95.1119, 95.5334] |
| am_dense / am_loop_cpu_ms | 0 | 43.6061 [43.3998, 44.3910] | 43.6221 [43.5165, 44.3984] |
| am_dense / am_loop_cpu_ms | 1 | 43.6631 [43.4880, 43.8578] | 43.4571 [43.3266, 43.5976] |
| am_absent / am_loop_cpu_ms | 0 | 54.6584 [54.6032, 56.0737] | 54.8233 [54.7515, 55.0160] |
| am_absent / am_loop_cpu_ms | 1 | 54.9680 [54.3598, 55.3324] | 54.7943 [54.3005, 55.2027] |

The separately reported R2 keeps the complete unchanged screen and fresh data/socket namespace and reports its own positive, negative and control outcomes. This r1 diagnostic remains published alongside it even if the repeat disagrees. No final speed claim, cache-line attribution, allocator explanation or control-adjusted estimate is made here.
