# Fresh matched hash composition build and fixture

Local preparation status: **static checked only**, recorded in `STATIC-AUDIT-v2.json` and `FINITE-COUNTS.json`. This preparation agent did not compile PostgreSQL, start a VM/server, create a seed, run SQL or collect timings. Root separately launched new build execution; its actual receipts remain separate from this local static audit. Old measured packets remain unchanged. Root owns source publication, transfer, execution, AM qualification and benchmark approval.

The source plan is `../source/SOURCE.json`: B72 `72b9498df9a369e747f8d96efb5a6cd33c2451e2`, exact no-op N, exact buffer hint H and the unchanged cherry-pick composition C. The archive contains all 7726 B72 source files (147165501 regular-file bytes). Every baseline byte is checked against the source manifest; each role starts from B72, applies its independently pinned standalone patch with zero fuzz, and checks its whole resulting tree plus exact edited-file snapshots. No fetch or network is used. `static-check.py` separately verifies Git snapshots, both patch orders, AST/help and the independent nineteenth-answer formula without running production code.

Use Linux x86_64, Python 3.9+, a local authentic B72 `git archive`, patch, GNU make, GCC (13.3 for continuity), binutils/objdump, Bison, Flex, Perl, OpenSSL and zlib development libraries. OS root privileges, perf and kernel changes are unnecessary. Reserve five unused regression ports and one seed port. Paths must be new, absolute, short enough for Unix sockets, and contain no whitespace. Keep the default current OS database username for the unchanged benchmark DSN protocol.

```sh
ROOT=/absolute/path/to/noop-buffer-combined-20261109
WORK=/short/new/owned/hash-combined
python3 "$ROOT/build-harness/build.py" --help
python3 "$ROOT/build-harness/build.py" \
  --source-archive /absolute/path/to/baseline.tar.gz \
  --output "$WORK/build" --core-port 40540
python3 "$ROOT/build-harness/prepare-fixture.py" \
  --build "$WORK/build" --output "$WORK/fixture" --port 40539
```

`--git /local/repository` is an alternative to `--source-archive` and reads only existing B72 objects. `--source-plan` defaults to this packet's source plan. The five original 239-case regression runs are mandatory; there is no switch to silently omit them. Build order is B, N, H, C release, then C assertions. Every build deletes only its own common build directory, uses the identical source pathname/build pathname/configured prefix and separate DESTDIR install. All use nice10, `make -j2`, `MAX_CONNECTIONS=2`, `CFLAGS='-O2 -g -fno-lto'`, `LDFLAGS='-fno-lto'`, `--without-icu --without-readline --with-openssl`; only assertions differ for C_assert. Explicit no-LTO flags are new-run provenance, not historical ELF identity. pageinspect, pg_prewarm and amcheck are installed. Expected outputs are never regenerated. Source, all 907 headers, full installed files, ELF, flags/compiler and normal hashsearch/hashpage/hashutil disassembly are recorded.

`build-receipt.json` has status `PASS_NEW_MATCHED_HASH_BUILDS` only after all five build/core runs; `status.json` must agree and have no cleanup error. Variants are B/N/H/C/C_assert. The runtime role map is exactly B→B, T→B, N→N, H→H, C→C. B and T therefore use one identical installation, ELF and entrypoint. Build PASS does not claim AM/lifecycle qualification. Failed command output and exact command metadata remain under the new output, and cleanup attempts only owned temporary regression clusters.

Fixture setup, pure C custom-hash support and engineered holdout generator are byte-identical to the newest no-op replay. All original 18 query objects/answers are preserved. Case19 is the exact prior H2 natural varying-residual query over existing `probes_hot` and `uniform_keys`, with no new rows/schema/support function. Its independently derived literal answer is `3000|1545|190739520` because 1545 probe thresholds admit key/id123456. The verifier performs all19 full seq/index EXCEPT ALL multisets, literal answers and untimed EXPLAIN checks. It requires case19's 3000 actual index loops with Memoize on, ordinary hot's one loop/2999 hits and disabled-Memoize hot's 3000 loops. These are seed checks with B, not evidence that all other roles passed.

The fresh C-locale UTF8 seed uses 512MB shared_buffers, autovacuum/JIT/query parallelism off, system timing clock, checkpoint interval1h and local Unix socket only. It creates setup data and all indexes, discovers the same prospectively defined 3000-absent-full-hash holdout on its own physical layout, then validates and cleanly stops. Index creation is untimed setup. All regular files are hashed/fsynced. Ten full stopped copies are created in numeric order `cohort0-slot0..4`, then `cohort1-slot0..4`; all copies match the full seed inventory and finish fsync **before any role assignment**. No old PGDATA or library is reused.

`fixture-receipt.json` status `PASS_NEW_SEED_AND_TEN_COPIES` binds the build receipt SHA, support path/SHA, cases/answers SHA, full seed inventory, holdout receipt/probe SHAs, all numeric copies and final-copy time. It deliberately contains no qualified runtime or performance PASS. Root's later runtime approval must bind these receipts and the separately reviewed AM gate. There is no circular fixture→qualification dependency. Ten copies are for accepted roles only; smoke/qualification use additional owned clones. The sibling controller receives the root-approved runtime and this fixture receipt. It does not obtain a fabricated timing approval from build or fixture PASS.

Resource expectations are estimates before execution: reserve8GB RAM and20GB free disk. The exact new fixture size S is recorded; the script checks at least `10*S + 1GiB` free before making its ten copies. Seed plus copies occupy11*S, plus five installed prefixes, one source tree and one common build. Historical matched nice10/j2 builds took about3–4min each including core; allow roughly20–30min for five builds on a comparable idle VM, plus seed/verification/copy/fsync time (storage/load dependent). These are planning estimates, not new observations. Scripts record actual command times, bytes and digests.

Read `SEMANTIC-REVIEW.md` for compatibility and the selected finite ordinary gate. The prior parent stale-hint/replacement/concurrency evidence remains separate and is not rerun or promoted to a proof for C.

After build and fixture PASS, root can review and run the new one-shot gate:

```sh
python3 "$ROOT/build-harness/gate.py" --build "$WORK/build" \
  --fixture "$WORK/fixture/fixture-receipt.json" \
  --output "$WORK/gates" --port 40550
```

This creates five EXTRA disposable clones, one each for B/N/H/C/C_assert, never starts the ten measurement copies, and uses each role's own installed headers and actual ELF. The complete-production-TU page oracle, original18 historical multiset/literal cases,126 logged/unlogged/TEMP lifecycle cases and21 cursor traces are exact preserved source from the prior no-op R3 gate; `gate-inputs/ORIGIN.json` binds those bytes. The fresh holdout receipt is supplied at runtime. Each role also runs the new full19 multiset/literal/plan verifier. Normal and UBSan oracle modules are newly compiled; no old binary is reused. They perform no native timing.

Successful `<gates>/status.json` has `PASS_MATCHED5_UNTIMED_GATES`, five role PASS records, zero accepted/timing samples, no cleanup errors, five stopped-cluster receipts and before/after/finally protection of all installed prefixes, seed, support and all ten unused copies. Finite totals are8862720 page cases,427064060 saved-item checks,95 full19 multisets,90 historical multiset cases,630 lifecycle checks and105 cursor traces. No timing runtime approval is created automatically; root must independently review and pin the exact gate/receipt hashes before creating its runtime manifest and smoke.

All failures and original output are preserved in the new gate attempt. Public result JSON files up to8MiB can be collected directly; if larger, the receipt names lossless gzip chunks of at most8MiB, preserving original size/SHA. PGDATA, modules and private server/full runner logs remain execution artifacts outside the clean text packet. No new native timing, CREATE INDEX speedup, source tuning or benchmark execution is part of these scripts.
