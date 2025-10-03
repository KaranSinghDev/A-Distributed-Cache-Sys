import sys
import os
import asyncio
import grpc
import random
import time
import uuid
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), 'generated'))
from generated import cache_pb2
from generated import cache_pb2_grpc

# --- Benchmark Configuration ---
# Addresses for connecting from the HOST machine (your terminal)
NODE_ADDRESSES = ["localhost:50051", "localhost:50052", "localhost:50053"]

# Total number of operations to perform for each benchmark
TOTAL_OPERATIONS = 20000

# Number of concurrent clients to simulate
CONCURRENCY = 50

# Size of the keys and values in bytes
KEY_SIZE = 16
VALUE_SIZE = 128

# --- Helper Functions ---
def print_header(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def print_stats(label, latencies_ms, duration_s, total_ops, errors):
    """Calculates and prints a full suite of performance statistics."""
    if not latencies_ms:
        print(f"\n--- {label} Results ---")
        print("  No successful operations recorded.")
        return

    p50 = np.percentile(latencies_ms, 50)
    p95 = np.percentile(latencies_ms, 95)
    p99 = np.percentile(latencies_ms, 99)
    avg = np.mean(latencies_ms)
    throughput = total_ops / duration_s

    print(f"\n--- {label} Results ---")
    print(f"Throughput: {throughput:,.0f} ops/sec")
    print(f"Latency Distribution:")
    print(f"  - Avg: {avg:.4f} ms")
    print(f"  - p50 (Median): {p50:.4f} ms")
    print(f"  - p95: {p95:.4f} ms")
    print(f"  - p99: {p99:.4f} ms")
    print(f"Errors: {errors}")

# --- Worker Logic ---
async def worker(worker_id, ops_queue, results_list, error_count):
    """A single asynchronous client worker."""
    node_address = random.choice(NODE_ADDRESSES)
    latencies = []
    errors = 0
    try:
        async with grpc.aio.insecure_channel(node_address) as channel:
            stub = cache_pb2_grpc.CacheServiceStub(channel)
            while not ops_queue.empty():
                op_type, key, value = await ops_queue.get()
                
                start_time = time.perf_counter()
                try:
                    if op_type == 'SET':
                        await stub.Set(cache_pb2.SetRequest(key=key, value=value))
                    elif op_type == 'GET':
                        await stub.Get(cache_pb2.GetRequest(key=key))
                    
                    end_time = time.perf_counter()
                    latencies.append((end_time - start_time) * 1000)
                except grpc.aio.AioRpcError:
                    errors += 1
                ops_queue.task_done()
    except Exception:
        # Catch connection errors etc.
        errors += ops_queue.qsize()

    results_list.extend(latencies)
    error_count[worker_id] = errors

# --- Main Benchmark Orchestrator ---
async def run_benchmark():
    print_header("Concurrent Key-Value Store Benchmark")
    print(f"Configuration: {CONCURRENCY} concurrent clients, {TOTAL_OPERATIONS:,} total operations")

    # --- SET Benchmark ---
    ops_queue = asyncio.Queue()
    keys_to_get = []
    for _ in range(TOTAL_OPERATIONS):
        key = uuid.uuid4().hex[:KEY_SIZE]
        keys_to_get.append(key)
        value = os.urandom(VALUE_SIZE)
        await ops_queue.put(('SET', key, value))

    set_latencies = []
    set_errors = [0] * CONCURRENCY
    start_time = time.perf_counter()
    worker_tasks = [
        asyncio.create_task(worker(i, ops_queue, set_latencies, set_errors))
        for i in range(CONCURRENCY)
    ]
    await asyncio.gather(*worker_tasks)
    end_time = time.perf_counter()
    print_stats("SET Benchmark", set_latencies, end_time - start_time, TOTAL_OPERATIONS, sum(set_errors))

    # --- GET Benchmark ---
    for key in keys_to_get:
        await ops_queue.put(('GET', key, None))
    
    get_latencies = []
    get_errors = [0] * CONCURRENCY
    start_time = time.perf_counter()
    worker_tasks = [
        asyncio.create_task(worker(i, ops_queue, get_latencies, get_errors))
        for i in range(CONCURRENCY)
    ]
    await asyncio.gather(*worker_tasks)
    end_time = time.perf_counter()
    print_stats("GET Benchmark (Hot Cache)", get_latencies, end_time - start_time, TOTAL_OPERATIONS, sum(get_errors))


if __name__ == '__main__':
    # This benchmark must be run against a live, running cluster.
    print("Starting benchmark in 3 seconds... Ensure your docker-compose cluster is up.")
    time.sleep(3)
    asyncio.run(run_benchmark())