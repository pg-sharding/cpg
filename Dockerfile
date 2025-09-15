ARG codename
FROM ubuntu:${codename:-bionic}

ARG codename
ENV CODE_NAME=${codename:-bionic}

ARG pgdg
ENV PGDG_VER=${pgdg:-242-2-pgdg18.04+1+yandex220}

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Moskow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN sed -i 's/archive.ubuntu.com/mirror.yandex.ru/g' /etc/apt/sources.list &&\
    apt-get update && apt-get install -y --no-install-recommends \
    sudo build-essential \
    gcc lsb-release libssl-dev gnupg openssl \
    gdb git curl gnupg

RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys FF5F4D0E27393420

RUN echo "deb http://dist.yandex.ru/mdb-${CODE_NAME}-secure stable/all/" >> /etc/apt/sources.list
RUN echo "deb http://dist.yandex.ru/mdb-${CODE_NAME}-secure stable/\$(ARCH)/" >> /etc/apt/sources.list

RUN curl -s 'http://keyserver.ubuntu.com/pks/lookup?op=get&search=0xafc3ce0d00e3c45a357e9e637fcd11186050cd1a' | \
    gpg --dearmour -o /etc/apt/trusted.gpg.d/yandex.gpg

RUN apt-get update && apt-get install -y --no-install-recommends \
    sudo build-essential \
    gcc lsb-release libssl-dev gnupg openssl \
    gdb git \
    libpam0g-dev \
    debhelper debootstrap devscripts make equivs debhelper-compat \
    libz-dev flex libicu-dev libio-pty-perl libipc-run-perl libkrb5-dev \
    libldap2-dev liblz4-dev liblz4-tool zstd libperl-dev libreadline-dev libselinux1-dev llvm-18-dev \
    libsystemd-dev libxml2-dev libxml2-utils libxslt1-dev \
    python3-dev systemtap-sdt-dev tcl-dev uuid-dev xsltproc zlib1g-dev \
    bison dh-exec docbook-xml docbook-xsl \
    clang-18 libcurl4-openssl-dev libnuma-dev liburing-dev libzstd-dev pkgconf tzdata
RUN apt-get install -y \
    libmdblocales1 libmdblocales-dev \
    postgresql-client-common=${PGDG_VER} \
    postgresql-common=${PGDG_VER} \
    postgresql-common-dev=${PGDG_VER}

RUN groupadd -g 999 build-user && \
    useradd -r -u 999 -g build-user build-user

COPY . /home/build-user
RUN chown build-user:build-user /home -R && usermod -aG sudo build-user

RUN echo 'build-user ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

USER build-user

ENTRYPOINT ["/home/build-user/docker/entrypoint.sh"]
