# B-tree: next changes after the matched V14/V7 campaigns

Date: 2026-11-09. All existing numbers below refer to pinned B72
(`72b9498df9a369e747f8d96efb5a6cd33c2451e2`), not current upstream master.
New source changes have no SQL speedup claim.

## 1. Empty qualification loop: strongest independent next candidate

The existing candidate avoids `_bt_checkkeys()` for an ordinary, non-array
page when page prechecking has already discharged every scan key. Its earlier
two-cohort unique-range screen measured CPU −8.79% / −9.29% against B72, and
−8.96% / −9.12% against its exact executable twin. Elapsed-time attribution was
weaker. This changes the unmodified B72 path and needs neither typed search nor
the IOS cache.

The immediate engineering question is whether we can keep that saving with
less code growth: `_bt_readpage` grew from 2,467 to 2,840 bytes (+15.1%). Inspect
the compiler's loop versions before factoring anything. Keep array advancement,
backward boundary checks, high-key prechecks and their assertions intact.

Next performance gate: replicate the existing candidate on the other build VM,
then expand SQL coverage to multicolumn, backward, SAOP/skip-array, bitmap,
parallel and short LIMIT controls. Do not interpret a faster unique scan as a
win for array scans. Only after the standalone result survives should it be
combined with V13 in a B72 / V13 / bypass / V13+bypass comparison.

Evidence: [earlier report](../btree-resume-20261108/third-direction/semantic-audit-v1/publication-v1/REPORT.md).
No new bypass source or timings were produced in this step.

## 2. Typed V8: remove generic attribute extraction inside the V6 kernel

V7's leaf-only change lost 5–9% on hot probes and about 9–10% on absent probes
against V6 in the latest campaign. Keep V6's typed internal descent.

The complete V6 disassembly still checks tuple-descriptor cache offsets,
attribute width and by-value representation inside each binary-search
comparison. The eligibility predicate already limits this path to one ordinary
ascending int8 attribute. For a non-NULL tuple its bytes have a known offset.
The new draft copies those eight bytes directly into a local `int64` with
`memcpy`; NULL tuples, truncated tuples and internal equality still use the
ordinary comparator. No subtraction is used for int64 comparison.

New evidence on VM158, GCC 13.3/-O2:

- Complete release and assert TUs compile; separately recompiled V6 twins are
  byte-identical.
- Release typed helper: 674 → 421 bytes; its 61-byte cold fragment disappears.
  Stack allocation in that helper: 40 → 24 bytes. This is code generation,
  **not a measured time saving**.
- Assert helper: 1,020 → 782 bytes; it retains the original same-page generic
  binary-search assertion.
- An additional linear walk using the ordinary comparator agrees for 30,240
  helper calls per version on live read-locked leaf/internal pages. Fixtures
  include unique and duplicate keys, NULLS FIRST/LAST, gaps, int64 extrema and
  an empty index. The empty index has no searchable page, so contributes zero
  helper calls. Observed root pivot forms include heap-TID suffixes and ordinary
  pivots; the reported inspected root has no NULL pivot.
- Five `amcheck` calls pass; the single owned cluster is stopped, its PID and
  socket are absent, and the existing installation is unchanged.

Next: full matched B72/twin/V6/V8 builds and the existing fixed SQL matrix,
including fresh exact1, heated exact1, absent/hot probes and int8 INSERT.
This edit does not remove the fresh-backend eligibility check or intentionally
change writes. Consequently it is not yet a proposed repair for those losses.

Artifacts: [draft and checks](typed-v8-firstattr/README.md).

## 3. IOS: reduce first-use work without slowing repeated hits

V13 retains large gains for wide posting tuples. V14's inline eligibility gate
made mixed-page CPU about 1–2% cheaper, but did not repair short-query and LIMIT
losses consistently. Repeating that gate is not the next experiment.

A different cost is visible in the source: the first eligible tuple is deformed
into owned cache arrays and then copied into the slot, even if LIMIT stops the
scan immediately. Experiment with first-use admission: initially fill the slot
normally, and populate the cache only on an actual visible reuse of the same
posting tuple. Keep a separate pending identity; a cache identity must continue
to mean that its independently owned arrays are valid. Never alias the slot's
arrays, and preserve visibility, materialization, descriptor, mark/restore and
page-lifetime contracts.

This is a tradeoff, not a free removal of work: the second use may need another
deformation, which is especially costly for wide tuples. First compare the
actual helper at reuse counts 1/2/3/4/8/long, then the fixed SQL LIMIT1/2,
short-posting, mixed-page, heap-fetch and wide controls against both B72 and
V13. Reject it if it buys LIMIT1 by losing the useful wide scan. No source draft
or measurements for this design exist yet.

## Deferred

Separator cache has no robust incremental SQL benefit over typed search.
Hybrid/midpoint search, packed posting comparator, compact scan state and lazy
dedup remain negative or inconclusive controls. Do not repeat those unchanged.
Typed specialization also has direct prior discussion; no novelty claim is
made by the new payload-load draft.

Latest completed campaigns: [results](../btree-benchmarks-20261109/RESULTS.md).
