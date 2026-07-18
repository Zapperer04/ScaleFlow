# ScaleFlow Overview

ScaleFlow is a distributed, agentic AI document intelligence and processing platform. It ingests complex, large-scale multi-format files (PDFs, images), conducts image enhancements, parses the text via multi-tiered OCR/VLM layout engines, extracts hierarchical Document Graphs, chunks the text semantically, generates vectors, indexes via sparse BM25, and provides hybrid retrieval (dense + sparse + graph expansion + reranking) for downstream LLM answering.

## System Architecture

```mermaid
graph TD
    UI[Frontend / Clients] -->|REST API| API[API Gateway / Flask App]
    API -->|Read/Write Metadata| DB[(PostgreSQL / SQLite)]
    API -->|Enqueue Tasks| RedisQueue[(Redis Queue / Celery-like)]
    RedisQueue -->|Dequeue & Execute| Worker1[ScaleFlow Worker 1]
    RedisQueue -->|Dequeue & Execute| Worker2[ScaleFlow Worker 2]
    Worker1 -->|Store Embeddings| Qdrant[(Qdrant Vector Store)]
    Worker1 -->|Store BM25 Index| Disk[Shared Disk / local storage]
    Worker1 -->|VLM Layout Queries| VLM[OpenRouter / Gemini API]
```

## System Deployment Model
- **Frontend**: React-based single-page application.
- **Backend (API)**: Flask-based REST service with SQLAlchemy connection pooling.
- **Workers**: Concurrency-managed Python worker processes executing tasks via capabilities.
- **Queue/Broker**: Redis instance handling task queues, priorities, lease timeouts, and heartbeats.
- **Databases**: PostgreSQL (fallback to SQLite) for metadata and transaction audit trail; Qdrant for semantic vector representation.\n