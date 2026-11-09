# Fresh matched IOS build front door

LOCAL STATIC PREPARATION ONLY. No build or Linux execution has run from this new script yet.

Minimal adaptation of the actually executed hash composition build/common scripts: B/V13/V14 release plus V14_assert, no hash fixture module, normal objects genam/nbtreadpage/nbtree/tableam_indexscan, pageinspect/pg_visibility/amcheck. Full source and build paths and compiled prefix are identical for all modes; each mode uses a fresh empty build directory and distinct install DESTDIR. B/T map to the exact same B ELF. Header ABI changes require full rebuild.

```sh
nice -n10 python3 build-harness/build.py --source-archive /absolute/baseline.tar.gz --source-plan /absolute/source/SOURCE.json --output /home/reshke/allfuzz/btree-ios-v14-campaign-20261109/build --core-port 40640
```

Root chooses a new nonexistent output; use GCC13.3, GNU make, Python3, Bison/Flex, OpenSSL/zlib development headers and objdump. Four serial fullclean builds, make -j2, CFLAGS=-O2 -g -fno-lto, LDFLAGS=-fno-lto, no assertions except final correctness build. Core239 each with MAX_CONNECTIONS=2; original expected files are never regenerated. Unchanged source archive must match all7726 pinned B72 files. No existing installed prefixes are changed. Need ~20GB free for build namespace, plus ~40GB later for SQL datasets; allow ~15-25min for four builds on prior VM scale, not a runtime guarantee. No timings launched automatically.

The later finite gate and19-case/two-cohort SQL campaign require their own reviewed frozen inputs and actual PASS receipts; this build script alone cannot establish correctness of the cache or performance.
