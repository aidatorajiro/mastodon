FROM ubuntu:jammy

RUN apt update

RUN apt install -y postfix telnet dnsutils redsocks iptables curl wget tini

ADD hostname hostname

RUN cp hostname /etc/mailname

ENTRYPOINT [ "/usr/bin/tini", "--" ]