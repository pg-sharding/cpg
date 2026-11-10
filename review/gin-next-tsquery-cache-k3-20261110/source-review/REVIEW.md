# K3 ordinary lifetime, callback and bounded prior-art review

No concrete source correctness defect was found in the reviewed valid single-session
scope. This is a source/protocol review, not compiler, SQL, AM-rescan or timing PASS.
The root-owned four clean builds are in progress; their eventual evidence is separate.
K1's completed packet and K2's source-only alternative were not edited.

## Lifetime and callback contract

Reviewed exact K3 commit `ec32d586cf3bb6cfa76eb672db70160b436ce47c`, fixed-B parent,
and the five byte-bound Git source snapshots under `source-reference/`.

- `ginscan.c:267` switches to `so->keyCtx` before query extraction and key construction;
  `ginFillScanKey` initializes the dispatcher at line199. The memo's palloc0 therefore
  lives in keyCtx, not the per-callback temporary context. `ginFreeScanKeys:237` releases
  entry resources then resets keyCtx at258. `ginrescan:488` frees old keys; `ginendscan:501`
  frees them and destroys the contexts. `gingetbitmap` also frees/rebuilds scan keys at
  `ginget.c:2002`. The disabled pointer and counter do not survive that key lifetime.
- `tsginidx.c:94` extracts a query-local operand map into extra_data. Its native tri
  callback at267 reads only the query, ternary check vector and operand map; it does
  not mutate recheck or invoke arbitrary opclass callbacks. Query strategy, collation,
  map, values and categories are fixed for a key. The OID **and native address** guard
  at `ginlogic.c:163` is unchanged, so arbitrary opclasses and bool/tri shims do not
  inherit an unsupported purity assumption. Generic VOLATILE forwarding remains a
  required negative gate.
- At `ginlogic.c:123`, an exact-vector hit resets misses and returns the complete
  ternary result. A miss calls the native helper before incrementing; miss64 returns
  that result after selecting the same direct helper at146. Counter overflow is not
  reachable on this path because the wrapper is abandoned at64. Native tri leaves
  recheck unchanged, including MAYBE; the surrounding existing scan code still forces
  recheck for lossy/MAYBE cases (`ginget.c:1232`,1280). No entry state, tuple position,
  locks, pins, frequency order or output bitmap behavior is changed by K3.
- Hidden entries can be appended after init. The total-entry bound is checked before
  memcmp/copy. Hidden9 stays on the existing wrapper/direct bound-fallback path; it
  does not increment the budget or switch pointers. No fixed-size memo overrun is
  introduced. Per-key memo ownership also survives the existing key-array reorder:
  the pointer is copied with its owning GinScanKey, not shared with another key.

## Concrete performance and validation limits

The threshold counts **dispatcher misses**, not output tuples. Startup required-entry
ternary probes (`ginget.c:600`) and lossy/exact probes also contribute. A scan can have
many cumulative misses separated by hits and remain cached; a single run of64 misses
permanently discards all later reuse until the key is rebuilt. This does not establish
that OR retains its K1 gain: aggregate repeat counts do not prove maximum miss-run
length. The new counter reset/store and miss bookkeeping may cost on short/hot paths;
scans shorter than64 misses still pay the wrapper overhead. The small per-key memo
allocation remains, with a new counter field; exact structure size requires the real
compiler ABI. Hidden9 and unsupported opclasses receive no new budget benefit.

The separate `k3-native-boundary-r1/` helper uses the installed initializer/dispatcher
and never reads the opaque memo. Its73/130/192/193 phase lengths ×2 recheck sentinels
produce1176 checked calls per query, with12 initializations and2 context resets.
Nine eligible queries ×2 K3 variants ×10 switches give180 expected transitions over
44 invocations/51744 calls. The single-term literal FALSE/TRUE/MAYBE totals are
394/400/382. A independently reconstructed these expectations and reviewed the source.

The helper's vectors are the three **uniform** vectors, so the preserved exhaustive
native oracle is still required for mixed vectors. Its native context reset/rebuild
is not an `index_rescan` execution; actual SQL/AM rescan evidence remains separate.
It observes a stable pointer change and exact results, not the name/address of the
static direct helper or a dynamic callback-invocation counter. The production source
assignment and single call site establish those latter properties. Source review and
native testing complement each other; neither is a performance result.

## Direct prior art and context

Read-only archive transactions used statement_timeout30s and explicit LIMITs. We first
re-read all6 known-topic30796 messages and attachment metadata (zero attachments).
The direct caching/truth-table proposal is explicit in
[Heikki, 2014-02-06](https://www.postgresql.org/message-id/52F373CC.4050800%40vmware.com), with
[Korotkov's reply](https://www.postgresql.org/message-id/CAPpHfdv%3D8TrpsO%3Dk%2BKrS62nSrUR6c7ofHvrZR69bmm5-XKGmHg%40mail.gmail.com) preferring caching and warning that few combinations
may be used. These are direct idea overlap; the reply's expectations are not measurements.

The related performance thread29701 predates that summary:
[Heikki, 2013](https://www.postgresql.org/message-id/51C4ACC5.2090707%40vmware.com) discusses precomputing a consistent truth table for small
term counts; [Korotkov's reply](https://www.postgresql.org/message-id/CAPpHfduJ-X9WKR9h-vyTrNEVNR37ZDx05qOLkA3ys3j-14uKXA%40mail.gmail.com) explains how rare terms can make those
combinations change per TID. [Heikki, January2014](https://www.postgresql.org/message-id/52E2AF14.9020306%40vmware.com) again names caching
expensive consistent results as a use for the ternary abstraction. This is direct cache
prior art plus relevant no-reuse/cost context, not proof of K3's specific miss rule.

The first narrow subject search used a substring GIN and yielded unrelated words such
as changing/plugin; those rows were not treated as relevant prior art. A word-boundary
correction recovered the known performance discussions. A final adaptive/consecutive/
miss-rate query timed out at30s and was preserved; it was replaced by reads restricted
to the already found performance thread29701. Seven named consistent/ternary attachment
metadata records were read there, with no attachment bodies fetched or code executed.
Their names alone do not establish an adaptive cache implementation. No adaptive or
consecutive-64 rule is established by the selected messages, and this bounded,
partly timed-out search makes **no absence or novelty claim**. No final upstream status
was inferred, and no new CommitFest or Git history status claim is made.

`PRIOR-ART-SELECTED.json` binds exact message IDs, encoded public links and body hashes;
`archive-*.json` preserve SQL, stdout, stderr and success/timeout evidence. The initial
sandbox-only SSH failure is preserved as r1; the explicitly reviewed read-only access
succeeded as r2. No archive writes, builds, tests, config changes or server restart were
performed; no VM84 benchmark or concurrent actor was launched.
