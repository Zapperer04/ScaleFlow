# ADR-001: Domain Layer Independence from Infrastructure

## Status
Accepted

## Context
In Clean Architecture, the domain layer represents the core business logic and rules of the system. In previous versions of the codebase, business services directly imported database sessions, Redis clients, Qdrant client objects, and performed raw filesystem operations. This tight coupling makes the code hard to test, difficult to scale, and prone to breaking during database migrations.

## Decision
- The Domain layer (entities, aggregates, value objects, exceptions, and repository interfaces) must contain zero imports or dependencies on the infrastructure layer (`backend/infrastructure/`).
- Repository interfaces define abstract contracts. Concrete persistence implementations (SQLAlchemy, Redis, Qdrant, Filesystem) reside exclusively inside the infrastructure layer.
- Dependencies flow inwards: `Infrastructure -> Repositories (Interfaces) -> Domain`. The reverse direction is strictly forbidden and checked via AST architectural fitness tests.

## Consequences
- Core domain logic can be tested in isolation using pure mocks or in-memory repositories.
- Replacing or modifying storage technologies (e.g. moving from SQLite to PostgreSQL, or local disk to S3) will not require changing any business logic.
