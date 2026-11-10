# GIN bitmap offset upper-bound experiment

The fixed screen is mixed and does not establish a general SQL improvement.
Full-prefix executor time was 1.62% / 1.61% slower than fixed B in the two
cohorts. Prefix rare3 was 1.89% / 6.53% slower; low-memory prefix was 1.46% /
2.09% faster. Actual-AM prefix rare0 CPU improved by 0.98% / 1.24%, while
full-prefix AM CPU changed by only -0.15% / -0.06%. These are medians of six
direct pairs per cohort, not ratios of independent medians.

All controls remain visible: OR executor +1.59% / +3.45%, Seq +8.44% / +3.24%,
and exact B/T Seq drift +2.47% / +1.21%. Small changes cannot be treated as
source-causal proof. No source tuning, case removal or repeat followed this
screen. This candidate is not selected as a general SQL optimization here.

The one-file prototype is independent over fixed B. It preserves the existing
last-offset page skip and adds short skip-0/1 handling before galloping and
upper-bound search through uint16 matchBitmap offsets. It changes neither
posting-list ItemPointer paths nor lossy/fuzzy contracts. This is not claimed
as a new search algorithm. Heikki Linnakangas's earlier GIN scan discussion
provides broader context: https://www.postgresql.org/message-id/52F373CC.4050800%40vmware.com

Three fresh matched full builds (B/Bitmap release and Bitmap assert), 239 core
tests and posting-list checks each, normal/UBSan valid-offset oracle, finite
ordinary/prefix/lossy SQL qualification and both zero-retained smokes/screens
passed. The screen has 576 raw / 432 retained / 144 warm observations, two
CPU/clone placements and exact B/T identity. Independent recount verified 240
absolute groups, 240 pair groups and 1440 direct pairs; all plan/row/loop/recheck
shapes matched and retained I/O counters were zero. Six screen clusters stopped.

* `evidence/screen-report-r1/RESULTS.md` presents every SQL/actual-AM case.
* Its three TSV files retain all absolute CPU/wall/executor spreads and pairs.
* `evidence/screen-evidence-r1/bt-r1/` retains raw full plans and exact bindings.
* `source/` contains the independent diff, format-patch, snapshots and published
  commit cc5c47d525e01a7eb6af7b6d6fed66fcbde5d7f9 provenance.
* `REPRODUCE.md` and `replay/` contain exact revisions, setup, build, finite gates
  and commands. A local exact-B72 Git repository replaces an omitted archive.
* `email-draft-UNSENT.txt` is an English draft, not a sent email.

The separate skip-0/1/2/4/large extracted-fragment micro is being qualified in
its own namespace; no micro result is claimed in this version of the packet.
Its later evidence, if approved, must remain separate from full-AM/SQL timings.
C11 and OR heap are independent alternatives and are not composed here.
This is finite synthetic serial evidence, not a concurrency or merge proof.
Root independently replayed the complete recount and all four derived tables.
MANIFEST.json freezes the reviewed packet; ROOT-REVIEW.json records checks.
