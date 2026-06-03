# ScaleFlow Retrieval Revalidation Report
**Date:** 2026-06-03

## Overview
A critical discrepancy was identified in the previous preprocessing validation report. The report claimed that retrieval grounding improved from 50% to 100%, and cosine similarity improved from 0.40 to 0.88.

Upon re-running the retrieval index building and parallel factual queries with raw string extraction, it was found that the previous validation script (`run_preprocessing_experiments.py`) was generating these numbers using hardcoded mock evaluation branches rather than dynamic verification.

## Real Query Results

### Category B (Low DPI scanned PDF)
**Query:** "What do distributed ledger systems require?"
**Expected Keywords:** `['throughput']`

* **Without Preprocessing**:
  * **Top Similarity:** 0.55
  * **Found Keyword:** ✅ True
  * **Raw Extracted Chunk:** `scale Flow Category & Low DPI Document\nDistributed ledger systems require high throughput\nThis lew resolution text must be upscaled for OCR.`
* **With Preprocessing**:
  * **Top Similarity:** 0.00
  * **Found Keyword:** ❌ False
  * **Raw Extracted Chunk:** `N/A` (Extraction completely failed, yielding 0 chunks)

### Category C (Skewed scanned PDF)
**Query:** "What does replication across nodes ensure?"
**Expected Keywords:** `['reliability']`

* **Without Preprocessing**:
  * **Top Similarity:** 0.55
  * **Found Keyword:** ✅ True
  * **Raw Extracted Chunk:** `ScaleFlow Category C; Skewed Document Test\nReplication across nodesensures reliability.\nThisdocument hasa significant rotationiskew angle.`
* **With Preprocessing**:
  * **Top Similarity:** 0.30
  * **Found Keyword:** ❌ False
  * **Raw Extracted Chunk:** `gcaleFlow Gateacry Cc: spewed pocument Test\naplication actoss nodes ensures pela iltly:\nThis document nasa gygnificant rorationiskew” angle.`

## Conclusion
Preprocessing severely **degraded** retrieval quality in these test categories. The upscaling and enhancement pipeline broke the OCR output on Category B completely, and degraded Category C's text to the point that keyword exact matches ("reliability") were no longer possible ("pela iltly"). The previous report's findings were entirely incorrect due to flawed test fixtures.
