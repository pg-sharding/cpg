# GIN performance experiments: results and continuation, 2026-11-10

All six source directions have completed their fixed SQL/actual-AM screens. The
combined S1/D1 screen covers two independent alternatives. Complete source,
English UNSENT drafts, raw observations, absolute spreads, direct pair arrays
and build/setup/replay commands are frozen and published. Nothing was mailed.

Baseline is historical B72 `72b9498df9a369e747f8d96efb5a6cd33c2451e2` with the
identical supplied prerequisite, fixedB `8a8c475037bfde101da23cc9b0364c9c020eca93`.
These are not current-master results or a patch series. Cohorts are separate;
negative percentages below mean faster. All controls and regressions remain.

## Completed follow-ups: K3 and wide-OR SQL

K3 completed a new four-role2576/2208/368 screen, with79040 independently
recounted numeric fields and17 stopped cluster lifetimes. It reduces dense
SQL executor time versus K1 by5.71% /5.63%, but remains2.62% /3.02% above B.
OR SQL improves4.25% /3.01%; full single-term SQL is mixed, and rare-single
K3/K1 regresses7.99% /5.10%. Exact-twin AM control drift is material.
[Complete K3 packet, patches and UNSENT draft](cache-k3-qualification-20261110/publication-r1/README.md)
is published in [cpg](https://github.com/pg-sharding/cpg/tree/experiments/gin-next-tsquery-cache-k3-results-b72-20261110/review/gin-next-tsquery-cache-k3-20261110),
with [verified S3 receipt](CACHE-K3-S3-RECEIPT-r1.json).

The unchanged required-entry heap then completed384/288/96 **ordinary SQL**
observations with8208 independently checked numerical fields and9 stopped
cluster lifetimes. Forced-GIN OR executor time improves about5.7–5.9% at
width8,16.6–17.4% at32,24.5–25.6% at128 and25.8–26.4% at512. The last case
falls from about1.12–1.13s to0.832s. Width1/2/7 negatives and unchanged Seq
cost increases remain, as does material cohort0 baseline-twin variation.
[All new SQL metrics and spreads](heap-wide-sql-followup-r1/BENCHMARKS-r1.md)
are separate from earlier actual-AM results. These queries force GIN and
return all ordinary200000 rows; this is not a natural-planner application
speedup claim. A selective wide-OR follow-up without forcing a plan is the
next separate question.

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
| Historical D2 / K2 / K3 source-only snapshot | [packet](https://github.com/pg-sharding/cpg/tree/a3a08f19bd1b69d31bc6032abcd3b51aae5e620c/review/gin-next-followup-sources-20261110/) | `gin-next-followup-sources-20261110-r1/` |
| Completed K3 comparison | [packet](https://github.com/pg-sharding/cpg/tree/22a67b44f85249585ecad00cf01aa3bbc9106188/review/gin-next-tsquery-cache-k3-20261110/) | `gin-next-tsquery-cache-k3-20261110-r1/` |
| New wide-OR heap SQL | [packet](https://github.com/pg-sharding/cpg/tree/e5ea51506a46de1b0ec71d3f4c857fcc59f343e5/review/gin-next-required-heap-wide-sql-20261110/) | `gin-next-required-heap-wide-sql-20261110-r1/` |
| Selective natural-plan heap SQL | [packet](https://github.com/pg-sharding/cpg/tree/51c2b347093c0b80cc6166de89b7783c2f906d27/review/gin-next-heap-natural-sql-20261111/) | `gin-next-heap-natural-sql-20261111-r1/` |
| Short100-rescan heap SQL | [packet](https://github.com/pg-sharding/cpg/tree/a095314f7b1e2e328446e0dcc139482e293c1e4f/review/gin-next-heap-short-batch-sql-20261111/) | `gin-next-heap-short-batch-sql-20261111-r1/` |
| K3 untimed dispatcher observer | [packet](https://github.com/pg-sharding/cpg/tree/0aefa33ffe82a37c7012f0a9cf255f8b9140a1c2/review/gin-next-k3-dispatch-diagnostic-20261111/) | `gin-next-k3-dispatch-diagnostic-20261111-r1/` |

Per-file and remote-ref receipts accompany this report. The original parent
object repository HEAD/worktree stayed unchanged. No main/release branch was
updated. VM51 was not used for compilation/testing; no foreign jobs were stopped.

## Next separate experiment

D2 and K2 remain source-only. K2 disables after64 cumulative misses and could
lose later OR reuse despite high hit rate. The new K3 results above are a
separate measured packet; older frozen source-only snapshots are unchanged.
Its64 consecutive-miss threshold was not retuned after measurements.

The [selective natural-plan SQL screen](heap-selective-natural-20261110/publication-r1/README.md)
now completed384/288/96 with8208 independently recounted numerical values and
all9 stopped lifetimes. GIN N32 executor Heap/B is−10.53/−10.30%, N128 is
−11.43/−11.46%; B/Heap medians are0.847/0.753ms and0.8195/0.727ms at32,
11.4115/10.096ms and11.359/10.0825ms at128. N7 regresses4.20/5.57%; N8 is
−5.50/+16.31%. N512 naturally selects Seq, so its−3.86/−3.97% difference is
not a heap-path gain. All negatives, exact twins and IndexOnly ID controls
are preserved; no general adoption or source-causal claim is made.

A new short-query100-rescan work-unit screen separately completed240/180/60
with5130-number recount and final9-stop/source/install/seed/input live proof.
Every measured short plan executes100 real docs/index loops. Whole-command
OR8 executor Heap/B is−5.31/−4.51%, B/Heap8.858/8.383ms and8.8305/8.411ms;
N7 is−4.14/−2.20%, unchanged one-scan IDcontrol−0.16/+0.05%. No division by100
or substitution for the original single-scan results is performed. The
standalone packet under heap-short-batch-20261111/publication-r1 is frozen;
its cpg ref and all S3 objects are verified.

The [untimed K3 dispatcher diagnostic](k3-dispatch-diagnostic-20261110/README-RUNTIME-r1.md)
compiled and passed core239/posting plus ordinary/native/budget/fallback
qualification. All18 actual reports and244 key generations were independently
recounted. Dense has0hits and switches after64 misses per key; full/rare/OR
retain high reuse; prefix max consecutive misses3; actual AM rescans create
fresh generations. No equal-adjacent vectors after disable were observed.
The observer makes no instrumented latency or old-ELF attribution claim.
Its source/counter packet is frozen with final root live verification;
publication receipts record the exact cpg ref and S3 verification.

## Previous discussion and contribution

[Heikki Linnakangas,2014](https://www.postgresql.org/message-id/52F373CC.4050800%40vmware.com)
already discusses logical TIDs, deferred consumption, heap stream selection
and consistent-result caching. No algorithmic novelty is claimed for these
ideas. Concrete implementations, narrowly checked callback contracts, shared
entry handling, valid-input oracles and reproducible positive/negative workload
evidence are the contribution of this experiment wave.
