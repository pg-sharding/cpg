# GIN regression repair experiments, 10 November 2026

R2 diagnosis and R3 screen/full-SQL confirmation are complete and independently reconstructed. C9 fixes absent CPU and the native inline penalty; full SQL inline is +1.79/-4.94% versus B and -4.83/-8.96% versus lazy V4. OR and single-rare CPU medians remain positive versus B in both full cohorts. This packet preserves the progress and those limits; it is not a ready-to-merge or general-speedup claim. A separate R4 real-AM diagnostic was started after the final R3 snapshot, without another PostgreSQL source change. R4 observations are outside this frozen packet.

- RESULTS.md: full25 SQL and actual-AM outcomes, absolute times, negative controls and limits.
- R2-RESULTS.md: rejected V7 state-layout experiment, same-binary calibration, software profiles.
- R3-SCREEN-RESULTS.md: L8/L9/combined screen with all alternatives and remaining costs.
- patches/gin-lazy-adaptive-v9-over-fixed-b72.diff: complete C9 code after fixed baseline 8a8c475037bfde101da23cc9b0364c9c020eca93. PATCH-VERIFICATION.json checks the distributed artifact against the actual measured source.
- followup-r3/patches/: incremental .diff/.patch files with explicit parents in CODE-COMMITS.json; they are alternatives to the complete diff, not something to apply twice.
- REPRODUCE.md: dependencies, revision/flags, data/index creation and commands for real-AM and SQL reproduction; metric boundaries are explicit.
- email-draft-UNSENT.txt: English draft with results, remaining costs, contribution and previous discussion. No mail was sent.
- PRIOR-ART.md: bounded prior-art evidence and contribution scope; no priority claim.
- evidence-r2/, evidence-r3/, results-r2/, results-r3/: selected metadata, synthetic raw observations, unpooled analyses, all pairs/ranges/SD/MAD and clean-shutdown proofs. Final checks are dated snapshots of these completed campaigns, not a claim that later R4 processes do not exist.
- CODE-PUBLICATION.json: verified experimental source branches in cpg, including rejected V7. CODE-COMMIT.json retains the original source-preparation checkpoint; current tests are in the evidence.

The original root campaign/gin-am-micro.c is retained only to document an adapter qualification failure with zero timing samples. Run runtime-r2 for R2 or followup-r3 for R3. Earlier published packets stay immutable. No current-master, CREATE INDEX or independent-host confidence claim. No main/MDB branch is modified. Publication receipts outside the frozen packet record the results branch and S3 verification.
