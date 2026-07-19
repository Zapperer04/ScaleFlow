# LeaseManager Documentation

## Responsibilities
Enforces exactly-once execution semantics by holding short-term locks on active job IDs.

## Inputs
- `job_id`: Unique identifier of the Job.
- `ttl_seconds`: Duration before the lease expires.

## Outputs
- `lease_id`: Token to release the lease.

## Failure Modes
- **Lease acquisition failed:** The worker aborts execution and skips the job, preventing concurrent processing.

## Invariants
- Lease release is authenticated: Only the holding worker (via `lease_id` verification) can release the lease.

## Metrics Emitted
- `lease_wait_seconds` (time spent acquiring lease).
