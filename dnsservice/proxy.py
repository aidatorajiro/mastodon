# Original Source Code taken from https://github.com/paulc/dnslib/blob/master/dnslib/proxy.py
# Commit ID 619f99bb34bba272a35b6f877cc20fdc98042431
#
# The Liscence of Original Source Code is as below:
#
# Copyright (c) 2010 - 2017 Paul Chakravarti.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# -*- coding: utf-8 -*-

from __future__ import print_function

import binascii, socket, struct

import dnslib
from dnslib import DNSRecord, RCODE, QTYPE, DNSLabel
from dnslib.server import DNSServer, DNSHandler, BaseResolver, DNSLogger

LOCAL_NAMES = ["tor", "db", "redis", "web", "streaming", "sidekiq", "postfix", "nginx", "dnsservice"]

class ProxyResolver(BaseResolver):
    """
        Proxy resolver - passes all requests to upstream DNS server and
        returns response
        Note that the request/response will be each be decoded/re-encoded
        twice:
        a) Request packet received by DNSHandler and parsed into DNSRecord
        b) DNSRecord passed to ProxyResolver, serialised back into packet
           and sent to upstream DNS server
        c) Upstream DNS server returns response packet which is parsed into
           DNSRecord
        d) ProxyResolver returns DNSRecord to DNSHandler which re-serialises
           this into packet and returns to client
        In practice this is actually fairly useful for testing but for a
        'real' transparent proxy option the DNSHandler logic needs to be
        modified (see PassthroughDNSHandler)
    """

    def __init__(self, address_local, port_local, address_tor, port_tor, address_surface, port_surface, timeout=0, strip_aaaa=False):
        self.address_local = address_local
        self.port_local = port_local
        self.address_tor = address_tor
        self.port_tor = port_tor
        self.address_surface = address_surface
        self.port_surface = port_surface
        self.timeout = timeout
        self.strip_aaaa = strip_aaaa

    def resolve(self, request: DNSRecord, handler):
        try:
            if self.strip_aaaa and request.q.qtype == QTYPE.AAAA:
                reply = request.reply()
                reply.header.rcode = RCODE.NXDOMAIN
            else:
                label: DNSLabel = request.q.qname

                if label in LOCAL_NAMES:
                    address = self.address_local
                    port = self.port_local

                    print("Use Local")
                elif label.matchGlob("*.onion"):
                    address = self.address_tor
                    port = self.port_tor

                    if request.q.qtype == QTYPE.MX:
                        print("Return dummy MX")
                        reply = request.reply()
                        reply.add_answer(*dnslib.RR.fromZone("mailserver." + str(label) + " 60 IN MX 10 " + str(label)))
                        return reply

                    print("Use Tor")
                else:
                    address = self.address_surface
                    port = self.port_surface
                    print("Use Surface")

                if handler.protocol == 'udp':
                    proxy_r = request.send(address, port,
                                           timeout=self.timeout)
                else:
                    proxy_r = request.send(address, port,
                                           tcp=True, timeout=self.timeout)
                
                reply = DNSRecord.parse(proxy_r)
        except socket.timeout:
            reply = request.reply()
            reply.header.rcode = getattr(RCODE, 'NXDOMAIN')

        return reply

class PassthroughDNSHandler(DNSHandler):
    """
        Modify DNSHandler logic (get_reply method) to send directly to
        upstream DNS server rather then decoding/encoding packet and
        passing to Resolver (The request/response packets are still
        parsed and logged but this is not inline)
    """

    def get_reply(self, data):
        request = DNSRecord.parse(data)
        self.server.logger.log_request(self, request)

        label: DNSLabel = request.q.qname
        if label.matchGlob("*.onion"):
            address = self.server.resolver.address_tor
            port = self.server.resolver.port_tor
            print("Use Tor")
        else:
            address = self.server.resolver.address_surface
            port = self.server.resolver.port_surface
            print("Use Surface")

        if self.protocol == 'tcp':
            data = struct.pack("!H", len(data)) + data
            response = send_tcp(data, address, port)
            response = response[2:]
        else:
            response = send_udp(data, address, port)

        reply = DNSRecord.parse(response)
        self.server.logger.log_reply(self, reply)

        return response


def send_tcp(data, host, port):
    """
        Helper function to send/receive DNS TCP request
        (in/out packets will have prepended TCP length header)
    """
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        sock.sendall(data)
        response = sock.recv(8192)
        length = struct.unpack("!H", bytes(response[:2]))[0]
        while len(response) - 2 < length:
            response += sock.recv(8192)
        return response
    finally:
        if (sock is not None):
            sock.close()


def send_udp(data, host, port):
    """
        Helper function to send/receive DNS UDP request
    """
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(data, (host, port))
        response, server = sock.recvfrom(8192)
        return response
    finally:
        if (sock is not None):
            sock.close()


if __name__ == '__main__':
    import argparse, sys, time

    p = argparse.ArgumentParser(description="DNS Proxy")
    p.add_argument("--port", "-p", type=int, default=53,
                   metavar="<port>",
                   help="Local proxy port (default:53)")
    p.add_argument("--address", "-a", default="",
                   metavar="<address>",
                   help="Local proxy listen address (default:all)")
    p.add_argument("--upstream_local", default="172.12.34.56:53",
                   metavar="<dns server:port>",
                   help="Local Upstream DNS server:port. For local lookup domains. (default:172.12.34.56:53)")
    p.add_argument("--upstream_tor", default="127.0.0.1:53",
                   metavar="<dns server:port>",
                   help="Tor Upstream DNS server:port. For .onion domains. (default:127.0.0.1:53)")
    p.add_argument("--upstream_surface", default="8.8.8.8:53",
                   metavar="<dns server:port>",
                   help="Surface Upstream DNS server:port. For normal internet domains. (default:8.8.8.8:53)")
    p.add_argument("--tcp", action='store_true', default=False,
                   help="TCP proxy (default: UDP only)")
    p.add_argument("--timeout", "-o", type=float, default=5,
                   metavar="<timeout>",
                   help="Upstream timeout (default: 5s)")
    p.add_argument("--strip-aaaa", action='store_true', default=False,
                   help="Retuen NXDOMAIN for AAAA queries (default: off)")
    p.add_argument("--passthrough", action='store_true', default=False,
                   help="Dont decode/re-encode request/response (default: off)")
    p.add_argument("--log", default="request,reply,truncated,error",
                   help="Log hooks to enable (default: +request,+reply,+truncated,+error,-recv,-send,-data)")
    p.add_argument("--log-prefix", action='store_true', default=False,
                   help="Log prefix (timestamp/handler/resolver) (default: False)")
    args = p.parse_args()

    args.dns_local, _, args.dns_port_local = args.upstream_local.partition(':')
    args.dns_port_local = int(args.dns_port_local or 53)

    args.dns_tor, _, args.dns_port_tor = args.upstream_tor.partition(':')
    args.dns_port_tor = int(args.dns_port_tor or 53)

    args.dns_surface, _, args.dns_port_surface = args.upstream_surface.partition(':')
    args.dns_port_surface = int(args.dns_port_surface or 53)

    print("Starting Proxy Resolver (%s:%d -> %s:%d %s:%d %s:%d) [%s]" % (
        args.address or "*", args.port,
        args.dns_local, args.dns_port_local,
        args.dns_tor, args.dns_port_tor,
        args.dns_surface, args.dns_port_surface,
        "UDP/TCP" if args.tcp else "UDP"))

    resolver = ProxyResolver(args.dns_local,
                             args.dns_port_local,
                             args.dns_tor,
                             args.dns_port_tor,
                             args.dns_surface,
                             args.dns_port_surface,
                             args.timeout,
                             args.strip_aaaa)

    handler = PassthroughDNSHandler if args.passthrough else DNSHandler
    logger = DNSLogger(args.log, prefix=args.log_prefix)
    udp_server = DNSServer(resolver,
                           port=args.port,
                           address=args.address,
                           logger=logger,
                           handler=handler)
    udp_server.start_thread()

    if args.tcp:
        tcp_server = DNSServer(resolver,
                               port=args.port,
                               address=args.address,
                               tcp=True,
                               logger=logger,
                               handler=handler)
        tcp_server.start_thread()

    while udp_server.isAlive():
        time.sleep(1)
