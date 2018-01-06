#!/usr/bin/env python3.6

class LightningRPC:
    def __init__(self, host):
        self.host = host
        self.stub = None

    @retry(wait_exponential_multiplier=1000, wait_exponential_max=30000)
    def connect(self):
        print(f"Connecting to lnd on {self.host}")

        cert = open(os.path.expanduser(f'/rpc/lnd-{self.host}.cert')).read()
        creds = grpc.ssl_channel_credentials(bytes(cert, 'ascii'))

        channel = grpc.secure_channel(f'{self.host}:10009', creds)
        self.stub = lnrpc.LightningStub(channel)

        response = self.get_info()
        self.pubkey = response.identity_pubkey

    def get_info(self):
        return self.stub.GetInfo(ln.GetInfoRequest())

    def peered(self, other):
        lnd_address = ln.LightningAddress(pubkey=other.pubkey, host=other.host)
        peers = self.stub.ListPeers(ln.ListPeersRequest()).peers

        for peer in peers:
            if peer.pub_key == other.pubkey:
                return True
        return False

    def peer(self, other):
        if self.peered(other):
            print(f"{self.host} already peered with {other.host}")
        else:
            lnd_address = ln.LightningAddress(pubkey=other.pubkey, host=other.host)
            print(f"{self.host} attempting to peer with {other.host}")
            response = self.stub.ConnectPeer(ln.ConnectPeerRequest(addr=lnd_address, perm=True))

            confirmed = False
            while not other.peered(self):
                print(f"{self.host} waiting for {other.host} to confirm peering")
                time.sleep(1)
            print("Confirmed")

    @retry(wait_exponential_multiplier=100, wait_exponential_max=5000)
    def create_channel(self, other):
        if self.has_channel(other):
            print(f"{self.host} already has a channel to {other.host}")
        else:
            print(f"{self.host} opening channel to {other.host}")
            openChannelRequest = ln.OpenChannelRequest(node_pubkey_string=other.pubkey,
                    local_funding_amount=100000,
                    push_sat = 50000,
                    private = False)
            response = self.stub.OpenChannelSync(openChannelRequest)

    def nodeinfo(self, other):
        try:
            response = self.stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=other.pubkey))
            return response
        except grpc.RpcError as e:
            if isinstance(e, grpc.Call):
                if e.details() == "unable to find node":
                    return None
            raise e

    def has_channel(self, other):
        exists = False
        active = False
        for channel in self.list_channels():
            if channel.remote_pubkey == other.pubkey and channel.local_balance > 0:
                exists = True
                if channel.active:
                    active = True

        print(f"{self.host} has_channel {other.host} exists={exists}, active={active}")

        return exists and active

    def list_channels(self):
        return self.stub.ListChannels(ln.ListChannelsRequest()).channels

    def send_payment(self, dest, value, memo):
        invoice = ln.Invoice(value=value, memo=memo)

        print(invoice)
        response = dest.stub.AddInvoice(invoice)
        print(response)

        payment_request = response.payment_request

        payment = ln.SendRequest(dest_string=dest.pubkey,
                                 amt=invoice.value,
                                 payment_request=payment_request,
                                 payment_hash=response.r_hash)
        print(payment)

        response = self.stub.SendPaymentSync(payment)
        print(response)
        if response.payment_error:
            raise Exception(response.payment_error)

    def new_address(self, address_type='np2wkh'):
        type_map = {
            "p2wkh": ln.NewAddressRequest.WITNESS_PUBKEY_HASH,
            "np2wkh": ln.NewAddressRequest.NESTED_PUBKEY_HASH,
            "p2pkh": ln.NewAddressRequest.PUBKEY_HASH
        }

        request = ln.NewAddressRequest(type=type_map[address_type])

        response = self.stub.NewAddress(request)

        print(f"new address: '{str(response.address)}'")

        return response.address
        
    def wallet_balance(self):
        response = self.stub.WalletBalance(ln.WalletBalanceRequest())

        return {
            "total_balance": response.total_balance,
            "confirmed_balance": response.confirmed_balance,
            "unconfirmed_balance": response.unconfirmed_balance
        }

    def wait_for_block_height(self, height):
        info = self.get_info()
        current = self.get_info().block_height
        while current < height:
            print(f'Waiting for lnd node {self.host} ({current}) to reach {height}')
            time.sleep(1)
            current = self.get_info().block_height


print("lngraphd starting")

hub = LightningRPC('lnd_hub')
hub.connect()

print("lngraphd finished")
