# Hash: no-op qualification plus recent-buffer hint

Completed 9 November 2026 on VM158. **The combined candidate C is not selected
as an additive improvement over H.** Both retained cohorts have higher CPU
and executor-time medians for C/H on the two intended rescan workloads.
The standalone hint H retains a useful narrow rescan signal; its tiny/absent
controls and uncertainty remain. The earlier large no-op random-query gain
was not repeated in this independently rebuilt campaign.

B = public PostgreSQL B72 `72b9498df9a369e747f8d96efb5a6cd33c2451e2`, not
current master; T = the exact same installation/ELF on a separate postmaster;
N = no-op cleanup `3fc5ad43e3f932374ad4eb1fa7e2da041e5ffc3b`;
H = buffer hint `989ba16d4557d01e9d0cf71dcf2ffe729b750f37`;
C = normal `git cherry-pick -x N` onto H, no conflicts:
`909e76d48524f5f2c9bfed09c01f25195fb1798a`.

[Experimental source branch](https://github.com/pg-sharding/cpg/tree/experiments/hash-noop-buffer-b72-v1-20261109).
No main/MDB branch was changed. N/H/C are alternative complete B72 patches.
`source/C/code.diff` is standalone. `source/H/commit.patch` followed by
`source/C/commit.patch` is the dependent two-commit form; do not apply all
three alternative standalone diffs as a series.

## Measured result

Percentages below are medians of ten direct same-round ratios; negative
means less time. The slash separates cohorts, not confidence limits.
All ranges and all ten role pairs for all 19 cases and three metrics are in
[BENCHMARKS.md](BENCHMARKS.md) and analysis/. Medians of individual times are
not used to calculate these percentages.

| Case | H/T CPU | C/T CPU | C/H CPU |
|---|---:|---:|---:|
| uniform_hot_rescans | -7.16% / -11.52% | -5.86% / -7.54% | +2.94% / +5.16% |
| uniform_hot_varying_residual | -11.99% / -7.28% | -10.07% / -7.55% | +3.17% / +1.14% |
| tiny_forced | +1.46% / +1.28% | +2.43% / +3.55% | +0.98% / +3.36% |
| uniform_random | -1.34% / +0.26% | +0.06% / -0.32% | +0.34% / +3.76% |
| seq_control | +1.59% / -2.21% | -1.90% / -2.97% | -3.14% / -1.21% |
| max_collisions_absent_forced | +1.35% / +0.66% | -1.66% / +8.73% | -2.91% / +9.07% |
| skew_duplicates | -0.14% / +2.73% | -3.44% / +0.12% | -1.94% / -4.60% |

Whole-command backend CPU medians, milliseconds per complete SQL command
(the two rescan commands each perform 3000 actual index loops):

| Case | B | T | N | H | C |
|---|---:|---:|---:|---:|---:|
| uniform_hot_rescans | 2.446957 / 2.436027 | 2.443392 / 2.469506 | 2.411043 / 2.451785 | 2.264659 / 2.174418 | 2.309326 / 2.302060 |
| uniform_hot_varying_residual | 3.591816 / 2.416251 | 3.269331 / 2.334940 | 2.393458 / 2.372020 | 3.367028 / 2.192676 | 3.450765 / 2.193423 |
| tiny_forced | 1.591193 / 1.617592 | 1.599902 / 1.612866 | 1.608324 / 1.623662 | 1.629996 / 1.619992 | 1.634823 / 1.683191 |
| uniform_random | 7.045354 / 5.141132 | 7.150587 / 5.398327 | 7.226565 / 5.300901 | 7.170567 / 5.290941 | 7.166370 / 5.384006 |

N/T random CPU is **+1.44% / -0.91%**, so the old 7–12%
random-query reduction against twin is historical, not a newly confirmed
result. H/T tiny forced CPU is **+1.46% / +1.28%**; H/B absent is
**+1.24% / +7.70%**, versus H/T **-3.94% / +1.58%**.
These controls do not establish that the earlier regressions were repaired.
C/H skew duplicates improves, while C/T MAX-absent-forced has a second-cohort
penalty; both remain in the full results. No general winner is declared.

The spread is substantial: e.g. first-cohort C/H residual CPU ratios range
from −20.24% to +83.95%. The second-cohort range is −7.72% to +7.13%.
Baseline/twin and off-path sequential controls also move. The sequential
control C/T CPU medians are -1.90% / -2.97% despite using no hash
index. We retain these observations without trimming, normalizing by controls,
claiming significance, attributing all changes to the deleted calls, or
starting timing-driven extra repetitions. The two cohorts switch sibling
logical threads on the same guest core pair; they are not independent hosts
or physical-core replications. The VM is shared.

## What actually ran

- Five serial fullclean builds: B/N/H/C release and C assertions, identical
  source/build/configured-prefix paths with separate DESTDIR installs.
  GCC 13.3, `-O2 -g -fno-lto`, `LDFLAGS=-fno-lto`, ICU/readline disabled,
  OpenSSL, nice 10 and two compile jobs. Each passed all 239 unchanged core
  tests with maximum two connections; expected files remained unchanged.
- Finite ordinary checks on five additional clones: 8,862,720 valid page
  cases normal/UBSan; 95 complete 19-case SQL multiset/answer/plan checks;
  90 historical multisets, 630 lifecycle and 105 cursor checks. Concurrent
  writers and replacement instrumentation were not repeated; this is not
  general merge qualification.
- Fresh baseline seed and ten full durable copies before role assignment;
  a separate five-copy smoke passed all 95 observations, zero accepted
  timing samples. Ten measurement copies remained stopped and unchanged.
- Fixed 19 cases × five roles × (two warm + ten retained) × two cohorts:
  2280 raw/1900 retained/380 warm. All answers, plans, loops, rechecks,
  Memoize policy and retained resident-read gates passed. Every raw response
  was fsynced before parsing/acceptance. All negatives remain.
- Independent, separately implemented audit passed all 85,500 numeric
  comparisons (maximum floating-point difference2.84e−14), chronology,
  all 2280 answers/plans and recorded source→build→gate→runtime→backend
  bindings. See independent-results-r1/INDEPENDENT-AUDIT.json.
- Final guards passed for all five installations/907 headers each,7726 source
  files, support, original seed and frozen inputs;16 seed/smoke/measurement
  clusters were stopped and own tracked PIDs absent. The five earlier gate
  clusters have separate clean-stop receipts. No unrelated service changed.

Normal object ASM confirms qualification call relocations B/N/H/C =2/0/2/0.
H/C hashpage disassemblies and recorded objects are byte-identical; both have
**two static** ReadRecentBuffer callsites. The first diagnostic incorrectly
expected one; its assertion stopped before receipt/accepted timing and the
corrected evidence records the assumption. This was a code-presence check,
not a timing threshold or a count of dynamic buffer accesses.

## Scope, prior discussion and artifacts

This is cleanup/composition of an existing buffer API, not a novel hashing
algorithm. A bounded earlier history search covers the
[scan/recheck contract](https://www.postgresql.org/message-id/20080516130442.GP28382%40it.is.rice.edu),
[per-tuple cleanup](https://www.postgresql.org/message-id/23649.1216398205%40sss.pgh.pa.us),
and [page-at-a-time loader](https://www.postgresql.org/message-id/CAA4eK1LnQi51L8%2BmsZasZ926fbiO7BGpjeaY5XcgQn3Xdcvm3w%40mail.gmail.com).
It does not prove absence of other proposals; CommitFest/current-master
status was not refreshed for this composition. The concrete contribution
here is a matched five-role test and its negative additivity result.

[English UNSENT draft](email-draft-UNSENT.txt), [reproduction](REPRODUCE.md),
[all metrics](BENCHMARKS.md), source/, collected/, analysis/ and the independent
audit are included. Raw is chunked only for transport and can be restored
losslessly. The original raw digests are c0
`1ed4b619f1c0e3f683fd795647d7d24c15ca7ddc93249af19579c26ef2ebb046`,
c1 `ec751009d55d71c83204d1f3094444f20cc21b7e1d47fb8291587a10080af569`.
No native-kernel speed or CREATE INDEX improvement is claimed. The native
complete-TU page oracle is untimed; the new performance result is the SQL
composition screen. Historical parent results remain unchanged. No email sent.
