# Actual matched IOS V14 outcome

V14 is not a general V13 upgrade. Mixed-scan CPU point estimates improve modestly, but short postings and some LIMIT/control cells worsen. Large wide-posting wins versus B/T remain. Every range and negative is retained; no significance or source-causal explanation is assigned.

CPU milliseconds below are median[min,max] over all12retained samples; percentages are medians of per-round ratios, not ratios of displayed medians. B/T use the same B ELF.

## Cohort 0

| Case | B CPU ms | T CPU ms | V13 CPU ms | V14 CPU ms | V14/B % | V14/T % | V14/V13 % |
|---|---:|---:|---:|---:|---:|---:|---:|
| f2_p2_count | 92.564 [89.602, 93.484] | 91.098 [86.190, 92.343] | 88.141 [87.078, 88.958] | 88.539 [84.562, 90.920] | -3.97 | -2.71 | +0.55 |
| f3_p2_count | 94.687 [91.076, 95.336] | 93.638 [89.557, 95.362] | 90.251 [87.105, 90.958] | 90.683 [87.852, 92.280] | -3.87 | -3.54 | +0.56 |
| f4_p2_count | 95.418 [91.785, 100.546] | 94.201 [90.695, 100.034] | 90.082 [87.269, 93.050] | 90.415 [87.987, 93.381] | -5.07 | -3.63 | +0.27 |
| limit1_from_long | 49.647 [44.558, 52.759] | 49.891 [43.498, 51.874] | 50.578 [46.420, 53.767] | 49.819 [46.990, 52.168] | -0.28 | +0.97 | -0.45 |
| limit2_from_long | 51.041 [48.671, 55.546] | 51.963 [47.565, 54.790] | 53.144 [46.072, 55.039] | 52.612 [48.956, 56.055] | +1.25 | +2.79 | +0.66 |
| heap_f4_count | 291.460 [242.925, 325.906] | 301.482 [246.484, 319.106] | 268.590 [251.058, 303.284] | 255.422 [238.800, 280.578] | -13.15 | -13.80 | -6.43 |
| w8_long_count | 116.019 [111.977, 119.034] | 119.269 [115.279, 120.241] | 84.713 [81.499, 85.890] | 85.360 [81.908, 86.335] | -27.06 | -28.73 | +0.67 |
| w8_long_tail | 124.896 [118.871, 126.112] | 127.350 [122.426, 128.923] | 91.477 [89.148, 92.808] | 93.190 [90.199, 93.319] | -25.36 | -27.19 | +0.59 |
| f32_long_count | 29.917 [28.819, 30.380] | 29.574 [28.881, 30.353] | 16.271 [15.623, 16.491] | 16.369 [15.784, 16.617] | -45.43 | -45.43 | +0.74 |
| w32_long_tail | 44.463 [43.139, 45.931] | 44.645 [43.045, 45.584] | 19.908 [19.155, 20.170] | 19.935 [19.301, 20.120] | -55.43 | -55.33 | +0.46 |
| one_bigint_long_count | 83.181 [80.181, 84.262] | 80.390 [77.005, 82.378] | 79.940 [76.727, 82.505] | 79.742 [77.483, 81.729] | -4.26 | -0.80 | -0.32 |
| one_bigint_singleton_count | 103.648 [99.899, 104.056] | 99.251 [98.716, 103.512] | 99.721 [95.772, 102.935] | 100.342 [96.644, 104.216] | -2.50 | +0.85 | +0.57 |
| seq_control | 68.945 [68.449, 71.835] | 69.585 [67.486, 71.661] | 70.668 [67.830, 72.337] | 68.841 [67.750, 71.063] | -0.64 | -0.45 | -0.89 |
| regular_heap_index_control | 61.352 [59.222, 61.758] | 60.524 [56.831, 60.771] | 59.909 [57.974, 60.621] | 59.953 [56.760, 60.681] | -2.21 | -0.73 | -0.12 |
| mixed2_count | 54.266 [52.197, 54.906] | 51.887 [49.986, 53.984] | 53.251 [51.287, 54.689] | 52.702 [50.860, 54.080] | -2.83 | +1.25 | -1.06 |
| mixed64_count | 74.125 [72.188, 75.290] | 72.824 [70.450, 75.101] | 70.864 [69.016, 73.180] | 71.219 [69.228, 72.401] | -4.30 | -2.63 | -0.59 |
| backward_mixed2_sum | 56.125 [54.050, 56.168] | 56.173 [53.948, 56.504] | 57.116 [54.923, 57.455] | 56.478 [54.300, 56.829] | +0.68 | +0.54 | -1.09 |
| backward_mixed64_sum | 53.436 [51.218, 54.722] | 53.350 [51.381, 54.410] | 52.800 [50.652, 54.017] | 52.374 [50.287, 53.375] | -2.01 | -1.86 | -0.92 |
| backward_f2_p2_sum | 101.544 [98.752, 104.203] | 102.586 [98.225, 104.723] | 100.818 [96.170, 101.916] | 101.953 [98.092, 102.681] | -0.52 | -0.88 | +0.97 |

## Cohort 1

| Case | B CPU ms | T CPU ms | V13 CPU ms | V14 CPU ms | V14/B % | V14/T % | V14/V13 % |
|---|---:|---:|---:|---:|---:|---:|---:|
| f2_p2_count | 88.564 [86.517, 91.011] | 88.937 [86.869, 91.525] | 86.229 [82.951, 87.523] | 87.815 [84.324, 89.162] | -2.49 | -2.39 | +1.68 |
| f3_p2_count | 93.321 [89.441, 96.226] | 92.464 [89.344, 94.204] | 88.454 [85.340, 91.276] | 90.581 [87.514, 91.839] | -3.06 | -2.74 | +1.69 |
| f4_p2_count | 95.672 [92.743, 99.511] | 96.267 [91.606, 98.469] | 90.392 [86.911, 92.100] | 91.077 [88.856, 94.004] | -5.53 | -5.45 | +0.76 |
| limit1_from_long | 48.660 [44.578, 50.396] | 48.449 [45.843, 51.958] | 47.863 [45.078, 50.916] | 48.865 [46.609, 51.743] | +1.62 | +1.48 | +2.09 |
| limit2_from_long | 50.269 [46.214, 53.983] | 48.599 [46.263, 54.246] | 48.427 [47.008, 54.125] | 50.299 [47.875, 54.632] | +1.43 | +2.54 | +3.14 |
| heap_f4_count | 256.972 [242.765, 282.039] | 258.775 [245.336, 271.496] | 236.282 [230.265, 270.047] | 246.911 [230.681, 268.586] | -6.01 | -4.93 | +2.75 |
| w8_long_count | 122.666 [115.767, 129.334] | 117.819 [112.465, 120.248] | 84.598 [81.565, 84.859] | 85.709 [82.283, 86.613] | -30.38 | -27.11 | +1.49 |
| w8_long_tail | 122.764 [121.628, 129.083] | 121.312 [119.046, 125.865] | 90.680 [89.445, 94.171] | 93.359 [91.211, 96.962] | -23.70 | -22.62 | +2.39 |
| f32_long_count | 30.058 [28.939, 30.217] | 30.110 [28.971, 30.590] | 16.575 [15.948, 16.732] | 16.344 [15.968, 16.719] | -44.84 | -44.94 | -0.15 |
| w32_long_tail | 44.472 [42.661, 45.195] | 44.402 [42.612, 45.305] | 20.004 [19.346, 20.297] | 20.035 [19.279, 20.254] | -54.98 | -54.77 | +0.07 |
| one_bigint_long_count | 79.225 [77.384, 82.071] | 79.549 [77.516, 82.136] | 80.514 [77.494, 82.943] | 80.447 [78.195, 81.320] | +0.78 | +0.78 | +0.20 |
| one_bigint_singleton_count | 100.570 [98.346, 104.926] | 100.090 [97.879, 104.790] | 100.821 [95.221, 104.547] | 101.021 [96.804, 105.322] | +0.40 | +0.52 | +0.54 |
| seq_control | 70.191 [67.598, 71.411] | 70.281 [67.716, 71.328] | 71.003 [68.334, 71.871] | 71.410 [68.787, 71.860] | +0.75 | +1.10 | +0.64 |
| regular_heap_index_control | 56.539 [54.194, 59.286] | 56.874 [54.840, 59.662] | 59.333 [55.511, 63.983] | 60.273 [54.669, 65.686] | +5.57 | +6.17 | +2.11 |
| mixed2_count | 52.361 [50.540, 54.455] | 52.932 [50.753, 54.560] | 52.970 [50.953, 55.062] | 52.272 [50.704, 53.317] | +0.14 | -0.48 | -1.36 |
| mixed64_count | 71.301 [68.594, 74.138] | 71.514 [69.590, 74.780] | 69.589 [66.469, 72.095] | 69.402 [66.707, 71.533] | -3.34 | -3.19 | -0.68 |
| backward_mixed2_sum | 56.688 [54.391, 58.108] | 56.605 [54.545, 58.022] | 57.259 [55.580, 58.819] | 56.429 [54.433, 58.207] | -0.15 | -0.24 | -1.97 |
| backward_mixed64_sum | 53.734 [51.739, 54.976] | 52.723 [51.388, 53.831] | 52.604 [51.021, 54.244] | 52.276 [50.518, 53.553] | -2.31 | -1.84 | -1.34 |
| backward_f2_p2_sum | 102.334 [98.809, 104.105] | 103.269 [98.556, 104.810] | 99.854 [97.405, 102.523] | 100.244 [97.486, 102.753] | -1.16 | -1.43 | +0.35 |

## Regressions, controls and interpretation

V14/V13 CPU mixed2 is−1.06%/−1.36%, mixed64−0.59%/−0.68%, backward mixed2−1.09%/−1.97%, backward mixed64−0.92%/−1.34%. Their round ranges largely cross zero; these are modest descriptive point estimates. Short2/3/4 CPU instead costs+0.55%/+1.68%,+0.56%/+1.69%,+0.27%/+0.76% versusV13. Wide8 COUNT/tail are+0.67%/+1.49% and+0.59%/+2.39% versusV13; fixed32 changes+0.74%/−0.15%, wide32tail+0.46%/+0.07%. Thus inherited wide wins against B/T are not a new broad V14-over-V13 gain.

LIMIT1 execution is+3.17%/+5.95% versusB, whereas ownbackendCPU is−0.28%/+1.62%. Cohort1 LIMIT2 execution is+11.48% versusB and+11.60% versusV13; CPU is+1.43%/+3.14%, respectively. Execution and CPU are distinct metrics and must not be interchanged. Full runqueue/clientwall evidence remains in all tables; no explanation is inferred from their divergence.

Controls are material: regular heap IndexScan V14/T CPU is−0.73%/+6.17%; cohort1 V14/B is+5.57% with round range[−2.93%,+16.58%]. SeqScan V14/T is−0.45%/+1.10%. Heap-fetch IOS V14/V13 changes−6.43%/+2.75%; cohort0 V14/B range[−22.60%,+11.49%] and cohort1[−11.42%,+7.21%]. Singleton V14/V13 is+0.57%/+0.54%, with wide per-round ranges. Exact twins are retained as controls, not normalization.

Wide8COUNT CPU V14/B is−27.06%/−30.38%, fixed32−45.43%/−44.84%, wide32tail−55.43%/−54.98%; each also improves versusT. These substantial inherited posting-cache effects coexist with negative short/LIMIT/control cells. No population is pooled across cohorts or earlier V13 experiments.

Exactly176of13680paired metric ratios are undefined because the denominator runqueue time is0:91incohort0,85incohort1,115runqueue groups total. All other metrics have0undefined ratios. All228runqueue pairgroups retain12absolute differences and12raw pairs; defined-ratio n ranges9..12. These are not trimmed observations.

## Completed checks and reproduction

Four fresh fullclean commonpath builds/core239each, original three SQL outputs perrole, actual-header native/cache/slot-ownership gates,76/0smoke, source/ELF/header bindings and17owncluster cleanup all passed. audit-results.py independently reconstructed760absolute groups,1140pairgroups and13680direct pairs, comparing49172numbers with maxerror0; every complete-tree plan matched the reviewed smoke, literal/reference/fixture histories matched retained oracles and retainedrootsharedreads were0. PsqlCPU was recounted as recorded; underlying client schedstat endpoints were not stored, so that counter was not independently re-derived.

NUMERICAL-REPLAY.json records actual whole-line gzip reconstruction of all55collection files and byte-identical original-analyzer summary; no Linux SQL rerun. BENCHMARKS.md and analysis/ preserve all5metrics/all6pairs/all19cases. REPRODUCE.md separates executed build/gate/SQL from historical unexecuted replacement-seed instructions and local packaging checks. Native helpers are correctness gates, not a new native performance campaign. No generic concurrency proof or merge-readiness claim.
