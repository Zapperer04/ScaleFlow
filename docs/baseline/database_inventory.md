# Database Inventory

## Tables

### 1. `pipelines`
- **Columns**: `id`, `name`, `pipeline_type`, `status`, `started_at`, `completed_at`, `error_message`, `owner_instance_id`, `owner_lease_expires_at`, `ownership_version`, `is_critical`, `segment_counter`, `created_at`, `updated_at`, `version`.
- **Indexes**: `idx_pipelines_status`, `idx_pipelines_owner_instance_id`, `idx_pipelines_created_at`.

### 2. `tasks`
- **Columns**: `id`, `type`, `data`, `status`, `priority`, `dependencies`, `retry_count`, `max_retries`, `error_message`, `started_at`, `completed_at`, `assigned_worker_id`, `lease_token`, `lease_expires_at`, `recovered_count`, `lease_renewal_count`, `last_progress_at`, `progress_json`, `pipeline_id`, `input_artifact_ids`, `output_artifact_ids`, `blocked_reason`, `deferred_at`, `created_at`, `updated_at`, `version`.
- **Indexes**: `idx_tasks_status`, `idx_tasks_pipeline_id`, `idx_tasks_lease_expires_at`, `idx_tasks_status_priority`.

### 3. `orchestration_events`
- **Columns**: `id`, `event_type`, `task_id`, `pipeline_id`, `worker_id`, `event_category`, `event_data`, `correlation_id`, `idempotency_key`, `segment_index`, `event_version`, `schema_version`, `created_at`, `updated_at`.

### 4. `worker_registry`
- **Columns**: `worker_id`, `capabilities`, `resource_limits`, `last_seen`, `status`, `created_at`, `updated_at`.\n