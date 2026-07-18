# ScaleFlow Confidence Scoring Design

Confidence scoring measures the trustworthiness of extracted text at both the document routing level and the individual chunk quality level.

## Document Routing Confidence
The routing confidence score ($C_r$) is computed by the pre-processor depending on the dominant page types:
- **DIGITAL**: $C_r = \text{digital\_ratio} \times (1.0 - \min(\text{image\_area\_ratio}, 0.5))$
- **SCANNED**: $C_r = \text{scanned\_ratio} \times (1.0 - \min(\text{page\_text\_density} / 1000.0, 0.5))$
- **MIXED**: $C_r = 1.0 - |\text{digital\_ratio} - \text{scanned\_ratio}|$

## Chunk Quality Score
The chunk quality score ($Q_c$) is computed by `evaluate_text_quality` based on lexical metrics:
$$Q_c = (\text{dict\_word\_ratio} \times 0.6 + \frac{\text{coherence\_score}}{100} \times 0.4) \times 100$$
Subject to penalties:
- If dictionary word ratio < threshold: $-50.0$ penalty.
- If printable character ratio < threshold: $-20.0$ penalty.
- If text coherence score < threshold: $-20.0$ penalty.

## Reranking and Filtering Opportunities
1. **Filtering Low-Quality Noise**: Exclude chunks with `chunk_quality_score < 40.0` from retrieval context.
2. **Quality-Weighted Reranking**: Boost search scores of high-quality chunks:
   $$\text{Score}_{\text{final}} = \text{Score}_{\text{retrieval}} \times (1.0 + 0.1 \times \text{chunk\_quality\_score} / 100)$$
3. **Audit Trails**: Explain grounding failures by highlighting if the source chunk was retrieved from a low-confidence OCR page.
