# Previous discussion and contribution

This SQL confirmation carries forward the bounded source/archive review saved
on 8 November 2026 in
`review/index-optimizations-20261107/gin-thread-comparison-20261108/GIN-THREAD-COMPARISON-20261108.md`.
It does not perform a new exhaustive mailing-list or literature search.

The earlier GIN fast-scan work already introduced `advancePast` and compressed
segment skipping:

- https://www.postgresql.org/message-id/52E42AD0.5060600%40vmware.com
- https://www.postgresql.org/message-id/52F36245.6070006%40vmware.com

Advance V4 operates on already decoded, sorted TIDs in `entryGetItem`: two
cheap adjacent probes, then exponential probing and binary upper-bound search.
V4's additional expression change directly compares logical unsigned TID keys
where only ordering is needed, instead of materializing a three-way result.
Galloping, binary search and direct ordering predicates are established
techniques. The concrete work is integrating them with existing GIN cursor
transitions and supplying source-bound measurements and negative controls.

Lazy V4 defers materialization of the selected posting-tree page's unused
compressed suffix. The suffix is privately copied under the existing lock;
later segments are decoded on demand without retaining an unlocked shared-page
pointer. First-page frequency estimation and sequential eager consumption are
preserved. This is an integration with GIN ownership/navigation/rescan rules,
not a new compression format or an invention of segment skipping.

David Geier's extraction/sort/build-accumulator series concerns earlier phases:

- https://www.postgresql.org/message-id/5d366878-2007-4d31-861e-19294b7a583b%40gmail.com
- https://www.postgresql.org/message-id/10afd923-38f4-451c-af89-34f8654533cb%40googlemail.com

The saved bounded review inspected the original thread's 52 messages and 59
attachments through v11, plus its collation continuation. It found no direct
duplicate of these consumer changes in those attachments; that is not a
priority claim for all GIN work. Our earlier pg_trgm radix/adaptive/MSD ideas
are direct followups to that extraction series and must be attributed as such.

This wave's new evidence is full-backend advance V4 SQL measurement and a
matched independent lazy V4 control, with one common prerequisite in every
tree. Both candidates retain their existing source. Their combined behavior,
native-body behavior with that prerequisite, index-building throughput and
current upstream master are not measured here. Gains from the two alternatives
or from extraction/build work must not be added arithmetically.
