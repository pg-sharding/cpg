# GIN measured follow-ups, 2026-11-10

These are separate alternatives on historical fixed B72, not current-master
measurements or a combined patch series. Nothing was mailed.

| Experiment | Actual outcome | Packet |
|---|---|---|
| K3 builtin-tsquery memo | Dense SQL executor improves5.71% /5.63% versus K1, but remains2.62% /3.02% above B. OR improves4.25% /3.01%; rare-single and prefix regressions remain. | [Verified cpg result](https://github.com/pg-sharding/cpg/tree/22a67b44f85249585ecad00cf01aa3bbc9106188/review/gin-next-tsquery-cache-k3-20261110/) |
| Required-entry heap, new SQL | Forced-GIN full-match OR32 improves16.6–17.4%; OR128–512 improves24.5–26.4%. Tiny cases and Seq negatives, plus twin drift, remain. | This complete packet; [cpg branch](https://github.com/pg-sharding/cpg/tree/experiments/gin-next-required-heap-wide-sql-results-b72-20261110/review/gin-next-required-heap-wide-sql-20261110/) |

Both screens passed, were independently reconstructed and replayed locally.
K3 has2576 raw /2208 retained; the new heap SQL has384 raw /288 retained.
All17 K3 and9 new heap cluster lifetimes stopped. All sources, installs and
seeds remained bound. Quiet launch windows do not establish hardware isolation;
all cohorts, metric boundaries, controls and negative results are preserved.

K3 S3 directory:
`s3://pgtrash/pgbugs-artifacts/gin-next-tsquery-cache-k3-20261110-r1/`.
New heap SQL directory:
`s3://pgtrash/pgbugs-artifacts/gin-next-required-heap-wide-sql-20261110-r1/`.
External per-file verification receipts establish completed uploads; this
packet's manifest itself makes no network-operation claim.

The [previous complete wave overview](https://github.com/pg-sharding/cpg/tree/ce76e0bd926f26800f6d3faed301b6534d6961e2/review/gin-next-wave-overview-20261110/)
retains all six initial directions and negatives. historical-parent/ here is
the unchanged earlier heap packet, with source/build/setup/native/AM replay.

followup-source-preparations/ contains two **unexecuted** next steps:
an instrumented K3 dispatcher diagnostic (18 planned untimed reports; no
compiler/runtime) and selective wide OR without forcing a natural plan
(integer oracle/protocol only; no SQL/EXPLAIN/benchmark). They are not new
performance results or production-source combinations. Heikki's2014 cache/
heap proposals are direct prior art, and no algorithmic novelty is claimed.
