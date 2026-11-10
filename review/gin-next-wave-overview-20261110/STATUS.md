# GIN performance continuation — 2026-11-10

The six source directions run in two workers. The experiments are independent
alternatives on fixed historical B72, not a patch series. Large C9/B gains
must not be attributed to a later small increment. Timings, correctness and
source-only preparation are separate statuses below.

| Direction | Current evidence | Remaining work |
|---|---|---|
| C11 key representation on C9 | Five clean builds, core239 and posting-list checks each; 25 SQL cases on five variants; bounded screen **2400 raw / 2000 retained / 400 warm**, independently recounted | No universal improvement over C10; full25 timing not promoted |
| Bitmap offset advancement | Three clean builds/core/posting tests; normal+UBSan oracle, **350600292 caller cases** and **268681332 helper cases** each; ordinary/prefix/lossy SQL passed; actual screen **576 raw / 432 retained**, independent recount passed | SQL/AM screen mixed or negative; separate fragment micro **720 raw / 540 retained**, large-skip gains and short-skip regressions with noisy twin controls |
| Early missing-entry rejection S1 | Six-variant correctness passed; completed shared-load screen, absent whole SQL CPU **−72.27% / −70.30%**, inline AM CPU **+22.25% / +24.22%** | Keep v1 negative; future deferred-opening design remains unimplemented |
| Four one-byte decoder batch D1 | Same completed screen; dense128 decoder inner CPU **−12.87% / −13.34%**, long delta2 **+38.60% / +41.31%** | D2 first-byte guard prepared as a source-only alternative; no measured fix yet |
| Wide required-entry heap | Three clean builds/core/posting tests, fragment oracles and real shared-array-entry SQL gate passed; actual screen **576 raw / 432 retained**, independent recount passed | AM width8/32/128/512 improves about12/23/27/25%; shared-entry SQL regresses about2–4%; retain both |
| Builtin tsquery consistent cache K1 | Three clean full builds/core/posting tests and ordinary/native/fallback gate passed; smoke69 and fixed **1104 raw / 828 retained** independently recounted | SQL full/OR CPU about7% faster; dense SQL CPU **+13.08% / +7.43%**, AM dense **+13.63% / +13.94%**. K3 consecutive-miss fallback is the next separate experiment |

These statuses are a live index, not a frozen result packet. Worker receipts
and reports carry exact source hashes, raw evidence and cleanup proofs.

## First measured outcome: C11

[Report and absolute/paired tables](c11-bitmap/screen-report-r2/RESULTS.md)
retain all 13 SQL and 7 actual-AM cases in two separate CPU/slot cohorts.
C11 versus C10 actual-AM full read is **+5.93% / +0.28%**, while SQL Seq
C11 versus B is **+1.27% / +5.27%**. Negative is faster in those tables.
There is no general C11 upgrade recommendation. All ten screen clusters
stopped cleanly; source, installed trees, seed and module were unchanged.

## Code and replay entry points

- [Verified cpg source branches](SOURCE-PUBLICATION-r1.json).
- [Frozen C11 result packet](c11-bitmap/publication-c11-r1/README.md),
  [verified cpg publication](C11-RESULTS-GIT-r1.json), [S3 receipt](C11-S3-RECEIPT-r1.json).
- [Frozen S1/D1 results and English UNSENT draft](startup-decoder/publication-shared84-r1/README.md),
  [verified cpg publication](STARTUP-DECODER-RESULTS-GIT-r1.json),
  [S3 receipt](STARTUP-DECODER-S3-RECEIPT-r1.json).
- [Frozen bitmap SQL/AM packet](c11-bitmap/bitmap/publication-r1/README.md),
  [separate fragment micro](c11-bitmap/bitmap/offset-micro-supplement-r2/README.md),
  [frozen required-entry heap packet](or-consistent/or/publication-r1/README.md).
- [Frozen builtin cache K1 packet](or-consistent/cache/publication-K1-r1/README.md):
  all target wins and material dense regressions, exact raw replay, standalone
  patches, fresh build/setup/SQL/AM commands and English UNSENT draft.
- [C11 packet](c11-bitmap/c11/REPRODUCE.md),
  [independent collected qualification recount](c11-bitmap/ROOT-REVIEW-QUALIFICATION-r1.json).
- [Bitmap source and checks](c11-bitmap/bitmap/README.md).
- [Wide heap source and invariant](or-consistent/or/README.md).
- S1/D1 [source and identity mapping](startup-decoder/SOURCE-IDENTITY-CORRECTION-r1.json):
  canonical root-authored format patches end in `-root.patch`; older identities
  remain only to explain frozen build receipts. Trees/code are identical.
- [Consistent callback contract and prior art](or-consistent/cache/CONTRACT-REVIEW.md).
- [Separate write/build controls](coverage/PROTOCOL.md) and
  [larger/restart-cache protocol](coverage/SCALE-PROTOCOL.md) all completed:
  **1264 raw / 1056 retained / 208 warm**, all **188 cluster lifetimes stopped**.
  [Collected evidence receipt](coverage/ROOT-COLLECTION-r1.json) binds 851 selected
  JSON/JSONL files; [independent results and replay](coverage/publication-r1/README.md)
  are frozen, with [verified S3 publication](COVERAGE-S3-RECEIPT-r1.json).

## Next separate regression work

D2 tests the first continuation bit before D1's four-byte batch checks and
remains source-only. K2's fixed64 cumulative-miss budget is also source-only;
it could lose later OR reuse even with a high overall hit rate. K3 instead
resets the miss counter on a hit and switches a scan key back to the direct
builtin callback after64 consecutive misses. New clean B/K1/K3/K3_assert
build/gate preparation is assigned to VM158 in a new namespace. No K3 compile,
qualification or timing result is claimed by this completed six-direction wave.

Heikki Linnakangas's [2014 discussion](https://www.postgresql.org/message-id/52F373CC.4050800%40vmware.com)
is direct conceptual prior art for heap selection and consistent caching.
No algorithmic novelty is claimed for those directions. A tsquery multiqual
alone does not prove shared GinScanEntry: its extractor supplies extra_data.
The wide-heap gate adds builtin array_ops multiquals with NULL extra_data.

VM158 timing jobs are serial and exclude our builds/profiles. VM84 has foreign
load; any screen there is labelled shared-load diagnostic. VM51 is used only
as a read-only archive. No foreign jobs are stopped or global caches dropped.
