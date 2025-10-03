import sys
import os
import asyncio
import grpc

sys.path.append(os.path.join(os.path.dirname(__file__), 'generated'))
from generated import cache_pb2
from generated import cache_pb2_grpc

from hash_ring import ConsistentHashRing

NODE_ADDRESSES = ["node1:50051", "node2:50052", "node3:50053"]
REPLICATION_FACTOR = 3

class CacheServiceServicer(cache_pb2_grpc.CacheServiceServicer):
    def __init__(self, my_address: str, all_nodes: list[str]):
        self.data = {}
        self.my_address = my_address
        self.ring = ConsistentHashRing(all_nodes)
        self.peer_stubs = {}
        print(f"[{self.my_address}] Servicer initialized.")

    async def _get_peer_stub(self, peer_address: str):
        if peer_address not in self.peer_stubs:
            channel = grpc.aio.insecure_channel(peer_address)
            self.peer_stubs[peer_address] = cache_pb2_grpc.CacheServiceStub(channel)
        return self.peer_stubs[peer_address]

    async def Set(self, request: cache_pb2.SetRequest, context) -> cache_pb2.SetResponse:
            key = request.key
            
            is_replication_request = any(k == 'is-replication' for k, v in context.invocation_metadata())

            # If this is ALREADY a replication request, just store locally and stop.
            if is_replication_request:
                self.data[key] = request.value
                return cache_pb2.SetResponse(success=True)

            # If this is the original request, coordinate the replication.
            target_nodes = self.ring.get_nodes(key, REPLICATION_FACTOR)
            # print(f"[{self.my_address}] Coordinating Set for key='{key}'. Replicating to {target_nodes}")
            
            tasks = []
            replication_metadata = [('is-replication', 'true')]

            for node in target_nodes:
                if node == self.my_address:
                    # If I am a target, I store it myself.
                    self.data[key] = request.value
                else:
                    # If it's a peer, create the coroutine/awaitable for the RPC call.
                    peer_stub = await self._get_peer_stub(node)
                    task = peer_stub.Set(request, metadata=replication_metadata) # THE FIX IS HERE
                    tasks.append(task)
            
            # Wait for all network replication tasks to complete.
            if tasks:
                await asyncio.gather(*tasks)
                
            return cache_pb2.SetResponse(success=True)

    async def Get(self, request: cache_pb2.GetRequest, context) -> cache_pb2.GetResponse:
        key = request.key
        value = self.data.get(key)
        if value is not None:
            return cache_pb2.GetResponse(value=value, found=True)
        else:
            return cache_pb2.GetResponse(found=False)

async def serve(address: str, all_nodes: list[str]):
    server = grpc.aio.server()
    cache_pb2_grpc.add_CacheServiceServicer_to_server(CacheServiceServicer(address, all_nodes), server)
    server.add_insecure_port(address)
    print(f"Starting server on {address}")
    await server.start()
    await server.wait_for_termination()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python server.py <node_address>")
        sys.exit(1)
        
    my_address = sys.argv[1]
    if my_address not in NODE_ADDRESSES:
        print(f"Error: Address '{my_address}' not in the known list of nodes.")
        sys.exit(1)
        
    asyncio.run(serve(my_address, NODE_ADDRESSES))