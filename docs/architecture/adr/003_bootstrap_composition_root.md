# ADR-003: Bootstrap as the Sole Composition Root

## Status
Accepted

## Context
When introducing dependency injection (DI), it is critical to prevent "DI container sprawl" where services directly instantiate their dependencies or lookup services from the container directly (Service Locator anti-pattern). Dependencies must be wired in a single centralized location.

## Decision
- `backend/infrastructure/providers/bootstrap.py` is established as the sole composition root for the application.
- Concrete infrastructure classes (such as `SqlAlchemyDocumentRepository`, `RedisCache`, `QdrantStore`, and `FilesystemStorage`) must only be instantiated inside `bootstrap.py` (or within unit/integration tests).
- All application services receive their dependencies exclusively through constructor injection. No service should have knowledge of how its dependencies are constructed.

## Consequences
- Clean separation of concern between object instantiation and object execution.
- Prevents coupling between application logic and concrete infrastructure types.
- Makes mocking and swapping dependencies for testing trivial.
