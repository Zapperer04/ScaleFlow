# System Configuration & Environment Guide (MR-RAG v1.0)

This guide outlines the configuration variables, feature flags, and environment variables used by the ScaleFlow serving platform.

## 1. Core Environmental Variables

Create a `.env` file in the `backend/` directory or pass these environment settings directly to the containers:

| Variable | Default Value | Description |
| --- | --- | --- |
| `DB_MODE` | `sqlite` | Primary metadata database engine (`sqlite` or `postgres`). |
| `REDIS_HOST` | `localhost` | Task queue and lock broker hostname. |
| `REDIS_PORT` | `6379` | Connection port for the Redis instance. |
| `QDRANT_HOST` | `localhost` | Vector DB hostname. |
| `QDRANT_PORT` | `6333` | Connection port for Qdrant. |
| `VLM_PROVIDER` | `openrouter` | Ingestion parser API provider (e.g. `openrouter`, `gemini`). |

---

## 2. Ingestion & Resource Limits

Enforce quality/size boundaries to prevent OOM errors:
- `MAX_CHARACTER_LIMIT`: Default `2000000`. Caps maximum text sizes processed per PDF.
- `MAX_CHUNKS`: Default `1500`. Caps chunk collections size.
- `PDF_MEMORY_LIMIT_MB`: Default `1500`. Triggers ValueError if process memory bounds are breached.

---

## 3. Retrieval & Weights

- `BM25_ENABLED`: Default `True`.
- `GRAPH_EXPANSION_ENABLED`: Default `True`.
- `DENSE_WEIGHT`: Default `0.6`. Reciprocal Rank Fusion weight.
- `BM25_WEIGHT`: Default `0.4`.

These configuration boundaries guarantee a platform that remains **Production Qualified under the evaluated benchmark suite**.
