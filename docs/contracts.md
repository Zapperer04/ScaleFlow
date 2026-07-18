# Contracts Specification

JSON Schema contracts enforce schema compliance at external boundaries. All schemas are versioned under `backend/contracts/schemas/v1/`.

## Generated JSON Schema Contracts

- **`ParserResponse.json`**: Structural validation of parser extraction.
- **`Chunk.json`**: Individual page segments and structural mappings.
- **`Graph.json`**: Complete knowledge graph hierarchy.
- **`Node.json`**: Singular concept representations in the RAG index.
- **`Edge.json`**: Logical relationships connecting concept nodes.
- **`Metadata.json`**: Validation of arbitrary key-value metadata payloads.
- **`Embedding.json`**: Dimension and data types for vectorized inputs.
- **`RetrievalRequest.json`**: Formal structure for query filters.
- **`RetrievalResponse.json`**: Expected schema of search results.
- **`PipelineState.json`**: State and lifecycle metadata constraints.

These schemas are generated directly from the Pydantic DTO models using `model_json_schema()`.
