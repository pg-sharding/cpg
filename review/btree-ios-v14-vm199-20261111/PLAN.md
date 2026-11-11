# IOS V14 on VM199, fixed independent replication

Requested by the user during GIN C9 setup, before new IOS build or timing.
All remote files live under `/home/reshke/wpgpg/ios14-199-1111`.
Wait for the GIN C9 campaigns to finish, then acquire the shared experiment
lock before building or running IOS. No concurrent timing/build campaigns.

Repeat the published IOS V14 protocol unchanged: B72
`72b9498df9a369e747f8d96efb5a6cd33c2451e2`, exact baseline twin, V13 and
V14 alternatives. V14 source identity is
`113e61347b43d2ae4afb187944ede9e9f6108c24`. Historical SOURCE manifests
keep their original null commit fields; new byte-identity verification is
recorded separately. No patch tuning or query selection on this machine.

Four full clean matched builds: B/V13/V14 release and V14_assert; same
compiler and absolute common build path, `-O2 -g -fno-lto`, OpenSSL,
no ICU/readline, make -j2 and nice 10. All original core239 tests per build.
Use the original finite target-output/native/layout/ownership gates.
The historical stopped seed is unavailable on this new VM: execute its
documented independent baseline recipe, then compare against all original
expected bytes without regenerating them. Preserve failures.

Use the original independent SQL setup and all 19 cases, including short
postings, LIMIT, mixed scans, heap fetches, single attribute and off-path
controls. Create and hash all eight measurement copies before assignment;
smoke-test four extra copies and independently review all 76 smoke plans,
source/build/input identities and clean shutdown before accepting timing.

Two fixed cohorts, baseline/twin/V13/V14, two warm and 12 retained rounds:
2128 raw / 1824 retained / 304 warm observations. CPUs backend/client 6/4
then 4/6, after checking separate guest cores. Original ports 40640..40643,
40649, 40750..40753, 40759, 40760..40763; private sockets only. Seed creation
uses 40648. Check availability before use. Keep every sample and metric,
undefined zero-denominator ratios, negative cases and baseline-twin drift.
Do not pool cohorts, trim, subtract controls or repeat based on timing signs.

This measures warm SQL execution; CREATE INDEX is setup and native helpers
are correctness checks. Report execution time and backend CPU separately,
absolute medians/ranges, paired ratios and differences, plus historical
comparison with the previous VM. Save exact patches, an English UNSENT
draft, raw synthetic evidence, all-case tables and reproduction instructions.
