#!/bin/bash

export PACKAGE_NAME=postgresql-16
export BUILD_USER=mdb-cc
export VERSION=$(grep 'PACKAGE_VERSION=' configure | cut -d= -f2 | sed s/\'//g)-201-yandex.$(git rev-list HEAD --count).$(git rev-parse --short HEAD)
export LC_ALL=C

cat > debian/changelog<<EOH
${PACKAGE_NAME} ($VERSION) stable; urgency=low

  * Yandex autobuild

 -- ${BUILD_USER} <${BUILD_USER}@yandex-team.ru>  $(date +'%a, %d %b %Y %H:%M:%S %z')
EOH

echo "VERSION=$VERSION" > version.properties

