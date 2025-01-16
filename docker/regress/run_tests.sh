#!/bin/bash

set -ex

cd /home/build-user

CFLAGS="" ./configure --prefix=/home/build-user/pgbin  --without-mdblocales  --enable-depend --enable-cassert --enable-debug --enable-tap-tests

make -j8 install
sed -i  '/mdb-related/,$d' src/test/regress/input/misc.source src/test/regress/output/misc.source src/test/regress/sql/misc.sql

make check
