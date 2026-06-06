#!/usr/bin/env bash
set -ex

export DEBIAN_FRONTEND=noninteractive
export TZ=Europe/Moskow
sudo bash -c "echo $TZ > /etc/timezone"

cd /home/build-user

cat /usr/share/postgresql-common/server/postgresql.mk
echo HUI

sudo ./docker/tzdata.sh

cat debian/changelog
export DEB_BUILD_OPTIONS="nocheck"
export DEB_BUILD_OPTIONS=nostrip
export DEB_BUILD_QUIET=0 

sudo dpkg-checkbuilddeps

sudo mk-build-deps  --build-dep --install --tool='apt-get -o Debug::pkgProblemResolver=yes --no-install-recommends --yes' debian/control

dpkg-buildpackage -b -rfakeroot -us -uc
#dpkg-buildpackage -us -uc

cd /home
rm -fr build-user

