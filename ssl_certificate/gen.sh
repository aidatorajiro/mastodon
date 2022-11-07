cat ssl.conf.temp | sed "s/<<<domain name>>>/`cat ../tor_docker/hidden_service/hostname`/" > ssl.conf

openssl req -config ssl.conf -new -x509 -sha512 -newkey rsa:4096 -nodes \
    -keyout privatekey.pem -days 365 -out certificate.pem

rm ssl.conf