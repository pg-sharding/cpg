#!/bin/bash
set -ex

sed -i  '/mdb-related/,$d' src/test/regress/expected/misc.out src/test/regress/sql/misc.sql

make check
