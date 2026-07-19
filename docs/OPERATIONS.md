# ScaleFlow Resource Execution Engine - Operations Runbook

This document details diagnostic steps, symptoms, recovery actions, and metrics for managing the Resource Execution Engine in production.

## 1. Redis Failure
### Symptoms
- Workers emit errors: `ConnectionError: Error connecting to localhost:6379`.
- Leases cannot be acquired; jobs fail to start.
- Metrics ingestion stalls.

### Diagnosis
- Check Redis availability: `redis-cli ping`.
- Check CPU utilization on the Redis container/host.

### Recovery
- Restart the Redis instance.
- Workers will fail back to sleep intervals, wait for connection re-establishment, and automatically resume processing since all jobs utilize stateless `JobSpecs` and the `ArtifactRegistry`.
- Verify locks and leases are clean. If necessary, flush expired leases: `redis-cli KEYS "lease:*" | xargs redis-cli DEL`.

---

## 2. Provider Completely Down
### Symptoms
- Massive surge in `PROVIDER_SELECTED` -> `JOB_FAILED` events.
- Health scores drop to 0 for a specific provider.
- Processing latency peaks.

### Diagnosis
- Inspect logs to check if exceptions indicate network timeout or authentication failures.
- Check provider status flag: `redis-cli GET provider:<provider_id>:available` (0 = unavailable).

### Recovery
- The `ResourceBroker` automatically bypasses unavailable providers.
- To manually disable a provider: `redis-cli SET provider:<provider_id>:available "0" EX 86400`.
- To force restore: `redis-cli SET provider:<provider_id>:available "1"`.

---

## 3. Queue Growth
### Symptoms
- `scheduler_queue_depth` increases continuously.
- Starvation metrics (`starvation_time` or `Starvation Index`) worsen.
- User uploads take too long to start.

### Diagnosis
- Check quota allocations via metrics or `redis-cli KEYS "quota:*"`.
- Verify worker utilization: Are workers active or idle? If idle, they may be blocked by quota limits.

### Recovery
- If blocked by quotas: Ingestion throttling will automatically activate at `MAX_QUEUE_DEPTH`, returning 429s to users.
- If workers are overloaded but quotas are available: Scale up the worker replicas.

---

## 4. Replay Investigation
### Symptoms
- A specific job fails deterministically under certain chaos/production workloads.

### Diagnosis
- Retrieve the unique run identifier: `run_<timestamp>`.
- Read the events leading up to the crash: `less execution_engine/simulation/runs/run_<timestamp>/event_log.jsonl`.

### Recovery
- Reproduce the exact bug locally:
  ```bash
  python -m execution_engine.replay runs/run_<timestamp>
  ```
- This locks Python's random state to the seed in `random_seed.txt`, guaranteeing identical scheduling decisions.

---

## 5. Shadow Mode & Emergency Rollback
### Symptoms
- Mismatches in graph parity drop below 99%.
- Real-time VLM parsing returns malformed Canonical JSON Graphs.

### Diagnosis
- Check shadow mode metrics dashboard in Grafana.
- Compare Legacy vs. new Engine graphs structurally and textually using stored artifact hashes.

### Recovery
- **Emergency Rollback:** If the new engine degrades production, flip the configuration parameter:
  - Change Strategy configuration back to `legacy`.
  - The Strategy factory will route all jobs through `LegacyStrategy` (the old parser), bypassing the Execution Engine without needing a code redeployment.

---

## 6. Core Efficiency Metrics
The Grafana dashboard tracks **Scheduling Efficiency**:
$$\text{Scheduling Efficiency} = \frac{\text{Useful Resource Time (Inference)}}{\text{Total Resource Reserved Time}}$$
If this metric drops below **80%**, the system is wasting reserved capacity through excessive retries, slow prompt compilation, or validation bottlenecks. Investigate worker overheads immediately.
