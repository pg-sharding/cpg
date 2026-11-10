# GIN logical TID construction: completed screen

R1 is complete and is not promoted to full SQL or CREATE INDEX. The shared four-byte load on fixed B72 (P10) produces substantial selective-query gains, together with a repeated absent-query cost. The same change on C9 (C10) adds smaller gains, with unresolved control movements. This is an experimental result, not a merge-ready recommendation. A separately declared preserved-layout follow-up is running; none of its outcomes are included here.

## Exact comparison

Raw PostgreSQL B72: `72b9498df9a369e747f8d96efb5a6cd33c2451e2` (20devel), with the same supplied prerequisite in every tree. Fixed B: `8a8c475037bfde101da23cc9b0364c9c020eca93`. This is not a measurement of current master. P10: `ca701de010d76b469d9fbfa09f4cad2fdb996e64`; C9: `0ab3bd65c8957ea5e25f9ef8981401f0616d99de`; C10: `cf6df20681101bc58dcb5cf47d3fafd738aaa458`. B/T and C9/U are exact executable twins.

P10/C10 read the two BlockId halfwords together with a bounded four-byte memcpy, reorder the halfwords on little-endian hosts and construct a transient unsigned key. Six-byte storage and two-byte alignment are unchanged. The prototype also changes the transient key shift from32 to16; the next experiment isolates that difference. It must not be presented as a proven cause of the regression.

## All main direct CPU comparisons

Columns are cohort0 / cohort1, medians of12 same-round percentages. Negative means less time. SQL rows use whole-command backend CPU; AM rows use the internal actual-AM loop CPU. These are different boundaries. There is no trimming, pooling, twin normalization or subtraction of historical percentages.

| Case | P10/B % | C10/C9 % | T/B % | U/C9 % |
|---|---:|---:|---:|---:|
| skew1000 | -15.21 / -20.07 | -1.97 / -3.91 | +0.25 / +0.79 | -4.74 / -0.76 |
| skew127 | -11.82 / -5.55 | -0.90 / -7.21 | +0.98 / +0.51 | -1.97 / +0.55 |
| dense_and | -7.78 / +6.35 | -2.46 / +0.21 | -3.22 / +16.14 | -0.21 / +3.92 |
| or_forced | -4.16 / -4.24 | -4.42 / -2.92 | -2.64 / -0.61 | -4.01 / +0.96 |
| single_forced | -1.15 / -7.43 | -3.32 / -0.50 | +0.15 / -0.71 | -2.61 / -1.08 |
| single_rare | +4.34 / -0.42 | -2.72 / -1.03 | -7.20 / +0.96 | -2.22 / +0.34 |
| inline | -0.12 / -1.21 | +5.11 / -0.13 | -0.20 / -2.20 | +0.83 / +7.18 |
| jsonb | -14.92 / -18.66 | -2.86 / -2.62 | +0.22 / +4.48 | -0.59 / -1.63 |
| lossy_and | +0.09 / -1.95 | -4.73 / -5.76 | +1.73 / -0.76 | -1.13 / +0.96 |
| seq_control | +8.27 / -0.16 | +1.55 / +3.13 | +0.91 / -1.06 | -0.46 / +1.10 |
| skew_group4096 | -17.28 / -22.43 | -3.50 / -3.66 | +1.13 / +0.55 | -3.50 / -2.30 |
| inline_single | -1.19 / -3.64 | -0.01 / -0.37 | +0.93 / +3.82 | -1.83 / -1.09 |
| absent | +5.98 / +4.39 | +6.59 / -1.76 | -1.90 / +0.05 | +3.78 / -5.12 |
| am_inline | -9.66 / -3.16 | -1.55 / -0.60 | -0.86 / -0.59 | +0.19 / -0.46 |
| am_absent | +5.05 / +3.94 | -2.10 / +0.47 | -0.43 / -0.01 | -2.07 / +1.86 |
| am_skew1000 | -22.76 / -14.17 | -3.84 / -4.37 | -0.08 / -0.00 | +0.73 / -0.25 |
| am_full | -7.75 / -2.88 | -2.09 / -0.32 | -0.82 / -3.05 | +2.02 / -0.57 |
| am_or | -9.95 / -5.12 | +3.17 / -2.09 | +2.28 / -1.59 | +3.90 / -2.64 |
| am_dense | -5.13 / -12.54 | -10.00 / -4.39 | +5.56 / -4.54 | +4.97 / -0.23 |
| am_rare | -2.78 / -6.89 | -1.28 / -2.31 | +1.35 / +2.77 | -0.45 / -5.78 |

## Absolute backend CPU and spread for selected SQL cases

Each cell is min / median / max ms across12 retained observations; separate rows retain separate cohorts. All SQL executor and client-wall values, SD/MAD, per-round pairs and every negative are in `results/*/tables/ALL-RESULTS.md`, CSV and JSON.

| Case | Cohort | B ms | P10 ms | C9 ms | C10 ms |
|---|---:|---:|---:|---:|---:|
| skew1000 | 0 | 76.822439 / 108.550017 / 122.169206 | 61.114353 / 91.394026 / 104.794328 | 20.629091 / 30.998649 / 34.170213 | 20.197833 / 30.356896 / 32.908049 |
| skew1000 | 1 | 77.337741 / 79.819876 / 122.190778 | 61.145910 / 64.751597 / 106.553639 | 19.704463 / 20.461093 / 33.800399 | 19.280437 / 20.370974 / 33.361290 |
| skew127 | 0 | 140.666567 / 145.556089 / 187.171104 | 122.708967 / 128.518198 / 146.571368 | 105.862443 / 110.249096 / 170.373153 | 104.896251 / 110.134543 / 130.692487 |
| skew127 | 1 | 142.212158 / 146.664066 / 215.508471 | 124.900964 / 140.103852 / 204.544418 | 107.144506 / 118.622859 / 165.638736 | 104.540278 / 108.726380 / 139.976502 |
| jsonb | 0 | 153.370023 / 157.551779 / 240.141563 | 122.685951 / 132.462614 / 208.938561 | 36.292599 / 38.175474 / 62.034723 | 34.492578 / 36.038327 / 60.269174 |
| jsonb | 1 | 166.443113 / 209.001111 / 237.431906 | 125.987456 / 176.309246 / 205.003487 | 38.763939 / 59.383630 / 62.303758 | 35.600240 / 57.708557 / 60.648133 |
| skew_group4096 | 0 | 58.093810 / 59.633560 / 80.766577 | 46.151496 / 49.501569 / 72.608373 | 6.735719 / 7.049751 / 11.450915 | 6.621438 / 6.822815 / 10.803484 |
| skew_group4096 | 1 | 61.189315 / 70.989394 / 90.577753 | 47.874422 / 57.236668 / 77.362458 | 6.924693 / 8.722075 / 11.460049 | 7.278574 / 9.415146 / 11.093509 |
| or_forced | 0 | 152.301609 / 191.682028 / 230.863438 | 145.448795 / 170.720903 / 232.286984 | 165.781200 / 224.143612 / 251.686660 | 157.709175 / 215.366601 / 233.943069 |
| or_forced | 1 | 170.869707 / 232.544455 / 242.063027 | 167.398736 / 227.998523 / 235.948880 | 177.626317 / 225.938526 / 237.047098 | 169.087182 / 215.795568 / 234.680546 |
| inline | 0 | 0.630145 / 0.975664 / 1.049425 | 0.684558 / 0.963927 / 1.071818 | 0.626520 / 0.926605 / 1.009525 | 0.665489 / 0.938228 / 1.018088 |
| inline | 1 | 0.662745 / 0.758554 / 1.025209 | 0.648373 / 0.754292 / 1.025669 | 0.586150 / 0.684106 / 0.917618 | 0.608553 / 0.678980 / 0.966481 |
| single_rare | 0 | 9.888481 / 10.398956 / 11.158336 | 9.493518 / 10.544656 / 11.006318 | 9.953309 / 10.583489 / 10.998918 | 7.723862 / 10.370990 / 10.776213 |
| single_rare | 1 | 6.761428 / 10.209057 / 10.735372 | 6.462789 / 9.009942 / 10.469633 | 6.448578 / 8.813668 / 10.686569 | 6.290751 / 8.872281 / 10.451075 |
| absent | 0 | 1.506280 / 1.594819 / 1.767653 | 1.580292 / 1.696371 / 1.871779 | 0.525849 / 0.542635 / 0.595524 | 0.561183 / 0.590926 / 0.637116 |
| absent | 1 | 1.403376 / 2.378144 / 2.470818 | 1.466712 / 2.441244 / 2.571479 | 0.534833 / 0.634247 / 0.876345 | 0.519209 / 0.632860 / 0.813622 |
| dense_and | 0 | 83.481763 / 90.318679 / 133.271568 | 77.058893 / 86.176466 / 125.801236 | 81.315421 / 85.896072 / 129.147018 | 77.151363 / 84.854944 / 137.870170 |
| dense_and | 1 | 89.119964 / 108.611618 / 170.930778 | 88.941927 / 127.206917 / 161.551062 | 94.844116 / 124.507174 / 163.692244 | 86.869247 / 109.257847 / 150.107847 |
| seq_control | 0 | 49.353011 / 66.692950 / 86.655255 | 55.126316 / 65.826214 / 87.349537 | 44.745886 / 63.929813 / 84.102343 | 47.200320 / 64.171920 / 84.902845 |
| seq_control | 1 | 69.089202 / 77.447906 / 84.700541 | 72.922445 / 78.661101 / 84.247902 | 69.799897 / 77.767100 / 81.991216 | 72.415142 / 79.172264 / 85.612601 |

## Decision and limits

P10 SQL absent CPU is +5.98 / +4.39%; actual-AM absent CPU is +5.05 / +3.94%. AM absolute B medians are 58.977435 / 98.797223 ms and P10 62.264639 / 102.609515 ms per5,000-scan loop. The corresponding per-scan medians are those values divided by5,000, not SQL latency. This cost repeats while exact B/T absent medians stay near zero. It is retained as a regression observation; a causal mechanism is unestablished.

C10/C9 adds native selective gains -3.84 / -4.37% and dense gains -10.00 / -4.39%. SQL Seq CPU is +1.55 / +3.13%. The source objects outside GIN are unchanged, which limits source-code scope but does not prove an explanation for off-path timing. Exact twins also have nonzero case-dependent movements. Neither a zero-regression claim nor a new algorithmic explanation is justified.

No full25-query timing or CREATE INDEX measurement was run in R1. Their commands/harness are supplied as conditional follow-ups, explicitly unexecuted. Earlier R3/R4 C9 results remain separate historical observations and are not combined with these percentages.

## Verification and setup

VM158, GCC13.3, -O2 -g -fno-lto, OpenSSL, no ICU/readline, nice10/make-j2, five fresh clean builds at matched paths. Every build passed original239 core tests and test_ginpostinglist. All non-GIN release backend objects are byte-identical to B; 7,726 source files and907 installed server headers per build are tracked. Both new variants passed1,009,216 ordering/property pairs, extreme values and both modulo-four alignment positions. Execution is x86-64 little-endian only; no32-bit/big-endian performance claim.

All five builds passed125 ordered Seq/GIN multiset, scalar and path checks,40 prepared comparisons/cached rescans and35 native answer checks. All25 row multisets repeat per timed role/cohort. Eight separate software profiles succeeded. Total3,360 raw /2,880 retained /480 warm observations. Two reversed CPU/slot/session/case-order cohorts each use six roles, two warm and12 retained Williams rounds,13 SQL plus seven real-AM cases. Warm-cache fixture:200,000 generated docs plus NULL/empty, inline, array and JSONB fixtures; JIT/parallel/memoize/autovacuum off,512MB shared_buffers. All measured retained read/write/temp/WAL counters are zero.

Final checks verified18 owned clusters shut down,12 measured backend PIDs absent, no own sockets/processes, unchanged seeds/runtime/modules/installs/final source. The local analysis reconstructed every raw order/count/answer and all804 absolute groups and2,010 pair groups. Only3e-15 relative tolerance for cross-Python sample-SD rounding was permitted; other values match exactly.

Both incremental diffs applied cleanly to their exact parents and matched committed/measured source bytes. Source was authored once on C9 and actually cherry-picked to fixed B. See PORT-NOTES.md, PATCH-VERIFICATION.json, evidence/FINAL-CHECKS-final-r1.json and REPRODUCE.md. No public packet contains PGDATA, executables,perf.data, full logs or private archive message bodies.

## Attribution

Heikki’s [2014 Small GIN optimizations message](https://www.postgresql.org/message-id/52F373CC.4050800%40vmware.com) directly proposed integer TID comparisons and private compressed-segment copying with deferred decoding. It is a direct conceptual predecessor to C9. The new experiment concerns code generation for an already established uint64 comparison scheme. No priority/algorithm novelty claim is made. [Noah’s2015 compiler discussion](https://www.postgresql.org/message-id/20150719195033.GB1300191%40tornado.leadboat.com) provides portability context; its specific compiler issue was not reproduced here. See PRIOR-ART.md and metadata for bounded search scope. The C9 attribution draft explicitly adds the2014 predecessor; its benchmark numbers remain historical R3 data.

## Artifacts

`patches/P10-incremental.diff` applies after fixed B. `patches/C10-over-C9.diff` applies after C9. They are alternatives, not a series. English UNSENT drafts, exact source plan, setup, actual-AM adapter, raw observations, complete ranges/negatives and repetition commands accompany this report. Experimental branches:

- https://github.com/pg-sharding/cpg/tree/experiments/gin-logical-tid-key-baseline-b72-20261110
- https://github.com/pg-sharding/cpg/tree/experiments/gin-logical-tid-key-c10-b72-20261110

