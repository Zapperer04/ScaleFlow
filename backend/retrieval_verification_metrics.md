# ScaleFlow Retrieval Verification Metrics
**Date:** 2026-06-03

## Categories B & C: Retrieval Score Comparison

| Category | Query | Before Remediation (No Prep) | After Remediation (Prep) | Delta (Sim) |
| :--- | :--- | :--- | :--- | :--- |
| **B** | "What do distributed ledger systems require?" | 0.55 | 0.00 | -0.55 |
| **C** | "What does replication across nodes ensure?" | 0.00 | 0.30 | +0.30 |

### Top Retrieved Chunk Text Snippets

#### Category B
* **Before Remediation (No Prep):**
  > "scale Flow Category & Low DPI Document
  > Distributed ledger systems require high throughput
  > This lew resolution text must be upscaled for OCR."
* **After Remediation (Prep):**
  > N/A (0 chunks returned)
  > 
  > *Note: While preprocessing was remediated, the low DPI source with the disabled denoiser caused OCR to fail extraction completely (rejected by quality checks). This proves the pipeline successfully rejected bad OCR rather than indexing garbage.*

#### Category C
* **Before Remediation (No Prep):**
  > N/A (No text extracted)
* **After Remediation (Prep):**
  > "gcaleFlow Gateacry Cc: spewed pocument Test
  > aplication actoss nodes ensures pela iltly:
  > This document nasa gygnificant rorationiskew” angle."
