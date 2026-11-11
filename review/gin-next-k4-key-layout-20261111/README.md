# K4: compact scan-key layout over K3

This is a **source and compile-only experiment**, with no backend build,
SQL execution or performance result for K4. It is independent of the D2
decoder work. The one-field reorder must not be described as fixing the
previous K3 timing regression.

The original K3 source is `ec32d586cf3bb6cfa76eb672db70160b436ce47c`,
on historical fixedB `8a8c475037bfde101da23cc9b0364c9c020eca93`
(raw upstream B72 `72b9498df9a369e747f8d96efb5a6cd33c2451e2`).
`SOURCE-COMMIT-r1.json` identifies the new K4 commit and experimental branch.
`K4-compact-key-over-K3.patch` is git format-patch; the matching `.diff`
is incremental over K3. `K4-full-over-fixedB.diff` includes K3 and K4 and
is an **alternative application route**, not another patch to apply after them.
The cache eligibility, callback arguments and consecutive-miss threshold64
are unchanged.

## Actual verification

On VM158, GCC13.3.0 compiled three `-fsyntax-only -Werror` probes against
the actual historical B and K3 installed headers. It verified all907
headers and each postgres ELF before and after; neither installation
changed. K4 used a separate override copy of `access/gin_private.h`.
No probe was linked or executed. See `LAYOUT-RESULT-r1.json`,
`VERIFY-LAYOUT-r1.py` and `layout-assert.c` for commands and assertions.

| 64-bit ABI property, bytes | B | K3 | K4 |
|---|---:|---:|---:|
| `sizeof(GinScanKeyData)` |152|160|152|
| `nrequired` offset |24|24|24|
| `nadditional` offset |40|40|28|
| `additionalEntries` offset |32|32|32|
| `entryRes` offset |48|48|40|
| `triConsistentFn` offset |64|64|56|
| `strategy` offset |128|128|120|
| `triCache` offset |absent|152|144|

K4 fills the alignment gap following `nrequired`; it does **not** restore
the B field offsets. Size equality is not equality of allocation cost,
cache-line placement or machine code. For a one-key allocation, both sizes
may occupy the same allocator size class. Multi-key stride changes, field
offsets and resulting code generation are separate possible effects.

The normal B/K1/K3 `directTriConsistentFn` object disassembly was also
read. The instruction bodies and object-relative address0x30 are identical
(body SHA256 `25694193dab75ab0965355eb97d9a0b4537f3b339c31724ca38aef7f3f88f1d9`).
This says nothing by itself about final linked placement or callers and
does not identify the cause of the measured K3 regression. The observer
overlay was not used for this comparison.

## Repeating the compile-only check

The recorded command was:

```sh
python3 -B /home/reshke/allfuzz/gin-key-layout-20261111/VERIFY-LAYOUT-r1.py
```

That verifier deliberately expects the pinned, unchanged B/K3 build
receipt under `/home/reshke/allfuzz/gin-cache-k3-20261110/build-r1/` and a
fresh output namespace. It is the historical VM verification command,
not a claim of a fresh-host replay. The complete parent build and source
instructions are in the independently published
[K3 packet](https://github.com/pg-sharding/cpg/tree/experiments/gin-next-tsquery-cache-k3-results-b72-20261110/review/gin-next-tsquery-cache-k3-20261110).

For another Linux x86-64 build, compile `layout-assert.c` with that build's
`pg_config --cflags` and `--cppflags`, `-I` its actual server headers and
include directory, `-fsyntax-only -Werror`, and the `EXPECT_*` definitions
recorded verbatim in `LAYOUT-RESULT-r1.json`. For K4 put its isolated
header override first on the include path. A different ABI can legitimately
fail these explicitly64-bit assertions. No new dependencies were installed.

## Remaining experiment

Before performance conclusions, build B, K3 and K4 with identical flags
and shared source/build paths; run core tests and the existing K3 ordered
SQL, prepared-query, lifecycle and callback checks without changing expected
answers. Use one physical fixture with fresh copies, B/T exact twins,
balanced orders and the old dense/full/OR/rare/prefix/control workloads.
Include multi-key cases to exercise stride. Compare K4/K3 and K4/B,
retaining absolute times, spread and negatives. A separately compacted B
is a useful control for a generic layout benefit. No threshold tuning is
part of this hypothesis. These runs have **not** been performed.
