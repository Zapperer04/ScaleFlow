# Frequently Asked Questions (FAQ)

Here are answers to common questions regarding technology choices, design patterns, and scaling characteristics.

---

## 1. Why SQLite for the Graph index?
SQLite provides zero-config relational mapping, keeping local testing simple and fast. Since graph expansion only queries node-edge relationships per document, SQLite provides sufficient single-node performance. For distributed enterprise environments, this can be migrated to Neo4j.

---

## 2. How are custom experts structured?
Subclass `BaseExpert` (see [Plugin Guide](file:///Users/kaustavkumar/Kaustav/Projects/task-schedular/docs/Plugin_System.md)) and add your logic. Register it in `RetrievalOrchestrator` to automatically include its outputs in Reciprocal Rank Fusion (RRF).

---

## 3. Can I run the benchmark suite completely offline?
Yes. Pre-cache all embedding models under `backend/hf_cache/` and set the environment flag:
```bash
export TEST_OFFLINE_MODE=True
```
This forces VLM fallbacks to run locally via `pypdf`/`pdfplumber` without calling external APIs.

---

## 4. Is this system suitable for enterprise production?
The platform has been validated as **"Production Qualified under the evaluated benchmark suite"**, meaning it passes strict quality, latency, resilience, and rate-limiting gates in the benchmark scenarios.
