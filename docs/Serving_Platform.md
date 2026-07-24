# Serving Platform & Scaling Architecture (MR-RAG v1.0)

This document describes the task scheduling, worker nodes, and horizontal scaling capabilities of the serving platform.

## Distributed Worker Node Ingestion

Workers poll task queues hosted inside the Redis broker. Tasks execution is handled using lease locks:

```mermaid
graph TD
    subgraph Distributed Worker Clusters
        W1[Worker 1]
        W2[Worker 2]
        W3[Worker 3]
    end
    
    Broker[(Redis Task Queue)] -->|Dequeue Task| W1
    Broker -->|Dequeue Task| W2
    Broker -->|Dequeue Task| W3
    
    W1 -->|Renew Lease every 15s| RedisLock[Redis Lease Manager]
    W2 -->|Renew Lease every 15s| RedisLock
    W3 -->|Renew Lease every 15s| RedisLock
    
    W1 -->|Write Status| SQLite[(SQLite DB)]
    W2 -->|Write Status| SQLite
    W3 -->|Write Status| SQLite
```

---

## 1. Task Queue Management
- **Task Dequeuing**: Workers pull pending tasks based on priority (high/medium/low).
- **Lease Mechanism**: Worker locks tasks for 60 seconds, extending lease every 15 seconds. If a worker crashes, lease expires and task returns to queue.
- **Backpressure**: Task counts are tracked. Ingestion halts if Redis backlog exceeds limits.

---

## 2. Horizontal Scaling Guidelines
- **Stateless Workers**: Adding workers scales CPU bounds (parsing/OCR).
- **Shared Storage**: Scale worker nodes by attaching a shared storage volume (NFS/EFS) to locate raw documents under `UPLOAD_DIR`.

This serving architecture ensures the system is **Production Qualified under the evaluated benchmark suite**.
