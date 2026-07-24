# Architectural Decision Records (ADR) Registry

This registry tracks the major architectural decisions made during the design, construction, and iteration of the MR-RAG platform. Each record details the context, proposed solution, and consequences of the choice.

## ADR Index

| ID | Title | Status | Description |
| --- | --- | --- | --- |
| **[ADR-001](file:///Users/kaustavkumar/Kaustav/Projects/task-schedular/docs/adr/ADR-001-vlm-first-parsing.md)** | VLM-First Ingestion & Parsing | `Accepted` | Leverages Vision-Language Models (VLM) as the primary pipeline stage, falling back to layout parsing and OCR. |
| **[ADR-002](file:///Users/kaustavkumar/Kaustav/Projects/task-schedular/docs/adr/ADR-002-ensemble-retrieval.md)** | Multi-Representation Expert Ensemble | `Accepted` | Replaces single dense retrieval with an ensemble of experts (Vector, Graph, Entity, Table, Layout) routed by query intent. |

## Lifecycle States
- **Proposed**: Under discussion and review.
- **Accepted**: Approved and implemented in codebase.
- **Superseded**: Replaced by a newer architectural choice (reference new ADR).
- **Rejected**: Discussed but not approved for implementation.
