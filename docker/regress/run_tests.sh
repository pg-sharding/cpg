#!/bin/bash

set -ex

cd /home/build-user

CFLAGS="" ./configure --prefix=/home/build-user/pgbin  --without-mdblocales  --enable-depend --enable-cassert --enable-debug --enable-tap-tests

make -j8
sed -i  '/mdb-related/,$d' src/test/regress/expected/misc.out src/test/regress/output/misc.source src/test/regress/input/misc.source

make check
