# C11 fullclean build preparation

Five serial fresh fullclean B/C9/C10/C11 release+C11_assert builds, make-j2/nice10, identical source/build/compiled-prefix paths and separate DESTDIR. Exact source snapshots and full7726baseline manifest are checked. Each runs original core239 and test_ginpostinglist, installs intarray/pageinspect/amcheck/pg_trgm, captures normal actual GIN objects and907headers. Non-GIN backend object bytes must match B across releases. No reuse of old objects or installs; no timing from build driver.

```sh
nice -n10 python3 build-harness/build.py --source-archive baseline.tar.gz --output /home/reshke/allfuzz/gin-next-c11-bitmap-20261110/build --core-port 45340
```

Existing public C11 commit ca6ad39111cd67f20ff2dd3a8f619239d0360a10 is unchanged. Shared prerequisite is treated identically and opaquely in all source trees. B72 raw72b9498d; fixed B8a8c4750; C90ab3bd65; C10cf6df206. Build dependencies/flags match the completed gin-tid-key campaign: GCC13.3, GNUmake, Python3, Bison/Flex, OpenSSL/zlib headers, binutils; -O2 -g -fno-lto, assertions only finalbuild, ICU/readlineoff/OpenSSLon. Coreports45340..44, postinglist45370..74. Qualification and timed screen require separate reviewed inputs and actual buildPASS. Estimated15–25min build, not a runtime guarantee. No perf or unrelated workload.
