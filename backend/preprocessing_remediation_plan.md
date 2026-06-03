# ScaleFlow Preprocessing Remediation Plan
**Date:** 2026-06-03

## Overview
Following the preprocessing audit which revealed significant regressions in extraction quality and latency, a comprehensive remediation pass was conducted. This pass focuses strictly on preventing harm and reducing latency, rather than expanding features.

## Remediation Actions

### 1. Protect Clean Digital PDFs
Clean, digital-born PDFs with perfect text layers were previously being rasterized and passed through OCR due to aggressive contrast thresholds. 
- **Action:** Implemented a hard bypass rule in `worker.py`. If a document's `extractable_text_ratio > 0.80`, it is marked as a clean PDF.
- **Effect:** The document skips image rendering, OpenCV enhancements, and the OCR parsing fallback chain entirely. It is routed directly to `pypdf`/`pdfplumber`, guaranteeing zero degradation.

### 2. Adaptive Enhancement 
The previous pipeline applied all enabled filters sequentially, creating compounded artifacts (e.g., upscaling noise, then sharpening the noise).
- **Action:** Refined `services/document_preprocessor.py` to only append the specific filter needed for a specific defect (e.g., `upscale` only if DPI is low, `deskew` only if skew > 2 degrees).
- **Effect:** Enhancements are decoupled, preventing full-chain chaining unless every single defect condition is genuinely met.

### 3. Disable Expensive Filters
- **Action:** Set `PREPROCESS_ENABLE_DENOISE = False` and `PREPROCESS_ENABLE_SHARPEN = False` in `config.py`.
- **Effect:** Removed the two heaviest operations that were dominating the 225-second latency and causing Tesseract to hallucinate text from structural artifacts.

### 4. OCR Sanity Framework
- **Action:** Added OCR validation logic to `services/pdf_parser.py`.
- **Effect:** If OCR extraction returns garbage (e.g., character count > 5x original, dictionary ratio < 15%, printable ratio < 90%, or massive repeated character blocks), the parser discards the OCR output and falls back to the original text.

### 5. Enhancement Safety Guard
- **Action:** Configured `MAX_ENHANCED_PAGE_COUNT = 25` in `config.py`.
- **Effect:** Prevents catastrophic latency on 100+ page scanned documents by capping synchronous enhancement. Pages beyond the cap pass through without enhancement.

## Conclusion
The preprocessing pipeline is now strictly a "do no harm" stage. It intelligently routes documents, selectively applies safe enhancements, and guards against OCR hallucinations.
