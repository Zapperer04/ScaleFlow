# ScaleFlow OCR Capability Matrix
**Date:** 2026-06-03

## Engine Support Matrix

*(Based on empirical benchmark initialization constraints on standard ingest workers)*

| Engine | Typed Text | Low DPI | Handwriting | Tables | Mixed Docs | Multi-column |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Tesseract** | Yes | No | No | No | No | No |
| **PaddleOCR** | N/A* | N/A* | N/A* | N/A* | N/A* | N/A* |
| **EasyOCR** | N/A* | N/A* | N/A* | N/A* | N/A* | N/A* |
| **DocTR** | N/A* | N/A* | N/A* | N/A* | N/A* | N/A* |
| **Surya OCR**| N/A* | N/A* | N/A* | N/A* | N/A* | N/A* |

*\* Note: N/A indicates the engine failed to initialize in the isolated CPU benchmark environment. While literature states DocTR/Surya support Handwriting/Tables natively, empirical capability on our current infrastructure is zero until hybrid GPU offloading is implemented.*
