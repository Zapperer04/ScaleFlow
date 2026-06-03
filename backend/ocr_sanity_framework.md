# ScaleFlow OCR Sanity Framework
**Date:** 2026-06-03

## Overview
The OCR Sanity Framework acts as a final quality gate inside the `pdf_parser` fallback chain. It prevents Tesseract OCR hallucinations (caused by noise or structural artifacts) from entering the search index by comparing the OCR output against the original extracted text and absolute quality thresholds.

## Validation Checks

When OCR extraction completes on a page, the resulting text string undergoes four distinct sanity checks:

### 1. Growth Check (Hallucination Detection)
If the OCR character count exceeds `5x` the original extracted character count, the output is rejected. OCR hallucinating 27,000 characters from a 140-character noisy page triggers this fallback.

### 2. Dictionary Ratio Validation
If the proportion of valid English dictionary words in the OCR text falls below `0.15` (15%), the output is rejected. Random noise letters (`ree ean 0 a3%`) fail this check.

### 3. Printable Ratio Validation
If the proportion of standard printable characters in the OCR text falls below `0.90` (90%), the output is rejected. Heavy OCR corruption often produces non-standard unicode artifacts.

### 4. Repeated Character Detection
A regex `(.)\1{10,}` searches for consecutive strings of 10 or more identical characters (e.g., `%%%%%%%%%%`, `1111111111`). If found, the output is immediately rejected as an OCR geometry artifact.

### 5. Overall Quality Comparison
If the OCR text passes the above absolute checks, its overall `quality_score` (combining dictionary ratio, printable ratio, and coherence) is compared to the original text's `quality_score`. If the OCR score is lower, the parser rejects it and uses the original extraction.

## Fallback Behavior
When OCR is rejected by any of these checks, the parser discards the OCR string, logs an `OCR rejected: [Reason]` trace, and gracefully falls back to the original text extracted by `pypdf` or `pdfplumber`.
