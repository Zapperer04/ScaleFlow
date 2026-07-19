# ADR 0004: Versioned Artifact Registry

## Context
Workers processed pages locally, maintaining temp files. If a worker crashed midway, partial state was lost, and resuming was impossible without re-ingesting from scratch.

## Decision
We enforce that all inputs and outputs are versioned, content-hashed, and stored in a centralized `ArtifactRegistry` (`LocalArtifactRegistry` or S3). The output of one task (e.g. `raw_ast.json`) is written back as an artifact, which the next task in the pipeline (e.g. validation) loads.

## Consequences
- **Pros:** Workers are 100% stateless. Worker crashes are completely recoverable by loading the latest written artifact and resuming execution.
- **Cons:** Storage footprint is larger due to storing intermediate artifacts.
