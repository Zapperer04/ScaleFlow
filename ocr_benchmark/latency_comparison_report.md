# ScaleFlow OCR Latency Comparison Report
**Date:** 2026-06-03

## Initialization & Latency Metrics

| Engine | Cold Startup Time (s) | Memory Usage (MB) | Status |
| :--- | :--- | :--- | :--- |
| **Tesseract** | 0.000s | N/A | Success |
| **PaddleOCR** | FAILED | N/A | Code Error (`show_log`) |
| **EasyOCR** | 366.243s | N/A | Initialized |
| **DocTR** | 308.680s | N/A | Initialized |
| **Surya** | 33.988s | N/A | Initialized |

## Analysis
Tesseract initializes instantly (0.000s) because it executes as a lightweight system subprocess via `pytesseract`. 

The deep-learning models (EasyOCR, DocTR, Surya) successfully installed and initialized, but they exhibit **massive cold-start latency (30 - 360+ seconds)** on the first run due to downloading hundreds of megabytes of tensor weights (ResNet, CRAFT, ViT) into the worker's cache. 

If ScaleFlow ingests documents via standard, ephemeral worker nodes, loading these architectures on-demand will completely destroy ingestion latency SLAs. They must be pre-loaded in memory on a persistent, dedicated microservice layer.
