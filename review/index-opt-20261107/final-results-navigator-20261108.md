# Final measured-family navigator — 2026-11-08

This NEW dated addendum updates the statuses of eight independent PostgreSQL index experiments after both IOS V11 cohorts and final artifact review. It preserves every file of the earlier metadata index, including its dated historical report and source indexes. Pending labels in those earlier snapshots remain historical; this page supplies the later status. This is a navigator to recorded results, not a new benchmark campaign or a merge recommendation.

All eight standalone patches target upstream `72b9498df9a369e747f8d96efb5a6cd33c2451e2`. They are independent alternatives, **not a patch series to stack**. Older sorting work uses 4848fd/51d7bf baselines and is linked separately. Do not pool absolute times across families, revisions or machines. All English drafts remain UNSENT.

## Outcomes

| Family / current source | Disposition and retained counterexamples |
|---|---|
| [typed-v6](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/typed-v6) | V6 remains a bounded read-positioning RFC. Hot int8 gains coexist with cold, inactive and write costs; it is not a generally faster replacement. |
| [ios-v11](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/ios-v11) | Both V11 cohorts are complete. Large master-relative SQL improvements coexist with material V11/V6 losses. Keep V11 as a bounded measured RFC/reference, not an unconditional V6 upgrade. |
| [gin-advance-v3](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/gin-advance-v3) | V3 remains a sparse-conjunction RFC. Short-skip native and smaller SQL/OR costs remain; no unconditional merge recommendation. |
| [gin-lazy-v4](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/gin-lazy-v4) | V4 partly repairs native full-read cost. Selective SQL gains against baseline coexist with repeated selective losses versus V3 and absent/control/native negatives; no unconditional V3 upgrade. |
| [trgm-positions-v5](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/trgm-positions-v5) | V5 is REJECTED FOR MERGE. A native similarity-kernel benefit does not establish SQL gain; phase1 long-LIKE losses of 6.29/8.23/9.10% and absent-LIKE 10.09% remain. |
| [hash-rank-v2](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/hash-rank-v2) | V2 is a narrow uniform-query experiment. Uniform SQL benefits repeat, while skew/overflow, tiny-page and constant-key native costs and sequential-control movement remain. |
| [hash-buffer-v1](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/hash-buffer-v1) | Unchanged V1 is a narrow rescan RFC. Natural varying-residual plain32 and EXPLAIN gains repeat against both controls; ordinary Memoize runs only one real probe. Absence/tiny/native/TEMP/unlogged controls remain. |
| [gist-box-v3](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/gist-box-v3) | V3 is a NONSELECTED repair/upgrade attempt. Sparse SQL gains versus baseline/twin remain, but V3/V2r2 is approximately flat and a stable NULL repair is not established. V2r2 remains an experimental reference; neither is generally merge-ready. |

### IOS V11: completed measurements, bounded conclusion

V11 is the cache-natts implementation already published as ios-v11. Both cohorts, each with 19 SQL and 28 native cells, direct six-way elapsed/CPU comparisons, cold/first-use controls, negative cases and software profiles are preserved in the final bundle. Against the baseline, wide count8 time fell 15.81%/23.39%, and tail32 fell 51.23%/43.41% in the two cohorts. Those gains do not establish a V6 upgrade: in phase1 V11/V6 f32, tail32 and tail8 were 14.05%, 9.06% and 7.64% slower. Slot-only native 2-attribute/text8 penalties also remain. No matched V11/V10 causal comparison is claimed, and the earlier V9R2 unequal-history erratum is preserved. Read absolute medians/ranges and all direct pairs in the linked BENCHMARKS.md; do not reconstruct paired ratios by dividing independent medians.

The IOS primary code SHA is `6044af2c3d2571d4f502af884ab0c7e6cf936307b3604262ada4ed635f99d992`; final manifest SHA is `4e79cde3b3e0745361b733eaa7b45d9a7a5edf95c7037884c2160d1315a6dc46`. Root final review is ios/parent-final-review-v11.json in the aggregate navigation capsule.

## Complete artifacts, drafts and replay

Each link below is relative to its internal S3 prefix. Download the **whole prefix** to retain the portable setup, SQL fixture, micro sources and script dependencies; reading one Python file alone is not a complete replay. Each independent replay document states dependencies, exact build flags/revision, nondefault server GUCs, data/index creation, new-build/new-DSN commands and metric units. The result tables contain absolute timings and spread; raw data, historical controls, model/dispatch errata and negative cases are retained in those bundles.

### typed

Prefix: `s3://pgtrash/pgbugs-artifacts/btree-typed-final-20261107/`

Code: [typed-v6.diff](s3://pgtrash/pgbugs-artifacts/btree-typed-final-20261107/typed-v6.diff). English UNSENT draft: [email-draft-new-thread.txt](s3://pgtrash/pgbugs-artifacts/btree-typed-final-20261107/email-draft-new-thread.txt). Replay: [REPLAY.md](s3://pgtrash/pgbugs-artifacts/btree-typed-final-20261107/REPLAY.md). Results: [BENCHMARKS.md](s3://pgtrash/pgbugs-artifacts/btree-typed-final-20261107/BENCHMARKS.md).

Manifest: [artifact-manifest.json](s3://pgtrash/pgbugs-artifacts/btree-typed-final-20261107/artifact-manifest.json), SHA256 `e5ab359319bb339ce31d882d31f9aa31b32d1400448e0d06ee04be3cefe53afc`.

### ios

Prefix: `s3://pgtrash/pgbugs-artifacts/btree-ios-followup-20261107/`

Code: [code.diff](s3://pgtrash/pgbugs-artifacts/btree-ios-followup-20261107/code.diff). English UNSENT draft: [email-draft-new-thread.txt](s3://pgtrash/pgbugs-artifacts/btree-ios-followup-20261107/email-draft-new-thread.txt). Replay: [REPRODUCE.md](s3://pgtrash/pgbugs-artifacts/btree-ios-followup-20261107/REPRODUCE.md). Results: [BENCHMARKS.md](s3://pgtrash/pgbugs-artifacts/btree-ios-followup-20261107/BENCHMARKS.md).

Manifest: [artifact-manifest.json](s3://pgtrash/pgbugs-artifacts/btree-ios-followup-20261107/artifact-manifest.json), SHA256 `4e79cde3b3e0745361b733eaa7b45d9a7a5edf95c7037884c2160d1315a6dc46`.

### gin-advance

Prefix: `s3://pgtrash/pgbugs-artifacts/gin-advance-20261107/`

Code: [gin-advance/gin-advance-v3.diff](s3://pgtrash/pgbugs-artifacts/gin-advance-20261107/gin-advance/gin-advance-v3.diff). English UNSENT draft: [gin-advance/email-draft.txt](s3://pgtrash/pgbugs-artifacts/gin-advance-20261107/gin-advance/email-draft.txt). Replay: [gin-advance/REPRODUCE.md](s3://pgtrash/pgbugs-artifacts/gin-advance-20261107/gin-advance/REPRODUCE.md). Results: [gin-advance/BENCHMARKS.md](s3://pgtrash/pgbugs-artifacts/gin-advance-20261107/gin-advance/BENCHMARKS.md).

Manifest: [MANIFEST.json](s3://pgtrash/pgbugs-artifacts/gin-advance-20261107/MANIFEST.json), SHA256 `62b515f6b1c42ab2284ad30745bd90d556e7a7856892436fd5d5bcd010b2163b`.

### gin-lazy

Prefix: `s3://pgtrash/pgbugs-artifacts/gin-lazy-20261107/`

Code: [gin-lazy-v4.diff](s3://pgtrash/pgbugs-artifacts/gin-lazy-20261107/gin-lazy-v4.diff). English UNSENT draft: [email-draft-new-thread.txt](s3://pgtrash/pgbugs-artifacts/gin-lazy-20261107/email-draft-new-thread.txt). Replay: [REPLAY.md](s3://pgtrash/pgbugs-artifacts/gin-lazy-20261107/REPLAY.md). Results: [BENCHMARKS.md](s3://pgtrash/pgbugs-artifacts/gin-lazy-20261107/BENCHMARKS.md).

Manifest: [artifact-manifest.json](s3://pgtrash/pgbugs-artifacts/gin-lazy-20261107/artifact-manifest.json), SHA256 `f5569366b8dc0e7fa31dbc4737fa22568489f4304933292ebfb9d1ffca46aa7e`.

### trgm-positions

Prefix: `s3://pgtrash/pgbugs-artifacts/gist-trgm-positions-20261107/`

Code: [trgm-positions-v5.diff](s3://pgtrash/pgbugs-artifacts/gist-trgm-positions-20261107/trgm-positions-v5.diff). English UNSENT draft: [email-draft-v5.txt](s3://pgtrash/pgbugs-artifacts/gist-trgm-positions-20261107/email-draft-v5.txt). Replay: [REPRODUCE-V5.md](s3://pgtrash/pgbugs-artifacts/gist-trgm-positions-20261107/REPRODUCE-V5.md). Results: [CONFIRMATION-RESULTS.md](s3://pgtrash/pgbugs-artifacts/gist-trgm-positions-20261107/CONFIRMATION-RESULTS.md).

Manifest: [MANIFEST.json](s3://pgtrash/pgbugs-artifacts/gist-trgm-positions-20261107/MANIFEST.json), SHA256 `3df8c801093f8d014a3942438acf082eea1f35053c56c62b0134dba1b2613b47`.

### hash-rank

Prefix: `s3://pgtrash/pgbugs-artifacts/hash-rank-20261107/`

Code: [hash-rank-v2.diff](s3://pgtrash/pgbugs-artifacts/hash-rank-20261107/hash-rank-v2.diff). English UNSENT draft: [email-draft-new-thread.txt](s3://pgtrash/pgbugs-artifacts/hash-rank-20261107/email-draft-new-thread.txt). Replay: [CLEAN-REPRODUCE.md](s3://pgtrash/pgbugs-artifacts/hash-rank-20261107/CLEAN-REPRODUCE.md). Results: [BENCHMARKS.md](s3://pgtrash/pgbugs-artifacts/hash-rank-20261107/BENCHMARKS.md).

Manifest: [ARTIFACT-MANIFEST.json](s3://pgtrash/pgbugs-artifacts/hash-rank-20261107/ARTIFACT-MANIFEST.json), SHA256 `57bb732a4fe5179d06c927af1391b03a74d65bf2e12debc1f849c8d31e57df10`.

### hash-buffer

Prefix: `s3://pgtrash/pgbugs-artifacts/hash-buffer-20261107/`

Code: [hash-buffer-v1.diff](s3://pgtrash/pgbugs-artifacts/hash-buffer-20261107/hash-buffer-v1.diff). English UNSENT draft: [email-draft-new-thread.txt](s3://pgtrash/pgbugs-artifacts/hash-buffer-20261107/email-draft-new-thread.txt). Replay: [REPLAY.md](s3://pgtrash/pgbugs-artifacts/hash-buffer-20261107/REPLAY.md). Results: [BENCHMARKS.md](s3://pgtrash/pgbugs-artifacts/hash-buffer-20261107/BENCHMARKS.md).

Manifest: [artifact-manifest.json](s3://pgtrash/pgbugs-artifacts/hash-buffer-20261107/artifact-manifest.json), SHA256 `edccdc25c0d0c57458871b8ca937145b5f240aa8450391280eb60b6917d071ce`.

### gist-box-batch

Prefix: `s3://pgtrash/pgbugs-artifacts/gist-box-batch-20261107/`

Code: [gist-box-batch-v3.diff](s3://pgtrash/pgbugs-artifacts/gist-box-batch-20261107/gist-box-batch-v3.diff). English UNSENT draft: [email-draft-new-thread.txt](s3://pgtrash/pgbugs-artifacts/gist-box-batch-20261107/email-draft-new-thread.txt). Replay: [REPLAY.md](s3://pgtrash/pgbugs-artifacts/gist-box-batch-20261107/REPLAY.md). Results: [BENCHMARKS.md](s3://pgtrash/pgbugs-artifacts/gist-box-batch-20261107/BENCHMARKS.md).

Manifest: [artifact-manifest.json](s3://pgtrash/pgbugs-artifacts/gist-box-batch-20261107/artifact-manifest.json), SHA256 `9e6fb3e78cc9f5440fb6becab06adddcd492246357e73953004c251c13cfc431`.


Preferred IOS letter: [editorial/email-draft-v11-copyedited-UNSENT.txt](s3://pgtrash/pgbugs-artifacts/index-optimizations-aggregate-20261108/editorial/email-draft-v11-copyedited-UNSENT.txt), SHA256 `02926f3cf0a3d99b59442318f4b2d9c2b0903a8ab2d33c7c3dd793dc31cfb8ad`. This is a separately versioned wording copyedit with unchanged technical claims; the original frozen family draft remains available above.

Example download (use an installed working AWS CLI and existing internal credentials):

```sh
aws --endpoint-url=https://storage.yandexcloud.net s3 sync \
  s3://pgtrash/pgbugs-artifacts/btree-ios-followup-20261107/ ./ios-v11/
```

Follow ./ios-v11/REPRODUCE.md from a fresh source/build/output directory; do not edit an archived release freeze or substitute initdb defaults for the recorded server settings. New replay measurements must receive their own identities and must not be appended to the original cohorts.

## What the measurements mean

SQL EXPLAIN Execution Time, a plain SELECT batch wall time, whole-command backend CPU and native C-loop nanoseconds measure different scopes. Plain32 wall time includes protocol/parse/plan/client work; per-query time is batch wall divided by the fixed 32 verified calls. Boundary CPU/queue observations stay outside the hot plain loop. The H2 actual exported getter includes real tag/pin paths; its older extracted-body matrix is retained only with the helper-model erratum. H1 original static/inlined versus exported helper call costs are likewise explicitly separated. G2 native models do not become full-AM measurements.

Most families timed warm runtime reads; CREATE INDEX commonly created the fixture and is not claimed to become faster. Historical sorting CREATE INDEX work is a separate campaign. Exact-ELF twins and two CPU/slot/creation-order placements expose some variation but are not independent hardware replication. Same-live-PID software profiles do not supply PMU counters or prove a hardware cause. Outliers, negative controls, order/carryover diagnostics and twin movement are retained rather than subtracted from wins.

## Source archives and historical experiments

There are 92 published source-state refs: 31 current versions, 17 older B-tree alternatives, 43 distinct historical sorting trees and 1 IOS V12 probe. This is not 92 distinct algorithms, 92 measured successes or a sequence to merge. The [current 31 source index](source-publication-index.json), [older 17 addendum](legacy-addendum-20261108.md), and [historical 43 sorting source index](historical-sorting-source-index-20261108.json) remain unchanged. The [dated historical synthesis](HISTORICAL-RESULTS-20261108.md) and [GIN comparison](gin-thread-comparison-20261108/GIN-THREAD-COMPARISON-20261108.md) preserve their original source-backed scope.

The 43 sorting trees include five explicit original-prerequisite control/series combinations; 16 identical trees are aliases instead of duplicate refs. 33 have scoped recorded-source bindings; five lack a full recorded runtime-source match, three are third-party prerequisite states and two are rejected helper-only states. Co-built controls and intarray extension/runtime mismatches remain explicit. David Geier retains author/date/body for his original three v11 commits; our sorting/growth followups inherit that chain and claim only their delta. Old pg_trgm radix/adaptive/MSD is direct followup work to that thread; current G1 decoded-TID advancement and G2 private compressed-suffix decoding have different mechanisms. This bounded comparison is not a global novelty proof or a combined-patch test.

### IOS V12 is separately scoped, not a measured upgrade

[ios-v12](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/ios-v12) is commit `a07d55855d5a74b5ede9b53b26b1cf56b988b07d`, tree `37e14630ad68a69885f37c8a80f0656700eb57e9`, sole parent 72b949. Its standalone code SHA is `bb4197c32f7aa9a9543add9c25316575c3a5709b1e7a514dc7fcb8d9b2b901c2`. Seven source files change; eight source hashes include unchanged nbtsearch.c as a provenance control. It is independent of the archived43 sorting states.

The qualified exact built-in unowned virtual-slot identity hit fuses clear/copy/store while copying AM-owned raw arrays on every hit; heap, name/conversion, custom, materialized and miss fallbacks remain. Actual-header module and containing-TU ASM remove the indirect clear/external store/natts reload on that edge. Production text grows 634→883 bytes and prologue stack 40→56 bytes; these costs are retained. Later bounded release/assert builds and old 751812-oracle/640-contract checks passed in a recorded snapshot. The shipped snapshot stops before expanded slot ownership/mutation validation; later follow-up checks require separately dated evidence. No accepted V12 native/SQL timings exist. Source/ASM/build evidence is not merge acceptance or proof of an IOS regression repair.

Separate V12 source-publication record: v12-source-publication/public-record-v2/MANIFEST.json, SHA `c825ec1b39b55185002a5641986d4537c3c8e3495d22071c2bc18d00d0def0d0`, in the aggregate capsule. Sorting source-publication record: public-record-v2/MANIFEST.json, SHA `9f85c978ffccf928dcc93c0817d5b672e26d0b70ea9e6b19d731a6e0e5bafe9f`. Those metadata projections exclude local Git repositories, scratch indexes, binaries, PGDATA and full runner logs.

## Aggregate navigation capsule and publication verification

The new aggregate prefix is `s3://pgtrash/pgbugs-artifacts/index-optimizations-aggregate-20261108/`. It contains navigation, selected source/publication proof, own literature/prior-art analysis and family pointers; full raw benchmark/replay corpora remain in their independent prefixes above.

IOS publication verification completed at `2026-11-08T07:10:24.597398+00:00`: all 1,910 selected objects/164,751,353 bytes were verified by recorded size and MD5/ETag, without deletion. The aggregate carries [s3-receipts/s3-receipt-ios-v11.json](s3://pgtrash/pgbugs-artifacts/index-optimizations-aggregate-20261108/s3-receipts/s3-receipt-ios-v11.json), SHA256 `8d129e49a98258cdab1cbdc320979f4356b5b8f426b0b3c2e3a4adf9e238ae1c`. This describes the selected-object verification, not a future live bucket total.

Aggregate frozen selected manifest: [MANIFEST.json](s3://pgtrash/pgbugs-artifacts/index-optimizations-aggregate-20261108/MANIFEST.json), SHA256 `430d10908515e9499f9e97b54a3fae00fab099030b41f8a5cd35d69936ec3e24` (336 payload files; 6,782,670 bytes). Root final aggregate review and selected-object upload verification have completed; this is the final frozen navigation snapshot.

Aggregate selected-object publication verification completed at `2026-11-08T07:14:56.337604+00:00`: 338 selected objects/6851288 bytes. The actual receipt SHA256 is `876700881cf259207fc4d8300c81539674bc677f1fca27188ac40a034e596a9a`; root final aggregate review SHA256 is `411bd518ea087b1e9915edc4da64f45cdfed7f683ac9abe496958149e6b8d315`. These are recorded size/MD5/ETag and local review receipts, not a fresh exhaustive runtime correctness test or a promise of future live bucket totals. The aggregate is navigation; benchmark binaries, PGDATA and full runner logs are not publication payloads.

No existing experiment source ref or earlier metadata file is changed by this dated addendum. No mail is sent by this publication.
