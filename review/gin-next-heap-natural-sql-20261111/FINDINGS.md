# Selective OR with natural planner choices: measured findings

The fixed screen completed **384 raw / 288 retained / 96 warm** observations in two fresh cohorts. Both frozen analyzers passed; the separate auditor reconstructed all full plans, literals, ordered digests, all-on settings, schedule and **8208 numerical values**, including 144 absolute groups, 144 pair groups and 864 direct pairs. All warm observations and negative controls remain. `BENCHMARKS-r1.md` and the two analysis directories retain all three metrics and full dispersions.

This is an unchanged-source follow-up: fixed B `8a8c475037bfde101da23cc9b0364c9c020eca93`, exact executable twin T and Heap `03dff8bfa5075e5838c7fbffc712d0b79d03f13d`, over historical B72 with the same opaque prerequisite. Old full builds/core239/actual-header qualification and the stopped seed were held exactly; no recompilation, source/threshold change, composition or outcome-dependent repeat was performed.

All scan paths were enabled under the fixed parallel/JIT/memoize-off protocol, 64MB work_mem and 512MB buffers. Planner costs remained seq_page_cost=1, random_page_cost=4, cpu_tuple/index_tuple/operator costs=.01/.005/.0025 and effective_cache_size=4GB. In every warm and retained observation in both cohorts, N1/2/7/8/32/128 used Bitmap Heap Scan with docs_d_gin; **N512 selected Seq Scan**. The historical `seq_control` name selected **Index Only Scan with docs_pkey**. These actual choices were retained without forcing or selecting a favorable plan.

For natural GIN N32, executor Heap/B paired medians were **−10.53% / −10.30%**; B/Heap absolute medians were **0.847/0.753 ms** and **0.8195/0.727 ms**. For N128, paired medians were **−11.43% / −11.46%**, with **11.4115/10.096 ms** and **11.359/10.0825 ms**. Whole-backend CPU Heap/B was −9.10%/−5.53% at N32 and −11.59%/−11.00% at N128; client wall is separately tabulated. These are bounded observations, not a general application or adoption result.

Negatives and limits matter. N8 executor Heap/B was −5.50% / **+16.31%**, so the threshold case did not produce a stable improvement. N7 executor was **+4.20% / +5.57%**, and whole-backend CPU **+13.68% / +11.40%**. N1 backend CPU was +14.70% / +5.77%; its cohort0 exact-twin executor pair was +56.13% around a 0.046ms baseline median, with a −17.02%..+89.74% direct range. Short-query percentages are noisy and all raw pairs remain.

Even the **N512 Seq path** showed Heap/B executor −3.86% / −3.97%, with B/Heap medians 2300.471/2205.450ms and 2262.3965/2170.944ms. This is not a required-entry heap execution benefit; the cause of the unchanged-path difference is unidentified. The ID Index Only control was +0.21% / +1.42% (backend CPU +0.51% / +1.71%). No control normalization or source-causal attribution is used. Prior forced-GIN/common-superset and native-AM results remain different workloads.

Each table entry below is milliseconds; percentages are the median of six same-round direct ratios `100*(right/left−1)` and may differ from a ratio of absolute medians. Positive means slower. Both cohorts remain separate. Full min/median/max/mean/sample stdev/MAD for all metrics and pairs are in `BENCHMARKS-r1.md`.

## Cohort 0: SQL executor

| Case | B median ms | T median ms | Heap median ms | Heap/B % [min,max] | Heap/T % [min,max] | T/B % [min,max] |
|---|---:|---:|---:|---:|---:|---:|
| sql_sparse_or1 | 0.0460 | 0.0685 | 0.0455 | +4.29 [-15.69,+64.86] | -20.38 [-40.58,+17.95] | +56.13 [-17.02,+89.74] |
| sql_sparse_or2 | 0.0605 | 0.0590 | 0.0610 | -5.66 [-26.19,+47.83] | +0.12 [-26.56,+52.00] | -2.47 [-29.76,+50.00] |
| sql_sparse_or7 | 0.1060 | 0.1070 | 0.1095 | +4.20 [-1.77,+36.75] | +1.26 [-2.70,+28.00] | +4.98 [-15.93,+12.12] |
| sql_sparse_or8 | 0.1190 | 0.1130 | 0.1155 | -5.50 [-18.12,+21.74] | +1.18 [-10.85,+29.63] | -3.93 [-16.67,+9.91] |
| sql_sparse_or32 | 0.8470 | 0.8375 | 0.7530 | -10.53 [-12.00,-9.42] | -10.22 [-16.57,-8.31] | -0.12 [-3.71,+8.57] |
| sql_sparse_or128 | 11.4115 | 11.4640 | 10.0960 | -11.43 [-13.09,-10.25] | -11.71 [-12.92,-10.84] | +0.45 [-1.07,+1.55] |
| sql_sparse_or512 | 2300.4710 | 2287.7605 | 2205.4500 | -3.86 [-4.47,-3.62] | -3.42 [-3.98,-3.29] | -0.37 [-1.14,+0.10] |
| seq_control | 12.7980 | 12.8930 | 12.8225 | +0.21 [-0.03,+0.67] | -0.41 [-0.81,+0.11] | +0.53 [+0.17,+1.42] |

## Cohort 1: SQL executor

| Case | B median ms | T median ms | Heap median ms | Heap/B % [min,max] | Heap/T % [min,max] | T/B % [min,max] |
|---|---:|---:|---:|---:|---:|---:|
| sql_sparse_or1 | 0.0415 | 0.0430 | 0.0405 | -2.24 [-13.64,+27.50] | -3.49 [-33.33,+34.21] | +3.58 [-6.52,+29.55] |
| sql_sparse_or2 | 0.0535 | 0.0475 | 0.0480 | -11.15 [-29.85,+10.64] | +0.00 [-26.47,+4.26] | -3.82 [-28.36,+15.25] |
| sql_sparse_or7 | 0.1080 | 0.1080 | 0.1155 | +5.57 [-6.88,+22.11] | +9.26 [+3.67,+19.59] | +0.01 [-20.63,+2.11] |
| sql_sparse_or8 | 0.1155 | 0.1225 | 0.1280 | +16.31 [-10.74,+33.33] | +0.43 [-30.34,+38.71] | +9.17 [-3.88,+40.16] |
| sql_sparse_or32 | 0.8195 | 0.8175 | 0.7270 | -10.30 [-12.55,-8.03] | -11.07 [-15.04,-5.89] | +0.36 [-2.28,+3.71] |
| sql_sparse_or128 | 11.3590 | 11.4280 | 10.0825 | -11.46 [-12.54,-10.92] | -11.92 [-13.45,-11.27] | +0.47 [-0.87,+2.68] |
| sql_sparse_or512 | 2262.3965 | 2302.1170 | 2170.9440 | -3.97 [-4.94,-3.52] | -5.72 [-5.87,-5.35] | +1.85 [+0.79,+2.42] |
| seq_control | 12.7520 | 12.8230 | 12.9220 | +1.42 [+1.17,+1.87] | +0.81 [+0.52,+1.26] | +0.62 [+0.09,+1.34] |

The recorded VM window began at load 0.13/0.23/0.12 and ended at 1.13/0.73/0.36. Server/client used guest CPUs 0/4 then 4/0 (advertised guest cores 0/2); hardware isolation and identical code placement are not established. Retained backend read/write bytes and minor/major faults were zero in both cohorts. Total retained runqueue was 11.84 ms / 9.97 ms; these diagnostics are not filters. The controller recorded all six accepted clusters stopped with cleanup [] / remaining_owned 0; smoke recorded three stops. The final [ROOT-FINAL-LIVE-r1.json](ROOT-FINAL-LIVE-r1.json) independently verified all nine stopped lifetimes, no owned PIDs/sockets, all three installed prefixes, 7726 source files, both seeds and frozen inputs unchanged.

No new microbenchmark, write benchmark, independent-host replay, profile attribution, concurrency claim or merge-readiness claim follows from this screen. The fresh-build plain SQL replay is independently usable but was only generated/static checked here; the held original controllers and actual receipts remain immutable.
