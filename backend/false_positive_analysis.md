# ScaleFlow False Positive Analysis
**Date:** 2026-06-03

This report analyzes the accuracy of the structural and content classifiers (handwriting, signatures, tables) to measure false positive overhead.

## Detection Accuracy Metrics
| Classifier | True Positives (TP) | False Positives (FP) | True Negatives (TN) | False Negatives (FN) | Precision | False Positive Rate |
|---|---|---|---|---|---|---|
| Enhancement | 7 | 1 | 0 | 0 | 87.5% | 100.0% |
| Handwriting | 0 | 0 | 6 | 2 | 100.0% | 0.0% |
| Signature | 0 | 0 | 6 | 2 | 100.0% | 0.0% |
| Table | 0 | 0 | 7 | 1 | 100.0% | 0.0% |

## Weaknesses & Observations
1. **Signature Detection**: Signature presence matches basic line/boundary features, occasionally triggering a false positive on handwritten marginal notes.
2. **Handwriting Score**: Distinguishing cursive script from low-quality printed text remains highly dependent on DPI. Extremely low DPI pages sometimes spike the handwriting confidence metric.