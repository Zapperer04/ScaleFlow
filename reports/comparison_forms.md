# Output Parity Comparison Report - FORMS

**Document**: `category_A_simple.pdf`
**Result**: `FAIL`

## Parity Scores
- **Structural Match**: 86.67%
- **Text Match**: 3.12%
- **Semantic Match**: 0.00%
- **Overall Confidence Score**: 67.0%

## Timings & Counts
- **Legacy Parse Time**: 0.018s (Nodes: 2, Edges: 1)
- **Engine Parse Time**: 8.893s (Nodes: 3, Edges: 1)
- **Parse Time Delta**: +50464.1%
- **Delta Node Count**: -1

## Detected Differences
- [STRUCTURAL] Node count mismatch: Legacy=2, Engine=3.
- [SEMANTIC] Missing key entities in Engine: ['invoicedate', 'paymentmethod', 'invoicenumber']

## Decomposed Confidence Factors
- **Structural Confidence**: 90.0%
- **Table Similarity Confidence**: 100.0%
- **Entity Matching Confidence**: 50.0%
- **Validator Repair Confidence**: 100.0%
