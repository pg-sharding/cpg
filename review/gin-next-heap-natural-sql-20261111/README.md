# GIN selective OR with natural planner choices

This packet records the completed ordinary SQL follow-up: **384 raw / 288
retained / 96 warm**, two fresh cohorts, exact B/T/Heap roles, all six role
orders, all three pairs and all three metric boundaries. The eight frozen
cells and every warm/negative/control observation remain. FINDINGS.md and
BENCHMARKS-r1.md retain all absolute dispersions and direct pair ranges.

Natural GIN N32/N128 executor observations were about 10–11% lower for Heap/B
in both cohorts. N8 was mixed (−5.50%/+16.31%); N7 and short backend CPU had
negatives. The planner chose **Seq at N512**, where −3.86%/−3.97% Heap/B cannot
be attributed to required-entry heap execution. The ID control selected
**Index Only**, despite its historical seq_control label. Small-cell exact-twin
variation is material. No filtering, pooling, correction by controls, general
application/adoption claim or causal attribution is made.

Fixed B is 8a8c475037bfde101da23cc9b0364c9c020eca93; Heap source remains
03dff8bfa5075e5838c7fbffc712d0b79d03f13d. B/T use the exact same prefix/ELF.
No source change, recompilation, composition, threshold/cost/statistics tuning
or performance-dependent repeat occurred in this follow-up. Its raw results
are distinct from previous native-AM and common-superset forced-GIN SQL.

- `reference-inputs/`: all 19 exact frozen runtime files, including the original
  prospective README/draft/static labels. Those preparation labels are retained
  byte-for-byte as historical input evidence; actual results are under evidence,
  analysis and final findings. They are not current NOTRUN labels.
- `evidence/`: all 36 selected text files, raw/full plans, literal journals,
  ordered-oracle proof, timed settings, backend/cost context, clone assignment,
  runtime/freeze/host/shutdown receipts and remote hash collection receipt.
- `analysis/cohort0/` and `analysis/cohort1/`: original frozen-analyzer results;
  SCREEN-INDEPENDENT-AUDIT-r1.json and ROOT-SCREEN-RECOUNT-r1.json recount 8208
  numbers without importing the benchmark analyzer.
- `ROOT-FINAL-LIVE-r1.json`: actual nine lifetime shutdown/PID/socket proofs,
  all three installed trees, 7726 source files, two seeds and frozen inputs
  unchanged. Quiet guest-window labels do not establish hardware isolation.
- `historical-parent/`: the COMPLETE unchanged 266-file original Heap packet,
  with standalone source patches, actual build/core/native/SQL qualification,
  old results/negatives, exact setup and independent build/native replay.
  This is the original or-consistent/or parent, not a recursive copy of the
  newer forced-wide SQL packet. The current source.diff/source.patch are the
  same Heap alternative in two formats, not a new patch series.
- `tools/`: exact original helper/replay sources and local provenance manifests.
  The simple fresh-build SQL frontdoor was generated/static checked only;
  no second Linux performance replay is claimed.

REPRODUCE.md gives fresh source/build/qualification and plain SQL instructions,
with new-result provenance and cleanup. Reference runtime commands intentionally
retain original path/ELF bindings; do not weaken ORIGIN or relabel new results.
For an offline reconstruction of this packet, use a nonexistent local directory:

```sh
python3 -B tools/replay-analysis.py --packet /absolute/path/to/packet \
  --out-new /absolute/path/to/new-local-reanalysis
```

This reruns the relocated frozen analyzer, byte-compares all six analysis JSON,
recounts8208 numerical values independently and rerenders the complete table.
It does not start PostgreSQL, compile, access a VM or claim a new benchmark.

The proposed short-batch100 follow-up is a separate later work unit, unexecuted
as evidence in this packet. No batch timings are included or substituted for
these single-scan observations. Drafts remain UNSENT. The top-level MANIFEST records root review and freeze;
Git/S3 publication receipts are kept outside this immutable packet.
