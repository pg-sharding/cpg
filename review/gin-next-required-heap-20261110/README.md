# GIN required-entry heap experiment

The copied-key heap improves the tested wide-OR actual-AM CPU loop, while
this screen's SQL sharing cases regress. At required widths 8/32/128/512,
Heap/B paired CPU changes were -11.98/-22.65/-28.32/-27.12% in cohort 0 and
-11.67/-22.52/-26.50/-23.90% in cohort 1. B/Heap absolute CPU medians at width
512 were 1113.065/810.601 ms and 1108.378/842.687 ms. Startup/allocation and
bitmap consumption remain inside that actual-AM loop.

Tiny widths 1/2/7 were 1.1% to 2.0% slower. SQL sharing8 regressed +1.83% /
+2.04%, sharing32 +3.02% / +3.86%, and absent512 +1.19% / +2.00%. Exact twin
Seq executor drift was -0.57% / +4.97%. Every control, spread and negative is
retained; no broad SQL, source-causality or merge recommendation follows.

The prototype owns per-key heap items with copied lower-bound TIDs, repairs
a stale root lazily and uses the baseline path below eight required entries
or under fuzzy search. Copied monotone lower bounds address shared entry
advancement by another key; a heap of mutable entry pointers alone would not.
Heikki Linnakangas proposed heaps and discussed shared GinScanEntry issues
in 2014: https://www.postgresql.org/message-id/52F373CC.4050800%40vmware.com
No heap novelty claim is made. This prototype is independent over fixed B,
not composed with C11 or the bitmap-offset candidate.

Three fresh matched full builds, 239 core and posting-list tests each, the
normal/UBSan valid-stream oracle and real-AM/SQL r2 qualification passed.
The explicit array_ops probe observed actual entry deduplication, NULL
extra_data, pointer sharing and per-role heap thresholds using each role's
actual private headers. Tsquery multiqual alone is not counted as sharing.
Unexecuted runtime r1 and preliminary r2 manifests remain marked separately.

The fixed screen completed 576 raw / 432 retained / 144 warm observations in
two CPU/clone placements with exact B/T prefix and ELF identity. Independent
recount verified 258 absolute groups, 258 pair groups and 1548 direct pairs.
Full plan/actual-row/loop/recheck shapes matched, retained I/O counters were
zero, and all six screen clusters stopped. No repeat or source tuning followed.

* `evidence/screen-report-r1/RESULTS.md` includes every actual-AM and SQL case.
* Its TSV files retain all absolute CPU/wall/executor spreads and all pairs.
* `evidence/screen-evidence-r1/ot-r1/` contains raw full plans and exact bindings.
* `source/` preserves diff, format-patch, snapshot and published source commit
  03dff8bfa5075e5838c7fbffc712d0b79d03f13d provenance.
* `REPRODUCE.md` and `replay/` provide exact revisions, setup, fresh builds,
  normal/UBSan and actual-AM/SQL gates, and standalone repeat commands.
* `email-draft-UNSENT.txt` is an English draft, not a sent email.

Root independently replayed the complete recount and all four derived tables.
MANIFEST.json freezes the reviewed packet; ROOT-REVIEW.json records checks. Its portable
frontdoor has not been executed on a second Linux machine. This is bounded
serial synthetic evidence, without concurrency/general merge qualification.
