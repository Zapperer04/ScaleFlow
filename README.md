# ScaleFlow

## Distributed Workflow Orchestration & State Recovery Runtime

ScaleFlow is a production-grade, highly available, distributed workflow orchestration runtime built to execute complex directed acyclic graphs (DAGs) of tasks with absolute fault tolerance. Built to align architecturally with industry platforms like **Temporal** and **Netflix Conductor**, ScaleFlow manages queue scheduling, stuck task leases, split-brain coordination, and vector ingestion pipelines with zero single-points-of-failure.

---

## 🏗️ System Architecture

ScaleFlow utilizes a decoupled, event-driven producer-consumer topology:

```text
                  +-----------------------------------+
                  |          React Client Dashboard   |
                  +-----------------+-----------------+
                                    | HTTP
                                    ▼
                  +-----------------+-----------------+
                  |     Orchestrator Runtime (Flask)  |
                  +-----+-----------+-----------+-----+
                        |           |           |
       Persistent State |           | Leases &  | Broker Queues
        & Event Ledger  |           | Fencing   | & Heartbeats
                        ▼           ▼           ▼
                 +------+---+   +---+------+   ++---------+
                 | Postgres |   | Postgres |   |  Redis   |
                 | (Ledger) |   | (Fencing)|   | (Broker) |
                 +----------+   +----------+   +----+-----+
                                                    |
                                       WRR Polling  |
                                       & Heartbeats |
                                                    ▼
                                               +----+-----+
                                               | Workers  |
                                               +----+-----+
                                                    |
                                      Vector Upsert |
                                                    ▼
                                               +----+-----+
                                               | Qdrant DB|
                                               +----------+
```

### Key Architectural Layers:
1. **Dashboard UI (React)**: Real-time console featuring interactive DAG graphs, a live audit timeline, worker heatmaps, congestion flows, and a sandboxed time-travel replay scrubber.
2. **Orchestrator Runtime (Flask)**: Stateless Active/Active coordinators. Orchestrators claim pipeline ownership leases, evaluate task dependencies, trigger queue admissions, and monitor heartbeats.
3. **Message Broker (Redis)**: volatile queue broker routing tasks via capability-specific queues (e.g. `task_queue_embedding_gpu_high`) using priority allocations.
4. **Worker Pool (Python Daemons)**: Concurrently pop and lease tasks from Redis using Weighted Round-Robin (WRR) queue selections, maintaining renewable leases.
5. **Durable Ledger (PostgreSQL)**: Transactional storage for task states and an append-only event sourcing history database.
6. **Vector Database (Qdrant)**: Stores document chunk embeddings and services metadata-filtered semantic search queries.

---

## 🚀 Quick Setup & Run

### 1. Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL
- Docker Desktop (for Qdrant & Redis)

### 2. Configure Environment
Create `.env` files in both `backend` and `frontend` directories using the provided `.env.example` configurations.

### 3. Launch Services
Start the entire cluster (Redis, PostgreSQL, Qdrant, Workers, Flask API, React UI) on Windows using:
```powershell
./start-services.bat
```
Select **Option 4** to spin up all processes in separate CLI terminals.

---

## 🎬 5-Minute Showcase Demo Walkthrough

Walk through this structured storytelling narrative to demo ScaleFlow's capabilities:

1. **Ingest Document**: In the dashboard, upload a PDF/text file and trigger `document_processing_demo`.
2. **Watch Live DAG**: The React Flow canvas visualizes the DAG, dynamically animating active running paths.
3. **Execute & Store Embeddings**: Worker nodes process tasks (`parse_document` $\rightarrow$ `chunk_text`), lazy-load Sentence Transformers, generate embeddings, and upsert them to Qdrant.
4. **Perform RAG Search**: In the Search panel, execute a semantic query. The system embeds the query, searches Qdrant, filters by file ID, and synthesizes an answer with citations.
5. **Simulate Worker Crash**: Claim a task and terminate the worker container.
6. **Automatic Lease Recovery**: The background recovery thread detects the expired lease in 10s, requeues the task in Redis, and increments the recovery counter.
7. **Fencing Block**: Start the crashed worker and attempt to complete the task with its old token. The database fencing token checks reject the stale write with a `409 Conflict`.
8. **Time-Travel Debug**: Open the Replay Sandbox, select the pipeline, and slide the scrubber. Watch the DAG state reconstruct deterministically from append-only Postgres logs.

---

## 🎯 System Design Interview Talking Points

Be ready to explain these design tradeoffs and choices:

### 1. Why use a Redis + PostgreSQL Hybrid Broker?
*Databases use row locks and index scans that degrade under concurrent queuing. Redis operates in memory with atomic popping (`rpop`, `brpop`), preventing double-claim execution. PostgreSQL guarantees ACID compliance for state ledgers, allowing safe recovery sweeps if the Redis memory broker crashes.*

### 2. How does the system handle stuck task lease recoveries?
*Workers claim tasks by acquiring a lease token and duration (30s) stored in PostgreSQL. A worker daemon runs a background thread to call `/renew-lease` every 15s. If a worker crashes, the lease expires. The Orchestrator leader scans PostgreSQL, detects the expired lease, resets the task status to `'pending'`, increments the retry counter, and re-queues it in Redis.*

### 3. How does the system prevent split-brain issues?
*Each pipeline maintains a monotonic `ownership_version` column serving as a fencing token. When a surviving orchestrator takes over an expired pipeline lease, it increments the database counter. If the partitioned orchestrator recovers and attempts a write, its lower version token is rejected by the database with a `409 Version Conflict` write gate.*

### 4. What is Replay Sandboxing?
*Reconstructs in-memory pipeline state by playing append-only PostgreSQL event logs. Replays execute solely in memory, ensuring that time-travel debugging never registers duplicate enqueues, vector updates, or email dispatches. Periodic snapshots at event watermarks keep replay reconstruction cost bound to $O(1)$.*

### 5. How does Pipeline Backpressure work?
*If downstream queues grow past 10 tasks, the capability is marked congested. The orchestrator blocks child task releases, marking them `'blocked'` with reason `'Upstream congestion: throttled'` and setting `deferred_at = now`. When queue depth drops, the unblock scanner releases them. Throttled tasks waiting > 60s undergo priority aging: they escalate to `'high'` and bypass backpressure bounds.*
