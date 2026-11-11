D2 reduces the D1 multibyte decoder penalty and retains dense-list gains, with residual regressions

This completed finite screen supports D2 as a useful revision of the D1 prototype, with a measured tradeoff. For the actual allocation-inclusive backend decoder, delta2 changes from D1/B +37.86/+38.11% to D2/B +4.52/+5.12% in cohorts 0/1; D2/D1 is -24.04/-24.08%. Dense128 remains faster than B by -10.71/-10.80%, while D2 is +3.35/+3.08% slower than D1 there. Delta3 and delta4 still cost +7.40/+6.81% and +6.21/+5.49% versus B. This is not a general upgrade recommendation.

These are fresh matched B/T/D1/D2 observations on one VM158 host. Historical D1 reports of roughly 39–41% delta2 regression motivated this run; those earlier reports are not pooled with, or treated as a matched baseline for, these results. B is fixed B 8a8c475037bfde101da23cc9b0364c9c020eca93. D1 c2b5dd6f9012cc4a27628c9d6c507ac467795ac5 and D2 a85a9242f455b12c93528f3ace33eb69b6cd1008 are independent alternatives. Both share the same prerequisite and do not include startup, advance, OR-heap or cache prototypes. T uses the identical B prefix, postgres ELF and decoder helper.

D2 only moves the first-delta continuation-bit test ahead of D1's four-one-byte-batch checks. Actual normal full-TU assembly confirms that a long first delta bypasses the batch bounds and remaining-byte OR. All normal backend objects outside ginpostinglist.o match B. That code-generation fact does not establish a causal explanation for every timing change. The normal decoder frame is unchanged (six register saves plus 24 local stack bytes); assertion-build objects are excluded from release equality comparisons.

Four fresh full builds passed unchanged core239 and posting-list tests. Qualification passed 72 decoder cases / 52,608 item checks, 188 ordered SQL/prepared digest comparisons and 48 serial lifecycle comparisons. The original expected files, C helper, fixtures and SQL were preserved; historical fixed-B references were checked along with fresh Seq/index comparisons. This is bounded ordinary serial qualification, not a concurrency or general merge proof.

The accepted screen contains 2,800 raw commands: 2,400 retained and 400 warm, after a separate 100-command smoke with zero accepted samples. All 25 cells use two warm and twelve retained four-role Williams rounds in each of two fresh cohorts. The second cohort reverses case and physical copy placement. CPU placements 0:4 then 4:0 use different physical guest cores within a cohort on one host; these are not independent machines. No trimming, repeat, control normalization or pooling was performed. The independent auditor matched 78,000 numerical fields, 600 absolute groups, 900 pair groups and 10,800 direct pairs. All retained samples have zero observed backend read/write bytes and zero minor/major fault deltas; aggregate runqueue time was 26.29/20.32 ms for 33.09/32.90 s backend CPU. These counters describe this warm-cache screen, not a cold-storage result.

Each table percentage is the median of twelve direct right/left round ratios, not the ratio of two absolute medians. All absolute values below are milliseconds per complete command and include [minimum, maximum]. SQL primary values are EXPLAIN Execution Time for all repeated probes: skew1000 100, dense_and 10, OR/single-forced 5, rare/prefix 100, Seq control 5. The Seq ID-only control has no GIN predicate. Native primary values are process CPU for the actual decoder's allocation, materialization and free; compression and the generated-TID oracle are outside that clock. Backend command CPU and client wall are separate metrics in the complete tables/JSON.

SQL skew1000 executor time improves -2.81/-2.46% versus B (76.6900/77.6275 ms to 74.5960/75.7105 ms per 100 probes), while D2/D1 is +0.26/+0.65%. Dense SQL is mixed (+2.25/-0.29%); rare is +0.80/+1.67%; forced single is +0.87/+0.16%; forced OR is +0.30/+0.58%; prefix is +0.02/-0.33%; Seq is +0.58/+1.32%. Seq exact-twin T/B itself is -0.78/+1.32%. These small whole-query changes must be assessed with the full ranges and control behavior, without assigning them all to decoder work.

Other retained negatives include native one +1.40/+1.67%, tail1 +2.02/+4.03%, tail2 +5.71/+5.86%, tail3 +2.71/+2.82%, and delta5 +0.54/+0.40% versus B. Delta7 is near neutral (+0.17/+0.32%). D2 remains slower than D1 on several dense/batch/growth cases. The dense_multi baseline median also shifts from 4.7356 to 6.1097 ms between cohorts, so cohort results are reported separately. Exact-twin observations are retained and do not provide a correction factor.

The complete 18+7 primary table follows. tables/ALL-ABSOLUTE.md and tables/ALL-PAIRS.md retain every metric and pair with ranges, mean, sample stdev and MAD; analysis0-r1 and analysis1-r1 JSON additionally retain every individual value and every direct pair. tables/CONTROLS-AND-NEGATIVES.json enumerates every positive D2/B case median across all metric boundaries, with twin ranges. Positive signs are observations, not significance classifications.

Primary metric for all 25 cells. Decoder = allocation/materialization/free process CPU; SQL = whole-command EXPLAIN execution time. All absolute values are milliseconds per complete command, median [min,max], n=12. Percent columns are medians of direct per-round ratios, not ratios of absolute medians. Positive means slower. Exact B/T is a control, not a correction.

Cohort 0

| Case | B ms | T ms | D1 ms | D2 ms | D1/B % | D2/B % | D2/D1 % | T/B % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| skew1000 | 76.6900 [76.4850, 78.0870] | 76.6470 [76.5010, 77.7430] | 74.4065 [74.1450, 75.9890] | 74.5960 [74.4410, 75.8440] | -3.09 | -2.81 | +0.26 | -0.10 |
| dense_and | 84.0435 [82.5500, 87.6810] | 85.1500 [82.0100, 89.5840] | 83.6240 [81.3960, 91.4020] | 85.1555 [82.2550, 91.6420] | -0.57 | +2.25 | +1.27 | -0.28 |
| or_forced | 151.3785 [149.8150, 154.3980] | 151.2575 [149.9890, 153.3690] | 151.8935 [150.1280, 153.8000] | 151.6325 [150.8550, 153.2360] | -0.05 | +0.30 | -0.09 | -0.14 |
| single_forced | 145.4475 [143.7730, 147.2150] | 145.0125 [143.5670, 148.7210] | 144.4810 [142.8090, 147.7840] | 146.2625 [145.1490, 149.0590] | -0.27 | +0.87 | +1.80 | -0.10 |
| single_rare | 6.0295 [5.9280, 6.2020] | 6.0245 [5.8000, 6.3640] | 5.9440 [5.8760, 6.2300] | 6.0775 [5.9800, 6.2470] | -0.04 | +0.80 | +0.77 | +0.02 |
| prefix | 93.3985 [91.7090, 95.9620] | 92.8690 [91.5960, 94.2340] | 95.7530 [94.1320, 96.0670] | 92.2955 [91.7240, 94.6210] | +2.63 | +0.02 | -2.73 | +0.01 |
| seq_control | 58.1775 [55.9800, 59.8910] | 57.6880 [54.3360, 59.8950] | 59.2035 [57.6100, 61.7910] | 58.6885 [56.2890, 59.8860] | +1.84 | +0.58 | -1.98 | -0.78 |
| decode_one | 1.6429 [1.6319, 1.6823] | 1.6380 [1.6021, 1.6637] | 1.7515 [1.7124, 1.7757] | 1.6656 [1.6548, 1.7000] | +5.82 | +1.40 | -4.42 | -0.77 |
| decode_tail1 | 1.7835 [1.7488, 1.7999] | 1.7398 [1.7059, 1.7579] | 1.8484 [1.8150, 1.9017] | 1.8203 [1.7814, 1.8402] | +3.78 | +2.02 | -1.57 | -2.64 |
| decode_tail2 | 1.9111 [1.8544, 1.9654] | 1.8996 [1.8699, 1.9212] | 1.9521 [1.9357, 1.9735] | 2.0022 [1.9900, 2.0416] | +2.35 | +5.71 | +3.06 | -0.36 |
| decode_tail3 | 2.1311 [2.1179, 2.1750] | 2.1323 [2.1049, 2.1636] | 2.1946 [2.1592, 2.4201] | 2.1877 [2.1739, 2.3836] | +3.18 | +2.71 | +0.16 | +0.15 |
| decode_batch4 | 2.3459 [2.3139, 2.3809] | 2.3685 [2.3169, 2.4321] | 2.2392 [2.2076, 2.2669] | 2.2533 [2.2190, 2.3421] | -4.48 | -3.98 | +0.60 | +0.55 |
| decode_batch5 | 2.4910 [2.4651, 2.5286] | 2.5000 [2.4768, 2.5375] | 2.4399 [2.4245, 2.5061] | 2.4503 [2.4123, 3.0087] | -2.01 | -1.67 | +0.22 | +0.29 |
| decode_batch8 | 3.1238 [3.0829, 3.1378] | 3.1269 [3.0946, 3.2365] | 2.9029 [2.8790, 2.9257] | 2.9553 [2.9333, 2.9821] | -6.85 | -5.07 | +2.05 | +0.38 |
| decode_dense128 | 2.7607 [2.7331, 2.7849] | 2.7623 [2.7150, 2.8612] | 2.3845 [2.3384, 2.4281] | 2.4736 [2.4163, 2.5109] | -13.64 | -10.71 | +3.35 | +0.00 |
| decode_dense4096 | 8.4727 [8.3943, 8.5793] | 8.5048 [8.3944, 8.6456] | 7.4112 [7.3087, 7.8251] | 7.6327 [7.5758, 7.6637] | -12.65 | -9.95 | +3.00 | +0.18 |
| decode_dense_multi | 4.7356 [4.7056, 4.8172] | 4.7079 [4.6974, 4.7910] | 4.0883 [4.0742, 4.1547] | 4.2139 [4.1798, 4.2712] | -13.61 | -11.08 | +2.89 | -0.43 |
| decode_first_singleton_grow | 4.7131 [4.6856, 4.7416] | 4.7066 [4.6786, 4.7635] | 4.1862 [4.1659, 4.2045] | 4.3009 [4.2664, 4.3380] | -11.17 | -8.77 | +2.76 | -0.10 |
| decode_singletons | 4.0097 [3.9828, 4.0625] | 4.0047 [3.9793, 4.0420] | 4.0145 [3.9984, 4.0624] | 4.0101 [3.9901, 4.0495] | +0.03 | +0.07 | -0.21 | -0.04 |
| decode_delta2 | 3.4937 [3.4707, 3.5345] | 3.5159 [3.4969, 3.5247] | 4.8102 [4.7945, 4.9588] | 3.6562 [3.6444, 3.6682] | +37.86 | +4.52 | -24.04 | +0.38 |
| decode_delta3 | 4.1764 [4.1652, 4.2303] | 4.1900 [4.1637, 4.3053] | 5.5169 [5.4950, 5.6440] | 4.4897 [4.4553, 4.5663] | +31.96 | +7.40 | -18.72 | +0.21 |
| decode_delta4 | 4.8858 [4.8582, 5.0966] | 4.8877 [4.8630, 4.9311] | 6.2224 [6.2107, 6.2702] | 5.1941 [5.1745, 5.2048] | +27.45 | +6.21 | -16.66 | +0.18 |
| decode_delta5 | 5.8845 [5.8471, 5.9128] | 5.8794 [5.8671, 6.0392] | 7.3119 [7.2618, 7.3785] | 5.9052 [5.8859, 6.0427] | +24.34 | +0.54 | -19.30 | +0.10 |
| decode_delta6 | 7.7860 [7.7699, 8.0834] | 7.7750 [7.7540, 8.0273] | 8.6072 [8.5615, 8.7100] | 7.2613 [7.2361, 7.2939] | +10.48 | -6.66 | -15.54 | -0.16 |
| decode_delta7 | 2.0453 [2.0433, 2.0664] | 2.0595 [2.0437, 2.0838] | 2.1078 [2.0819, 2.1355] | 2.0556 [2.0446, 2.0756] | +3.05 | +0.17 | -2.44 | +0.47 |

Cohort 1

| Case | B ms | T ms | D1 ms | D2 ms | D1/B % | D2/B % | D2/D1 % | T/B % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| skew1000 | 77.6275 [77.4400, 77.9830] | 77.4870 [77.3940, 77.6490] | 75.2030 [75.0910, 75.4660] | 75.7105 [75.5400, 75.7780] | -3.04 | -2.46 | +0.65 | -0.23 |
| dense_and | 83.4380 [79.9740, 87.8160] | 83.3170 [81.8170, 88.9480] | 83.3080 [81.0790, 87.6750] | 83.5490 [80.7050, 88.1130] | -0.38 | -0.29 | -0.20 | -0.27 |
| or_forced | 150.7890 [149.3960, 152.0440] | 150.8405 [148.3210, 152.5060] | 150.9025 [149.9970, 153.4260] | 151.4295 [150.1560, 152.0660] | +0.10 | +0.58 | +0.25 | +0.24 |
| single_forced | 143.9385 [142.7480, 145.4920] | 143.8345 [141.3880, 145.8850] | 144.0390 [142.5700, 146.0100] | 144.0695 [143.2270, 145.5080] | +0.23 | +0.16 | +0.09 | -0.00 |
| single_rare | 5.9285 [5.7910, 6.0220] | 6.0210 [5.8510, 6.0710] | 5.9510 [5.8070, 6.0190] | 6.0585 [5.8860, 6.1020] | +0.10 | +1.67 | +1.76 | +0.95 |
| prefix | 91.9480 [91.7840, 92.1180] | 91.7620 [91.6680, 91.9340] | 94.0645 [93.8510, 94.4490] | 91.6350 [91.5210, 91.9990] | +2.28 | -0.33 | -2.61 | -0.19 |
| seq_control | 56.9595 [54.9400, 59.8620] | 57.7805 [56.2870, 60.2980] | 57.2810 [55.3350, 59.5670] | 57.8435 [55.4760, 59.2160] | +0.48 | +1.32 | -0.02 | +1.32 |
| decode_one | 1.6239 [1.6009, 1.6588] | 1.6320 [1.6159, 1.9941] | 1.7198 [1.6956, 1.7339] | 1.6497 [1.6204, 1.6799] | +6.05 | +1.67 | -4.11 | +0.59 |
| decode_tail1 | 1.7246 [1.7149, 1.7309] | 1.7156 [1.6920, 1.7399] | 1.8227 [1.8024, 1.8412] | 1.7902 [1.7718, 1.8201] | +5.73 | +4.03 | -1.71 | -0.73 |
| decode_tail2 | 1.8797 [1.8741, 1.9166] | 1.8872 [1.8640, 1.9040] | 1.9427 [1.9118, 1.9735] | 1.9875 [1.9789, 2.0272] | +3.07 | +5.86 | +2.40 | +0.04 |
| decode_tail3 | 2.0973 [2.0923, 2.1311] | 2.1030 [2.0937, 2.1190] | 2.1516 [2.1376, 2.1680] | 2.1613 [2.1455, 2.1789] | +2.56 | +2.82 | +0.47 | +0.04 |
| decode_batch4 | 2.3162 [2.3073, 2.3431] | 2.3106 [2.3049, 2.3443] | 2.2151 [2.1998, 2.2379] | 2.2193 [2.2035, 2.2675] | -4.54 | -4.22 | +0.28 | -0.28 |
| decode_batch5 | 2.4781 [2.4668, 2.4891] | 2.5090 [2.4860, 2.5474] | 2.4347 [2.4192, 2.4451] | 2.4311 [2.4125, 2.4579] | -1.68 | -1.77 | +0.12 | +1.16 |
| decode_batch8 | 3.0892 [3.0761, 3.1158] | 3.0918 [3.0734, 3.1179] | 2.8791 [2.8616, 2.9241] | 2.9252 [2.9087, 3.0680] | -6.74 | -5.42 | +1.28 | +0.04 |
| decode_dense128 | 2.7320 [2.7123, 2.7711] | 2.7140 [2.7092, 2.7685] | 2.3620 [2.3397, 2.6212] | 2.4345 [2.4180, 2.6502] | -13.48 | -10.80 | +3.08 | -0.71 |
| decode_dense4096 | 8.4729 [8.3643, 8.6086] | 8.4395 [8.3902, 8.5829] | 7.3264 [7.3144, 7.3619] | 7.5361 [7.5160, 7.5940] | -13.49 | -10.76 | +2.88 | -0.70 |
| decode_dense_multi | 6.1097 [6.0726, 6.1330] | 6.1288 [6.0835, 6.1467] | 5.5120 [5.4973, 5.6002] | 5.5676 [5.5495, 5.6050] | -9.89 | -8.89 | +0.89 | +0.44 |
| decode_first_singleton_grow | 4.6533 [4.6480, 4.6879] | 4.7055 [4.6854, 4.7575] | 4.1735 [4.1687, 4.2015] | 4.2363 [4.2267, 4.2588] | -10.30 | -8.94 | +1.48 | +1.11 |
| decode_singletons | 3.7443 [3.7346, 3.7682] | 3.7402 [3.7307, 3.7793] | 3.8266 [3.8077, 3.8552] | 3.7390 [3.7248, 3.7765] | +2.20 | -0.07 | -2.36 | -0.05 |
| decode_delta2 | 3.4827 [3.4627, 3.5839] | 3.4747 [3.4584, 3.4857] | 4.8066 [4.7878, 4.8132] | 3.6514 [3.6219, 3.6761] | +38.11 | +5.12 | -24.08 | -0.25 |
| decode_delta3 | 4.1805 [4.1606, 4.2670] | 4.1746 [4.1691, 4.2274] | 5.5028 [5.4869, 5.5368] | 4.4701 [4.4426, 4.5180] | +31.59 | +6.81 | -18.73 | -0.18 |
| decode_delta4 | 4.9106 [4.8869, 4.9826] | 4.9566 [4.9479, 5.0048] | 6.2534 [6.2405, 6.3057] | 5.1788 [5.1708, 5.2073] | +27.17 | +5.49 | -17.16 | +1.01 |
| decode_delta5 | 5.8767 [5.8341, 5.9436] | 5.8804 [5.8399, 5.9576] | 7.2939 [7.2715, 7.3199] | 5.9008 [5.8780, 5.9394] | +24.23 | +0.40 | -19.09 | +0.07 |
| decode_delta6 | 7.7861 [7.7708, 7.8365] | 7.7853 [7.7581, 7.8866] | 8.5463 [8.5297, 8.5989] | 7.2852 [7.2652, 7.3085] | +9.72 | -6.56 | -14.78 | -0.02 |
| decode_delta7 | 2.0402 [2.0303, 2.0552] | 2.0419 [2.0312, 2.0687] | 2.1022 [2.0908, 2.1086] | 2.0449 [2.0325, 2.0533] | +2.96 | +0.32 | -2.61 | +0.26 |


Root final read-only proof confirms all 17 qualification/smoke/cohort lifetimes stopped, controller PID gone, full source, four prefixes/headers, modules, seeds and frozen scripts unchanged. No new VM action is required. The fresh portable frontdoor is static-tested only; the historical build/gate/campaign execution described above used the separately pinned original controllers.
