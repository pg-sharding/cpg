# Held-build Heap short-query100-rescan SQL: complete results

240 raw / 180 retained / 60 warm; two fresh cohorts, five SQL work-unit cells, all three roles and all three pairs. Four short OR predicates each execute100 real rescans; the natural planner may choose GIN, Seq or the ID-index for the control. No plan differences were filtered. These are new ordinary SQL measurements; earlier AM timings remain separate.

B/T use the identical fixed-B executable. Heap source is `03dff8bfa5075e5838c7fbffc712d0b79d03f13d`; B is `8a8c475037bfde101da23cc9b0364c9c020eca93`, both over historical B72 with the same prerequisite. No source change, composition, native helper, extra run or threshold tuning was made.

All times are milliseconds for one complete SQL command (100 rescans for short cases,1 for control; no per-probe normalization). Backend CPU, client wall and EXPLAIN Execution Time have separate boundaries. A separate literal command immediately before each measured EXPLAIN is explicit extra warming. All warm and retained observations passed literal, plan, one-loop and independent ordered Seq/GIN checks.

Pair percentages are same-round 100*(right/left−1). Their median need not equal the ratio of absolute medians. Six retained observations per group; sample stdev and MAD are shown. No pooling, trimming, twin/control normalization, significance or causal attribution. The FRESH_HOST_CLEAN_SCREEN label records the observed host window, not independent hardware or identical code placement. All controls and exact-twin variation remain visible.

## Cohort 0

120 raw / 90 retained / 30 warm. Raw SHA256 `20d462301e150cc093eea66945c4a6b21ce19c657f1d86a4d0352f568e30ca39`.

Retained diagnostics: `{"cpu_ns": 622141031, "major_faults": 0, "minor_faults": 0, "read_bytes": 0, "runqueue_ns": 476975, "slices": 109, "write_bytes": 0}`.

### sql_batch_or1

Expected literal: `4800|481689600`; 48 ordered IDs per scan; 100 rescans per measured command. Natural path observations: `{"B": {"Bitmap Heap Scan/docs_d_gin": 8}, "Heap": {"Bitmap Heap Scan/docs_d_gin": 8}, "T": {"Bitmap Heap Scan/docs_d_gin": 8}}`.

**backend_cpu_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 1.893301 | 1.926887 | 1.956186 | 1.926147 | 0.021852 | 0.010255 |
| T | 6 | 1.892160 | 1.919967 | 1.953391 | 1.919871 | 0.021469 | 0.013976 |
| Heap | 6 | 1.908444 | 1.926762 | 1.982175 | 1.933419 | 0.025204 | 0.003916 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | 0.380888 | -2.301604 | 0.842717 | 1.411239 | 0.400688 | 0.007241 |
| Heap/B | 0.022257 | -1.631644 | 2.346164 | 1.559430 | 1.084431 | 0.000425 |
| Heap/T | 0.269196 | -1.324261 | 4.757262 | 2.239921 | 1.347516 | 0.005168 |

**client_wall_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 2.375988 | 2.395713 | 2.436731 | 2.397546 | 0.021376 | 0.009359 |
| T | 6 | 2.327143 | 2.383809 | 2.418633 | 2.378881 | 0.030165 | 0.010045 |
| Heap | 6 | 2.362778 | 2.371942 | 2.435950 | 2.380962 | 0.027276 | 0.003646 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | -0.778895 | -2.355122 | 1.024516 | 1.325956 | 1.176342 | -0.018678 |
| Heap/B | -0.970720 | -3.034927 | 2.523666 | 1.808855 | 0.411587 | -0.023270 |
| Heap/T | -0.656930 | -1.917240 | 4.675561 | 2.316140 | 0.307267 | -0.015663 |

**sql_execution_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 1.652000 | 1.690000 | 1.728000 | 1.693333 | 0.027097 | 0.018000 |
| T | 6 | 1.653000 | 1.698500 | 1.728000 | 1.695167 | 0.026134 | 0.014500 |
| Heap | 6 | 1.659000 | 1.682000 | 1.707000 | 1.681000 | 0.017697 | 0.012000 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | 0.030266 | -1.571595 | 1.182732 | 0.980698 | 0.503256 | 0.000500 |
| Heap/B | -0.709604 | -3.067130 | 1.486326 | 1.661559 | 1.055869 | -0.012000 |
| Heap/T | -0.528070 | -3.067130 | 1.486326 | 1.763558 | 1.452721 | -0.009000 |

### sql_batch_or2

Expected literal: `9700|963384100`; 97 ordered IDs per scan; 100 rescans per measured command. Natural path observations: `{"B": {"Bitmap Heap Scan/docs_d_gin": 8}, "Heap": {"Bitmap Heap Scan/docs_d_gin": 8}, "T": {"Bitmap Heap Scan/docs_d_gin": 8}}`.

**backend_cpu_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 2.620022 | 2.643728 | 2.684549 | 2.649315 | 0.021908 | 0.010586 |
| T | 6 | 2.616627 | 2.666252 | 2.700574 | 2.659348 | 0.030560 | 0.021422 |
| Heap | 6 | 2.573212 | 2.608019 | 2.631880 | 2.606176 | 0.021459 | 0.015723 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | 0.089391 | -1.160782 | 3.074478 | 1.694185 | 1.148182 | 0.002188 |
| Heap/B | -1.700154 | -3.032241 | 0.452592 | 1.250829 | 0.797800 | -0.045083 |
| Heap/T | -2.256064 | -2.942821 | -0.301070 | 0.929998 | 0.442242 | -0.060201 |

**client_wall_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 3.086693 | 3.124195 | 3.133324 | 3.117487 | 0.017658 | 0.007391 |
| T | 6 | 3.092542 | 3.116715 | 3.167537 | 3.122520 | 0.030226 | 0.023436 |
| Heap | 6 | 3.034553 | 3.073208 | 3.098782 | 3.066359 | 0.025733 | 0.017071 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | 0.038962 | -1.301557 | 1.973083 | 1.249099 | 1.082780 | 0.001212 |
| Heap/B | -1.650963 | -3.086084 | -0.305959 | 1.005219 | 0.756175 | -0.051624 |
| Heap/T | -2.021502 | -2.707498 | 0.154072 | 1.016588 | 0.298052 | -0.063131 |

**sql_execution_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 2.386000 | 2.430500 | 2.449000 | 2.426667 | 0.024089 | 0.017000 |
| T | 6 | 2.391000 | 2.426500 | 2.460000 | 2.424833 | 0.023302 | 0.012500 |
| Heap | 6 | 2.317000 | 2.341000 | 2.374000 | 2.343833 | 0.025996 | 0.024000 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | -0.574610 | -0.993789 | 3.101425 | 1.563268 | 0.182542 | -0.014000 |
| Heap/B | -3.739660 | -4.924087 | -0.502934 | 1.565022 | 0.655442 | -0.091000 |
| Heap/T | -3.493347 | -4.453608 | -2.265239 | 0.833385 | 0.662917 | -0.085500 |

### sql_batch_or7

Expected literal: `34200|3371930100`; 342 ordered IDs per scan; 100 rescans per measured command. Natural path observations: `{"B": {"Bitmap Heap Scan/docs_d_gin": 8}, "Heap": {"Bitmap Heap Scan/docs_d_gin": 8}, "T": {"Bitmap Heap Scan/docs_d_gin": 8}}`.

**backend_cpu_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 7.790542 | 7.867458 | 8.165765 | 7.942525 | 0.161922 | 0.054897 |
| T | 6 | 7.642260 | 7.733636 | 7.928338 | 7.765204 | 0.104474 | 0.060550 |
| Heap | 6 | 7.540918 | 7.582951 | 7.685914 | 7.594511 | 0.053947 | 0.030095 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | -2.071204 | -5.285335 | 0.939327 | 2.089405 | 1.073940 | -0.162364 |
| Heap/B | -3.730819 | -7.429433 | -1.343013 | 2.436173 | 1.672397 | -0.293595 |
| Heap/T | -2.189737 | -4.055465 | 0.571218 | 1.670275 | 1.113399 | -0.169038 |

**client_wall_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 8.301636 | 8.380146 | 8.665972 | 8.449442 | 0.164335 | 0.069081 |
| T | 6 | 8.166549 | 8.253353 | 8.448120 | 8.271221 | 0.109065 | 0.086367 |
| Heap | 6 | 8.048038 | 8.075275 | 8.223707 | 8.108569 | 0.068257 | 0.016490 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | -2.182939 | -4.502842 | 1.533875 | 2.099403 | 0.992188 | -0.182520 |
| Heap/B | -3.583487 | -6.861527 | -0.938719 | 2.351093 | 1.893733 | -0.299742 |
| Heap/T | -1.960900 | -4.481328 | 0.699904 | 1.815970 | 1.126277 | -0.161487 |

**sql_execution_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 7.545000 | 7.589500 | 7.875000 | 7.657500 | 0.141394 | 0.042000 |
| T | 6 | 7.397000 | 7.486000 | 7.699000 | 7.512167 | 0.108300 | 0.065500 |
| Heap | 6 | 7.252000 | 7.275500 | 7.430000 | 7.311000 | 0.069547 | 0.013500 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | -2.001778 | -4.774603 | 1.409378 | 2.058036 | 0.985151 | -0.151500 |
| Heap/B | -4.137287 | -7.911111 | -1.589404 | 2.431233 | 2.123234 | -0.314000 |
| Heap/T | -2.736035 | -5.494220 | 0.446127 | 2.060507 | 1.206238 | -0.204500 |

### sql_batch_or8

Expected literal: `39100|3853654000`; 391 ordered IDs per scan; 100 rescans per measured command. Natural path observations: `{"B": {"Bitmap Heap Scan/docs_d_gin": 8}, "Heap": {"Bitmap Heap Scan/docs_d_gin": 8}, "T": {"Bitmap Heap Scan/docs_d_gin": 8}}`.

**backend_cpu_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 9.092306 | 9.133443 | 9.154319 | 9.128651 | 0.023042 | 0.015789 |
| T | 6 | 9.009813 | 9.041180 | 9.140448 | 9.056731 | 0.046782 | 0.020982 |
| Heap | 6 | 8.640408 | 8.671354 | 8.731384 | 8.677936 | 0.036289 | 0.029564 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | -0.879117 | -1.440540 | 0.296706 | 0.599043 | 0.231656 | -0.080296 |
| Heap/B | -4.904441 | -5.583670 | -4.191890 | 0.560490 | 0.464445 | -0.447291 |
| Heap/T | -4.285499 | -4.492825 | -3.572118 | 0.370545 | 0.198572 | -0.387621 |

**client_wall_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 9.611996 | 9.669985 | 9.696706 | 9.658080 | 0.034230 | 0.018279 |
| T | 6 | 9.521508 | 9.538956 | 9.704978 | 9.570201 | 0.070059 | 0.013692 |
| Heap | 6 | 9.126435 | 9.192116 | 9.270135 | 9.200602 | 0.050096 | 0.029826 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | -1.235405 | -1.635495 | 0.883473 | 0.915063 | 0.249597 | -0.119642 |
| Heap/B | -4.742948 | -5.662229 | -3.636730 | 0.691896 | 0.335644 | -0.458760 |
| Heap/T | -3.858912 | -4.480618 | -2.943620 | 0.570391 | 0.365744 | -0.368913 |

**sql_execution_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 8.832000 | 8.858000 | 8.872000 | 8.854833 | 0.016666 | 0.013500 |
| T | 6 | 8.724000 | 8.764500 | 8.899000 | 8.793667 | 0.068108 | 0.025500 |
| Heap | 6 | 8.335000 | 8.383000 | 8.404000 | 8.378333 | 0.026786 | 0.018500 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | -1.021798 | -1.534989 | 0.758605 | 0.841951 | 0.321578 | -0.090500 |
| Heap/B | -5.305756 | -6.042160 | -4.846014 | 0.417415 | 0.254610 | -0.469500 |
| Heap/T | -4.529614 | -5.883017 | -3.771206 | 0.837808 | 0.627790 | -0.397000 |

### seq_control

Expected literal: `200000|20000100000`; 200000 ordered IDs per scan; 1 rescans per measured command. Natural path observations: `{"B": {"Index Only Scan/docs_pkey": 8}, "Heap": {"Index Only Scan/docs_pkey": 8}, "T": {"Index Only Scan/docs_pkey": 8}}`.

**backend_cpu_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 13.178409 | 13.279301 | 13.376506 | 13.276110 | 0.068735 | 0.042549 |
| T | 6 | 13.143876 | 13.297472 | 13.362306 | 13.282345 | 0.078552 | 0.046766 |
| Heap | 6 | 13.183256 | 13.275033 | 13.331729 | 13.271883 | 0.053406 | 0.035690 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | -0.107310 | -0.262042 | 0.530001 | 0.360773 | 0.148067 | -0.014257 |
| Heap/B | -0.141871 | -0.431316 | 0.776361 | 0.425274 | 0.159391 | -0.018839 |
| Heap/T | -0.100107 | -0.664668 | 0.299607 | 0.362152 | 0.246299 | -0.013350 |

**client_wall_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 13.470748 | 13.603672 | 13.679127 | 13.580977 | 0.075443 | 0.043085 |
| T | 6 | 13.450057 | 13.610747 | 13.749805 | 13.620305 | 0.114508 | 0.090343 |
| Heap | 6 | 13.514185 | 13.621229 | 13.680849 | 13.610851 | 0.064068 | 0.049315 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | 0.359656 | -0.400253 | 1.052163 | 0.521712 | 0.335142 | 0.048704 |
| Heap/B | 0.159017 | -0.333142 | 1.101555 | 0.535267 | 0.366833 | 0.021418 |
| Heap/T | -0.031855 | -1.045582 | 0.891998 | 0.812855 | 0.672990 | -0.004793 |

**sql_execution_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 12.962000 | 13.019000 | 13.075000 | 13.022167 | 0.041954 | 0.033000 |
| T | 6 | 12.918000 | 13.026000 | 13.163000 | 13.040000 | 0.085744 | 0.054500 |
| Heap | 6 | 12.940000 | 13.012500 | 13.049000 | 13.008500 | 0.038495 | 0.019500 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | -0.007455 | -0.339454 | 1.160467 | 0.556691 | 0.244860 | -0.001000 |
| Heap/B | -0.161633 | -0.482315 | 0.323176 | 0.270655 | 0.126325 | -0.021000 |
| Heap/T | -0.095859 | -1.093976 | 0.170305 | 0.482796 | 0.246291 | -0.012500 |

## Cohort 1

120 raw / 90 retained / 30 warm. Raw SHA256 `6205fea5d2c4c1b28667371dd765718f639c2c4333f65cf4a716f11748338f79`.

Retained diagnostics: `{"cpu_ns": 622355811, "major_faults": 0, "minor_faults": 0, "read_bytes": 0, "runqueue_ns": 378166, "slices": 103, "write_bytes": 0}`.

### sql_batch_or1

Expected literal: `4800|481689600`; 48 ordered IDs per scan; 100 rescans per measured command. Natural path observations: `{"B": {"Bitmap Heap Scan/docs_d_gin": 8}, "Heap": {"Bitmap Heap Scan/docs_d_gin": 8}, "T": {"Bitmap Heap Scan/docs_d_gin": 8}}`.

**backend_cpu_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 1.888064 | 1.961599 | 2.034103 | 1.966698 | 0.056156 | 0.045904 |
| T | 6 | 1.930748 | 1.955364 | 2.223997 | 1.999414 | 0.112715 | 0.021392 |
| Heap | 6 | 1.927763 | 1.962370 | 2.009075 | 1.966705 | 0.031675 | 0.028147 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | 0.857987 | -2.015572 | 9.335515 | 4.171050 | 1.859489 | 0.016545 |
| Heap/B | 0.118206 | -4.722641 | 4.069512 | 3.270100 | 2.304813 | 0.001652 |
| Heap/T | -0.257582 | -9.663772 | 3.137110 | 4.592922 | 2.540748 | -0.005103 |

**client_wall_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 2.358512 | 2.437051 | 2.524155 | 2.447993 | 0.060529 | 0.042636 |
| T | 6 | 2.382578 | 2.476521 | 2.802409 | 2.513307 | 0.148603 | 0.034738 |
| Heap | 6 | 2.402979 | 2.475029 | 2.510984 | 2.462377 | 0.039141 | 0.020782 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | 1.147370 | -0.153530 | 11.023649 | 4.245015 | 1.275645 | 0.027471 |
| Heap/B | 1.793433 | -4.196226 | 3.154977 | 2.954864 | 1.291107 | 0.043592 |
| Heap/T | 0.574614 | -11.481943 | 1.973577 | 5.241878 | 1.303265 | 0.014207 |

**sql_execution_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 1.665000 | 1.693000 | 1.730000 | 1.695167 | 0.026034 | 0.022000 |
| T | 6 | 1.681000 | 1.705000 | 1.794000 | 1.714500 | 0.040293 | 0.008000 |
| Heap | 6 | 1.637000 | 1.675000 | 1.698000 | 1.672000 | 0.022441 | 0.016500 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | 0.451152 | -2.138728 | 7.232516 | 3.427296 | 1.935044 | 0.007500 |
| Heap/B | -0.469627 | -5.375723 | 1.494322 | 2.588597 | 1.366938 | -0.008000 |
| Heap/T | -2.576457 | -5.351171 | 0.535396 | 1.980740 | 0.949644 | -0.044000 |

### sql_batch_or2

Expected literal: `9700|963384100`; 97 ordered IDs per scan; 100 rescans per measured command. Natural path observations: `{"B": {"Bitmap Heap Scan/docs_d_gin": 8}, "Heap": {"Bitmap Heap Scan/docs_d_gin": 8}, "T": {"Bitmap Heap Scan/docs_d_gin": 8}}`.

**backend_cpu_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 2.603267 | 2.641094 | 2.685831 | 2.644509 | 0.029286 | 0.018588 |
| T | 6 | 2.629156 | 2.659882 | 2.753553 | 2.673331 | 0.044283 | 0.021943 |
| Heap | 6 | 2.560523 | 2.616642 | 2.639080 | 2.607241 | 0.031296 | 0.018933 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | 0.780365 | -1.139908 | 4.592802 | 2.118273 | 1.539702 | 0.020446 |
| Heap/B | -1.362501 | -3.299566 | 0.758278 | 1.542096 | 1.172184 | -0.036390 |
| Heap/T | -1.766914 | -7.010216 | -0.233877 | 2.479517 | 1.060208 | -0.046851 |

**client_wall_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 3.077048 | 3.105131 | 3.146254 | 3.107142 | 0.022371 | 0.004442 |
| T | 6 | 3.114696 | 3.154732 | 3.211243 | 3.152153 | 0.034857 | 0.020047 |
| Heap | 6 | 3.046983 | 3.089873 | 3.173576 | 3.097647 | 0.051451 | 0.042550 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | 1.469501 | 0.180407 | 3.581701 | 1.249545 | 0.783693 | 0.045454 |
| Heap/B | -0.010085 | -1.997500 | 0.995435 | 1.272183 | 0.942001 | -0.000290 |
| Heap/T | -1.557138 | -5.093978 | 0.645084 | 1.925613 | 0.796804 | -0.048884 |

**sql_execution_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 2.379000 | 2.412500 | 2.437000 | 2.411500 | 0.024672 | 0.023000 |
| T | 6 | 2.410000 | 2.440000 | 2.469000 | 2.438667 | 0.020868 | 0.014500 |
| Heap | 6 | 2.318000 | 2.350500 | 2.391000 | 2.348333 | 0.027464 | 0.021000 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | 0.733602 | -0.082508 | 2.832153 | 1.290825 | 0.733822 | 0.017500 |
| Heap/B | -2.672230 | -4.331683 | -1.176965 | 1.342775 | 1.157629 | -0.064500 |
| Heap/T | -3.699975 | -6.115836 | -1.968020 | 1.463570 | 0.902275 | -0.090500 |

### sql_batch_or7

Expected literal: `34200|3371930100`; 342 ordered IDs per scan; 100 rescans per measured command. Natural path observations: `{"B": {"Bitmap Heap Scan/docs_d_gin": 8}, "Heap": {"Bitmap Heap Scan/docs_d_gin": 8}, "T": {"Bitmap Heap Scan/docs_d_gin": 8}}`.

**backend_cpu_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 7.718975 | 7.756697 | 7.778855 | 7.755420 | 0.022177 | 0.015904 |
| T | 6 | 7.782721 | 7.827037 | 7.876101 | 7.824715 | 0.032001 | 0.017271 |
| Heap | 6 | 7.579937 | 7.611198 | 7.701648 | 7.625611 | 0.045306 | 0.023494 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | 1.040498 | 0.079328 | 1.500254 | 0.595402 | 0.424523 | 0.080625 |
| Heap/B | -1.875715 | -2.328564 | -0.838933 | 0.623629 | 0.352560 | -0.145499 |
| Heap/T | -2.495579 | -3.506240 | -1.266328 | 0.797381 | 0.509154 | -0.194767 |

**client_wall_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 8.191728 | 8.284264 | 8.315797 | 8.271633 | 0.045730 | 0.025178 |
| T | 6 | 8.265051 | 8.346360 | 8.430312 | 8.343909 | 0.055521 | 0.028628 |
| Heap | 6 | 8.042159 | 8.111385 | 8.164487 | 8.110821 | 0.050632 | 0.040632 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | 0.840492 | -0.610236 | 2.177451 | 0.928939 | 0.426052 | 0.069637 |
| Heap/B | -1.993561 | -3.142542 | -0.407008 | 0.890319 | 0.235478 | -0.164927 |
| Heap/T | -2.815280 | -4.189513 | -1.216738 | 1.168953 | 1.030602 | -0.234974 |

**sql_execution_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 7.481000 | 7.499500 | 7.548000 | 7.504000 | 0.025985 | 0.017000 |
| T | 6 | 7.524000 | 7.556500 | 7.621000 | 7.562000 | 0.033847 | 0.016000 |
| Heap | 6 | 7.310000 | 7.343500 | 7.421000 | 7.350333 | 0.039026 | 0.015000 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | 0.955340 | -0.092740 | 1.410512 | 0.606725 | 0.364807 | 0.071500 |
| Heap/B | -2.200780 | -2.927928 | -0.907998 | 0.692823 | 0.362978 | -0.165000 |
| Heap/T | -2.800089 | -3.477234 | -1.669538 | 0.670420 | 0.453870 | -0.211500 |

### sql_batch_or8

Expected literal: `39100|3853654000`; 391 ordered IDs per scan; 100 rescans per measured command. Natural path observations: `{"B": {"Bitmap Heap Scan/docs_d_gin": 8}, "Heap": {"Bitmap Heap Scan/docs_d_gin": 8}, "T": {"Bitmap Heap Scan/docs_d_gin": 8}}`.

**backend_cpu_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 9.059086 | 9.082451 | 9.122352 | 9.087380 | 0.025101 | 0.019899 |
| T | 6 | 9.144304 | 9.174153 | 9.227879 | 9.175192 | 0.029404 | 0.014036 |
| Heap | 6 | 8.689161 | 8.722241 | 8.753087 | 8.721419 | 0.024535 | 0.021777 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | 1.044408 | 0.432071 | 1.258085 | 0.293213 | 0.146637 | 0.094857 |
| Heap/B | -4.038850 | -4.530426 | -3.687138 | 0.312358 | 0.224275 | -0.367696 |
| Heap/T | -4.959243 | -5.145191 | -4.714629 | 0.143017 | 0.063451 | -0.453661 |

**client_wall_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 9.576212 | 9.610644 | 9.710877 | 9.622329 | 0.046013 | 0.008974 |
| T | 6 | 9.707732 | 9.736382 | 9.768035 | 9.735291 | 0.022901 | 0.018679 |
| Heap | 6 | 9.211405 | 9.268908 | 9.327432 | 9.271141 | 0.047832 | 0.041418 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | 1.192836 | 0.588598 | 1.817796 | 0.400675 | 0.131385 | 0.114670 |
| Heap/B | -3.751022 | -4.165123 | -3.049333 | 0.441257 | 0.305846 | -0.360100 |
| Heap/T | -4.810760 | -5.298397 | -4.257037 | 0.458082 | 0.394788 | -0.468465 |

**sql_execution_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 8.748000 | 8.830500 | 8.874000 | 8.815000 | 0.053389 | 0.034500 |
| T | 6 | 8.871000 | 8.892000 | 8.908000 | 8.891333 | 0.015055 | 0.014500 |
| Heap | 6 | 8.387000 | 8.411000 | 8.475000 | 8.417000 | 0.030424 | 0.009000 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | 0.634143 | 0.383142 | 1.611797 | 0.498532 | 0.154632 | 0.056000 |
| Heap/B | -4.513155 | -5.206220 | -3.772291 | 0.529726 | 0.376656 | -0.399000 |
| Heap/T | -5.377332 | -5.568029 | -4.850118 | 0.269173 | 0.146733 | -0.477500 |

### seq_control

Expected literal: `200000|20000100000`; 200000 ordered IDs per scan; 1 rescans per measured command. Natural path observations: `{"B": {"Index Only Scan/docs_pkey": 8}, "Heap": {"Index Only Scan/docs_pkey": 8}, "T": {"Index Only Scan/docs_pkey": 8}}`.

**backend_cpu_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 13.037637 | 13.069715 | 13.402926 | 13.127719 | 0.138793 | 0.024596 |
| T | 6 | 13.338018 | 13.442635 | 13.502234 | 13.428651 | 0.064450 | 0.046190 |
| Heap | 6 | 13.050566 | 13.111168 | 13.209906 | 13.121963 | 0.064263 | 0.053695 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | 2.578721 | 0.110886 | 3.444785 | 1.275834 | 0.745287 | 0.337002 |
| Heap/B | 0.135537 | -1.629025 | 1.205170 | 0.974176 | 0.495553 | 0.017727 |
| Heap/T | -2.228986 | -3.152771 | -1.602187 | 0.590425 | 0.502697 | -0.299458 |

**client_wall_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 13.361121 | 13.388308 | 13.861585 | 13.482593 | 0.195767 | 0.023696 |
| T | 6 | 13.695352 | 13.779375 | 13.890790 | 13.784443 | 0.084212 | 0.070447 |
| Heap | 6 | 13.391377 | 13.447834 | 13.587647 | 13.471752 | 0.078411 | 0.045620 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | 2.932156 | -0.995052 | 3.843602 | 1.878707 | 0.797033 | 0.392219 |
| Heap/B | 0.400343 | -1.976239 | 1.241896 | 1.188641 | 0.491207 | 0.053502 |
| Heap/T | -2.362478 | -3.164158 | -0.991048 | 0.809830 | 0.620930 | -0.325998 |

**sql_execution_ms (ms)**

| Role | n | min | median | max | mean | sample stdev | MAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 12.812000 | 12.840500 | 13.133000 | 12.897500 | 0.122283 | 0.019000 |
| T | 6 | 13.118000 | 13.181500 | 13.232000 | 13.175000 | 0.048033 | 0.042000 |
| Heap | 6 | 12.809000 | 12.885500 | 12.918000 | 12.876667 | 0.045399 | 0.031000 |

| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |
|---|---:|---:|---:|---:|---:|---:|
| T/B | 2.543150 | 0.243661 | 3.117207 | 1.135653 | 0.521854 | 0.326500 |
| Heap/B | 0.050861 | -1.637097 | 0.631234 | 0.847920 | 0.521586 | 0.006500 |
| Heap/T | -2.211355 | -3.072266 | -1.547492 | 0.558320 | 0.391654 | -0.291500 |

