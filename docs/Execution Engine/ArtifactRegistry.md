# ArtifactRegistry Documentation

## Responsibilities
Saves and loads raw files and intermediate AST graphs. Keeps workers completely stateless.

## Inputs
- Content (bytes)
- Content Type & Version

## Outputs
- `ArtifactRef`: Contains unique URI, hash, and metadata.

## Invariants
- **Rule 9:** Every artifact is versioned and content-hashed (SHA256) for cache consistency.
