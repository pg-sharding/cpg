# Source and workload review — prospective only

B72 is 72b9498df9a369e747f8d96efb5a6cd33c2451e2. All roles share the same
opaque prerequisite in fixed B 8a8c475037bfde101da23cc9b0364c9c020eca93.
Heap 03dff8bfa5075e5838c7fbffc712d0b79d03f13d is unchanged. B/T use the same
prefix, ELF and SQL entry point. This capsule compiles nothing and is not
combined with C9/C11/cache/decoder alternatives. ORIGIN.json binds all old
source/build/qualification/ELF receipts. The prior completed Heap SQL run SHA
is required and all its owned clusters/PIDs must be stopped before each stage.

The retained setup defines exactly one group(g%4096) term per base row g1..200000,
plus two special NULL/empty rows that do not match. N=1/2/7/8/32/128/512 ORs
select residues0..N-1 without common. Since200000=48*4096+3392, expected count
is49N-1 and sum is4816896N+49N(N-1)/2. Canonical ordered decimal IDs have no
trailing newline. Counts/sums/digests were generated from integer enumeration,
then checked independently by residue blocks, not candidate output. Each group
has48/49 rows; this can exercise materially different posting/storage/callback
work from the old common-superset result. No performance prediction is made.

Measured settings explicitly enable Seq/bitmap/index/index-only/TID paths, with
fixed64MB work_mem and unchanged costs/statistics. Untimed ordered Seq and GIN
oracles use separate transactions and ROLLBACK. The control has only a forced
Seq reference, not a nonexistent GIN condition. Natural plans and timed-setting
snapshots remain separate; observed Seq, GIN and legitimate primary-key index
plans are accepted when exact counts/rows/loops and scalar/digests agree. No
cross-role plan-signature equality is imposed. Complete costs/enable_* planner
settings and raw full plans are retained. Neither natural GIN selection nor a
new SQL improvement is known before actual EXPLAIN/timings.

Only capsule namespace/previous-run guard, query/answer/settings policy,
untimed natural metadata, validator and independent arithmetic adaptation
change from the successful previous SQL harness. Session metric boundaries,
build helper, held source/ELFs/seed, allocation of clones, fixed schedule,
cleanup and durable observation before acceptance remain. The controller now
also maps SIGTERM to finally cleanup. ADAPTATION.diff records the exact delta.

Prior context: the source's copied lower-bound heap/lazy root repair addresses
shared GinScanEntry advancement; no new source contribution or novelty claim
is introduced. Existing upstream heap discussion is retained in the complete
historical parent, including Heikki Linnakangas2014:
https://www.postgresql.org/message-id/52F373CC.4050800%40vmware.com
This is inherited verified context, not a new archive search.
