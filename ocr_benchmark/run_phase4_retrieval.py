"""
Phase 4 — Retrieval Quality Benchmark
Loads extracted texts from extracted/{engine}_{cat}.txt
Indexes them with sentence-transformers + qdrant in-memory
Queries for Categories B and C, records similarity scores and keyword presence.
Writes retrieval_quality_validation.md.
"""

import os, sys
from pathlib import Path

REPO_ROOT     = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = Path(__file__).parent / "extracted"

CATEGORIES    = ["B", "C", "D", "E", "F", "G", "H"]
ENGINES       = ["Tesseract", "PaddleOCR", "EasyOCR", "DocTR", "Surya"]

QUERIES = {
    "B": {
        "query":   "What do distributed ledger systems require?",
        "keyword": "throughput",
    },
    "C": {
        "query":   "What does replication across nodes ensure?",
        "keyword": "reliability",
    },
}


def load_extracted(engine: str) -> dict:
    texts = {}
    for cat in CATEGORIES:
        p = EXTRACTED_DIR / f"{engine}_{cat}.txt"
        if p.exists():
            texts[cat] = p.read_text(encoding="utf-8")
    return texts


def run_retrieval_for_engine(engine: str, model, QdrantClient, VectorParams, Distance, PointStruct) -> dict:
    texts = load_extracted(engine)
    if not texts:
        return {"engine": engine, "error": "No extracted texts found", "results": {}}

    client = QdrantClient(":memory:")
    if client.collection_exists("bench"):
        client.delete_collection("bench")
    client.create_collection(
        collection_name="bench",
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

    points = []
    for i, (cat, txt) in enumerate(texts.items()):
        if len(txt.strip()) > 5:
            vec = model.encode(txt, show_progress_bar=False).tolist()
            points.append(PointStruct(id=i, vector=vec, payload={"cat": cat}))

    if points:
        client.upsert(collection_name="bench", points=points)

    results = {}
    for q_cat, q_info in QUERIES.items():
        q_vec = model.encode(q_info["query"], show_progress_bar=False).tolist()
        hits = client.query_points(collection_name="bench", query=q_vec, limit=1).points
        if hits:
            top    = hits[0]
            txt    = texts.get(top.payload["cat"], "")
            kw_hit = q_info["keyword"].lower() in txt.lower()
            results[q_cat] = {
                "top_similarity":  round(top.score, 4),
                "retrieved_cat":   top.payload["cat"],
                "correct_cat":     top.payload["cat"] == q_cat,
                "keyword_in_text": kw_hit,
                "snippet":         txt[:120].replace("\n", " "),
            }
        else:
            results[q_cat] = {
                "top_similarity": 0.0, "retrieved_cat": None,
                "correct_cat": False, "keyword_in_text": False, "snippet": "",
            }

    return {"engine": engine, "error": None, "results": results}


def generate_report(all_results: list) -> str:
    lines = [
        "# Phase 4 — Retrieval Quality Validation Report",
        "",
        "## Query Definitions",
        "",
        "| Category | Query | Expected Keyword |",
        "| :--- | :--- | :--- |",
    ]
    for cat, q in QUERIES.items():
        lines.append(f"| {cat} | {q['query']} | `{q['keyword']}` |")

    lines += [
        "",
        "## Per-Engine Retrieval Results",
        "",
        "| Engine | Query Cat | Similarity | Retrieved Cat | Correct | Keyword Hit |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for er in all_results:
        eng = er["engine"]
        if er.get("error"):
            lines.append(f"| {eng} | — | — | — | ❌ {er['error']} | — |")
            continue
        for q_cat, res in er["results"].items():
            sim  = res["top_similarity"]
            rcat = res["retrieved_cat"] or "N/A"
            corr = "✅" if res["correct_cat"] else "❌"
            kw   = "✅" if res["keyword_in_text"] else "❌"
            lines.append(f"| {eng} | {q_cat} | {sim} | {rcat} | {corr} | {kw} |")

    return "\n".join(lines)


def main():
    print("=== Phase 4: Retrieval Quality Benchmark ===")

    try:
        from sentence_transformers import SentenceTransformer
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct
    except ImportError as e:
        print(f"  ❌ Missing dependency: {e}")
        return []

    model = SentenceTransformer("all-MiniLM-L6-v2")
    all_results = []

    for eng in ENGINES:
        print(f"  Running retrieval for {eng}...")
        r = run_retrieval_for_engine(eng, model, QdrantClient, VectorParams, Distance, PointStruct)
        all_results.append(r)
        for q_cat, res in r.get("results", {}).items():
            print(f"    Cat {q_cat}: sim={res['top_similarity']} correct={res['correct_cat']} kw={res['keyword_in_text']}")

    report = generate_report(all_results)
    out = Path(__file__).parent / "retrieval_quality_validation.md"
    out.write_text(report, encoding="utf-8")
    print(f"\nReport written: {out}")
    return all_results


if __name__ == "__main__":
    main()
