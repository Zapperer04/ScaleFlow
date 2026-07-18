# Redis Queue & Inventory

## Queue Channels
- **Priority Queues**: `queue:high`, `queue:medium`, `queue:low` (mapped based on worker capabilities).
- **Format**: JSON serialized strings representing worker tasks.
- **Retry Mechanism**: Rejected tasks are returned to the DB status block and re-queued by the manager check loop.\n