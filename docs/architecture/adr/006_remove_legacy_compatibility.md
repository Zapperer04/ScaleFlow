# ADR 006: Remove Legacy Compatibility Layers

## Status
Accepted

## Context
During the incremental transition to the Clean Architecture in Phases 2–4, several temporary shims and compatibility layers were introduced to prevent disruption to existing clients and services:
1. `LegacyRepositoryAdapter` – adapted domain aggregates to the old SQLAlchemy models.
2. `LegacyStorageAdapter` – mapped domain dictionary objects to JSON bytes on disk.
3. `CompatibleDocument` – a subclass shim of the `Document` domain aggregate that exposed dict-style attributes (`.pages`, `.document_graph`, `.stats`) to maintain backward compatibility with old parser code.
4. `VLMCompatibilityAdapter` – dynamically injected provider names into environment variables (e.g. `VLM_PROVIDER`).

Now that all clients, endpoints, and background tasks have successfully migrated to constructor-injected abstractions and DTOs, these shims are obsolete.

## Decision
1. **Permanent Deletion**: Delete `LegacyRepositoryAdapter`, `LegacyStorageAdapter`, `CompatibleDocument`, and `VLMCompatibilityAdapter`.
2. **Absorb Serialization**: Migrate the serialization helpers (`_to_bytes` and `_from_bytes`) directly into `ArtifactStore` as private methods. The serialization output remains byte-for-byte identical to the legacy implementation.
3. **Domain Representation**: Return a clean `Document` aggregate directly from `ParsingServiceImpl`. Store parser-layer outputs (`document_graph`, `stats`, and the raw pages list) in `Document.metadata`.
4. **Explicit Parameter Passing**: Eliminate `os.environ` mutations. Pass `provider_name` down the parsing and preprocessor function chain explicitly.

## Consequences
- Single unified clean architecture path remains.
- No legacy translation code paths left to maintain.
- Standardized metadata access via dictionary fields on `Document.metadata`.
- **Architectural Guidance**: Metadata should not become a general-purpose extension mechanism for future domain concepts. Concepts that belong to the core business logic or are domain aggregates should be modeled explicitly on domain objects.
