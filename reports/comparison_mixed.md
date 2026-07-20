# Output Parity Comparison Report - MIXED

**Document**: `category_B_low_dpi.pdf`
**Result**: `FAIL`

## Parity Scores
- **Structural Match**: 86.67%
- **Text Match**: 4.00%
- **Semantic Match**: 0.00%
- **Overall Confidence Score**: 65.0%

## Timings & Counts
- **Legacy Parse Time**: 0.337s (Nodes: 2, Edges: 1)
- **Engine Parse Time**: 8.675s (Nodes: 3, Edges: 1)
- **Parse Time Delta**: +2473.5%
- **Delta Node Count**: -1

## Detected Differences
- [STRUCTURAL] Node count mismatch: Legacy=2, Engine=3.
- [TEXTUAL] Text length delta: Legacy=220 chars, Engine=140 chars.
- [SEMANTIC] Missing key entities in Engine: ['invoicedate', 'invoicenumber', 'totalamount']

## Decomposed Confidence Factors
- **Structural Confidence**: 90.0%
- **Table Similarity Confidence**: 100.0%
- **Entity Matching Confidence**: 50.0%
- **Validator Repair Confidence**: 90.0%
