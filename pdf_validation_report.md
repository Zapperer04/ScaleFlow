# Document Intelligence Hardening — Validation Report
**Date:** 2026-05-29 12:28:41

## Summary
| Category | File | Parse Status | Parser Used | Duration | Chunks |
|---|---|---|---|---|---|
| A | category_A_simple.pdf | completed | pypdf | 47.14s | 1 |
| B | category_B_academic.pdf | completed | pypdf | 2.32s | 1 |
| C | category_C_large.pdf | completed | pypdf | 29.32s | 200 |
| D | category_D_scanned.pdf | completed | ocr_fallback | 4.31s | 0 |
| E | category_E_malformed.pdf | failed | N/A | 28.7s | 0 |

### Category A: Simple Text PDF
- **Status**: SUCCESS
- **Parser Used**: pypdf
- **Chunks Generated**: 1
- **Duration**: 47.14s

**Retrieval Tests:**

### Category B: Academic PDF (equations/references)
- **Status**: SUCCESS
- **Parser Used**: pypdf
- **Chunks Generated**: 1
- **Duration**: 2.32s

### Category C: Large PDF (50+ pages)
- **Status**: SUCCESS
- **Parser Used**: pypdf
- **Chunks Generated**: 200
- **Duration**: 29.32s

### Category D: Scanned/Image PDF
- **Status**: SUCCESS
- **Parser Used**: ocr_fallback
- **Chunks Generated**: 0
- **Duration**: 4.31s

### Category E: Malformed/Corrupted PDF
- **Status**: FAILED (Expected for malformed)
- **Error**: Stream has ended unexpectedly