# Output Parity Comparison Report - DIAGRAMS

**Document**: `photographed_notes.pdf`
**Result**: `FAIL`

## Parity Scores
- **Structural Match**: 73.33%
- **Text Match**: 0.00%
- **Semantic Match**: 0.00%
- **Overall Confidence Score**: 61.5%

## Timings & Counts
- **Legacy Parse Time**: 0.021s (Nodes: 2, Edges: 1)
- **Engine Parse Time**: 11.807s (Nodes: 6, Edges: 1)
- **Parse Time Delta**: +55802.3%
- **Delta Node Count**: -4

## Detected Differences
- [STRUCTURAL] Node count mismatch: Legacy=2, Engine=6.
- [TEXTUAL] Text length delta: Legacy=220 chars, Engine=407 chars.
- [SEMANTIC] Missing key entities in Engine: ['invoicedate', 'paymentmethod', 'invoicenumber']

## Decomposed Confidence Factors
- **Structural Confidence**: 75.0%
- **Table Similarity Confidence**: 100.0%
- **Entity Matching Confidence**: 50.0%
- **Validator Repair Confidence**: 95.0%
