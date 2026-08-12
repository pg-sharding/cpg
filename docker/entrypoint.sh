#!/usr/bin/env bash
set -ex

export DEBIAN_FRONTEND=noninteractive
export TZ=Europe/Moskow
sudo bash -c "echo $TZ > /etc/timezone"

cd /home/build-user

sudo ./docker/tzdata.sh

cat debian/changelog
export DEB_BUILD_OPTIONS="nocheck"

sudo dpkg-checkbuilddeps

sudo mk-build-deps  --build-dep --install --tool='apt-get -o Debug::pkgProblemResolver=yes --no-install-recommends --yes' debian/control
DEB_BUILD_OPTIONS="parallel=auto"
dpkg-buildpackage -b -rfakeroot -us -uc
#dpkg-buildpackage -us -uc

cd /home
rm -fr build-user

