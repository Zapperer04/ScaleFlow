# ScaleFlow Latency Verification Metrics
**Date:** 2026-06-03

## Enhancement Latency Breakdown

Based on `cProfile` metrics captured during a single-page enhancement and parsing pass for Category B:

* **PDF Rendering (`convert_from_path`):** ~11.205s
* **Deskew:** ~0.000s (skipped for Category B)
* **Upscale (PIL resize/copy):** ~3.387s
* **Contrast enhancement (CLAHE array ops):** ~7.809s
* **OCR (`_extract_page_ocr`):** ~22.134s
* **Parsing framework overhead:** ~0.063s

**Total Stage Duration:** ~44.598s per document page.

*Note: By disabling `fastNlMeansDenoising` and `Unsharp Mask`, the image manipulation stage `enhance_document` alone dropped from ~192.6s to 14.189s. The OCR parser adds ~22s, ensuring the entire block operates within acceptable constraints without catastrophic blocking.*
