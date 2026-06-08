import os, sys, json, time, math
from pathlib import Path
import numpy as np
os.environ["OMP_NUM_THREADS"] = "1"

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
from services.chunking_service import chunk_text
import config

def tokenize(text):
    import re
    return [t for t in re.split(r'\W+', text.lower()) if t]

def calculate_ndcg5(rank):
    if rank is None or rank > 5: return 0.0
    return 1.0 / math.log2(rank + 1)

def run_hybrid_benchmark():
    print("[0.0s] Starting Hybrid Benchmark...", flush=True)
    t_start = time.time()
    
    from sentence_transformers import SentenceTransformer
    from rank_bm25 import BM25Okapi
    
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
    chunk_map = {}
    points = []
    point_id = 0
    tokenized_corpus = []
    
    print("Chunking and encoding corpus...", flush=True)
    for cat, data in corpus.items():
        text = data["text"]
        chunks = chunk_text(text)
        if not chunks: continue
        
        vecs = model.encode(chunks, batch_size=32, show_progress_bar=False)
        for i, chunk in enumerate(chunks):
            points.append(vecs[i])
            chunk_map[point_id] = (cat, chunk)
            tokenized_corpus.append(tokenize(chunk))
            point_id += 1
            
    print("Building BM25 Index...", flush=True)
    bm25 = BM25Okapi(tokenized_corpus)
    dense_matrix = np.array(points) # [N, 768]
    
    failures_to_track = [
        "What type of document is Category B?",
        "What does replication across nodes ensure?",
        "What kind of test is Category C?",
        "What handles arbitrary failures including malicious actors?"
    ]
    tracked_failures_data = {}
    
    metrics = {
        "Dense Only": {"hits":0, "r1":0, "r3":0, "r5":0, "mrr":0.0, "ndcg5":0.0},
        "BM25 Only": {"hits":0, "r1":0, "r3":0, "r5":0, "mrr":0.0, "ndcg5":0.0},
        "Weighted Hybrid": {"hits":0, "r1":0, "r3":0, "r5":0, "mrr":0.0, "ndcg5":0.0},
        "RRF Hybrid": {"hits":0, "r1":0, "r3":0, "r5":0, "mrr":0.0, "ndcg5":0.0},
    }
    
    print("Evaluating queries...", flush=True)
    for gt in ground_truth:
        query = gt["query"]
        exp_cat = gt["expected_category"]
        exp_kw = gt["expected_keyword"].lower()
        
        # 1. Dense Scoring
        q_vec = model.encode([query], show_progress_bar=False)[0]
        dense_scores = np.dot(dense_matrix, q_vec) / (np.linalg.norm(dense_matrix, axis=1) * np.linalg.norm(q_vec))
        
        # 2. BM25 Scoring
        tokenized_query = tokenize(query)
        bm25_scores = bm25.get_scores(tokenized_query)
        
        # Rankings (higher is better)
        dense_ranks = np.argsort(-dense_scores)
        bm25_ranks = np.argsort(-bm25_scores)
        
        # Create map from doc_id to its rank (1-indexed)
        dense_rank_map = {doc_id: rank+1 for rank, doc_id in enumerate(dense_ranks)}
        bm25_rank_map = {doc_id: rank+1 for rank, doc_id in enumerate(bm25_ranks)}
        
        # 3. Weighted Hybrid Scoring
        # Min-Max Normalize
        def normalize(scores):
            min_s = np.min(scores)
            max_s = np.max(scores)
            if max_s == min_s: return np.zeros_like(scores)
            return (scores - min_s) / (max_s - min_s)
            
        norm_dense = normalize(dense_scores)
        norm_bm25 = normalize(bm25_scores)
        weighted_scores = 0.5 * norm_dense + 0.5 * norm_bm25
        weighted_ranks = np.argsort(-weighted_scores)
        
        # 4. RRF Hybrid Scoring (k=60)
        k = 60
        rrf_scores = np.zeros(len(chunk_map))
        for doc_id in range(len(chunk_map)):
            rrf_scores[doc_id] = (1.0 / (k + dense_rank_map[doc_id])) + (1.0 / (k + bm25_rank_map[doc_id]))
        rrf_ranks = np.argsort(-rrf_scores)
        
        # Helper to find target rank
        def get_rank(ranks_list):
            for i, doc_id in enumerate(ranks_list):
                cat, text = chunk_map[doc_id]
                if cat == exp_cat and exp_kw in text.lower():
                    return i + 1
            return None
            
        r_dense = get_rank(dense_ranks)
        r_bm25 = get_rank(bm25_ranks)
        r_weighted = get_rank(weighted_ranks)
        r_rrf = get_rank(rrf_ranks)
        
        # Save failure tracking
        if query in failures_to_track:
            tracked_failures_data[query] = {
                "dense": r_dense,
                "bm25": r_bm25,
                "weighted": r_weighted,
                "rrf": r_rrf
            }
            
        # Accumulate Metrics
        for strategy, rank in [("Dense Only", r_dense), ("BM25 Only", r_bm25), 
                               ("Weighted Hybrid", r_weighted), ("RRF Hybrid", r_rrf)]:
            if rank:
                metrics[strategy]["hits"] += 1
                if rank == 1: metrics[strategy]["r1"] += 1
                if rank <= 3: metrics[strategy]["r3"] += 1
                if rank <= 5: metrics[strategy]["r5"] += 1
                metrics[strategy]["mrr"] += 1.0 / rank
                metrics[strategy]["ndcg5"] += calculate_ndcg5(rank)
                
    # Normalize
    q_count = len(ground_truth)
    for strategy in metrics:
        metrics[strategy]["r1"] /= q_count
        metrics[strategy]["r3"] /= q_count
        metrics[strategy]["r5"] /= q_count
        metrics[strategy]["mrr"] /= q_count
        metrics[strategy]["ndcg5"] /= q_count
        
    # Generate Output Reports
    art_dir = Path(r"C:\Users\Kaustav\.gemini\antigravity-ide\brain\07e03dee-9a3c-44ae-8e91-51b22b0f52ae")
    
    # 1. Benchmark MD
    bm_lines = [
        "# Phase 4A: Hybrid Retrieval Benchmark Results",
        "",
        "| Strategy | Recall@1 | Recall@3 | Recall@5 | MRR | NDCG@5 |",
        "|---|---|---|---|---|---|"
    ]
    for strategy, m in metrics.items():
        bm_lines.append(f"| {strategy} | {m['r1']:.1%} | {m['r3']:.1%} | {m['r5']:.1%} | {m['mrr']:.3f} | {m['ndcg5']:.3f} |")
    
    (art_dir / "hybrid_retrieval_benchmark.md").write_text("\n".join(bm_lines), encoding="utf-8")
    
    # 2. Failure Analysis MD
    fail_lines = [
        "# Hybrid Failure Recovery Analysis",
        "",
        "Tracks the recovery of the 4 known Dense ranking failures.",
        "",
        "| Query | Failure Cause | Dense Rank | BM25 Rank | Weighted Rank | RRF Rank | Recovered? |",
        "|---|---|---|---|---|---|---|"
    ]
    
    causes = {
        "What type of document is Category B?": "OCR Corruption",
        "What does replication across nodes ensure?": "OCR Corruption",
        "What kind of test is Category C?": "Dense Distinction",
        "What handles arbitrary failures including malicious actors?": "Dense Abstraction"
    }
    
    for q, d in tracked_failures_data.items():
        cause = causes.get(q, "Unknown")
        dr = d['dense'] or ">Top10"
        br = d['bm25'] or ">Top10"
        wr = d['weighted'] or ">Top10"
        rr = d['rrf'] or ">Top10"
        
        recovered = "✅ YES" if (wr == 1 or rr == 1) else "❌ NO"
        fail_lines.append(f"| {q} | {cause} | {dr} | {br} | {wr} | {rr} | {recovered} |")
        
    (art_dir / "hybrid_failure_analysis.md").write_text("\n".join(fail_lines), encoding="utf-8")
    
    # 3. Architecture Recommendation
    best_strategy = max(metrics.keys(), key=lambda k: metrics[k]["mrr"])
    best_mrr = metrics[best_strategy]["mrr"]
    best_r1 = metrics[best_strategy]["r1"]
    
    dense_mrr = metrics["Dense Only"]["mrr"]
    dense_r1 = metrics["Dense Only"]["r1"]
    
    mrr_diff = best_mrr - dense_mrr
    r1_diff = best_r1 - dense_r1
    
    approved = mrr_diff >= 0.03 or r1_diff >= 0.05
    
    rec_lines = [
        "# Retrieval Architecture Recommendation",
        "",
        f"**Verdict:** {'✅ APPROVED' if approved else '❌ REJECTED'}",
        "",
        "## Justification",
        f"- Target MRR Improvement: +0.03 (Actual: {mrr_diff:+.3f})",
        f"- Target Recall@1 Improvement: +5.0% (Actual: {r1_diff*100:+.1f}%)",
        "",
        f"The best performing architecture is **{best_strategy}** with an MRR of {best_mrr:.3f} and Recall@1 of {best_r1:.1%}."
    ]
    (art_dir / "retrieval_architecture_recommendation.md").write_text("\n".join(rec_lines), encoding="utf-8")
    
    print(f"[{time.time()-t_start:.1f}s] Benchmark complete. Artifacts saved.", flush=True)

if __name__ == "__main__":
    run_hybrid_benchmark()
