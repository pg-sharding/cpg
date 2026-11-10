# Short-query SQL batch: complete-command findings

The separate fixed work-unit screen completed **240 raw / 180 retained / 60 warm** commands, two fresh cohorts, B/exact twin/Heap, all six role orders and all three pairs. Both frozen analyzers passed; the independent auditor reconstructed **5130 numerical values**, 90 absolute groups, 90 pair groups and 540 direct pairs. All warm/negative/control data remain.

Every one of the **192 batch observations** executed the docs scan and docs_d_gin index **100 loops**, with the original per-loop rows (48/97/342/391 at widths 1/2/7/8). All **48 control observations** executed one docs_pkey Index Only scan. The untimed actual EXPLAIN gate also passed for every role/case before samples. Ordered Seq/GIN row oracles remain one scan; literal output totals are independently multiplied by 100. No materialized/decorrelated scan1 shortcut was accepted.

**All times are milliseconds for the complete SQL command**: 100 rescans for short cases, one scan for the unchanged ID control. No division by 100 is used. The batch includes correlated rescan state and one planning/executor command; it does not represent 100 independent client requests, replace the earlier single-scan measurements or identify their regression/noise cause.

For N8, executor Heap/B paired medians were **−5.31% / −4.51%**. B/Heap absolute medians were **8.858/8.383 ms** and **8.8305/8.411 ms**. Whole-backend CPU was −4.90% / −4.04%; client wall −4.74% / −3.75%. N7 executor was −4.14% / −2.20%, N2 −3.74% / −2.67%, N1 −0.71% / −0.47%. These are bounded observations for this new work unit, not proof that the old short-case negatives are fixed.

Negatives and variation remain: N1 backend CPU was **+0.02% / +0.12%**, and client wall **−0.97% / +1.79%**. Its cohort1 Heap/B CPU direct range was −4.72%..+4.07%. The one-probe Index Only control executor was −0.16% / +0.05%, while its exact-twin T/B moved −0.01% / **+2.54%** (CPU −0.11% / +2.58%). N7 twin executor moved −2.00% / +0.96%. All control values/ranges are retained without normalization or a source-causal/general adoption claim.

Fixed B remains 8a8c475037bfde101da23cc9b0364c9c020eca93; Heap 03dff8bfa5075e5838c7fbffc712d0b79d03f13d. Same prerequisite, old builds/ELFs/qualified seed, natural scans enabled, memoize/parallel/JIT off, 64MB work_mem and 512MB buffers. No source/build/threshold/cost/statistics change, composition or outcome-dependent repeat occurred. Backend CPU, client wall and SQL executor have separate boundaries; a literal command before each measured EXPLAIN is explicit extra warming.

Each row below gives absolute executor medians and median same-round direct ratios, with min/max over all six pairs. Positive is slower. A paired median need not equal a ratio of absolute medians. BENCHMARKS-r1.md retains all three metrics, min/median/max/mean/sample stdev/MAD and every direct value in the analysis JSON.

## Cohort 0: SQL executor for complete commands

| Case | rescans | B median ms | T median ms | Heap median ms | Heap/B % [min,max] | Heap/T % [min,max] | T/B % [min,max] |
|---|---:|---:|---:|---:|---:|---:|---:|
| sql_batch_or1 | 100 | 1.6900 | 1.6985 | 1.6820 | -0.71 [-3.07,+1.49] | -0.53 [-3.07,+1.49] | +0.03 [-1.57,+1.18] |
| sql_batch_or2 | 100 | 2.4305 | 2.4265 | 2.3410 | -3.74 [-4.92,-0.50] | -3.49 [-4.45,-2.27] | -0.57 [-0.99,+3.10] |
| sql_batch_or7 | 100 | 7.5895 | 7.4860 | 7.2755 | -4.14 [-7.91,-1.59] | -2.74 [-5.49,+0.45] | -2.00 [-4.77,+1.41] |
| sql_batch_or8 | 100 | 8.8580 | 8.7645 | 8.3830 | -5.31 [-6.04,-4.85] | -4.53 [-5.88,-3.77] | -1.02 [-1.53,+0.76] |
| seq_control | 1 | 13.0190 | 13.0260 | 13.0125 | -0.16 [-0.48,+0.32] | -0.10 [-1.09,+0.17] | -0.01 [-0.34,+1.16] |

## Cohort 1: SQL executor for complete commands

| Case | rescans | B median ms | T median ms | Heap median ms | Heap/B % [min,max] | Heap/T % [min,max] | T/B % [min,max] |
|---|---:|---:|---:|---:|---:|---:|---:|
| sql_batch_or1 | 100 | 1.6930 | 1.7050 | 1.6750 | -0.47 [-5.38,+1.49] | -2.58 [-5.35,+0.54] | +0.45 [-2.14,+7.23] |
| sql_batch_or2 | 100 | 2.4125 | 2.4400 | 2.3505 | -2.67 [-4.33,-1.18] | -3.70 [-6.12,-1.97] | +0.73 [-0.08,+2.83] |
| sql_batch_or7 | 100 | 7.4995 | 7.5565 | 7.3435 | -2.20 [-2.93,-0.91] | -2.80 [-3.48,-1.67] | +0.96 [-0.09,+1.41] |
| sql_batch_or8 | 100 | 8.8305 | 8.8920 | 8.4110 | -4.51 [-5.21,-3.77] | -5.38 [-5.57,-4.85] | +0.63 [+0.38,+1.61] |
| seq_control | 1 | 12.8405 | 13.1815 | 12.8855 | +0.05 [-1.64,+0.63] | -2.21 [-3.07,-1.55] | +2.54 [+0.24,+3.12] |

Retained backend read/write bytes and minor/major faults were zero in both cohorts. Total retained runqueue was 0.477 ms / 0.378 ms; these diagnostics are not filters. ROOT-FINAL-LIVE-r1.json independently verified all nine owned smoke/accepted lifetimes stopped, no owned PIDs/sockets, all three installed prefixes, 7726 source files, both seeds and frozen inputs unchanged. Guest CPUs 0/4 then 4/0 were used; no hardware isolation or second host is claimed.

The original natural single-scan negative evidence is preserved separately and linked with exact hashes in PRIOR-NATURAL-EVIDENCE.json; it is not recursively copied or reclassified by this packet. In particular its N8 instability, short-query negative/twin noise and N512 Seq movement remain valid observations. No new native microbenchmark, concurrency, second-host replay or merge-readiness claim is made.
