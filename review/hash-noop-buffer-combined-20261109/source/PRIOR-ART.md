# Previous discussion and novelty boundary

This is a cleanup hypothesis, not a new hash indexing algorithm. Current pinned PostgreSQL source says `_hash_checkqual()` cannot inspect the original indexed value and always returns true; the executor performs the lossy heap recheck. Removing the two call predicates preserves that behavior, retaining the exported stub and existing recheck flags.

A bounded READ ONLY archive search found13 messages across the2008hash-value-only and2017page-at-a-time work. Three selected attachments from topic36025 were Base64-decoded locally as data, never executed: v16 page-at-a-time adds both call predicates; the companion `_hash_step` cleanup removes an older obsolete loop call, rather than these loader calls; a later cleanup attachment does not mention `_hash_checkqual`. Their exact metadata/SHA are in prior-art-scope.json. Raw message excerpts/attachment bodies remain private and are not part of a future public bundle.

- [2008 scan/recheck design](https://www.postgresql.org/message-id/20080516130442.GP28382%40it.is.rice.edu): hash equality chooses candidates and the executor rechecks the original key. Direct semantic prior art.
- [2008 inner-loop cleanup review](https://www.postgresql.org/message-id/23649.1216398205%40sss.pgh.pa.us): reducing per-tuple work in `_hash_checkqual` and reading the known hash-tuple layout. Direct historical motivation, a different patch.
- [2017 page-at-a-time loader review](https://www.postgresql.org/message-id/CAA4eK1LnQi51L8%2BmsZasZ926fbiO7BGpjeaY5XcgQn3Xdcvm3w%40mail.gmail.com): the present loader predicates are already visible in the reviewed code. Context for their origin, not a proposed removal.

No retrieved selected attachment proposes this exact two-predicate deletion. The query and attachment selection cannot establish absence elsewhere or under renamed subjects, and latest CommitFest/Git status was not refreshed. No novelty/priority claim is made or needed for this measurement. Related overflow-prefetch and duplicate-page-check ideas have NOT received their own prior-art search.
