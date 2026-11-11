Reproduce the recorded data offline

Python 3.9+ is sufficient. Run from any location with a new nonexistent output directory:

```sh
python3 -B /path/to/packet/review-recorded-r1.py \
  --packet /path/to/packet --output /tmp/d2-recorded-replay
```

This restores all 77 timing files from exact metadata and whole-line gzip chunks, validates the 39 frozen input members, independently recounts the four-build ordinary gate, checks the 100-command smoke, reruns both cohort analyzers and compares all six resulting analysis files byte-for-byte. It independently reconstructs all 78,000 numerical fields and verifies the full recount against the recorded receipt. It does not start PostgreSQL, compile, access a VM or use the network. Failed outputs remain available and are never reused automatically.

For restoration only:

```sh
python3 -B /path/to/packet/restore-raw-r1.py \
  --packet /path/to/packet --output /tmp/d2-restored-timing
```

Fresh Linux build, setup and benchmark

Follow [fresh-replay-r1/README.md](fresh-replay-r1/README.md). It specifies dependencies, flags, exact source revisions, the existing-B72-Git alternative to the omitted archive, fresh paths/ports, resource limits, four clean builds and unchanged ordinary qualification. Fixture creation is the exact inputs/qualification/inputs/setup.sql, executed automatically in a fresh owned seed. The original decoder-native.c is compiled against each actual installed header set; no old ELF or helper is reused for fresh builds.

The frontdoor stops after build and qualification. Timing is a separate prepare -> 100-command smoke -> independent semantic/live review -> fixed run workflow. It keeps 18 native allocation-inclusive cases and seven complete SQL cells, all six pairs, exact B/T and all negatives. The newly written fresh frontdoor has only static/help validation. Its Linux execution has not been run. Historical controllers did execute the pinned results in this packet.

Time and evidence boundaries

Native inner CPU covers actual backend decoding allocation/materialization/free and excludes compression/full generated-output verification. Whole backend command CPU and client wall remain separate. SQL uses the full repeated-probe EXPLAIN execution time as its primary metric, with backend CPU/client wall separately retained. Do not divide a LATERAL command into independent client requests or pool the cohorts. All raw, warm and negative observations are preserved; no trimming, normalization, significance or causal claim is made.

Source application

D1 and D2 are alternatives over the identical fixed B. Their format patches in source/ each apply independently to that baseline; D2-over-D1-review.diff is only an incremental review aid. The builder's complete raw-B72 overlays already include the common prerequisite and must also be used as alternatives, not stacked. Every extracted baseline/source file is verified, and expected files are never regenerated from candidate output. No baseline source archive, ELF, PGDATA or complete runner log is distributed here.

The exact four required external-review fields and a hash-generation example after actual semantic/live checks are documented in fresh-replay-r1/README.md. Do not reuse the historical approval receipt for a fresh run.
