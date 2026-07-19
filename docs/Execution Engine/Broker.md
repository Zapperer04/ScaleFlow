# ResourceBroker Documentation

## Responsibilities
The `ResourceBroker` is responsible for selecting the best available compute resource (e.g. VLM, LLM, local GPU) to execute a given `JobSpec` based on requirements, availability, and health.

## Inputs
- `ProviderRequirements`: Capability constraints (context size, multimodal requirements).

## Outputs
- `ResourceProvider`: The chosen, qualified adapter.

## Failure Modes
- **No capable resources found:** Raises exception to be handled by the Execution Worker.

## Invariants
- **Rule 3:** Broker never retries.
- **Rule 10:** Schedulers and Brokers never inspect provider internals.

## Metrics Emitted
- `broker_selection_seconds` (latency to resolve routing).
