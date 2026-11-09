# GIN: full SQL confirmation of advance V4 and lazy V4

Both alternatives retain large selective SQL gains on the new common baseline.
Advance V4 now has full-backend SQL evidence. Neither alternative is a general
replacement: repeated negative movements remain, including advance's absent
case and an off-path Seq control whose cause is unresolved.

This wave started on 9 November and completed on 10 November 2026, +05:00.
Baseline is B72 `72b9498df9a369e747f8d96efb5a6cd33c2451e2` plus the same
supplied prerequisite in every tree. These are fresh observations, not a
current-master claim or pooled historical data. Candidate source was unchanged.

## Actual SQL gains

Absolute retained EXPLAIN Execution Time medians in ms, cohort 0 / cohort 1.
Each listed selective command performs 100 probes. Percentages are medians
of 12 direct same-round whole-backend-command CPU ratios in each cohort;
they are not ratios of the absolute medians.

| Case | Baseline ms | Advance V4 ms | Lazy V4 ms | Advance/B CPU % | Lazy/B CPU % |
|---|---:|---:|---:|---:|---:|
| Common/rare FTS | 79.2875 / 79.6255 | 34.8645 / 36.9435 | 29.4185 / 29.8335 | -55.80 / -53.24 | -63.07 / -62.97 |
| JSONB containment | 153.2210 / 155.1050 | 66.0725 / 71.5810 | 53.8735 / 54.6835 | -56.53 / -55.16 | -64.52 / -64.39 |
| intarray | 80.2470 / 78.6115 | 34.0210 / 35.0985 | 28.1725 / 28.3175 | -56.07 / -54.99 | -64.07 / -63.86 |
| Builtin array | 78.9805 / 77.5750 | 35.2365 / 34.7310 | 28.3480 / 27.6675 | -56.32 / -54.72 | -63.85 / -64.19 |
| Grouped skew | 57.3435 / 61.4850 | 23.3880 / 29.4180 | 11.5160 / 12.7400 | -58.56 / -54.14 | -79.55 / -80.27 |
| FTS skew127 | 149.0540 / 157.1080 | 106.2500 / 104.1555 | 163.8715 / 148.2635 | -28.80 / -29.35 | -0.98 / +0.49 |

The common/rare FTS, JSONB and grouped targets improve in all 12 paired CPU
observations against both B and its exact-executable twin in both cohorts.
This is finite observed evidence, not an independent-host confidence claim.
Advance also helps the moderately selective skew127 case where lazy is near
neutral in paired CPU. Lazy is better on the strongest common/rare and grouped
targets; advance is better on the positive phrase/NOT cases. The candidates
have not been combined and their gains cannot be added.

For common/rare FTS, cohort 0 absolute min/median/max ms are B
77.595/79.2875/119.467, A4 34.277/34.8645/55.900 and L4
27.782/29.4185/45.331. Cohort 1: B 77.785/79.6255/122.641, A4
35.546/36.9435/51.935 and L4 28.008/29.8335/45.464. All 25 cases,
three metric boundaries, six direct pairs, ranges, MAD, sample deviation
and individual values are in [the full tables](results/ALL-RESULTS.md),
[absolute.csv](results/absolute.csv), [pairs.csv](results/pairs.csv) and JSON.

## Negative results and unresolved controls

Direct paired whole-command CPU percentages versus B, cohort 0 / cohort 1:

| Case | Advance V4/B CPU % | Lazy V4/B CPU % |
|---|---:|---:|
| Absent | +7.26 / +6.65 | +0.84 / +5.71 |
| Tiny inline conjunction | -3.77 / -1.78 | +5.60 / +5.17 |
| Full-consumption single key | +2.44 / -1.90 | +2.60 / +2.58 |
| Forced OR | -0.63 / +3.79 | +2.00 / +1.23 |
| Dense conjunction | -0.62 / -2.07 | +0.75 / +3.85 |
| Inline single | -0.56 / +2.30 | +1.13 / +1.13 |
| Dense array | +0.01 / -4.48 | -1.59 / -0.76 |
| Off-path Seq control | +8.69 / +11.21 | +6.30 / +8.06 |

Advance absent medians are B 1.3020/1.1785ms versus A4 1.3645/1.2595ms.
Paired CPU versus the exact twin is also positive, +5.66/+4.39%. Its paired
A4/B CPU ranges are -0.20..+26.38% and -33.54..+39.79%; 11/12 pairs are
positive in each cohort. This repeated movement remains an open issue.
Lazy's tiny-inline CPU cost repeats too; versus the twin it is +6.76/+2.23%.
The full-read lazy CPU movement repeats versus B but is -0.20/+1.36% versus
the twin, so the controls matter.

Seq control has no GIN index path. B medians 64.6950/63.3960ms become A4
70.3315/70.1260ms and L4 71.1295/69.4675ms. Exact-twin CPU itself moves
+3.90/+1.30% versus B. A4/T paired CPU is +1.98/+11.70%, L4/T +3.91/+4.12%.
Its observed pair ranges are broad and cross zero in both cohorts: A4/B
-15.49..+70.15% and -10.94..+46.59%, L4/B -22.56..+90.04% and
-8.85..+19.67%. Keep these observations as unresolved control movements;
neither an algorithmic GIN cause nor a harmless-noise explanation is proved.
They are not normalized away and prevent a general speedup claim.

Some absolute medians and direct paired percentages differ substantially,
including skew127 and forced OR. Distributions move within the run; the raw
chronology and all paired values are retained. Do not divide aggregate medians
and call that the paired result. No trimming, pooling or control correction
was applied. Small SQL costs are not considered repaired by earlier native
results, and V3 was not a role in this campaign.

## Execution and checks

- VM158, 8 logical CPUs / 4 physical cores, 16GB RAM; shared host. Unrelated
  workloads were untouched; load snapshots were roughly 3.2–4.1. VM84 was
  initially overloaded and the read-only archive host was not used.
- GCC 13.3.0, common source/build/compiled-prefix paths, fresh build directories
  and separate DESTDIR installations; `-O2 -g -fno-lto`, OpenSSL, no ICU/readline,
  nice 10, make -j2. Four full builds each passed original 239 core tests:
  B/L4/A4 release plus A4 assertions. Expected files stayed unchanged.
- One baseline-built physical seed: 200000 generated rows plus NULL/empty rows,
  FTS/intarray/JSONB/builtin-array indexes, inline fixture. Every clone was
  verified and fsynced before role assignment. No candidate-specific build
  timing, new native microbenchmark or combined candidate was measured.
- Initial ordinary qualification: 100 full Seq/GIN multiset comparisons,
  100 frozen scalar checks, expected plans and 32 generic prepared parameter
  checks with a repeated cached GIN execution. Each variant's 25-case reference
  contains 982001 rows. Each measured cohort additionally checked all 100
  role/case Seq/GIN multisets and cross-role equality.
- Two fresh four-role cohorts, B/T share the exact ELF; server/client CPU
  0/4 then 4/0, reversed physical-role slots/session births/case order.
  25 cases, 2 warm + 12 retained Williams4 rounds: 2800 raw, 2400 retained,
  400 warm. Literal-answer execution precedes every measured EXPLAIN.
- JIT/parallel/memoize/autovacuum off, 512MB shared_buffers, 64MB work_mem
  except the original 64kB lossy case, explicit system timing clock. Retained
  root-plan shared reads/dirties/writes, temp IO and WAL bytes are all zero;
  whole-command backend read/write bytes are zero too. This is warm-cache SQL.
- Both local Python 3.9 and remote Python 3.12 recounts passed 13100 checks;
  their Markdown and audit are byte-identical. Derived statistics allow only
  2e-15 final float rounding differences; raw/scalar/order/count checks are
  exact. All 13 own ordinary clusters, their postmasters and eight measured
  backends are stopped/absent; no process uses our installs/build executable.
  All 7726 source files, four installs, seed and frozen inputs stayed unchanged.

Candidate source revisions and runtime/build receipts are in
[build-source/SOURCE.json](build-source/SOURCE.json) and `evidence/`.
[REPRODUCE.md](REPRODUCE.md) gives exact build/setup/run commands.
[PRIOR-ART.md](PRIOR-ART.md) records previous discussion and the bounded
contribution. The English [draft](email-draft-UNSENT.txt) is unsent.
