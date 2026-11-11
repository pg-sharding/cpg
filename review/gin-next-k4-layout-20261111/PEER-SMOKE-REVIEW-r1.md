# Independent review of actual K4 smoke evidence

As of 2026-11-11: **PASS for the collected actual smoke evidence; no blocking issue found.** This review read local files only. It did not contact the VM, change runtime inputs or infer performance from smoke. The machine-readable receipt is [PEER-SMOKE-REVIEW-r1.json](PEER-SMOKE-REVIEW-r1.json).

The collection contains 729 hash-bound files plus COLLECTION.json. All file sizes and SHA256 values match. The actual receipt contains five clean builds with unchanged expected files, all core239 and posting-list checks passing, 907 installed headers per build, and installed ABI sizes B 152 / C 144 / K3 160 / K4 152 / K4_assert 152. Source pins, variant snapshots, assertions flags and common build flags match the fixed plan. Every changed release backend object remains under access/gin/.

Qualification has 125 original ordered cases, 75 extra cases, 35 prepared cases, 60 lifecycle comparisons, 55 native-vector cases, 55 budget cases and 55 generic-fallback cases. The budget calls total 64680. Stored qualification status confirms unchanged source, inputs, installed trees and seed, with no owned process or cleanup error remaining.

The 120 measured smoke commands contain 85 whole-SQL plans and 35 actual-AM results; none is retained. This review parsed raw JSON directly, without importing the runtime validator. Each SQL case has the same semantic tree and actual row/loop counts across all five roles. The comparison also covers index searches, recheck removals, exact/lossy heap blocks, filters and conditions. Each index scan uses the expected index and fixed probe count. All 35 AM results and their preceding literal commands have the expected loops and total TIDs.

All 120 recorded settings were checked against expected values, including the per-case forced scans, seq-control flags and 64kB lossy work_mem. This is stronger than checking equality between roles. Lossy-and really has 18040 lossy heap blocks and 142623 rows removed by index recheck in the B smoke plan, with identical counts in the other roles. The separate_keys Index Cond contains two distinct @@ expressions joined by AND. All 125 ordered oracle digest pairs match.

Each literal monotonic timestamp precedes its measured command, and measured commands do not overlap in the recorded ordering. All smoke commands record zero major faults and disk read/write bytes. B and T use the same installed prefix and backend SHA; role source/backend and common AM-module hashes match the frozen receipts. The root review binds the exact freeze/smoke-status hashes and the FRESH_HOST_CLEAN_SCREEN label.

The stored live proof reports 11 stopped cluster lifetimes and 10 verified untouched accepted copies, with consistent build/freeze bindings. That is a review of the recorded remote proof, not a new independent live process inspection. The clean-host label remains bounded by the recorded host checks; low sampled load alone cannot establish absence of every interference source.

The accepted run was already started separately by root after its own smoke gate. Its completion, final cleanup, all raw/retained values, paired arithmetic and performance interpretation remain outside this smoke PASS.
