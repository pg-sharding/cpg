# Fresh matched fixture, prepared before code assignment

The adjacent build-harness owns execution of this recipe. This document is
stage-only: no cluster/setup/SQL has been run in preparing the harness.

1. Fullclean B/N/H/C release plus C assertions use the same source/build/
   compiled-prefix paths and compiler/configuration, independent install roots,
   `-O2 -g`, no LTO, make-j2, nice10. B/T use one exact baseline install.
   Keep source/header/compiler/config/ELF and unchanged expected-file proofs.
2. On a NEW B-only seed install amcheck/pageinspect/pg_prewarm and compile the
   exact existing fixture-only custom-hash-support.c. Bind its path/SHA; it
   contains no new production search implementation. Load the byte-identical
   inputs/setup.sql. Data are1000003uniform rows,300000skew/2048keys,
   100000identity rows,5000zero/MAX-collision rows each,32tiny,50000ordinary
   write-fixture rows and original probes. Index creation is untimed setup.
3. Run the unchanged deterministic holdout discovery from latest no-op replay:
   actual overflow bucket,3000distinct absent probe keys whose full hashes are
   not among stored full hashes in that bucket. Record its new physical chain,
   probes and discovery SHA; no dependency on old PGDATA/support.so/old probes.
4. Preserve all18 scalar maps and Seq/hash EXCEPT ALL multiset checks. The19th
   is the exact old H2 residual query over existing probes_hot (id1..3000,
   k123456), predicate `h.id <= 122000+p.id`. Since uniform_keys has id=k,
   p.id1456..3000 pass:1545rows, checksum123456×1545=190739520. The frozen
   aggregate is3000|1545|190739520, not candidate-generated expected output.
5. Untimed EXPLAIN must confirm residual3000actual index loops with Memoize
   enabled; ordinary hot remains1probe/2999Memoizehits; forced rescans3000;
   engineered holdout3000absent probes/chain work and separate zero target heap
   counter proof; collision-present64loops/4999rechecks per probe; tiny natural
   Seq/forced index and off-path Seq controls are retained. Save full plans and
   full multiset results across all qualified variants. No new concurrency job
   is part of this performance recipe.
6. Cleanly stop/check/fsync seed. Create all ten numeric cohort×slot copies,
   hash every regular/numeric/fork file and fsync them BEFORE any code-role
   assignment or postmaster startup. Freeze inventory/copy timestamps and seed
   receipt. Root checks ten copies still unused after the separate smoke.
7. Create five separate fresh smoke copies. Start smoke postmasters/sessions
   in numeric order; no accepted copy may be consumed by smoke. After PASS and
   clean stops, root reviews fixed inputs and ten unused accepted copies.
8. Accepted numeric role order is B/T/N/H/C then C/H/N/T/B; case order reverses
   in cohort1. Root owns starts, final best-effort stops, PIDs/pg_ctl/control-
   state checks and revalidation of source/runtime/modules/seed/freeze.

`verify-fixture.py` in this directory is an ordinary independent multiset/
literal verifier over the exact19definitions. The build owner's finite verifier
also saves the untimed actual-loop/Memoize proof. Neither verifier turns static
packet preparation into an executed gate. Preserve every failed attempt.
