# Phase 3 — Warm vs Cold Start + Peak Memory Benchmark

> **Cold Start** = time to load model weights from local disk cache into RAM.
> **First Inference** = extraction on the first document (model warm-up).
> **Warm Inference** = extraction on the second document (model already resident).
> **Peak RSS** = maximum resident memory observed during the full session.

| Engine | Cold Start (s) | Init ΔMem (MB) | First Inference (s) | Warm Inference (s) | Peak RSS (MB) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Tesseract | 1.66 | 51.0 | 1.306 | 1.046 | 129.2 |
| PaddleOCR | 20.839 | 693.7 | 0.0 | 0.0 | 764.1 |
| EasyOCR | 4.753 | 85.2 | 32.877 | 33.65 | 4354.2 |
| DocTR | 8.046 | -373.1 | 2.858 | 2.266 | 3779.3 |
| Surya | 3.385 | 134.0 | 7.987 | 6.953 | 3908.7 |

## Analysis

Warm inference latency is the production-relevant metric for a pre-loaded microservice.
Cold start latency is the production-relevant metric for ephemeral/autoscaled worker nodes.

Engines with Cold Start > 30s cannot be embedded in on-demand ingest workers without
degrading ingestion SLA. They require persistent pre-loaded service deployment.