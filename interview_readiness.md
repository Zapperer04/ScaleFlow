# ScaleFlow – Interview Readiness & System Design Guide

This document maps out the system design tradeoffs, fault-tolerance mechanisms, and scalability pathways implemented in ScaleFlow. Use this as a cheat sheet for technical placement interviews and engineering reviews.

---

## 1. Why use a Redis + PostgreSQL Hybrid Broker Model?
- **Core Dilemma**: Absolute write speed vs. Strict ACID persistence guarantees.
- **Why simple SQL Database polling fails**: Databases use heavy row-locks and index scans. If multiple workers concurrently poll a table (e.g. `SELECT * FROM tasks WHERE status = 'pending' LIMIT 1 FOR UPDATE`), database transaction contention builds quickly, causing severe bottlenecks and query timeout failures under high load.
- **Why pure Redis queuing fails**: In-memory storage is volatile. If the Redis broker container crashes, all current queue slots and worker lease trackers vanish, leaving the system in an inconsistent state.
- **The Hybrid Solution**:
  - **Redis** is used as the high-throughput, low-latency (<1ms) message broker. Workers pop tasks atomically (`rpop` or blocking `brpop`) from capability-specific priority queues, guaranteeing that no two workers can claim the same task.
  - **PostgreSQL** is the source of truth database. It records the append-only event ledger and task state updates. If the Redis broker crashes, the coordinator reconciles queue statuses by scanning PostgreSQL and re-enqueuing missing jobs.

---

## 2. Stuck Task Lease Recovery Protocol
- **Problem**: A worker claims a task, but the worker VM crashes, the container runs out of memory, or the process hangs. How does the engine release the locked task?
- **Mechanism**:
  - **Lease Claim**: When a worker claims a task via `POST /tasks/<id>/claim`, it receives a lease token and duration (e.g., 30s) and writes `lease_expires_at` to PostgreSQL.
  - **Active Renewal**: The worker spawns a background `LeaseRenewer` daemon thread that periodically (every `duration / 2` seconds) calls `POST /tasks/<id>/renew-lease` to push `lease_expires_at` forward.
  - **Orchestrator Sweeper**: The Orchestrator leader instance runs a background `Recovery Scanner` thread every 10s. It queries PostgreSQL for tasks in `'running'` status whose `lease_expires_at` is older than `datetime.now()`.
  - **Failover**: When a stale lease is detected, the scanner increments `task.recovered_count` and `task.retry_count`, resets the assigned worker/token to NULL, sets status back to `'pending'`, and re-enqueues the task in Redis.
  - **Max Retries**: If `retry_count >= max_retries`, the task is marked `'failed'`, and dependency failures are propagated downstream.

---

## 3. Split-Brain Prevention via Monotonic Fencing Tokens
- **Problem**: An orchestrator instance coordinating a pipeline experiences a long JVM/runtime pause (e.g., garbage collection or host network latency). Its lease expires, and another orchestrator assumes ownership. If the first orchestrator wakes up, it might attempt scheduling operations, leading to dual-execution split-brain errors.
- **Fencing Token Mechanism**:
  - We store a monotonic `ownership_version` counter on each `Pipeline` record in the database.
  - When an orchestrator instance claims or takes over a pipeline, it increments the version counter (`ownership_version = ownership_version + 1`). This new value serves as a **Fencing Token**.
  - All database state writes, task completions (`PATCH /tasks/<id>`), and queue releases check that the local cached `ownership_version` matches the database row.
  - If a split-brain orchestrator wakes up and attempts a write, the database rejects the transaction with an **HTTP 409 Conflict** (Fencing Version Mismatch). The stale orchestrator evicts the pipeline from its local cache, aborting further updates.

---

## 4. Replay Sandboxing & Snapshot Consistency
- **Problem**: Time-travel debugging or crash failover requires reconstructing the workflow state. How do we ensure that executing a replay does not cause duplicate side effects (e.g., sending duplicate emails or writing duplicate vectors)?
- **Solution**:
  - ScaleFlow uses an **Append-Only Event Store** (`orchestration_events` table). Every lifecycle transition publishes a canonical, validated event (e.g., `TASK_CLAIMED`, `TASK_COMPLETED`).
  - **Deterministic Sandbox**: The Replay Engine reconstructs the pipeline state by playing events chronologically from a designated watermark forward. The replay executes state updates *only in memory* and is strictly prohibited from enqueuing tasks to Redis, writing vectors to Qdrant, or updating live database records.
  - **Segmented Compaction & Snapshots**: Rather than replaying thousands of events from event ID 0, the coordinator saves snapshots of the pipeline state every 10 events. The Replay Engine loads the nearest snapshot prior to the target watermark and plays only the remaining events, keeping reconstruction cost bound to $O(1)$ relative to total pipeline size.

---

## 5. Pipeline Backpressure & Starvation Prevention (WRR)
- **Downstream Saturated Queue Throttling (Backpressure)**:
  - If a downstream worker capability queue (e.g., GPU summaries) grows past 10 tasks, it is flagged as congested.
  - On completing parent tasks, instead of enqueuing child tasks, the coordinator blocks release, marking the child tasks as `'blocked'` with reason `'Upstream congestion: throttled'` and setting `deferred_at = now`.
  - The background `Unblock Scanner` periodically checks congested queues, releasing blocked tasks as `'pending'` once queue depth falls below the limit.
- **Priority Aging**:
  - To prevent low-priority tasks from being blocked indefinitely under persistent backpressure, any task waiting in the backpressure buffer for more than 60s is aged: its priority is escalated to `'high'` and it is enqueued immediately.
- **Weighted Round-Robin (WRR) Queue Polling**:
  - Workers pull tasks using a structured cycle: `[high, high, high, high, high, high, medium, medium, medium, low]` (60% High, 30% Medium, 10% Low allocation).
  - This prevents high-priority tasks from starving low-priority tasks, ensuring all queues receive consistent slot allocations.

---

## 6. Scalability Limits & Distributed Partitioning
- **Current BottleNeck**:
  - PostgreSQL lock contention. Orchestrator heartbeats and lease claiming require atomic updates (`UPDATE pipelines SET owner_instance_id = :my_id ...`).
  - As concurrent pipeline execution scales to $10,000+$, database lock queue wait times will increase, causing latency spikes.
- **How to Scale Further (Consistent Hashing Ring)**:
  - Implement a **Consistent Hash Ring** partitioner.
  - Instead of having all orchestrators query the entire `pipelines` table, hash the pipeline UUIDs and distribute ownership segments across orchestrators. Each orchestrator becomes exclusively responsible for scheduling a specific hash range.
  - If an orchestrator crashes, surviving orchestrators re-partition the hash ring, take over the lost segments, load snapshots, and resume execution. This divides database write contention by the number of active orchestrator nodes.
