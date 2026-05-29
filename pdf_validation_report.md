# Document Intelligence Hardening — Validation Report
**Date:** 2026-05-29 13:19:37

## Summary
| Category | File | Parse Status | Parser Used | Duration | Chunks |
|---|---|---|---|---|---|
| A | category_A_simple.pdf | completed | pypdf | 115.16s | 1 |
| B | category_B_academic.pdf | completed | pypdf | 7.36s | 1 |
| C | category_C_large.pdf | completed | pypdf | 156.56s | 200 |
| D | category_D_scanned.pdf | completed | ocr_fallback | 58.78s | 0 |
| E | category_E_malformed.pdf | failed | N/A | 33.72s | 0 |
| K | Kaustav_OOPsAssign2.pdf | failed | N/A | 31.29s | 0 |

### Category A: Simple Text PDF
- **Status**: SUCCESS
- **Parser Used**: pypdf
- **OCR Activated**: NO
- **OCR Confidence**: 100.0%
- **Printable Ratio**: 100.00%
- **Dictionary Word Ratio**: 52.94%
- **Coherence Score**: 90.2/100.0
- **Parsed Preview**: `ScaleFlow Category A Test Document This is a simple text PDF designed to test basic parsing capabilities. It has no images, no complex layout, and sho...`
- **Chunks Generated**: 1
- **Duration**: 115.16s

**Retrieval Tests:**

### Category B: Academic PDF (equations/references)
- **Status**: SUCCESS
- **Parser Used**: pypdf
- **OCR Activated**: NO
- **OCR Confidence**: 100.0%
- **Printable Ratio**: 100.00%
- **Dictionary Word Ratio**: 51.16%
- **Coherence Score**: 93.0/100.0
- **Parsed Preview**: `Advanced Orchestration in Distributed Systems Jane Doe, John Smith Abstract: This paper explores the performance of distributed DAG execution in highl...`
- **Chunks Generated**: 1
- **Duration**: 7.36s

### Category C: Large PDF (50+ pages)
- **Status**: SUCCESS
- **Parser Used**: pypdf
- **OCR Activated**: NO
- **OCR Confidence**: 100.0%
- **Printable Ratio**: 100.00%
- **Dictionary Word Ratio**: 68.25%
- **Coherence Score**: 100.0/100.0
- **Parsed Preview**: `Page 1 of Large Document This is a repeated paragraph to simulate a large document and test chunking caps, memory limits, and timeouts. ScaleFlow must...`
- **Chunks Generated**: 200
- **Duration**: 156.56s

### Category D: Scanned/Image PDF
- **Status**: SUCCESS
- **Parser Used**: ocr_fallback
- **OCR Activated**: YES
- **OCR Confidence**: 82.5%
- **Printable Ratio**: 100.00%
- **Dictionary Word Ratio**: 44.44%
- **Coherence Score**: 72.2/100.0
- **Parsed Preview**: `This isan image-based PDF. pypdfand pdfplumber will fail to extract this text Itshould trigger the OCR fallback....`
- **Chunks Generated**: 0
- **Duration**: 58.78s

### Category E: Malformed/Corrupted PDF
- **Status**: FAILED (Expected for malformed)
- **Error**: Stream has ended unexpectedly

### Category K: Kaustav OOPs Assignment 2 PDF
- **Status**: FAILED (Expected for malformed)
- **Error**: Document unreadable / OCR quality too low: Dictionary-word ratio 6.40% is below threshold 20.00%