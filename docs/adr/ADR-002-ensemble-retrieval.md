# ADR-002: Parallel Ensemble Expert Retrieval

## Status
Accepted

## Context
RAG retrieval pipelines typically route to a single index strategy (e.g. vector lookup only). In complex scenarios, querying a single index misses graph structures, metadata associations, or layout coordinates.

## Decision
We execute multiple parallel Expert retrievers (Vector, Graph, Entity, Table, Layout) to capture diverse aspects of the document representation. Their results are fused and reranked using a Cross-Encoder.

## Consequences
- **Pros**:
  - High recall and semantic coverage.
  - Combines structured data (tables/graphs) and unstructured vector search.
- **Cons**:
  - Requires parallel thread execution to minimize end-to-end latency.
