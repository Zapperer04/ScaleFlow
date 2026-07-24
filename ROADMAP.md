# ScaleFlow MR-RAG Project Roadmap

This roadmap outlines planned iterations, optimization tracks, and feature sets for future releases post v1.0.

---

## v1.0 (Current Frozen Baseline)
- **Status**: Stable Release Freeze
- **Scope**: Core document intelligence, ensemble experts, RRF, Redis queues, and qualification benchmarks.
- **Verification**: **Production Qualified under the evaluated benchmark suite**.

---

## v1.1 (Performance & Infrastructure Optimization)
- **Target Date**: Q4 2026
- **Focus**:
  - GPU-accelerated local VLM parsing and inference engines (vLLM integration).
  - Quantized embedding support in Qdrant (binary/int8 quantization configurations).
  - Multi-threaded batch ingestion to double worker parsing throughput.

---

## v1.2 (Agentic Reasoning & Multi-Hop Querying)
- **Target Date**: Q1 2027
- **Focus**:
  - LangGraph integration to execute multi-agent query expansion and planning.
  - Contextual chunking improvements using recursive layout boundaries.
  - Multi-document session memory and reference validation.

---

## v2.0 (Distributed Graph & Knowledge-Base Integration)
- **Target Date**: H2 2027
- **Focus**:
  - Migrating graph indexing from SQLite to a distributed Neo4j cluster.
  - Real-time knowledge graph evolution (updating relationships dynamically during conversation).
  - Support for multi-lingual and multi-modal document collections.
