# Output Parity Comparison Report - HANDWRITTEN

**Document**: `category_H_handwritten.pdf`
**Result**: `FAIL`

## Parity Scores
- **Structural Match**: 65.00%
- **Text Match**: 0.00%
- **Semantic Match**: 0.00%
- **Overall Confidence Score**: 68.5%

## Timings & Counts
- **Legacy Parse Time**: 0.012s (Nodes: 2, Edges: 1)
- **Engine Parse Time**: 7.603s (Nodes: 1, Edges: 1)
- **Parse Time Delta**: +60777.5%
- **Delta Node Count**: 1

## Detected Differences
- [STRUCTURAL] Node count mismatch: Legacy=2, Engine=1.
- [TEXTUAL] Text length delta: Legacy=220 chars, Engine=48 chars.
- [SEMANTIC] Missing key entities in Engine: ['invoicedate', 'paymentmethod', 'invoicenumber']

## Decomposed Confidence Factors
- **Structural Confidence**: 95.0%
- **Table Similarity Confidence**: 100.0%
- **Entity Matching Confidence**: 50.0%
- **Validator Repair Confidence**: 100.0%
