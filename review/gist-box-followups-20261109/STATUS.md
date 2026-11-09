# BOX followups — measurements and checks complete

All six full builds passed core239. Layout unchanged: 24664-byte scan state,
new C bool at offset34. The finite six-role SQL/AM gate and 132 full multiset
comparisons passed. Accepted r2: 2400 raw / 2000 retained / 400 warm; independent
28800-value recount PASS and local replay PASS. Both failed diagnostic attempts
remain separate with zero accepted rows. See RESULTS.md for all negatives.

C is not selected as a general upgrade. D forced all-match SQL median effects
versus V2r2: -1.83/-2.99%, both ranges cross zero; sparse D/R changes sign
(+10.42/-3.43%). No general replacement or merge recommendation is made.

Final read-only checks: 37 owned data directories shut down, 64 recorded runtime
PIDs absent, sockets absent, all six installations/source/seed/module unchanged.
The VM158 task is finished; no task was launched on VM84. Archive VM untouched.

Both source branches are pushed and ls-remote verified; CODE-COMMITS.json has
exact identities. Curated results publication and S3 receipts are tracked
separately in PUBLICATION.json and S3-RECEIPT-r2.json after shipment.
