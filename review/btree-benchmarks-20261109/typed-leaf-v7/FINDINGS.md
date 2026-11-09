# Leaf-only typed int8 B-tree V7: completed matched SQL follow-up

The full R5 correctness gate and fixed SQL campaign completed. This experiment
does not establish a general fresh-query regression repair or a clean
replacement for V6. V7 retains some random/absent-probe gains against B/T,
but loses part of V6's gain and retains several negative controls. No source,
threshold or repeat was selected after looking at these results.

B is B72; T is its exact ELF/entrypoint twin. V6 and leaf-only V7 are
independent alternatives against B72, not a series. V7 restores ordinary
internal descent and specializes initial leaf positioning only. All original
19 cases, two cohorts and six direct same-round pairs remain in the complete
three-metric tables in `BENCHMARKS.md` and authoritative `summary.json`.
Percentages below are medians of direct within-round ratios, not ratios of
absolute medians. Cohorts remain separate; negative means less time.

| Case / measure | Cohort0 L7/B | Cohort1 L7/B | Cohort0 L7/T | Cohort1 L7/T | Cohort0 L7/V6 | Cohort1 L7/V6 |
|---|---:|---:|---:|---:|---:|---:|
| perm_hot, EXPLAIN | −4.45% | +0.18% | −4.01% | +0.09% | +4.83% | +8.97% |
| perm_random, EXPLAIN | −4.04% | −5.61% | −5.87% | −4.80% | +1.86% | +3.71% |
| perm_absent, EXPLAIN | −3.57% | −3.97% | −3.24% | −3.69% | +9.45% | +9.80% |
| fresh exact1, EXPLAIN | −6.90% | +8.26% | −6.90% | −3.28% | −1.53% | +21.51% |
| fresh exact1, command CPU | +3.38% | +2.07% | +0.41% | +4.85% | −0.41% | +0.46% |
| heated exact1, EXPLAIN | +23.24% | +9.23% | +5.22% | −2.46% | −10.26% | −1.52% |
| write_i8_control, EXPLAIN | +3.07% | +4.78% | +3.65% | +3.18% | −1.04% | +1.83% |
| text_control, EXPLAIN | −3.96% | +6.09% | −2.89% | +5.42% | −3.60% | +5.94% |

Permanent hot25000 absolute B/L7 medians are21.939/20.775ms in cohort0 and
21.964/22.1845ms in cohort1. The corresponding B ranges are21.492–33.138ms
and21.793–23.214ms; L7 ranges20.653–22.907ms and21.825–26.007ms. The L7/B
paired ranges are−36.56..+6.24% and−4.09..+17.01%. The hot result therefore
cannot be summarized as a retained improvement in both cohorts.

Fresh exact1 absolute B/L7 medians are65.5/58us and49.5/54us; ranges B50–89us
and39–73us, L7 48–80us and45–114us. The L7/B paired EXPLAIN ranges are
−39.08..+54.00% and−27.69..+56.16%. CPU medians are845.55/825.49us and
809.79/826.02us, yet direct CPU ratio medians are+3.38/+2.07%; this is why
ratios of medians are not substituted for the paired result. Fresh excludes
connection startup and follows settings/metadata; it is neither cold disk
nor end-user latency.

Negatives remain visible. Heated exact1 has L7/B command CPU+17.52/+11.59%.
Append-int8 writes have B/L7 absolute EXPLAIN medians1.692/1.7405ms and
1.664/1.738ms, with L7/B command CPU+3.58/+5.79% and L7/T+4.35/+3.09%.
Permuted unique int4 writes have L7/B EXPLAIN+5.05/+0.97%, with cohort0
all twelve L7/B ratios above baseline (+0.94..+13.48%). These are observations,
not attribution to the leaf helper. Text control changes sign between cohorts.
The seqscan L7/T cohort1 EXPLAIN median is+5.02% while command CPU is−0.45%.
All controls, absolute ranges, position/predecessor diagnostics and counters
remain in the raw/summary; no control normalization or significance claim is
made. Guest CPU0/4 reversal and shared-host conditions do not establish
physical host isolation.

Four actual full builds each passed original core239. R5 matched SQL,
complete formula multisets, same-locked-page linear/fallback oracle,
lifecycle and permanent physical standby passed. The two-session empty-tree
injection barrier remains NOT RUN. There is no new native microtiming in this
wave: earlier209664 offset checks and prior V6 micro/SQL evidence are separate
historical evidence, not new V7 measurements. Actual object-code identity in
`CODEGEN-REVIEW.json` is narrower than whole-ELF or linked write-path identity.

Primary observations:2720raw,2112retained,608warm. Separate fixed-PID diagnostic
repeats are retained outside ranking. Independent arithmetic verified 456
absolute groups,684paired groups,9504direct pairs and 89660numeric values;
maximum difference was3.73e−9 in ns-scale descriptive statistics. Exact frozen
analyzer replay on a new local copy passed all plans/64write-key gzip proofs;
its audit.json/BENCHMARKS.md are byte-identical. summary.json has 662 tiny
roundoff differences between local Python3.9 and recorded Linux3.12, explicitly
recorded in `FROZEN-ANALYZER-REPLAY-r1.json`; archived VM outputs are unchanged.
Root's final live receipt verifies18own clusters stopped, PID/socket absence,
canonical seed and source7726×3/four complete installs unchanged. No accepted
sample failure/retry occurred.

R3 failed before SQL because a staged psql loaded system libpq. R4's four real
SQL backends passed, then its synthetic oracle key left `allequalimage=false`
and asserted on a posting tuple. R5 initializes actual metapage metadata with
native `_bt_metaversion`, preserving the assertion/fixture. Both earlier
failures and cleanup are preserved as harness attempts, not candidate failures.
See `HARNESS-ATTEMPTS.md`.

Published V7 commit48cf00b7cdf70f26f4f431486871eaf50adfbbf8 maps byte-exactly
to the already-built source f7324791… on parentB72. This is posthoc source
publication identity, not a new build or timing run. Earlier prototype/archive
references in the draft are carried-forward context; no new exhaustive novelty
search or new typed-comparison algorithm is claimed.
