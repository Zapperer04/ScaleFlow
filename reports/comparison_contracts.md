# Output Parity Comparison Report - CONTRACTS

**Document**: `category_C_large.pdf`
**Result**: `FAIL`

## Parity Scores
- **Structural Match**: 60.80%
- **Text Match**: 1.96%
- **Semantic Match**: 0.00%
- **Overall Confidence Score**: 50.0%

## Timings & Counts
- **Legacy Parse Time**: 0.613s (Nodes: 2, Edges: 1)
- **Engine Parse Time**: 90.870s (Nodes: 100, Edges: 1)
- **Parse Time Delta**: +14712.3%
- **Delta Node Count**: -98

## Detected Differences
- [STRUCTURAL] Node count mismatch: Legacy=2, Engine=100.
- [TEXTUAL] Text length delta: Legacy=220 chars, Engine=24840 chars.
- [SEMANTIC] Missing key entities in Engine: ['invoicedate', 'paymentmethod', 'invoicenumber']

## Decomposed Confidence Factors
- **Structural Confidence**: 50.0%
- **Table Similarity Confidence**: 100.0%
- **Entity Matching Confidence**: 50.0%
- **Validator Repair Confidence**: 100.0%
