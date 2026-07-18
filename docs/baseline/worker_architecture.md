# Worker Architecture

ScaleFlow uses a custom polling consumer model (non-Celery) communicating through Redis and HTTP API.

## Worker Lifecycle

```mermaid
sequenceDiagram
    participant W as Worker
    participant R as Redis
    participant A as API Gateway
    
    W->>A: POST /workers/register
    W->>R: BRPOP queue with capability match
    R-->>W: Task Payload
    W->>A: POST /tasks/{id}/claim
    Note over W: Start LeaseRenewer Thread
    Loop Every 10-15s
        W->>A: POST /tasks/{id}/renew-lease
    End
    W->>W: Execute Handler
    W->>A: PATCH /tasks/{id} (status=completed)
    Note over W: Stop LeaseRenewer
```

## Lease Management & Heartbeats
- **Lease Duration**: Est. Runtime * LEASE_MULTIPLIER (3.0). Explicit overrides are defined per task (e.g., embedding=900s, parsing=600s).
- **LeaseRenewer Thread**: Runs in background during task execution. Extends lease using `/tasks/{task_id}/renew-lease`.
- **Heartbeats**: Workers ping `/workers/heartbeat` every `WORKER_HEARTBEAT_SECONDS` (10s).
- **Concurrency**: Governed by backend slots (Gemini rate manager) and local worker thread pools.\n