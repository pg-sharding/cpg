# GIN C9/C11: additional write, scale and restart coverage

All five predeclared VM158 campaigns completed: 1264 raw, 1056 retained and
208 warm observations. All 188 owned cluster lifetimes stopped. An independent
offline reconstruction checked all schedules, stored large-query answers/plans,
integer-set reference digests, durable write-command bindings and all 624
absolute / 936 paired groups. Every observation and negative control remains.

This supplements the earlier C11 scan screen. Sources are unchanged, on
historical B72 `72b9498df9a369e747f8d96efb5a6cd33c2451e2`, with the common
supplied prerequisite in every tree. Fixed B is
`8a8c475037bfde101da23cc9b0364c9c020eca93`, C9
`0ab3bd65c8957ea5e25f9ef8981401f0616d99de`, C11
`ca6ad39111cd67f20ff2dd3a8f619239d0360a10`. This is not current-master evidence.
C11's large advantage over B is chiefly inherited from C9; its incremental
comparison is C11/C9. These are alternatives, not patches to apply together.

For the warm one-million-row `common & rare0` query, SQL executor medians were
3.9135 / 3.9305 ms for B, 1.127 / 1.164 ms for C9 and 1.106 / 1.146 ms for C11
in cohorts 0 / 1. Direct paired medians versus B were −71.60% / −70.33% for C9
and −71.72% / −70.95% for C11. C11/C9 was +0.39% / −1.60%, with mixed signs.
For `common & rare2`, C9/B was −20.95% / −24.35%, C11/B −23.13% / −22.66%.

The heap plus index occupies 97,517,568 bytes against 67,108,864 shared-buffer
bytes. The working set is not claimed to exceed RAM. Repeated answer queries,
copying, hashing and qualification warm the OS cache. After restarting the own
postmaster before every target query, `common & rare0` executor medians were
20.769 / 20.4865 ms for B, 17.9935 / 17.8745 for C9 and 18.197 / 17.791 for C11.
Paired improvements shrink to −14.00% / −13.67% and −13.53% / −13.06%.
This is empty shared buffers with warm OS cache, not cold-storage performance;
postmaster startup is excluded from query latency. Only four retained rounds
per role/case/cohort were declared for this mode, versus twelve for the others.

Full-read and dense/OR results are smaller and mixed. Warm full-read C11/C9
executor time was +0.31% / +1.78%; there is no general C11 upgrade conclusion.
The restarted Seq control moved +6.53% / −0.75% for C11/B, with identical-B
T/B −1.46% / +4.66%. Warm Seq C9/B was −4.06% / +1.61%. No result is corrected
with the twin, no cohorts are pooled, and small changes are not causal claims.

CREATE INDEX on 200,002 docs had B CPU medians 135.600 / 135.925 ms, C11
129.745 / 129.678 ms, paired −4.21% / −4.34%. INSERT SELECT of 5,000 docs had
B 46.258 / 46.697 ms and C11 43.828 / 44.843 ms, paired −4.17% / −3.48%.
These scan-oriented changes do not establish an intended build/write algorithm
improvement: compiled layout and environmental effects remain possible.
INSERT client wall has large durability/scheduling variation, including C11
cohort-1 median 81.517 ms versus B 65.257 ms despite the same-round ratio's
different sign. Both summaries and every raw pair are retained. VACUUM CPU
C11/B was +1.31% / −1.98%, also mixed. WAL, process write bytes, run queue and
wall time are separate metrics in the full tables.

The write harness executes amcheck, exact table count, ordered Seq/GIN digests
and forced-index plan checks after each measured operation. It stores the
reference digests, a PASS receipt and resulting relation shape, but not every
individual validation plan/digest output. The independent audit does not
claim to reconstruct those unrecorded outputs. Large-query raw plans and
scalar answers were stored and independently checked for every sample.

`report/BENCHMARKS.md` contains every metric, absolute min/median/max, sample
SD/MAD and all six direct role pairs. `analysis/*-recomputed.json` retains every
numerical vector. Replay and new-host build/setup commands are in REPRODUCE.md;
the English draft is UNSENT. There is no new algorithmic novelty claim: earlier
discussion already covered logical TID keys and deferred segment consumption:
https://www.postgresql.org/message-id/52F373CC.4050800%40vmware.com
