#!/usr/bin/env python3

import grpc
import json
import os

from google.protobuf.json_format import MessageToJson

from retrying import retry

import lnd.rpc_pb2 as ln
import lnd.rpc_pb2_grpc as lnrpc

class LightningRPC:
    def __init__(self, host):
        self.host = host
        self.stub = None

    @retry(wait_exponential_multiplier=1000, wait_exponential_max=30000)
    def connect(self):
        try:
            print("Connecting to lnd on %s" % (self.host,))

            # cert = open(os.path.expanduser("/rpc/lnd-%s.cert" % (self.host,)).read())
            home = os.environ['HOME']
            cert = open(home + "/.lnd/tls.cert").read()
            creds = grpc.ssl_channel_credentials(bytes(cert, 'ascii'))

            channel = grpc.secure_channel("%s:10009" % (self.host,), creds)
            self.stub = lnrpc.LightningStub(channel)

            response = self.get_info()
            self.pubkey = response.identity_pubkey
        except Exception as ex:
            print(str(ex))

    def get_info(self):
        return self.stub.GetInfo(ln.GetInfoRequest())

    def describe_graph(self):
        return self.stub.DescribeGraph(ln.ChannelGraphRequest())


print("lngraphd starting")

lnd = LightningRPC('localhost')
lnd.connect()

graph = lnd.describe_graph()

json = MessageToJson(graph)

print(json)

print("lngraphd finished")
