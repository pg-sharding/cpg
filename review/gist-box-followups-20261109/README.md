# GiST BOX: rescan eligibility and dense-page continuation

The six full builds, finite SQL/AM qualification and accepted 2,400-observation
r2 campaign are complete. C is not selected; D has lower dense-case medians
against R, with broad ranges and inconsistent sparse differences. See
[RESULTS.md](RESULTS.md) and [all absolute results](results/ALL-RESULTS.md).

This is a new experiment above the unchanged V2r2 reference, against exact
B72 `72b9498df9a369e747f8d96efb5a6cd33c2451e2`. It is not latest master.

- **R**: historical V2r2, complete source SHA256
  `0af264c406f4d61c8ed91011fb7ba44f46b2be9748c0350eb03909f432ea4dea`.
- **C**: recompute necessary caller eligibility at every `gistrescan`, after
  consistent functions are copied into the keys. Do not cache the BOX pointer
  or weaken full helper eligibility. Change the page caller to read one bool.
- **D**: after eight valid BOX sample tuples all match, return the first
  unprocessed offset and continue the original generic page loop. Previously
  the specialized helper completed even dense pages. Already reported sample
  tuples are neither checked nor emitted twice.

C and D are independent alternatives, each above R. Their standalone diffs
apply directly to B72; the small `*-over-V2r2.diff` files are alternative patch
forms for review, not additional patches in a series. Batch/sample size 8 and
minimum page size 16 remain fixed. Buffer/predicate locks, NSN/rightlinks,
queue/bitmap/TID/recheck handling, tuple reconstruction and stored index format
are unchanged.

`prepare.py` generates exact pinned source snapshots and the source plan.
Standalone and incremental patch forms have exact replay checks. The six
full builds and all new runtime measurements are tracked separately; do not
interpret source generation as a performance result. See PROTOCOL.md.

VM84 was inspected but not used for builds or measurements because its load
was about 11 on eight guest CPUs. Its uploaded preparation directory contains
no running task. The new six-build campaign runs on VM158 with j2/nice10.

The first C microbenchmark compile preflight used the old three-argument
`index_beginscan_bitmap` interface. B72 takes instrumentation as its third
argument and key count fourth. The corrected new driver passes NULL and 1;
the first source/compile failure is preserved and produced no observations.
This correction changes diagnostic code only, not either production candidate.

The first matrix driver then stopped at its first warm observation because
Boolean metadata overwrote its native-result JSON. That attempt has one
preserved raw warm row, zero accepted rows and clean stops. r2 changes the
metadata name and output/data/socket namespaces, repeats smoke with fresh
copies, and retains the original production sources, cases and clock boundaries.
All failed evidence remains separate; it is not pooled into r2.

The new microbenchmark uses the actual GiST AM rescan and bitmap API, not the
historical extracted page-loop model. Its results must remain separate from
the older native/model numbers. SQL reuses the 16 actual V3-confirmation case
texts/settings; the older root queries.json has a stale two-key case and was
deliberately not used as the timed source. Original full-multiset verification
queries supply additional correctness coverage.

Prior context is the existing local BOX experiment and its bounded discussion
review. This is implementation work on scalar page-local conservative rejection,
not a new spatial algorithm or SIMD implementation. No new novelty search or
current CommitFest/adoption status claim is made.
