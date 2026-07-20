# ADR 009: Artifact Registry as System of Record

## Context

During Phase 2 (Production Qualification & Live Shadow Validation), we collect extensive benchmark trials, shadow parser outputs, execution latency details, and graph comparator parity scores.
Previously, reports and metrics were generated dynamically and written directly by active workers or shadow runners to ad-hoc files. This creates a tight coupling between the execution runtime and the reporting logic, risks inconsistent formats, and makes debugging historic runs difficult.

## Decision

We will establish the **Artifact Registry** as the single system of record for all execution telemetry, historic runs, and metadata.
- Every execution run creates an **Execution Manifest** (`execution_manifest.json`) containing environmental parameters, model capability versions, schema hashes, and active module versions (normalizer, validator).
- The Execution Manifest, alongside raw/canonical output graphs, is stored directly in the Artifact Registry as versioned binaries or JSON payloads.
- All post-run reports (e.g., `provider_report.md`, `provider_history.json`, `candidate_queue.json`, and dashboards) are derived *exclusively* by querying records stored in the Artifact Registry.

## Consequences

- **Pros**:
  - Stateless workers: Workers do not perform ad-hoc report writing or handle filesystem telemetry.
  - Reproducibility: Every graph comparison or benchmark run can be perfectly reconstructed using the corresponding execution manifest.
  - Flexibility: New reports and analytics can be developed and run retrospectively over historical artifacts.
- **Cons**:
  - Slight storage overhead for storing run manifests, which can be mitigated via retention policies.
