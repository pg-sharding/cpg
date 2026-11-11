# Repeat the D3 experiment on a fresh Linux host

The recorded full backend builds and finite ordinary gate have passed. The new fresh-host frontdoor below has been checked locally for AST, help and exact frozen-input hashes only. No new Linux execution through that frontdoor is claimed. The recorded D3 campaign is complete: 3136 raw commands, 2688 retained and 448 warm; results are in RESULTS.md.

Use an ordinary OS account, Linux x86-64, Python 3.9 or later, GCC 13.3 or a documented equivalent, make, binutils, Git, Perl, Bison/Flex and OpenSSL development headers. Install dependencies separately. The scripts do not fetch packages or source. Keep the output path short and nonexistent, use unused ports, and reserve enough disk for four serial full clean builds and fresh cluster copies. No existing database, source tree or installed prefix is modified.

The build flags are `-O2 -g -fno-lto`, with `LDFLAGS=-fno-lto`, ICU/readline disabled and OpenSSL enabled. Pageinspect, intarray, amcheck and pg_trgm are built from the same tree. The scripts use nice 10, at most two make jobs and a 3,000,000,000-byte address-space cap inherited by children. Original regression expected files are preserved.

## Source, build and ordinary gate

Let `I` be the packet root containing the three unchanged input manifests and their member directories, not this documentation preparation directory. The source repository must already contain exact raw B72. The builder uses Git objects read-only, makes its own archive and verifies all 7726 baseline file hashes before applying the pinned per-variant diffs.

```sh
I=/absolute/path/to/d3-packet
O=/tmp/dec-d3-r1
python3 -B "$I/fresh-replay-r1/replay.py" --inputs "$I" --static-check
python3 -B "$I/fresh-replay-r1/replay.py" --inputs "$I" \
  --git /existing/repository/containing/B72 --output "$O" \
  --core-port 48100 --qual-port 48160
```

`--source-archive /existing/authentic-B72.tar.gz` is an alternative to `--git`. The archive is not distributed. Validation uses the full baseline manifest, so gzip representation need not reproduce the historical archive SHA. The known historical archive SHA is `8c074fcf94a17d381e2df4a2b0554b925d76a777acb7e2f8a508abe7dfd2bbc4`.

Ports 48100–48103 and 48130–48133 are used for core/posting checks; 48160–48164 are used by ordinary qualification. All must be unused. The four builds B/D2/D3/D3_assert use the same fresh source/build/configured-prefix paths and separate DESTDIR installs. The frontdoor invokes the unchanged qualifier directly; it bypasses the historical namespace/PID-specific waitchain and stops after ordinary qualification.

The exact fixture comes from `qualification/inputs/setup.sql`; no old PGDATA is needed. Original ordered SQL/prepared/lifecycle references and decoder cases are preserved. The new valid mixed patterns and boundary metadata are independently reconstructed. A successful new run must report `PASS_GIN_D3_MATCHED_BUILDS`, `PASS_D3_ORDINARY_SQL_AND_VALID_DECODER`, zero cleanup errors and five stopped owned qualification lifetimes. Inspect normal release ASM, source/907-header inventories and ELF/module bindings before timing. Do not convert a failed new attempt into PASS by changing expected output or reusing its directory.

## Prepare and smoke, then stop for independent review

Reserve a quiet host with no overlapping compiler, profiler or other timing job. Verify allowed CPUs and actual guest-core topology before choosing `CPU`. The original plan uses server/client 0:4 then 4:0; these are two placements on one host, not independent machines. Replace pairs only before a new freeze. Use `SHARED_LOAD_DIAGNOSTIC` if that is the prospectively chosen scope; a clean label by itself does not prove a quiet window.

```sh
P="$I/timing-prep-r1/campaign.py"
CPU=0:4,4:0
LABEL=FRESH_HOST_CLEAN_SCREEN
python3 -B "$P" --stage prepare --build "$O/build-r1" \
  --qualified "$O/qualification-r1" --output "$O/timing-r1" \
  --first-port 48200 --cpu-pairs "$CPU" --environment-label "$LABEL"
python3 -B "$P" --stage smoke --build "$O/build-r1" \
  --qualified "$O/qualification-r1" --output "$O/timing-r1" \
  --first-port 48200 --cpu-pairs "$CPU" --environment-label "$LABEL"
python3 -B "$I/timing-prep-r1/review-smoke-r1.py" \
  --timing-root "$O/timing-r1" --output "$O/new-smoke-recount.json"
```

Prepare hashes and fsyncs a timing seed plus 12 numeric copies before role assignment. Four are used only for the 112-command smoke; eight accepted-run copies must remain unused and unchanged afterward. Default timing ports are 48200–48203 for smoke and 48210–48217 for accepted cohorts. Keep sockets below the platform path limit by using a short output root.

Stop here. An independent reviewer must inspect the actual 112 raw/literal commands, 100 ordered Seq/index comparisons, seven SQL plan signatures, all 28 case settings, native checksums/bytes/loop counts, exact B/T identity, source/installed-prefix/header/module/seed hashes, owned PID/socket shutdown, eight unused accepted copies, and the host/topology window. The offline smoke recount does not itself approve timing.

Only after those actual checks, write a new external review JSON with exactly these required fields (additional evidence fields are permitted):

```json
{
  "status": "PASS_SMOKE_REVIEW_FOR_FIXED_RUN",
  "freeze_sha256": "SHA256 of the NEW timing-r1/freeze.json bytes",
  "smoke_status_sha256": "SHA256 of the NEW timing-r1/smoke-status.json bytes",
  "environment_label": "FRESH_HOST_CLEAN_SCREEN"
}
```

Compute SHA256 with `sha256sum` or Python's `hashlib.sha256(path.read_bytes()).hexdigest()`. Use the label in that run's freeze. Do not reuse a historical review or manufacture the status without completing the checks.

## One fixed accepted run and local recount

```sh
python3 -B "$P" --stage run --build "$O/build-r1" \
  --qualified "$O/qualification-r1" --output "$O/timing-r1" \
  --first-port 48200 --cpu-pairs "$CPU" --environment-label "$LABEL" \
  --review "$O/actual-independent-review.json"
python3 -B "$I/timing-prep-r1/analyze.py" "$O/timing-r1/cohort0" "$O/analysis0-new"
python3 -B "$I/timing-prep-r1/analyze.py" "$O/timing-r1/cohort1" "$O/analysis1-new"
python3 -B "$I/timing-prep-r1/audit-independent-r1.py" \
  --run-root "$O/timing-r1" --analysis0 "$O/analysis0-new" --analysis1 "$O/analysis1-new" \
  --answers "$I/qualification/inputs/answers.json" --out-new "$O/new-independent-recount.json"
```

Expected totals are 3136 raw, 2688 retained and 448 warm commands. All 28 cells and six role pairs remain fixed. The primary decoder metric includes actual backend allocation/materialization/free; compression and full-output checking remain outside that clock. Whole backend CPU and client wall are separate. SQL EXPLAIN execution time covers the entire fixed repeated-probe command. Preserve absolute median/min/max/mean/sample-stdev/MAD, direct round differences and ratios, all negative cells and exact-twin controls. No trimming, pooling, control normalization, tuning or automatic repeat is part of this protocol.

After execution, verify all owned lifetimes stopped, every known controller/backend PID and socket disappeared, and source, four prefixes, modules, fixture seeds and frozen inputs remain unchanged. Preserve a failed attempt and its cleanup evidence. No script is authorized to stop another workload. Historical root-only helpers contain the original namespace and are not a substitute for the fresh portable commands above.

For a final recorded packet, `review-recorded-r1.py` can rerun the local text-only qualification, codegen, smoke and arithmetic checks into a new outside directory. It does not start PostgreSQL or qualify a new Linux replay.

## Offline replay of the final recorded packet

The final packet retains all raw/literal journals as plain `.jsonl` files. The full original `evidence-full-r1/COLLECTION.json` binds every selected file. The offline wrapper checks every collection path, size and SHA before recomputing both cohorts and comparing the three regenerated analysis JSON files byte for byte with each bundled analysis. It does not require a final assembly/freeze manifest.

```sh
python3 -B "$I/review-recorded-r1.py" --packet "$I" --output /tmp/d3-recorded-recount-new
```

For an ordinary build/qualification/codegen-only recount, add `--qualification-only`; no timing evidence is then required. This is a local text replay, not a fresh Linux backend or timing run. Preserve failures in the new output directory. The final packet includes the actual completed D3 collection. Its separate local offline execution receipt records reconstruction of all 87,360 numeric fields and byte-identical bundled analyses; this is not a new Linux performance run.
