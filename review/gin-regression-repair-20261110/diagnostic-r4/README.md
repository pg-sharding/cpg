# GIN C9: addressed OR and startup diagnostic

This completed follow-up reuses C9 and the verified R3 installations. PostgreSQL code did not change. It repeats the two remaining SQL controls and measures actual-AM OR/dense/single-rare costs in two fresh reversed cohorts. Native and SQL OR/rare measurements improve against baseline in both new cohorts; the earlier full-SQL positive movements remain in the report. Seq is still variable. This packet supplies evidence, not a general regression-free or ready-to-merge claim.

- RESULTS.md is the current self-contained report, with new real-AM/SQL data and a clearly separate earlier full-SQL summary.
- patches/gin-lazy-adaptive-v9-over-fixed-b72.diff is the same candidate after fixed base8a8c475037bfde101da23cc9b0364c9c020eca93. PATCH-VERIFICATION.json binds it to the executed source. Apply one alternative form only.
- email-draft-UNSENT.txt is an English addendum to the main unsent draft; no message was sent.
- REPRODUCE.md gives dependencies, revision/flags, data/index setup, fresh-build or reused-build commands, exact diagnostic mode and native/SQL boundaries.
- evidence/ and results/ contain raw observations, all pairs/metrics/ranges/SD/MAD, independent reconstruction, software-profile text and final checks. Historical raw data stays in the preceding immutable R3 packet; HISTORICAL-R3.json pins the included summary and its hashes.
- build-source/, build-harness/, harness/ and the C adapter are the actual used inputs. Protocol snapshots remain unchanged. All15 new campaign cluster directories were shut down, eight measured backends/sockets absent, and six reference builds/final sources/seed/runtime/module unchanged. Core tests/builds were reused, not rerun by this diagnostic.

The supervisor PIPELINE collection-pending status inside evidence is a dated checkpoint. CLOSEOUT.json records the subsequent successful export and independent reconstruction. Publication receipts remain outside the frozen packet. Previous frozen packets are unchanged; no main/MDB branch was touched. No current-master, CREATE INDEX, independent-host confidence or priority claim.
