# K3: fixed consecutive miss budget, source only

K3 is an independently applicable alternative over fixed B. It inherits K1's
builtin-only last-vector memo and adds a fixed threshold of 64 consecutive
eligible vector misses per GinScanKey. Every memo hit resets the miss counter
to zero. The first fill counts as a miss. The threshold was specified before
K3 compilation or performance observations and must not be tuned from results.
K1's completed measurements remain immutable. K2's cumulative-budget source
is preserved separately and has not been compiled or timed.

After the original native helper computes the result for miss 64, K3 invalidates
the memo and switches this key's triConsistentFn to the original direct helper.
That result is returned once; later calls skip memo lookup, comparison and copy.
A hit before miss 64 restarts the consecutive-miss budget. A new key receives
zeroed state through the existing initialization. There is no global counter.
The small per-key allocation remains in the normal key memory context.

The exact builtin support OID and native-address guard, eight-entry bound,
hidden-entry overflow fallback, arbitrary opclass and shim paths, query/map/
strategy/categories/extra_data lifetime and native tri recheck behavior are
unchanged. The complete FALSE/TRUE/MAYBE result is retained. No data format,
callback API, posting-list allocation, entry/frequency/pin state or lossy/recheck
semantics is changed. This is not a generic opclass purity assumption.

The motivation is K1's measured no-reuse dense regression. A consecutive budget
can remove sustained memo work there, while the earlier OR callback probe's
401 changes among 200001 calls does not by itself imply 64 consecutive misses.
K3 can still forfeit later hits after any sufficiently long no-reuse stretch.
Counter reset/store overhead, short scans and alternating phases are controls.
No dense fix, preserved OR gain or latency improvement is claimed from source.

## Required qualification before timing

Compile against actual production headers and install independent clean B,
K1, K3 and K3_assert backends. Keep the existing native ternary/generic fallback
oracle, all ordered SQL and prepared/lifecycle checks byte-identical. Add a
separate valid native budget oracle using installed ginInitConsistentFunction
and actual GinScanKey dispatch, without reinterpreting the opaque memo struct:

- Fresh key: 63 distinct successive vectors retain the initial memo function;
  miss 64 switches away; call 65 uses the same direct function pointer.
- A hit after 63 misses retains memo dispatch and resets the budget; a further
  63 consecutive misses still retain it, and the next miss switches it.
- More than 64 cumulative misses, each separated by a hit, do not disable memo.
- A fresh key restarts the budget after another key has disabled memo.
- Compare every return to the independent builtin callback and preserve both
  recheck sentinels, with one/eight entries and the existing hidden/nine-entry
  fallback cases. B and K1 retain their original dispatch behavior.

Only after these checks, the full build/core/posting-list tests and ordinary
SQL gates pass should a new finite screen retain all existing 23 SQL/actual-AM
cells, including full/OR, no-reuse dense, NOT, phrase, inline, rare, absent and
Seq controls. Root owns the clean-host lease and launch. This source packet
has no compiler, native, SQL, runtime or performance execution.

Heikki's 2014 discussion remains direct caching prior art; no novelty claim is
made for memoization or adaptive fallback generally. The source was written
once with root <localhost> author and committer. An external Git index created
the standalone commit over fixed B, leaving repository HEAD and worktree
unchanged. K3-over-K1-review.diff and K3-over-K2-review.diff are review deltas;
K3-over-fixed-B.diff / root.patch are standalone alternatives, not a series.
Approved ports use a real cherry-pick of the canonical commit. The common
prerequisite remains identical and opaque.
