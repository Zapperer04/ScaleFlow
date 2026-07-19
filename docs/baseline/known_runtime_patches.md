# Known Runtime Patches & Compatibility Layers

This document explicitly lists the temporary runtime monkey-patches and compatibility layers introduced in `tests/utilities/run_worker.py` and `tests/utilities/run_app.py` to allow the regression testing framework to execute offline in local environments.

These shims document existing production bottlenecks and bugs. They will be removed once the corresponding production refactoring phases address the root causes.

| Patch | Target Location / Module | Reason | Temporary? | Target Phase |
| :--- | :--- | :--- | :--- | :--- |
| **Whoosh escape shim** | `whoosh.qparser.escape` | Whoosh import error on Python 3.10+ due to module structure changes. | Yes | Phase 3 (Retrieval Abstraction) |
| **Chunk node map shim** | `services.chunking_service._build_node_map` | Mismatch where `_build_node_map` expects `node_id` or `id`, but the plaintext parser output only includes `chunk_id`. | Yes | Phase 5 (Chunking & Processing Pipelines) |
| **Qdrant offline mock** | `services.vector_store.upsert_document_chunks` | Bypasses local dependency on running Qdrant daemon for offline regression baselining. Resolves 3-tuple/4-tuple return type mismatch. | Yes | Phase 4 (Storage & Embedding Service Abstraction) |
| **ArtifactType serialization** | `/artifacts/<id>/content` route | Flask's `jsonify` raises a 500 error when serializing the custom `ArtifactType` SQLAlchemy Enum directly. | Yes | Phase 8 (API & Web Server Refactoring) |
| **set_chunk_lookup import bug** | `services.graph_expansion_service` | `retrieval_service.py` attempts to import `set_chunk_lookup` from `graph_expansion_service`, but only `set_batch_chunk_lookup` exists. | Yes | Phase 3 (Retrieval Abstraction) |


## Tech Debt Backlog Items

### DEBT-06: Fix ArtifactType Serialization
- **Root Cause**: The Flask route `/artifacts/<int:artifact_id>/content` returns the raw SQLAlchemy `ArtifactType` object in the JSON payload, which Flask cannot serialize by default.
- **Resolution**: Convert `artifact.artifact_type` to its string value (`artifact.artifact_type.value`) within production code.

### DEBT-07: Fix Chunk Builder Assumptions
- **Root Cause**: The chunking service's `_build_node_map` expects parsing nodes to have `node_id` or `id`. However, the plain text parsing path assigns `chunk_id` to paragraphs.
- **Resolution**: Align parser output contracts across both PDF/VLM and plaintext parsers to guarantee uniform schema compliance.

### DEBT-08: Remove Whoosh Compatibility Shim
- **Root Cause**: `from whoosh.qparser import escape` fails in Whoosh versions on newer Python runtimes.
- **Resolution**: Upgrade/replace Whoosh or encapsulate term escaping behind a standardized index utility class.

### DEBT-09: Offline Vector Store Abstraction
- **Root Cause**: Direct coupling of RAG ingestion steps to Qdrant without a clean interface for mock/dry-run capabilities.
- **Resolution**: Build a database adapter/interface layer that supports simple in-memory or mock storage drivers for testing.
