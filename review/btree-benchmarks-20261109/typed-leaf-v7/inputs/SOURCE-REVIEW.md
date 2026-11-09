# Source review — prospective leaf-only V7

## Motivation and bounded change

The previous V6 fresh exact1 paired ratios are 1.1784/1.1946 versus baseline
and 1.0625/1.2143 versus the exact-ELF twin. Absolute B/V6 medians are
43.5/50 us and 40.5/48.5 us. Hot 25000-probe ratios are .9093/.9042 versus
baseline and .8974/.9011 versus twin. These are completed old V6 cohorts,
reported in `typed/final-prep/{REVIEW,BENCHMARKS}.md`, not new measurements.
“Fresh” means a new backend after settings/metadata commands, warm shared
buffers; it excludes connection latency and does not mean cold disk.

The retained B72 object dump and V6 object dump have identical initial
`_bt_first` frame size (0xac8) and six saved registers. Their paths, SHA256s and
exact prologue excerpts are recorded in `existing-asm-observations.json` and
`*-existing-first-prologue.txt`. V6 eligibility changes its caller CFG and
register allocation, but frame growth is not supported by these dumps.
Neither observation establishes the cause of SQL timings. Existing software
profiles warmed exact1 to about 9 us and cannot resolve the fresh difference.

One structural candidate is implemented. It restores the complete B72 tree
descent, makes the leaf call choose typed/generic inside a noinline dispatcher,
and eliminates the typed descent clone and bool live across descent. This is
an experimental change of scope, not a proved cold-regression repair. We do
not add padding, a width/history/admission threshold, a cache, or a tuning grid.

## Exact source locations (candidate snapshot)

All paths below are relative to `source/`:

- `src/backend/access/nbtree/nbtsearch.c:53`: both V6 comparison helpers copied
  verbatim. The helper still uses `index_getattr`, not a raw tuple offset.
- `nbtsearch.c:129`: `_bt_binsrch_read` is explicitly `pg_noinline`. Its only
  production caller is the initial leaf positioning in `_bt_first`.
- `nbtsearch.c:132`: assert-build leaf precondition. The ordinary B72 search
  returns a read-locked, pinned leaf or InvalidBuffer; invalid/empty handling
  and serializable retry precede the call.
- `nbtsearch.c:135`: full eligibility expression, normalized only by replacing
  `inskey.` with `key->`, is literally equal to V6's expression. It is evaluated
  after manufacture of every insertion-key field.
- `nbtsearch.c:1613` and `:1636`: original generic descent/retry, with no typed
  scan flag. Empty tree returns before the new leaf helper.
- `nbtsearch.c:1647`: the sole altered line of the B72 `_bt_first` body.

The complete source outside the three includes, the two copied helpers, the
new dispatcher and this single call substitution is byte-identical to B72.
This stronger source identity covers generic `_bt_search`, `_bt_binsrch`,
write descent, lock movement, page deletion, and serializable retry; it does
not establish linked assembly or performance identity.

## Eligibility and semantics retained

One search key, attno1, one TOTAL index attribute (so INCLUDE is excluded),
ASC/non-NULL argument, heapkeyspace, no search TID, INT8OID descriptor,
F_BTINT8CMP and exactly `btint8cmp` function address are all required. A custom
opclass legitimately using that builtin comparator can qualify. A new custom
comparator OID, wrapper, DESC, domain, multicolumn/INCLUDE and cross-type
comparator remain generic. Replacing a builtin function definition is not a
valid fallback oracle because fmgr may resolve its builtin fast path.

The comparison helpers retain signed relational comparison (no overflowing
subtraction), NULL/tuple-shape fallback to `_bt_compare`, nextkey/backward
bounds, empty/high-key-only page return and same-page generic assertion.
V7 invokes them only for leaves; their old internal safeguards remain intact
rather than being rewritten in this source probe. Generic descent handles
all internal equality, minus infinity, truncated pivot and heap-TID semantics.
Posting tuples remain supported under the original leaf equality contract.

No page pointer, key datum, descriptor-derived value or result survives its
existing call/pin/lock lifetime. Rescan manufactures and checks a new key; no
eligibility is retained. No MemoryContext, relation invalidation, WAL/recovery,
local/shared buffer, or reference-count contract is added. TEMP, UNLOGGED,
recovery and catalog calls remain allowed under the same structural guards.

## Remaining risks and evidence boundary

V7 gives up typed internal comparison. Hot/random/absent SQL can lose its old
benefit. Every ineligible first-leaf position now has an extra outlined
entry/guard path, so text/int4/control queries may worsen. The compiler may
still move registers or change unrelated linked addresses. Keeping `_bt_first`
source almost unchanged is not an assembly-size or cold-latency proof.

`verify-source.py` passes 18 source-only checks: pinned identities, copied
helper bytes, exact guards, restoration to B72, one callsite, both independent
patch replays and whitespace. No parser/compiler or live PostgreSQL has run.
The next useful gate is normal full-TU codegen, followed by the correctness
and matched SQL protocol. Stop if it is incorrect; retain any slow result.
