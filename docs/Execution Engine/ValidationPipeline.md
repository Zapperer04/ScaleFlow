# ValidationPipeline Documentation

## Responsibilities
Enforces schema validation and invokes normalizers to translate provider-specific ASTs into ScaleFlow's Canonical JSON Graph.

## Inputs
- Raw JSON string output by provider.

## Outputs
- Canonical JSON Graph (dict).

## Invariants
- **Rule 2:** Normalizers never call providers. They act purely as data mappers.
