# ScaleFlow Technical Debt Audit Report

This report categorizes the identified technical debt, defects, and optimizations in ScaleFlow into actionable phases.

---

## 1. Must Fix Before Production (Defects / High Risk)

These issues represent architectural vulnerabilities or defects that can lead to data inconsistency, race conditions, or operational failure under load.

### 1.1. Single-Point-of-Failure Database Connections
* **Risk**: The database startup connection block in `models.py` exits immediately if PostgreSQL is momentarily unresponsive. There is no retry policy on initialization.
* **Remediation**: Implement a retry loop with exponential backoff on engine connection validation during startup.

### 1.2. Lack of Database Indices on Pipeline Foreign Keys
* **Risk**: The `Artifact`, `TaskDependency`, and `TaskLog` tables contain foreign keys referencing `pipelines(id)` and `tasks(id)`. These keys lack explicit database indices, which will cause queries to degrade from Index Scans to Full Table Scans as data scales.
* **Remediation**: Add SQLAlchemy indexes on `pipeline_id` and `task_id` fields inside `models.py`.

### 1.3. Synchronous Task Claim Network Overhead
* **Risk**: When a worker claims a task, it performs synchronous HTTP PATCH calls to the orchestrator. If the orchestrator is heavily loaded, the worker blocks.
* **Remediation**: Introduce a local worker retry buffer or asynchronous task state synchronization using message brokers.

### 1.4. Hardcoded Database Ports in Local Validation Configurations
* **Risk**: Several test validation scripts (`validate_pdf_pipeline.py`, `run_all_validations.py`) hardcode target ports or API secrets instead of loading them directly from a unified config.
* **Remediation**: Refactor all test suites to import settings from `backend/config.py`.

---

## 2. Nice To Have (Optimizations)

These items improve execution efficiency, reduce overheads, or simplify maintenance without resolving critical defects.

### 2.1. Dynamic Embedding Model Caching
* **Optimization**: Loading the SentenceTransformer model takes 2-4 seconds. If a worker goes offline and restarts frequently, this introduces overhead.
* **Remediation**: Cache the initialized model state locally on the worker filesystem, or run a dedicated embedding service container accessed via gRPC.

### 2.2. Bulk Artifact Registry Endpoint
* **Optimization**: Currently, workers post each output artifact individually via POST `/artifacts`. For pipelines generating hundreds of pages or partitions, this floods the connection pool.
* **Remediation**: Implement POST `/artifacts/bulk` in `app.py`.

### 2.3. Asynchronous Worker Logging
* **Optimization**: Worker trace calls (`emit_task_trace`) perform synchronous HTTP requests to the API during task runs. Under heavy CPU workloads, this slows task processing.
* **Remediation**: Buffer trace logs in memory and flush them in batches using a background thread.

---

## 3. Domain-Specific Future Work (Adapters / Customizations)

These tasks represent capabilities that depend on the specific target domain selection and are not required for core platform stability.

### 3.1. Fine-tuned Embeddings for Technical Glossaries
* **Scope**: The base `all-MiniLM-L6-v2` model is generic. Legal, medical, or agricultural domains have specialized vocabularies that require specialized models.
* **Remediation**: Configure `EMBEDDING_MODEL` in `config.py` to target custom models (e.g. `Legal-BERT` or domain-specific sentence transformers) and adjust `EMBEDDING_DIMENSION`.

### 3.2. Form/Table Extraction Parsers
* **Scope**: In legal contracts and reports, key data resides in tables. The current textual output from pypdf/pdfplumber ignores layouts.
* **Remediation**: Integrate layout-aware extractors (such as Unstructured layout parsers or PyMuPDF table parsing) inside the future domain adapters.

### 3.3. Prompt Engineering and LLM Answer Guardrails
* **Scope**: Extractive answer generation is highly sensitive to the domain prompt. Legal needs exact quotes; agricultural needs simple explanations.
* **Remediation**: Define prompt-formatting templates in pluggable adapter files.
