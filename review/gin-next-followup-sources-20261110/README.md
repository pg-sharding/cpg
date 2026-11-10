# GIN regression follow-ups: source preparation only

D2, K2 and K3 are independent alternatives over fixed B, not a series. No compile, SQL qualification or timing result existed for these snapshots at packaging. No claim that a measured regression is fixed follows.

D2 short-circuits a known long first delta before testing the four-byte batch. K2 disables the memo after64 cumulative misses; that could discard later OR reuse. K3 instead resets the miss counter on a hit and switches back to direct callbacks after64 consecutive misses. The threshold is fixed before measurements.

Each directory includes standalone format-patch/diff, minimal review deltas, exact source snapshots, root-authored commit identity and design limits. Existing D1/K1 result packets preserve all motivating gains and regressions. New four-clean-build K3 qualification and timing are prepared separately; no old result is relabelled.

See email-draft-UNSENT.txt and REPRODUCE.md. These are source hypotheses, not merge recommendations.
