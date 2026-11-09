# Source review before new BOX measurements

C and D each start from exact V2r2 `ebd53d036faaece35a56139abe24641496affbe6`.
The parent commit's complete gistget.c bytes were checked against the retained
reference snapshot before creating either commit. Both patch forms independently
reconstruct the declared candidate snapshots. C touches three files; D one.

## C: lifetime and cache scope

The cached value contains only necessary caller conditions. Its expression
short-circuits before touching keyData[0] when the scan does not have exactly
one key. It is recomputed at the end of every gistrescan, after new key data,
support functions and order-by data have been copied. A NULL key argument means
reuse of existing keys, so recomputation still uses the current scan state.
beginscan's palloc0 leaves a conservative false value until the first rescan.

The cached bool does not retain query pointers, page data, type metadata or a
normalization result. The unchanged helper still rejects the wrong attribute,
strategy, subtype, type/opclass, compression/decompression or support function.
It obtains the current argument every time. Necessary false positives cannot
bypass those checks; a false negative only misses an optimization. This does
not justify intentionally stale initialization or weaken normal rescan duties.

The extra bool is expected to fit existing padding, but only the new installed
header layout test may establish actual size/offset equality. All header users
are rebuilt from clean directories, including each assert candidate.

## D: continuation and side effects

The helper returns the next unprocessed offset instead of a bool. Ineligible
queries return FirstOffsetNumber without touching output. Completed pages
return maxoff+1. After eight *valid non-NULL BOX* ordinary keytests all pass,
the helper returns at the top of the next iteration. Every earlier match has
already gone through the ordinary bitmap/pageData/queue/reconstruction path.
The generic loop starts at the returned offset and preserves that output.
Neither sample keytests nor accepted sample tuples are repeated.

Killed tuples skipped by the old path do not consume sample slots. NULL and
legacy-invalid tuples do not count toward admission; they retain ordinary
handling. If fewer than eight valid tuples exist, the old helper simply
finishes the page. If any sampled valid BOX fails, the previous batching path
continues. Declining batching is a performance heuristic; it makes no claim
that later entries will also match. All later entries still receive keytests.

The generic loop body and the source suffix after it are byte-identical to
the reference; its initial offset changes. Buffer/predicate locking,
split/rightlink/NSN processing and page-state initialization precede this
dispatch and remain unchanged. OffsetNumberNext(maxoff) is within its type's
range for a valid BLCKSZ-sized GiST page. No persisted state or WAL changes.

## Performance questions to keep open

C still pays full helper eligibility on eligible pages. D adds a branch on
the sampled path, and its resumed generic loop may change code generation.
Neither source argument proves a speedup or explains old small-query losses.
Keep direct comparisons to R and B/exact B twin, sparse as well as dense and
offpath controls, and the two fresh process cohorts separate.

The new actual-AM microbenchmark includes rescan and bitmap costs. Its
process-CPU clock excludes relation opening and array setup, while SQL and
whole-command CPU have wider boundaries. The old extracted native model is
historical context only. No new algorithm or exhaustive novelty is claimed.
