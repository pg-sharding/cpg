# Batch 100 protocol/source audit

No production source changes or recompilation. ORIGIN.json retains all original
B72/fixed-B/Heap commit, source-plan, build, qualification and ELF pins. B/T
remain the same prefix/ELF/entrypoint. Session, common and build_common are
byte-identical to the completed natural SQL campaign.

Width1/2/7/8 original predicates/rows_sql and one-scan ordered digests are exact.
Expected per-scan count 49N-1 and sum 4816896N+49N(N-1)/2 were independently
enumerated from fixture IDs 1..200000. Batch totals multiply these frozen
scalars by 100; the control remains one probe. Probes, per-loop rows and output
totals are separate fields. No candidate-generated expected data is used.

The OFFSET(p.i%1) parameter binds each inner rescan while preserving offset 0.
That source intention is not proof of execution: the untimed actual EXPLAIN
gate and every measured raw plan must demonstrate docs/index Actual Loops100,
original Actual Rows per loop, and top aggregate 1 row / 1 loop. Scan1 from a
materialized/decorrelated shortcut fails closed, preserving its plan and
stopping clusters. No rewrite or retry is automatically attempted. Single-scan
row oracles have separate settings and loop scope.

The work unit intentionally amortizes per-command costs but introduces a
rescan context; it does not reproduce100 independent scans and cannot replace
the prior one-scan evidence. Report COMPLETE 100-rescan command timings,
absolute ranges and all controls, without causal/noise claims before samples.
All source/ELF/seed/cost/statistics inputs remain held; natural scan settings
are on, memoize/parallel/JIT off, and all resulting paths retained.

Inherited prior-art context, not a new novelty search:
https://www.postgresql.org/message-id/52F373CC.4050800%40vmware.com
Existing required-entry heap source 03dff8bfa5075e5838c7fbffc712d0b79d03f13d
is the same independent alternative; no cache/decoder composition occurs.
