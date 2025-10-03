# Python Distributed Key-Value Store

Based on the reasearch of foundational distributed systems like Amazon's DynamoDB and Redis Cluster, I wanted to move beyond theory and implement the core principles of resilience and scale myself. This project is the result: a fault-tolerant key-value store built from scratch to explore how systems can guarantee data safety in the face of network and server failures.
To make this, I implemented the two fundamental methods: consistent hashing for data partitioning and N-way replication for data safety. The system's resilience is validated by an automated chaos test that proves it can withstand sudden node outages without data loss.

This project is a fault-tolerant, distributed key-value store built from scratch in Python. It is a deep dive into the principles of distributed systems, focusing on high availability, data partitioning, and modern, high-concurrency backend design.

The system operates as a cluster of nodes that replicate data to survive failures, partition data using consistent hashing, and communicate using high-performance gRPC.

## Key Features & Architectural Highlights

- **Distributed & Fault-Tolerant:** The system is designed to run as a multi-node cluster, with N-way replication ensuring data safety and high availability.
- **Asynchronous from the Ground Up:** Built entirely on Python's asyncio framework to handle thousands of concurrent client connections with high throughput.
- **Consistent Hashing:** Implemented for intelligent data partitioning, allowing the cluster to scale horizontally while minimizing data re-shuffling.
- **High-Performance Networking:** Uses gRPC and Protocol Buffers for a strongly-typed API contract and low-latency internal communication.
- **Proven Resilience:** Includes an automated "chaos test" to validate the system's fault tolerance by actively terminating nodes and verifying data integrity.
- **Fully Containerized:** The entire multi-node cluster is defined and orchestrated with Docker and Docker Compose for one-command deployment.

## Performance Benchmarks

Benchmarks were run against a 3-node cluster, simulating a high-concurrency workload of 50 simultaneous clients.

| Metric            | Result            | Analysis                                                                                                           |
|-------------------|-------------------|--------------------------------------------------------------------------------------------------------------------|
| GET Throughput    | ~17,000 ops/sec   | Demonstrates the efficiency of the asyncio architecture for I/O-bound workloads.                                  |
| GET Latency (p99) | < 6 ms            | Shows that 99% of read requests completed in under 6 milliseconds, even under heavy concurrent load.             |
| SET Throughput    | ~3,500 ops/sec    | Reflects the necessary trade-off for fault tolerance, as each SET is coordinated and replicated across the cluster.|
| Data Safety       | Zero Data Loss    | Validated via an automated chaos test where nodes were randomly terminated during operation.                      |

## System Architecture

Each node in the cluster is identical. When a client sends a request to any node, that node acts as a coordinator. It uses a consistent hash ring to identify the N nodes responsible for the key and then manages the replication or retrieval of the data.

``` mermaid

graph TD
    Client([Client])
    
    subgraph "Distributed Cache Cluster (N=3)"
        Node1("Node 1 (Coordinator)")
        Node2("Node 2 (Replica)")
        Node3("Node 3 (Replica)")
    end

    Client -- "SET('my_key', 'value')" --> Node1;
    Node1 -- "1. Writes data locally" --> Storage1(( ))
    Node1 -- "2. Replicates write" --> Node2;
    Node1 -- "2. Replicates write" --> Node3;
    Node2 -- "Stores data" --> Storage2(( ))
    Node3 -- "Stores data" --> Storage3(( )) 
```

## How to Run the Cluster & Tests

This project is orchestrated with Docker Compose.

### Prerequisites

- Docker & Docker Compose
- Git
- Python 3.10+ (for running the test scripts)

### 1. Launch the 3-Node Cluster

Clone the repository and use Docker Compose to build and start the services.

```bash
git clone https://github.com/YourUsername/python-distributed-cache.git
cd python-distributed-cache
docker-compose up --build
```

The cluster is now running. You will see logs from node1, node2, and node3 in your terminal.

### 2. Run the Fault Tolerance (Chaos) Test

While the cluster is running, open a second terminal to run the chaos test. This script will set a key, randomly kill one of the nodes, and verify that the key can still be retrieved from a surviving node.

```bash
# In a new terminal, from the project root
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python chaos_test.py
```

Upon successful completion, you will see a `✅ CHAOS TEST PASSED ✅` message.

### 3. Run the Performance Benchmark

To run the performance benchmark against the live cluster:

```bash
# In a new terminal, with the venv activated
python benchmark.py
```
