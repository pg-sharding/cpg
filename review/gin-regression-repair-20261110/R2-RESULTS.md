# Regression diagnosis and V7 negative result

These are newly executed R2 measurements on VM158, on fixed B72, not current PostgreSQL master. The initial R1 scan-key adapter error produced zero timing observations; its failure and stopped-cluster proofs are preserved. R2 corrected only the adapter and reused the same code and builds.

All five clean builds passed 239 original core tests. Both finite campaigns passed: null 660 raw/600 retained/60 warm; screen 3080 raw/2800 retained/280 warm. Final verification checked 34 shut-down cluster directories, 20 absent measured backend PIDs, all five unchanged installs, 7726 unchanged final source files, three unchanged seeds, both frozen runtime snapshots and all three unchanged AM modules. Independent local reconstruction matched all four raw cohorts; the only tolerated cross-Python rounding is at relative 3e-15 in sample standard deviation.

## V7 did not repair inline

V7 reduced GinScanEntryData from L4 848 to 832 bytes; baseline is 824. All 21 original field offsets matched. It moved private cursor pointers into their allocation and did not change decode/navigation policy. It is retained as a negative experiment, not selected for full confirmation.

| Cohort | Case / metric | B median ms [min,max] | L4 median ms [min,max] | L7 median ms [min,max] | L4/B paired % | L7/B paired % | L7/L4 paired % |
|---:|---|---|---|---|---:|---:|---:|
| 0 | inline / backend_cpu_ms | 0.666931 [0.620902,0.793662] | 0.703491 [0.644837,0.788944] | 0.707171 [0.625108,0.782875] | +3.626 | +3.562 | +0.841 |
| 0 | am_inline / am_loop_cpu_ms | 18.259580 [17.956480,22.096603] | 20.100487 [19.789260,32.194588] | 19.915685 [19.677052,32.333407] | +10.197 | +9.555 | -0.723 |
| 0 | absent / backend_cpu_ms | 1.511173 [1.470307,1.589566] | 1.513140 [1.475695,1.607262] | 1.500527 [1.454523,1.616787] | +0.439 | -1.181 | -1.119 |
| 0 | am_absent / am_loop_cpu_ms | 56.383592 [55.710492,57.403924] | 52.750145 [52.205131,53.637521] | 52.754090 [52.240714,53.502568] | -6.102 | -6.163 | -0.158 |
| 0 | seq_control / backend_cpu_ms | 54.464723 [49.579000,78.728098] | 54.942049 [48.607402,76.383018] | 55.344793 [48.251067,83.976605] | +1.806 | -0.803 | -1.291 |
| 0 | skew1000 / backend_cpu_ms | 81.193618 [77.203469,104.159507] | 30.417988 [28.206623,43.436441] | 29.974612 [28.545432,42.349950] | -62.869 | -63.131 | -1.540 |
| 0 | jsonb / backend_cpu_ms | 164.194082 [154.779418,242.055777] | 55.402380 [53.360655,85.991549] | 57.058416 [54.466034,86.269916] | -65.505 | -64.547 | +1.619 |
| 1 | inline / backend_cpu_ms | 0.646535 [0.615214,0.788984] | 0.683982 [0.635844,0.740701] | 0.678038 [0.658639,0.734182] | +5.275 | +4.976 | +1.697 |
| 1 | am_inline / am_loop_cpu_ms | 18.358413 [17.887747,19.755450] | 20.243327 [19.655940,23.006690] | 20.153296 [19.573967,31.621998] | +10.115 | +10.512 | -0.630 |
| 1 | absent / backend_cpu_ms | 1.478519 [1.387983,2.431759] | 1.518694 [1.368904,2.523778] | 1.446191 [1.371108,2.456366] | +2.294 | -1.229 | -3.167 |
| 1 | am_absent / am_loop_cpu_ms | 60.929585 [55.486907,100.655336] | 61.158839 [56.678745,101.748838] | 60.308248 [56.482762,101.575719] | +2.011 | +1.210 | -0.638 |
| 1 | seq_control / backend_cpu_ms | 72.125373 [49.916105,84.401183] | 75.331345 [54.205944,83.178917] | 74.943382 [56.421169,84.589064] | +1.041 | +1.372 | -0.071 |
| 1 | skew1000 / backend_cpu_ms | 81.308706 [78.691393,123.553694] | 29.959885 [28.569718,46.061370] | 29.641402 [28.627746,45.961250] | -63.400 | -63.780 | -0.454 |
| 1 | jsonb / backend_cpu_ms | 155.201286 [148.502989,244.411962] | 56.218464 [52.728717,86.461875] | 55.269790 [52.770309,87.085140] | -64.606 | -64.361 | +0.686 |

## Same-binary calibration

Five independent processes use the exact same baseline ELF. These observations measure process/cohort variability; they do not prove that candidate source cannot affect a control, and are not used to normalize candidate measurements.

| Cohort | Case | T/B CPU % | N2/B CPU % | N3/B CPU % | N4/B CPU % |
|---:|---|---:|---:|---:|---:|
| 0 | inline | -1.759 | -3.165 | -1.481 | -1.820 |
| 0 | seq_control | +2.078 | +1.961 | +0.419 | +3.657 |
| 0 | absent | +0.320 | +1.948 | -0.626 | +1.056 |
| 1 | inline | -1.451 | -1.334 | -2.361 | -1.483 |
| 1 | seq_control | -1.237 | -0.950 | -5.868 | -2.737 |
| 1 | absent | +0.028 | +0.739 | +0.130 | +1.988 |

## Diagnostic software profiles

All 12 software profiles passed, 199 Hz cpu-clock:u and DWARF stacks in separate qualification backends. They are not PMU cycle attribution, throughput samples, or justification for a particular hardware-cache explanation. The absent query spends roughly 61–73% of sampled leaf time in ginPostingListDecodeAllSegments across these four builds. This motivated the separately preflighted exact-count first-page deferral in R3. Seq profiles remain in ordinary heap tuple deformation, not the GIN path. Full exported stacks and symbol reports are under evidence-r2/screen-r2/profile-*; perf.data and full runner logs remain private.

The advance and baseline gingetbitmap instruction shapes match after normalizing code addresses/RIP displacements. This static observation does not establish identical timing or rule out layout effects. No root cause for the older off-path Seq movement is claimed.

All cases, all metrics, all direct pairs, per-round observations, absolute ranges, sample deviations and MAD remain in results-r2 and evidence-r2. There is no trimming, pooling or twin correction.
