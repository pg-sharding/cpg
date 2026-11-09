# GIN fixed-source SQL: all cases

B72 plus the common prerequisite in every role. A4=advance V4, L4=lazy V4; independent alternatives. T is the exact B executable in a separate cluster.

2800 raw / 2400 retained / 400 warm samples. Four full builds passed original 239 core tests each. All ordinary answers/plans passed; all 13 own clusters stopped.

Absolute min/median/max, sample deviation, MAD and all direct values are in absolute.json/CSV and pairs.json/CSV. Each cohort and metric remains separate. Paired spreads are observed ranges, not population confidence intervals.

The host is shared. Exact-twin and Seq controls remain visible. No new native, CREATE INDEX, combined-candidate or current-master result follows.

## Cohort 0

Absolute retained medians in milliseconds; percentages are medians of twelve direct same-round ratios.

| Case | B ms | T ms | A4 ms | L4 ms | A4/B Exec % | L4/B Exec % | A4/B CPU % | L4/B CPU % | T/B CPU % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| skew1000 | 79.2875 | 78.8395 | 34.8645 | 29.4185 | -55.99 | -63.35 | -55.80 | -63.07 | -0.21 |
| skew127 | 149.0540 | 151.7325 | 106.2500 | 163.8715 | -28.89 | -1.06 | -28.80 | -0.98 | +0.58 |
| skew17 | 103.1560 | 101.1585 | 93.3160 | 104.7320 | -10.18 | -0.64 | -10.13 | -0.63 | -1.10 |
| separate_keys | 99.0370 | 112.8430 | 39.2195 | 36.8890 | -53.27 | -59.48 | -52.97 | -59.21 | +0.18 |
| dense_and | 90.2945 | 88.2010 | 88.1535 | 88.5540 | +0.12 | +0.73 | -0.62 | +0.75 | +1.25 |
| or_forced | 162.0480 | 163.8310 | 171.1635 | 168.9820 | -0.65 | +2.01 | -0.63 | +2.00 | +0.88 |
| single_forced | 150.4905 | 154.6050 | 156.0215 | 155.2095 | +2.43 | +2.63 | +2.44 | +2.60 | +1.47 |
| single_rare | 6.3395 | 6.3355 | 6.2780 | 6.2660 | -1.05 | +0.24 | -0.78 | +0.25 | +1.01 |
| inline | 0.4670 | 0.4555 | 0.4370 | 0.4800 | -6.35 | +3.84 | -3.77 | +5.60 | -0.81 |
| prefix | 93.9860 | 95.5570 | 94.3290 | 94.1060 | -0.49 | -0.53 | -0.56 | -0.53 | -0.71 |
| phrase | 78.3595 | 78.4875 | 35.3850 | 29.3275 | -54.80 | -62.75 | -54.61 | -62.43 | -0.20 |
| not | 42.9130 | 48.5940 | 24.7090 | 26.4385 | -53.61 | -46.47 | -53.33 | -46.16 | +1.13 |
| intarray | 80.2470 | 81.5480 | 34.0210 | 28.1725 | -56.30 | -64.45 | -56.07 | -64.07 | +0.34 |
| builtin_array | 78.9805 | 79.6235 | 35.2365 | 28.3480 | -56.55 | -64.15 | -56.32 | -63.85 | -0.50 |
| jsonb | 153.2210 | 154.6565 | 66.0725 | 53.8735 | -56.68 | -64.69 | -56.53 | -64.52 | +0.14 |
| lossy_and | 141.4580 | 140.5360 | 138.8785 | 138.3290 | -1.16 | -2.29 | -1.16 | -2.31 | -0.48 |
| seq_control | 64.6950 | 67.5405 | 70.3315 | 71.1295 | +8.74 | +6.41 | +8.69 | +6.30 | +3.90 |
| phrase_positive | 45.5990 | 45.7670 | 23.4105 | 27.3885 | -48.57 | -39.70 | -48.26 | -39.40 | -0.39 |
| not_positive | 42.5880 | 43.5440 | 26.2230 | 27.4795 | -51.41 | -43.93 | -50.96 | -43.60 | +0.57 |
| skew_group4096 | 57.3435 | 58.0830 | 23.3880 | 11.5160 | -58.89 | -79.96 | -58.56 | -79.55 | +0.67 |
| array_dense | 1817.4445 | 1773.7590 | 1763.4170 | 1760.7900 | +0.01 | -1.59 | +0.01 | -1.59 | -1.49 |
| inline_single | 2.9220 | 2.9090 | 2.8890 | 2.9145 | -1.09 | +1.00 | -0.56 | +1.13 | -0.21 |
| absent | 1.3020 | 1.3095 | 1.3645 | 1.2850 | +7.10 | -0.90 | +7.26 | +0.84 | +0.56 |
| not_only | 190.8105 | 200.4735 | 194.4265 | 183.4270 | -2.37 | -4.41 | -2.36 | -4.43 | +0.51 |
| empty_array | 183.5960 | 181.8065 | 186.6310 | 189.5385 | +1.62 | +2.08 | +1.61 | +2.09 | +0.36 |

Retained root-plan IO/WAL totals and whole-command counters: `{"Shared Dirtied Blocks": 0, "Shared Read Blocks": 0, "Shared Written Blocks": 0, "Temp Read Blocks": 0, "Temp Written Blocks": 0, "WAL Bytes": 0, "backend_read_bytes": 0, "backend_runqueue_ns": 72950193, "backend_write_bytes": 0}`.

## Cohort 1

Absolute retained medians in milliseconds; percentages are medians of twelve direct same-round ratios.

| Case | B ms | T ms | A4 ms | L4 ms | A4/B Exec % | L4/B Exec % | A4/B CPU % | L4/B CPU % | T/B CPU % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| skew1000 | 79.6255 | 80.3710 | 36.9435 | 29.8335 | -53.50 | -63.21 | -53.24 | -62.97 | +0.13 |
| skew127 | 157.1080 | 148.9055 | 104.1555 | 148.2635 | -29.43 | +0.50 | -29.35 | +0.49 | +0.83 |
| skew17 | 97.6600 | 97.6910 | 90.6210 | 99.9950 | -6.88 | +2.33 | -6.88 | +2.26 | -0.02 |
| separate_keys | 80.3070 | 80.9060 | 36.1415 | 38.0205 | -55.03 | -54.80 | -54.74 | -54.50 | +0.50 |
| dense_and | 94.6595 | 86.8560 | 91.5265 | 91.3610 | -2.09 | +3.83 | -2.07 | +3.85 | -0.07 |
| or_forced | 161.3520 | 160.7510 | 166.4095 | 163.1775 | +3.81 | +1.23 | +3.79 | +1.23 | +0.29 |
| single_forced | 159.3970 | 154.8785 | 160.7885 | 162.1150 | -1.88 | +2.57 | -1.90 | +2.58 | -0.72 |
| single_rare | 6.1470 | 6.1040 | 6.1265 | 6.1605 | -0.08 | +0.31 | +0.05 | +0.33 | -0.50 |
| inline | 0.4520 | 0.4700 | 0.4445 | 0.4725 | -2.21 | +3.54 | -1.78 | +5.17 | +2.38 |
| prefix | 98.7780 | 98.0755 | 99.9570 | 93.4460 | -1.64 | -0.14 | -1.65 | -0.15 | -1.00 |
| phrase | 78.9575 | 79.2630 | 36.1375 | 28.8640 | -54.28 | -63.74 | -54.08 | -63.48 | -0.14 |
| not | 37.4295 | 37.4480 | 15.6240 | 19.6470 | -58.32 | -47.52 | -57.93 | -47.16 | +0.06 |
| intarray | 78.6115 | 77.8595 | 35.0985 | 28.3175 | -55.20 | -64.11 | -54.99 | -63.86 | -0.76 |
| builtin_array | 77.5750 | 76.6780 | 34.7310 | 27.6675 | -54.96 | -64.45 | -54.72 | -64.19 | -1.05 |
| jsonb | 155.1050 | 155.9210 | 71.5810 | 54.6835 | -55.32 | -64.55 | -55.16 | -64.39 | -0.91 |
| lossy_and | 143.8640 | 146.0185 | 146.7215 | 140.5055 | +0.75 | -3.52 | +0.74 | -3.50 | +1.37 |
| seq_control | 63.3960 | 59.0275 | 70.1260 | 69.4675 | +11.27 | +8.13 | +11.21 | +8.06 | +1.30 |
| phrase_positive | 45.8435 | 47.8410 | 24.1550 | 27.6050 | -47.57 | -40.42 | -47.09 | -40.17 | +2.22 |
| not_positive | 42.4000 | 43.3075 | 18.7960 | 23.7730 | -56.01 | -42.13 | -55.64 | -41.68 | +2.39 |
| skew_group4096 | 61.4850 | 63.2150 | 29.4180 | 12.7400 | -54.48 | -80.57 | -54.14 | -80.27 | -0.10 |
| array_dense | 1755.8925 | 1830.9370 | 1699.4580 | 1767.7555 | -4.47 | -0.76 | -4.48 | -0.76 | +4.13 |
| inline_single | 2.8850 | 2.8595 | 2.9240 | 2.8765 | +1.98 | +0.09 | +2.30 | +1.13 | -0.84 |
| absent | 1.1785 | 1.1855 | 1.2595 | 1.2395 | +7.49 | +6.02 | +6.65 | +5.71 | +1.95 |
| not_only | 180.1045 | 179.9370 | 177.1895 | 181.5565 | +0.79 | +1.75 | +0.78 | +1.73 | +0.35 |
| empty_array | 180.2990 | 180.9230 | 181.6205 | 178.3925 | -0.91 | -0.19 | -0.93 | -0.19 | +0.06 |

Retained root-plan IO/WAL totals and whole-command counters: `{"Shared Dirtied Blocks": 0, "Shared Read Blocks": 0, "Shared Written Blocks": 0, "Temp Read Blocks": 0, "Temp Written Blocks": 0, "WAL Bytes": 0, "backend_read_bytes": 0, "backend_runqueue_ns": 54259325, "backend_write_bytes": 0}`.

