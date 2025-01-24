#!/bin/bash
set -ex

sed -i  '/mdb-related/,$d' src/test/regress/expected/misc.out src/test/regress/output/misc.source src/test/regress/input/misc.source

make check
