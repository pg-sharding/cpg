# C11 ordinary SQL and actual AM screen

All five new matched builds and finite correctness gates passed. The fixed screen completed 2400 raw / 2000 retained / 400 warm observations. C11 retains the combined C9 gains against fixed B, but this screen does not establish a general improvement over C10. Actual-AM full scan regressed against C10 by +5.93% in cohort 0 and +0.28% in cohort 1. No full 25 timing promotion was run.

Independent recount passed all 670 absolute groups, 1,340 pair groups and 13,400 direct pairs. Retained SQL shared reads/dirties/writes/temp/WAL and backend read/write-byte counters were zero. Plan/actual-row/loop signatures matched within every case/cohort. Ten clusters stopped cleanly; source, installed trees, module and seed remained unchanged.

Percentages are medians of ten direct paired values:100*(C11/comparator-1), with negative faster. Cohorts stay separate and swap CPUs 0/4, clone assignment, session and case order. Exact B/T twin drift is uncorrected. Every absolute CPU/wall/executor value and min/median/max/mean/sampleSD/MAD is in absolute.tsv; pairs.tsv and direct-pairs.tsv retain all comparisons.

## SQL executor

| Case | Cohort | B median ms | C11 median ms [min,max] | C11/B % | C11/C9 % | C11/C10 % | T/B % |
|---|---:|---:|---:|---:|---:|---:|---:|
| skew1000 | 0 | 76.538500 | 19.100500 [18.975000,19.157000] | -75.03 | -2.39 | +0.52 | -0.17 |
| skew1000 | 1 | 78.499000 | 19.843500 [19.767000,19.976000] | -74.74 | -2.19 | -0.33 | -0.07 |
| skew127 | 0 | 139.117000 | 103.797500 [103.196000,105.880000] | -25.44 | +0.93 | +1.26 | -0.87 |
| skew127 | 1 | 144.565000 | 105.855500 [103.555000,106.214000] | -26.73 | -0.61 | -0.58 | -2.90 |
| dense_and | 0 | 82.319500 | 78.217500 [76.324000,83.302000] | -4.71 | -3.37 | +0.91 | +0.02 |
| dense_and | 1 | 83.871500 | 77.819000 [76.343000,80.736000] | -7.42 | -5.65 | -1.18 | -1.58 |
| or_forced | 0 | 152.547500 | 152.910000 [152.368000,156.875000] | +0.48 | -0.80 | +0.40 | -1.04 |
| or_forced | 1 | 154.066500 | 149.998000 [148.782000,152.266000] | -2.51 | -1.71 | +0.64 | -1.52 |
| single_forced | 0 | 145.690500 | 145.981500 [143.565000,148.150000] | -0.30 | -1.08 | -0.60 | -1.09 |
| single_forced | 1 | 146.798000 | 143.064500 [140.445000,144.980000] | -2.60 | -0.76 | +1.24 | -2.07 |
| single_rare | 0 | 5.977000 | 5.895500 [5.810000,6.212000] | -0.82 | -2.16 | -0.49 | +0.18 |
| single_rare | 1 | 6.046000 | 6.007500 [5.892000,6.106000] | -0.59 | -0.83 | -2.64 | +0.24 |
| inline | 0 | 0.439000 | 0.407000 [0.394000,0.420000] | -7.39 | -3.10 | +0.99 | +0.11 |
| inline | 1 | 0.450000 | 0.415000 [0.400000,0.423000] | -7.41 | -0.24 | -2.22 | -0.11 |
| jsonb | 0 | 150.622000 | 34.028500 [33.783000,35.015000] | -77.42 | -3.03 | +0.31 | +0.12 |
| jsonb | 1 | 148.253500 | 35.046500 [34.509000,35.338000] | -76.38 | -1.57 | +1.02 | +0.07 |
| lossy_and | 0 | 129.997500 | 129.469000 [128.397000,131.338000] | -0.20 | -0.42 | +1.51 | +2.69 |
| lossy_and | 1 | 130.917500 | 129.713000 [127.649000,130.752000] | -1.45 | -1.60 | -1.57 | +1.80 |
| seq_control | 0 | 57.511500 | 56.730000 [54.840000,62.743000] | +1.27 | +2.33 | +1.50 | -3.93 |
| seq_control | 1 | 57.709000 | 59.440500 [57.817000,64.264000] | +5.27 | +0.66 | +2.97 | -1.97 |
| skew_group4096 | 0 | 57.892000 | 6.569000 [6.536000,6.744000] | -88.64 | -1.50 | +1.08 | -0.38 |
| skew_group4096 | 1 | 56.045500 | 6.353000 [6.309000,6.511000] | -88.66 | -1.30 | +0.15 | +0.22 |
| inline_single | 0 | 2.811000 | 2.797500 [2.704000,2.870000] | -0.81 | -2.40 | -0.26 | +0.60 |
| inline_single | 1 | 2.818000 | 2.726500 [2.713000,2.747000] | -3.15 | -5.36 | -0.82 | +0.09 |
| absent | 0 | 1.281000 | 0.320500 [0.301000,0.323000] | -75.39 | +0.01 | +1.60 | -1.32 |
| absent | 1 | 1.159000 | 0.301500 [0.297000,0.322000] | -74.13 | -0.99 | -5.38 | -0.13 |

## Actual AM loop CPU

| Case | Cohort | B median ms | C11 median ms [min,max] | C11/B % | C11/C9 % | C11/C10 % | T/B % |
|---|---:|---:|---:|---:|---:|---:|---:|
| am_inline | 0 | 17.755954 | 14.377719 [14.316036,14.453502] | -19.09 | -2.62 | +0.34 | +0.10 |
| am_inline | 1 | 17.898908 | 14.348986 [14.311589,14.399240] | -19.95 | -4.02 | -0.14 | -0.34 |
| am_absent | 0 | 54.674498 | 6.813811 [6.772925,6.903361] | -87.54 | -0.76 | +0.98 | +0.21 |
| am_absent | 1 | 54.320731 | 6.985239 [6.963951,7.007828] | -87.14 | -1.99 | -0.35 | +0.11 |
| am_skew1000 | 0 | 71.268502 | 12.583591 [12.494031,12.746010] | -82.37 | -4.39 | -0.01 | -0.04 |
| am_skew1000 | 1 | 70.789118 | 12.545253 [12.476305,12.765209] | -82.29 | -4.84 | -0.08 | -0.02 |
| am_full | 0 | 98.054463 | 94.269207 [94.046298,94.958467] | -3.83 | +0.50 | +5.93 | -0.69 |
| am_full | 1 | 96.641638 | 88.966939 [88.919443,89.047705] | -7.98 | -4.83 | +0.28 | +0.04 |
| am_or | 0 | 110.647880 | 102.314152 [102.151042,102.916120] | -7.50 | -5.00 | +0.43 | +0.35 |
| am_or | 1 | 110.185580 | 101.816390 [101.709429,101.891832] | -7.60 | -5.23 | -0.75 | -0.14 |
| am_dense | 0 | 43.576776 | 38.551440 [38.467843,38.717429] | -11.46 | -7.89 | -0.43 | +0.10 |
| am_dense | 1 | 43.465680 | 38.476833 [38.324508,39.122557] | -11.54 | -7.92 | -0.73 | +0.01 |
| am_rare | 0 | 10.832783 | 10.630795 [10.576304,10.832397] | -1.95 | +0.49 | +3.40 | -0.77 |
| am_rare | 1 | 10.692147 | 10.240319 [10.218066,10.268942] | -4.18 | -2.43 | +0.42 | -0.15 |

## Limits and provenance

There are 13 timed SQL cases and 7 actual AM cases. All25 original SQL cases were checked for ordered Seq/GIN multisets and frozen scalars on B/C9/C10/C11/C11_assert. AM loop clocks include real index_rescan/index_getbitmap/tbm_free startup and consumption; output conversion is outside that loop. Whole backend CPU and client wall are separate metrics.

C11 is a header-only increment over C10. B comparisons also include C9 deferred decoding and advancement, so their large gains cannot be attributed to the header increment. SQL Seq C11/B is +1.27%/+5.27%; exact T/B is -3.93%/-1.97% there. The full-AM C11/C10 difference changes markedly across cohorts. Controls limit small-difference and source-causal claims. No trimming, pooling, normalization, repeats or posthoc case removal was used. The old header-only P11 absent regression belongs to another population and is not declared repaired.

Raw B72:72b9498df9a369e747f8d96efb5a6cd33c2451e2. FixedB:8a8c475037bfde101da23cc9b0364c9c020eca93; C9:0ab3bd65c8957ea5e25f9ef8981401f0616d99de; C10:cf6df20681101bc58dcb5cf47d3fafd738aaa458; C11:ca6ad39111cd67f20ff2dd3a8f619239d0360a10. GCC 13.3, -O2 -g -fno-lto, release timed roles, nice10, fullclean common paths and DESTDIR installs. B/T share the exact installed baseline ELF.

VM158 namespace:/home/reshke/allfuzz/gin-next-c11-bitmap-20261110. A quiet process window with no active compiler preceded timing. Earlier correctness builds ran under recorded foreign-build load. This is finite serial synthetic coverage, without concurrency/general-merge qualification. No second-host, larger/restart-cache, CREATE INDEX/INSERT/VACUUM result is claimed here.

Reproduce with ../c11/REPRODUCE.md and its build-harness/README.md. Workload/setup/answers/native module bytes are retained; fresh output directories are required. Raw/analysis is in ../screen-evidence-r1/screen-r1; audit is ../audit-screen.py. This report does not publish or send mail.
