import os, sys, json, time
from pathlib import Path
os.environ["OMP_NUM_THREADS"] = "1"

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
from services.chunking_service import chunk_text
import config

def run_forensics():
    print("Loading dependencies...", flush=True)
    from sentence_transformers import SentenceTransformer
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct

    texts_path = Path(r"C:\Users\Kaustav\.gemini\antigravity-ide\brain\07e03dee-9a3c-44ae-8e91-51b22b0f52ae\scratch\all_corpus_texts.json")
    with open(texts_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)
        
    gt_path = REPO_ROOT / "ocr_benchmark" / "ground_truth_v2.json"
    with open(gt_path, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)
        
    cache_dir = Path.home() / ".cache" / "huggingface" / "hub" / "models--BAAI--bge-base-en-v1.5"
    snapshots_dir = cache_dir / "snapshots"
    snapshot = list(snapshots_dir.iterdir())[0] if snapshots_dir.exists() else None
    
    print("Loading Model...", flush=True)
    model = SentenceTransformer(str(snapshot) if snapshot else "BAAI/bge-base-en-v1.5")
    
    config.CHUNK_TARGET_WORDS = 300
    points = []
    point_id = 0
    chunk_map = {}
    
    print("Chunking and encoding corpus...", flush=True)
    for cat, data in corpus.items():
        text = data["text"]
        chunks = chunk_text(text)
        if not chunks: continue
        print(f"Encoding {len(chunks)} chunks for {cat}...", flush=True)
        t0 = time.time()
        vecs = model.encode(chunks, batch_size=32, show_progress_bar=False)
        print(f"  -> Encoded in {time.time()-t0:.1f}s", flush=True)
        for i, chunk in enumerate(chunks):
            points.append(PointStruct(id=point_id, vector=vecs[i].tolist(), payload={"cat": cat}))
            chunk_map[point_id] = (cat, chunk)
            point_id += 1
            
    print("Building index...", flush=True)
    client = QdrantClient(":memory:")
    client.create_collection("eval", vectors_config=VectorParams(size=768, distance=Distance.COSINE))
    client.upsert(collection_name="eval", points=points)
    
    failures = []
    
    print("Evaluating queries...", flush=True)
    for gt in ground_truth:
        query = gt["query"]
        exp_cat = gt["expected_category"]
        exp_kw = gt["expected_keyword"].lower()
        
        q_vec = model.encode([query], show_progress_bar=False)[0].tolist()
        hits = client.query_points(collection_name="eval", query=q_vec, limit=5).points
        
        rank = None
        for i, hit in enumerate(hits):
            if hit.payload["cat"] == exp_cat and exp_kw in chunk_map[hit.id][1].lower():
                rank = i + 1
                break
                
        if rank != 1:
            # It's a failure (either ranked 2-5 or not retrieved at all)
            retrieved_chunk = chunk_map[hits[0].id][1] if hits else ""
            retrieved_cat = hits[0].payload["cat"] if hits else ""
            retrieved_score = hits[0].score if hits else 0.0
            
            # Find the expected chunk manually by searching the chunk_map
            expected_chunks = []
            for cid, (c_cat, c_text) in chunk_map.items():
                if c_cat == exp_cat and exp_kw in c_text.lower():
                    # Calculate similarity score to query
                    c_vec = client.retrieve(collection_name="eval", ids=[cid], with_vectors=True)[0].vector
                    # We can get the score from qdrant by doing a direct lookup or just re-encoding
                    expected_chunks.append({"id": cid, "text": c_text})
            
            exp_scores = []
            if expected_chunks:
                for ec in expected_chunks:
                    c_vec = model.encode([ec["text"]], show_progress_bar=False)[0].tolist()
                    # Cosine sim
                    import numpy as np
                    v1 = np.array(q_vec)
                    v2 = np.array(c_vec)
                    score = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                    exp_scores.append(float(score))
            
            best_exp_score = max(exp_scores) if exp_scores else 0.0
            best_exp_text = expected_chunks[exp_scores.index(best_exp_score)]["text"] if expected_chunks else "NOT FOUND (Extraction Failure)"
            
            failures.append({
                "query": query,
                "expected_category": exp_cat,
                "expected_keyword": exp_kw,
                "retrieved_category_rank1": retrieved_cat,
                "retrieved_score_rank1": retrieved_score,
                "expected_chunk_best_score": best_exp_score,
                "retrieved_chunk_text": retrieved_chunk,
                "expected_chunk_text": best_exp_text,
                "rank": rank if rank else "Not in top 5"
            })
            
    out_path = Path(r"C:\Users\Kaustav\.gemini\antigravity-ide\brain\07e03dee-9a3c-44ae-8e91-51b22b0f52ae\scratch\forensics_data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(failures, f, indent=2)
        
    print(f"Done. Found {len(failures)} failures.")

if __name__ == "__main__":
    run_forensics()
