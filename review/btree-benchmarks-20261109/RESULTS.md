# B-tree: matched SQL experiments, 9 November 2026

IOS V14 and typed leaf V7 completed their fixed comparisons. Neither is selected
as a general replacement for its parent. All comparisons use pinned PostgreSQL
B72 (`72b9498df9a369e747f8d96efb5a6cd33c2451e2`), not today's master.

Percentages below are medians of direct same-round ratios. Two numbers mean
cohort 0 / cohort 1; negative means less time. Cohorts are reported separately.

| Experiment | Actual result | Decision |
|---|---|---|
| IOS V14 eligibility gate | Eight-text COUNT execution time −24.07% / −29.40% versus B; fixed32 COUNT −43.43% / −44.62%; wide32 tail −56.60% / −55.20% | Retains the wide-posting benefit, without a general improvement over V13 |
| V14 mixed-page CPU versus V13 | Forward mixed2 −1.06% / −1.36%; backward mixed2 −1.09% / −1.97% | A small measured tradeoff; individual paired ranges cross zero |
| V14 short-query negatives | LIMIT2 CPU +1.25% / +1.43% versus B, +0.66% / +3.14% versus V13; cohort 1 execution time +11.48% versus B | No blanket LIMIT regression repair; executor time and whole-command CPU differ |
| Typed leaf V7 | Permanent absent execution time −3.57% / −3.97% versus B, but +9.45% / +9.80% versus V6 | Leaf-only specialization gives up much of V6's benefit |
| V7 hot lookup and write negatives | Hot execution time −4.45% / +0.18% versus B, +4.83% / +8.97% versus V6; int8 INSERT +3.07% / +4.78% versus B | No general replacement for V6; write regressions remain |
| V7 fresh exact lookup | Execution time −6.90% / +8.26% versus B; whole-command CPU +3.38% / +2.07% | No robust repair claim; the earlier V6 fresh regression did not repeat uniformly in this campaign |

For absolute scale: IOS cohort 1 wide32 tail execution medians were B 47.5995 ms,
V13 22.632 ms, V14 22.373 ms. Typed permanent hot medians were B/V7
21.939/20.775 ms and 21.964/22.1845 ms. Ratios of these displayed medians
need not equal the paired percentages above.

IOS completed four fresh builds, 239 original core tests each, finite dispatch,
cache and ownership gates, and a separate 76-command smoke. Its fixed SQL matrix
contains 2,128 raw / 1,824 retained / 304 warm observations across all 19 cases,
four roles and two cohorts. The independent audit checked 49,172 numeric values.

Typed uses four previously completed matched builds, 239 original core tests
each. Its new SQL/oracle/lifecycle/physical-standby gate and 76-command smoke
passed. Its fixed matrix contains 2,720 raw / 2,112 retained / 608 warm
observations. The independent audit checked 89,660 numeric values; the strict
analyzer also verified complete write-key multisets. Two earlier harness
failures, involving client library selection and synthetic-key metadata, are
preserved separately and produced no accepted timing samples.

The exact baseline executable twin, every negative control, full plans, absolute
ranges and all direct role pairs remain in each packet. No samples were trimmed,
no twin correction was applied, and cohorts were not pooled. Shared VM load and
same-code control movement limit causal interpretation. Local artifact replay
is distinguished from the original Linux runs. CREATE INDEX was fixture setup,
not a measured optimization target.

Final read-only checks confirmed all 17 IOS and 18 typed owned clusters stopped,
PID/socket absence, and unchanged source/install inputs. Foreign services were
untouched.

The other retained B-tree directions are independent: empty-qualification-loop
bypass has about 9% lower CPU on its earlier range-scan screen, with weaker
elapsed-time attribution; separator cache V2 has no robust incremental benefit
over typed search. Hybrid search, packed comparator, compact scan state and
lazy dedup remain archived controls or negative experiments.

Source branches, verified against the actual built source bytes after the runs:

- [IOS V14](https://github.com/pg-sharding/cpg/tree/experiments/btree-ios-v14-b72-20261109), commit `113e61347b43d2ae4afb187944ede9e9f6108c24`.
- [Typed leaf V7](https://github.com/pg-sharding/cpg/tree/experiments/btree-typed-leaf-v7-b72-20261109), commit `48cf00b7cdf70f26f4f431486871eaf50adfbbf8`.

The Git commits are post-run source identities, not additional builds. Full
results, English UNSENT drafts, alternatives, source manifests and reproduction
scripts are in the separate IOS V14 and typed V7 publication packets.
