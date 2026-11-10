# Attribution and bounded history review

A new read-only search of the existing hackorum archive located Heikki Linnakangas's 2014 Small GIN optimizations list:

https://www.postgresql.org/message-id/52F373CC.4050800%40vmware.com

This is a direct conceptual predecessor for C9's private copying of compressed posting segments and deferred per-segment decoding. It also proposes integer TID representation for cheaper comparisons. Future C9 drafts should explicitly credit this message, in addition to the previously cited fast-scan thread. The previous immutable packets remain historical checkpoints; this note adds the more direct attribution. The concrete contribution is the new integration/measurement, not invention of lazy compressed consumption.

The current shared comparator already constructs uint64 keys in the baseline. P10/C10 optimize their construction using a bounded four-byte memcpy and an endian-dependent halfword reorder, preserving six-byte storage and two-byte alignment. This is a code-generation experiment in a known idea, not a new algorithm or a priority claim. No exact earlier four-byte-load patch was established by this bounded search; that is not evidence of novelty across all attachments or differently titled discussions.

Noah Misch's 2015 report is relevant portability context:

https://www.postgresql.org/message-id/20150719195033.GB1300191%40tornado.leadboat.com

It describes a particular old32-bit xlc inline-expression miscompilation and discusses how uint64 layout choices can affect32-bit ABIs. This wave does not reproduce that problem and does not infer current compiler support status from it. The prototype changes only transient comparison keys, not stored TID layout. Actual execution here is x86-64 little-endian; no32-bit,big-endian or independent-compiler performance claim is made. Keeping the prior transient <<32 layout is another possible refinement before a broad-platform proposal; this prototype also tests a compact48-bit logical key.

The source changes were written once on C9 and actually cherry-picked to fixed B72, resolving only the absent C9-only helper. All source preparation, preflight/build/screen outcomes and negatives remain separate. The existing C9/extraction-series review is in the earlier packets. Primary message metadata and bounded search scope are in PRIOR-ART-METADATA.json; full message bodies stay outside the public artifact bundle.
