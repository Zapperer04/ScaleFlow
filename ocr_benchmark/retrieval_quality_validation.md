# Phase 4 — Retrieval Quality Validation Report

## Query Definitions

| Category | Query | Expected Keyword |
| :--- | :--- | :--- |
| B | What do distributed ledger systems require? | `throughput` |
| C | What does replication across nodes ensure? | `reliability` |

## Per-Engine Retrieval Results

| Engine | Query Cat | Similarity | Retrieved Cat | Correct | Keyword Hit |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Tesseract | B | 0.5469 | E | ❌ | ❌ |
| Tesseract | C | 0.5454 | E | ❌ | ❌ |
| PaddleOCR | B | 0.0 | N/A | ❌ | ❌ |
| PaddleOCR | C | 0.0 | N/A | ❌ | ❌ |
| EasyOCR | B | 0.5077 | B | ✅ | ✅ |
| EasyOCR | C | 0.5191 | E | ❌ | ❌ |
| DocTR | B | 0.4847 | E | ❌ | ❌ |
| DocTR | C | 0.4991 | E | ❌ | ❌ |
| Surya | B | -0.0179 | G | ❌ | ❌ |
| Surya | C | 0.0047 | C | ✅ | ❌ |