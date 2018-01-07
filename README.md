
# Lightning Graph Daemon

Setup
----------------------------------------------------------------

    sudo pip3 install --no-cache-dir -r requirements.txt

    sudo python3 -m grpc_tools.protoc --proto_path=vendor --python_out=. --grpc_python_out=. vendor/lnd/rpc.proto

