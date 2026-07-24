# Optimization Recommendations

1. **VLM Parser Threading**: Batch process document page VLM parses to reduce latency.
2. **Quantization**: Enable embedding vector quantization to reduce memory footprint by 75%.
3. **Cross-Encoder Cache**: Store rerank scores for identical query-document chunk pairs to improve throughput.
