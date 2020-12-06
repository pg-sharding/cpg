FROM ubuntu:bionic

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Moskow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN sed -i 's/archive.ubuntu.com/mirror.yandex.ru/g' /etc/apt/sources.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    sudo build-essential \
    gcc lsb-release libssl-dev gnupg openssl \
    gdb git \
    libpam0g-dev \
    debhelper debootstrap devscripts make equivs

RUN groupadd -g 999 build-user && \
    useradd -r -u 999 -g build-user build-user

COPY . /home/build-user
RUN chown build-user:build-user /home -R && usermod -aG sudo build-user

RUN echo 'build-user ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

USER build-user

ENTRYPOINT ["/home/build-user/docker/entrypoint.sh"]
