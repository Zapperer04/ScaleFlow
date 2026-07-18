# ADR-000: ScaleFlow Baseline Architecture

## Context
ScaleFlow needs a documented architecture baseline to evaluate the structural changes in future stages.

## Baseline Architecture Decisions

### 1. Parser Architecture
- **Decision**: Multi-tier cascading fallback.
- **Logic**: Check character length of digital extract. If below threshold (20 chars), route to VLM/OCR layout parse.

### 2. Worker Architecture
- **Decision**: Custom active pollers with lease renewal threads.
- **Logic**: Redis handles task distribution. Worker registers capabilities and spawns `LeaseRenewer` threads during runtime.

### 3. Retrieval Architecture
- **Decision**: Hybrid Fusion + Graph Neighbors + Reranking.
- **Logic**: Combines Qdrant Dense Vector search and filesystem BM25 Sparse search, expands context with graph neighbors, and filters via Cross-Encoder.

### 4. Storage Architecture
- **Decision**: Postgres (or fallback SQLite) for metadata transactions; local directories for files; Qdrant for semantic embeddings.

### 5. Deployment Architecture
- **Decision**: Single-node docker-compose with scale-ready environment hooks.\n