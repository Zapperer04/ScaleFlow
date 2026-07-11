import os
import sys
import json

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Set Poppler path for Windows environment
POPPLER_BIN = r"C:\Users\Kaustav\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin"
os.environ["PREPROCESS_POPPLER_PATH"] = POPPLER_BIN

import config
from services.document_preprocessor import evaluate_document
from services.pdf_parser import parse_pdf
from services.chunking_service import chunk_text
from services.quality_gate_service import compute_quality_score
from worker import handle_preprocess_document, handle_parse_document, handle_chunk_text, handle_generate_embeddings, handle_summarize_document

def run_integration_test():
    print("=== STARTING SCALEFLOW INTEGRATION TEST ===")
    
    test_pdf = os.path.join(backend_dir, "test_data", "category_A_simple.pdf")
    if not os.path.exists(test_pdf):
        print(f"Error: Test PDF not found at {test_pdf}")
        sys.exit(1)
        
    print(f"Testing with PDF: {test_pdf}")
    
    # 1. Test Preprocessor Direct
    print("\n--- 1. Testing preprocessor evaluation directly ---")
    report = evaluate_document(test_pdf)
    print(f"Document Type: {report.document_type}")
    print(f"Extractable Text Ratio: {report.extractable_text_ratio:.2%}")
    print(f"Needs Enhancement: {report.needs_enhancement}")
    print(f"Overall Quality Score: {report.overall_quality_score}")
    
    # Mock payload & input_artifacts for worker handlers
    payload = {
        "_pipeline_id": "test-pipeline-123",
        "_task_id": "test-task-123",
        "_lease_token": "test-lease-token",
        "source_text": ""
    }
    
    # Mocking get_uploaded_file_path to return our local simple pdf
    import worker
    original_get_path = worker.get_uploaded_file_path
    worker.get_uploaded_file_path = lambda pid: test_pdf
    
    # 2. Test Preprocess Handler
    print("\n--- 2. Testing preprocess handler ---")
    preprocess_res = handle_preprocess_document(payload, {})
    print(f"Preprocess Handler Keys: {list(preprocess_res.keys())}")
    
    # 3. Test Parse Handler
    print("\n--- 3. Testing parse handler ---")
    input_artifacts = {"preprocessing_report": preprocess_res}
    parse_res = handle_parse_document(payload, input_artifacts)
    print(f"Parse Handler Keys: {list(parse_res.keys())}")
    print(f"Document Type: {parse_res.get('document_type')}")
    print(f"Page Count: {len(parse_res.get('pages', []))}")
    if parse_res.get("pages"):
        first_page = parse_res["pages"][0]
        print(f"First page keys: {list(first_page.keys())}")
        print(f"First page extraction method: {first_page.get('extraction_method')}")
        print(f"First page length: {len(first_page.get('text', ''))}")
        
    # 4. Test Chunker Handler
    print("\n--- 4. Testing chunker handler ---")
    input_artifacts = {"parsed_text": parse_res}
    chunks = handle_chunk_text(payload, input_artifacts)
    print(f"Total Chunks Generated: {len(chunks)}")
    if chunks:
        print(f"First chunk structure: {list(chunks[0].keys())}")
        print(f"First chunk text (preview): {chunks[0]['text'][:100]!r}")
        print(f"First chunk metadata: {json.dumps(chunks[0]['metadata'], indent=2)}")
        
    # 5. Test Embeddings Handler
    print("\n--- 5. Testing embeddings handler ---")
    # Mock upsert_document_chunks to avoid Qdrant network requests during integration test if needed
    import services.vector_store as vs
    original_upsert = vs.upsert_document_chunks
    vs.upsert_document_chunks = lambda *args, **kwargs: (True, 0.001, 0.002)

    # Mock embedding model to avoid loading torch/sentence-transformers
    import services.embedding_service as es
    class MockEmbeddingModel:
        def encode(self, texts, batch_size=32, show_progress_bar=False, convert_to_numpy=True):
            import numpy as np
            if isinstance(texts, str):
                return np.zeros(768, dtype=np.float32)
            return np.zeros((len(texts), 768), dtype=np.float32)
    es.get_embedding_model = lambda: MockEmbeddingModel()
    
    # Mock get_pipeline_file_info
    worker.get_pipeline_file_info = lambda pid: ("test-file-id", "category_A_simple.pdf", "test-art-id")
    
    input_artifacts = {"text_chunks": chunks}
    embed_res = handle_generate_embeddings(payload, input_artifacts)
    print(f"Embedding Handler Keys: {list(embed_res.keys())}")
    print(f"Total Vectors: {embed_res.get('vector_count')}")
    print(f"Qdrant Upserted: {embed_res.get('qdrant_upserted')}")
    if embed_res.get("chunk_refs"):
        print(f"First Chunk Ref: {embed_res['chunk_refs'][0]}")
        
    # 6. Test Summarize Handler
    print("\n--- 6. Testing summarize handler ---")
    input_artifacts = {"text_chunks": chunks}
    summary_res = handle_summarize_document(payload, input_artifacts)
    print(f"Summary output (preview): {summary_res[:200]!r}")
    
    # Restore original functions
    worker.get_uploaded_file_path = original_get_path
    vs.upsert_document_chunks = original_upsert
    
    print("\n=== INTEGRATION TEST COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_integration_test()
