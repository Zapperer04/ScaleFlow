"""
run_embedding_benchmark.py
Phase 1-5 — Embedding Architecture Benchmark

Evaluates different embedding models against the Ground Truth v2 dataset.
Measures retrieval performance and resource usage.
"""

import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os, json, time, math, tracemalloc
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

import config
from services.chunking_service import chunk_text

try:
    from sentence_transformers import SentenceTransformer
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
except ImportError as e:
    print(f"Missing dependency: {e}")
    sys.exit(1)

ART_DIR = Path(r"C:\Users\Kaustav\.gemini\antigravity-ide\brain\07e03dee-9a3c-44ae-8e91-51b22b0f52ae")
SCRATCH_DIR = ART_DIR / "scratch"
GT_PATH = Path(__file__).parent / "ground_truth_v2.json"
CORPUS_PATH = SCRATCH_DIR / "all_corpus_texts.json"

MODELS = {
    "all-MiniLM-L6-v2": {
        "id": "all-MiniLM-L6-v2",
        "doc_prefix": "",
        "query_prefix": ""
    },
    "BAAI/bge-small-en-v1.5": {
        "id": "BAAI/bge-small-en-v1.5",
        "doc_prefix": "",
        "query_prefix": "Represent this sentence for searching relevant passages: "
    },
    "BAAI/bge-base-en-v1.5": {
        "id": "BAAI/bge-base-en-v1.5",
        "doc_prefix": "",
        "query_prefix": "Represent this sentence for searching relevant passages: "
    },
    "intfloat/e5-base-v2": {
        "id": "intfloat/e5-base-v2",
        "doc_prefix": "passage: ",
        "query_prefix": "query: "
    }
}

CHUNK_SIZE = 300  # Based on previous optimal finding

def calculate_ndcg(rank, k=5):
    if rank is None or rank > k:
        return 0.0
    # Binary relevance: Ideal DCG is 1.0 (since there's only 1 correct chunk we care about)
    return 1.0 / math.log2(rank + 1)

def run_benchmark():
    print("=== PHASE 1: Embedding Benchmark ===")
    
    with open(GT_PATH, encoding="utf-8") as f:
        ground_truth = json.load(f)
        
    with open(CORPUS_PATH, encoding="utf-8") as f:
        corpus = json.load(f)
        
    # Pre-chunk the corpus (same chunks for all models)
    config.CHUNK_TARGET_WORDS = CHUNK_SIZE
    print(f"Chunking corpus at {CHUNK_SIZE} words...")
    chunks_by_cat = {}
    total_chunks = 0
    for cat, info in corpus.items():
        text = info["text"]
        if not text.strip():
            chunks_by_cat[cat] = []
            continue
        chunks = chunk_text(text)
        chunks_by_cat[cat] = chunks
        total_chunks += len(chunks)
    print(f"Total chunks generated: {total_chunks}")
    
    results = {}
    
    for model_name, m_config in MODELS.items():
        print(f"\n--- Evaluating {model_name} ---")
        
        # 1. Cold Start
        tracemalloc.start()
        start_t = time.time()
        model = SentenceTransformer(m_config["id"])
        load_time = time.time() - start_t
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_ram_mb = peak / (1024 * 1024)
        print(f"Loaded in {load_time:.2f}s | Peak RAM: {peak_ram_mb:.1f} MB")
        
        # 2. Index Build
        vector_size = model.get_sentence_embedding_dimension()
        client = QdrantClient(":memory:")
        client.create_collection(
            "eval", vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )
        
        points = []
        point_id = 0
        chunk_map = {}
        
        start_t = time.time()
        for cat, chunks in chunks_by_cat.items():
            for i, ch in enumerate(chunks):
                doc_text = m_config["doc_prefix"] + ch
                vec = model.encode(doc_text, show_progress_bar=False).tolist()
                points.append(PointStruct(id=point_id, vector=vec, payload={"cat": cat, "chunk_index": i}))
                chunk_map[point_id] = {"cat": cat, "text": ch}
                point_id += 1
                
        if points:
            client.upsert("eval", points=points)
        index_time = time.time() - start_t
        print(f"Indexed {point_id} vectors in {index_time:.2f}s")
        
        # 3. Warm Query Execution
        metrics = {
            "q": len(ground_truth),
            "hits": 0, "r1": 0, "r3": 0, "r5": 0, 
            "mrr": 0.0, "ndcg5": 0.0, "avg_sim": 0.0
        }
        
        per_query_evidence = []
        start_t = time.time()
        
        for entry in ground_truth:
            query = entry["query"]
            exp_cat = entry["expected_category"]
            exp_kw = entry["expected_keyword"].lower()
            
            q_text = m_config["query_prefix"] + query
            q_vec = model.encode(q_text, show_progress_bar=False).tolist()
            
            hits = client.query_points("eval", query=q_vec, limit=5).points
            
            top5 = []
            rank = None
            sim_sum = 0.0
            
            for i, hit in enumerate(hits):
                rec = chunk_map.get(hit.id, {"cat": "?", "text": ""})
                cat_ok = rec["cat"] == exp_cat
                kw_ok = exp_kw in rec["text"].lower()
                score = float(hit.score)
                sim_sum += score
                
                top5.append({
                    "rank": i + 1,
                    "score": round(score, 4),
                    "cat": rec["cat"],
                    "cat_match": cat_ok,
                    "kw_match": kw_ok,
                    "snippet": rec["text"][:120].replace("\n", " ")
                })
                
                if cat_ok and kw_ok and rank is None:
                    rank = i + 1
                    
            if hits:
                metrics["avg_sim"] += (sim_sum / len(hits))
                
            if rank is not None:
                metrics["hits"] += 1
                if rank == 1: metrics["r1"] += 1
                if rank <= 3: metrics["r3"] += 1
                if rank <= 5: metrics["r5"] += 1
                metrics["mrr"] += 1.0 / rank
                metrics["ndcg5"] += calculate_ndcg(rank)
                
            per_query_evidence.append({
                "query": query,
                "expected_category": exp_cat,
                "expected_keyword": exp_kw,
                "rank": rank,
                "top5": top5
            })
            
        query_time = time.time() - start_t
        avg_query_lat = query_time / len(ground_truth)
        
        q = metrics["q"]
        if q > 0:
            metrics["r1"] /= q
            metrics["r3"] /= q
            metrics["r5"] /= q
            metrics["mrr"] /= q
            metrics["ndcg5"] /= q
            metrics["avg_sim"] /= q
            metrics["hit_rate"] = metrics["hits"] / q
            
        print(f"Recall@1: {metrics['r1']:.1%} | MRR: {metrics['mrr']:.3f} | Latency: {avg_query_lat*1000:.1f}ms")
        
        results[model_name] = {
            "resource": {
                "load_time_s": load_time,
                "peak_ram_mb": peak_ram_mb,
                "index_time_s": index_time,
                "total_vectors": point_id,
                "avg_query_lat_s": avg_query_lat
            },
            "metrics": metrics,
            "evidence": per_query_evidence
        }
        
        # Free memory
        del model
        del client
        
    return results

def generate_reports(results):
    print("\n--- Generating Reports ---")
    
    # 1. Benchmark Report
    lines = [
        "# Embedding Benchmark Report",
        "",
        "## Performance Comparison",
        "",
        "| Model | Recall@1 | Recall@3 | Recall@5 | MRR | NDCG@5 | Hit Rate | Avg Sim |",
        "|---|---|---|---|---|---|---|---|"
    ]
    for model, data in results.items():
        m = data["metrics"]
        lines.append(
            f"| {model} | {m['r1']:.1%} | {m['r3']:.1%} | {m['r5']:.1%} | {m['mrr']:.3f} | "
            f"{m['ndcg5']:.3f} | {m['hit_rate']:.1%} | {m['avg_sim']:.3f} |"
        )
    (ART_DIR / "embedding_benchmark_report.md").write_text("\n".join(lines), encoding="utf-8")
    
    # 2. Resource Report
    lines = [
        "# Embedding Resource Report",
        "",
        "| Model | Load Time (s) | Peak RAM (MB) | Index Time (s) | Avg Query Latency (ms) | Vectors |",
        "|---|---|---|---|---|---|"
    ]
    for model, data in results.items():
        r = data["resource"]
        lines.append(
            f"| {model} | {r['load_time_s']:.2f} | {r['peak_ram_mb']:.1f} | {r['index_time_s']:.2f} | "
            f"{r['avg_query_lat_s']*1000:.1f} | {r['total_vectors']} |"
        )
    (ART_DIR / "embedding_resource_report.md").write_text("\n".join(lines), encoding="utf-8")
    
    # 3. Failure Analysis
    lines = [
        "# Embedding Failure Analysis",
        "",
        "Detailed breakdown of queries where Rank > 1 or retrieval failed completely.",
        ""
    ]
    
    failure_counts = {model: {"total": 0, "mismatch": 0, "rank_drop": 0} for model in results}
    
    for model, data in results.items():
        lines.extend([f"## {model}", ""])
        failures = [q for q in data["evidence"] if q["rank"] is None or q["rank"] > 1]
        failure_counts[model]["total"] = len(failures)
        
        if not failures:
            lines.extend(["No failures or rank drops recorded.", ""])
            continue
            
        for f in failures:
            status = "MISS" if f["rank"] is None else f"RANK DROP (Rank {f['rank']})"
            if f["rank"] is None:
                failure_counts[model]["mismatch"] += 1
                cat = "Semantic Mismatch"
            else:
                failure_counts[model]["rank_drop"] += 1
                cat = "Ranking Issue"
                
            lines.extend([
                f"### Query: \"{f['query']}\"",
                f"- **Status**: {status}",
                f"- **Expected Category**: {f['expected_category']}",
                f"- **Classification**: {cat}",
                "",
                "**Top 3 Results:**",
                "| Rank | Score | Cat | KW Match | Snippet |",
                "|---|---|---|---|---|"
            ])
            for t in f["top5"][:3]:
                c_mark = "✅" if t["cat_match"] else "❌"
                k_mark = "✅" if t["kw_match"] else "❌"
                lines.append(f"| {t['rank']} | {t['score']} | {t['cat']} {c_mark} | {k_mark} | {t['snippet']} |")
            lines.append("")
            
    (ART_DIR / "embedding_failure_analysis.md").write_text("\n".join(lines), encoding="utf-8")
    
    # 4. Recommendation
    base = results["all-MiniLM-L6-v2"]
    
    lines = [
        "# Embedding Architecture Recommendation",
        "",
        "## Evaluation Criteria",
        "- Minimum Improvement: +5% Recall@1 or +0.05 MRR",
        "",
        "## Model Trade-offs vs all-MiniLM-L6-v2",
        "",
        "| Model | Δ Recall@1 | Δ MRR | Δ RAM (MB) | Δ Latency (ms) | Recommendation |",
        "|---|---|---|---|---|---|"
    ]
    
    recommended_model = "all-MiniLM-L6-v2"
    best_mrr = base["metrics"]["mrr"]
    
    for model, data in results.items():
        if model == "all-MiniLM-L6-v2":
            continue
            
        d_r1 = data["metrics"]["r1"] - base["metrics"]["r1"]
        d_mrr = data["metrics"]["mrr"] - base["metrics"]["mrr"]
        d_ram = data["resource"]["peak_ram_mb"] - base["resource"]["peak_ram_mb"]
        d_lat = (data["resource"]["avg_query_lat_s"] - base["resource"]["avg_query_lat_s"]) * 1000
        
        justified = (d_r1 >= 0.05) or (d_mrr >= 0.05)
        rec = "UPGRADE JUSTIFIED" if justified else "NOT JUSTIFIED"
        
        if justified and data["metrics"]["mrr"] > best_mrr:
            best_mrr = data["metrics"]["mrr"]
            recommended_model = model
            
        lines.append(
            f"| {model} | {d_r1:+.1%} | {d_mrr:+.3f} | {d_ram:+.1f} | {d_lat:+.1f} | **{rec}** |"
        )
        
    lines.extend([
        "",
        "## Conclusion",
        f"**Selected Model**: `{recommended_model}`",
        "",
        "If a challenger met the criteria and achieved the highest MRR, it is recommended. "
        "Otherwise, the baseline MiniLM remains the optimal choice due to its balance of performance and efficiency."
    ])
    
    (ART_DIR / "embedding_architecture_recommendation.md").write_text("\n".join(lines), encoding="utf-8")
    
    # 5. Save Raw JSON
    (SCRATCH_DIR / "embedding_benchmark_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("Reports generated.")

def main():
    results = run_benchmark()
    generate_reports(results)
    
if __name__ == "__main__":
    main()
