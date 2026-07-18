# ScaleFlow Handwriting Detection Report

Handwriting detection prevents unreadable handwriting from polluting the vector space and triggers rejection warnings on opt-in pipelines.

## Handwriting Detection Rates

| Test Category | Target Document | Expected Handwriting | Detected Handwriting | Result |
| :--- | :--- | :--- | :--- | :--- |
| **Printed Only** | `category_A_simple.pdf` | No | No | ✅ Correct |
| **Printed + Handwriting** | `category_G_handwritten_names.pdf` | Yes | Yes | ✅ Correct |
| **Mostly Handwritten** | `category_H_handwritten.pdf` | Yes | Yes | ✅ Correct |

## Metrics Summary
- **Detection Rate (Recall)**: 100.0%
- **Precision**: 100.0%
- **False Positives (FP)**: 0
- **False Negatives (FN)**: 0

## Technical Heuristic
The pre-processor combines three statistical checks on ink stroke textures:
1. **Stroke Width Variance**: Distance transform variance along ink pixels (handwriting has highly variable stroke widths).
2. **Component Size Coefficient of Variation**: Connected component area deviation (handwritten characters vary heavily in size).
3. **Ink Density Irregularity**: Standard deviation of adaptive thresholding blocks.
