FROM ubuntu:bionic

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Moskow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN sed -i 's/archive.ubuntu.com/mirror.yandex.ru/g' /etc/apt/sources.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    sudo build-essential \
    gcc lsb-release libssl-dev gnupg openssl \
    gdb git

RUN echo 'deb http://dist.yandex.ru/mdb-bionic-secure stable/all/' >> /etc/apt/sources.list
RUN echo 'deb http://dist.yandex.ru/mdb-bionic-secure stable/$(ARCH)/' >> /etc/apt/sources.list

RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 7FCD11186050CD1A && apt-get update && apt-get install -y --no-install-recommends \
    sudo build-essential \
    gcc lsb-release libssl-dev gnupg openssl \
    gdb git \
    libpam0g-dev \
    debhelper debootstrap devscripts make equivs debhelper-compat \
    libz-dev flex libicu-dev libio-pty-perl libipc-run-perl libkrb5-dev \
    libldap2-dev liblz4-dev liblz4-tool postgresql-client-common=242-2-pgdg18.04+1+yandex220 postgresql-common=242-2-pgdg18.04+1+yandex220 zstd libperl-dev libreadline-dev libselinux1-dev llvm-dev \
    libsystemd-dev libxml2-dev libxml2-utils libxslt1-dev \
    pkg-config python3-dev systemtap-sdt-dev tcl-dev uuid-dev xsltproc zlib1g-dev \
    bison dh-exec docbook-xml docbook-xsl

RUN groupadd -g 999 build-user && \
    useradd -r -u 999 -g build-user build-user

COPY . /home/build-user
RUN chown build-user:build-user /home -R && usermod -aG sudo build-user

RUN echo 'build-user ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

USER build-user

ENTRYPOINT ["/home/build-user/docker/entrypoint.sh"]
