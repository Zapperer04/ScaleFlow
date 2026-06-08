import os, sys, json, time
from pathlib import Path

def run_fast_benchmark():
    t_start = time.time()
    print("[0.0s] Starting Fast Benchmark...", flush=True)
    
    print(f"[{time.time()-t_start:.1f}s] Importing dependencies...", flush=True)
    from sentence_transformers import SentenceTransformer
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    
    REPO_ROOT = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    from services.chunking_service import chunk_text
    import config

    texts_path = Path(r"C:\Users\Kaustav\.gemini\antigravity-ide\brain\07e03dee-9a3c-44ae-8e91-51b22b0f52ae\scratch\all_corpus_texts.json")
    print(f"[{time.time()-t_start:.1f}s] Loading corpus...", flush=True)
    with open(texts_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)
        
    gt_path = REPO_ROOT / "ocr_benchmark" / "ground_truth_v2.json"
    with open(gt_path, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)
        
    cache_dir = Path.home() / ".cache" / "huggingface" / "hub" / "models--BAAI--bge-base-en-v1.5"
    snapshots_dir = cache_dir / "snapshots"
    snapshot = list(snapshots_dir.iterdir())[0] if snapshots_dir.exists() else None
    
    print(f"[{time.time()-t_start:.1f}s] Loading Model from disk...", flush=True)
    model = SentenceTransformer(str(snapshot) if snapshot else "BAAI/bge-base-en-v1.5")
    
    CHUNK_SIZES = [300]
    results = {}
    
    for size in CHUNK_SIZES:
        print(f"\n[{time.time()-t_start:.1f}s] Evaluating Chunk Size: {size}", flush=True)
        config.CHUNK_TARGET_WORDS = size
        points = []
        point_id = 0
        chunk_map = {}
        
        for cat, data in corpus.items():
            text = data["text"]
            chunks = chunk_text(text)
            if not chunks:
                continue
            
            print(f"[{time.time()-t_start:.1f}s] Encoding {len(chunks)} chunks for {cat}...", flush=True)
            t_enc = time.time()
            vecs = model.encode(chunks, batch_size=32, show_progress_bar=False)
            print(f"  -> Encoded in {time.time()-t_enc:.1f}s", flush=True)
            
            for i, chunk in enumerate(chunks):
                points.append(PointStruct(id=point_id, vector=vecs[i].tolist(), payload={"cat": cat}))
                chunk_map[point_id] = (cat, chunk)
                point_id += 1
                
        print(f"[{time.time()-t_start:.1f}s] Building Qdrant Index with {len(points)} points...", flush=True)
        client = QdrantClient(":memory:")
        client.create_collection(
            collection_name="eval",
            vectors_config=VectorParams(size=768, distance=Distance.COSINE)
        )
        if points:
            client.upsert(collection_name="eval", points=points)
            
        print(f"[{time.time()-t_start:.1f}s] Running Queries...", flush=True)
        metrics = {"queries": len(ground_truth), "hits": 0, "recall@1": 0, "recall@3": 0, "mrr": 0.0}
        
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
                    
            if rank:
                metrics["hits"] += 1
                if rank == 1: metrics["recall@1"] += 1
                if rank <= 3: metrics["recall@3"] += 1
                metrics["mrr"] += 1.0 / rank
                
        q_count = metrics["queries"]
        if q_count > 0:
            metrics["recall@1"] /= q_count
            metrics["recall@3"] /= q_count
            metrics["mrr"] /= q_count
            
        print(f"[{time.time()-t_start:.1f}s] Size {size} -> Recall@1: {metrics['recall@1']:.1%} | MRR: {metrics['mrr']:.3f} | Hits: {metrics['hits']}/{q_count}", flush=True)
        results[size] = metrics

    lines = [
        "# Embedding Validation Benchmark Results (BGE-base-en-v1.5)",
        "",
        "| Chunk Size | Recall@1 | Recall@3 | MRR | Hits |",
        "|---|---|---|---|---|"
    ]
    for size, m in results.items():
        lines.append(f"| {size} words | {m['recall@1']:.1%} | {m['recall@3']:.1%} | {m['mrr']:.3f} | {m['hits']}/{m['queries']} |")
        
    art_dir = Path(r"C:\Users\Kaustav\.gemini\antigravity-ide\brain\07e03dee-9a3c-44ae-8e91-51b22b0f52ae")
    out_path = art_dir / "embedding_validation_metrics.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nSaved to {out_path}", flush=True)

if __name__ == "__main__":
    run_fast_benchmark()
