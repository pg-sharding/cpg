# Repeat C11 independently

Use Linux x86-64 with GCC 13.3, GNU make, Python 3, Bison, Flex, OpenSSL and
zlib development headers, binutils, util-linux (`taskset`, `lscpu`) and procfs.
ICU and readline are disabled. Run as an ordinary user with at least 20 GB
free disk space and preferably 16 GB RAM. CPUs 0 and 4 must be available and
belong to different physical cores; inspect `lscpu -e=CPU,CORE,SOCKET,ONLINE`.
Other CPU layouts require a separately reviewed controller adaptation.

The original runs used GCC 13.3, `-O2 -g -fno-lto`, serial clean builds with
make `-j2` and nice 10, identical source/build/compiled-prefix paths and
separate DESTDIR installations. Timed builds have assertions off; only the
final C11 assertion build enables them. The driver runs 239 core regression
tests and the posting-list test for all five builds, installs the included
contrib dependencies and verifies source, header, ELF and object bindings.

The commands below are a portable entry point, not an assertion that this
exact new replay was executed. The recorded actual build used `--source-archive`
with B72 SHA-256 `8c074fcf94a17d381e2df4a2b0554b925d76a777acb7e2f8a508abe7dfd2bbc4`.
That archive is omitted from this packet. An existing local Git repository
containing B72 is enough; no network access or checkout change is needed.

From the packet root, choose a new, short output root and unused ports:

```sh
gin_packet=$(pwd)
gin_run=/tmp/gin-c11-replay-new
mkdir "$gin_run"
nice -n 10 python3 -B "$gin_packet/c11/build-harness/build.py" \
  --git /absolute/path/to/postgresql \
  --source-plan "$gin_packet/c11/build-source/SOURCE.json" \
  --output "$gin_run/build" --core-port 45340

nice -n 10 python3 -B "$gin_packet/c11/campaign.py" \
  --build "$gin_run/build" --output "$gin_run/qualify" \
  --first-port 45400 --mode qualify
```

Require `PASS_GIN_C11_BUILDS` and qualification `PASS`, with empty cleanup
errors. Qualification creates a fresh checksummed deterministic seed of
200,002 docs rows. All 25 ordered Seq/GIN multisets and frozen scalar answers
are checked on B/C9/C10/C11/C11_assert, along with prepared rescans and actual
AM calls. Expected answers are included; never regenerate them from a
candidate. The seed and helper module remain immutable for the next stage.

Review host load, active compilers and topology before one bounded screen:

```sh
nice -n 10 python3 -B "$gin_packet/c11/campaign.py" \
  --build "$gin_run/build" --output "$gin_run/screen" \
  --first-port 45400 --mode screen --qualified-from "$gin_run/qualify"
```

This is the recorded protocol: B/T/C9/C10/C11, 13 SQL cases and 7 actual AM
cases, two warm and ten retained Williams-order rounds in each of two CPU,
clone and session placements. It produces 2,400 raw / 2,000 retained samples.
Shared buffers are 512 MB per postmaster; work_mem is normally 64 MB, with the
declared lossy control at 64 kB. Autovacuum, JIT, parallelism and Memoize are
disabled. Normal durability remains enabled. Only Unix sockets are used.
All copies are hashed and fsynced before role assignment; all owned clusters
must stop. Preserve failed outputs and use a fresh root for a reviewed fix.

The whole-command CPU and client wall boundaries differ from SQL executor
time and the real `index_rescan`/`index_getbitmap`/`tbm_free` loop clocks.
Report them separately, retain every pair and spread, and do not normalize
by the B/T twin. The full mode is only prepared code; it was not executed and
must not be promoted automatically from the screen.

## Replay the recorded numbers without PostgreSQL

These commands restore the original collected evidence in a new directory,
then recount the recorded data. They do not build or run a database server.

```sh
python3 -B restore-screen.py --output-new /tmp/c11-recorded-restore-new
python3 -B audit-screen.py \
  --collection /tmp/c11-recorded-restore-new/screen-r1 \
  --output-new /tmp/c11-recorded-audit-new
python3 -B render-screen.py \
  --collection /tmp/c11-recorded-restore-new/screen-r1 \
  --output-new /tmp/c11-recorded-tables-new
```

Restoration checks every gzip chunk and all 58 original collected files.
The independent auditor does not import the campaign analyzer; it reconstructs
the five-role Williams sequence and checks chronology, all raw answers,
source/executable bindings, plans, I/O and all numerical groups using its own
formulas. The original frozen analyzer and its outputs are also retained.
