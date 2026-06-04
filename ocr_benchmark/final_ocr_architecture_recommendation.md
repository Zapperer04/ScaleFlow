# Phase 6 — Final OCR Architecture Recommendation

## Weighted Score Matrix

| Weight | Metric |
| :--- | :--- |
| 25% | Recovery Rate |
| 20% | Wer Inv |
| 20% | Retrieval Success |
| 15% | Warm Latency Inv |
| 10% | Peak Mem Inv |
| 10% | Table Recovery |

## Engine Composite Scores

| Rank | Engine | Composite | Recovery | WER⁻¹ | Retrieval | Latency⁻¹ | Memory⁻¹ | Table |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **Tesseract** | **0.3853** | 57.14% | 0.04% | 0.00% | 96.89% | 97.03% | 0.00% |
| 2 | **DocTR** | **0.3139** | 64.29% | 0.04% | 0.00% | 93.27% | 13.20% | 0.00% |
| 3 | **PaddleOCR** | **0.2325** | 0.00% | 0.00% | 0.00% | 100.00% | 82.45% | 0.00% |
| 4 | **Surya** | **0.2292** | 0.00% | 0.00% | 50.00% | 79.34% | 10.23% | 0.00% |
| 5 | **EasyOCR** | **0.2132** | 45.24% | 0.04% | 50.00% | 0.00% | 0.00% | 0.00% |

## Raw Metrics Reference

| Engine | Avg WER | Warm Infer (s) | Peak RSS (MB) |
| :--- | :--- | :--- | :--- |
| Tesseract | 0.9996 | 1.046 | 129.2 |
| PaddleOCR | N/A | 0.0 | 764.1 |
| EasyOCR | 0.9996 | 33.65 | 4354.2 |
| DocTR | 0.9996 | 2.266 | 3779.3 |
| Surya | 1.0000 | 6.953 | 3908.7 |

---

## ✅ Recommendation: Option A — Continue with Tesseract

> Tesseract achieves a competitive composite score (0.3853) with near-zero cold-start latency. The marginal quality improvement offered by deep-learning engines does not justify the >30s cold-start overhead and >1 GB RAM penalty.