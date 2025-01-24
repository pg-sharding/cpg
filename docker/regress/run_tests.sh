#!/bin/bash
set -ex

sed -i  '/mdb-related/,$d' src/test/regress/input/misc.source src/test/regress/output/misc.source src/test/regress/sql/misc.sql

make check-world
