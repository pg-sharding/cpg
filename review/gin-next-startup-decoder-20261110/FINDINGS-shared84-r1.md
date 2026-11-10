# Completed S1/D1 screen: shared-load diagnostic

All 4920 observations passed the fixed protocol and independent reconstruction: 4100 retained and 820 warm, 1300 absolute groups, 2600 pair groups and 26000 direct same-round pairs. The independent audit compared 188500 numeric values (largest floating-point difference 1.14e-13). Every warm observation, literal, intended plan/loop count, actual-AM total and generated decoder checksum was checked.

S1 has a useful targeted absent-path observation, but its positive inline path regresses. D1 improves the intended one-byte decoder series but substantially regresses long-delta decoding. Neither prototype is recommended for general adoption from this screen. The complete alternatives and all negative results remain available; no tuning, filtering or repeat was performed after seeing these outcomes.

VM84 is a shared-load diagnostic, not a clean-host confirmation: host load was about 11.1 before and 12.0 after on eight guest CPUs. Server/client CPUs were 0/4 then 4/0 (recorded as different guest cores); guest labels do not prove independent physical resources. Retained backend I/O bytes were zero, but queue time was 7.864/7.113 seconds total and unchanged paths moved. That does not explain or remove any candidate difference.

S1 absent whole-command CPU changed −72.27%/−70.30% versus B; its actual-AM inner CPU changed −90.78%/−90.82%. In contrast, actual-AM inline whole CPU changed +22.25%/+24.22% and SQL inline executor time +13.01%/+9.18%. These match the anticipated extra lookup cost as a hypothesis, not a profile-proved attribution.

D1 allocation/materialization/free CPU changed −12.87%/−13.34% for dense128, −17.57%/−14.97% for dense_multi, and −5.28%/−5.34% for batch4. Long-delta negatives were large: delta2 +38.60%/+41.31%, delta3 +18.80%/+18.78%, and delta4 +19.03%/+18.44%. T/B paired medians were close to zero for these three negative cells; all direct ranges remain below. Short scalar tails also fail to show a general win.

D1 full-read actual-AM inner CPU was −0.59%/−0.88%, OR −1.04%/−2.49%, and dense −0.32%/−0.80%. Whole SQL OR CPU was −4.58%/+0.85% and dense −1.20%/+1.98%. These are separate metric boundaries and mixed SQL observations. This matrix does not contain D1+C9 and does not establish a decoder gain on C9; its requested full-read/OR/dense profile remains a separate future stage.

Controls matter: unchanged Seq whole CPU T/B was −4.61%/−3.12%, S1/B +2.78%/+11.86%, D1/B −6.18%/+0.42%. S1 leaves the decoder source unchanged, yet delta3 inner CPU moved −9.39%/−9.35%. Code placement/shared load and other effects are not isolated; no causal claim is made. The exact twin is reported and never used to normalize results.

Below, absolute medians are milliseconds per fixed command; ratio figures are the median of ten same-round right/B percentages. A median ratio need not equal the ratio of two absolute medians. Cohorts are never pooled. All-role absolute min/median/max/stdev/MAD and all ten pair ranges appear in BENCHMARKS-shared84-r1.md; raw/difference arrays are retained in analysis JSON.

## Cohort 0: every SQL and actual-AM cell, whole-command CPU

| Cell | B median ms | S1 median ms | S1/B % | D1 median ms | D1/B % | T/B % | C9/B % |
|---|---:|---:|---:|---:|---:|---:|---:|
| skew1000 | 116.983 | 114.665 | -2.275 | 110.764 | -5.482 | -0.283 | -71.453 |
| skew127 | 223.493 | 219.639 | -1.723 | 216.149 | -3.346 | -0.454 | -23.031 |
| dense_and | 136.496 | 136.596 | 0.972 | 134.091 | -1.201 | 2.762 | -2.843 |
| or_forced | 246.308 | 243.411 | -0.893 | 239.186 | -4.583 | -1.270 | -2.494 |
| single_forced | 228.117 | 230.733 | 0.745 | 228.322 | -0.265 | 0.290 | -1.134 |
| single_rare | 10.813 | 10.881 | 0.694 | 10.906 | 0.853 | 0.798 | -1.863 |
| inline | 0.935 | 1.042 | 10.247 | 0.948 | 0.662 | 1.119 | -3.471 |
| prefix | 161.185 | 158.431 | -1.690 | 162.776 | 0.810 | -0.170 | -0.850 |
| phrase | 118.137 | 116.630 | -1.190 | 111.797 | -4.944 | 0.319 | -69.916 |
| not | 56.459 | 55.559 | -1.734 | 54.374 | -3.745 | 0.042 | -63.708 |
| jsonb | 229.186 | 221.793 | -2.195 | 216.708 | -5.343 | 0.158 | -73.583 |
| lossy_and | 232.147 | 231.250 | -2.421 | 235.940 | -1.476 | 0.927 | -2.779 |
| seq_control | 81.590 | 83.531 | 2.776 | 74.494 | -6.183 | -4.607 | 1.143 |
| skew_group4096 | 92.206 | 91.841 | -0.018 | 87.741 | -5.360 | 0.004 | -86.830 |
| inline_single | 5.139 | 5.063 | -1.045 | 5.034 | -2.481 | -1.065 | -2.320 |
| absent | 2.529 | 0.714 | -72.271 | 2.255 | -11.313 | -1.346 | -68.445 |
| am_inline | 31.103 | 38.056 | 22.249 | 30.319 | -2.149 | -0.483 | -15.115 |
| am_absent | 98.505 | 9.250 | -90.666 | 84.038 | -15.000 | -0.552 | -86.902 |
| am_skew1000 | 107.909 | 111.114 | 1.094 | 101.117 | -5.934 | -0.509 | -78.024 |
| am_full | 161.544 | 162.221 | 0.205 | 161.766 | -0.560 | 0.609 | -3.228 |
| am_or | 186.876 | 186.207 | -2.915 | 187.756 | -1.028 | -0.948 | -3.866 |
| am_dense | 71.578 | 70.960 | 0.122 | 70.849 | -0.321 | 0.026 | -5.101 |
| am_rare | 18.829 | 18.796 | -0.035 | 18.856 | 0.224 | -0.052 | -3.963 |

## Cohort 0: every decoder cell, allocation/materialization/free CPU

| Cell | B median ms | D1 median ms | D1/B median % | direct min % | direct max % | T/B median % | unchanged-decoder S1/B % | C9/B % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| decode_one | 2.782 | 2.819 | 0.179 | -1.343 | 12.771 | 0.509 | 3.901 | 2.847 |
| decode_tail1 | 3.068 | 3.147 | 2.881 | -1.895 | 43.342 | 0.328 | 1.602 | 1.557 |
| decode_tail2 | 3.650 | 3.635 | 4.628 | -10.675 | 16.472 | -0.197 | 0.284 | 1.021 |
| decode_tail3 | 4.131 | 4.109 | 2.406 | -6.059 | 10.544 | -0.133 | 0.142 | 0.514 |
| decode_batch4 | 4.044 | 3.831 | -5.278 | -9.171 | -4.804 | -0.103 | 1.448 | 1.076 |
| decode_batch5 | 4.375 | 5.002 | 1.825 | -4.362 | 14.830 | 0.215 | 1.809 | 1.751 |
| decode_batch8 | 5.386 | 4.959 | -8.033 | -15.725 | -7.403 | -0.122 | 1.341 | 1.574 |
| decode_dense128 | 4.706 | 4.089 | -12.874 | -14.245 | -11.542 | 0.075 | -0.586 | -0.240 |
| decode_dense4096 | 16.077 | 14.541 | -11.050 | -28.220 | 7.518 | -0.155 | -0.413 | -0.434 |
| decode_dense_multi | 8.815 | 7.243 | -17.567 | -19.285 | -15.002 | 0.034 | -5.961 | 5.486 |
| decode_first_singleton_grow | 10.663 | 9.187 | -13.681 | -22.808 | 0.518 | -0.231 | -4.275 | 0.007 |
| decode_singletons | 5.381 | 5.421 | 1.022 | -4.532 | 4.318 | -0.376 | -0.282 | -0.297 |
| decode_delta2 | 6.274 | 9.203 | 38.602 | 28.481 | 65.590 | -0.657 | -0.591 | 0.094 |
| decode_delta3 | 7.863 | 9.458 | 18.805 | 18.135 | 26.585 | 0.083 | -9.386 | 0.087 |
| decode_delta4 | 9.322 | 11.104 | 19.032 | 17.408 | 19.897 | -0.212 | -5.967 | 0.007 |
| decode_delta5 | 11.967 | 12.479 | 4.826 | 0.718 | 25.009 | -0.096 | -7.753 | -0.100 |
| decode_delta6 | 14.591 | 16.591 | 14.556 | -2.124 | 22.981 | 0.104 | -1.665 | 0.241 |
| decode_delta7 | 3.899 | 3.940 | 0.006 | -4.682 | 7.141 | -0.025 | -1.466 | 2.541 |

## Cohort 1: every SQL and actual-AM cell, whole-command CPU

| Cell | B median ms | S1 median ms | S1/B % | D1 median ms | D1/B % | T/B % | C9/B % |
|---|---:|---:|---:|---:|---:|---:|---:|
| skew1000 | 118.019 | 120.272 | -0.537 | 116.955 | -2.768 | 0.212 | -71.363 |
| skew127 | 218.867 | 217.671 | -0.167 | 215.329 | -1.622 | -0.193 | -20.750 |
| dense_and | 133.712 | 137.621 | 3.177 | 136.224 | 1.983 | 0.369 | 0.346 |
| or_forced | 240.537 | 241.524 | 1.110 | 241.812 | 0.848 | -0.826 | -1.392 |
| single_forced | 223.866 | 227.990 | 2.501 | 226.796 | 2.452 | -0.124 | -0.145 |
| single_rare | 10.729 | 10.715 | -1.601 | 10.846 | -1.179 | -0.462 | -2.046 |
| inline | 1.011 | 1.067 | 3.344 | 1.006 | -1.469 | -0.526 | -3.463 |
| prefix | 158.669 | 157.711 | -0.628 | 163.427 | 2.089 | 0.974 | -0.065 |
| phrase | 117.404 | 115.139 | -1.519 | 110.919 | -5.475 | -1.963 | -70.517 |
| not | 55.883 | 54.482 | -2.317 | 54.940 | -3.001 | 0.590 | -63.408 |
| jsonb | 227.478 | 224.504 | -2.414 | 213.138 | -5.313 | -1.488 | -72.873 |
| lossy_and | 223.945 | 225.715 | -0.124 | 234.511 | 1.024 | -3.273 | -0.670 |
| seq_control | 76.559 | 85.383 | 11.856 | 78.217 | 0.416 | -3.119 | 5.167 |
| skew_group4096 | 85.776 | 84.312 | -1.420 | 80.832 | -5.923 | 0.024 | -86.246 |
| inline_single | 4.979 | 4.925 | -1.038 | 4.928 | -0.469 | -1.094 | -0.833 |
| absent | 2.265 | 0.680 | -70.304 | 1.987 | -12.678 | -0.648 | -66.581 |
| am_inline | 30.863 | 38.440 | 24.224 | 30.519 | -1.139 | 0.088 | -14.540 |
| am_absent | 97.321 | 9.195 | -90.697 | 84.683 | -14.416 | -0.134 | -86.697 |
| am_skew1000 | 114.558 | 113.700 | -0.901 | 109.009 | -6.006 | -1.101 | -78.416 |
| am_full | 162.734 | 162.894 | 0.417 | 161.502 | -0.898 | -0.274 | -3.982 |
| am_or | 191.875 | 188.926 | -1.543 | 186.104 | -2.485 | -1.859 | -3.534 |
| am_dense | 71.075 | 71.045 | -0.048 | 70.553 | -0.785 | -0.037 | -5.522 |
| am_rare | 18.544 | 18.607 | 0.250 | 18.484 | -0.238 | 0.014 | -3.794 |

## Cohort 1: every decoder cell, allocation/materialization/free CPU

| Cell | B median ms | D1 median ms | D1/B median % | direct min % | direct max % | T/B median % | unchanged-decoder S1/B % | C9/B % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| decode_one | 2.959 | 2.927 | 0.437 | -9.190 | 10.617 | -0.109 | 0.514 | 0.653 |
| decode_tail1 | 3.223 | 3.143 | 2.239 | -11.830 | 8.175 | 0.103 | 0.995 | 0.978 |
| decode_tail2 | 3.566 | 3.582 | 4.371 | -7.530 | 7.421 | -0.186 | 0.980 | 2.096 |
| decode_tail3 | 3.754 | 4.361 | 6.750 | 2.020 | 39.880 | 0.093 | 1.598 | 2.121 |
| decode_batch4 | 3.914 | 3.709 | -5.340 | -5.997 | -4.485 | 0.001 | 1.345 | 1.347 |
| decode_batch5 | 4.234 | 4.170 | -1.371 | -2.811 | -0.757 | 0.018 | 1.815 | 1.784 |
| decode_batch8 | 5.417 | 4.993 | -7.857 | -8.637 | -5.076 | 0.277 | 1.614 | 1.609 |
| decode_dense128 | 4.888 | 4.164 | -13.342 | -17.266 | -5.771 | 0.105 | -0.086 | 0.371 |
| decode_dense4096 | 14.434 | 12.854 | -12.872 | -23.530 | 5.349 | 0.980 | -0.501 | -0.393 |
| decode_dense_multi | 9.644 | 7.893 | -14.966 | -24.099 | -13.102 | -0.232 | -0.529 | -5.510 |
| decode_first_singleton_grow | 8.795 | 7.374 | -15.795 | -24.896 | -2.962 | 0.072 | -6.567 | -4.081 |
| decode_singletons | 5.386 | 5.489 | 1.917 | 0.492 | 2.785 | 2.145 | -0.378 | -1.206 |
| decode_delta2 | 6.112 | 9.995 | 41.306 | 36.281 | 64.758 | 0.041 | -0.474 | 0.552 |
| decode_delta3 | 7.997 | 9.483 | 18.776 | 17.806 | 19.542 | 0.144 | -9.351 | -0.186 |
| decode_delta4 | 9.390 | 11.125 | 18.435 | 9.913 | 37.653 | -0.064 | -6.147 | -0.049 |
| decode_delta5 | 12.559 | 14.330 | 14.751 | 2.230 | 24.749 | -0.038 | -7.469 | 0.099 |
| decode_delta6 | 14.141 | 14.791 | 3.159 | 1.565 | 20.291 | -0.034 | -6.288 | 0.408 |
| decode_delta7 | 4.077 | 4.221 | 3.239 | -3.911 | 9.933 | 0.905 | -1.105 | 1.123 |

## Provenance, prior work and next steps

The six matched full builds and unchanged core239/posting-list checks passed before timing; all 40 ordinary SQL cases, seven repeated prepared cases, 12 lifecycle comparisons and 18 actual decoder vectors passed per variant. Full native prototype/callback-count proofs for the separate K1 direction are included as untimed evidence, not K1 performance results. Main and smoke cleanup stopped 10+5 own clusters; complete frozen/source/installed-tree checks passed. Root final live checks remain a separate receipt.

Canonical root-authored S1 832af7d60b9d4c69a5f922dd1522a917bf337761 and D1 c2b5dd6f9012cc4a27628c9d6c507ac467795ac5 have identical trees and diff bytes to historical build commits; SOURCE-IDENTITY-CORRECTION-r1.json records the map. SOURCE-PUBLICATION-r1.json records the verified isolated public branches. Historical build receipts are unchanged.

CF7352 output-array sizing is direct prior art and deliberately excluded from D1. The already-unrolled scalar per-integer codec is baseline behavior. Heikki 2014 explicitly precedes result caching/deferred segments. Retained archive metadata and decoded inert allocation attachment establish the references; no new novelty search is claimed.

No clean-host speedup claim or production recommendation follows. A later attempt would need separately frozen source, negative controls and clean-host confirmation; this wave is complete without source/threshold changes. K1 is a separate bounded builtin-only memo, pending full-backend qualification and a separately reviewed three-role campaign.
