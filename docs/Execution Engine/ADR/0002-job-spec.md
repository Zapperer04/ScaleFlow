# ADR 0002: Immutable Job Specification (`JobSpec`)

## Context
Legacy task queues fanned out documents using raw image arrays or local file paths, which made worker states volatile, retries non-deterministic, and execution history difficult to trace.

## Decision
All jobs scheduled in the execution engine are modeled via an immutable `JobSpec` (Pydantic `frozen=True`). The `JobSpec` contains `requirements`, `estimated_cost`, and an `attempts` log, but holds no binary payloads directly (only versioned `ArtifactRef` references).

## Consequences
- **Pros:** Guaranteed execution reproducibility. Jobs can be safely retried or re-routed based on their history without risking side-effects or state mutation bugs.
- **Cons:** Requires compiling a `JobSpec` object prior to execution.
