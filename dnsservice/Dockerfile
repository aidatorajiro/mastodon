FROM ubuntu:jammy

RUN apt update && apt install -y python3 python3-pip tini dnsutils redsocks iptables curl wget

RUN VERSION=$(curl -s https://api.github.com/repos/AdguardTeam/dnsproxy/releases/latest | grep tag_name | cut -d '"' -f 4) && \
    echo "Latest AdguardTeam dnsproxy version is $VERSION" && \
    wget -O dnsproxy.tar.gz "https://github.com/AdguardTeam/dnsproxy/releases/download/${VERSION}/dnsproxy-linux-amd64-${VERSION}.tar.gz"

RUN mkdir dnsproxy-unpack && mv dnsproxy.tar.gz dnsproxy-unpack &&\
    cd dnsproxy-unpack && tar -xzvf dnsproxy.tar.gz &&\
    cd linux-amd64 && mv dnsproxy /usr/bin/dnsproxy

RUN pip install dnslib

ENTRYPOINT ["/usr/bin/tini", "--"]
