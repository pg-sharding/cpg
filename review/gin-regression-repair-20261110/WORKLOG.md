# Regression repair checkpoint

Task: repair repeated ordinary performance costs in advance V4/lazy V4 and diagnose off-path Seq movement. Old SQL packet remains immutable.

- New code: lazy V7 `1841cbedf6366c9588b06c4f2934785eb7fbb408`, parent L4 `aee770c6ed58bf352fd3c086418b6c0dda93ae42`; local branch `experiments/gin-lazy-v7-private-state-b72-20261110`. Three code files only; patch/diff in patches/. Decoder state moved into private allocation. Actual layouts B824/L4 848/L7 832, all 21 old offsets unchanged.
- All five new builds B/L4/A4/L7 release plus L7_assert passed original 239 core tests each. Build PID2849186 finished. No source change after this build.
- VM158 root: /home/reshke/allfuzz/gin-regression-repair-20261110-r1. VM51 archive untouched; no VM84 work launched.
- Original adapter r1 compiled but used InvalidOid in ScanKeyInit, causing normal cache-lookup ERROR during initial baseline qualification. Zero timing observations; both own seed/qualification clusters stopped. Root runtime and failed null-r1/PIPELINE.json remain unchanged; see NOT-AM-ADAPTER-r1.md.
- Adapter-only fix is isolated in runtime-r2/ (real F_TS_MATCH_VQ). Five-source ordinary/micro qualification has passed. Active supervisor2924612 is continue-r2.py, state PIPELINE-r2.json. It runs null-r2 then screen-r2; profiles only in screen qualification, separate from timed cohorts. Root original files remain immutable.
- Null: B/T/N2/N3/N4 all same ELF, 3 original SQL commands, 660 raw/600 retained/60 warm across two fresh cohorts. First cohort PASS; second underway at checkpoint.
- Screen: B/T/A4/L4/L7, 10 SQL +4 actual-AM cases; 3080 raw/2800 retained/280 warm. Both cohorts and all ten pairs; source/thresholds unchanged. See PROTOCOL.md and runtime-r2/harness/protocol.py.
- Full confirmation is pending screen review: `python3 -B runtime-r2/campaign.py --build <root>/build --output <root>/full-r2 --mode full --first-port 43000` gives B/T/L4/L7, all25 SQL cases, 2800 raw/2400 retained/400 warm. Do not select L7 without reading target, selective and negative/control pairs in both screen cohorts.
- B/A4 prior production gingetbitmap instruction shapes match after normalizing code addresses/RIP displacements; see STATIC-CODEGEN.json. This does not itself explain timings or prove zero source cost.
- After actual results: independent recount/compact collection, .diff/.patch + English UNSENT draft + all absolute/range/negative data + reproducible commands, push experimental code/results branches, publish to new flat S3 prefix and verify every object. Preserve failed/negative attempts. Existing working uploader is previous wave publish-s3.py (handles multipart by downloaded SHA256); adapt stage prefix to this wave. AWS CLI: review/s3-upload-20261028/venv-awscli/bin/aws. No main/MDB branch updates; no mail send.


## Checkpoint 2026-11-09T21:12:19.881081+00:00

R2 null and repair screen completed and locally reconstructed. V7 failed its inline target and is retained as a negative. All 34 own cluster directories are shut down; all source/install/fixture/runtime/module identities verified. Selected data downloaded with archive SHA256 af1e0f81b94e58476b6daada7b19df887af1cd661b2ab2c7fecf85d696b2b570.

R3 code L8/L9/C9 committed locally, actual-header preflight passed, five release builds and C9_assert passed 239 original core tests each. L8/L9/C9 release transitions changed exactly ginget.o. Fresh finite 6-role screen is running on VM158; no R3 timing result is accepted yet. Followup sources/protocol/commits/patches are under followup-r3/.


## R3 closeout 2026-11-09T21:46:16.358313+00:00

Both screen cohorts and full25 SQL cohorts completed. R3 34 ordinary cluster directories shut down; eight full and twelve screen measured backend PIDs absent, all six installs/final sources/two seeds/runtime/modules unchanged. Final selected archive SHA256 6a8e5123e7790c9febee6ab0fe13936dec2d4ba34fed0951282f6c9f3565d7b3; local raw reconstruction passed.

C9 absent CPU improves -66.99/-62.97%; native inline -17.89/-17.05%; full SQL inline is +1.79/-4.94% versus B and -4.83/-8.96% versus L4. OR +10.73/+1.75% and single_rare +3.49/+2.34% versus B remain unresolved. Do not call all regressions fixed.

A separate R4 diagnostic (same R3 source/builds, no source edits) is now running at /home/reshke/allfuzz/gin-diag-r4-20261110. It adds actual-AM OR/dense/single-rare cases plus existing AM and four unchanged SQL controls. New finite protocol is in diagnostic-r4/PROTOCOL.md; source and R3 packet remain unchanged.
