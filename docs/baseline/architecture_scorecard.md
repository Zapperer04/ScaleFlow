# Current Architecture Scorecard

| Category | Score (1-10) | Explanation |
| :--- | :--- | :--- |
| **Maintainability** | 3/10 | Monolithic file structures (`app.py`, `worker.py`) make finding, reviewing, and patching code slow and risky. |
| **Coupling** | 4/10 | Services depend tightly on internal details of database tables. Tight cycles exist between API routes and task state steps. |
| **Cohesion** | 5/10 | Helper modules (`document_preprocessor`) are well-focused on their domains, but core orchestration is split across several files. |
| **Scalability** | 4/10 | Queue architecture handles distributed task dispatching, but local BM25 indexing and state locks degrade horizontal scaling. |
| **Testability** | 5/10 | Integration tests exist, but mocking remote resources is difficult due to the lack of abstract interfaces. |
| **Extensibility** | 3/10 | Adding a new ingestion parser stage requires hardcoded updates in the `dag_builder` and `task_registry`. |
| **Reliability** | 6/10 | Lease management and retry policies prevent complete dropouts, but event timeouts are common under load. |
| **Production Readiness** | 4/10 | Single-point-of-failure database bindings and raw environment file reliance are unsuitable for secure staging. |\n