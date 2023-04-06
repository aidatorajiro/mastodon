# syntax=docker/dockerfile:1.4
# This needs to be bullseye-slim because the Ruby image is built on bullseye-slim
ARG NODE_VERSION="16.18.1-bullseye-slim"

FROM ghcr.io/moritzheiber/ruby-jemalloc:3.0.6-slim as ruby
FROM node:${NODE_VERSION} as build

COPY --link --from=ruby /opt/ruby /opt/ruby

ENV DEBIAN_FRONTEND="noninteractive" \
    PATH="${PATH}:/opt/ruby/bin"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /opt/mastodon
COPY Gemfile* package.json yarn.lock /opt/mastodon/

# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential \
        ca-certificates \
        git \
        libicu-dev \
        libidn11-dev \
        libpq-dev \
        libjemalloc-dev \
        zlib1g-dev \
        libgdbm-dev \
        libgmp-dev \
        libssl-dev \
        libyaml-0-2 \
        ca-certificates \
        libreadline8 \
        python3 \
        shared-mime-info && \
    bundle config set --local deployment 'true' && \
    bundle config set --local without 'development test' && \
    bundle config set silence_root_warning true && \
    bundle install -j"$(nproc)" && \
    yarn install --pure-lockfile --network-timeout 600000

FROM node:${NODE_VERSION}

ARG UID="991"
ARG GID="991"

COPY --link --from=ruby /opt/ruby /opt/ruby

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN gem install bundler

RUN apt install -y redsocks iptables sudo curl dnsutils

# RUN VERSION=$(curl -s https://api.github.com/repos/AdguardTeam/dnsproxy/releases/latest | grep tag_name | cut -d '"' -f 4) && \
#	echo "Latest AdguardTeam dnsproxy version is $VERSION" && \
#	wget -O dnsproxy.tar.gz "https://github.com/AdguardTeam/dnsproxy/releases/download/${VERSION}/dnsproxy-linux-amd64-${VERSION}.tar.gz"

# RUN mkdir dnsproxy-unpack && mv dnsproxy.tar.gz dnsproxy-unpack &&\
#	cd dnsproxy-unpack && tar -xzvf dnsproxy.tar.gz &&\
#	cd linux-amd64 && mv dnsproxy /usr/bin/dnsproxy

ENV DEBIAN_FRONTEND="noninteractive" \
    PATH="${PATH}:/opt/ruby/bin:/opt/mastodon/bin"

# Ignoreing these here since we don't want to pin any versions and the Debian image removes apt-get content after use
# hadolint ignore=DL3008,DL3009
RUN apt-get update && \
    echo "Etc/UTC" > /etc/localtime && \
    groupadd -g "${GID}" mastodon && \
    useradd -l -u "$UID" -g "${GID}" -m -d /opt/mastodon mastodon && \
    apt-get -y --no-install-recommends install whois \
        wget \
        procps \
        libssl1.1 \
        libpq5 \
        imagemagick \
        ffmpeg \
        libjemalloc2 \
        libicu67 \
        libidn11 \
        libyaml-0-2 \
        file \
        ca-certificates \
        tzdata \
        libreadline8 \
        tini && \
    ln -s /opt/mastodon /mastodon

COPY --chown=mastodon:mastodon . /opt/mastodon
COPY --chown=mastodon:mastodon --from=build /opt/mastodon /opt/mastodon

ENV RAILS_ENV="production" \
    NODE_ENV="production" \
    RAILS_SERVE_STATIC_FILES="true" \
    BIND="0.0.0.0"

RUN echo "sh /bin/redsocks_prepare_sync.sh" > /bin/redsocks_prepare.sh

RUN echo "mastodon ALL=(root) NOPASSWD: /bin/redsocks_prepare.sh" >> /etc/sudoers

RUN chmod +x /bin/redsocks_prepare.sh

# Set the run user
USER mastodon
WORKDIR /opt/mastodon

# Precompile assets
RUN OTP_SECRET=precompile_placeholder SECRET_KEY_BASE=precompile_placeholder rails assets:precompile && \
    yarn cache clean

# Set the work dir and the container entry point
ENTRYPOINT ["/usr/bin/tini", "--"]
EXPOSE 3000 4000
