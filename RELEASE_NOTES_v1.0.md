# Release Notes - ScaleFlow MR-RAG v1.0.0 (Frozen Release)

We are proud to announce the stable release freeze of **ScaleFlow MR-RAG v1.0**.

This release establishes the baseline architecture for a production-capable, multi-representation document retrieval system.

## Key Highlights

1. **Document Intelligence Core**: Enforces robust PDF parsing fallback tiers (VLM -> Layout Plumber -> PyPDF -> Tesseract OCR) to guarantee document extraction success across skewed, scanned, and clean digital documents.
2. **Multi-Representation Expert Ensemble**: Dynamic query intent mapping routes queries to specific database layers, merging results via Reciprocal Rank Fusion (RRF) and Cross-Encoder rerankers.
3. **Task Orchestration Serving Platform**: Employs distributed, lease-based Redis queues to process file uploads and indexing pipelines asynchronously.
4. **Research-Grade Scientific Benchmarks**: Delivers dedicated testing scripts (latency percentiles, scalability up to 100,000 pages, resource usage profiling, and regression tracking).
5. **Quality Qualification**: The codebase meets all quality validation metrics to declare the version **"Production Qualified under the evaluated benchmark suite"**.

## Upgrade Path
This is the baseline stable release. Docker Compose files and helm configurations are frozen.
