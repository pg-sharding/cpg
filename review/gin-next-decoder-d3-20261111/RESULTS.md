# D3: selective decoder gains with remaining tradeoffs

D3 reduces D2's multi-byte-delta overhead and retains its dense decoding gain in this fixed comparison, but it is not a general upgrade over D2. It loses the D2 benefit when a long delta appears first and dense deltas follow, and it gives back much of the first-singleton/growth benefit. Delta2, singleton and small-input regressions remain. Whole SQL results are mixed.

All percentages below are medians of direct per-round ratios, positive meaning slower. Slash-separated values are cohort 0 / cohort 1; they are not pooled. Absolute medians are milliseconds per complete native or SQL command. A ratio median need not equal the ratio of absolute medians. All 12 retained observations, min/max/mean/sample-stdev/MAD and all six role pairs are retained.

## Decoder outcome

- Dense128 D3/B is -10.45% / -10.65%, versus D2/B -10.67% / -10.81%. Absolute B CPU is 2.7724 / 2.7203 ms and D3 is 2.4804 / 2.4326 ms for the complete 20,000-loop command.
- Delta3 moves from D2/B +7.15% / +7.29% to D3/B -0.20% / +0.12%; delta4 moves from +6.20% / +6.31% to +0.32% / +0.05%. These observations approach B in this grid, without establishing equality or a universal fix.
- Delta2 still costs +2.30% / +3.22% versus B, although D3/D2 is -1.91% / -0.91%. Delta5 and delta7 also retain small positive case medians in at least one cohort.
- Alternating one-/multi-byte deltas improve from D2/B +16.41% / +16.75% to D3/B +1.56% / +1.45%. Dense-first/long-later D3/B is -2.59% / -2.04%.
- The prospectively declared long-first/dense-later negative is concrete: D2/B is -10.46% / -10.90%, but D3/B is +0.20% / -0.04%, so D3/D2 is +12.11% / +12.08%. Selecting scalar for the whole segment gives back the late dense benefit in this case.
- First-singleton/growth D3/D2 is +8.39% / +8.71%; D3/B is only -1.79% / -2.17%, compared with D2/B -9.15% / -10.03%. Singleton-segment D3/B is +2.38% / +2.51%. Batch4, batch5 and batch8 also become slower than D2 in both cohorts; every value and range remains in the full tables.

The native inner CPU includes the actual backend decoder's allocation, TID materialization and free. Input generation, compression and full-output verification are outside that clock. Backend command CPU and client wall time are separate metrics in the JSON and all-metric tables. These are allocation-inclusive backend workloads, not isolated instruction fragments.

## Whole SQL outcome and controls

Skew1000 D3/B executor time is -2.05% / -1.47%: B 77.8575 / 77.6110 ms to D3 76.2910 / 76.4315 ms for the entire 100-probe command. D2 is 76.0030 / 75.8845 ms, with D2/B -2.43% / -2.19%; D3/D2 is +0.43% / +0.69%. D3 therefore retains a modest B-relative benefit here while giving back some of D2's benefit.

Dense SQL D3/B is +1.23% / -0.13%; prefix is -0.68% / -0.81%; rare is +1.55% / -0.16%. Forced OR is +1.53% / +0.34% and forced single-term is +1.61% / +0.59%. D2/B forced OR is +4.17% / -0.45%, and forced single is +2.90% / -0.46%; the cohort-0 regressions do not repeat in cohort 1, so the first-cohort reduction is not a stable universal-repair result. The ID-only Seq control is +0.05% / -0.17% and has no GIN predicate. SQL timings refer to the complete fixed repeated-probe EXPLAIN command, not a per-request latency estimate.

Exact B/T controls are retained without correction. The ranges below are the minimum and maximum case medians for each primary metric, not confidence intervals:

| Cohort | Primary metric family | T/B case-median range |
|---|---|---:|
| 0 | decoder | -1.61% to +0.39% |
| 0 | sql | -1.61% to +0.45% |
| 1 | decoder | -1.12% to +0.75% |
| 1 | sql | -0.16% to +0.96% |

All CPU, wall and executor controls and every positive D3/B or D3/D2 case median are listed in `tables-r1/CONTROLS-AND-NEGATIVES.json`. Sign alone is not a significance classification. There is no pooling, trimming, twin normalization or source-causal attribution.

## Evidence and limits

The accepted campaign contains 3136 raw commands: 2688 retained and 448 warm, 21 native decoder cells and seven SQL cells. Two fresh cohorts each use two warm and 12 retained balanced four-role rounds. The independent recount passed all 87,360 numeric comparisons, 672 absolute groups, 1008 pair groups and 12,096 direct round pairs. Both independent regenerations are byte-identical to the canonical analyses. Raw and literal journals remain plain JSONL.

The extra observation review checked 224 case/role setting objects against 12 explicit expected GUC values each, 784 actual SQL plans, 200 historical ordered Seq/index reference hashes, eight backend/source/ELF/header/module bindings and the final 17-lifetime shutdown proof. No production source, expected output, loop, threshold or case was changed after the freeze.

Four clean backend builds B/D2/D3/D3_assert each passed the original 239 core and posting tests. The finite ordinary gate passed 188 ordered/prepared SQL and 48 lifecycle comparisons, 84 decoder cases/54,144 item checks, and 768 valid boundary cases/1536 decode calls/33,408 item checks. The old fixed-B reference is unchanged. Assertion-build object equality is not applicable because its flags differ. Auxiliary auditor draft errors are preserved separately from actual runtime PASS.

Normal full-build ASM matches the reviewed r2 translation unit: no outlined decode_varbyte calls, a 24-byte local frame and the same six saved registers. D3 remains 1241 bytes versus D2 844 and B 589. The extra static growth-call site does not prove extra runtime allocations. D3r1's helper outlining and 56-byte local-frame outcome is retained as a codegen-only negative; it was not timed as a full backend.

The bounded host monitor recorded 49 five-second endpoint samples, load1 0.1538–1.1099, and covered the accepted campaign status interval. Recorded controller/runner/backend PIDs account for the major Python/PostgreSQL consumers. Other low activity remains visible. Endpoint/top20 snapshots can miss short-lived work; there is no per-thread affinity, host-steal or CPU-frequency proof. The two CPU placements are on one VM, not a second-host replication. Retained command read/write bytes and major faults were zero in both cohorts; this is not a disk-cold experiment.

The actual root final proof confirms 17 owned lifetimes stopped, controller PIDs gone and source, four installed prefixes, headers, modules, seeds and frozen inputs unchanged. This is a finite ordinary performance experiment, not arbitrary concurrency or general merge qualification. Fresh Linux replay remains a static-validated frontdoor until a new Linux run through it is actually performed. The completed recorded-data offline replay is a separate local validation.

## Complete primary table

Primary metric for all 28 cells. Decoder = allocation/materialization/free process CPU; SQL = whole-command EXPLAIN execution time. All absolute values are milliseconds per complete command, median [min,max], n=12. Percent columns are medians of direct per-round ratios, not ratios of absolute medians. Positive means slower. Exact B/T is a control, not a correction.

Cohort 0

| Case | B ms | T ms | D2 ms | D3 ms | D2/B % | D3/B % | D3/D2 % | T/B % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| skew1000 | 77.8575 [77.7250, 78.9650] | 77.7550 [76.1630, 77.9560] | 76.0030 [74.7820, 76.2580] | 76.2910 [75.0300, 77.7830] | -2.43 | -2.05 | +0.43 | -0.17 |
| dense_and | 85.2350 [82.5770, 90.8490] | 83.7870 [82.5040, 88.6720] | 84.9810 [83.7970, 91.2520] | 85.1120 [83.8250, 97.6230] | -0.30 | +1.23 | +0.03 | -1.61 |
| or_forced | 151.9045 [151.2000, 152.9280] | 152.1640 [150.9670, 156.1610] | 158.5570 [157.0810, 159.2070] | 154.2500 [152.3120, 155.2710] | +4.17 | +1.53 | -2.69 | +0.20 |
| single_forced | 145.9725 [143.9590, 149.0900] | 145.2240 [144.5150, 147.8650] | 149.8855 [148.7460, 152.3150] | 147.5085 [146.3770, 150.2610] | +2.90 | +1.61 | -1.67 | +0.33 |
| single_rare | 6.0855 [5.9700, 6.4290] | 6.1070 [5.9980, 6.1790] | 6.4755 [6.3230, 6.6690] | 6.1650 [6.0610, 6.3170] | +6.61 | +1.55 | -4.94 | +0.45 |
| prefix | 92.5115 [91.8160, 93.6900] | 92.2390 [92.0290, 93.8340] | 92.5410 [92.2570, 95.2950] | 91.9190 [91.5220, 93.4840] | +0.32 | -0.68 | -0.95 | +0.17 |
| seq_control | 57.6975 [56.3830, 62.5240] | 58.9765 [55.7750, 61.2820] | 58.4890 [56.3110, 60.3710] | 59.0600 [56.5040, 61.2100] | +0.12 | +0.05 | +0.62 | -0.63 |
| decode_one | 1.6302 [1.6067, 1.6728] | 1.6293 [1.6116, 1.6652] | 1.6465 [1.6165, 1.7113] | 1.6631 [1.6373, 1.6925] | +0.76 | +2.04 | +0.59 | +0.39 |
| decode_tail1 | 1.7323 [1.7195, 1.7607] | 1.7449 [1.7192, 1.7586] | 1.8397 [1.7920, 1.8484] | 1.7550 [1.7356, 2.8742] | +5.79 | +1.31 | -3.91 | +0.14 |
| decode_tail2 | 1.9069 [1.8813, 1.9631] | 1.9021 [1.8722, 1.9217] | 2.0279 [1.9889, 2.0469] | 1.9089 [1.8750, 1.9485] | +5.81 | +0.42 | -5.76 | -0.09 |
| decode_tail3 | 2.1440 [2.1134, 2.1820] | 2.1291 [2.1113, 2.4607] | 2.2061 [2.1658, 2.2362] | 2.1432 [2.1243, 2.1854] | +2.88 | -0.01 | -2.75 | -0.57 |
| decode_batch4 | 2.3650 [2.3416, 2.3964] | 2.3664 [2.3443, 2.4073] | 2.2456 [2.2307, 2.2593] | 2.3109 [2.2734, 2.3414] | -5.04 | -2.03 | +2.92 | +0.08 |
| decode_batch5 | 2.5231 [2.4885, 2.5416] | 2.5184 [2.4885, 2.5410] | 2.4695 [2.4343, 3.1368] | 2.5269 [2.4764, 2.5507] | -1.87 | +0.02 | +1.95 | -0.16 |
| decode_batch8 | 3.1045 [3.0939, 3.1770] | 3.1067 [3.0792, 3.1747] | 2.9445 [2.9070, 2.9997] | 2.9880 [2.9730, 3.0661] | -5.32 | -3.67 | +1.71 | -0.26 |
| decode_dense128 | 2.7724 [2.7376, 2.8049] | 2.7696 [2.7073, 2.8249] | 2.4765 [2.4610, 2.8206] | 2.4804 [2.4659, 2.5008] | -10.67 | -10.45 | +0.19 | -0.21 |
| decode_dense4096 | 8.5552 [8.5063, 8.7892] | 8.5453 [8.4940, 8.6151] | 7.6537 [7.6284, 7.8192] | 7.6565 [7.6318, 7.8803] | -10.77 | -10.35 | +0.03 | -0.30 |
| decode_dense_multi | 4.8022 [4.7706, 4.8742] | 4.7957 [4.7752, 4.8638] | 4.2340 [4.2121, 4.2522] | 4.3218 [4.3068, 4.3412] | -11.88 | -10.04 | +2.13 | -0.18 |
| decode_first_singleton_grow | 4.7854 [4.7236, 4.8206] | 4.7865 [4.7021, 4.8703] | 4.3450 [4.2696, 4.3997] | 4.7117 [4.6367, 4.7965] | -9.15 | -1.79 | +8.39 | -0.00 |
| decode_singletons | 4.3005 [4.2453, 4.3746] | 4.3157 [4.2657, 4.3351] | 4.0654 [3.9787, 4.1264] | 4.4147 [4.3357, 4.4814] | -5.75 | +2.38 | +8.49 | +0.23 |
| decode_delta2 | 3.5552 [3.4729, 3.6153] | 3.5445 [3.4892, 3.5825] | 3.7004 [3.6584, 3.7463] | 3.6253 [3.5879, 3.6850] | +4.36 | +2.30 | -1.91 | -0.25 |
| decode_delta3 | 4.2230 [4.1755, 4.2626] | 4.2231 [4.1818, 4.2886] | 4.5268 [4.4705, 4.5789] | 4.2318 [4.1744, 4.2826] | +7.15 | -0.20 | -6.83 | -0.01 |
| decode_delta4 | 4.8926 [4.8638, 4.9208] | 4.9003 [4.8766, 4.9468] | 5.1904 [5.1622, 5.2855] | 4.8985 [4.8845, 4.9825] | +6.20 | +0.32 | -5.68 | +0.16 |
| decode_delta5 | 5.9802 [5.8844, 6.8126] | 5.9426 [5.8541, 6.1080] | 5.9902 [5.9049, 6.0240] | 5.9729 [5.8960, 6.0290] | -0.22 | +0.02 | -0.11 | -0.38 |
| decode_delta6 | 7.9576 [7.8646, 8.2716] | 7.7890 [7.7534, 7.9558] | 7.3425 [7.2523, 7.4945] | 7.1533 [7.1242, 7.3316] | -7.84 | -9.61 | -1.86 | -1.61 |
| decode_delta7 | 2.0586 [2.0469, 2.1007] | 2.0673 [2.0436, 2.0939] | 2.0608 [2.0438, 2.1262] | 2.0666 [2.0442, 2.1064] | +0.03 | +0.01 | +0.36 | -0.05 |
| decode_long_first_then_dense | 2.7353 [2.7240, 2.7857] | 2.7240 [2.7024, 2.7548] | 2.4454 [2.4199, 2.4856] | 2.7386 [2.7131, 2.7503] | -10.46 | +0.20 | +12.11 | -0.49 |
| decode_dense_first_then_long | 3.5945 [3.5502, 3.6433] | 3.5935 [3.5221, 3.6162] | 3.6091 [3.5877, 3.7641] | 3.5129 [3.4833, 3.5514] | +0.54 | -2.59 | -2.68 | +0.10 |
| decode_alternating_one_multibyte | 3.1362 [3.1337, 3.1721] | 3.1382 [3.1198, 3.1507] | 3.6564 [3.6316, 3.6652] | 3.1883 [3.1664, 3.8483] | +16.41 | +1.56 | -12.75 | -0.16 |

Cohort 1

| Case | B ms | T ms | D2 ms | D3 ms | D2/B % | D3/B % | D3/D2 % | T/B % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| skew1000 | 77.6110 [77.4150, 77.8420] | 77.6525 [77.4610, 77.8220] | 75.8845 [75.7010, 76.8910] | 76.4315 [76.2630, 77.8270] | -2.19 | -1.47 | +0.69 | +0.06 |
| dense_and | 83.1205 [81.5720, 88.3840] | 84.0460 [81.8840, 88.4210] | 84.5130 [83.1130, 88.9780] | 83.6220 [82.0890, 86.7230] | +2.47 | -0.13 | -1.25 | +0.96 |
| or_forced | 152.0215 [150.9860, 153.1430] | 152.1985 [150.6340, 153.4750] | 151.5895 [150.7060, 152.4560] | 152.3020 [151.5920, 153.7110] | -0.45 | +0.34 | +0.73 | -0.16 |
| single_forced | 145.1045 [144.0080, 145.8760] | 145.0100 [143.4420, 146.6780] | 144.7645 [143.6170, 146.2330] | 145.5420 [144.0210, 147.1300] | -0.46 | +0.59 | +0.58 | -0.08 |
| single_rare | 5.9670 [5.7990, 6.0340] | 5.9990 [5.9210, 6.0990] | 6.0300 [5.9000, 6.0960] | 5.9795 [5.9160, 6.0680] | +0.58 | -0.16 | -0.64 | +0.24 |
| prefix | 92.1405 [91.8710, 93.8700] | 91.9690 [91.6460, 93.9010] | 92.7935 [92.6510, 94.6020] | 91.4525 [91.2830, 93.5250] | +0.82 | -0.81 | -1.47 | -0.16 |
| seq_control | 58.8460 [55.5320, 62.6050] | 59.6170 [57.5960, 61.9660] | 59.1095 [56.9890, 61.3680] | 58.8355 [57.2280, 63.0700] | +0.11 | -0.17 | -1.10 | +0.04 |
| decode_one | 1.6199 [1.6087, 1.6697] | 1.6198 [1.6102, 1.6564] | 1.6740 [1.6454, 1.7035] | 1.6665 [1.6393, 1.7174] | +3.25 | +2.22 | -0.98 | -0.17 |
| decode_tail1 | 1.7379 [1.7203, 1.7989] | 1.7319 [1.7218, 1.7520] | 1.8404 [1.8144, 1.8718] | 1.7821 [1.7552, 1.8961] | +5.55 | +2.41 | -3.51 | -0.59 |
| decode_tail2 | 1.8968 [1.8681, 1.9358] | 1.9003 [1.8834, 1.9587] | 2.0072 [1.9768, 2.0555] | 1.9034 [1.8569, 1.9448] | +6.23 | +0.08 | -5.44 | +0.75 |
| decode_tail3 | 2.1216 [2.0998, 2.1458] | 2.1187 [2.0856, 2.1708] | 2.1798 [2.1394, 2.2231] | 2.1132 [2.0908, 2.1385] | +2.62 | -0.22 | -2.65 | -0.11 |
| decode_batch4 | 2.3155 [2.2984, 2.3284] | 2.3141 [2.3012, 2.3219] | 2.2096 [2.1985, 2.4160] | 2.2596 [2.2469, 2.3070] | -4.39 | -2.36 | +2.19 | -0.02 |
| decode_batch5 | 2.4923 [2.4742, 2.5722] | 2.4841 [2.4648, 2.5127] | 2.4289 [2.4089, 2.4697] | 2.4795 [2.4744, 2.5268] | -2.43 | -0.46 | +2.33 | -0.09 |
| decode_batch8 | 3.0847 [3.0698, 3.1411] | 3.0836 [3.0703, 3.1206] | 2.9206 [2.9081, 2.9269] | 2.9754 [2.9619, 2.9821] | -5.32 | -3.68 | +1.94 | +0.01 |
| decode_dense128 | 2.7203 [2.7054, 2.7505] | 2.7146 [2.7085, 2.7610] | 2.4318 [2.4169, 2.4713] | 2.4326 [2.4208, 2.4589] | -10.81 | -10.65 | -0.08 | -0.12 |
| decode_dense4096 | 8.4631 [8.4012, 8.8808] | 8.5063 [8.3572, 8.8841] | 7.5432 [7.5318, 7.5966] | 7.5660 [7.5553, 7.7516] | -10.84 | -10.70 | +0.35 | -0.06 |
| decode_dense_multi | 5.0290 [5.0034, 5.0889] | 5.0376 [5.0229, 5.0835] | 4.5104 [4.4963, 4.5135] | 4.5940 [4.5757, 4.6100] | -10.34 | -8.90 | +1.91 | +0.22 |
| decode_first_singleton_grow | 4.7359 [4.7276, 4.7425] | 4.6809 [4.6614, 4.7031] | 4.2612 [4.2533, 4.2900] | 4.6327 [4.6076, 4.6594] | -10.03 | -2.17 | +8.71 | -1.12 |
| decode_singletons | 3.7417 [3.7352, 3.7611] | 3.7499 [3.7359, 3.7684] | 3.7458 [3.7363, 3.7590] | 3.8354 [3.8264, 3.8984] | +0.08 | +2.51 | +2.38 | +0.27 |
| decode_delta2 | 3.4725 [3.4592, 3.5103] | 3.4720 [3.4617, 3.4986] | 3.6335 [3.6278, 3.6424] | 3.6010 [3.5260, 3.6298] | +4.52 | +3.22 | -0.91 | -0.05 |
| decode_delta3 | 4.1719 [4.1613, 4.2026] | 4.1673 [4.1589, 4.1958] | 4.4772 [4.4539, 4.5904] | 4.1760 [4.1653, 4.1923] | +7.29 | +0.12 | -6.76 | -0.14 |
| decode_delta4 | 4.8682 [4.8597, 4.9510] | 4.8660 [4.8502, 4.8933] | 5.1742 [5.1608, 5.2159] | 4.8692 [4.8591, 4.8937] | +6.31 | +0.05 | -5.93 | -0.01 |
| decode_delta5 | 5.8672 [5.8362, 5.9070] | 5.8786 [5.8322, 5.9063] | 5.9056 [5.8867, 5.9595] | 5.8825 [5.8498, 6.1862] | +0.64 | +0.30 | -0.27 | +0.12 |
| decode_delta6 | 7.7897 [7.7669, 7.9122] | 7.7855 [7.7776, 8.0053] | 7.2625 [7.2510, 7.2942] | 7.1364 [7.1287, 7.2187] | -6.77 | -8.40 | -1.70 | -0.01 |
| decode_delta7 | 2.0466 [2.0308, 2.0785] | 2.0448 [2.0304, 2.0748] | 2.0485 [2.0366, 2.0854] | 2.0459 [2.0381, 2.1355] | +0.35 | +0.07 | -0.01 | -0.26 |
| decode_long_first_then_dense | 2.7398 [2.7147, 2.7895] | 2.7371 [2.7243, 2.7421] | 2.4405 [2.4296, 2.4529] | 2.7370 [2.7215, 2.7496] | -10.90 | -0.04 | +12.08 | -0.22 |
| decode_dense_first_then_long | 3.5856 [3.5643, 3.6074] | 3.5908 [3.5599, 3.6327] | 3.5925 [3.5782, 3.6311] | 3.5039 [3.4895, 3.5328] | +0.39 | -2.04 | -2.36 | +0.17 |
| decode_alternating_one_multibyte | 3.1222 [3.1086, 3.1557] | 3.1253 [3.1196, 3.1371] | 3.6445 [3.6274, 3.6783] | 3.1686 [3.1440, 3.2431] | +16.75 | +1.45 | -13.00 | +0.09 |



All three metrics, absolute spread statistics and direct pairs are in `ALL-ABSOLUTE.md`, `ALL-PAIRS.md` and the unchanged `analysis0-r1/` and `analysis1-r1/` JSON. D2 and D3 are independent alternatives over the same fixed B; the comparison does not stack their standalone patches.
