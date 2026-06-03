# ScaleFlow Adaptive Enhancement Design
**Date:** 2026-06-03

## Overview
The "Adaptive Enhancement" framework replaces the monolithic enhancement chain with a defect-driven routing mechanism. Instead of pushing every low-quality document through all available image filters, enhancements are applied *only* if the specific defect threshold is crossed.

## Defect-Driven Routing Rules

1. **Low DPI Defect**
   - **Condition:** Embedded images exist, but their calculated DPI is `< 150` (`PREPROCESS_DPI_MIN`).
   - **Action:** Apply **Upscale** (Lanczos resampling to 300 DPI).

2. **Skew Defect**
   - **Condition:** Page rotation exceeds `2.0` degrees (`PREPROCESS_SKEW_MAX_DEG`).
   - **Action:** Apply **Deskew** (Affine rotation to $0^\circ$).

3. **Contrast Defect**
   - **Condition:** Foreground/Background contrast score is `< 35.0` (`PREPROCESS_CONTRAST_MIN`).
   - **Action:** Apply **Contrast Enhancement** (CLAHE).

4. **Noise Defect (Currently Disabled)**
   - **Condition:** Image noise density score is `< 40.0` (`PREPROCESS_NOISE_MIN`).
   - **Action:** Apply **Denoise** (`fastNlMeansDenoising`).
   - *Status:* Disabled by default due to high latency ($>1 \text{ min/page}$) and OCR hallucination risks.

5. **Blur Defect (Currently Disabled)**
   - **Condition:** Laplacian variance score is `< 40.0` (`PREPROCESS_BLUR_MIN`).
   - **Action:** Apply **Sharpen** (Unsharp Mask).
   - *Status:* Disabled by default due to compounding artifacts when combined with upscaling.

## Protection for Clean Documents
The adaptive routing is superseded by a global bypass for clean digital PDFs:
If `extractable_text_ratio > 0.80`, the document completely skips the evaluation thresholds and all OpenCV image manipulations. This guarantees that clean text layers are never degraded by rasterization.
