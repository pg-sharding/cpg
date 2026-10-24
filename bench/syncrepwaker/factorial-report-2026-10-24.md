# Incremental synchronous replication wakeup experiments

Measured on 2026-10-24. [Results JSON](factorial-results-2026-10-24.json), [environment and provenance](factorial-environment-2026-10-24.json), [full raw-log audit](factorial-log-audit-2026-10-24.json).

The bounded-prefix change improves RAM saturation TPS by **3.1%** and p50 at a common 50k/s by **4.1%**. Notification coalescing alone has no consistent benefit across these workloads. Together they improve RAM saturation TPS by **4.1%** and fixed-rate p50 by **7.0%**, while saturation p99.9 rises **7.3%**. Persistent-disk results are mixed. On cross-AZ insert32k, the combined variant loses **9.7% TPS** and raises p50 **6.2%**; its paired TPS median is **-6.4%**, with a range of **-11.5% to +0.2%**. These results support a targeted RAM experiment, not a general replacement for the control.

The control (`current-hybrid8`) contains the earlier latch-after-unlock change. It is not pristine MDB. All four variants enable the waker with direct limit 8. `prefix-hybrid8` adds only bounded direct wakeups, `coalesce-hybrid8` adds only pending-notification coalescing, and `hybrid8` adds both.

Cells below show **Δ TPS / Δ p50 / Δ p99**, calculated from medians of the same three rotating rounds. Positive TPS and negative latency are improvements. Fixed-rate latency includes scheduling lag. Saturation latency compares different achieved throughputs. Shared-VM and disk variability limit conclusions from small changes.

## Independent effects relative to the current implementation

| Dataset / case | Prefix only | Coalescing only | Both |
| --- | ---: | ---: | ---: |
| crossaz-tls / batch10-sat | +0.1% / -0.3% / +8.6% | -3.9% / +3.6% / +4.3% | -0.9% / +1.2% / -5.3% |
| crossaz-tls / batch1000-sat | -2.4% / -1.1% / +1.4% | +2.4% / +0.0% / -16.1% | +1.2% / -1.2% / -17.5% |
| crossaz-tls / insert-c1-sat | -2.0% / +1.7% / -0.9% | -5.2% / +3.3% / +7.6% | -1.6% / +1.6% / -1.9% |
| crossaz-tls / insert32k-sat | -3.1% / +0.3% / -1.1% | -6.0% / -2.0% / +3.5% | -9.7% / +6.2% / +3.8% |
| crossaz-tls / simple-update-sat | -6.5% / +5.6% / +12.3% | -2.7% / +1.5% / +19.6% | -1.2% / +1.2% / +3.0% |
| local-tls / batch10-sat | -1.5% / +1.7% / +9.8% | +0.7% / -0.8% / -4.6% | -2.8% / +2.8% / -4.8% |
| local-tls / batch1000-sat | +5.2% / -5.0% / -4.6% | +3.9% / -2.8% / +1.4% | +1.8% / -1.7% / +0.2% |
| local-tls / insert-c1-sat | -9.0% / +10.4% / +4.7% | -5.2% / +5.2% / +7.1% | -2.5% / +2.4% / +4.4% |
| local-tls / insert32k-sat | +7.0% / -8.0% / +28.1% | +5.3% / -7.8% / +20.1% | +3.2% / -4.0% / -0.1% |
| local-tls / simple-update-sat | +0.2% / -0.4% / +4.2% | -0.3% / +0.5% / -0.4% | +0.8% / -0.7% / -3.3% |
| ram-rate50k / micro-c128-rate | -0.0% / -4.1% / +1.5% | -0.0% / +2.8% / +22.4% | -0.0% / -7.0% / -4.4% |
| ram-sat / micro-c128-sat | +3.1% / -5.0% / +0.5% | -0.8% / +0.6% / +2.1% | +4.1% / -5.7% / -0.2% |

## Conditional effects

These comparisons show whether one change helps when the other is already enabled. The same Δ TPS / Δ p50 / Δ p99 notation applies.

| Dataset / case | Add prefix to coalescing | Add coalescing to prefix |
| --- | ---: | ---: |
| crossaz-tls / batch10-sat | +3.1% / -2.3% / -9.2% | -1.0% / +1.5% / -12.8% |
| crossaz-tls / batch1000-sat | -1.1% / -1.3% / -1.6% | +3.7% / -0.2% / -18.6% |
| crossaz-tls / insert-c1-sat | +3.7% / -1.7% / -8.9% | +0.4% / -0.2% / -1.0% |
| crossaz-tls / insert32k-sat | -3.9% / +8.4% / +0.2% | -6.8% / +5.9% / +5.0% |
| crossaz-tls / simple-update-sat | +1.5% / -0.3% / -13.8% | +5.7% / -4.2% / -8.2% |
| local-tls / batch10-sat | -3.5% / +3.6% / -0.2% | -1.3% / +1.1% / -13.3% |
| local-tls / batch1000-sat | -2.0% / +1.1% / -1.2% | -3.2% / +3.5% / +5.1% |
| local-tls / insert-c1-sat | +2.9% / -2.6% / -2.5% | +7.2% / -7.2% / -0.2% |
| local-tls / insert32k-sat | -2.0% / +4.1% / -16.9% | -3.6% / +4.3% / -22.0% |
| local-tls / simple-update-sat | +1.1% / -1.2% / -2.9% | +0.6% / -0.4% / -7.2% |
| ram-rate50k / micro-c128-rate | -0.0% / -9.6% / -21.9% | +0.0% / -3.1% / -5.8% |
| ram-sat / micro-c128-sat | +5.0% / -6.2% / -2.3% | +1.0% / -0.7% / -0.8% |

## Paired TPS changes

Each cell pairs a candidate with the control from the same rotating round/seed, then shows the median percentage and observed minimum/maximum. This helps expose drift between rounds. The range is not a confidence interval; these values can differ from ratios of medians above.

| Dataset / case | Prefix only | Coalescing only | Both |
| --- | ---: | ---: | ---: |
| crossaz-tls / batch10-sat | -1.6% [-12.0, +0.4] | -3.9% [-6.8, -1.9] | +0.3% [-5.0, +3.6] |
| crossaz-tls / batch1000-sat | +3.2% [-2.6, +3.8] | +2.4% [-3.7, +6.4] | -1.6% [-2.9, +7.6] |
| crossaz-tls / insert-c1-sat | +1.8% [-5.4, +5.0] | -5.2% [-6.8, +1.6] | -2.1% [-3.0, +5.4] |
| crossaz-tls / insert32k-sat | -2.3% [-10.9, +7.7] | -3.3% [-8.0, -0.7] | -6.4% [-11.5, +0.2] |
| crossaz-tls / simple-update-sat | -6.7% [-7.3, +4.7] | -1.8% [-2.7, -1.4] | +0.1% [-2.0, +3.4] |
| local-tls / batch10-sat | -2.3% [-4.5, -1.5] | +0.7% [-5.6, +1.1] | -2.8% [-8.5, +0.3] |
| local-tls / batch1000-sat | +0.0% [+0.0, +5.2] | +3.5% [-3.9, +3.9] | +1.8% [-6.2, +2.7] |
| local-tls / insert-c1-sat | +3.3% [-9.0, +5.2] | -4.6% [-5.2, +6.5] | -1.7% [-2.5, +8.2] |
| local-tls / insert32k-sat | -4.2% [-8.2, +7.0] | +0.4% [-14.7, +5.3] | -0.2% [-17.4, +3.2] |
| local-tls / simple-update-sat | -0.2% [-1.0, +1.9] | -0.4% [-0.6, +3.2] | +2.5% [+0.5, +2.7] |
| ram-rate50k / micro-c128-rate | +0.0% [-0.0, +0.0] | +0.0% [-0.0, +0.0] | +0.0% [-0.0, +0.0] |
| ram-sat / micro-c128-sat | +3.6% [+3.1, +3.7] | -0.8% [-0.9, -0.3] | +4.1% [+3.8, +4.7] |

## Absolute results and control-relative changes

| Dataset / case | Variant | Runs | TPS (Δ current-hybrid8) | p50 ms (Δ) | p95 ms (Δ) | p99 ms (Δ) | p99.9 ms (Δ) | TPS range | p99 range ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| crossaz-tls / batch10-sat | current-hybrid8 | 3 | 11,810 | 9.693 | 16.902 | 28.017 | 59.438 | 11,667–12,012 | 25.857–28.746 |
| crossaz-tls / batch10-sat | hybrid8 | 3 | 11,701 (-0.9%) | 9.808 (+1.2%) | 17.562 (+3.9%) | 26.540 (-5.3%) | 48.226 (-18.9%) | 11,410–12,241 | 25.794–29.155 |
| crossaz-tls / batch10-sat | coalesce-hybrid8 | 3 | 11,353 (-3.9%) | 10.043 (+3.6%) | 18.675 (+10.5%) | 29.217 (+4.3%) | 46.251 (-22.2%) | 11,191–11,451 | 26.601–29.835 |
| crossaz-tls / batch10-sat | prefix-hybrid8 | 3 | 11,818 (+0.1%) | 9.662 (-0.3%) | 17.206 (+1.8%) | 30.430 (+8.6%) | 49.009 (-17.5%) | 10,267–11,862 | 29.168–34.739 |
| crossaz-tls / batch1000-sat | current-hybrid8 | 3 | 1,821 | 59.077 | 121.688 | 238.304 | 567.792 | 1,711–1,939 | 147.557–420.018 |
| crossaz-tls / batch1000-sat | hybrid8 | 3 | 1,842 (+1.2%) | 58.340 (-1.2%) | 118.950 (-2.3%) | 196.703 (-17.5%) | 541.644 (-4.6%) | 1,791–1,882 | 150.844–374.365 |
| crossaz-tls / batch1000-sat | coalesce-hybrid8 | 3 | 1,863 (+2.4%) | 59.106 (+0.0%) | 116.888 (-3.9%) | 199.849 (-16.1%) | 652.619 (+14.9%) | 1,821–1,868 | 172.481–253.004 |
| crossaz-tls / batch1000-sat | prefix-hybrid8 | 3 | 1,777 (-2.4%) | 58.453 (-1.1%) | 121.373 (-0.3%) | 241.672 (+1.4%) | 621.523 (+9.5%) | 1,774–2,001 | 139.679–428.594 |
| crossaz-tls / insert-c1-sat | current-hybrid8 | 3 | 130 | 7.112 | 10.888 | 18.123 | 23.502 | 121–132 | 14.205–18.539 |
| crossaz-tls / insert-c1-sat | hybrid8 | 3 | 127 (-1.6%) | 7.224 (+1.6%) | 10.900 (+0.1%) | 17.777 (-1.9%) | 26.387 (+12.3%) | 127–128 | 16.155–19.274 |
| crossaz-tls / insert-c1-sat | coalesce-hybrid8 | 3 | 123 (-5.2%) | 7.349 (+3.3%) | 11.824 (+8.6%) | 19.504 (+7.6%) | 25.927 (+10.3%) | 121–125 | 19.265–20.778 |
| crossaz-tls / insert-c1-sat | prefix-hybrid8 | 3 | 127 (-2.0%) | 7.235 (+1.7%) | 11.432 (+5.0%) | 17.955 (-0.9%) | 24.170 (+2.8%) | 125–132 | 15.961–18.276 |
| crossaz-tls / insert32k-sat | current-hybrid8 | 3 | 2,439 | 36.816 | 109.502 | 301.296 | 360.946 | 2,194–2,489 | 235.278–302.688 |
| crossaz-tls / insert32k-sat | hybrid8 | 3 | 2,202 (-9.7%) | 39.116 (+6.2%) | 122.408 (+11.8%) | 312.628 (+3.8%) | 394.792 (+9.4%) | 2,198–2,281 | 292.728–330.251 |
| crossaz-tls / insert32k-sat | coalesce-hybrid8 | 3 | 2,291 (-6.0%) | 36.081 (-2.0%) | 118.237 (+8.0%) | 311.908 (+3.5%) | 376.292 (+4.3%) | 2,177–2,357 | 295.083–328.546 |
| crossaz-tls / insert32k-sat | prefix-hybrid8 | 3 | 2,363 (-3.1%) | 36.938 (+0.3%) | 113.134 (+3.3%) | 297.854 (-1.1%) | 361.782 (+0.2%) | 2,217–2,383 | 291.341–297.998 |
| crossaz-tls / simple-update-sat | current-hybrid8 | 3 | 10,121 | 11.776 | 18.031 | 24.937 | 65.276 | 9,220–10,206 | 24.734–32.378 |
| crossaz-tls / simple-update-sat | hybrid8 | 3 | 10,000 (-1.2%) | 11.914 (+1.2%) | 18.559 (+2.9%) | 25.685 (+3.0%) | 68.609 (+5.1%) | 9,531–10,135 | 25.161–27.770 |
| crossaz-tls / simple-update-sat | coalesce-hybrid8 | 3 | 9,848 (-2.7%) | 11.947 (+1.5%) | 19.672 (+9.1%) | 29.813 (+19.6%) | 67.773 (+3.8%) | 9,089–10,022 | 27.190–35.171 |
| crossaz-tls / simple-update-sat | prefix-hybrid8 | 3 | 9,463 (-6.5%) | 12.434 (+5.6%) | 20.388 (+13.1%) | 27.993 (+12.3%) | 68.836 (+5.5%) | 9,442–9,649 | 27.431–32.147 |
| local-tls / batch10-sat | current-hybrid8 | 3 | 24,430 | 4.824 | 6.258 | 9.515 | 84.729 | 23,460–27,020 | 8.531–10.406 |
| local-tls / batch10-sat | hybrid8 | 3 | 23,735 (-2.8%) | 4.958 (+2.8%) | 6.534 (+4.4%) | 9.063 (-4.8%) | 84.142 (-0.7%) | 23,541–24,711 | 8.675–9.376 |
| local-tls / batch10-sat | coalesce-hybrid8 | 3 | 24,591 (+0.7%) | 4.784 (-0.8%) | 6.346 (+1.4%) | 9.080 (-4.6%) | 83.903 (-1.0%) | 23,722–25,497 | 8.925–10.031 |
| local-tls / batch10-sat | prefix-hybrid8 | 3 | 24,057 (-1.5%) | 4.904 (+1.7%) | 6.448 (+3.0%) | 10.449 (+9.8%) | 83.104 (-1.9%) | 22,913–25,795 | 10.237–10.729 |
| local-tls / batch1000-sat | current-hybrid8 | 3 | 1,149 | 97.272 | 179.470 | 192.097 | 246.016 | 1,104–1,282 | 171.558–199.940 |
| local-tls / batch1000-sat | hybrid8 | 3 | 1,169 (+1.8%) | 95.605 (-1.7%) | 177.233 (-1.2%) | 192.520 (+0.2%) | 326.226 (+32.6%) | 1,134–1,202 | 188.195–197.396 |
| local-tls / batch1000-sat | coalesce-hybrid8 | 3 | 1,193 (+3.9%) | 94.562 (-2.8%) | 174.656 (-2.7%) | 194.768 (+1.4%) | 214.633 (-12.8%) | 1,144–1,231 | 187.578–196.067 |
| local-tls / batch1000-sat | prefix-hybrid8 | 3 | 1,209 (+5.2%) | 92.390 (-5.0%) | 172.200 (-4.1%) | 183.252 (-4.6%) | 229.620 (-6.7%) | 1,105–1,282 | 176.616–196.044 |
| local-tls / insert-c1-sat | current-hybrid8 | 3 | 387 | 2.501 | 3.122 | 4.032 | 6.088 | 308–422 | 3.741–4.478 |
| local-tls / insert-c1-sat | hybrid8 | 3 | 378 (-2.5%) | 2.562 (+2.4%) | 3.152 (+1.0%) | 4.210 (+4.4%) | 5.824 (-4.3%) | 333–415 | 3.812–4.685 |
| local-tls / insert-c1-sat | coalesce-hybrid8 | 3 | 367 (-5.2%) | 2.630 (+5.2%) | 3.323 (+6.4%) | 4.317 (+7.1%) | 6.590 (+8.2%) | 328–403 | 3.846–4.503 |
| local-tls / insert-c1-sat | prefix-hybrid8 | 3 | 352 (-9.0%) | 2.761 (+10.4%) | 3.276 (+4.9%) | 4.220 (+4.7%) | 6.746 (+10.8%) | 318–444 | 3.597–4.649 |
| local-tls / insert32k-sat | current-hybrid8 | 3 | 1,500 | 64.203 | 169.971 | 309.843 | 524.579 | 1,477–2,065 | 304.760–351.251 |
| local-tls / insert32k-sat | hybrid8 | 3 | 1,547 (+3.2%) | 61.619 (-4.0%) | 165.332 (-2.7%) | 309.405 (-0.1%) | 522.173 (-0.5%) | 1,473–1,706 | 285.140–352.978 |
| local-tls / insert32k-sat | coalesce-hybrid8 | 3 | 1,579 (+5.3%) | 59.192 (-7.8%) | 159.260 (-6.3%) | 372.267 (+20.1%) | 551.673 (+5.2%) | 1,484–1,762 | 293.683–498.815 |
| local-tls / insert32k-sat | prefix-hybrid8 | 3 | 1,605 (+7.0%) | 59.098 (-8.0%) | 159.808 (-6.0%) | 396.808 (+28.1%) | 574.224 (+9.5%) | 1,415–1,896 | 309.042–477.923 |
| local-tls / simple-update-sat | current-hybrid8 | 3 | 15,224 | 8.001 | 11.544 | 13.513 | 65.383 | 14,850–15,272 | 13.169–16.522 |
| local-tls / simple-update-sat | hybrid8 | 3 | 15,348 (+0.8%) | 7.942 (-0.7%) | 11.148 (-3.4%) | 13.073 (-3.3%) | 64.447 (-1.4%) | 15,257–15,602 | 12.853–13.694 |
| local-tls / simple-update-sat | coalesce-hybrid8 | 3 | 15,177 (-0.3%) | 8.039 (+0.5%) | 11.350 (-1.7%) | 13.458 (-0.4%) | 59.297 (-9.3%) | 15,157–15,328 | 12.682–14.231 |
| local-tls / simple-update-sat | prefix-hybrid8 | 3 | 15,249 (+0.2%) | 7.971 (-0.4%) | 11.477 (-0.6%) | 14.080 (+4.2%) | 59.054 (-9.7%) | 14,708–15,509 | 13.463–14.395 |
| ram-rate50k / micro-c128-rate | current-hybrid8 | 3 | 49,958 | 0.752 | 1.304 | 2.342 | 13.361 | 49,938–49,994 | 2.291–3.990 |
| ram-rate50k / micro-c128-rate | hybrid8 | 3 | 49,957 (-0.0%) | 0.699 (-7.0%) | 1.230 (-5.7%) | 2.239 (-4.4%) | 13.432 (+0.5%) | 49,939–49,996 | 2.063–2.346 |
| ram-rate50k / micro-c128-rate | coalesce-hybrid8 | 3 | 49,958 (-0.0%) | 0.773 (+2.8%) | 1.363 (+4.5%) | 2.866 (+22.4%) | 13.464 (+0.8%) | 49,939–49,998 | 2.308–3.430 |
| ram-rate50k / micro-c128-rate | prefix-hybrid8 | 3 | 49,956 (-0.0%) | 0.721 (-4.1%) | 1.263 (-3.1%) | 2.377 (+1.5%) | 13.345 (-0.1%) | 49,939–49,995 | 2.350–2.467 |
| ram-sat / micro-c128-sat | current-hybrid8 | 3 | 83,253 | 1.432 | 2.131 | 2.594 | 4.409 | 82,845–83,265 | 2.588–2.618 |
| ram-sat / micro-c128-sat | hybrid8 | 3 | 86,693 (+4.1%) | 1.351 (-5.7%) | 2.093 (-1.8%) | 2.588 (-0.2%) | 4.730 (+7.3%) | 86,423–86,744 | 2.581–2.605 |
| ram-sat / micro-c128-sat | coalesce-hybrid8 | 3 | 82,565 (-0.8%) | 1.441 (+0.6%) | 2.159 (+1.3%) | 2.648 (+2.1%) | 4.756 (+7.9%) | 82,483–82,607 | 2.639–2.652 |
| ram-sat / micro-c128-sat | prefix-hybrid8 | 3 | 85,849 (+3.1%) | 1.361 (-5.0%) | 2.106 (-1.2%) | 2.608 (+0.5%) | 4.853 (+10.1%) | 85,834–86,304 | 2.582–2.623 |

## CPU cost

CPU includes pgbench and both servers. Costs use process-counter deltas per completed transaction; remote snapshots bracket a slightly longer interval. These are not profiler samples.

| Dataset / case | Variant | All CPU us/tx | Sender us/tx | Waker us/tx |
| --- | --- | ---: | ---: | ---: |
| crossaz-tls / batch10-sat | current-hybrid8 | 207.33 | 7.74 | 6.29 |
| crossaz-tls / batch10-sat | prefix-hybrid8 | 210.87 | 10.41 | 3.64 |
| crossaz-tls / batch10-sat | coalesce-hybrid8 | 206.63 | 7.62 | 6.25 |
| crossaz-tls / batch10-sat | hybrid8 | 210.32 | 10.47 | 3.63 |
| crossaz-tls / batch1000-sat | current-hybrid8 | 2094.64 | 46.74 | 7.60 |
| crossaz-tls / batch1000-sat | prefix-hybrid8 | 2100.15 | 48.73 | 5.50 |
| crossaz-tls / batch1000-sat | coalesce-hybrid8 | 2102.20 | 46.68 | 7.69 |
| crossaz-tls / batch1000-sat | hybrid8 | 2130.92 | 49.16 | 5.43 |
| crossaz-tls / insert-c1-sat | current-hybrid8 | 640.68 | 154.78 | 0.00 |
| crossaz-tls / insert-c1-sat | prefix-hybrid8 | 646.71 | 159.21 | 0.00 |
| crossaz-tls / insert-c1-sat | coalesce-hybrid8 | 645.42 | 155.38 | 0.00 |
| crossaz-tls / insert-c1-sat | hybrid8 | 639.47 | 155.70 | 0.00 |
| crossaz-tls / insert32k-sat | current-hybrid8 | 926.31 | 31.23 | 7.03 |
| crossaz-tls / insert32k-sat | prefix-hybrid8 | 934.35 | 33.99 | 4.87 |
| crossaz-tls / insert32k-sat | coalesce-hybrid8 | 932.80 | 32.08 | 7.12 |
| crossaz-tls / insert32k-sat | hybrid8 | 939.77 | 33.66 | 5.00 |
| crossaz-tls / simple-update-sat | current-hybrid8 | 557.26 | 9.48 | 6.42 |
| crossaz-tls / simple-update-sat | prefix-hybrid8 | 562.01 | 12.28 | 3.33 |
| crossaz-tls / simple-update-sat | coalesce-hybrid8 | 562.98 | 9.60 | 6.40 |
| crossaz-tls / simple-update-sat | hybrid8 | 559.09 | 12.48 | 3.16 |
| local-tls / batch10-sat | current-hybrid8 | 182.79 | 3.88 | 5.81 |
| local-tls / batch10-sat | prefix-hybrid8 | 186.87 | 6.05 | 3.39 |
| local-tls / batch10-sat | coalesce-hybrid8 | 184.93 | 3.92 | 5.82 |
| local-tls / batch10-sat | hybrid8 | 186.06 | 6.03 | 3.36 |
| local-tls / batch1000-sat | current-hybrid8 | 2365.82 | 71.40 | 7.41 |
| local-tls / batch1000-sat | prefix-hybrid8 | 2346.83 | 70.33 | 5.79 |
| local-tls / batch1000-sat | coalesce-hybrid8 | 2377.84 | 71.46 | 7.54 |
| local-tls / batch1000-sat | hybrid8 | 2384.50 | 72.68 | 5.56 |
| local-tls / insert-c1-sat | current-hybrid8 | 550.59 | 130.37 | 0.00 |
| local-tls / insert-c1-sat | prefix-hybrid8 | 556.34 | 135.26 | 0.00 |
| local-tls / insert-c1-sat | coalesce-hybrid8 | 554.52 | 133.50 | 0.00 |
| local-tls / insert-c1-sat | hybrid8 | 557.25 | 136.13 | 0.00 |
| local-tls / insert32k-sat | current-hybrid8 | 976.86 | 39.01 | 7.33 |
| local-tls / insert32k-sat | prefix-hybrid8 | 978.94 | 39.59 | 5.01 |
| local-tls / insert32k-sat | coalesce-hybrid8 | 976.84 | 48.44 | 7.38 |
| local-tls / insert32k-sat | hybrid8 | 977.94 | 40.07 | 5.17 |
| local-tls / simple-update-sat | current-hybrid8 | 489.23 | 4.62 | 5.66 |
| local-tls / simple-update-sat | prefix-hybrid8 | 491.04 | 7.12 | 2.75 |
| local-tls / simple-update-sat | coalesce-hybrid8 | 489.89 | 4.88 | 5.60 |
| local-tls / simple-update-sat | hybrid8 | 487.30 | 7.10 | 2.63 |
| ram-rate50k / micro-c128-rate | current-hybrid8 | 136.42 | 8.45 | 4.12 |
| ram-rate50k / micro-c128-rate | prefix-hybrid8 | 137.20 | 10.29 | 1.64 |
| ram-rate50k / micro-c128-rate | coalesce-hybrid8 | 137.47 | 8.29 | 4.19 |
| ram-rate50k / micro-c128-rate | hybrid8 | 137.21 | 10.49 | 1.55 |
| ram-sat / micro-c128-sat | current-hybrid8 | 90.45 | 2.92 | 4.49 |
| ram-sat / micro-c128-sat | prefix-hybrid8 | 88.65 | 3.49 | 2.89 |
| ram-sat / micro-c128-sat | coalesce-hybrid8 | 91.36 | 2.92 | 4.50 |
| ram-sat / micro-c128-sat | hybrid8 | 87.71 | 3.51 | 2.88 |

## Conditions and validation

There are **144 accepted runs**: 12 cases, four variants, and three rotating rounds (seeds 1000/1001/1002), grouped into 36 complete phases. Every run uses 5 seconds of warmup and a 20-second measurement window. The audit passed for **48,710,485 window transactions** and **69,919,896 full raw-log records**, including warmup and tail. Counts agree with pgbench, raw logs cover every window, and there are no failed/skipped transactions, missing CPU samples, or checkpoint/restartpoint events inside windows.

The primary and pgbench run on `zov` (`51.250.6.134`, `10.128.0.41`, ru-central1-a). The cross-AZ standby runs on `pgfuzz` (`158.160.212.50`, `10.0.0.8`, ru-central1-d). Both guests expose 8 vCPUs with AMD EPYC Genoa CPUs and about 16 GiB RAM. The standby always uses the pristine baseline installation. Private-IP ping averaged **5.149 ms before** and **5.188 ms after**, with no packet loss in either 10-packet sample.

RAM cases put both servers' data and WAL on tmpfs, with TLS disabled. The five disk cases run locally and across AZs with client and replication TLS enabled: pgbench simple-update, INSERT batches of 10 and 1000 rows, one INSERT client, and 128 clients inserting uncompressed external 32-KiB payloads. Other cases use 128 clients. The fixed RAM rate was selected before these runs and is identical for all variants. All use prepared mode, synchronous_commit=on (remote flush), fsync and full_page_writes on, 256-MiB shared buffers, 64-MiB WAL buffers, max_wal_size=16GB, autovacuum off, and checkpoint_timeout=30min. Within each rotating round, the four variant runs restore the same stopped primary and standby snapshots.

The primary CPU interference threshold is 10%; the separate standby threshold is 60%, retained from the previous shared-VM experiment. Actual maximum unattributed busy CPU in accepted windows was **1.24% on the primary** and **11.73% on the standby**. No scored rounds were rejected by CPU guards. One initial cross-AZ attempt failed SSH authentication before producing any measured rows; it was resumed with a dedicated persistent VM-to-VM SSH connection. Its failed-attempt metadata remains in the environment JSON. Four local smoke runs are excluded. Unrelated workloads remained running. CPU guards do not isolate underlying storage or network variability.

Cross-AZ single-client windows contain 2,415–2,649 transactions each, so p99.9 in that case depends on only a few observations. Three-run ranges are descriptive, and small differences on shared disks should be treated as exploratory.

The seven synchronous replication recovery tests passed **158 assertions** with assertions and injection points enabled. The final strengthened notification-race test also passed its 19 assertions after explicitly waiting for ACK publication to complete. The Linux harness passed all ten unit tests. Release builds use the same `-O2 -g -fno-omit-frame-pointer` flags, OpenSSL, and disabled assertions. The driver requires four distinct postgres hashes, and every phase records the hashes and effective GUCs.

Source versions: the control has core behavior from `2e1e7821b1c` (source snapshot `b399b107352`); prefix-only is `7641cc29e352e298a88b92d3fb54b2987e23036c`; both is `b9431a07f4945b49e17346427d1ab51254fb2dc3`. Coalescing-only applies the five-file core diff from `7641cc29e35..b9431a07f49` to the control. The exact diff hash, source hashes, reconstruction command, and compiler settings are recorded in the environment JSON.

Selected compressed raw logs and phase metadata remain under `/home/reshke/pgpg2/compare-factorial-2026-10-24` on zov. The `collected` directory contains the audited canonical JSONs. All disposable benchmark servers have stopped on both VMs, RAM data has been removed, and the dedicated SSH master is closed.
