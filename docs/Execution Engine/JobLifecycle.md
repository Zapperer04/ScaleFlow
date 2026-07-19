# JobLifecycle Documentation

## Responsibilities
Defines the state progression of a job spec from creation to terminal output.

## Workflow Transitions (Events Emitted)
1. `JOB_CREATED`
2. `LEASE_ACQUIRED`
3. `PROVIDER_SELECTED`
4. `PROMPT_SENT`
5. `STREAM_STARTED`
6. `ARTIFACT_WRITTEN` / `JOB_FAILED`
7. `LEASE_RELEASED`

## Invariants
- **Rule 7:** Every `JobSpec` is immutable.
- **Rule 8:** Every execution step emits a structured immutable event. Status is computed by event histories, not mutation.
