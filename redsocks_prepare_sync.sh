# https://superuser.com/questions/1401585/how-to-force-all-linux-apps-to-use-socks-proxy

redsocks -c /etc/redsocks.conf

# to reset:
# iptables -F
# iptables -t nat -F
# iptables -t mangle -F
# iptables -X

iptables -t nat -N REDSOCKS
iptables -t nat -A REDSOCKS -d 0.0.0.0/8 -j RETURN
# iptables -t nat -A REDSOCKS -d 10.0.0.0/8 -j RETURN
iptables -t nat -A REDSOCKS -d 10.0.0.0/10 -j RETURN # Redirect access to Tor's Virtual Network through SOCKS (so RETURN only some first part of 10.0.0.0/8. the rest (10.192.0.0/10) goes through redsocks)
iptables -t nat -A REDSOCKS -d 127.0.0.0/8 -j RETURN
iptables -t nat -A REDSOCKS -d 169.254.0.0/16 -j RETURN
iptables -t nat -A REDSOCKS -d 172.16.0.0/12 -j RETURN
iptables -t nat -A REDSOCKS -d 192.168.0.0/16 -j RETURN
iptables -t nat -A REDSOCKS -d 224.0.0.0/4 -j RETURN
iptables -t nat -A REDSOCKS -d 240.0.0.0/4 -j RETURN
iptables -t nat -A REDSOCKS -p tcp -j REDIRECT --to-ports 12345
iptables -t nat -A OUTPUT -p tcp -j REDSOCKS
iptables -t nat -A PREROUTING -p tcp -j REDSOCKS

if test -d /var/spool/postfix/etc; then
  dnsproxy -l 127.0.0.1 -p 53 -u https://8.8.8.8/dns-query &
  echo "nameserver 127.0.0.1" >> /etc/resolv.conf
  cp /etc/resolv.conf /var/spool/postfix/etc/resolv.conf
  postalias /etc/aliases
else
  echo "nameserver $(dig +short tor)" >> /etc/resolv.conf
fi

#iptables -t nat -A REDSOCKS -p udp -j REDIRECT --to-ports 10053
#iptables -t nat -A OUTPUT -p udp -j REDSOCKS
#iptables -t nat -A PREROUTING -p udp -j REDSOCKS