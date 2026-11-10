# GIN performance experiments: results and continuation, 2026-11-10

All six source directions have completed their fixed SQL/actual-AM screens. The
combined S1/D1 screen covers two independent alternatives. Complete source,
English UNSENT drafts, raw observations, absolute spreads, direct pair arrays
and build/setup/replay commands are frozen and published. Nothing was mailed.

Baseline is historical B72 `72b9498df9a369e747f8d96efb5a6cd33c2451e2` with the
identical supplied prerequisite, fixedB `8a8c475037bfde101da23cc9b0364c9c020eca93`.
These are not current-master results or a patch series. Cohorts are separate;
negative percentages below mean faster. All controls and regressions remain.

| Direction | Observed outcome | Decision / limit |
|---|---|---|
| C11 logical TID representation | No universal increment over C10; AM full C11/C10 +5.93% /+0.28% | Large selective gains versusB mostly inherited from C9 |
| Bitmap uint16 offsets | Full-prefix SQL executor +1.62% /+1.61%; prefixrare3 +1.89% /+6.53% | No useful general SQL improvement in this screen |
| S1 missing-entry startup | Absent SQL CPU −72.27% /−70.30%, inline AM CPU +22.25% /+24.22% | Reject v1 as a general optimization; positive-path cost remains |
| D1 four-byte delta batch | Dense128 decoder CPU −12.87% /−13.34%, long delta2 +38.60% /+41.31% | D2 first-byte guard is a separate unmeasured hypothesis |
| Wide required-entry heap | AM width8 −11.98% /−11.67%; widths32–512 about23–28% faster | SQL sharing8/32 regresses about2–4%; no general SQL recommendation |
| K1 builtin ternary memo | Full/OR SQL CPU about7% faster; AM full about17%, OR about19% | Dense SQL CPU +13.08% /+7.43%, AM dense +13.63% /+13.94%; K3 follows |

S1/D1 and K1 ran on VM84 with foreign load near11–12 on eight guest CPUs and
are explicitly shared-load diagnostics. VM158 scan screens and the separate
offset micro have their own host/control receipts. The short offset micro is
noisy: large skips improve, small skips regress and exact twins move by up to
about25%. No small-difference causal or SQL claim is inferred from fragments.

## New workload coverage for existing C9/C11

All five extra campaigns passed: CREATE INDEX, INSERT SELECT, VACUUM, a
million-row fixture exceeding64MB shared buffers and a restart before every
query. Counts:1264raw/1056retained/208warm, all188 cluster lifetimes stopped.

For warm million-row `common & rare0`, executor medians were B3.9135/3.9305ms,
C9 1.127/1.164ms and C11 1.106/1.146ms. Paired C9/B is about−71%/−70%.
With empty shared buffers after each restart, B20.769/20.4865ms versus
C9 17.9935/17.8745ms gives about−14%/−14%. OS cache remains warm; server
startup is excluded. C11/C9 is mixed. Write/build CPU observations, durability
variation, Seq controls and all negative ranges are in the coverage packet.

## Published artifacts

Each link points to an exact cpg result commit. The directory contains patches,
English draft, full tables/raw and replay instructions. S3 prefixes are under
`s3://pgtrash/pgbugs-artifacts/`; synchronization used no delete and every
object was checked by size and MD5/ETag or full downloaded digest.

| Packet | cpg exact result | S3 directory |
|---|---|---|
| C11 | [packet](https://github.com/pg-sharding/cpg/tree/e128a208bfdd2a0ea44f9e224fe7553f1c7389f8/review/gin-next-c11-20261110/) | `gin-next-c11-20261110-r1/` |
| S1 / D1 | [packet](https://github.com/pg-sharding/cpg/tree/4478a0c2ba66b77b5ab17282634b6df3947868d8/review/gin-next-startup-decoder-20261110/) | `gin-next-startup-decoder-20261110-r1/` |
| Bitmap SQL/AM | [packet](https://github.com/pg-sharding/cpg/tree/927b089ac6c673feea0a3c1b3301c0a36dca730f/review/gin-next-bitmap-20261110/) | `gin-next-bitmap-20261110-r1/` |
| Required heap | [packet](https://github.com/pg-sharding/cpg/tree/a8edf34a6826e231db38d2767d864e424eb54b5b/review/gin-next-required-heap-20261110/) | `gin-next-required-heap-20261110-r1/` |
| Builtin cache K1 | [packet](https://github.com/pg-sharding/cpg/tree/e4813802396b6c13a1f239d3e8ca19f2d64366a3/review/gin-next-tsquery-cache-20261110/) | `gin-next-tsquery-cache-20261110-r1/` |
| Offset fragment supplement | [packet](https://github.com/pg-sharding/cpg/tree/d2010cf8994c82a9f05f3a4795061e1f91fc9df6/review/gin-next-offset-micro-20261110/) | `gin-next-offset-micro-20261110-r2/` |
| Write/scale/restart coverage | [packet](https://github.com/pg-sharding/cpg/tree/d45a67c586081439c4ab5e6f857ee9e1a975e43a/review/gin-next-coverage-20261110/) | `gin-next-coverage-20261110-r1/` |
| D2 / K2 / K3 source only | [packet](https://github.com/pg-sharding/cpg/tree/a3a08f19bd1b69d31bc6032abcd3b51aae5e620c/review/gin-next-followup-sources-20261110/) | `gin-next-followup-sources-20261110-r1/` |

Per-file and remote-ref receipts accompany this report. The original parent
object repository HEAD/worktree stayed unchanged. No main/release branch was
updated. VM51 was not used for compilation/testing; no foreign jobs were stopped.

## Next separate experiment

D2 and K2 remain source-only. K2 disables after64 cumulative misses and could
lose later OR reuse despite high hit rate. K3 instead resets on each memo hit
and switches the scan key to the original direct builtin helper after64
consecutive misses. Threshold64 is fixed before timing. B/K1/K3/K3_assert clean
build and ordinary/native/fallback qualification preparation is assigned to
VM158 in a new namespace; boundary tests cover63/64 misses and hit resets.
No K3 build, correctness or performance pass is claimed by these frozen results.

## Previous discussion and contribution

[Heikki Linnakangas,2014](https://www.postgresql.org/message-id/52F373CC.4050800%40vmware.com)
already discusses logical TIDs, deferred consumption, heap stream selection
and consistent-result caching. No algorithmic novelty is claimed for these
ideas. Concrete implementations, narrowly checked callback contracts, shared
entry handling, valid-input oracles and reproducible positive/negative workload
evidence are the contribution of this experiment wave.
