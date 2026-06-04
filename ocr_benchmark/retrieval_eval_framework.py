import os
import sys
import time
import json
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

import config
from services.pdf_parser import parse_pdf
from services.chunking_service import chunk_text

try:
    from sentence_transformers import SentenceTransformer
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
except ImportError as e:
    print(f"Missing dependency: {e}. Please ensure sentence-transformers and qdrant-client are installed.")
    sys.exit(1)

TEST_DATA_DIR = REPO_ROOT / "backend" / "test_data"
GROUND_TRUTH_PATH = Path(__file__).parent / "ground_truth.json"

CHUNK_SIZES = [200, 300, 400, 500, 600]

def load_ground_truth():
    if not GROUND_TRUTH_PATH.exists():
        print(f"Ground truth file {GROUND_TRUTH_PATH} not found.")
        sys.exit(1)
    with open(GROUND_TRUTH_PATH, "r") as f:
        return json.load(f)

def extract_corpus_texts():
    print("--- Extracting Corpus Texts ---")
    texts = {}
    # Or just use the known list
    TEST_DOCS = {
        "B": "category_B_low_dpi.pdf",
        "C": "category_C_skewed.pdf",
        "D": "category_D_noisy.pdf",
        "E": "photographed_notes.pdf",
        "F": "category_F_large_doc.pdf",
        "G": "category_G_handwritten_names.pdf",
        "H": "category_H_handwritten.pdf"
    }
    
    for cat, fname in TEST_DOCS.items():
        fpath = TEST_DATA_DIR / fname
        if not fpath.exists():
            print(f"File {fname} not found!")
            continue
        
        # We will parse it as DIGITAL to just get native text if it exists, 
        # or it will fallback to OCR if needed. 
        # To avoid massive OCR delays, we rely on the parser's logic.
        print(f"Parsing {fname}...")
        res = parse_pdf(str(fpath), document_type="MIXED", routing_confidence=1.0)
        texts[cat] = res.text
    return texts

def evaluate_retrieval():
    ground_truth = load_ground_truth()
    corpus_texts = extract_corpus_texts()
    
    print("\n--- Loading Embedding Model ---")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    results = {}
    
    for size in CHUNK_SIZES:
        print(f"\n=== Evaluating Chunk Size: {size} words ===")
        config.CHUNK_TARGET_WORDS = size
        
        # 1. Chunk texts
        points = []
        point_id = 0
        chunk_map = {} # id -> (cat, text)
        
        for cat, text in corpus_texts.items():
            if not text.strip():
                continue
            chunks = chunk_text(text)
            for chunk in chunks:
                vec = model.encode(chunk, show_progress_bar=False).tolist()
                points.append(PointStruct(id=point_id, vector=vec, payload={"cat": cat}))
                chunk_map[point_id] = (cat, chunk)
                point_id += 1
                
        if not points:
            print("No chunks generated!")
            continue
            
        # 2. Build Qdrant index
        client = QdrantClient(":memory:")
        client.create_collection(
            collection_name="eval",
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        client.upsert(collection_name="eval", points=points)
        
        # 3. Execute Queries
        metrics = {
            "queries": len(ground_truth),
            "hits": 0,
            "recall@1": 0,
            "recall@3": 0,
            "recall@5": 0,
            "mrr": 0.0,
            "grounding_acc": 0
        }
        
        for gt in ground_truth:
            query = gt["query"]
            exp_cat = gt["expected_category"]
            exp_kw = gt["expected_keyword"].lower()
            
            q_vec = model.encode(query, show_progress_bar=False).tolist()
            hits = client.query_points(collection_name="eval", query=q_vec, limit=5).points
            
            # Find rank of first correct chunk
            rank = None
            kw_found = False
            for i, hit in enumerate(hits):
                ret_cat = hit.payload["cat"]
                chunk_txt = chunk_map[hit.id][1].lower()
                
                # A chunk is correct if it comes from the expected category AND contains the expected keyword
                if ret_cat == exp_cat and exp_kw in chunk_txt:
                    rank = i + 1
                    kw_found = True
                    break
                    
            if rank is not None:
                metrics["hits"] += 1
                if rank == 1: metrics["recall@1"] += 1
                if rank <= 3: metrics["recall@3"] += 1
                if rank <= 5: metrics["recall@5"] += 1
                metrics["mrr"] += 1.0 / rank
                metrics["grounding_acc"] += 1
                
        # Normalize
        q_count = metrics["queries"]
        if q_count > 0:
            metrics["recall@1"] /= q_count
            metrics["recall@3"] /= q_count
            metrics["recall@5"] /= q_count
            metrics["mrr"] /= q_count
            metrics["grounding_acc"] /= q_count
            
        results[size] = metrics
        print(f"Recall@1: {metrics['recall@1']:.1%} | MRR: {metrics['mrr']:.3f} | Hits: {metrics['hits']}/{q_count}")
        
    return results

def generate_markdown_report(results):
    lines = [
        "# ScaleFlow Retrieval Evaluation Framework (Verified)",
        "",
        "This report was automatically generated by sweeping the `CHUNK_TARGET_WORDS` parameter over the raw corpus and testing against the `ground_truth.json` Q&A set on a live Qdrant index.",
        "",
        "## Chunk Size Sweep Results",
        "",
        "| Chunk Size | Recall@1 | Recall@3 | Recall@5 | MRR | Grounding Acc | Hit Rate |",
        "|---|---|---|---|---|---|---|"
    ]
    
    for size, m in results.items():
        lines.append(f"| **{size} words** | {m['recall@1']:.1%} | {m['recall@3']:.1%} | {m['recall@5']:.1%} | {m['mrr']:.3f} | {m['grounding_acc']:.1%} | {m['hits']}/{m['queries']} |")
        
    lines.extend([
        "",
        "## Analysis",
        "These metrics represent empirical, programmatic results directly extracted from the indexing and semantic search process, replacing the previous hardcoded values."
    ])
    
    art_dir = Path(r"C:\Users\Kaustav\.gemini\antigravity-ide\brain\07e03dee-9a3c-44ae-8e91-51b22b0f52ae")
    out_path = art_dir / "retrieval_benchmark_report.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport generated: {out_path}")

def main():
    results = evaluate_retrieval()
    generate_markdown_report(results)

if __name__ == "__main__":
    main()
