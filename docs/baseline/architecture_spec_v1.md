# Architecture Specification & Refactoring Plan (v1.1 Final)

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

## Architecture Decision Log (ADR)

- **ADR-001**: Application layer owns orchestration.
- **ADR-002**: Domain models are framework-independent.
- **ADR-003**: All provider implementations must implement `BaseParserProvider`.
- **ADR-004**: Repositories expose domain objects only.
- **ADR-005**: Storage stores raw artifacts only.
- **ADR-006**: Every pipeline stage communicates through DTOs.
- **ADR-007**: Golden Dataset is the single source of truth for regression testing.

---

## Functional Invariants (Do Not Break)

The following behaviours MUST remain identical throughout every refactoring phase:
- Same parser outputs
- Same chunk boundaries
- Same graph structure
- Same embeddings
- Same retrieval ranking
- Same API contracts
- Same worker semantics
- Same database schema (unless explicitly migrated)
- Same authentication behaviour

*Any intentional behaviour change must be accompanied by: (1) ADR update, (2) Contract update, (3) Golden dataset update.*

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
│   ├── states.py               # Pipeline state machine
│   └── events/                 # Domain events
├── dto/                        # Data Transfer Objects
│   ├── parsing.py
│   ├── chunking.py
│   └── retrieval.py
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
│   ├── base.py
│   └── sqlite_pg_repo.py
├── interfaces/                 # Outer-most request delivery mechanisms
│   ├── api/                    # Flask routers
│   └── workers/                # Background runner & queue listeners
└── tests/
    ├── fixtures/               # Golden dataset inputs
    └── expected/               # Golden truth output files
```

---

## Target Implementation Phases & Exit Criteria

### Phase 0: Architecture Baseline ✅
- **Exit Criteria**: All hotspots, dependencies, configurations, and violations are quantified and documented.

### Phase 0.5: Golden Dataset
- **Objective**: Create a permanent benchmark suite containing diverse document fixtures under `tests/fixtures/` and verified outputs under `tests/expected/`.
- **Exit Criteria**: Ground truth JSON outputs frozen for all files in the test suite.

### Phase 1: Safety Net
- **Objective**: Implement comprehensive regression testing verifying the frozen Golden Dataset.
- **Exit Criteria**: 100% pass rate on regression validations using current production codebase.

### Phase 2: Domain Models + DTOs + Contracts + Adapters
- **Objective**: Introduce structured representations and mappings without breaking legacy setups.
- **Exit Criteria**: Integration tests pass using adapters and new contracts while using the legacy pipeline.

### Phase 3: Provider Abstraction
- **Objective**: Decouple the parser from concrete LLM APIs via `BaseParserProvider`.
- **Exit Criteria**:
  - Parser contains zero provider-specific library imports or direct `os.environ` updates.
  - Golden dataset outputs match perfectly.

### Phase 4: Storage + Repository Abstraction
- **Objective**: Segregate physical assets from query engines.
- **Exit Criteria**: All DB/Redis/Qdrant references decoupled from core service scripts.

### Phase 5: Parser Refactor
- **Objective**: Decompose parser code by responsibility (orchestrator, graph builder, routing).
- **Exit Criteria**: Total `pdf_parser.py` code modularized. Golden dataset output matches exactly.

### Phase 6: Retrieval Refactor
- **Objective**: Split BM25, dense vector, reranker, and graph expansion into modular application services.
- **Exit Criteria**:
  - Hybrid retrieval unchanged.
  - Recall@5 and Precision@5 >= previous baseline.
  - Average latency unchanged.
  - Golden dataset passes.

### Phase 7: Worker Refactor
- **Objective**: Clean background worker leases and queue mechanisms.
- **Exit Criteria**:
  - Worker restart, lease recovery, and dead worker recovery verified.
  - Retry logic verified with no duplicate task execution.

### Phase 8: API Refactor
- **Objective**: Restructure HTTP router endpoints.
- **Exit Criteria**:
  - `app.py` < 500 LOC.
  - Controllers contain zero business logic.
  - Services contain zero Flask imports.
  - Routes contain only request validation.

### Phase 9: Performance & Production Hardening
- **Objective**: Caching, OpenTelemetry, metrics exporting, load testing.
- **Exit Criteria**:
  - P95 latency, CPU, and memory targets achieved.
  - OpenTelemetry traces and Prometheus metrics working.
  - Load and memory-leak tests passed.

---

## Progress Tracking

| Phase | Status | Branch | Tests |
| :--- | :--- | :--- | :--- |
| **0** | ✅ | `main` | N/A |
| **0.5** | ⬜ | `phase-0.5` | Pending |
| **1** | ⬜ | `phase-1` | Pending |
| **2** | ⬜ | `phase-2` | Pending |
| **3** | ⬜ | `phase-3` | Pending |
| **4** | ⬜ | `phase-4` | Pending |
| **5** | ⬜ | `phase-5` | Pending |
| **6** | ⬜ | `phase-6` | Pending |
| **7** | ⬜ | `phase-7` | Pending |
| **8** | ⬜ | `phase-8` | Pending |
| **9** | ⬜ | `phase-9` | Pending |
