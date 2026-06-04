# ScaleFlow Retrieval Accuracy Comparison
**Date:** 2026-06-03

## Categories B & C Retrieval Quality

| Engine | Cat B Similarity | Cat B Success | Cat B Recovered KWs | Cat C Similarity | Cat C Success | Cat C Recovered KWs |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Tesseract** | 0.000 | False | 0 | 0.000 | False | 0 |
| **PaddleOCR** | N/A | False | 0 | N/A | False | 0 |
| **EasyOCR** | N/A | False | 0 | N/A | False | 0 |
| **DocTR** | N/A | False | 0 | N/A | False | 0 |
| **Surya** | N/A | False | 0 | N/A | False | 0 |

## Analysis
Because the deep-learning engines failed to initialize in the isolated worker environment, no chunks were extracted and indexed. Tesseract successfully initialized but failed to extract the raw text due to an infrastructure dependency failure (Poppler path rendering isolation). 

**Resulting Retrieval Quality:** 0.00 across all engines. 

This proves that extraction capability cannot be separated from infrastructure constraints. An engine with high theoretical accuracy provides 0.00 retrieval quality if it crashes the worker node or fails to initialize.
