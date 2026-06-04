import os
import sys
import json
import time
import traceback
from pathlib import Path

# Add backend to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.services.pdf_parser import evaluate_text_quality
from pdf2image import convert_from_path

from benchmark_wrappers import TesseractWrapper, PaddleWrapper, EasyOCRWrapper, DocTRWrapper, SuryaWrapper

def main():
    print("Locating Dataset...")
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_data_dir = os.path.join(backend_dir, "backend", "test_data")
    
    # We only care about B-H
    benchmark_categories = {
        'B': os.path.join(test_data_dir, "category_B_low_dpi.pdf"),
        'C': os.path.join(test_data_dir, "category_C_skewed.pdf"),
        'D': os.path.join(test_data_dir, "category_D_noisy.pdf"),
        'E': os.path.join(test_data_dir, "photographed_notes.pdf"),
        'F': os.path.join(test_data_dir, "category_F_mixed_content.pdf"),
        'G': os.path.join(test_data_dir, "category_G_handwritten_names.pdf"),
        'H': os.path.join(test_data_dir, "category_H_handwritten.pdf")
    }
    
    engines = {
        "Tesseract": TesseractWrapper,
        "PaddleOCR": PaddleWrapper,
        "EasyOCR": EasyOCRWrapper,
        "DocTR": DocTRWrapper,
        "Surya": SuryaWrapper
    }
    
    expected_keywords = {
        "B": ["throughput", "ledger", "distributed"],
        "C": ["replication", "nodes", "reliability"],
        "D": ["noisy", "document", "test"],
        "E": ["photographed", "lighting", "shadow"],
        "F": ["signature", "authorization", "mixed", "table"],
        "G": ["john", "doe", "printed", "handwriting"],
        "H": ["mostly", "handwritten", "cursive"]
    }
    
    retrieval_queries = {
        "B": "What do distributed ledger systems require?",
        "C": "What does replication across nodes ensure?"
    }
    
    results = {}
    
    # Pre-render images
    print("Rendering PDFs to images...")
    images = {}
    for cat, pdf_path in benchmark_categories.items():
        if os.path.exists(pdf_path):
            try:
                img = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1)[0]
                img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"cat_{cat}.png")
                img.save(img_path)
                images[cat] = img_path
            except Exception as e:
                print(f"Warning: Failed to render {pdf_path}: {e}")
        else:
            print(f"Warning: {pdf_path} does not exist.")
            
    # Load Sentence Transformers for Retrieval Evaluation
    try:
        from sentence_transformers import SentenceTransformer
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct
        model = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception as e:
        print(f"Retrieval dependencies missing: {e}")
        model = None
    
    for engine_name, wrapper_cls in engines.items():
        print(f"\n--- Testing Engine: {engine_name} ---")
        engine_results = {
            "startup_time_s": 0.0,
            "failed_init": False,
            "categories": {},
            "retrieval": {}
        }
        
        # Initialize Engine
        t0 = time.perf_counter()
        try:
            wrapper = wrapper_cls()
            engine_results["startup_time_s"] = round(time.perf_counter() - t0, 3)
            print(f"{engine_name} initialized in {engine_results['startup_time_s']}s")
        except Exception as e:
            print(f"Failed to initialize {engine_name}: {e}")
            engine_results["failed_init"] = True
            engine_results["error"] = str(e)
            results[engine_name] = engine_results
            continue
            
        # Extract Texts
        extracted_texts = {}
        for cat in benchmark_categories:
            img_path = images.get(cat)
            if not img_path:
                continue
                
            print(f"  Processing Category {cat}...")
            try:
                ext_res = wrapper.extract_text(img_path)
                text = ext_res["text"]
                metrics = evaluate_text_quality(text)
                
                # Keyword Recovery
                expected = expected_keywords.get(cat, [])
                recovered = sum(1 for kw in expected if kw.lower() in text.lower())
                recovery_rate = recovered / len(expected) if expected else 0.0
                
                engine_results["categories"][cat] = {
                    "latency_s": round(ext_res["latency_s"], 3),
                    "memory_mb": round(ext_res["memory_mb"], 2),
                    "char_count": len(text),
                    "dict_ratio": round(metrics["dict_word_ratio"], 3),
                    "printable_ratio": round(metrics["printable_ratio"], 3),
                    "coherence_score": round(metrics["coherence_score"], 2),
                    "quality_score": round(metrics["quality_score"], 2),
                    "recovery_rate": round(recovery_rate, 2),
                    "text_snippet": text[:100].replace("\n", " ") + "..."
                }
                extracted_texts[cat] = text
            except Exception as e:
                print(f"  Failed extraction for {cat}: {e}")
                traceback.print_exc()
                engine_results["categories"][cat] = {"error": str(e)}
                
        # Run Retrieval Test
        if model:
            print(f"  Running Retrieval Benchmark for {engine_name}...")
            try:
                client = QdrantClient(":memory:")
                client.recreate_collection(
                    collection_name="benchmark",
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
                
                # Index all text chunks
                points = []
                idx = 0
                for cat, txt in extracted_texts.items():
                    if len(txt.strip()) > 10:
                        vec = model.encode(txt).tolist()
                        points.append(PointStruct(id=idx, vector=vec, payload={"cat": cat, "text": txt}))
                        idx += 1
                
                if points:
                    client.upsert(collection_name="benchmark", points=points)
                    
                    # Search
                    for r_cat, r_query in retrieval_queries.items():
                        q_vec = model.encode(r_query).tolist()
                        hits = client.search(collection_name="benchmark", query_vector=q_vec, limit=1)
                        if hits:
                            engine_results["retrieval"][r_cat] = {
                                "top_similarity": round(hits[0].score, 3),
                                "retrieved_cat": hits[0].payload.get("cat"),
                                "success": hits[0].payload.get("cat") == r_cat
                            }
                        else:
                            engine_results["retrieval"][r_cat] = {"top_similarity": 0.0, "success": False}
            except Exception as e:
                print(f"  Retrieval failed: {e}")
        
        results[engine_name] = engine_results
        
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark_results.json"), "w") as f:
        json.dump(results, f, indent=2)
        
    print("Benchmark complete. Results saved to benchmark_results.json")

if __name__ == "__main__":
    main()
