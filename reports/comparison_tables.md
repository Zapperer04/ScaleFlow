# Output Parity Comparison Report - TABLES

**Document**: `synthetic_table.pdf`
**Result**: `FAIL`

## Parity Scores
- **Structural Match**: 65.00%
- **Text Match**: 0.00%
- **Semantic Match**: 0.00%
- **Overall Confidence Score**: 50.0%

## Timings & Counts
- **Legacy Parse Time**: 0.013s (Nodes: 2, Edges: 1)
- **Engine Parse Time**: 8.343s (Nodes: 1, Edges: 1)
- **Parse Time Delta**: +61914.2%
- **Delta Node Count**: 1

## Detected Differences
- [STRUCTURAL] Node count mismatch: Legacy=2, Engine=1.
- [TEXTUAL] Text length delta: Legacy=220 chars, Engine=82 chars.
- [SEMANTIC] Missing key entities in Engine: ['invoicedate', 'paymentmethod', 'invoicenumber']

## Decomposed Confidence Factors
- **Structural Confidence**: 95.0%
- **Table Similarity Confidence**: 50.0%
- **Entity Matching Confidence**: 50.0%
- **Validator Repair Confidence**: 90.0%
