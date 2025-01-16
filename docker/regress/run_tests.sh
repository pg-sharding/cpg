#!/bin/bash

set -ex

cd /home/build-user

CFLAGS="" ./configure --prefix=/home/build-user/pgbin  --without-mdblocales  --enable-depend --enable-cassert --enable-debug --enable-tap-tests

make -j8 install

make check
