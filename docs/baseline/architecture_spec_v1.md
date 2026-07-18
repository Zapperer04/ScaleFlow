# Architecture Specification & Refactoring Plan (v1.1)

> [!IMPORTANT]
> **The Core Architectural Principle:**
> The application layer orchestrates work but never performs provider-specific logic, storage-specific logic, or transport-specific logic. Infrastructure implements capabilities. Domain owns business rules. Interfaces only trigger workflows.

## Architectural Rules

1. Domain never imports Infrastructure.
2. Infrastructure never imports Interfaces.
3. Application owns orchestration only.
4. Providers never call databases.
5. Storage never calls providers.
6. Routers never execute business logic.
7. Workers never contain parser logic.
8. Domain objects never depend on Flask, SQLAlchemy, Redis, or Qdrant.
9. Every stage communicates only through DTOs or Domain Models.
10. Every public interface must have tests.

---

## Target Folder Structure

```text
backend/
├── core/                       # Configurations, logging, global exceptions
│   ├── config.py
│   ├── logging.py
│   └── exceptions.py
├── domain/                     # Pure domain models & business events (no framework dependencies)
│   ├── document.py
│   ├── chunk.py
│   ├── graph.py
│   ├── node.py
│   ├── edge.py
│   ├── artifact.py
│   ├── states.py               # Pipeline state machine (Uploaded, Preprocessed, Parsed, Chunked, Embedded, Indexed, Ready, Failed)
│   └── events/                 # Domain events (DocumentUploaded, ParsingStarted, etc.)
├── dto/                        # Data Transfer Objects
│   ├── parsing.py              # ParseRequest, ParseResponse
│   ├── chunking.py             # ChunkRequest
│   └── retrieval.py            # RetrievalRequest, RetrievalResponse
├── contracts/                  # Versioned serialization & validation contracts
│   ├── document_contract_v1.md
│   ├── parser_contract_v1.md
│   ├── graph_contract_v1.md
│   ├── chunk_contract_v1.md
│   └── retrieval_contract_v1.md
├── shared/                     # Cross-cutting helpers
│   ├── constants.py
│   ├── types.py
│   ├── utils.py
│   └── validators.py
├── application/                # Business logic orchestration layers
│   ├── parsing/
│   │   ├── orchestrator.py
│   │   ├── routing.py
│   │   ├── checkpoint.py
│   │   ├── graph_builder.py
│   │   ├── graph_validator.py
│   │   ├── chunk_builder.py
│   │   ├── resume.py
│   │   └── statistics.py
│   ├── retrieval/
│   ├── embedding/
│   └── indexing/
├── infrastructure/             # Concrete libraries, APIs, DB setups
│   ├── qdrant/
│   ├── postgres/
│   ├── redis/
│   ├── bm25/
│   ├── gemini/
│   ├── openrouter/
│   └── huggingface/
├── repositories/               # Repository interfaces & query implementations
│   ├── base.py                 # Abstract repository definitions
│   └── sqlite_pg_repo.py       # SQL Alchemy queries for domain models
├── interfaces/                 # Outer-most request delivery mechanisms
│   ├── api/                    # Flask routers (routing and request validation only)
│   └── workers/                # Background runner & queue listeners
└── tests/
    ├── fixtures/               # Golden dataset inputs
    └── expected/               # Golden truth output files
```

---

## Target Implementation Phases & Success Criteria

### Phase 0: Architecture Baseline ✅
- **Objective**: Set base stats, hotspots, dead code, and target architecture specifications.

### Phase 0.5: Golden Dataset
- **Objective**: Create a permanent benchmark suite containing diverse document fixtures.
- **Scope**:
  - Store source files (`tests/fixtures/`) categorized under: `digital`, `scanned`, `mixed`, `tables`, `forms`, `multicolumn`, and `images`.
  - Store verified outputs (`tests/expected/`) including text parser content, graphs, chunks, embeddings, and retrieval outputs.
- **Success Criteria**:
  - Ground truth JSON outputs frozen for all files in the test suite.

### Phase 1: Safety Net
- **Objective**: Implement comprehensive regression testing verifying the frozen Golden Dataset.
- **Scope**:
  - **Parser**: Digital PDF, Scanned PDF, Mixed PDF, Resume parsing, Batch parsing, OCR fallback, Provider switching, Checkpoint recovery, Large PDF, Corrupted PDF.
  - **Worker**: Lease, Heartbeat, Resume, Retry, Failure, Queue Priority, Dead Worker Recovery.
  - **Retrieval**: Dense, BM25, Hybrid, Metadata filtering, Reranking, Graph expansion, Intent routing.
  - **Integration**: Complete end-to-end pipeline (Upload -> Preprocess -> Parse -> Chunk -> Embed -> Retrieve -> LLM).
- **Success Criteria**:
  - 100% pass rate on regression validations using current production codebase.

### Phase 2: Domain Models + DTOs + Contracts + Adapters
- **Objective**: Introduce structured representations without breaking changes.
- **Scope**:
  - Define `domain/` objects (Node, Edge, Artifact, State Machine).
  - Implement bidirectional Adapters (`Legacy -> Domain`, `Legacy -> DTO`).
- **Success Criteria**:
  - Integration tests pass using adapters and new contracts while using the legacy pipeline.

### Phase 3: Provider Abstraction
- **Objective**: Wrap parser providers cleanly behind capability matrices.
- **Scope**:
  - Implement `BaseParserProvider` interfaces.
  - Integrate Gemini, OpenRouter, and OCR fallbacks with Retry Policies, Circuit Breakers, and Rate Limiters.
- **Success Criteria**:
  - Parser contains zero provider-specific library imports or direct `os.environ` updates.
  - Golden dataset outputs match perfectly.

### Phase 4: Storage + Repository Abstraction
- **Objective**: Segregate physical assets from query engines.
- **Scope**:
  - Separate `Repository`, `Storage`, `Cache`, `Artifact Store`, `Vector Store`, and `Metadata Store`.
- **Success Criteria**:
  - All DB/Redis/Qdrant references decoupled from core service scripts.

### Phase 5: Parser Refactor
- **Objective**: Decompose parser code by responsibility.
- **Scope**:
  - Break down into: Routing -> Checkpoint -> VLM -> OCR -> Graph -> Chunk -> Statistics.
- **Success Criteria**:
  - Total `pdf_parser.py` code modularized. Golden dataset output matches exactly.

### Phase 6: Retrieval Refactor
- **Objective**: Simplify and isolate search pipelines.
- **Scope**:
  - Separate: Query -> Intent -> Metadata Filter -> Dense -> BM25 -> Fusion -> Graph Expansion -> Reranker -> Context Builder.

### Phase 7: Worker Refactor
- **Objective**: Clean background worker leases and queue mechanisms.
- **Scope**:
  - Separate: Lease Manager, Heartbeat, Executor, Retry Queue, DLQ, Metrics.

### Phase 8: API Refactor
- **Objective**: Restructure entry points.
- **Scope**:
  - Decouple routes, controllers, request validations, application services, and repositories.

### Phase 9: Performance & Production Hardening
- **Objective**: Secure runtime stability, observability, and scaling.
- **Scope**:
  - Profiling, caching, OpenTelemetry tracing, Prometheus/Grafana monitoring, Memory leak tests, CI/CD pipelines, and security checks.
- **Success Criteria**:
  - Zero memory leaks under load tests.
  - Observability stats report properly via tracing.
