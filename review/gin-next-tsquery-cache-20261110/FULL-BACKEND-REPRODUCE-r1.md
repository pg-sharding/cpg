# K1 full-backend qualification, new attempt r1

This packet is staged only. Its Python AST, command help and exact source snapshots
have been checked locally. The earlier actual-header/native prototype passed;
these three full builds and this SQL gate have not yet run. No timing is invoked.
Keep the original startup/decoder builds, screen and every earlier attempt intact.

K1 is an independent alternative over fixed B, not a patch series with S1, D1 or
C9. Raw B72 is `72b9498df9a369e747f8d96efb5a6cd33c2451e2`; the identical opaque
common prerequisite is `8a8c475037bfde101da23cc9b0364c9c020eca93`. K1 is
`9e0d6e84c5bd538e58a534c99cb39ca669c567b7`, authored by root <localhost>.
No output-array sizing change from the separate upstream posting-list discussion
is included. The one-vector cache follows prior GIN cache proposals, including
Heikki's 2014 discussion; it is not presented as a new general idea.

Use a new own namespace, for example
`/home/reshke/allfuzz/gin-next-tsquery-cache-20261110`. Stop and verify the separate
startup/decoder screen first; its final status must be `PASS_FIXED_SCREEN`, raw
4920 / retained 4100 / warm 820, remaining_owned=0, cleanup_errors=[], and all own
screen postmaster/backend PIDs absent. Never overlap these compilers with timings.
Do not change affinity, foreign processes, kernel settings or protected installs.

The root reviewer imports the declared input manifest/archive without overwrites.
Then, in that new namespace:

```sh
python3 -B full-build-harness-r1/build.py \
  --source-archive /home/reshke/allfuzz/gin-next-startup-decoder-20261110/baseline.tar.gz \
  --source-plan full-build-source-r1/SOURCE.json \
  --output build-r1 --core-port 45740
```

The existing public raw-B72 archive must have SHA256
`8c074fcf94a17d381e2df4a2b0554b925d76a777acb7e2f8a508abe7dfd2bbc4`.
Alternatively provide an independently obtained exact B72 archive, or use `--git`
with a local repository. Every one of the 7726 extracted files is compared with
the frozen source manifest before applying the declared exact source overlays.
The build writes all clean variants at the same source/build/compiled-prefix
paths, using separate DESTDIR installs. Sequence: B release, K1 release,
K1 assert. Configuration: GCC, `CFLAGS=-O2 -g -fno-lto`, `LDFLAGS=-fno-lto`,
empty CPPFLAGS, `--without-icu --without-readline --with-openssl`, cassert only
for the third variant; no LTO. nice 10, make -j2, at most 3 GB address space
(set that limit in the root launch wrapper). Required dependencies include GCC,
make, Perl, Python 3, bison/flex and OpenSSL development headers/libraries.
Each build must pass unchanged core239 and test_ginpostinglist. The receipt binds
all 7726 source files, 907 actual installed headers, compiler/configuration,
backend ELF, complete install tree, normal GIN object assembly and non-GIN
release object identity. Do not regenerate expected files.

After reviewing `build-r1/build-receipt.json` and `build-r1/status.json`:

```sh
python3 -B full-qualification-r1/qualify.py \
  --build build-r1 --output qualification-r1 --first-port 45800
```

This creates one fresh B seed and three private variant copies; no earlier
PGDATA or support .so is reused. It compiles native helpers against each
variant's actual installed headers/production flags. The native helper calls the
installed backend's `ginInitConsistentFunction` directly, without compiling a
replacement production TU. A compile-time macro only permits accessing the
appended K1 cache field with K1 headers. Eleven valid ternary-vector cases cover
one/two/eight/nine entries, phrase/weight/prefix/NOT, post-init hidden entries,
all FALSE/TRUE/MAYBE vectors, two initial recheck sentinels and repeated calls.
Expected totals per variant: 45,993 vectors and 183,972 checks. No timer runs.

The SQL fixture, 25 old literal answers, 15 extra ordinary cases, seven repeated
prepared cases and 12 single-session write/lifecycle comparisons are copied from
the passed startup/decoder gate. They compare complete ordered Seq/GIN multisets,
intended paths and cross-variant digests. Extras include absent/OR/phrase/prefix/
NOT/empty/null categories, intarray, builtin array and JSONB. Empty tsquery may
fold instead of producing a scan. Eleven further custom-opclass cases use exact
forwarding VOLATILE wrappers with different support OIDs/addresses. Their full
callback/result/recheck/repetition counts must equal B, as well as the ordered
SQL answers. This checks the generic fallback; it makes no general purity claim.

Raw native text and callback observations are fsynced before parsing/acceptance.
The helpers' shared libraries are produced inside the new output path and are
not publication artifacts. Finally, each own client and cluster is closed
independently with bounded deadlines, pg_ctl status=3, shut-down control state,
no socket/pidfile and postmaster/backend PID absence. The original seed, source
plan/installs and frozen qualification files must remain unchanged. Any failure
is preserved in this namespace; do not retry or change source thresholds after
a result. Correctness/build duration is not a performance observation.

Expected successful status is
`PASS_ORDINARY_SQL_NATIVE_CACHE_AND_GENERIC_FALLBACK`, timing_samples=0,
remaining_owned=0 and cleanup_errors=[]. Root reviews the actual evidence before
any separate timing proposal. No accepted K1 SQL timing is claimed by this packet.
