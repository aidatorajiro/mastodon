FROM ubuntu:jammy

RUN apt update && apt install -y apt-transport-https lsb-release ca-certificates wget gnupg

RUN echo "deb     [signed-by=/usr/share/keyrings/tor-archive-keyring.gpg] https://deb.torproject.org/torproject.org <DISTRIBUTION> main" >> /etc/apt/sources.list.d/tor.list

RUN echo "deb-src [signed-by=/usr/share/keyrings/tor-archive-keyring.gpg] https://deb.torproject.org/torproject.org <DISTRIBUTION> main" >> /etc/apt/sources.list.d/tor.list

RUN sed -i "s/<DISTRIBUTION>/jammy/" /etc/apt/sources.list.d/tor.list

ADD A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89.asc .

RUN cat A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89.asc | gpg --dearmor | tee /usr/share/keyrings/tor-archive-keyring.gpg

RUN apt update && apt install -y tor deb.torproject.org-keyring obfs4proxy

ADD hidden_service /var/lib/tor/hidden_service

RUN chmod -R 700 /var/lib/tor/hidden_service

ENTRYPOINT [ "/bin/tor" ]