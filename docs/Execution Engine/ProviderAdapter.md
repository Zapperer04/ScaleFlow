# ProviderAdapter Documentation

## Responsibilities
Wraps external API or local compute endpoints, handling authentication, formatting prompt structures, and executing raw inference requests.

## Inputs
- `ArtifactRef`
- Prompt configuration payload

## Outputs
- Raw provider-specific AST (JSON dict).

## Invariants
- **Rule 1:** Adapters never normalize raw responses to the canonical graph. They return intermediate outputs representing raw JSON.
