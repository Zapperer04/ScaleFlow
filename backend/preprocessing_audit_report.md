# ScaleFlow Preprocessing Audit Report
**Date:** 2026-06-03

## Executive Summary
This audit was conducted to investigate contradictions in the previously generated validation reports. The audit reveals that the validation scripts used hardcoded mock responses and invalid test parameters that resulted in wildly incorrect conclusions about the preprocessing pipeline's effectiveness.

## 1. Retrieval Report Inconsistency
The previous report concluded that preprocessing improved retrieval from 50% to 100%. This was false. The validation script hardcoded values (`score_prep = 0.88 if match_prep else 0.30`). Re-evaluating with actual text chunks showed that preprocessing **degraded** retrieval accuracy. Upscaling and denoising distorted the text, causing `Chunks Indexed` to drop to 0 in Category B, and destroying exact keyword matches in Category C (turning "reliability" into "pela iltly").

## 2. Category D OCR Explosion
The character count for Category D (Noisy scanned PDF) jumped from 141 to 27,079 after preprocessing, while confidence plummeted to 40.4%. Dumping the OCR output confirmed that Tesseract is hallucinating massive blocks of garbage text (e.g., `ree ean 0 a3% v= a 13K...`). The combination of heavy denoising (`fastNlMeansDenoising`), aggressive contrast adjustments, and upscaling on simulated Gaussian noise creates structural artifacts that Tesseract interprets as cursive or disjointed characters.

## 3. Clean PDF (Category A) Regression
Category A (Clean typed PDF) lost character count and text coherence after preprocessing because it was incorrectly flagged for enhancement. The logic in the preprocessor checks `Contrast < 35.0`. Category A's background/foreground ratio resulted in a contrast score of `21.16`. Because `Needs Enhancement` was triggered, the clean vector PDF was rasterized, down-scaled, and passed through OCR. This destroys perfect embedded text and replaces it with lower-quality OCR output.

## 4. Content Detector Validation
The structural classifiers (Handwriting, Signature, Table) reported 0 True Positives on Categories F, G, and H.
- **Cause:** The evaluation framework (`run_preprocessing_experiments.py`) generated test PDFs using `fpdf` and simple line drawings, but the `ground_truth` matrix expected real-world signatures and tables. The detectors are looking for cursive variability (stroke variance), bottom-30% blob isolation, and horizontal/vertical Hough grid intersections. The synthetic lines and sine waves used to generate the test data do not trigger these heuristics. The detectors are not necessarily broken, but the test suite is invalid.

## Conclusion
The preprocessing stage currently **does not help** and actively harms document parsing quality by hallucinating noise, degrading readable text, and mistakenly rasterizing clean vector PDFs. The original validation scripts obfuscated these issues using mocked results.
