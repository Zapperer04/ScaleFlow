# Scheduler Documentation

## Responsibilities
Ensures fair resource utilization, prevents queue starvation, and manages job backlogs.

## Invariants
- Round-robins processing tasks by document IDs using the `InterleavedFairQueue` implementation.
- Emits queue metrics (e.g. `scheduler_queue_depth`, `scheduler_oldest_job_age`).
