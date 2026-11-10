# K3 consecutive-miss cache: four fresh build preparation

This is a new independent comparison on raw B72 with the same opaque fixed
prerequisite in every tree. Exact release roles are B, K1 and K3; the fourth
build is K3_assert. K2's cumulative-miss variant remains source-only. K3 is a
standalone alternative over fixed B, not a series applied after K1 or K2.

The source review passed, but no K3 compiler, runtime or timing has run.
source/SOURCE.json binds all 7726 public baseline files and the complete
per-variant overlays. Local strict patch replay reconstructed all three
source trees exactly. The build is minimally adapted from the executed K1
clean builder; complete adaptation diffs and original oracle/SQL hashes are
retained. Old frozen measurements and publication packets are unchanged.

Every build cleans and reuses the same owned source/build/configured-prefix
paths, stages its install with DESTDIR, and runs core239 plus posting-list
checks. No expected files are regenerated. GCC13.3, -O2 -g -fno-lto,
--without-icu --without-readline --with-openssl, nice10 and make -j2 are kept.
All 907 headers, source inventories, flags/configure, ELF hashes and actual
normal GIN objects/ASM are recorded. Release non-GIN backend object identity
is required. The script stops its own regression clusters in finally.

Proposed new remote root is /home/reshke/allfuzz/gin-cache-k3-20261110.
Core ports are 46140..46143; posting-list ports 46170..46173. The later ordinary
gate uses 46200+. Four builds should take roughly 15–20 minutes on the leased
8 logical/4 core VM, with no performance job overlapping. Allow roughly 10 GB for
builds, installed trees and later synthetic clones. Actual status/elapsed
will replace this estimate; a new full matrix is not launched automatically.

The already verified immutable public B72 source archive may be read from
/home/reshke/allfuzz/gin-next-c11-bitmap-20261110/inputs/baseline.tar.gz,
SHA256 8c074fcf94a17d381e2df4a2b0554b925d76a777acb7e2f8a508abe7dfd2bbc4.
No old source tree, prefix, header, ELF or PGDATA is reused as a matched build.
A new host may instead use --git with an existing local repository containing
exact B72; the script performs local git archive with network disabled.

```sh
ROOT=/home/reshke/allfuzz/gin-cache-k3-20261110
python3 -B "$ROOT/inputs/build-harness/build.py" \
  --source-archive /home/reshke/allfuzz/gin-next-c11-bitmap-20261110/inputs/baseline.tar.gz \
  --source-plan "$ROOT/inputs/source/SOURCE.json" \
  --output "$ROOT/build-r1" --core-port 46140
```

The separate gate overlay will preserve all original SQL, native-vector and
VOLATILE generic-fallback oracles byte-for-byte and add a distinct actual-
dispatch helper for 63/64/65 misses, hit reset, >64 cumulative interleaved
misses, permanent direct dispatch, fresh keys and hidden-entry bounds. It
must be independently reviewed and frozen before use. No timing is part of
this build-only capsule and no dense-regression repair is claimed yet.
