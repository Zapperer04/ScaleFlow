# Output Parity Comparison Report - INVOICES

**Document**: `category_C_skewed.pdf`
**Result**: `FAIL`

## Parity Scores
- **Structural Match**: 86.67%
- **Text Match**: 2.04%
- **Semantic Match**: 0.00%
- **Overall Confidence Score**: 67.0%

## Timings & Counts
- **Legacy Parse Time**: 0.020s (Nodes: 2, Edges: 1)
- **Engine Parse Time**: 8.873s (Nodes: 3, Edges: 1)
- **Parse Time Delta**: +44141.3%
- **Delta Node Count**: -1

## Detected Differences
- [STRUCTURAL] Node count mismatch: Legacy=2, Engine=3.
- [TEXTUAL] Text length delta: Legacy=220 chars, Engine=142 chars.
- [SEMANTIC] Missing key entities in Engine: ['invoicedate', 'paymentmethod', 'invoicenumber']

## Decomposed Confidence Factors
- **Structural Confidence**: 90.0%
- **Table Similarity Confidence**: 100.0%
- **Entity Matching Confidence**: 50.0%
- **Validator Repair Confidence**: 100.0%
