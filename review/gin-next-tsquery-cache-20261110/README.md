# K1 builtin-tsquery memo: completed shared-load diagnostic

The fixed B/T/K1 matrix passed: 1104 raw /828 retained /276 warm, two separate
fresh cohorts, every 23 SQL/actual-AM cells and all three pairs retained. The
independent local reconstruction checked 456 absolute groups, 456 pair groups,
2736 direct pairs and 25992 numerical fields. This is a shared-load diagnostic
on VM84, not a clean-host claim or a general adoption recommendation.

K1 improves the full-read/OR targets but has a material dense negative: actual-AM
inner CPU full −16.79%/−17.13%, OR −19.56%/−18.56%, dense +13.63%/+13.94% versus B.
SQL full/OR whole CPU improves about 7%, while dense whole CPU regresses
+13.08%/+7.43%. Unchanged Seq/twin and broad tiny client-wall ranges remain.
Read FINDINGS-K1-r1.md, then BENCHMARKS-K1-r1.md for every cell/metric/role and
all direct ranges. Cohorts and metric boundaries are separate; no trim, pooling,
twin normalization, significance or causal attribution. The English draft is
UNSENT, with positive and negative absolute values and prior-work credit.

Canonical root-authored K1 commit is 9e0d6e84c5bd538e58a534c99cb39ca669c567b7,
an independent alternative over fixed B 8a8c475037bfde101da23cc9b0364c9c020eca93,
with raw B72 72b9498df9a369e747f8d96efb5a6cd33c2451e2 and the identical supplied
opaque prerequisite. SOURCE-PUBLICATION-r1.json records the verified isolated
public branch. This is not a series/combination with S1, D1, C9, D2 or future K2.
No decoder benefit is claimed. Source/diff/patch and exact build snapshots are
provided; no new purity assumption is made for arbitrary operator classes.

The memo is restricted by exact known builtin support OIDs and function
addresses. It stores one at-most-eight-entry ternary vector/result per scan key,
including MAYBE, leaving native tri recheck unchanged. Query/map/strategy/
categories lifetime is that key. Generic/shim paths and hidden/nine-entry
fallback remain ordinary callbacks. Heikki's 2014 cache proposal is direct prior
art, explicitly credited; no novelty claim for the caching idea is made.

All three full B/K1/K1_assert builds passed unchanged core239/posting-list tests.
The installed-dispatch gate checked 40 ordinary ordered SQL cases, 7 prepared,
12 lifecycle, 11 native ternary cases and 11 VOLATILE generic fallback cases per
variant: 137979 valid vectors /551916 result-plus-recheck checks total. The
separate 69-row smoke and external root review preceded the fixed run. Complete
73-file collection hashes, all 225 ordered phase-oracle records, actual header/
compiler/ELF/source bindings and every warm/retained observation were audited.

The original frozen local analyzer had a stale n==10 assertion despite the
registered six retained rounds and stopped before output. It is preserved in
screen/, with its failure receipt. New analysis-tools-K1-r2/ changes only that
count guard to six; metrics/statistics/rows/pairing are unchanged. It passed both
cohorts and the independent implementation. No VM timing was retried or altered.
Use the corrected local analyzer for replay; never edit the historical freeze.

REPRODUCE.md gives exact local raw/analysis replay and a new Linux build/setup/
qualification/staged campaign. Frozen full-build instructions and SOURCE status
are historical staged inputs kept byte-identical; actual receipts establish the
completed checks. No old PGDATA/support .so or binary is required for a new run.
The bounded-exec front door has AST/help checks, not an independent Linux replay.

RAW-CHUNKS.json stores gzip chunks at whole-line boundaries, at most 4MiB raw
per chunk. restore-raw.py reconstructs a new exact 73-file collection and checks
all hashes. No PGDATA, binaries, object files, shared libraries or full runner/
server logs are included. Root final-live proof independently verifies all 13
cluster lifetimes/PIDs/sockets, 7726 source files, three prefixes/ELFs, both seeds
and frozen inputs/AM helper unchanged. Root independently restored and recounted the entire packet; ROOT-REVIEW.json
records the review and MANIFEST.json freezes all packet members.
