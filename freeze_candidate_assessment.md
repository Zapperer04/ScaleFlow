# ScaleFlow Freeze Candidate Assessment

This document provides a realistic, evidence-based assessment of ScaleFlow's current software freeze state.

---

## 1. Stable Areas (Proven & Hardened)

These components have run through validation validation suites, integration tests, and multi-tenant simulations without regressions.

### 1.1. Weighted Round-Robin Scheduling
* **Status**: Stable.
* **Evidence**: Priority-based task selection (high, medium, low) operates reliably under active backpressure, preventing starvation.

### 1.2. Lease-Based Task Recovery
* **Status**: Stable.
* **Evidence**: The recovery daemon successfully detects offline worker node leases and re-enqueues orphaned tasks without duplicate executions.

### 1.3. Event Sourcing State Audit
* **Status**: Stable.
* **Evidence**: Pipeline state changes are logged as immutable events in the PostgreSQL database, providing a complete replay trail.

---

## 2. Risky Areas (Requires Monitoring)

These areas present higher operational risk under extreme load or system partitions.

### 2.1. Redis-PostgreSQL State Desynchronization
* **Risk**: Task states are saved in PostgreSQL, while task scheduling IDs are held in Redis lists. If a network partition occurs between Redis and PostgreSQL during a task transition (claim or complete), a task can become stuck in an inconsistent state.
* **Accepted Limitation**: The recovery daemon will eventual-consistently sweep and fix these states.

### 2.2. Heavy OCR Task Resource Spikes
* **Risk**: pytesseract OCR parsing requires rasterizing PDF pages to images. Under high concurrency, this causes massive CPU/memory spikes on the worker nodes, occasionally leading to memory governance limit restarts (RSS limits).
* **Accepted Limitation**: Managed by worker RSS memory checks that raise memory errors rather than causing VM Out-Of-Memory crashes.

---

## 3. Accepted System Limitations

These are known design limits that are accepted for the platform freeze candidate.

### 3.1. Extractive Answer Generation
* **Limitation**: The system generates context-based extractive summaries instead of abstractive generative answers (no LLM reasoning layer is integrated yet).
* **Rationale**: Keeps the core pipeline fast, deterministic, and free of external LLM API costs.

### 3.2. Local Upload Storage
* **Limitation**: File uploads are stored on the worker's local filesystem (`storage/uploads/`). In a multi-node cluster, workers on separate machines cannot access files uploaded to other machines.
* **Rationale**: Sufficient for single-node deployments and testing. Production deployments must configure a shared S3/NFS volume.
