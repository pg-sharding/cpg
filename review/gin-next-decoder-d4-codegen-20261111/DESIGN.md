# D4: resume batching after a scalar delta

This is one small structural alternative to D3r2, prepared on 2026-11-11. It removes D3's permanent per-segment choice of a scalar loop. The caller consumes the first byte, uses its continuation bit to select scalar continuation decoding or a bounded four-item batch, and can return to batching at any later one-byte delta in the same segment. This is deliberately D2-shaped control flow. It is not evidence of fewer instructions or faster execution than D2.

The draft changes only `ginpostinglist.c` against D3r2 commit `1ce29c18ceb41882deced3ebe680ee75ba2c29b0`. Its source hash is `d01496315db5513bc64bb399f003f14be8eb9edf4d634173b1543d5285731113`; its diff hash is `af9db752019fb20bc68344f29531680b7e829372566a8e578169525a05daf79a`. Initial draft preparation created no commit/ref and executed no compiler or runtime. `SOURCE.json` preserves that historical source-only state. Root subsequently created canonical commit `d2866655e3b0932ce449fe8ecbf3db52404fe4f8` and completed isolated normal full-TU codegen; their receipts and `NORMAL-ASM-REVIEW.md` describe that later stage. D4 still has no full backend qualification or timing result.

## What the completed D3 screen motivates

The table reports paired median percentage changes, cohort 0 / cohort 1, with twelve retained rounds in each cohort. Positive means longer. These are selected observations from the completed D3 run, not D4 predictions. Native primary time includes allocation, decoded-item materialization and free. `OBSERVED-D3-RESULTS.json` preserves the selected absolute medians, min/max ranges and B/T controls as well as paired values; the complete screen remains in `../decoder-d3/analysis0-r1/` and `analysis1-r1/`.

| Existing cell | D3 / B | D3 / D2 |
|---|---:|---:|
| long first, then dense | +0.20 / −0.04% | +12.11 / +12.08% |
| first singleton, then growth | −1.79 / −2.17% | +8.39 / +8.71% |
| singleton segments | +2.38 / +2.51% | +8.49 / +2.38% |
| delta2 | +2.30 / +3.22% | −1.91 / −0.91% |
| delta3 | −0.20 / +0.12% | −6.83 / −6.76% |
| delta4 | +0.32 / +0.05% | −5.68 / −5.93% |
| dense128 | −10.45 / −10.65% | +0.19 / −0.08% |
| alternating long / one byte | +1.56 / +1.45% | −12.75 / −13.00% |
| skew1000 whole SQL batch | −2.05 / −1.47% | +0.43 / +0.69% |

The skew row is the complete command with 100 probes, not per-request latency. The D2 singleton result itself differs between cohorts (D2/B −5.75% / +0.08%); it does not support a stable 8.5% singleton recovery target. B/T, all negative cells and whole-command secondary metrics must stay visible in any later comparison.

D3 selects its batched loop only if the first four encoded bytes are complete one-byte deltas. Otherwise it uses scalar decoding for the entire segment. Therefore the declared long-first fixture cannot batch its later dense run in D3. In `first_singleton_grow`, ordinary dense TIDs cross block boundaries while 511-item segment starts move relative to those boundaries; some segments begin with a multibyte delta among their first encoded positions. This explains which source paths are eligible. It does not establish how much of any measured difference those paths caused.

The completed normal release ASM also limits the hypothesis. B, D2 and D3r2 all inline scalar decoding and have the same 24-byte local stack allocation plus six saved registers. Their decoder function sizes are 589, 844 and 1241 bytes. D3's extra static growth call site is a consequence of two source loops, not evidence of more executed allocations. Neither size nor source branch count establishes an instruction-cache, spill or latency cause.

## Minimal control-flow change

The original static `decode_varbyte()` has one calling function and two source call sites, one in each D3 loop body. The draft replaces that helper with `decode_varbyte_after_first(ptr, first)`, retains `pg_always_inline`, and has one direct call in one loop:

1. The existing capacity check/growth runs at the top of the loop.
2. The caller consumes byte 0. If its continuation bit is set, it immediately enters the unrolled byte-2-to-byte-7 helper.
3. For a one-byte value only, it checks that three input bytes and four output slots remain, then tests those three continuation bits. If all are short it emits four items; otherwise it emits the already consumed value singly.
4. The next loop iteration can try a batch again. No segment-wide scalar state, retry counter, learned threshold or backoff constant exists.

At source level the long path performs the normal first-byte continuation decision and enters scalar continuation decoding without executing the batch bounds or three-byte eligibility expression. The helper's initial value is `first & 0x7f`; the remaining shifts 7, 14, 21, 28, 35 and 42, final-byte assertion, and final pointer update preserve the existing unrolled decoding convention. This is a re-expression of a decision the compiler may already reuse in D2. No duplicate-load/test removal or miscompilation claim is made.

The decisive tradeoff is visible in alternating data: every short byte can now attempt a batch and reject the following long value, whereas D3 can remain scalar. D2 was about 16.4% / 16.8% longer than B on the declared alternating cell. D4 may retain that regression. Homogeneous long deltas may compile similarly to D2, so this draft does not demonstrate preservation of D3's delta3/delta4 improvement. If it merely restores D2 machine code or makes the tradeoff worse, reject it rather than add retries tuned to these cases.

## Pointer, capacity and representation review

`ptr < endptr` precedes the initial byte read. The helper is called only for a consumed continuation byte and receives a pointer to byte 2. Like the existing decoder it assumes a valid compressed posting list; this draft adds no malformed-input behavior or new format contract.

On the short path, left-to-right short-circuit checks require at least three remaining bytes before `ptr[0..2]` are read, and at least four free output entries before four writes. `ptr += 3` follows the four emissions because byte 0 was already consumed. A rejected batch emits just that first value and leaves the pointer at the next integer. The normal growth check guarantees room for that single emission. Batch capacity rejection does not grow early: later iterations reach the original doubling point. The outer segment traversal, first item, initial capacity, growth formula, allocation APIs, item conversion, count/null-count behavior, compression and on-disk layout are unchanged.

`PATCH-APPLICATION-REVIEW.json` proves that the diff applies to the exact D3r2 snapshot and reproduces the saved draft bytes in a temporary tree. Manual source review supports the bounds/order argument above. It is not compiled-C correctness, assertion coverage or AM qualification.

## Gate before any broader experiment

The normal full-translation-unit B/D2/D3r2/D4 object comparison has now passed with identical source/object paths, the actual GCC 13.3 release flags (`-O2 -g -fno-lto` included), and the same recorded 907 installed headers. `NORMAL-RELEASE-COMPILE-ARGV.json` supplies the exact command data; `COMPILE-ONLY.md` explains replay and its prerequisites. `NORMAL-ASM-REVIEW.md` records the actual inline continuation/batch flow, unchanged 24-byte local frame and 838-byte D4 decoder versus D2 844/D3r2 1241. Control bytes/relocations repeat exactly. D2 already reused byte 0, and D4 is not an established instruction optimization. Source rearrangement and compiler size/placement changes alone are insufficient reason to launch throughput work.

If that gate yields a convincing distinct candidate, a later separately authorized qualification would retain all existing valid-input checks: the 21 native fixtures; the 192 mixed-boundary cases (six patterns × eight sizes × two segment lengths × initial singleton on/off), each checked with count and null-count output; ordinary 40 SQL, seven prepared and twelve lifecycle cases; core239 and posting checks; and a separate assertion build. Compare exact decoded TIDs, order, counts and checksums with the generated independent fixtures. Keep the existing allocation/growth and 1-to-7-byte cases, segment tails and all three mixed timing definitions. No malformed-input or unrelated investigation is proposed.

A later timing design must preserve all 21 native plus seven whole-SQL cells, the existing data/loop counts and clock boundaries, and compare fixed B, its exact twin T, D2, D3r2 and D4. Five roles require a prospectively fixed balanced five-role schedule and fresh cohorts; the old four-role scheduler/counts cannot simply be relabeled. Record raw/retained/warm counts before running. Preserve per-round pairs, absolute medians and spread, exact-twin drift, negative outcomes, semantic plans/settings, and bounded host-load evidence. Keep native allocation/materialization/free CPU, whole-backend CPU/client wall, and complete SQL ExecutionTime separate. No threshold search, case dropping, post-outcome repeat or control normalization is justified by this draft.

This wave stops at the draft and isolated codegen review. It contains no D4 full build, qualification or performance result and makes no speed claim.
