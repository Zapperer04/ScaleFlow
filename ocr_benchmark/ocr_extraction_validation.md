# Phase 2 — OCR Extraction Validation Report

## Synthetic Image-Only Test

| Engine | Init (s) | Synthetic chars | Success | Snippet |
| :--- | :--- | :--- | :--- | :--- |
| Tesseract | 0.851 | 43 | OK | The quick brown fox jumpsover the lazy dog, |
| PaddleOCR | 18.6 | 0 | FAIL |  |
| EasyOCR | 4.539 | 42 | OK | The quick brown fox jumpsover the lazydog_ |
| DocTR | 19.816 | 44 | OK | The quick brown fox jumps overthe laz zydog. |
| Surya | 3.293 | 67 | OK | ERROR: AttributeError: 'PolygonBox' object has no attribute 'label' |

## Extraction by Category

| Engine | Cat | Char Count | Latency (s) | Keyword Hits | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Tesseract | B | 142 | 0.86 | throughput, ledger, distributed | ✅ |
| Tesseract | C | 142 | 0.924 | replication, nodes, reliability | ✅ |
| Tesseract | D | 78 | 9.019 | test | ✅ |
| Tesseract | E | 411 | 1.178 | none | ✅ |
| Tesseract | F | 350 | 0.993 | none | ✅ |
| Tesseract | G | 114 | 0.824 | john, handwriting | ✅ |
| Tesseract | H | 49 | 1.269 | handwritten | ✅ |
| PaddleOCR | B | 0 | N/A | none | ❌ Zero chars |
| PaddleOCR | C | 0 | N/A | none | ❌ Zero chars |
| PaddleOCR | D | 0 | N/A | none | ❌ Zero chars |
| PaddleOCR | E | 0 | N/A | none | ❌ Zero chars |
| PaddleOCR | F | 0 | N/A | none | ❌ Zero chars |
| PaddleOCR | G | 0 | N/A | none | ❌ Zero chars |
| PaddleOCR | H | 0 | N/A | none | ❌ Zero chars |
| EasyOCR | B | 133 | 30.58 | throughput, ledger, distributed | ✅ |
| EasyOCR | C | 136 | 36.271 | nodes, reliability | ✅ |
| EasyOCR | D | 130 | 58.964 | document, test | ✅ |
| EasyOCR | E | 389 | 63.049 | none | ✅ |
| EasyOCR | F | 345 | 70.853 | none | ✅ |
| EasyOCR | G | 110 | 68.661 | john | ✅ |
| EasyOCR | H | 48 | 57.332 | none | ✅ |
| DocTR | B | 143 | 3.0 | throughput, ledger, distributed | ✅ |
| DocTR | C | 113 | 3.003 | replication, nodes, reliability | ✅ |
| DocTR | D | 130 | 3.304 | document, test | ✅ |
| DocTR | E | 405 | 4.723 | none | ✅ |
| DocTR | F | 346 | 5.409 | none | ✅ |
| DocTR | G | 110 | 3.056 | john, handwriting | ✅ |
| DocTR | H | 47 | 2.719 | handwritten | ✅ |
| Surya | B | 67 | 7.289 | none | ✅ |
| Surya | C | 67 | 6.484 | none | ✅ |
| Surya | D | 67 | 6.604 | none | ✅ |
| Surya | E | 67 | 8.216 | none | ✅ |
| Surya | F | 67 | 8.263 | none | ✅ |
| Surya | G | 67 | 6.44 | none | ✅ |
| Surya | H | 67 | 6.622 | none | ✅ |

## Extraction Success Summary

- **Category B:** ✅ At least one engine extracted text
- **Category C:** ✅ At least one engine extracted text
- **Category E:** ✅ At least one engine extracted text