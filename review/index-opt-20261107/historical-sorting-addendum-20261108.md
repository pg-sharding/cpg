# Historical sorting source addendum — 2026-11-08

This dated source publication preserves43 distinct complete experimental trees on `4848fd6752ad6b88c5a066442df35ba208dfcec5`, with16 exact aliases indexed rather than duplicated. The43 refs are additional source archives; they are not a merge recommendation, one series, or43 newly tested variants. All54 original patches and5 original-prerequisite compositions were replayed without code edits. Root independently checked all43 trees and source hashes (290 source checks).

The [exact source index](historical-sorting-source-index-20261108.json) gives commit/tree/parent/source SHA, original payload SHA, author, prerequisite and historical runtime-binding scope.33 distinct trees have scoped recorded-source evidence. The remaining10 are5 without a full recorded runtime-source match,3 third-party prerequisite states not separately measured here, and2 rejected helper-only variants. These classifications are not a fresh correctness audit. Original David Geier v11 authorship/dates are preserved in the original3-commit chain; our growth/sorting changes inherit it.

## Reading the results

The byte-identical [historical synthesis](HISTORICAL-RESULTS-20261108.md) and [62-source catalog](HISTORICAL-RESULTS-20261108-sources.json) describe recorded gains and counterexamples across the old and current work. This is a dated snapshot: IOS V11 phase0 was preliminary and phase1/final disposition pending when written. It is not updated implicitly by later source publication. Original review-relative links in that snapshot retain their workspace context; the artifact navigator below supplies the actual internal storage locations.

The [GIN comparison](gin-thread-comparison-20261108/GIN-THREAD-COMPARISON-20261108.md) is our analysis and bounded archive/source index, not copied upstream mail/patch bodies. Our old pg_trgm adaptive/bitmap/radix6/MSD tests directly extend Geier’s extraction/sorting work. Current G1 decoded posting-list upper-bound advancement and G2 private compressed-suffix demand decoding act at later scan stages. Galloping search and radix/MSD are established techniques; no global novelty proof or combined end-to-end benchmark is claimed. G2 baseline already skipped segment headers; the proposal delays unused suffix decoding. G1/G2 cannot be silently stacked as a ready series.

The strongest early integrated examples are large prefix unions, large GiST tsvector/intarray inputs and long SP-GiST text labels. Tuplesort/VACUUM offset experiments did not establish material integrated gains. Typed array regressions and failed sample/small-radix attempts remain published as negative source controls. Bare-master repeated trigrams regressed with bitmap/radix6; v11 gains belong to their own separate reference. Partial nplus results and extension/runtime provenance mismatches remain explicit. A measured helper speedup is never promoted to an unmeasured full SQL speedup.

## Drafts and complete replay artifacts

The links point into existing internal S3 artifact prefixes. Download the entire prefix for sibling scripts/input dependencies, then follow its BENCHMARK/METHOD document; a standalone script alone is not a complete replay. Example: `aws --endpoint-url=https://storage.yandexcloud.net s3 sync s3://pgtrash/pgbugs-artifacts/sort-experiments-20261028/ ./sort-experiments-20261028/` (no delete). Stored absolute times, min/median/max, raw measurements, setup/build flags and negative cases are in those independent reports. No new bucket verification is claimed here.

### sort-experiments-20261028

77 recorded SQL comparisons; original co-built controls are explicit. Repro smokes separate.

Drafts: [email-draft.txt](s3://pgtrash/pgbugs-artifacts/sort-experiments-20261028/email-draft.txt), [email-draft-spgist-text.txt](s3://pgtrash/pgbugs-artifacts/sort-experiments-20261028/email-draft-spgist-text.txt), [email-draft-word-typed.txt](s3://pgtrash/pgbugs-artifacts/sort-experiments-20261028/email-draft-word-typed.txt), [email-draft-gts-radix.txt](s3://pgtrash/pgbugs-artifacts/sort-experiments-20261028/email-draft-gts-radix.txt), [email-draft-fts-positions.txt](s3://pgtrash/pgbugs-artifacts/sort-experiments-20261028/email-draft-fts-positions.txt).
Repro: [BENCHMARK.md](s3://pgtrash/pgbugs-artifacts/sort-experiments-20261028/BENCHMARK.md), [repro-bench.py](s3://pgtrash/pgbugs-artifacts/sort-experiments-20261028/repro-bench.py), [repro-micro.py](s3://pgtrash/pgbugs-artifacts/sort-experiments-20261028/repro-micro.py), [repro-summarize-micro.py](s3://pgtrash/pgbugs-artifacts/sort-experiments-20261028/repro-summarize-micro.py).
Results: [BENCHMARK-RESULTS.md](s3://pgtrash/pgbugs-artifacts/sort-experiments-20261028/BENCHMARK-RESULTS.md), [sql-comparison.json](s3://pgtrash/pgbugs-artifacts/sort-experiments-20261028/sql-comparison.json).

### fts-followups-20261029

Original followup results, rejected typed-array/noinline/sample/small-radix retained.

Drafts: [email-draft.txt](s3://pgtrash/pgbugs-artifacts/fts-followups-20261029/email-draft.txt), [email-draft-gist-negative.txt](s3://pgtrash/pgbugs-artifacts/fts-followups-20261029/email-draft-gist-negative.txt).
Repro: [BENCHMARK.md](s3://pgtrash/pgbugs-artifacts/fts-followups-20261029/BENCHMARK.md).
Results: [BENCHMARK-RESULTS.md](s3://pgtrash/pgbugs-artifacts/fts-followups-20261029/BENCHMARK-RESULTS.md), [findings.md](s3://pgtrash/pgbugs-artifacts/fts-followups-20261029/findings.md).

### fts-gist-intarray-new-threads-20261029

Four UNSENT new-thread drafts; position alternatives are alternatives, parser/ranking attachments are a series; intarray code-only diff.

Drafts: [01-fts-positions/email-draft.txt](s3://pgtrash/pgbugs-artifacts/fts-gist-intarray-new-threads-20261029/01-fts-positions/email-draft.txt), [02-fts-parser-ranking/email-draft.txt](s3://pgtrash/pgbugs-artifacts/fts-gist-intarray-new-threads-20261029/02-fts-parser-ranking/email-draft.txt), [03-gist-tsvector/email-draft.txt](s3://pgtrash/pgbugs-artifacts/fts-gist-intarray-new-threads-20261029/03-gist-tsvector/email-draft.txt), [04-intarray/email-draft.txt](s3://pgtrash/pgbugs-artifacts/fts-gist-intarray-new-threads-20261029/04-intarray/email-draft.txt).
Repro: [bench/README.md](s3://pgtrash/pgbugs-artifacts/fts-gist-intarray-new-threads-20261029/bench/README.md), [01-fts-positions/BENCHMARK.md](s3://pgtrash/pgbugs-artifacts/fts-gist-intarray-new-threads-20261029/01-fts-positions/BENCHMARK.md), [02-fts-parser-ranking/BENCHMARK.md](s3://pgtrash/pgbugs-artifacts/fts-gist-intarray-new-threads-20261029/02-fts-parser-ranking/BENCHMARK.md), [03-gist-tsvector/BENCHMARK.md](s3://pgtrash/pgbugs-artifacts/fts-gist-intarray-new-threads-20261029/03-gist-tsvector/BENCHMARK.md), [04-intarray/BENCHMARK.md](s3://pgtrash/pgbugs-artifacts/fts-gist-intarray-new-threads-20261029/04-intarray/BENCHMARK.md).
Results: [README.md](s3://pgtrash/pgbugs-artifacts/fts-gist-intarray-new-threads-20261029/README.md), [03-gist-tsvector/RESULTS.md](s3://pgtrash/pgbugs-artifacts/fts-gist-intarray-new-threads-20261029/03-gist-tsvector/RESULTS.md), [04-intarray/RESULTS.md](s3://pgtrash/pgbugs-artifacts/fts-gist-intarray-new-threads-20261029/04-intarray/RESULTS.md).

### trgm-three-approaches-84-20261028

Original5repeat CREATE INDEX and micro; bare master and full v11 references separate. Smaller-radix/MSD negatives retained.

Drafts: [email-draft-v11-bitmap.txt](s3://pgtrash/pgbugs-artifacts/trgm-three-approaches-84-20261028/email-draft-v11-bitmap.txt).
Repro: [METHOD.txt](s3://pgtrash/pgbugs-artifacts/trgm-three-approaches-84-20261028/METHOD.txt), [build-variants.sh](s3://pgtrash/pgbugs-artifacts/trgm-three-approaches-84-20261028/build-variants.sh), [setup.sql](s3://pgtrash/pgbugs-artifacts/trgm-three-approaches-84-20261028/setup.sql), [run-index.sh](s3://pgtrash/pgbugs-artifacts/trgm-three-approaches-84-20261028/run-index.sh), [index-bench.py](s3://pgtrash/pgbugs-artifacts/trgm-three-approaches-84-20261028/index-bench.py), [micro/README.txt](s3://pgtrash/pgbugs-artifacts/trgm-three-approaches-84-20261028/micro/README.txt).
Results: [REPORT.txt](s3://pgtrash/pgbugs-artifacts/trgm-three-approaches-84-20261028/REPORT.txt), [index-summary.json](s3://pgtrash/pgbugs-artifacts/trgm-three-approaches-84-20261028/index-summary.json).

The n2/n5/n8 source states are preserved, while the nplus report is partial and its extension source matches do not establish a matching full-backend revision. The source-only intarray analogues survey has no production patch and is excluded. Full local source/provenance fields are in the exact source index; the [machine-readable navigator](historical-artifact-links-20261108.json) separates artifact locations from execution claims.

## Additional source refs

| Variant | Source ref | Historical evidence scope |
|---|---|---|
| sort28-0001-spgist-text-direct-label-map | [04d67b36aa0f](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-sort28-0001-spgist-text-direct-label-map) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| sort28-0002-spgist-box-select-median | [1a9b9448ad5e](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-sort28-0002-spgist-box-select-median) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| sort28-0003-spgist-kd-select-partition | [6c2c6e98073e](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-sort28-0003-spgist-kd-select-partition) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| sort28-0004-spgist-typed-page-offset-sort | [153bf4f00004](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-sort28-0004-spgist-typed-page-offset-sort) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| sort28-brin-merge | [42862406598d](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-sort28-brin-merge) | NO_FULL_RECORDED_RUNTIME_SOURCE_MATCH_DO_NOT_CLAIM_TESTED |
| sort28-intarray-radix | [888f1194f663](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-sort28-intarray-radix) | NO_FULL_RECORDED_RUNTIME_SOURCE_MATCH_DO_NOT_CLAIM_TESTED |
| sort28-prefix-bitmap | [c4df5d8ac429](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-sort28-prefix-bitmap) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| sort28-tspos-typed | [8469baefb211](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-sort28-tspos-typed) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| sort28-tsvector-hash-radix | [58777474ca1c](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-sort28-tsvector-hash-radix) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| sort28-tuplesort-bitmap | [c67287683bf0](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-sort28-tuplesort-bitmap) | NO_FULL_RECORDED_RUNTIME_SOURCE_MATCH_DO_NOT_CLAIM_TESTED |
| sort28-vacuum-bitmap | [0e69242df99e](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-sort28-vacuum-bitmap) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| sort28-vacuum-offset | [6da9ad0a031d](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-sort28-vacuum-offset) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| sort28-word-radix | [d03d93fff918](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-sort28-word-radix) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| sort28-word-typed | [39b30cc3b589](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-sort28-word-typed) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| fts29-array-lexemes-typed | [9c2ab84dc05e](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-fts29-array-lexemes-typed) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| fts29-array-noinline-followup | [4d92097e7d00](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-fts29-array-noinline-followup) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| fts29-gist-crc-sample-followup | [c60f16d0032c](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-fts29-gist-crc-sample-followup) | REJECTED_HELPER_ONLY_SOURCE_INPUT_NO_BACKEND_RUNTIME_CLAIM |
| fts29-gist-crc-small-radix-followup | [c9c21cc6b112](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-fts29-gist-crc-small-radix-followup) | REJECTED_HELPER_ONLY_SOURCE_INPUT_NO_BACKEND_RUNTIME_CLAIM |
| fts29-input-lexemes-typed | [f45aa9fb5927](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-fts29-input-lexemes-typed) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| fts29-prefix-bitmap-ordered-followup | [729ee83ccbe3](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-fts29-prefix-bitmap-ordered-followup) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| fts29-prefix-ordered-runs | [3ca90fee29ab](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-fts29-prefix-ordered-runs) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| fts29-rank-doc-typed | [c0a01a02bfcc](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-fts29-rank-doc-typed) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| fts29-rank-operands-typed | [baa5e552074b](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-fts29-rank-operands-typed) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| threads29-04-intarray-0001-use-radix-and-bounded-dictionary-sorting-in-intarray | [b1436db1fc68](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-threads29-04-intarray-0001-use-radix-and-bounded-dictionary-sorting-in-intarray) | RECORDED_MEASURED_SOURCE_EQUIVALENCE_AND_MODULE_INPUT_CHAIN_NO_NEW_TEST |
| intarray-smalln-20261030-experimental-intarray-union-n5 | [2f03db2d7d6a](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-intarray-smalln-20261030-experimental-intarray-union-n5) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| intarray-nplus-20261030-experimental-intarray-n2 | [66c9918be33b](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-intarray-nplus-20261030-experimental-intarray-n2) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| intarray-nplus-20261030-experimental-intarray-n8 | [b4c9bdb646d2](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-intarray-nplus-20261030-experimental-intarray-n8) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| trgm-v11-basis-v11-0001-use-branchless-comparisons-in-btint4cmp-and-btin | [59d6bfb5347f](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-trgm-v11-basis-v11-0001-use-branchless-comparisons-in-btint4cmp-and-btin) | THIRD_PARTY_PREREQUISITE_NOT_SEPARATELY_BENCHMARKED_HERE |
| trgm-v11-basis-v11-0002-use-radix-sort-to-extract-trigrams | [04b8aea695bc](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-trgm-v11-basis-v11-0002-use-radix-sort-to-extract-trigrams) | THIRD_PARTY_PREREQUISITE_NOT_SEPARATELY_BENCHMARKED_HERE |
| trgm-v11-basis-v11-0003-replace-gin-build-accumulator-rb-tree-with-a-has | [623a4b855210](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-trgm-v11-basis-v11-0003-replace-gin-build-accumulator-rb-tree-with-a-has) | THIRD_PARTY_PREREQUISITE_NOT_SEPARATELY_BENCHMARKED_HERE |
| trgm-gin-growth-0001-account-for-gin-hash-growth | [6d3f2cfb1f57](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-trgm-gin-growth-0001-account-for-gin-hash-growth) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| trgm-adaptive-0003-trgm-adaptive-sort | [bce74929f31b](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-trgm-adaptive-0003-trgm-adaptive-sort) | NO_FULL_RECORDED_RUNTIME_SOURCE_MATCH_DO_NOT_CLAIM_TESTED |
| trgm-patches-master-bitmap | [e008272eb710](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-trgm-patches-master-bitmap) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| trgm-patches-master-msd | [abba6d360fe9](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-trgm-patches-master-msd) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| trgm-patches-master-smallradix | [978f80159eae](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-trgm-patches-master-smallradix) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| trgm-patches-v11-bitmap | [d08dae7c0f66](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-trgm-patches-v11-bitmap) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| trgm-patches-v11-msd | [dfabe19f770a](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-trgm-patches-v11-msd) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| trgm-patches-v11-smallradix | [252bba7a3202](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-trgm-patches-v11-smallradix) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| combined-spgist-four-control | [6d27f0a3088b](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-combined-spgist-four-control) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| combined-integer-v2-control | [6663f31cd52f](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-combined-integer-v2-control) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| combined-brin-tuplesort-control | [8e7a27610c26](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-combined-brin-tuplesort-control) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| combined-fts-initial-five-control | [faf0cf46d250](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-combined-fts-initial-five-control) | RECORDED_SOURCE_HASH_MATCH_WITH_EXPLICIT_SCOPE_NOT_NEW_TEST |
| combined-fts-parser-ranking-thread | [a9d925b28693](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-sort-combined-fts-parser-ranking-thread) | NO_FULL_RECORDED_RUNTIME_SOURCE_MATCH_DO_NOT_CLAIM_TESTED |

No preexisting source branch, index file or archived publication manifest is changed by this metadata addendum. All original files of the previous experiment-index tree are preserved byte-for-byte. The only intended existing remote ref update is a fast-forward of the metadata experiment-index after review.
