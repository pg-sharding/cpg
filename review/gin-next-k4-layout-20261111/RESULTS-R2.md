# K4 r2 — complete unchanged repeat, bounded interpretation

**The compact layout is functionally qualified, but this screen does not establish a general performance improvement or identify a cause of earlier dense overhead.** R2 repeats every fixed case and preserves every sample. Incremental K4/K3 differences are generally much smaller than the conspicuous K4/B reductions, while exact-twin and off-path controls still move. We retain those findings without control normalization, trimming, significance claims or cache-line/allocator/instruction-placement attribution.

R1 remains a separate complete shared-load diagnostic. Its repeat decision was saved before inspecting accepted-run timing values, after smoke correctness review. R2 used fresh R/r2/timing-r2 copies and R/r2/s sockets, ports 47300+, the same source/build/qualification and seed bindings, all 24 cases, five roles, two warm plus ten retained rounds, and CPU pairs 0:4 then 4:0. No source, schedule, loop count or acceptance threshold was tuned to r1 outcomes. Both r2 cohorts passed: 2880 raw / 2400 retained / 480 warm, plus separate 120-command smoke.

The full independent peer recount passed all 114550 numerical fields, exact 395-absolute/790-pair key sets per cohort, all 2040 SQL plans and 840 AM results, expected GUCs and monotonic literal/measurement chronology. All 17 expanded semantic/actual signatures match r1, including rows/loops, index searches and recheck/lossy conditions. The final stored live proof records 21 stopped lifetimes and unchanged source/prefix/seed/input/module bindings. Root's actual root auditor also passed; the independent peer reads raw directly without importing its protocol or validator. These checks do not prove a particular performance cause.

R2's monitor recorded 100 five-second samples, began before the campaign run-status start and finished after its completed status. Sampled one-minute load ranged from 0.1704 to 1.1870. No go/pool.test name appears in the recorded consumers. Editor/services and other background names still appear at low sampled rates; Python/PostgreSQL activity includes the owned harness. The monitor observes only endpoint deltas and top 20 consumers, not all short-lived tasks, thread placement, frequency/steal time or exact command overlap. We therefore describe a quieter recorded repeat window, not an interference-free host. R1 and r2 are never pooled or averaged together.

The controls remain material. Seq_control uses no GIN, yet K4/B whole-SQL executor time changes −2.428% / +1.250%; its C/B is +5.938% / +2.583%. Prefix's exact-twin T/B is −0.576% / +7.240%. In cohort 1, actual-AM OR T/B is −6.506% and dense T/B is −6.175%, despite identical prefix/ELF and matching answers/plans. These observations prevent interpreting every candidate-versus-B reduction as a memo/layout effect. They are not subtracted from any reported percentage, and no sample is removed.

On the intended skew path, K4/K3 whole-SQL executor differences are +0.178% / −0.134% for skew1000 and +0.447% / −0.389% for separate_keys. K4/B is −0.517% / −0.318% and −0.383% / −0.180%, respectively; exact T/B is −0.453% / −0.209% and −0.468% / −0.139%. C/B is positive in both cases/cohorts. Thus K4/C reductions of about 2% are not equivalent to a 2% reduction over the original baseline, and the screen does not show a consistent incremental gain over K3 on these SQL batches.

Dense-and SQL K4/K3 is −0.382% / −1.821%, with direct-pair ranges [−14.344%, +5.992%] and [−4.975%, +0.288%]. K4/B is +0.090% / −1.247%, while T/B is +2.249% / −0.611%. Actual-AM dense inner CPU K4/K3 is −1.162% / −1.716%; K4/B is −0.669% / −5.814%, and the cohort-1 T/B drift is itself −6.175%. The actual-AM work and full executor command have different boundaries. This does not establish that the reorder fixes dense overhead.

Forced-OR SQL K4/B is −4.744% / −5.122%, but K3/B is already −4.598% / −4.698%; the incremental K4/K3 is −0.456% / −0.238%. Actual-AM OR inner CPU K4/B is −13.847% / −19.054%, versus K3/B −13.231% / −18.479% and K4/K3 −0.701% / −0.616%. Actual-AM full and rare also retain negative K4/B values, with much smaller K4/K3 differences. The larger headline percentages cannot be assigned to the new layout; the exact-twin movement further limits attribution.

The layout-only control C is not a uniformly better baseline. For absent SQL, C/B is +4.391% / +9.259%; K4/C is −3.664% / −6.980%, while K4/B is only −0.193% / +0.347%. Actual-AM absent C/B is +5.234% / +5.112%; K4/C is −4.727% / −4.669%, while K4/B is +0.378% / +0.208%. Other negative incremental results include NOT SQL K4/K3 +0.281% / +0.337%, prefix +0.426% / +0.156%, and seq_control +0.531% / +1.819%. Single-rare K4/K3 changes sign (+1.126% / −5.184%). All controls and negatives remain in the tables.

The complete [absolute/spread tables](RESULTS-R2-TABLES.md) contain all 79 metrics per role/cohort, all five absolute distributions and six displayed comparisons. Analyzer JSON retains every raw-derived value, mean/stdev/MAD, absolute differences, direct arrays and all ten role pairs. Backend CPU/client wall refer to whole commands; SQL executor includes the complete fixed probe batch; AM CPU/wall refer to the actual inner rescan/getbitmap/tbm batch. They are not interchangeable and are not single-probe latencies.

Below, each cell is cohort 0 / cohort 1 median of ten direct round percentages, 100 × (candidate/reference − 1); negative is lower time. The SQL table uses whole-command executor time and the AM table uses inner-loop CPU. Percentages are not ratios of absolute medians.


## sql / sql_execution_ms

| Case | C/B c0 / c1 | K4/K3 c0 / c1 | K4/C c0 / c1 | K3/B c0 / c1 | K4/B c0 / c1 | T/B c0 / c1 |
|---|---:|---:|---:|---:|---:|---:|
| skew1000 | +1.503 / +2.296 | +0.178 / -0.134 | -2.110 / -2.469 | -0.554 / -0.156 | -0.517 / -0.318 | -0.453 / -0.209 |
| skew127 | +0.579 / +2.766 | +0.608 / -1.130 | -2.136 / -4.328 | -2.287 / -0.627 | -1.633 / -1.715 | -0.834 / -0.384 |
| separate_keys | +1.473 / +2.198 | +0.447 / -0.389 | -1.907 / -2.390 | -0.786 / +0.136 | -0.383 / -0.180 | -0.468 / -0.139 |
| dense_and | +1.029 / +4.628 | -0.382 / -1.821 | -2.058 / -6.452 | +0.726 / +0.192 | +0.090 / -1.247 | +2.249 / -0.611 |
| or_forced | +1.455 / +4.762 | -0.456 / -0.238 | -5.954 / -9.134 | -4.598 / -4.698 | -4.744 / -5.122 | -0.309 / -0.566 |
| single_forced | +1.674 / +5.674 | -0.029 / -0.309 | -3.911 / -7.521 | -2.269 / -2.233 | -2.081 / -2.548 | -0.516 / -0.662 |
| single_rare | -0.099 / +3.257 | +1.126 / -5.184 | -1.204 / -5.813 | -1.863 / +2.519 | -1.023 / -2.592 | -0.564 / -0.938 |
| inline | +0.350 / +1.283 | +0.094 / -1.571 | -0.579 / -0.220 | -0.107 / +1.380 | -0.002 / -0.254 | -3.670 / -1.922 |
| prefix | -0.508 / -0.127 | +0.426 / +0.156 | -0.217 / -0.302 | -0.881 / -0.547 | -0.766 / -0.417 | -0.576 / +7.240 |
| phrase | +1.804 / +1.989 | +0.118 / -0.382 | -2.370 / -2.602 | -0.651 / -0.223 | -0.643 / -0.697 | +0.322 / -0.283 |
| not | +2.083 / +2.583 | +0.281 / +0.337 | -2.589 / -2.728 | -0.854 / -0.458 | -0.652 / -0.158 | -0.287 / -0.025 |
| jsonb | +1.959 / +2.101 | +0.066 / -0.204 | -1.944 / -2.021 | -0.088 / +0.173 | -0.096 / -0.061 | -0.110 / -0.242 |
| lossy_and | +0.098 / +1.466 | -1.391 / -1.759 | -1.014 / -1.112 | +0.839 / +2.270 | -0.703 / +0.331 | +0.044 / +0.274 |
| seq_control | +5.938 / +2.583 | +0.531 / +1.819 | -6.431 / -1.172 | -3.445 / -0.428 | -2.428 / +1.250 | -1.120 / +0.079 |
| skew_group4096 | +1.568 / +2.273 | +0.511 / +0.012 | -1.721 / -1.623 | -0.603 / +0.547 | -0.012 / +0.457 | -0.223 / +0.053 |
| inline_single | +0.000 / +8.569 | -0.036 / -1.272 | -2.767 / -10.205 | -2.858 / -0.909 | -2.432 / -2.841 | -0.476 / +1.300 |
| absent | +4.391 / +9.259 | +0.311 / -0.259 | -3.664 / -6.980 | -0.502 / +0.302 | -0.193 / +0.347 | -0.039 / +0.348 |

## am / am_loop_cpu_ms

| Case | C/B c0 / c1 | K4/K3 c0 / c1 | K4/C c0 / c1 | K3/B c0 / c1 | K4/B c0 / c1 | T/B c0 / c1 |
|---|---:|---:|---:|---:|---:|---:|
| am_inline | +0.794 / +1.519 | -0.400 / +0.515 | -1.361 / -1.552 | -0.355 / -0.545 | -0.741 / -0.072 | +0.022 / +0.105 |
| am_absent | +5.234 / +5.112 | +0.182 / -0.289 | -4.727 / -4.669 | +0.267 / +0.485 | +0.378 / +0.208 | +0.417 / -0.111 |
| am_skew1000 | +1.903 / +1.876 | +0.133 / +0.246 | -2.250 / -1.896 | -0.347 / -0.326 | -0.273 / -0.047 | -0.163 / -0.013 |
| am_full | +1.497 / +0.410 | -0.073 / -0.428 | -8.330 / -7.013 | -6.949 / -6.288 | -6.951 / -6.669 | -0.284 / +0.157 |
| am_or | +1.422 / -5.884 | -0.701 / -0.616 | -15.053 / -13.921 | -13.231 / -18.479 | -13.847 / -19.054 | +0.074 / -6.506 |
| am_dense | +1.008 / -5.434 | -1.162 / -1.716 | -1.486 / -0.362 | +0.398 / -4.143 | -0.669 / -5.814 | -0.187 / -6.175 |
| am_rare | +0.005 / -1.773 | -0.378 / -0.524 | -5.870 / -5.112 | -6.081 / -6.265 | -6.017 / -6.767 | -0.139 / -0.421 |


## Absolute examples and retained range

Each entry is median [min, max] in milliseconds; every other role/metric is in the complete tables.

| Case / metric | Cohort | B ms | K4 ms |
|---|---:|---:|---:|
| seq_control / sql_execution_ms | 0 | 60.9760 [58.6910, 62.5010] | 58.9510 [57.0080, 61.1470] |
| seq_control / sql_execution_ms | 1 | 57.5240 [56.9780, 62.1690] | 58.4550 [56.7500, 60.4700] |
| prefix / sql_execution_ms | 0 | 92.3640 [92.1450, 92.9260] | 91.7400 [91.5440, 92.7210] |
| prefix / sql_execution_ms | 1 | 91.8760 [91.7330, 92.2580] | 91.5155 [91.3780, 91.8610] |
| skew1000 / sql_execution_ms | 0 | 76.7815 [76.5150, 77.7410] | 76.3435 [76.1830, 76.6470] |
| skew1000 / sql_execution_ms | 1 | 76.4920 [76.1450, 76.6380] | 76.2400 [76.1480, 76.4970] |
| separate_keys / sql_execution_ms | 0 | 76.6955 [76.5400, 77.5640] | 76.3875 [76.1740, 76.7350] |
| separate_keys / sql_execution_ms | 1 | 76.4740 [76.3350, 76.6300] | 76.3100 [76.2160, 76.5110] |
| dense_and / sql_execution_ms | 0 | 85.0530 [83.4520, 88.1760] | 83.8805 [82.1890, 89.9090] |
| dense_and / sql_execution_ms | 1 | 84.3245 [82.9150, 87.9340] | 82.9740 [82.2550, 88.4250] |
| or_forced / sql_execution_ms | 0 | 151.7905 [150.8730, 152.5860] | 144.5640 [143.1010, 146.4130] |
| or_forced / sql_execution_ms | 1 | 151.6425 [148.9990, 153.5410] | 144.9805 [142.0730, 148.1650] |
| absent / sql_execution_ms | 0 | 1.2950 [1.2820, 1.3120] | 1.2885 [1.2610, 1.3140] |
| absent / sql_execution_ms | 1 | 1.1545 [1.1480, 1.1960] | 1.1575 [1.1520, 1.3670] |
| am_or / am_loop_cpu_ms | 0 | 110.7781 [110.6629, 111.6540] | 95.3859 [95.2576, 96.6372] |
| am_or / am_loop_cpu_ms | 1 | 118.0889 [117.9863, 118.2771] | 95.6320 [95.5023, 95.8377] |
| am_dense / am_loop_cpu_ms | 0 | 44.2168 [43.6253, 44.6431] | 43.7410 [43.6203, 44.4635] |
| am_dense / am_loop_cpu_ms | 1 | 46.4436 [46.4216, 46.6425] | 43.7489 [43.7248, 44.3140] |
| am_absent / am_loop_cpu_ms | 0 | 54.7541 [54.7340, 55.2690] | 54.9872 [54.8921, 55.2840] |
| am_absent / am_loop_cpu_ms | 1 | 54.1916 [54.1291, 54.2472] | 54.2842 [54.2310, 54.4181] |

The concrete result is a verified C/K4 source/layout control and a complete reproducible comparison with unresolved variation. Advancing the reorder as a broad optimization is not supported by these two attempts. A subsequent experiment should first explain or bound identical-binary placement variation under a prospectively fixed design; this packet neither promises that another source rewrite will win nor claims a causal explanation from these timings.
