# D2 matched decoder build inputs

This builds B, D1, D2 and D2_assert serially from authentic raw B72
72b9498df9a369e747f8d96efb5a6cd33c2451e2. B is fixed B
8a8c475037bfde101da23cc9b0364c9c020eca93; D1 is canonical
c2b5dd6f9012cc4a27628c9d6c507ac467795ac5 and D2 is
 a85a9242f455b12c93528f3ace33eb69b6cd1008. D1 and D2 are independent
alternatives over fixed B, with no S1/C9/cache changes. Their common prerequisite
is identical. The D2 source snapshot SHA256 for ginpostinglist.c is
0235eb70b0d860fed7e41476074b93617ed7013ac5af00856faffd60ab956705.

The tested startup-decoder builder is copied into a new owned namespace. Each
variant gets a fresh clean build in the same common-source/common-build/configured
prefix paths, with separate DESTDIR installations. Expected core/posting-list
files are unchanged. All four builds must pass core239 and posting-list tests.
The release object gate permits changes only in access/gin/ginpostinglist.o.
Source inventories, 907 installed headers, full installs, ELF hashes, compiler
flags and actual normal full-TU ASM for ginget/ginscan/ginpostinglist are saved.
B/T will refer to the exact same B ELF in a later separately reviewed timing stage.

Use GCC -O2 -g -fno-lto, LDFLAGS=-fno-lto, ICU/readline off, OpenSSL on;
pageinspect/intarray/amcheck/pg_trgm are installed for the unchanged fixture.
Python3, Git, make, binutils, GCC, Perl, Bison/Flex and OpenSSL development files
must already exist. No package installation is part of this capsule.
The parent and all children have a 3,000,000,000-byte address-space cap and nice10;
make is fixed -j2. Existing data, prefixes and foreign processes remain untouched.
Before any owned regression cleanup signal, the live PID/ownUID/backend ELF and
resolved -D directory must match this new build namespace.

After parent review, the intended build-only command on VM158 is:

```sh
R=/home/reshke/allfuzz/gin-dec-d2-20261111
python3 -B "$R/inputs/build-harness/build.py" \
 --source-archive /path/to/already-present/authentic-B72.tar.gz \
 --source-plan "$R/inputs/build-source/SOURCE.json" \
 --output "$R/build-r1" --core-port 46900
```

The known authentic gzip SHA256 is
8c074fcf94a17d381e2df4a2b0554b925d76a777acb7e2f8a508abe7dfd2bbc4.
The importer checks that full hash, while the builder independently checks all
7,726 baseline files. `--git /existing/B72/repository` is the alternative builder
input and performs no network access; its exact Git archive is verified by the
same complete source manifest. No baseline archive is distributed in this text
capsule and no archive is read from VM51. Core ports are46900..46903 and posting
ports46930..46933. Runtime ports46960..46964 belong to a later qualification overlay.

Local BUILD-STATIC-r1.json is actual strict source replay/AST/help evidence only.
No compiler, backend, correctness gate or timing ran during preparation. Failed
attempts are retained and never retried automatically. Qualification and timing
are separate; this build script cannot launch a benchmark or claim D2 repairs
D1's long-delta regression.
