# GIN C9: repaired targets and addressed control repetitions

C9 fixes the measured native inline penalty and the absent cost while preserving large selective SQL gains. In a new same-source diagnostic, OR, dense AND and single-rare AM CPU improve in both reversed cohorts; unchanged OR/rare SQL controls improve too. Earlier full-SQL positive movements remain valid unresolved observations. No additional PostgreSQL source change was justified by this diagnostic, and no universal or current-master speedup is claimed.

Source remains 0ab3bd65c8957ea5e25f9ef8981401f0616d99de, experiments/gin-combined-v9-b72-20261110. Baseline is fixed B72 (72b9498df9a369e747f8d96efb5a6cd33c2451e2 plus the same prerequisite), fixed base8a8c475037bfde101da23cc9b0364c9c020eca93. The complete same C9 diff and its prior artifact verification are included. All code branches and failed earlier alternatives remain preserved.

## New real-AM CPU measurements

Each entry is cohort0 / cohort1, kept separate. Absolute columns and paired percentages both use internal process CPU for real index_rescan/index_getbitmap/tbm_free loops. Percentages are medians of direct same-round ratios, not ratios of aggregate medians. These are not SQL throughput or heap visibility.

| Case | B CPU ms | L4 CPU ms | C9 CPU ms | C9/B % | C9/T % | C9/L4 % |
|---|---:|---:|---:|---:|---:|---:|
| am_inline | 19.1205 / 17.9211 | 21.0060 / 19.7225 | 15.4816 / 14.8468 | -17.34 / -17.03 | -17.40 / -17.36 | -24.56 / -24.68 |
| am_absent | 57.0882 / 57.4234 | 56.2183 / 56.3149 | 7.0499 / 7.4556 | -87.69 / -86.89 | -87.58 / -87.02 | -87.37 / -86.85 |
| am_skew1000 | 72.8112 / 71.4141 | 22.4781 / 22.5331 | 13.6487 / 13.2828 | -81.36 / -81.39 | -81.23 / -81.53 | -39.70 / -40.95 |
| am_full | 101.8003 / 100.8355 | 98.9810 / 98.2205 | 96.7056 / 95.5690 | -4.97 / -4.50 | -4.77 / -5.44 | -2.34 / -2.37 |
| am_or | 113.5217 / 114.5873 | 113.7453 / 114.8879 | 110.4483 / 111.7898 | -2.56 / -1.98 | -2.55 / -1.35 | -2.77 / -2.61 |
| am_dense | 44.9046 / 44.3340 | 45.3722 / 45.0464 | 42.7025 / 42.2457 | -4.93 / -4.38 | -3.91 / -4.10 | -5.95 / -5.84 |
| am_rare | 10.9662 / 10.8188 | 11.0768 / 10.9530 | 10.7824 / 10.5558 | -1.87 / -2.47 | -3.72 / -2.55 | -2.61 / -3.69 |

## New SQL controls

Absolute medians are EXPLAIN executor ms. Paired percentages are whole-command backend CPU, a separate boundary. Commands/data are unchanged.

| Case | B executor ms | C9 executor ms | C9/B CPU % | T/B CPU % | C9/T CPU % | C9/L4 CPU % |
|---|---:|---:|---:|---:|---:|---:|
| or_forced | 158.3450 / 159.0190 | 155.5360 / 155.7635 | -2.05 / -2.04 | -1.38 / -0.06 | +0.45 / -2.11 | +1.31 / -2.30 |
| single_rare | 6.2600 / 6.0495 | 6.1725 / 5.9765 | -1.51 / -1.53 | -1.03 / +2.17 | -1.06 / -2.81 | -0.68 / -1.53 |
| inline | 0.4375 / 0.4540 | 0.4335 / 0.4245 | -0.11 / -5.29 | +0.60 / +3.61 | -3.09 / -7.42 | -8.00 / -8.49 |
| seq_control | 62.6345 / 57.6330 | 55.5175 / 60.9755 | -9.31 / +7.89 | +2.30 / -3.18 | -5.85 / +4.07 | -3.20 / -1.49 |

Seq changes sign (-9.31/+7.90% versus B); L4 also changes -1.58/+10.28%. Keep those data as off-path/control variability, without claiming a proven harmless cause or an algorithmic cause. No baseline-twin normalization is applied. The new OR/rare results do not erase the earlier full-SQL positives.

## Earlier complete 25-case SQL campaign

These are previously executed R3 observations, not new diagnostic results or pooled cohorts. The full immutable packet contains all 25 cases, all metrics, every pair/raw chronology and failed alternatives. HISTORICAL-R3.json pins this summary and its raw hashes/manifest. Absolute medians here are executor ms; percentages are paired backend CPU.

| Case | B executor ms | C9 executor ms | C9/B CPU % |
|---|---:|---:|---:|
| skew1000 | 80.9340 / 78.8805 | 21.6475 / 19.9840 | -72.94 / -74.20 |
| skew127 | 149.5775 / 150.9795 | 111.9625 / 114.4035 | -24.77 / -24.85 |
| jsonb | 158.4965 / 152.0990 | 36.4350 / 36.0025 | -76.29 / -76.36 |
| intarray | 79.3685 / 80.5080 | 19.7980 / 19.1425 | -74.95 / -75.72 |
| builtin_array | 83.9715 / 78.3405 | 21.7715 / 19.1550 | -73.42 / -75.85 |
| skew_group4096 | 60.1100 / 59.9025 | 6.9960 / 7.1060 | -88.21 / -87.69 |
| inline | 0.4725 / 0.4540 | 0.4500 / 0.4025 | +1.79 / -4.94 |
| absent | 2.1975 / 1.2610 | 0.4980 / 0.3345 | -66.99 / -62.97 |
| or_forced | 157.9975 / 156.1935 | 177.2810 / 159.7720 | +10.73 / +1.75 |
| single_rare | 6.1980 / 6.1535 | 6.4045 / 6.3715 | +3.49 / +2.34 |
| seq_control | 68.3005 / 56.9845 | 61.3625 / 55.0165 | -5.42 / -0.29 |

The historical inline SQL result is mixed versus B (+1.79/-4.94%) but improves versus L4 (-4.83/-8.96%). The diagnostic gives -0.11/-5.29% versus B and -8.00/-8.49% versus L4; native inline improves about 17% versus B and25% versus L4 in both diagnostic cohorts. These boundaries and experiments must stay separate.

The earlier OR (+10.73/+1.75%) and single-rare (+3.49/+2.34%) full-SQL costs are retained. They were not repeated in the address-specific SQL runs and no positive inner-AM cost repeats there. That narrows the evidence for another source edit; it does not prove the older SQL differences harmless. Keep the prototype experimental and check representative workloads before proposing a merge.

## Spread and checks

| Cohort | AM case | B CPU min / median / max ms | C9 CPU min / median / max ms |
|---:|---|---:|---:|
| 0 | am_inline | 18.133776 / 19.120526 / 30.171453 | 14.751669 / 15.481635 / 26.567654 |
| 0 | am_absent | 56.110963 / 57.088235 / 60.924257 | 6.869490 / 7.049891 / 9.470293 |
| 0 | am_or | 112.091431 / 113.521652 / 191.187931 | 107.620120 / 110.448290 / 131.630194 |
| 0 | am_dense | 44.303643 / 44.904574 / 46.121521 | 42.206715 / 42.702514 / 43.092154 |
| 0 | am_rare | 10.849032 / 10.966168 / 12.093601 | 10.528711 / 10.782442 / 12.490987 |
| 1 | am_inline | 17.811673 / 17.921062 / 18.850643 | 14.796567 / 14.846843 / 15.151129 |
| 1 | am_absent | 54.873977 / 57.423383 / 84.020421 | 7.054949 / 7.455579 / 10.087620 |
| 1 | am_or | 110.939171 / 114.587346 / 169.150989 | 108.367380 / 111.789762 / 170.559882 |
| 1 | am_dense | 43.830312 / 44.333988 / 60.007762 | 41.945022 / 42.245658 / 42.969830 |
| 1 | am_rare | 10.730504 / 10.818828 / 10.945688 | 10.485427 / 10.555752 / 10.798337 |

All absolute min/median/max, sample SD/MAD, native CPU/wall, SQL executor/whole-command CPU/client wall and all six direct pairs remain in results/cohort*/tables and JSON. Exact raw observations/status/oracles and software stacks are in evidence/run-r1. Independent local reconstruction matches both remote analyses, with only relative3e-15 cross-Python sample-SD rounding tolerated. No trimming,pooling or twin correction.

- New work reused the checked R3 build installations. No new PostgreSQL code/build/core-test execution is claimed. Prior eleven builds each passed original239 tests; new qualification repeats all 25 ordered Seq/GIN multiset/scalar/path checks and eight prepared comparisons/cached rescans on all six builds, plus seven exact AM answers per build. C9_assert checks exact first-page counts by independent decoding. All25 multisets repeat per timed role/cohort.
- VM158, same GCC13.3 release flags -O2 -g -fno-lto, no ICU/readline, OpenSSL. Four roles B/T/L4/C9, exact B/T ELF, two warm+12 retained balanced rounds per case, two fresh CPU0/4→4/0 cohorts with reversed slots/session births/case order. New totals1232 raw / 1056 retained / 176 warm. JIT/parallel/memoize/autovacuum off,512MB shared_buffers,system timing clock. Every measured call follows an extra literal-answer execution. All retained recorded IO/WAL and backend read/write byte counters are zero.
- Six separate original-query software profiles of B/C9 OR,rare,Seq passed before fresh timing clusters. They are diagnostic software samples, not PMU attribution or paired timings. No host configuration or foreign workload was changed. No archive database was used.
- Final collector verifies all15 own new cluster directories shut down, eight measured backend PIDs/sockets absent, all six reference installs/final7726-source inventory/seed/frozen runtime/AM module unchanged, and no process using owned install/build executables. The supervisor PIPELINE pending-collection status is an earlier checkpoint; FINAL-CHECKS and CLOSEOUT record successful later collection/reconstruction.

REPRODUCE.md contains exact source/setup/dependency/build/new-run commands and all seven AM loop counts. The same full candidate .diff is in patches/; this is not a new patch to stack. The English addendum is unsent. Prior-art scope remains bounded in PRIOR-ART.md, with no priority claim. No CREATE INDEX,current-master,independent-host confidence or general-regression-free claim.
