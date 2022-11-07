FROM ubuntu:jammy

RUN apt update

RUN apt install -y postfix telnet dnsutils redsocks iptables curl wget tini

RUN VERSION=$(curl -s https://api.github.com/repos/AdguardTeam/dnsproxy/releases/latest | grep tag_name | cut -d '"' -f 4) && \
    echo "Latest AdguardTeam dnsproxy version is $VERSION" && \
    wget -O dnsproxy.tar.gz "https://github.com/AdguardTeam/dnsproxy/releases/download/${VERSION}/dnsproxy-linux-amd64-${VERSION}.tar.gz"

RUN mkdir dnsproxy-unpack && mv dnsproxy.tar.gz dnsproxy-unpack &&\
    cd dnsproxy-unpack && tar -xzvf dnsproxy.tar.gz &&\
    cd linux-amd64 && mv dnsproxy /usr/bin/dnsproxy

ADD hostname hostname

RUN cp hostname /etc/mailname

ADD main.cf /etc/postfix/main.cf

RUN sed -i "s/<<<thisismyhostname>>>/`cat /etc/mailname`/" /etc/postfix/main.cf

ENTRYPOINT [ "/usr/bin/tini", "--" ]