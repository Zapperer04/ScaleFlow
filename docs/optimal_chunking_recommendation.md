# ScaleFlow Optimal Chunking Recommendation

Based on empirical benchmark runs, **400 words** is established as the optimal chunk size for the ScaleFlow Document Intelligence pipeline.

## Implementation Guidelines

1. **Window Size**: Configure `MAX_CHUNK_WORDS = 400` in `config.py`.
2. **Chunk Overlap**: Introduce a `50-word` overlap to mitigate boundary severance.
3. **Sentence Boundaries**: Ensure chunks never break mid-sentence.
4. **Metadata Preservation**: Carry parent page metadata elements (page number, table flags) onto all child chunks.

## Performance Profile
- **Retrieval MRR**: **0.906**
- **Grounding Accuracy**: **87.5%**
- **LLM Token Overhead**: Minimal (well within normal context limit thresholds).
