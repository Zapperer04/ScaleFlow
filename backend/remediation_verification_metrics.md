# ScaleFlow Remediation Verification Metrics
**Date:** 2026-06-03

## Categories A–H Verification Metrics (After Remediation)

| Category | Parse Duration (s) | Char Count | Printable Ratio | Dict Ratio | Coherence Score | Quality Score | OCR Accepted? | OCR Rejection Reason | Parser Path |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **A** | 0.005 | 308 | 1.000 | 0.529 | 90.20 | 67.80 | False | N/A | `pypdf` |
| **B** | 36.799 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | False | N/A | `pypdf` |
| **C** | 47.994 | 141 | 1.000 | 0.167 | 100.00 | 0.00 | True | N/A | `ocr_fallback` |
| **D** | 269.552 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | False | Dictionary ratio too low (0.11) | `pypdf` |
| **E** | 17.078 | 410 | 1.000 | 0.220 | 100.00 | 53.20 | True | N/A | `ocr_fallback` |
| **F** | 18.627 | 833 | 1.000 | 0.344 | 97.50 | 59.70 | True | N/A | `ocr_fallback` |
| **G** | 49.935 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | False | Dictionary ratio too low (0.07) | `pypdf` |
| **H** | 41.806 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | False | Dictionary ratio too low (0.06) | `pypdf` |

*(Note: The table represents the exact measured values generated after the pipeline remediation was deployed.)*

## Category D: OCR Explosion Prevention

* **Original extracted text length:** 0
* **OCR extracted text length:** 27,079 (measured before remediation) -> `rejected`
* **Which OCR sanity rule triggered:** "Dictionary ratio too low (0.11)"
* **Final text length accepted by parser:** 0

## Category A: Clean PDF Protection

* **OCR skipped:** `True` (Extractable ratio 1.0 > 0.80)
* **Enhancement skipped:** `True`
* **Parser path used:** `pypdf`
