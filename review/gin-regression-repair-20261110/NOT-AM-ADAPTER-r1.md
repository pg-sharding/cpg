# AM adapter r1: rejected before performance

The initial adapter passed compilation but ScanKeyInit with procedure InvalidOid raised cache lookup failed for function 0 during baseline ordinary qualification. This is an adapter error, not a PostgreSQL or candidate result. Zero performance observations were taken. The seed and qualification postmasters stopped cleanly. Original runtime files and failed null-r1/pipeline receipts remain unchanged.

Runtime-r2 uses the real F_TS_MATCH_VQ procedure for the tsvector/tsquery scan key. Candidate source1841cbedf6366c9588b06c4f2934785eb7fbb408 and all five completed builds are unchanged. It runs into fresh null-r2/screen-r2 directories; no r1 observations are accepted or mixed.
