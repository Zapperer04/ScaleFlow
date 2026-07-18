# DTO Design Specification

Data Transfer Objects (DTOs) decouple external/internal serialization formats from the domain representation. In ScaleFlow, DTOs are defined using Pydantic v2 `BaseModel` for validation, versioning, and auto-generated JSON schemas.

## DTO Matrix

| DTO Class | File Path | Version | Target Area | Description |
|---|---|---|---|---|
| `ParserResponseDTO` | `backend/dto/parsing.py` | v1 | Parsing | Document parsing outputs |
| `ChunkDTO` | `backend/dto/chunking.py` | v1 | Chunking | Extracted document chunks |
| `EmbeddingDTO` | `backend/dto/embedding.py` | v1 | Embedding | Vector embeddings |
| `RetrievalRequestDTO` | `backend/dto/retrieval.py` | v1 | Retrieval | Incoming search query criteria |
| `RetrievalResponseDTO` | `backend/dto/retrieval.py` | v1 | Retrieval | Retrieval outputs and rank metadata |
| `WorkerTaskDTO` | `backend/dto/worker.py` | v1 | Queue/Worker | Leased tasks for execution workers |
| `PipelineStateDTO` | `backend/dto/pipeline.py` | v1 | Orchestration | Pipeline tracking and active state |
| `StorageArtifactDTO` | `backend/dto/storage.py` | v1 | Storage | Extracted files and graph snapshots |
| `GraphDTO` | `backend/dto/graph.py` | v1 | Graph | Schema representation of knowledge graph |

## Immutable Configuration

Every DTO enforces immutability via:
```python
model_config = {"frozen": True}
```
This protects execution state from side-effects during inter-process mapping.
