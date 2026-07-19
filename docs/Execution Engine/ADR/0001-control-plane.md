# ADR 0001: Control Plane vs. Data Plane Separation

## Context
Legacy workers executed parsing tasks synchronously, directly calling APIs. This combined routing, rate-limit management, lock acquisition, and parsing into a single monolithic block, causing resource starvation and API 429 oversubscription.

## Decision
We split the Resource Execution Engine into a **Control Plane** (Leases, Quota management, Broker decisions) and a **Data Plane** (Adapters, Normalizers, Validators). 

- Workers run on the Data Plane and only execute the work assigned to them.
- Decisions on *which* provider gets selected, *when* a job runs, and *what* locks are held are decoupled into the Control Plane.

## Consequences
- **Pros:** Orchestration logic remains clean and testable without active provider connections.
- **Cons:** Introduces minor IPC overhead between worker execution threads and the central Redis quota database.
