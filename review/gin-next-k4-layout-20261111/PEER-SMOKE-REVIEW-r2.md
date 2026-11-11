# Independent actual r2 smoke review

2026-11-11: **PASS for the prospective accepted-run gate.** The receipt is [PEER-SMOKE-REVIEW-r2.json](PEER-SMOKE-REVIEW-r2.json). Review used local raw JSON directly, without importing protocol/validate or running any VM/backend process.

All 738 collection-bound files match their sizes and SHA256. There are 120 measured smoke commands, zero retained observations, 85 SQL plans and 35 actual-AM results. All 17 expanded semantic and actual plan signatures match reviewed r1, including rows/loops, index searches, exact/lossy blocks and recheck removals. Expected settings were checked for all 120 commands, all 125 ordered oracle digest pairs match, and literal/measurement monotonic chronology passes. The lossy and separate-@@ cases retain their intended conditions.

Protocol/script/build/qualification/seed bindings match r1 exactly. R2 has 15 fresh fsynced copies, its separate R/r2/s namespace and ports 47300+, with B/T prefix/backend identity preserved. The stored live proof records 11 stopped lifetimes and ten untouched accepted copies with matching build/freeze hashes. This is review of stored live evidence rather than a new live inspection.

No performance conclusion is drawn from smoke. The complete accepted r2 run, source/install/seed/module final bindings, shutdown/socket proof, monitor/environment review and independent full recount remain separate gates. R1 remains a complete shared-load diagnostic and is not pooled with r2.
