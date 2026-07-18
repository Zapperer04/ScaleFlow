# Architecture Specification & Refactoring Plan (v1.0)

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
```

---

## Capability-Based Provider Interface

```python
class BaseParserProvider(ABC):
    @abstractmethod
    def supports_pdf(self) -> bool: pass

    @abstractmethod
    def supports_images(self) -> bool: pass

    @abstractmethod
    def supports_batch(self) -> bool: pass

    @abstractmethod
    def max_pages(self) -> int: pass

    @abstractmethod
    def max_tokens(self) -> int: pass

    @abstractmethod
    def parse(self, request: ParseRequest) -> ParseResponse:
        """Process document parsing request through concrete VLM or OCR service."""
        pass
```

### Provider Capability Matrix

| Provider | PDF | Images | Batch | Resume | OCR | Tables |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Gemini** | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **OpenRouter** | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **OCR (Tesseract/EasyOCR)** | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ |

---

## Non-Functional Requirements (NFRs)

### 1. Parser Subsystem
- **Latency**: < 5s per 10 pages for digital layouts.
- **Memory Profile**: < 1.5 GB memory footprint.
- **Scale**: Support up to a 600-page PDF document.
- **Resiliency**: Checkpoint every batch; full capability to resume from interrupted state.

### 2. Retrieval Subsystem
- **P95 Latency**: < 150ms for hybrid dense/sparse vector search.
- **Concurrency**: Maintain performance under 50 simultaneous user threads.

---

## Migration Strategy

Every refactor should follow a safe transition model to avoid regressions:
```text
Current State -> Introduce Adapter/DTOs -> Implement New Interface -> Swap callers -> Remove Legacy Code
```

---

## Target Implementation Phases

### Phase 1: Safety Net (Before moving files)
- **Objective**: Establish and verify a comprehensive integration and regression test harness.
- **Scope**: Integration, parser, retrieval, worker, and ingestion smoke tests.

### Phase 2: Domain Models (Zero risk setup)
- **Objective**: Create `domain/`, `dto/`, and `contracts/` definitions.
- **Scope**: Add code without modifying active paths. Introduce adapters to map legacy dicts to domain structures.

### Phase 3: Provider Abstraction (First refactor)
- **Objective**: Decouple the parser from concrete LLM APIs.
- **Scope**: Implement `BaseParserProvider` for Gemini/OpenRouter.

### Phase 4: Storage Layer
- **Objective**: Wrap vector databases, SQL repositories, caching, and files.
- **Scope**: Abstract Qdrant, Postgres, Redis, and BM25 storage formats.

### Phase 5: Parser Decomposition
- **Objective**: Dismantle `pdf_parser.py`.
- **Scope**: Split parsing into individual orchestration, routing, checkpointing, and building files.

### Phase 6: Retrieval Decomposition
- **Objective**: Clean search pathways.
- **Scope**: Split BM25, dense vector, reranker, and graph expansion into modular application services.

### Phase 7: Workers
- **Objective**: Streamline background task engine.
- **Scope**: Simplify `worker.py` to lease, fetch, execute, and acknowledge cycles.

### Phase 8: API Routing
- **Objective**: Decouple HTTP/Flask wrapper.
- **Scope**: Split `app.py` into distinct endpoint router modules under `interfaces/api/`.

---

## Verification Plan

Run the test suite at each phase:
- Ensure 100% test coverage for parser formats.
- Run hybrid retrieval benchmarks to verify recall is preserved.
