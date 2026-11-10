# Offset-fragment micro: conditional gains and substantial short-skip negatives

The fixed extracted-fragment run completed 720 raw / 540 retained / 180 warm commands. Independent recount passed all 360 absolute groups, 360 pair groups and 2160 direct pairs. The exact B/T executable and arguments matched. All checksums and source/install/input identities passed.

Large skips favor the candidate in this fragment: n64/skip63 paired kernel CPU changed -56.82% / -51.70%, and n291/skip290 -87.81% / -87.45%. Shorter skips include clear negatives: n8/skip4 +45.01% / +51.84%, n8/skip7 +30.58% / +19.68%, and n291/skip4 +15.57% / +31.16%. These are paired medians, not ratios of independent medians.

Short kernels are noisy. Exact B/T paired kernel CPU drift reached -25.40% to +15.61% across cells. The recorded load averages were 3.18, 1.13, 0.55 before and 3.22, 1.21, 0.59 after the run. This is diagnostic fragment evidence; no clean small-difference, full-AM or SQL benefit is claimed. No source tuning, repeat, trimming, pooling or control correction followed.

Each command makes 250,000 calls through a common volatile indirect function pointer. Real PostgreSQL GinScanEntryData and uint16 offsets are used, but the scan body is extracted. The before/after last-offset guard and candidate helper/caller are frozen exact fragments. Actual normal ASM verified a call inside every iteration, without loop hoisting. Kernel clocks exclude process startup/initialization/validation/JSON; outer clocks retain them.

## Kernel process CPU

| Cell | Cohort | B median ms [min,max] | Candidate median ms [min,max] | Candidate/B % | T/B % |
|---|---:|---:|---:|---:|---:|
| n8_skip0 | 0 | 0.657742 [0.424867,0.694001] | 0.369114 [0.343625,0.528894] | -40.78 | -3.27 |
| n8_skip0 | 1 | 0.672570 [0.441052,0.698738] | 0.427627 [0.343435,0.592399] | -29.68 | -3.46 |
| n8_skip1 | 0 | 0.579475 [0.442284,0.717487] | 0.653135 [0.470386,0.680772] | -3.25 | +15.61 |
| n8_skip1 | 1 | 0.711292 [0.465158,0.721913] | 0.577236 [0.451959,0.677487] | -8.30 | -24.38 |
| n8_skip2 | 0 | 0.806119 [0.478778,0.867252] | 0.775219 [0.547091,1.065599] | +17.84 | -4.44 |
| n8_skip2 | 1 | 0.676365 [0.505899,0.861263] | 0.575379 [0.565058,1.077528] | +10.80 | +5.62 |
| n8_skip4 | 0 | 0.657467 [0.647352,0.915474] | 1.096160 [0.839831,1.454062] | +45.00 | -0.60 |
| n8_skip4 | 1 | 0.895348 [0.697637,1.187893] | 1.340958 [0.944908,1.448494] | +51.84 | +5.76 |
| n8_skip7 | 0 | 1.109445 [0.867693,1.592941] | 1.615369 [1.178810,2.017367] | +30.58 | -0.89 |
| n8_skip7 | 1 | 1.456471 [0.857357,1.559510] | 1.756451 [1.493001,2.009937] | +19.68 | +6.47 |
| n64_skip0 | 0 | 0.590046 [0.410887,0.699059] | 0.588643 [0.343255,0.602514] | -14.57 | +15.41 |
| n64_skip0 | 1 | 0.540776 [0.425949,0.684047] | 0.565584 [0.343225,0.621814] | -2.58 | -0.05 |
| n64_skip1 | 0 | 0.616650 [0.471768,0.720882] | 0.676540 [0.501663,0.685358] | +3.96 | +10.94 |
| n64_skip1 | 1 | 0.695198 [0.436685,0.742023] | 0.652083 [0.411939,0.683636] | -3.82 | +1.85 |
| n64_skip2 | 0 | 0.828819 [0.511027,0.865529] | 0.782940 [0.546490,0.957066] | +3.80 | +2.54 |
| n64_skip2 | 1 | 0.787797 [0.524928,0.867442] | 0.998284 [0.560581,1.084317] | +21.87 | +8.84 |
| n64_skip4 | 0 | 1.104948 [0.692258,1.158690] | 0.983887 [0.857617,1.426181] | +16.33 | -1.28 |
| n64_skip4 | 1 | 1.014127 [0.636425,1.156255] | 1.261508 [1.133201,1.394003] | +30.17 | +10.36 |
| n64_skip63 | 0 | 7.252911 [5.341167,8.604014] | 2.829842 [2.722787,3.238069] | -56.81 | -8.09 |
| n64_skip63 | 1 | 7.972886 [7.058344,8.490894] | 3.752231 [3.361215,3.900344] | -51.70 | -9.91 |
| n291_skip0 | 0 | 0.600907 [0.546781,0.690226] | 0.584882 [0.343556,0.619109] | -0.77 | +6.26 |
| n291_skip0 | 1 | 0.592789 [0.412069,0.697707] | 0.587171 [0.360070,0.622163] | -5.74 | +9.26 |
| n291_skip1 | 0 | 0.700616 [0.475003,0.728854] | 0.631919 [0.551648,0.664428] | -8.41 | -25.40 |
| n291_skip1 | 1 | 0.703305 [0.411438,0.744277] | 0.588834 [0.411507,0.668383] | -15.14 | -4.07 |
| n291_skip2 | 0 | 0.821338 [0.495303,0.878308] | 0.749915 [0.546410,1.071197] | +11.35 | +3.44 |
| n291_skip2 | 1 | 0.782986 [0.479430,0.872880] | 0.774207 [0.546631,1.074913] | +12.96 | -17.40 |
| n291_skip4 | 0 | 1.027492 [0.645158,1.136636] | 1.135524 [0.882054,1.354634] | +15.57 | +4.58 |
| n291_skip4 | 1 | 0.703286 [0.617417,0.974112] | 0.940847 [0.821493,1.184958] | +31.16 | -0.72 |
| n291_skip290 | 0 | 31.669271 [28.116428,32.930884] | 3.763153 [3.120954,4.722307] | -87.81 | +0.87 |
| n291_skip290 | 1 | 32.137714 [29.513705,34.849744] | 4.100529 [3.315115,4.649729] | -87.45 | -0.84 |

## Kernel monotonic wall

| Cell | Cohort | B median ms [min,max] | Candidate median ms [min,max] | Candidate/B % | T/B % |
|---|---:|---:|---:|---:|---:|
| n8_skip0 | 0 | 0.651435 [0.419170,0.687090] | 0.363680 [0.338467,0.523279] | -41.07 | -3.30 |
| n8_skip0 | 1 | 0.665871 [0.435244,0.703294] | 0.421604 [0.338457,0.584332] | -30.60 | -3.46 |
| n8_skip1 | 0 | 0.573585 [0.443498,0.711036] | 0.647294 [0.464790,0.664765] | -3.29 | +15.68 |
| n8_skip1 | 1 | 0.704872 [0.459021,0.714901] | 0.567061 [0.446011,0.670925] | -8.90 | -25.33 |
| n8_skip2 | 0 | 0.799826 [0.473823,0.861065] | 0.769354 [0.541487,1.058887] | +17.98 | -4.47 |
| n8_skip2 | 1 | 0.670299 [0.500434,0.853754] | 0.575514 [0.559364,1.069974] | +11.98 | +5.65 |
| n8_skip4 | 0 | 0.651560 [0.640247,0.909398] | 1.089920 [0.834755,1.447540] | +45.45 | +0.44 |
| n8_skip4 | 1 | 0.889484 [0.691125,1.181755] | 1.333882 [0.938403,1.441101] | +52.05 | +5.77 |
| n8_skip7 | 0 | 1.095392 [0.862217,1.586122] | 1.608652 [1.173312,2.019904] | +31.93 | -0.04 |
| n8_skip7 | 1 | 1.448672 [0.850890,1.552911] | 1.749156 [1.497327,2.001266] | +19.72 | +6.55 |
| n64_skip0 | 0 | 0.590196 [0.406131,0.692707] | 0.582034 [0.338457,0.596200] | -14.76 | +13.84 |
| n64_skip0 | 1 | 0.534652 [0.420592,0.677034] | 0.559138 [0.338466,0.614959] | -2.66 | -0.19 |
| n64_skip1 | 0 | 0.610993 [0.466292,0.713620] | 0.669663 [0.495346,0.677474] | +3.86 | +10.96 |
| n64_skip1 | 1 | 0.688557 [0.430418,0.736044] | 0.644294 [0.406131,0.676403] | -3.93 | +2.52 |
| n64_skip2 | 0 | 0.829371 [0.505372,0.859172] | 0.775289 [0.541487,0.951372] | +2.96 | +1.57 |
| n64_skip2 | 1 | 0.769625 [0.519323,0.861095] | 0.991649 [0.555348,1.088432] | +23.95 | +8.85 |
| n64_skip4 | 0 | 1.097896 [0.686759,1.161053] | 0.982516 [0.860364,1.419628] | +16.43 | -1.74 |
| n64_skip4 | 1 | 1.007229 [0.631184,1.150167] | 1.260876 [1.127231,1.388069] | +30.99 | +10.43 |
| n64_skip63 | 0 | 7.258374 [5.349218,8.607615] | 2.860098 [2.715787,3.230823] | -56.94 | -8.29 |
| n64_skip63 | 1 | 7.977557 [7.050696,8.483225] | 3.743501 [3.355053,3.892574] | -51.74 | -9.89 |
| n291_skip0 | 0 | 0.593417 [0.540806,0.683835] | 0.578143 [0.338467,0.612956] | -0.75 | +6.14 |
| n291_skip0 | 1 | 0.585885 [0.406130,0.690925] | 0.580411 [0.338497,0.615390] | -5.86 | +10.57 |
| n291_skip1 | 0 | 0.695722 [0.468746,0.720090] | 0.625485 [0.545843,0.657934] | -8.53 | -25.27 |
| n291_skip1 | 1 | 0.696729 [0.406131,0.736735] | 0.582510 [0.406130,0.659407] | -15.18 | -4.14 |
| n291_skip2 | 0 | 0.815215 [0.489918,0.870600] | 0.743801 [0.541477,1.064646] | +11.41 | +3.46 |
| n291_skip2 | 1 | 0.769235 [0.473803,0.866213] | 0.779976 [0.541486,1.068702] | +14.48 | -17.53 |
| n291_skip4 | 0 | 1.025491 [0.639667,1.130096] | 1.129584 [0.876608,1.361589] | +16.31 | +4.04 |
| n291_skip4 | 1 | 0.697340 [0.611955,0.968409] | 0.935172 [0.816237,1.177358] | +31.36 | -0.77 |
| n291_skip290 | 0 | 31.675301 [28.108223,32.921544] | 3.769947 [3.112653,4.713127] | -87.79 | +0.88 |
| n291_skip290 | 1 | 32.232932 [29.506809,34.858972] | 4.092986 [3.324506,4.640857] | -87.45 | -0.84 |

## Replay and scope

The auditor retains every outer CPU/wall metric, all absolute min/median/max/mean/sample SD/MAD, all role pairs and all direct values in its JSON and TSV outputs. CPU cohorts remain separate. B/T invoke selector 0 in one executable; candidate invokes selector 1. Common indirect-call overhead remains. Both static functions remain in the same normal executable, 77 and 263 bytes respectively.

The original compile-only r1 failed before compiler invocation because the harness assumed include/server. The separate r2 uses each installed pg_config server-header path, with containment and 907-header equality. Production C, extracted C, cases and loops were unchanged. That failure and its exact correction are preserved. This is a harness precondition erratum, not a production-source failure.

This supplement does not change the separately completed mixed/negative bitmap SQL screen. It neither proves a SQL benefit nor a concurrency/general merge property. All micro child commands returned; no clusters were created. Final namespace shutdown/unchanged-ELF proof is retained separately.
