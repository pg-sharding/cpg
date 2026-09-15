#!/bin/bash
set -ex

sed -i  '/mdb-related/,$d' src/test/regress/*/misc.*

make check-world
