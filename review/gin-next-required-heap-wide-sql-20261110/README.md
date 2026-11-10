# Required-entry heap: measured wide-OR SQL follow-up

The unchanged heap prototype improves observed SQL executor time about17% at
32 OR entries and24–26% at128–512 entries in two fresh cohorts. At512 entries,
baseline1.12–1.13s becomes0.832s. These are **forced-GIN, full-match synthetic
queries**. The result does not establish a speedup under the default planner.
Widths1/2/7 and unchanged Seq negatives, plus exact-twin variation, remain.

- `required-entry-heap.diff` and `.patch`: the same canonical source alternative,
  commit03dff8bfa5075e5838c7fbffc712d0b79d03f13d; no new production code here.
- `FINDINGS.md` and `BENCHMARKS-r1.md`: all eight cells, three metrics, three
  pairs, absolute times/spreads and negatives, plus analysis/ raw numeric arrays.
- `email-draft-results-UNSENT.txt`: English new-thread draft; nothing mailed.
- `REPRODUCE-SQL.md`: SQL reproduction, exact setup/build origins and numerical
  replay. New generated convenience SQL is separate from executed harness evidence.
- `reference-inputs/`: exact19 original reference-campaign files. Its receipt
  pins refer to the real held-build campaign; fresh build receipts differ.
- `evidence/`: all33 selected text files, including every warm/raw/literal row,
  ordered digests, full measured plans, runtimes, births/CPUs and cleanup.
- `historical-parent/`: complete unchanged earlier frozen packet, including
  source, clean-build/fixture/native/AM replay and earlier SQL/AM negatives.
  Its MANIFEST is preserved; those measurements are not the new SQL observations.

The new fixed screen passed384 raw /288 retained /96 warm, with48 ordered
Seq/GIN comparisons. Independent arithmetic and root replay checked8208
numeric fields:144 absolute groups,144 pair groups and864 direct pairs.
All9 new smoke/accepted cluster lifetimes stopped. Three held installed trees,
all7726 source files, two seeds and every frozen harness input were unchanged.
No new backend/module was compiled. The raw B72 base is historical
72b9498df9a369e747f8d96efb5a6cd33c2451e2; fixed B is
8a8c475037bfde101da23cc9b0364c9c020eca93. These are not current-master results.

VM158 had an own quiet window labelled FRESH_HOST_CLEAN_SCREEN; that does not
establish hardware isolation. All three role pairs are retained without pooling,
trimming, control normalization, significance or causal claims. Backend CPU,
client wall and SQL executor time are separate boundaries. A separate literal
command before each measured EXPLAIN adds warming. OR512 exact-twin T/B differs
+8.46% in cohort0; unchanged Seq Heap/B differs+7.40% /+5.03%. No cohort is dropped.
Retained reads/writes and minor/major faults were zero; runqueue14.46/11.19ms
per cohort is diagnostic. Heikki's2014 heap discussion is direct prior art;
there is no novelty claim for heap selection itself. The next separate question
is a selective OR workload without forcing the planner.

The unrelated completed K3 comparison is linked by the separate-K3/ publication
receipts. It is not composed with this heap source. Source-only future
diagnostics, if included, have their own status and are not runtime evidence.
