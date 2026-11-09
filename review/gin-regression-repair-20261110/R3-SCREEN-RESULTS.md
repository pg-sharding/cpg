# R3: direct ordering, exact first-page counts, and combined advancement

C9 is selected for full SQL confirmation. Both complete screen cohorts improve the inline and absent targets in real SQL and actual-AM CPU, and retain selective gains. OR and Seq costs from cohort0 reverse in cohort1. This does not establish that every regression is repaired; the full 25-query confirmation remains a separate required stage.

All measurements are fixed B72 on VM158, one shared host and one fixture. B/T are the exact same executable. Candidate source stayed frozen; there is no trimming, pooling or twin correction.

## Source and checks

- L8 75431a5a15d705aa43188d39b84b220cae7bd036: direct boolean logical TID ordering in two decoded loops, retaining L4 state layout.
- L9 67afd66eb433a208e2ceb3905a3ea4dfd30b9b60: additionally defer compressed first-page decoding for multi-entry startup, with exact varbyte-terminator/popcount cardinality preserving the original frequency estimate. Singleton/legacy/empty paths stay eager.
- C9 0ab3bd65c8957ea5e25f9ef8981401f0616d99de: additionally combine two-probe/exponential/binary decoded advancement with lazy consumption. This is a newly measured combination; old alternative gains are not added.
- Six builds passed original 239 tests each, including C9 assertions. Full source/header identities and install hashes recorded. B/C9_assert clean; release L4/L8/L9/C9 reuse unchanged objects at common paths and flags. Each L8/L9/C9 transition changes exactly ginget.o among backend objects.
- All six builds passed 25 ordered Seq/GIN multisets, scalar answers and index paths, eight prepared-query comparisons and cached rescans, plus four actual-AM answer checks. C9 assertions independently decode first-page counts and compare exact cardinality.
- Screen: six roles, 12 SQL plus four AM cases, two warm+12 retained balanced rounds, two reversed CPU/slot/session/case cohorts; 2688 raw/2304 retained/384 warm. All 25 row multisets repeat on every measured role/cohort. All retained recorded IO/WAL counters are zero. Fifteen separate software profiles passed; they are diagnostic and are excluded from timing samples.

## SQL screen

Absolute columns are EXPLAIN executor medians in ms, cohort0 / cohort1. Percent columns are direct paired whole-command backend CPU medians, kept separate per cohort. These are different boundaries, not ratios of the displayed absolute medians.

| Case | B executor ms | L4 executor ms | C9 executor ms | L4/B CPU % | C9/B CPU % | C9/L4 CPU % |
|---|---:|---:|---:|---:|---:|---:|
| skew1000 | 79.7200 / 79.7610 | 29.0260 / 29.2905 | 20.8635 / 21.1265 | -63.27 / -63.18 | -73.55 / -73.73 | -28.36 / -29.81 |
| skew127 | 144.9680 / 145.1595 | 147.6630 / 146.4775 | 109.0445 / 108.6035 | +1.64 / +1.50 | -23.92 / -24.98 | -25.51 / -25.72 |
| skew_group4096 | 59.8015 / 94.7115 | 11.1050 / 17.9335 | 6.5775 / 11.2465 | -80.95 / -80.77 | -88.48 / -87.81 | -39.76 / -36.68 |
| jsonb | 171.4695 / 148.8835 | 55.0190 / 53.3425 | 38.0940 / 35.9300 | -67.75 / -64.05 | -77.27 / -75.76 | -30.70 / -32.91 |
| phrase_positive | 45.8375 / 62.8120 | 27.4335 / 32.9365 | 19.3745 / 30.4940 | -39.90 / -39.54 | -57.00 / -54.59 | -27.44 / -24.58 |
| inline | 0.6290 / 0.4655 | 0.5105 / 0.4600 | 0.6280 / 0.4075 | +3.02 / +1.42 | -3.19 / -7.66 | -3.86 / -8.17 |
| absent | 1.3845 / 1.1980 | 1.6855 / 1.2620 | 0.3840 / 0.3270 | +11.45 / +0.31 | -63.31 / -61.78 | -65.52 / -62.53 |
| or_forced | 160.3390 / 171.4855 | 166.1655 / 172.2575 | 171.7550 / 164.3390 | +1.90 / +4.14 | +5.95 / -2.79 | +3.75 / -1.93 |
| single_forced | 164.7060 / 161.6655 | 156.9205 / 154.5460 | 161.6585 / 155.4180 | +0.44 / -3.75 | +0.43 / -3.26 | +1.54 / -1.64 |
| inline_single | 2.9050 / 2.9150 | 2.8770 / 3.8450 | 3.0130 / 3.2300 | -0.38 / +3.50 | +3.11 / +0.73 | +5.09 / -4.52 |
| lossy_and | 143.6480 / 134.5925 | 148.9500 / 142.4840 | 144.8870 / 133.8080 | +5.26 / +1.78 | +0.20 / -0.67 | -4.42 / -2.54 |
| seq_control | 56.3950 / 69.5495 | 65.5045 / 68.5265 | 62.4425 / 61.5680 | +3.10 / -0.51 | +9.06 / -5.96 | +1.48 / -7.00 |

## Actual AM screen

Absolute columns and paired percentages below both use the internal real index_rescan/getbitmap/tbm_free loop process CPU. The module is compiled against the actual public headers and shared unchanged across all roles. These are not heap visibility or full SQL throughput measurements.

| Case | B loop CPU ms | L4 loop CPU ms | C9 loop CPU ms | L4/B CPU % | C9/B CPU % | C9/L4 CPU % |
|---|---:|---:|---:|---:|---:|---:|
| am_inline | 18.2737 / 18.3950 | 20.3404 / 20.2539 | 15.0749 / 15.3345 | +10.62 / +10.37 | -17.89 / -17.05 | -25.10 / -24.19 |
| am_absent | 56.6929 / 58.7498 | 53.1101 / 58.6210 | 7.0791 / 7.2361 | -5.77 / -3.20 | -87.41 / -88.04 | -86.66 / -87.58 |
| am_skew1000 | 74.2673 / 73.6087 | 22.5953 / 22.7221 | 14.3709 / 13.7170 | -69.62 / -69.42 | -80.76 / -81.15 | -36.89 / -38.81 |
| am_full | 103.1329 / 98.8109 | 101.8984 / 99.1288 | 99.1422 / 99.1054 | -1.18 / +0.61 | -4.63 / -0.33 | -3.14 / -0.14 |

## Negative alternatives and variable controls

L8 and L9 alone do not remove the native inline penalty: L8/B AM CPU +5.97/+7.09%, L9/B +4.58/+5.11%. L9 OR CPU is +3.75/+6.90%. Their complete observations are retained, not hidden by the C9 selection. V7 is a separate failed layout experiment, documented in R2-RESULTS.md.

C9 OR is +5.95/-2.79% and Seq +9.06/-5.96% across reversed cohorts. The exact-binary T/B Seq control itself moves -2.13/+8.34%. This is evidence of variability and lack of a repeated screen regression, not proof of a harmless explanation for older repeated costs. Full SQL controls remain required. B/T absent CPU differs +15.25/-2.67% in the short SQL command while its AM CPU difference is +0.01/-1.66%; all controls and boundaries remain separate.

All absolute min/median/max, SD/MAD, raw observations, each metric and all 15 direct role pairs are in results-r3/screen-cohort*/tables and evidence-r3/screen-r1. Independent reconstruction matched both complete raw cohorts (only cross-Python standard deviation rounding at relative 3e-15 allowed). The screen collector verified all 19 own clusters shut down, all 12 measured backend PIDs absent, six unchanged installs, final 7726-source inventory, seed, runtime and module identities.

The full candidate diff patches/gin-lazy-adaptive-v9-over-fixed-b72.diff was independently applied to the exact fixed baseline in a temporary directory; all three resulting code files match the executed C9 source snapshot.
