FROM ubuntu:bionic

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Moskow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN sed -i 's/archive.ubuntu.com/mirror.yandex.ru/g' /etc/apt/sources.list &&\
    apt-get update && apt-get install -y --no-install-recommends \
    sudo build-essential \
    gcc lsb-release libssl-dev gnupg openssl \
    gdb git \
    libpam0g-dev \
    debhelper debootstrap devscripts make equivs debhelper-compat \
    libz-dev flex libicu-dev libio-pty-perl libipc-run-perl libkrb5-dev \
    libldap2-dev liblz4-dev libperl-dev libreadline-dev libselinux1-dev \
    libsystemd-dev libxml2-dev libxml2-utils libxslt1-dev \
    pkg-config python3-dev systemtap-sdt-dev tcl-dev uuid-dev xsltproc zlib1g-dev \
    bison dh-exec docbook-xml docbook-xsl

RUN echo 'deb http://dist.yandex.ru/mdb-bionic-secure stable/all/' | tee -a /etc/apt/sources.list &&\
    echo 'deb http://dist.yandex.ru/mdb-bionic-secure stable/amd64/' | tee -a /etc/apt/sources.list &&\
    apt-get update -o Acquire::AllowInsecureRepositories=true &&\
    apt-get install -y --no-install-recommends --allow-unauthenticated libmdblocales1 libmdblocales-dev

RUN groupadd -g 999 build-user && \
    useradd -r -u 999 -g build-user build-user

COPY . /home/build-user
RUN chown build-user:build-user /home -R && usermod -aG sudo build-user

RUN echo 'build-user ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

USER build-user

ENTRYPOINT ["/home/build-user/docker/entrypoint.sh"]
