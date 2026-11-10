# K3 GIN dispatcher observer: actual finite counts

Dense reaches the intended fallback at 64 consecutive cache misses. Rare,
full, OR and prefix keep the cache in the captured workloads. All 18 untimed
reports passed; no new latency was measured. The observer adds work and changes
code layout, so its counts do not identify the cause of earlier K3 regressions.

Per dense key: 66,667 dispatcher calls, zero hits, 64 misses, one switch, then
66,603 direct native calls with zero equal-adjacent vectors after disable.
Per OR key: 200,001 calls, 199,600 hits, 401 cumulative misses, maximum consecutive
misses two and no switch. Per original prefix key: 201 calls, 102 hits, 99 misses,
maximum consecutive misses three and no switch. Rare/full/inline/absent and the
Seq control are retained in [FINDINGS-r1.md](FINDINGS-r1.md), including all totals,
run histograms and limitations in the raw data and independent audit.

The SQL reports contain 10 dense keys, 100 rare keys, 5 full keys, 5 OR keys,
0 Seq keys and 100 prefix keys. The 12 actual-AM reports separately cover six
queries with one and three real index_rescan/getbitmap iterations. Three-rescan
reports have fresh generations with exactly repeated per-key observations.
There are 18 ordered row comparisons: 17 GIN predicates and one ID-only control
reference; the Seq control has no GIN condition or key.

## Actual execution and scope

A fresh, separate normal-release full backend on VM84 passed unmodified 239 core
tests and posting-list tests before runtime interpretation. The unchanged finite
oracles then passed 40 ordered SQL cases, 7 prepared cases, 12 write-lifecycle
comparisons, 11 mixed-vector native cases (183,972 checks), 11 budget-boundary
cases (12,936 calls, 90 transitions), and 11 generic callback forwarding cases.
The observer stayed disabled in this gate. Independent fixed-B and Seq results
supply the expected values; expected files were not resnapshotted from DIAG.

All 18 captures passed independent recount: 244 key generations, 4,574,271
dispatches, 3,627,299 hits, 14,530 misses, 14 switches and 932,442 direct calls.
The shared-load VM was used for counts only. All three runtime cluster lifetimes
stopped cleanly. Root final read-only proof r2 reverified the source, installation,
907 headers, seed, frozen inputs, four actual normal object/ASM pairs and known
PIDs/sockets. There are no timing samples, concurrent-writer proof, new assertion
build, second-host replay or new threshold/policy changes in this packet.

The earlier root final-live helper r1 failed on an unrelated /proc/exe permission
check after its substantive checks. Its failure and the narrowed read-only r2
are retained. Two local post-run auditor draft failures are also retained as
packaging/auditor errata; the actual executed gate, captures and source stayed
unchanged. The ordinary gate and both independent recounts passed.

## Source identity

The sequential build dependency chain is:

1. Raw B72 `72b9498df9a369e747f8d96efb5a6cd33c2451e2`, all 7,726 source hashes.
2. Identical fixed B `8a8c475037bfde101da23cc9b0364c9c020eca93` prerequisite.
3. Exact K3 `ec32d586cf3bb6cfa76eb672db70160b436ce47c`, fixed 64 consecutive misses.
4. Observer overlay, canonical commit `b267e8808ad9d9c3574eb89d047761704266a757`.

The sole new source path is `src/backend/access/gin/ginlogic-probe.inc`; full
inventories are 7,726 / 7,726 / 7,727 files. The observer does not change K3's
threshold, callback arguments, results or dispatch assignments. Actual normal
ASM retains the miss64 direct-helper switch and hit reset. The backend exports
`gin_k3_diag_begin`, `gin_k3_diag_end` and `gin_k3_diag_report`.

Canonical observer commit creation happened after the input plan was frozen.
Historical `instrumented_commit:null` / `LOCAL_NOT_PUSHED` receipts remain intact;
content hashes prove the mapping, and the separate remote-verification receipt
records the subsequent source push. This mapping is not a claim that the build
checked out that later commit. The observer format-patch is relative to K3;
`inputs/source/steps/` contains the complete pinned dependency chain from B72.
These are diagnostic dependencies, not a new performance patch series.

This follows the existing K1/K3 research prototypes. Related historical GIN scan
work is [Heikki's 2014 discussion](https://www.postgresql.org/message-id/52F373CC.4050800%40vmware.com),
which is general context rather than a claim that it proposes this memo policy.
The concrete contribution here is bounded real-dispatch observation, not a new
cache algorithm or a novelty claim.

## Repeat and independently review

[REPRODUCE.md](REPRODUCE.md) gives Linux dependencies, exact revisions, flags,
setup, commands and metric definitions. `portable-replay-r1.py` accepts an existing
local B72 Git repository, so no baseline archive or Git history is distributed.
It directly invokes the unchanged builder, qualification and capture controllers
in a fresh short namespace. Historical `inputs/run.py` is retained as executed
provenance and has the original fixed namespace; the portable frontdoor bypasses
that wrapper. No old prefix, source tree or PGDATA is reused.

**The new portable frontdoor was checked locally with AST/help and all frozen
input byte checks only. It has not been executed as a fresh Linux replay.**
Actual execution is the original frozen build/qualification/capture chain in the
evidence directory. This distinction also applies to the independent peer's
frontdoor review. No mail was sent; the English draft is UNSENT.

`inputs/` preserves the exact executed text inputs and historical preparation
receipts, whose old NOT_EXECUTED labels describe preparation time. Actual PASS
receipts and raw captures are under `evidence/`. The packet excludes baseline
archives, PGDATA, binaries, objects, secrets and full runner logs. The root
reviewer owns final freeze and publication.
