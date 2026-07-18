# ScaleFlow Signature Detection Report

Signature detection identifies document validation zones without performing signature verification or image classification.

## Heuristic Detection Rates (CV2 Contour circularity)

| Test Category | Target Document | Expected Signature | Detected Signature | Result |
| :--- | :--- | :--- | :--- | :--- |
| **Printed Only** | `category_A_simple.pdf` | No | No | ✅ Correct |
| **Printed Only** | `category_B_low_dpi.pdf` | No | No | ✅ Correct |
| **Printed + Signature** | `category_F_large_doc.pdf` | Yes | Yes | ✅ Correct |
| **Mostly Handwritten** | `category_H_handwritten.pdf` | No | No | ✅ Correct |

## Metrics Summary
- **Detection Rate (Recall)**: 100.0%
- **Precision**: 100.0%
- **False Positives (FP)**: 0
- **False Negatives (FN)**: 0

## Implementation Rationale
ScaleFlow runs contour circularity checks on 72 DPI page thumbnails:
- Filter contours with area $> 200$ pixels.
- Calculate circularity: $C = 4\pi \times \text{Area} / \text{Perimeter}^2$.
- Flag as signature if circularity is between $0.01$ and $0.5$ (highly irregular, elongated curves) and located in the bottom 30% of the page.
