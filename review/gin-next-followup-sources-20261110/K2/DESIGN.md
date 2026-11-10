# K2: fixed cumulative miss budget, source only

K2 is not compiled, qualified or timed. It is a standalone alternative over
fixed B that inherits K1's exact builtin-only last-vector memo and unchanged
private-header pointer. The only new behavior is a fixed cumulative budget of
64 eligible vector misses per GinScanKey. This value was selected before any
K2 data, with no tuning. K1's completed dense negative and full/OR positives
remain immutable; K2 does not replace, relabel or imply a fix for those results.

The first empty fill and each later eligible vector mismatch count as one miss;
hits do not reset the count. On the 64th miss, the original direct native helper
has already computed the ordinary result. K2 returns it, marks the memo invalid
and changes this key's triConsistentFn to that same original direct helper.
Later calls skip memo lookup/comparison/copy entirely. The cache allocation
remains owned by the same key context and is cleaned normally; a new/rescanned
key receives the usual zeroed cache state. There is no global/adaptive counter.

The exact builtin support OID/native-address guard, bound of eight entries,
hidden-entry overflow path, generic/shim paths and query/strategy/categories/
extra_data lifetime rules are unchanged. Native tri returns the complete
FALSE/TRUE/MAYBE result and leaves recheck unchanged; the fallback receives the
same key/arguments as K1's miss path. The64th miss does not invoke the callback
twice. No data format, callback API, entry/frequency/pin state, lossy/recheck
semantics or posting-list allocation policy is changed. The intended semantic
equivalence still requires actual compiler/native/SQL qualification.

The goal is to amortize persistent no-reuse overhead, but there are new required
negatives. A cumulative cap also affects a mostly-repeating workload with
occasional changes: the previous untimed OR probe had 401 changes in 200001 calls,
so it can reach 64 despite a high repetition ratio. K2 may forfeit later OR hits;
that cost must remain visible, without increasing or fitting the threshold.
The extra per-memo counter/first-miss work and short scans also require controls.
No latency benefit, dense fix or general adoption is claimed from source.

Before any future timing, review actual-header production normal/assert codegen
and extend the valid native dispatch oracle around 63/64/65 misses, repeated hits
between misses (no reset), one/eight entries, hidden/nine-entry fallback and both
recheck sentinels. Verify the function pointer selects ordinary direct dispatch
after the budget and resets only with a new key, while every result equals the
native builtin. Then require full clean builds/core239/posting-list tests,
unchanged ordered SQL/literals, prepared/lifecycle and VOLATILE fallback gates.
Keep every existing 23 SQL/actual-AM cell and fixed source/metric/sample protocol
in a fresh attempt, with all no-reuse dense, OR/full, inline/rare/absent/NOT/
phrase/Seq negatives. No extra VM build or timing is part of this wave.

Heikki 2014 remains direct caching prior art; there is no novelty claim for
memoization or adaptive fallback in general. The source was written once in a
new snapshot with root <localhost> author/committer. An external Git index
created the standalone tree, leaving the original source object repository and
this clone's HEAD/worktree untouched. K2-over-K1-review.diff is for the minimal
review delta only; K2-over-fixed-B.diff / root.patch are an alternative to K1,
not a series. Any future approved port uses a real cherry-pick of the canonical
K2 commit. The supplied common prerequisite is identical and opaque.
