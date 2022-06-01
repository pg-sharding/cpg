#!/usr/bin/env bash

export DEBIAN_FRONTEND=noninteractive
export TZ=Europe/Moskow
sudo bash -c "echo $TZ > /etc/timezone"

cd /home/build-user

sudo ./docker/tzdata.sh

cat debian/changelog

sudo mk-build-deps  --build-dep --install --tool='apt-get -o Debug::pkgProblemResolver=yes --no-install-recommends --yes' debian/control

dpkg-buildpackage -us -uc

cd /home
rm -fr build-user

