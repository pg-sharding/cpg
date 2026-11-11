# D3 decoder: selective gains and remaining regressions

D3 reduces D2's delta3/4 and alternating-delta overhead while retaining the dense128 gain, but it is not a general upgrade over D2. Dense128 remains about 10.5% faster than B; delta2 still regresses, and long-first/dense-later gives back D2's late-batching benefit. First-singleton/growth and several small batches become slower than D2. Whole SQL is mixed. See [RESULTS.md](RESULTS.md) for exact cohort-specific values, absolute times, ranges and all negative controls.

The actual accepted run passed: 3136 raw commands, 2688 retained and 448 warm, following a separate 112-command smoke with zero accepted samples. Independent recount reconstructed all 87,360 numeric fields; peer and canonical analyses are byte-identical. All 28 cases, three metrics, six role pairs, 672 absolute groups, 1008 pair groups and 12,096 direct round pairs remain in the packet without pooling, filtering or twin normalization.

## Revisions and alternatives

| Label | Commit | Scope |
|---|---|---|
| Raw B72 | `72b9498df9a369e747f8d96efb5a6cd33c2451e2` | Authentic public source, 7726 files |
| B | `8a8c475037bfde101da23cc9b0364c9c020eca93` | Identical shared fixed prerequisite in every tree |
| D2 | `a85a9242f455b12c93528f3ace33eb69b6cd1008` | Earlier decoder alternative over B |
| D3r1 | `da951d2777e7b021966e5c9ade770bd434242e15` | Preserved codegen-only negative; no full backend timing |
| D3r2 | `1ce29c18ceb41882deced3ebe680ee75ba2c29b0` | Current candidate, alternative over B |


The D3 source branches were pushed and remotely verified in `pg-sharding/cpg`: [D3r1 codegen-only branch](https://github.com/pg-sharding/cpg/tree/experiments/gin-next-decoder-segment-dispatch-v3-20261111), [D3r2 current branch](https://github.com/pg-sharding/cpg/tree/experiments/gin-next-decoder-segment-inline-v3-20261111). `SOURCE-PUSH-K4-D3-r1.json` is the exact global verification receipt; its separate K4 ref is not a D3 result. The source commits identify the code and do not themselves assert timing PASS.

Standalone D2 and D3 patches are alternatives, not a patch series. Incremental D3/D2 and r2/r1 diffs are review aids. Do not apply all standalone patches together. T uses the exact B backend and native module with a separate fresh data copy.

D3r1 split the loops but GCC outlined `decode_varbyte` and enlarged its local frame to 56 bytes. The one-line r2 change uses B72's existing `pg_always_inline` macro. Actual full-build machine bytes match the reviewed r2 normal translation unit: no helper calls, a 24-byte local frame and the same six saved registers. Both revisions and the negative r1 outcome remain visible.

## Actual qualification and codegen

Four fresh B/D2/D3/D3_assert full backend builds each passed the original 239 core and posting tests without changing expected files. The finite ordinary gate passed 188 ordered/prepared SQL and 48 lifecycle comparisons; 84 decoder cases/54,144 item checks; 768 valid boundary cases/1536 decode calls/33,408 item checks. Source inventories have 7726 files and installed-header inventories 907 files per build. Only ginpostinglist.o changes among release backend objects; assertion flags differ, so assert/release object equality is not applicable.

Actual release ASM has no outlined decode_varbyte helper calls and the same 24-byte local frame/six saved registers as B and D2. D3 is 1241 bytes, compared with D2 844 and B 589. D3r1's helper-outlining/56-byte-frame negative remains codegen-only and was not timed as a full backend. No latency cause is inferred from code size.

Auxiliary auditor draft errors and the portable wrapper's source-only cleanup revision are retained distinctly from actual runtime PASS. Original frozen input READMEs retain their prospective wording and exact hashes; this README and RESULTS describe the completed run.

## Data and replay

- [tables-r1/PRIMARY.md](tables-r1/PRIMARY.md) has every case in both cohorts with absolute primary CPU/executor times and ranges. [ALL-ABSOLUTE.md](tables-r1/ALL-ABSOLUTE.md) and [ALL-PAIRS.md](tables-r1/ALL-PAIRS.md) retain all three metrics, spreads and six role pairs; unchanged JSON and direct values are in analysis0-r1/ and analysis1-r1/.
- evidence-qualification-r1/ preserves the complete 346-file ordinary collection. evidence-full-r1/ preserves the complete 432-file full collection, including plain raw/literal JSONL, settings, semantic plans, backend bindings, smoke, monitor and final live proof. COLLECTION hashes bind every selected file.
- [REPRODUCE.md](REPRODUCE.md) gives exact revisions, flags/dependencies, fixture creation, build, qualification, native/SQL smoke and separately reviewed fixed-run commands. The fresh Linux frontdoor is static-validated only; actual historical runs used the recorded root controllers. Offline recorded-data replay is a separate local operation and cannot approve a new timing run.
- review-recorded-r1.py verifies frozen inputs and complete selected collections, regenerates both analyses and compares their three JSON files byte for byte with the bundled versions. It does not require a final freeze manifest and starts no database/compiler.

The root final live proof records 17 stopped owned lifetimes, controller PIDs gone and unchanged source, four prefixes, headers, modules, seeds and frozen inputs. The bounded 49-sample host monitor covered the campaign; endpoint/top20 sampling can miss short-lived/thread activity and does not prove frequency or steal-time stability. Two placements on one VM are not second-host replication, and this is not a disk-cold or general concurrency qualification.

D2 and D3 patches are independent alternatives over the identical fixed prerequisite. No stack with S1/C9/cache or unrelated production patch is measured. The packet excludes the baseline archive, Git history, PGDATA, binaries, object/shared-library files and full runner logs. Nothing was sent to the mailing list. Root independently executed the complete packaged offline replay and verified byte equality of all six analysis files and the 87,360-field recount. ROOT-PACKET-REVIEW-r1.json records the final checks; MANIFEST.json binds the frozen packet. Git/S3 delivery receipts are kept alongside the local packet after publication.
