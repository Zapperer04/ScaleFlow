# ADR-002: Repository Implementations as Legacy Persistence Wrappers

## Status
Accepted

## Context
Refactoring the database access layer in a production system carries a high risk of regression, query performance degradation, and data schema corruption. To ensure safe, incremental migration, we need to introduce the persistence abstractions without changing the underlying SQL queries, Redis interactions, or database schemas.

## Decision
- During Phase 4A, all concrete repository implementations (under `backend/infrastructure/persistence/sqlalchemy/`) must act strictly as thin wrappers around existing database queries and SQLAlchemy models.
- No new SQL queries, ORM optimizations, table schema updates, or migrations are allowed.
- The repository implementations call the legacy SQLAlchemy models (`FileRecord`, `Pipeline`, `Artifact`) using the current session manager to prevent any query behavioral drift.

## Consequences
- Guarantees that the Golden Dataset remains byte-for-byte identical.
- Allows existing regression and integration tests to continue passing without modifications.
- Isolates persistence logic under repositories, enabling a clean swap of the persistence layer in Phase 4B.
