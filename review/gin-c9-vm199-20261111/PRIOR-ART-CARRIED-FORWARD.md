# Previous discussion and contribution

This repair wave carries forward the bounded source/archive review saved on 8 November 2026 in review/index-optimizations-20261107/gin-thread-comparison-20261108/GIN-THREAD-COMPARISON-20261108.md, plus the prior fixed-source SQL comparison in review/gin-sql-confirmation-20261109/. It did not perform a new exhaustive mailing-list/literature search. The references below are carried-forward evidence; no priority claim is made.

The earlier GIN fast-scan work already introduced advancePast and compressed segment skipping:

- https://www.postgresql.org/message-id/52E42AD0.5060600%40vmware.com
- https://www.postgresql.org/message-id/52F36245.6070006%40vmware.com

Advance V4 applies two cheap adjacent probes, exponential probing and binary upper-bound search to already decoded sorted TIDs in entryGetItem. It also compares logical unsigned TID keys directly where only ordering is required. Lazy V4 privately copies a selected compressed posting-page suffix while holding the existing lock and decodes its segments on demand. It does not retain an unlocked shared-page pointer or change the compression format. Earlier first-page frequency estimation and sequential eager consumption remained unchanged. Galloping, direct ordering and lazy consumption are established techniques, not inventions of this work.

The preceding full SQL campaign measured those alternatives independently and found absent/inline regressions plus unresolved off-path Seq movements. Their gains could not be added arithmetically. This wave tests actual changes: V7's smaller scan-entry state (negative), L8's boolean predicate in the lazy consumer, L9's deferred first-page materialization and exact cardinality using masked popcount of varbyte continuation bits, and C9's combined adaptive/lazy scan. Exact cardinality preserves the existing frequency estimate and associated entry ordering/sampling thresholds. The contribution is that PostgreSQL GIN integration, source-bound real-AM and SQL measurements, and explicit negative/control results. It is not a new compression scheme or a general index-build optimization.

David Geier's extraction/sort/build-accumulator series concerns earlier phases:

- https://www.postgresql.org/message-id/5d366878-2007-4d31-861e-19294b7a583b%40gmail.com
- https://www.postgresql.org/message-id/10afd923-38f4-451c-af89-34f8654533cb%40googlemail.com

The saved bounded review inspected the original thread's 52 messages and 59 attachments through v11 plus its collation continuation and found no direct duplicate of the consumer changes in those reviewed attachments. That is not proof of novelty across all GIN discussion, attachments or subsequent work. Earlier pg_trgm radix/adaptive/MSD prototypes are direct followups to that extraction series and should be attributed as such; those build/extraction gains are not mixed with this scan-repair wave.

All new measurements here use B72 plus the same supplied prerequisite. Current upstream master, CREATE INDEX throughput and independent-host confidence are not established by these experiments. Historical results, new screen measurements, full SQL confirmation and software-profile diagnostics remain separate.
