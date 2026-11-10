# Actual untimed K3 dispatcher observations

The observer confirms that the 64-consecutive-miss policy disengages on the dense workload. It keeps the cache on rare, full, OR and prefix workloads. This is a separate instrumented executable and supplies counts, not a latency comparison or a causal explanation of previously measured K3 regressions.

All 18 reports passed independent recount: 244 key generations, 4,574,271 dispatches, 3,627,299 cache hits, 14,530 cache misses and 14 switches. The 932,442 subsequent direct calls had zero equal-adjacent vectors after disable. This last counter describes the captured streams only; it does not prove that a later workload could never regain reuse.

| Report | Keys | Dispatches | Hits | Misses | Switches | Direct after disable | Equal adjacent after disable | Max consecutive misses |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| sql/dense_and | 10 | 666,670 | 0 | 640 | 10 | 666,030 | 0 | 64 |
| sql/single_rare | 100 | 20,000 | 19,900 | 100 | 0 | 0 | 0 | 1 |
| sql/single_forced | 5 | 1,000,000 | 999,995 | 5 | 0 | 0 | 0 | 1 |
| sql/or_forced | 5 | 1,000,005 | 998,000 | 2,005 | 0 | 0 | 0 | 2 |
| sql/seq_control | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| sql/prefix | 100 | 20,100 | 10,200 | 9,900 | 0 | 0 | 0 | 3 |
| am_dense/loops1 | 1 | 66,667 | 0 | 64 | 1 | 66,603 | 0 | 64 |
| am_dense/loops3 | 3 | 200,001 | 0 | 192 | 3 | 199,809 | 0 | 64 |
| am_rare/loops1 | 1 | 200 | 199 | 1 | 0 | 0 | 0 | 1 |
| am_rare/loops3 | 3 | 600 | 597 | 3 | 0 | 0 | 0 | 1 |
| am_full/loops1 | 1 | 200,000 | 199,999 | 1 | 0 | 0 | 0 | 1 |
| am_full/loops3 | 3 | 600,000 | 599,997 | 3 | 0 | 0 | 0 | 1 |
| am_or/loops1 | 1 | 200,001 | 199,600 | 401 | 0 | 0 | 0 | 2 |
| am_or/loops3 | 3 | 600,003 | 598,800 | 1,203 | 0 | 0 | 0 | 2 |
| am_inline/loops1 | 1 | 5 | 3 | 2 | 0 | 0 | 0 | 2 |
| am_inline/loops3 | 3 | 15 | 9 | 6 | 0 | 0 | 0 | 2 |
| am_absent/loops1 | 1 | 1 | 0 | 1 | 0 | 0 | 0 | 1 |
| am_absent/loops3 | 3 | 3 | 0 | 3 | 0 | 0 | 0 | 1 |

Dense produces 66,667 dispatcher calls per key for 33,333 result TIDs. Every observed vector run has length one. The cache sees 64 misses, switches at dispatch 64, and delegates the remaining 66,603 calls directly. A residual regression in the earlier uninstrumented dense timings cannot be described as a failure to switch based on these observations. They do not establish which other cost caused that regression.

Rare has one initial miss followed by 199 hits per key. Full has one initial miss followed by 199,999 hits. OR has 401 cumulative misses and 199,600 hits, but its longest consecutive miss run is two. Its miss runs are one run of length one and 200 runs of length two. This distinguishes the consecutive policy from the earlier source-only cumulative-budget alternative; no K2 latency comparison was performed.

The original prefix statement performs 100 probes. Each key has 201 dispatches: 102 hits and 99 misses, with maximum consecutive misses three. Per key the exact miss histogram is 8 runs of length one, 44 of length two and one of length three. There is no switch in this observer run. The previously measured prefix regression therefore does not coincide with budget disengagement in this captured workload. Rare and prefix latency causes remain unestablished.

The Seq control creates no GIN keys. Inline has five dispatches, three hits and two misses per key; absent has one miss and no hit. These controls are retained. A dispatcher call is not an output TID: startup and other consistency checks participate in the policy.

Each actual-AM three-rescan capture has three new generations and exactly three copies of its one-scan counters, vector histogram and stream checksum. The checksum is an ordered noncryptographic diagnostic; ordered SQL result identity uses SHA256 separately. No pointer address is exported.

Qualification passed before tracing: unchanged core239 and posting-list tests, 40 ordered SQL cases, 7 prepared cases, 12 INSERT/DELETE/VACUUM comparisons, 11 mixed-vector native cases (183,972 checks), 11 budget-boundary cases (12,936 calls, 90 dispatcher transitions, 132 initializations, 22 context resets), and 11 generic callback forwarding cases. All 47 ordered reference digests agree with prior fixed-B evidence and independent Seq results. All 18 captures have ordered row comparisons and literal or AM tuple-count checks. Seventeen use GIN predicates with independent Seq/index/fixed-B digests; the ID-only Seq control uses its pinned ordered row reference and creates no GIN key. The observer remains disabled during the ordinary gate.

The separate full build uses GCC 13.3.0, -O2 -g -fno-lto and 907 installed headers. Full source inventories are verified at 7,726 fixed-B files, 7,726 K3 files and 7,727 observer files; the sole new path is ginlogic-probe.inc. Actual normal full-TU ASM retains the miss64 dispatch assignment and memo-hit reset, and the installed backend exports all three observer APIs.

All three runtime cluster lifetimes are stopped, with no cleanup errors. Root final read-only proof r2 also rechecks source, install, seed, frozen inputs, four normal object/ASM pairs and known PIDs/sockets. Its initial r1 proof failed while reading unrelated /proc metadata after the substantive checks; that failure and the narrower read-only r2 correction are retained. Two local post-run auditor draft mistakes are retained separately and did not change any executed input or captured data.

Limits: finite static synthetic queries, one instrumented release build, one shared-load VM, no concurrent writers, no new assertion build, no latency/CPU/wall measurements, no threshold changes and no universal correctness or policy recommendation. The new portable frontdoor has local AST/help/input-byte validation only; it has not had a fresh Linux replay. Actual execution belongs to the frozen build/qualification/capture controllers bundled here.
