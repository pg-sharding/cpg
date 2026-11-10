# Prospective selective wide-OR SQL follow-up

Status: local source/protocol preparation only. No server, build, EXPLAIN or timing was run. The completed common-superset forced-GIN campaign and its negatives remain unchanged. This note makes no new SQL performance claim.

The workload is fixed in `WORKLOAD.json` (SHA256 `ecbe56a9196c5d2192a798784d05acf0e927eb3e4651edaf779385aad49e4861`). It reuses the exact qualified Heap fixture and source alternatives: fixed B `8a8c475037bfde101da23cc9b0364c9c020eca93`, exact-ELF twin T, and Heap `03dff8bfa5075e5838c7fbffc712d0b79d03f13d`. These historical ELF/source pins describe the proposed reference runtime, not a newly verified live binding. A fresh build would need its own reviewed receipts.

Seven literal predicates use only `group0 | ... | group(N-1)` at N=1/2/7/8/32/128/512. There is no `common` term. Widths 1/2/7 retain the below-threshold negatives; widths 8/32/128/512 test the existing threshold without tuning it. The eighth cell retains the unchanged ID-range query as a no-GIN control, now with natural planner settings too.

The setup inserts IDs 1..200000, each with exactly one `group(g % 4096)` lexeme, plus NULL/empty special rows -1/-2. Since 200000 = 48*4096 + 3392, residue 0 has 48 rows and residues 1..3392 have 49. For these widths, the expected set is `1 <= g <= 200000 AND g % 4096 < N`, with count `49*N-1` and sum `4816896*N + 49*N*(N-1)/2`. JSON contains independently generated ascending-ID SHA256/byte counts and scalars. This arithmetic was checked locally by integer enumeration, not against candidate query output.

| Width | Expected rows | Expected sum(id) |
|---:|---:|---:|
| 1 | 48 | 4816896 |
| 2 | 97 | 9633841 |
| 7 | 342 | 33719301 |
| 8 | 391 | 38536540 |
| 32 | 1567 | 154164976 |
| 128 | 6271 | 616960960 |
| 512 | 25087 | 2472660736 |

Each group contributes only 48 or 49 rows. Posting storage, callback work and heap-versus-linear overhead may differ materially from the common-superset campaign; actual plans and valid qualification must establish the exercised path. Prior wide-OR wins do not predict a win here.

All measured scan-type settings are enabled (`enable_seqscan`, `enable_bitmapscan`, `enable_indexscan`, `enable_indexonlyscan`, `enable_tidscan`). No planner costs, statistics or work_mem are tuned after observing a plan. The default/natural plan is unknown until actual EXPLAIN. GIN is not an acceptance condition: retain Seq choices and any role/cohort plan differences, report actual nodes/index/loops/recheck/lossy fields, and do not replace or drop cases. This isolates a different workload from the prior forced-GIN common-superset query; comparisons across waves are descriptive only.

Before samples, use separate untimed forced-Seq and forced-GIN ordered-ID queries for the seven group predicates and compare both to the independent frozen rowset/digest and scalar for all roles. The ID-range control uses its independent Seq reference, without requiring a nonexistent GIN condition. Force settings apply only to these oracle commands and must be restored before natural-plan checks/samples. Reject incorrect rows, not an unexpected natural path. Preserve complete natural EXPLAIN plans, literal answers, and the unchanged historical source/build qualification. Require a fresh smoke with 24 commands, zero accepted samples, all three clusters stopped, and explicit root review before an accepted run.

The prospective matrix is B/T/Heap, two fresh cohorts, two warm and six retained rounds per cell: 384 raw / 288 retained / 96 warm. Retained orders are all six role permutations in JSON, each role twice per position and every directed adjacency twice. Warm orders are the first two. Hash/fsync three smoke and six accepted numeric copies before assignments; verify accepted copies unused after smoke. Reverse accepted role birth and case order in cohort 1. Preserve exact B/T executable identity and the prior fixed CPU/host/cleanup protocol under a new namespace/ports selected before launch. No own build, profiler or other benchmark overlaps.

Separate full SQL EXPLAIN Execution Time, whole-backend CPU and client wall; the independent literal answer immediately before EXPLAIN remains explicit extra warming. Persist every raw observation before validation. Retain all warm/retained data, all three same-round pairs, all eight cells and three metrics, absolute min/median/max/mean/sample SD/MAD, pair ranges/direct values, runqueue/fault/read/write diagnostics and all controls. Do not pool cohorts, trim, normalize by twins, select a favorable path, or repeat based on outcomes. Final receipts must prove all owned clusters/PIDs stopped and source/install/seed/frozen inputs unchanged.

This two-file note is not an executable runtime capsule. It needs root review and separately frozen runner/bindings/gate/smoke inputs before any VM action. It introduces no source change, budget tuning, composition or claim that natural planning will favor GIN.
