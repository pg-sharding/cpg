# GIN short-query batch of 100 actual SQL rescans

This packet records a separate completed work-unit experiment: **240 raw /
180 retained / 60 warm** commands, five cells, B/exact twin/Heap, two fresh
cohorts, all six role orders and all three pairs. All raw plans and every
negative/control observation remain. Both frozen analyzers and the independent
5130-value audit passed. BENCHMARKS-r1.md retains all 90 absolute/pair groups,
540 direct pairs and all three metric boundaries/dispersions.

The four original width 1/2/7/8 predicates each execute 100 correlated LATERAL
rescans in one command. Every one of 192 batch observations proved docs/index
**Actual Loops 100**, with original rows per loop. All 48 ID-control observations
proved one Index Only scan. Single-scan ordered Seq/GIN oracles and separately
multiplied scalar totals passed before acceptance. Scan 1 from materialization
or decorrelation would fail closed; no retry or SQL rewrite occurred.

**All reported milliseconds cover the whole command**, not a value divided
by 100. Rescan state, command planning and client overhead differ from 100
independent requests. N8 executor Heap/B was −5.31%/−4.51%, but N1 CPU remained
+0.02%/+0.12% and wall −0.97%/+1.79%. The cohort1 control exact twin moved +2.54%
executor. These observations do not explain or fix the earlier one-scan
negatives; no control normalization, source-causal or adoption claim is made.

Source remains fixed B 8a8c475037bfde101da23cc9b0364c9c020eca93 and unchanged
Heap 03dff8bfa5075e5838c7fbffc712d0b79d03f13d. B/T share one prefix/ELF.
No recompilation, source/threshold/cost/statistics tuning or composition occurs.
The actual root live proof verifies nine lifetimes stopped, no owned PIDs or
sockets, all three prefixes, 7726 source files, both seeds and inputs unchanged.

- `reference-inputs/` contains all 19 exact frozen runtime files. Its prospective
  README/draft/static labels are historical inputs, not current NOTRUN claims.
- `evidence/` retains all 36 selected text proofs, complete raw JSON plans,
  literals, 100-loop gate, one-scan ordered oracles, GUC/cost metadata, clone
  assignment/host/birth/shutdown receipts and transport hashes.
- `analysis/cohort0/` and `analysis/cohort1/` contain the original analyzer JSON;
  all audits and root live receipts are copied separately at packet root.
- `historical-parent/` is the unchanged original 266-file or-consistent/or Heap
  packet, with source patches, actual full builds/core/native/SQL qualification,
  complete setup and independent build/native replay. Neither newer natural nor
  forced-wide packets are recursively copied. `source.diff`/`source.patch`
  are two formats of the same existing alternative, not a new series.
- `PRIOR-NATURAL-EVIDENCE.json` pins original single-scan negative/control data
  by immutable results commit and hashes. `prior-natural-evidence/` contains
  only its manifest/findings/table/audit/rootproof metadata subset plus actual
  remote/S3 publication receipts; original raw data stays at the linked packet.
- `tools/` retains exact helper sources. Fresh SQL generation is static-only,
  not a new Linux execution; reference campaign paths/ELFs remain intentionally
  hard-bound. REPRODUCE.md gives the standalone fresh-build/SQL route.

The separate earlier natural packet is linked by exact commit:
https://github.com/pg-sharding/cpg/blob/51c2b347093c0b80cc6166de89b7783c2f906d27/review/gin-next-heap-natural-sql-20261111/FINDINGS.md
Its N8/short negatives, twin noise and Seq512 movement are preserved.

For local-only relocated reconstruction, choose a nonexistent output:

```sh
python3 -B tools/replay-analysis.py --packet /absolute/path/to/packet \
 --out-new /absolute/path/to/new-local-reanalysis
```

This checks selected inputs/evidence, reruns both frozen analyzers, byte-compares
all six JSON, independently recounts 5130 numbers and rerenders the full table.
No server, compiler, VM or network is invoked. Guest quiet-window/CPU pin labels
do not establish hardware isolation or a second-host result. Drafts are UNSENT. The top-level MANIFEST records root review and freeze;
Git/S3 publication receipts are kept outside this immutable packet.
