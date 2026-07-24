# Troubleshooting Manual (MR-RAG v1.0)

This manual provides operational diagnostics for handling error states, CPU blockages, memory limitations, and network failures.

## 1. Task Queue Blockages
- **Symptom**: Ingestion tasks stay in `pending` or `blocked` status indefinitely.
- **Diagnostic**: Check if Redis is reachable and verify worker instances are running:
  ```bash
  docker compose ps
  docker compose logs worker
  ```
- **Remedy**: Ensure workers are listening to the same database namespaces as the Flask API container. Clear stalled leases by restarting workers to release execution locks.

---

## 2. Ingestion Out-Of-Memory (OOM) Safely
- **Symptom**: Log displays `ValueError: Governance Limit Exceeded` or worker process dies.
- **Diagnostic**: Check PDF size, character density, or chunk counts.
- **Remedy**: Scale up memory bounds in `backend/config.py` (`PDF_MEMORY_LIMIT_MB`) or adjust chunk targets if the document contains large structural lists.

---

## 3. Provider Connection Timeouts (HTTP 429 / 503)
- **Symptom**: Chat query returns fallback status or reports failure.
- **Diagnostic**: Inspect provider API keys and usage quotas.
- **Remedy**: The platform will automatically execute backing retry loops. If quota limits persist, configure fallback providers in `LLM_PROVIDER_ORDER`.

This manual ensures that operations keep the system **Production Qualified under the evaluated benchmark suite**.
