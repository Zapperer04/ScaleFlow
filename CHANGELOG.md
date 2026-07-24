# Changelog (ScaleFlow MR-RAG)

All notable changes to this project will be documented in this file.

---

## [1.0.0] - 2026-07-24
### Added
- **VLM-First Parsing**: Baseline Vision-Language Model extraction with layout and PyPDF fallbacks.
- **Expert Ensemble**: Cosine similarity, structural graph traversal, table coordinate parsing, and entity detection.
- **Serving Platform**: Flask routing, Redis task queue, worker leases, JWT authentication, and RBAC authorization.
- **Validation Framework**: Automated Pytest suites and out-of-process benchmark scripts (quality, latency, scalability, load tests).
- **Qualification Gates**: Assertion-based gates marking the platform as **"Production Qualified under the evaluated benchmark suite"**.

---

## [0.9.0-beta] - 2026-06-15
### Added
- Beta implementation of Qdrant vector database storage.
- Basic Redis-based worker orchestration.
