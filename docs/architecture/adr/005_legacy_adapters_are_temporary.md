# ADR-005: Legacy Compatibility Adapters as Temporary Migration Anchors

## Status
Accepted

## Context
During refactoring, some legacy application services, workers, or API endpoints still expect ORM-style objects, database records, or raw dictionaries. To prevent changing production behavior, we require a translation layer to bridge the new repository/domain layer with the legacy code. However, keeping these adapters permanently would introduce technical debt.

## Decision
- `legacy_repository_adapter.py` and `legacy_storage_adapter.py` are temporary translation layers introduced solely to facilitate Phase 4A compatibility.
- They must only be referenced within the bootstrap composition root, repositories, or tests.
- These adapters are explicitly scheduled for deprecation and removal in Phase 5, once all services migrate to using clean domain models and DTOs.

## Consequences
- Protects production code from regressions during the abstraction phase.
- Clear technical debt boundaries that are explicitly marked for cleanup.
