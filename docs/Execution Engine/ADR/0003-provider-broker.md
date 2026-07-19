# ADR 0003: Scoring-Based Resource Broker

## Context
The system uses multiple external API providers (Gemini, OpenRouter, Groq) with volatile rate limits and varying capability sets. Hardcoded round-robin or first-match assignment resulted in suboptimal provider matching and cascading failures.

## Decision
We decouple resource allocation into a `ResourceBroker` utilizing:
- **Capability Matching:** Matching required context windows, schema output types, and modalities.
- **Dynamic EWMA Scoring:** Scoring health (0-100) on latency, 429 frequency, and malformed rates.
- **Provider Status:** Binary availability check (RPM/RPD status).

The broker always routes jobs to the available resource with the highest score.

## Consequences
- **Pros:** Adapting to new APIs or shifting workloads (e.g. from Gemini to a local GPU) requires registering capabilities, with zero modifications to scheduling logic.
- **Cons:** Score updates introduce minimal write load to Redis.
