# GIN K3 memo: dense penalty reduced, remaining regressions preserved

K3 is a standalone builtin-tsquery last-vector memo with a fixed fallback after
64 consecutive misses. It reduces K1's dense SQL penalty but does not remove
it: executor time is5.71% /5.63% lower than K1 and still2.62% /3.02% above B.
OR SQL executor time is4.25% /3.01% lower than B. Full single-term SQL is mixed,
and rare-single and prefix negatives remain. There is no general adoption claim.

The complete fixed comparison passed2576 raw /2208 retained /368 warm,
23 SQL/AM cells, four roles, two cohorts and12 retained rounds. All608 absolute
groups,912 pair groups and10944 direct pairs are retained. Independent arithmetic
and root replay matched79040 numerical fields;200 ordered oracles and32 complete
plan/row/loop signatures passed. All17 gate/smoke/accepted cluster lifetimes
stopped, with full source/install/seed/helper/input identities unchanged.

- [Findings and every primary cell](FINDINGS-K3-r1.md).
- [All metric groups and spreads](RESULTS-ALL-GROUPS-K3-r1.md), plus analysis/.
- [English new-thread draft, UNSENT](email-draft-K3-UNSENT.txt).
- Canonical standalone source: source/K3-canonical/K3-over-fixed-B.diff and
  source/K3-canonical/K3-over-fixed-B-root.patch. K1-reference is an alternative,
  not an earlier patch in a series.
- [Source/build/setup/SQL/AM replay](REPRODUCE.md); restore-raw.py reproduces
  original selected evidence byte-for-byte for offline analysis.

Sources are historical raw B72 72b9498df9a369e747f8d96efb5a6cd33c2451e2,
fixed B8a8c475037bfde101da23cc9b0364c9c020eca93, K1
9e0d6e84c5bd538e58a534c99cb39ca669c567b7 and K3
ec32d586cf3bb6cfa76eb672db70160b436ce47c. B/T are exact executable twins.
These are not current-master results. Four clean full builds passed unchanged
core239 and posting-list tests. Ordinary/native/budget/generic-fallback gates
include160 ordered SQL cases and51744 new budget-dispatch checks.

VM158 used an own quiet window, labelled FRESH_HOST_CLEAN_SCREEN; physical
isolation is not established. Cohort0 has material exact-twin variation:
OR AM inner CPU T/B−9.50%, dense−6.61%. Neither cohort is dropped or normalized.
All SQL executor, whole backend CPU/client wall and AM inner CPU/wall metrics
stay separate. Raw IO/runqueue/fault diagnostics and negatives are preserved.
The source threshold was not retuned after observations. A future untimed
dispatcher diagnostic is a separate follow-up, not evidence in this packet.

The source/lifetime/prior-art review credits the2014 cache proposal. No novelty
claim is made for memoization or adaptive fallback. Exact original input READMEs
and preparer-history/ preserve their historical planned statuses; this README
and the actual measured receipts describe the completed campaign. The new
portable replay.py frontdoor has only AST/help/source-binding checks; the
original production controllers executed, but a separate Linux replay through
that new frontdoor has not. The read-only final-proof helper's foreign-UID
access failure is preserved separately from its corrected own-UID proof;
no benchmark was retried. Nothing has been sent to the mailing list.
