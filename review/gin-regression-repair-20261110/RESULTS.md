# GIN regression repair: full SQL and real-AM results

C9 fixes the absent cost and improves the measured native inline loop; full SQL inline/control movements must be read from the unpooled table below. It combines direct logical-TID ordering and adaptive decoded advancement with lazy posting consumption, including deferred first-page decoding with an exact frequency count. This is a tested prototype on fixed B72, not a current-master or general speedup claim.

Selected source: 0ab3bd65c8957ea5e25f9ef8981401f0616d99de, branch experiments/gin-combined-v9-b72-20261110. Baseline B72 is 72b9498df9a369e747f8d96efb5a6cd33c2451e2 plus the same supplied prerequisite in every tree (fixed base 8a8c475037bfde101da23cc9b0364c9c020eca93). Earlier published observations are historical context, not pooled data.

## Full SQL confirmation

Absolute columns are retained EXPLAIN executor medians in ms, cohort0 / cohort1. Paired columns are same-round whole-command backend CPU percent medians. Negative means less time. They are different measurement boundaries, not ratios of the displayed absolute medians. Every full-SQL query uses the original data/probe counts.

| Case | B executor ms | L4 executor ms | C9 executor ms | L4/B CPU % | C9/B CPU % | C9/L4 CPU % |
|---|---:|---:|---:|---:|---:|---:|
| skew1000 | 80.9340 / 78.8805 | 30.0570 / 28.4460 | 21.6475 / 19.9840 | -62.32 / -63.81 | -72.94 / -74.20 | -26.63 / -28.83 |
| skew127 | 149.5775 / 150.9795 | 153.6310 / 150.0960 | 111.9625 / 114.4035 | -0.69 / -0.86 | -24.77 / -24.85 | -24.38 / -24.31 |
| skew17 | 101.4675 / 99.1790 | 104.8480 / 98.8790 | 95.7655 / 91.4565 | +1.25 / -0.98 | -8.02 / -8.01 | -8.64 / -7.39 |
| separate_keys | 79.6220 / 79.6165 | 32.3505 / 30.4570 | 22.5015 / 21.2355 | -60.47 / -61.44 | -71.56 / -73.12 | -27.60 / -30.48 |
| dense_and | 106.8715 / 88.4830 | 91.5425 / 86.2230 | 126.4680 / 86.2895 | +3.17 / +0.27 | +7.75 / -2.53 | +16.27 / -2.04 |
| or_forced | 157.9975 / 156.1935 | 162.0255 / 154.5520 | 177.2810 / 159.7720 | +3.44 / -0.84 | +10.73 / +1.75 | +9.25 / +2.73 |
| single_forced | 172.9220 / 157.6730 | 154.7035 / 154.7320 | 166.1440 / 155.1715 | -0.26 / -1.97 | +6.70 / -2.77 | +7.81 / -2.10 |
| single_rare | 6.1980 / 6.1535 | 6.2925 / 6.0455 | 6.4045 / 6.3715 | +0.60 / -0.17 | +3.49 / +2.34 | +1.61 / +0.03 |
| inline | 0.4725 / 0.4540 | 0.4720 / 0.4700 | 0.4500 / 0.4025 | +1.46 / +3.73 | +1.79 / -4.94 | -4.83 / -8.96 |
| prefix | 115.7285 / 94.5625 | 99.8870 / 93.8525 | 105.9815 / 94.1050 | -1.21 / +0.37 | -0.81 / -0.83 | +0.34 / +0.06 |
| phrase | 81.6005 / 80.7615 | 29.9005 / 30.4540 | 23.6395 / 20.2055 | -62.73 / -62.30 | -72.71 / -74.79 | -28.05 / -30.84 |
| not | 38.0090 / 39.6055 | 20.4350 / 20.1685 | 12.1105 / 12.3130 | -46.81 / -49.05 | -67.93 / -68.59 | -38.19 / -39.43 |
| intarray | 79.3685 / 80.5080 | 28.6985 / 28.2980 | 19.7980 / 19.1425 | -63.78 / -65.53 | -74.95 / -75.72 | -30.43 / -31.23 |
| builtin_array | 83.9715 / 78.3405 | 30.7185 / 27.4720 | 21.7715 / 19.1550 | -63.16 / -64.93 | -73.42 / -75.85 | -30.30 / -30.29 |
| jsonb | 158.4965 / 152.0990 | 53.5580 / 54.1890 | 36.4350 / 36.0025 | -65.82 / -64.47 | -76.29 / -76.36 | -31.65 / -33.93 |
| lossy_and | 145.3100 / 135.7830 | 149.6555 / 137.3790 | 142.4430 / 139.2550 | +5.33 / +0.86 | -1.15 / +2.95 | -6.00 / +1.10 |
| seq_control | 68.3005 / 56.9845 | 61.6065 / 57.8715 | 61.3625 / 55.0165 | -6.73 / -0.99 | -5.42 / -0.29 | +4.40 / -5.47 |
| phrase_positive | 48.4825 / 45.6935 | 27.8380 / 27.4310 | 19.3065 / 19.3295 | -40.14 / -40.21 | -60.04 / -57.34 | -29.36 / -28.22 |
| not_positive | 41.9195 / 43.3920 | 23.7355 / 23.3645 | 15.1175 / 15.9950 | -43.27 / -45.10 | -63.64 / -62.30 | -34.24 / -32.39 |
| skew_group4096 | 60.1100 / 59.9025 | 11.3355 / 11.3660 | 6.9960 / 7.1060 | -80.77 / -80.87 | -88.21 / -87.69 | -38.84 / -37.44 |
| array_dense | 1779.1570 / 1670.1130 | 1804.9405 / 1710.5160 | 1679.2565 / 1640.8935 | +0.07 / +1.50 | -4.06 / -2.85 | -7.55 / -3.72 |
| inline_single | 4.5920 / 4.7460 | 4.4990 / 4.7050 | 4.1035 / 4.6415 | -3.13 / -1.31 | -11.13 / -3.02 | -2.07 / -1.67 |
| absent | 2.1975 / 1.2610 | 2.1825 / 1.3400 | 0.4980 / 0.3345 | -2.45 / +5.34 | -66.99 / -62.97 | -65.90 / -64.49 |
| not_only | 175.9675 / 177.9565 | 179.6900 / 188.9585 | 178.3120 / 178.0505 | +1.59 / +2.47 | +1.85 / -0.86 | +0.80 / -2.47 |
| empty_array | 178.5415 / 190.5820 | 179.6980 / 190.0415 | 182.6000 / 181.5800 | -1.37 / -1.56 | +2.06 / -3.78 | +0.63 / -3.58 |

## Real-AM diagnostic screen

These are newly executed real index_rescan/index_getbitmap/tbm_free loops on the actual backend, separate from SQL/heap visibility. Absolute columns and paired percentages in this table both measure the internal loop process CPU. No modeled loader or private extracted body is used.

| Case | B AM CPU ms | L4 AM CPU ms | C9 AM CPU ms | C9/B CPU % | C9/L4 CPU % |
|---|---:|---:|---:|---:|---:|
| am_inline | 18.2737 / 18.3950 | 20.3404 / 20.2539 | 15.0749 / 15.3345 | -17.89 / -17.05 | -25.10 / -24.19 |
| am_absent | 56.6929 / 58.7498 | 53.1101 / 58.6210 | 7.0791 / 7.2361 | -87.41 / -88.04 | -86.66 / -87.58 |
| am_skew1000 | 74.2673 / 73.6087 | 22.5953 / 22.7221 | 14.3709 / 13.7170 | -80.76 / -81.15 | -36.89 / -38.81 |
| am_full | 103.1329 / 98.8109 | 101.8984 / 99.1288 | 99.1422 / 99.1054 | -4.63 / -0.33 | -3.14 / -0.14 |

## Spread, negatives, and limits

Full-SQL cases with positive C9/B CPU paired medians in both cohorts: or_forced, single_rare. All cases and all pairs remain in the table and raw evidence; this sign check alone is not a significance test. Check B/T and C9/T alongside B, without normalizing by either.

| Full SQL control | C9/B CPU % | T/B CPU % | C9/T CPU % |
|---|---:|---:|---:|
| inline | +1.79 / -4.94 | +2.97 / -0.12 | -5.49 / -5.85 |
| absent | -66.99 / -62.97 | +0.22 / +0.21 | -66.36 / -63.06 |
| or_forced | +10.73 / +1.75 | +1.54 / +3.79 | +9.74 / -0.44 |
| single_forced | +6.70 / -2.77 | -0.18 / +0.67 | +8.32 / -4.28 |
| inline_single | -11.13 / -3.02 | -0.07 / -1.96 | -2.46 / -1.53 |
| dense_and | +7.75 / -2.53 | +5.24 / -4.07 | +9.55 / +1.98 |
| array_dense | -4.06 / -2.85 | -1.34 / +0.93 | -1.78 / -2.04 |
| lossy_and | -1.15 / +2.95 | -0.19 / +1.31 | -0.83 / +1.08 |
| seq_control | -5.42 / -0.29 | -1.94 / +1.96 | -1.94 / -3.71 |

The R3 screen had C9 OR +5.95/-2.79% and Seq +9.06/-5.96% across reversed cohorts; those first-cohort increases did not repeat there. Earlier repeated off-path Seq costs are preserved as unresolved historical observations. The same-binary calibration in R2 also moved, but does not prove a harmless cause or rule out source/layout effects. No cache/branch explanation is inferred from software samples or identical instruction shapes.

V7 reduced scan-entry state from 848 to 832 bytes but did not repair inline; R2 native inline remained about +10% versus baseline. L8/L9 alone left native inline +5.97/+7.09% and +4.58/+5.11%, respectively; L9 also had OR +3.75/+6.90%. All failed/partial improvements and their source branches are retained. See R2-RESULTS.md and R3-SCREEN-RESULTS.md.

Absolute executor min/median/max for the repaired targets and key controls:

| Cohort | Case | B min / median / max ms | C9 min / median / max ms |
|---:|---|---:|---:|
| 0 | inline | 0.427000 / 0.472500 / 0.684000 | 0.407000 / 0.450000 / 0.706000 |
| 0 | absent | 1.558000 / 2.197500 / 2.275000 | 0.481000 / 0.498000 / 0.527000 |
| 0 | skew1000 | 77.921000 / 80.934000 / 113.671000 | 20.360000 / 21.647500 / 33.383000 |
| 0 | jsonb | 152.066000 / 158.496500 / 165.735000 | 35.559000 / 36.435000 / 41.948000 |
| 0 | or_forced | 150.215000 / 157.997500 / 210.910000 | 166.808000 / 177.281000 / 228.035000 |
| 0 | seq_control | 54.749000 / 68.300500 / 82.419000 | 48.542000 / 61.362500 / 79.433000 |
| 1 | inline | 0.429000 / 0.454000 / 0.636000 | 0.392000 / 0.402500 / 0.614000 |
| 1 | absent | 1.191000 / 1.261000 / 1.328000 | 0.303000 / 0.334500 / 0.401000 |
| 1 | skew1000 | 77.813000 / 78.880500 / 80.323000 | 19.738000 / 19.984000 / 21.027000 |
| 1 | jsonb | 150.912000 / 152.099000 / 159.319000 | 35.348000 / 36.002500 / 36.861000 |
| 1 | or_forced | 148.911000 / 156.193500 / 173.229000 | 148.017000 / 159.772000 / 186.718000 |
| 1 | seq_control | 46.986000 / 56.984500 / 67.240000 | 48.422000 / 55.016500 / 64.976000 |

Every absolute min/median/max, SD/MAD, all metric boundaries, every direct pair and per-round observation is preserved in results-r2/, results-r3/ and evidence-r2/, evidence-r3/. No sample trimming, cohort pooling or twin correction. The former holdout filenames are historical; these are no longer unseen discovery cases.

## Executed validation and scope

- VM158: 8 logical CPUs/4 physical cores, 16GB RAM, shared host. No foreign job or configuration was changed. The archive host was not used. CPU 0/4 server/client then 4/0, reversed roles/physical slots/session births/case order. Identical B/T ELFs, unchanged fixtures and frozen queries.
- GCC 13.3.0, -O2 -g -fno-lto, OpenSSL, no ICU/readline, nice 10, make -j2, common source/build/compiled-prefix paths with separate DESTDIR installs. R2 five clean builds; R3 clean B/C9_assert and incremental L4/L8/L9/C9, all source/header manifests verified. Every L8/L9/C9 release transition changed exactly ginget.o among backend objects. All eleven builds passed original 239 core tests each, without expected regeneration.
- Every R3 campaign first qualified all six variants on 25 ordered Seq/GIN multisets, scalar answers/expected plans, eight prepared-query comparisons with cached rescans, and four AM answers. C9_assert independently decoded first-page counts to verify exact cardinality. All 25 multisets repeat per measured role/cohort. Core has only a weak existing fuzzy-search smoke test; no new statistical fuzzy-sampling or legacy-page migration validation is claimed.
- Completed R2 null: 660 raw/600 retained/60 warm; R2 screen 3080/2800/280. Completed R3 screen: 2688/2304/384; full SQL: 2800/2400/400. All warm and failed-attempt records stay separate. The R1 adapter error produced zero timing samples and is documented in NOT-AM-ADAPTER-r1.md.
- Two warm+12 retained balanced rounds per R3 case. Each measured call follows an extra literal-answer execution. JIT/parallel/memoize/autovacuum off; shared_buffers 512MB, work_mem 64MB except the unchanged 64kB lossy case, explicit system timing clock. Recorded retained root-plan IO/WAL and whole-command read/write byte counters are reported in each analysis receipt.
- Independent local raw reconstruction verifies order/roles/answers/counts/hashes and matches remote analyses; only relative 3e-15 rounding in sample SD across Python versions is tolerated. All 68 ordinary campaign cluster directories across both waves were checked shut down, measured postmaster/backend PIDs and sockets absent, installs/final sources/seeds/runtime/AM modules unchanged. At the completed-wave final snapshots no process used the owned install/build executables; a later separate diagnostic is outside those snapshots.
- Real exported C9 .diff was independently applied to the exact fixed-base files and matched the executed three-file snapshot. Code branches, including negatives, were pushed and ls-remote verified. Publication receipts outside the frozen packet record results-branch and S3 verification.

No current upstream master, CREATE INDEX throughput, independent-host confidence, exhaustive prior-art search, or universal speedup claim. These are known algorithmic ingredients; concrete contribution and previous discussion are in PRIOR-ART.md. Run instructions, exact dependencies/source/build flags/data creation/commands/metric boundaries are in REPRODUCE.md. The English mailing-list draft remains UNSENT.
