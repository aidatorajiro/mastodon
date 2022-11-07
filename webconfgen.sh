ONIONAME=`cat tor_docker/hidden_service/hostname`

cd ssl_certificate

cat ssl.conf.temp | sed "s/<<<domain name>>>/$ONIONAME/" > ssl.conf

openssl req -config ssl.conf -new -x509 -sha512 -newkey rsa:4096 -nodes \
    -keyout privatekey.pem -days 365 -out certificate.pem

rm ssl.conf

cd ../nginx

cat onionginx.conf.temp | sed "s/<<<domain name>>>/$ONIONAME/" > onionginx.conf

cd ../postfix

echo $ONIONAME > hostname

cat main.cf.temp | sed "s/<<<domain name>>>/$ONIONAME/" > main.cf

