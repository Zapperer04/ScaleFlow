# Output Parity Comparison Report - RECEIPTS

**Document**: `category_D_scanned.pdf`
**Result**: `FAIL`

## Parity Scores
- **Structural Match**: 86.67%
- **Text Match**: 2.00%
- **Semantic Match**: 0.00%
- **Overall Confidence Score**: 65.0%

## Timings & Counts
- **Legacy Parse Time**: 0.434s (Nodes: 2, Edges: 1)
- **Engine Parse Time**: 9.217s (Nodes: 3, Edges: 1)
- **Parse Time Delta**: +2023.6%
- **Delta Node Count**: -1

## Detected Differences
- [STRUCTURAL] Node count mismatch: Legacy=2, Engine=3.
- [TEXTUAL] Text length delta: Legacy=220 chars, Engine=115 chars.
- [SEMANTIC] Missing key entities in Engine: ['invoicedate', 'paymentmethod', 'invoicenumber']

## Decomposed Confidence Factors
- **Structural Confidence**: 90.0%
- **Table Similarity Confidence**: 100.0%
- **Entity Matching Confidence**: 50.0%
- **Validator Repair Confidence**: 90.0%
