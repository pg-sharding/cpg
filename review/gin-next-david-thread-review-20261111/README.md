# David Geier GIN thread review — publication candidate r1

Prepared for root review and freezing. No publication, mail or upload has been performed by this subtask.

The research snapshot is **2026-11-11 around 06:17 UTC**. A status-only addendum around **06:30 UTC** records root starting a separate D2 build/qualification on VM158. No D2 qualification result or timing is claimed. That fixed screen has18 native allocation-inclusive cases and7 whole-SQL workloads; full actual-AM/rescan coverage is an additional desirable follow-up.

Contents:

- [REVIEW.md](REVIEW.md): full thread evolution, concrete overlap matrix, merged SHA checks, current limitations and experiment specification.
- [PRIMARY-SOURCES.md](PRIMARY-SOURCES.md): dated primary links with encoded Message-ID and v12 attachment hashes.
- [SOURCE-AUDIT.json](SOURCE-AUDIT.json):60 main and22 collation message references, metadata for64 main and15 collation attachments, read-only archive bounds and Git/source checks.
- [email-addendum-UNSENT.txt](email-addendum-UNSENT.txt): optional English related-scan draft, unsent.
- [PACKAGE-METADATA.json](PACKAGE-METADATA.json): provenance and preparation boundaries.
- [SHA256-MANIFEST.json](SHA256-MANIFEST.json): exact candidate file sizes/hashes, excluding the manifest itself.

Only original analysis and compact metadata are included. Full email bodies, decoded upstream patches, downloaded source files, benchmark datasets, builds, binaries, clusters, credentials and runner logs are excluded. This is a research-review packet, not a new benchmark wave or patch series.

Research used the archive on VM51 only through limited READ ONLY transactions with a local30s timeout, then fresh public PostgreSQL/CommitFest/Git sources to cover continuations beyond the archive snapshot. Source code from attachments was neither applied nor executed. No frozen packets or existing Git refs were changed.

SOURCE-AUDIT query references beginning ../../ are relative to the original review directory; paths beginning review/ are relative to the workspace root /Users/reshke/work/pgpg. The one old-overview relative link in the packaged REVIEW was adjusted by one parent level for this extra publication-r1 directory. That external historical document is intentionally not copied into the packet. All required analysis is in the packet itself.

The independent K4 layout peer review, if needed, remains outside this packet as ../PEER-REVIEW.md; it is not part of the David-thread source snapshot.
