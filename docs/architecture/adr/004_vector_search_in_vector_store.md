# ADR-004: Vector Search Belonging Exclusively to VectorStore

## Status
Accepted

## Context
Repositories are responsible for managing the persistence of domain aggregates and entities. In contrast, approximate nearest neighbor (ANN) vector search, similarity queries, and collection management are indexing responsibilities. Combining vector searching with the `EmbeddingRepository` violates the single responsibility principle and muddies the boundary between storage/database operations and indexing/retrieval operations.

## Decision
- `EmbeddingRepository` is restricted to generic CRUD and metadata persistence operations (`save`, `load`, `delete`, `get_by_chunk_id`).
- All vector search, index, upsert, and collection management operations reside in the `BaseVectorStore` interface and `QdrantStore` implementation.
- All query inputs and filters use dedicated domain DTOs (`VectorPoint`, `VectorQueryFilter`) to avoid leaking vendor-specific structures.

## Consequences
- Maintains a clean separation between database CRUD persistence (repositories) and vector search capabilities.
- Allows switching vector databases (e.g. from Qdrant to Pinecone or Milvus) without modifying metadata repositories.
