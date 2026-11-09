# Typed V8 first-attribute load — experimental draft

This is an incremental alternative above V6, preserving its typed internal and
leaf search. It changes only extraction of a non-NULL, known single int8 key.
It is not a general replacement for B72 or a measured SQL improvement.

- `v6-to-v8-firstattr.diff`: apply above V6. This is the small review diff.
- `typed-v8-firstattr.diff`: standalone B72 alternative. These two files are
  **not a series**; do not apply both.
- `SOURCE.json`, `source/`: exact baseline, parent and candidate source pins.
- `prepare.py`: deterministic generation from pinned local historical inputs.
- `PATCH-REPLAY.json`: both diffs apply and reproduce the exact candidate.
- `compile-gate.py`, `codegen-r1/`: complete normal translation units compiled
  against the existing matched release/assert installations, including an exact
  V6 compilation twin for each. No backend was relinked.
- `page-oracle.py`, `page-oracle.c.in`, `page-oracle-r1/`: diagnostic DSOs include
  each complete actual TU. Only the static helper is invoked, against a linear
  walk on the same locked page, in the existing assert backend in a new cluster.
  DSOs are never presented as a patched server or used for SQL timings.

VM158 checks pass: 30,240 calls per helper version across leaf and internal
pages, five amcheck calls, and a stopped owned cluster. Installed files are
unchanged. Release helper size is 674 → 421 bytes, and its 61-byte cold fragment
is gone. Assert helper size is 1,020 → 782 bytes. These are byte counts; there
are **no new microbenchmark times, SQL times or full-backend core test runs**.

The production eligibility predicate and source after the changed extraction
block are identical to V6. The generic comparator is still used for NULLs,
truncated tuples and internal equality. The candidate uses `memcpy` into an
int64 rather than relying on Datum by-value representation or an aligned cast.
Only Linux x86-64/GCC 13.3 was checked. Root NULL pivots were not demonstrated
by the recorded shape query; wider layout/platform coverage remains future work.

## Reproduce these checks

Python 3, Git, GCC 13.3, binutils, and the original matched B72 installation
with amcheck/pageinspect are required. This step reuses read-only installations
from the previous typed campaign; it does not silently substitute another
PostgreSQL build. The scripts verify complete installed-file inventories and
backend hashes against its `build-proof/*/binding.json` before use. The server
must run as an unprivileged user. Use a new output directory and free port.

```sh
python3 compile-gate.py \
  --existing-root /home/reshke/allfuzz/typed-leaf-v7-sql-20261108-r1 \
  --out-new /home/reshke/allfuzz/typed-v8-recheck/codegen

python3 page-oracle.py \
  --existing-root /home/reshke/allfuzz/typed-leaf-v7-sql-20261108-r1 \
  --out-new /home/reshke/allfuzz/typed-v8-recheck/oracle \
  --port 40882
```

The actual run used output root
`/home/reshke/allfuzz/btree-typed-v8-firstattr-20261109-r1`, port 40881,
nice 10, `-O2 -g`, and the prior build's complete warning/configuration flags.
The scripts record compiler commands and source/module hashes. The oracle
creates its own fixture data, has no external input data, and stops its own
cluster in `finally`. Its temporary `data/` directory is not an artifact to
publish. Never point it at a pre-existing data directory.

For a fresh backend build, apply the standalone diff to exact B72, or the
incremental diff to exact V6, in a separate checkout. Reuse the previous
campaign's common-path build method, compiler/configuration and fixed matrix;
rebuild B72, twin, V6 and V8 consistently. The previous tested harness and full
setup are in
`review/index-optimizations-followups-20261108/typed-leaf-v7/full-sql-results-20261109-r5/publication-r1/`.
Its V7-specific assertions, source/ELF bindings and role names need a deliberate
V8 adaptation; this packet does not claim that adaptation or replay was run.
Keep fresh backends distinct from warmed same-PID diagnostics and report
absolute times, paired ranges and both cohorts. CREATE INDEX remains fixture
setup for this read-search experiment.

## Prior discussion and readiness

Direct context: [Support specialized B-tree page searches, 2026-08-05](https://www.postgresql.org/message-id/79FF16D2-B815-45C9-A24A-D0851981E78B%40yandex-team.ru).
The proposal predates this experiment. The local contribution here is a small
implementation refinement of our V6 control, not a new search algorithm.
No new archive search or adoption-status verification was performed in this
step. The English email draft is UNSENT and explicitly not ready as a speedup
report until full-backend and timing checks are complete.
