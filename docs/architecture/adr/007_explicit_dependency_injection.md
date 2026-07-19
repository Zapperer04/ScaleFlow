# ADR 007: Explicit Dependency Injection

## Status
Accepted

## Context
Dependency resolution in ScaleFlow previously relied on a module-level global Service Locator pattern via `get_container()` in `bootstrap.py`. This coupled internal services to mutable module-level state and obscured dependencies. Furthermore, the use of mutators (setters) to set up dependencies introduces hidden state mutations.

## Decision
1. **Eliminate get_container()**: Remove the `get_container()` service locator function and any underlying module-level global storage from `bootstrap.py`.
2. **Constructor-Only Injection**: Mandate constructor injection for all production services (e.g. `ParsingServiceImpl`).
3. **Explicit Parameter Propagation**: For flat, non-class utility modules where constructor injection cannot be used without a complete class wrapper refactor (specifically `embedding_service.py`, `vector_store.py`, and `retrieval_service.py`), explicitly pass dependencies (such as the `ArtifactStore`, `CacheStore`, and `VectorStore`) at call sites instead of retrieving them dynamically from global state.
4. **Composition Root Exclusivity**: Use `bootstrap_app()` exclusively at the entry points (e.g. `app.config["CONTAINER"]` initialization in Flask, worker initialization) to construct and wire the application graph.

## Consequences
- Hidden dependencies are exposed, making unit testing simpler with mock parameters.
- Production code is free from mutable global dependency references.
- Decouples application modules from the environment.
