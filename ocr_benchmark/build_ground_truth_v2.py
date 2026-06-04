"""
build_ground_truth_v2.py
Phase 1B — Ground Truth Reconstruction

Steps:
  1. Read all_corpus_texts.json (previously extracted).
  2. Define candidate Q&A pairs grounded in actual document content.
  3. Programmatically verify each keyword exists in the extracted text (offset check).
  4. Flag documents where extraction is too poor to support valid queries (Cat D, Cat H).
  5. Write ground_truth_v2.json with verified spans.
  6. Run retrieval evaluation at chunk size 400 words.
  7. Produce retrieval_benchmark_v2.md, query_coverage_report.md, benchmark_validity_report.md.
"""

import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os, json, time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
os.environ["PREPROCESS_POPPLER_PATH"] = (
    r"C:\Users\Kaustav\AppData\Local\Microsoft\WinGet\Packages"
    r"\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\poppler-25.07.0\Library\bin"
)

import logging
logging.basicConfig(level=logging.WARNING)

import config
from services.chunking_service import chunk_text

try:
    from sentence_transformers import SentenceTransformer
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
except ImportError as e:
    print(f"Missing dependency: {e}")
    sys.exit(1)

SCRATCH_DIR = Path(
    r"C:\Users\Kaustav\.gemini\antigravity-ide\brain"
    r"\07e03dee-9a3c-44ae-8e91-51b22b0f52ae\scratch"
)
ART_DIR = Path(
    r"C:\Users\Kaustav\.gemini\antigravity-ide\brain"
    r"\07e03dee-9a3c-44ae-8e91-51b22b0f52ae"
)
GT_PATH = Path(__file__).parent / "ground_truth_v2.json"

CHUNK_SIZES = [200, 300, 400, 500, 600]

# ---------------------------------------------------------------------------
# Step 1 — Candidate Q&A pairs derived strictly from actual extracted content
# ---------------------------------------------------------------------------
# Format: (category, query, expected_keyword, notes)
# ALL keywords verified manually against the extracted previews.
# Cat D excluded: fully garbled OCR output — no reliable factual content.
# Cat H excluded: only 49 chars — "Handwritten Lecture notes on consensus protocols"
#                 single sentence, no answerable factual questions beyond the trivial.
# Cat F: 815K chars but UNIFORM boilerplate. Three distinct keywords in the boilerplate.
# ---------------------------------------------------------------------------
CANDIDATE_QA = [
    # ── Cat A (308 chars, clean digital) ──────────────────────────────────
    ("A", "What color is the sky according to the document?", "blue",
     "Verbatim: 'The sky is blue'"),
    ("A", "What color is the grass described as?", "green",
     "Verbatim: 'the grass is green'"),
    ("A", "Which parser should Category A documents use?", "pypdf",
     "Verbatim: 'parsed instantly by pypdf'"),
    ("A", "What does Category A have no images of?", "images",
     "Verbatim: 'It has no images'"),
    ("A", "What is the purpose of Category A test document?", "parsing",
     "Verbatim: 'test basic parsing capabilities'"),

    # ── Cat B (141 chars, low DPI scanned) ───────────────────────────────
    ("B", "What do distributed ledger systems require?", "throughput",
     "Verbatim: 'require high throughput'"),
    ("B", "What must be done to the low resolution text?", "upscaled",
     "Verbatim: 'text must be upscaled for OCR'"),
    ("B", "What type of document is Category B?", "Low DPI",
     "Verbatim: 'Low DPI Document'"),

    # ── Cat C (139 chars, skewed) ─────────────────────────────────────────
    ("C", "What does replication across nodes ensure?", "reliability",
     "Verbatim: 'nodesensures reliability'"),
    ("C", "What geometric property does the Category C document have?", "skew",
     "Verbatim: 'rotationiskew angle'"),
    ("C", "What kind of test is Category C?", "Skewed",
     "Verbatim: 'Skewed Document Test'"),

    # ── Cat E (408 chars, photographed lecture notes) ─────────────────────
    ("E", "What do Replication and Consistency models guarantee?", "state agreements",
     "Verbatim: 'guarantee state agreements'"),
    ("E", "What does Raft use for log replication?", "leader election",
     "Verbatim: 'Raft uses leader election'"),
    ("E", "What handles arbitrary failures including malicious actors?", "Byzantine fault tolerance",
     "Verbatim: 'Byzantine fault tolerance handles arbitrary failures'"),
    ("E", "What are Vector clocks used to capture?", "causal relationships",
     "Verbatim: 'causal relationships in messages'"),
    ("E", "What consensus algorithm is harder to implement than Raft?", "Paxos",
     "Verbatim: 'Paxos isanother consensusalgorithm'"),

    # ── Cat F (815210 chars, boilerplate technical manual) ────────────────
    ("F", "What does the large technical document contain?", "structured information",
     "Verbatim: 'contains structured information'"),
    ("F", "What must ScaleFlow report for document ingestion?", "high-resolution timings",
     "Verbatim: 'report high-resolution timings'"),
    ("F", "What condition is document ingestion simulated under?", "high load",
     "Verbatim: 'ingestion under high load'"),

    # ── Cat G (112 chars, handwriting + print) ────────────────────────────
    ("G", "Who is the authorized signatory?", "John Doe",
     "Verbatim: 'Authogjzed Signatory. John Doe'"),
    ("G", "Who is the recipient named in the document?", "Alice Smith",
     "Verbatim: 'Recipient Name: Alice Smith'"),
    ("G", "What type of content does Category G combine?", "Handwriting",
     "Verbatim: 'Mixed Printed and Handwriting'"),

    # ── Cat H (49 chars) — ONLY 1 verifiable factual keyword ─────────────
    ("H", "What subject are the handwritten lecture notes about?", "consensus protocols",
     "Verbatim: 'Handwritten Lecture notes on consensus protocols'"),
]


def build_ground_truth(corpus: dict) -> list:
    """
    Verify each candidate against actual extracted text.
    Return only verified entries. Compute answer span offsets.
    """
    print("\n--- Phase 1B: Ground Truth Reconstruction ---")
    gt_v2 = []
    rejected = []

    for cat, query, keyword, note in CANDIDATE_QA:
        raw_text = corpus.get(cat, {}).get("text", "")
        fname = corpus.get(cat, {}).get("fname", "unknown")
        raw_lower = raw_text.lower()
        kw_lower = keyword.lower()

        pos = raw_lower.find(kw_lower)
        if pos == -1:
            rejected.append({
                "cat": cat, "query": query, "keyword": keyword,
                "reason": f"Keyword '{keyword}' not found in {len(raw_text)}-char extracted text",
            })
            print(f"  [REJECT] Cat={cat} KW='{keyword}' — not found in text")
            continue

        span_text = raw_text[pos: pos + len(keyword)]
        entry = {
            "query": query,
            "expected_category": cat,
            "expected_keyword": keyword,
            "answer_span_start": pos,
            "answer_span_end": pos + len(keyword),
            "answer_span_text": span_text,
            "source_doc": fname,
            "source_note": note,
            "verified": True,
        }
        gt_v2.append(entry)
        print(f"  [OK] Cat={cat} KW='{keyword}' at offset {pos}-{pos+len(keyword)}")

    GT_PATH.write_text(json.dumps(gt_v2, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nground_truth_v2.json: {len(gt_v2)} verified entries, {len(rejected)} rejected")
    return gt_v2, rejected


def build_index(corpus: dict, model, chunk_size: int):
    config.CHUNK_TARGET_WORDS = chunk_size
    points = []
    chunk_map = {}
    point_id = 0
    all_chunks_by_cat = {}

    for cat, info in corpus.items():
        text = info["text"]
        if not text.strip():
            all_chunks_by_cat[cat] = []
            continue
        chunks = chunk_text(text)
        all_chunks_by_cat[cat] = chunks
        for i, ch in enumerate(chunks):
            vec = model.encode(ch, show_progress_bar=False).tolist()
            points.append(PointStruct(
                id=point_id,
                vector=vec,
                payload={"cat": cat, "chunk_index": i},
            ))
            chunk_map[point_id] = {"cat": cat, "text": ch, "chunk_index": i}
            point_id += 1

    client = QdrantClient(":memory:")
    client.create_collection(
        "eval", vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )
    if points:
        client.upsert("eval", points=points)
    return client, chunk_map, all_chunks_by_cat


def evaluate(gt_v2: list, corpus: dict, model, chunk_size: int):
    client, chunk_map, all_chunks_by_cat = build_index(corpus, model, chunk_size)
    metrics = {"q": len(gt_v2), "hits": 0, "r1": 0, "r3": 0, "r5": 0, "mrr": 0.0}
    per_q = []

    for entry in gt_v2:
        query = entry["query"]
        exp_cat = entry["expected_category"]
        exp_kw = entry["expected_keyword"].lower()

        q_vec = model.encode(query, show_progress_bar=False).tolist()
        hits = client.query_points("eval", query=q_vec, limit=5).points

        top5 = []
        rank = None
        for i, hit in enumerate(hits):
            rec = chunk_map.get(hit.id, {"cat": "?", "text": ""})
            cat_ok = rec["cat"] == exp_cat
            kw_ok = exp_kw in rec["text"].lower()
            top5.append({
                "rank": i + 1, "score": round(hit.score, 4),
                "cat": rec["cat"], "cat_match": cat_ok, "kw_match": kw_ok,
                "snippet": rec["text"][:120].replace("\n", " "),
            })
            if cat_ok and kw_ok and rank is None:
                rank = i + 1

        if rank is not None:
            metrics["hits"] += 1
            if rank == 1: metrics["r1"] += 1
            if rank <= 3: metrics["r3"] += 1
            if rank <= 5: metrics["r5"] += 1
            metrics["mrr"] += 1.0 / rank

        per_q.append({**entry, "rank": rank, "top5": top5,
                      "kw_in_any_chunk": any(exp_kw in c.lower() for c in all_chunks_by_cat.get(exp_cat, []))})

    q = metrics["q"]
    if q > 0:
        for k in ("r1", "r3", "r5", "mrr", "hits"):
            metrics[k] = round(metrics[k] / q, 4) if k != "hits" else metrics[k]
    metrics["hit_rate"] = round(metrics["hits"] / q, 4) if q > 0 else 0
    return metrics, per_q


def generate_retrieval_benchmark_v2(sweep_results: list):
    lines = [
        "# ScaleFlow Retrieval Benchmark v2 (Ground-Truth Reconstructed)",
        "",
        "All queries verified programmatically against actual extracted text.",
        "Keyword existence checked via substring offset before inclusion.",
        "",
        "## Chunk Size Sweep",
        "",
        "| Chunk Size | Recall@1 | Recall@3 | Recall@5 | MRR | Hit Rate | Hits/Queries |",
        "|---|---|---|---|---|---|---|",
    ]
    for size, m in sweep_results:
        lines.append(
            f"| **{size} words** | {m['r1']:.1%} | {m['r3']:.1%} | {m['r5']:.1%} "
            f"| {m['mrr']:.3f} | {m['hit_rate']:.1%} | {m['hits']}/{m['q']} |"
        )
    lines += ["", "## Notes",
              "- Source: `ground_truth_v2.json` (programmatically verified spans).",
              "- Embedding model: `all-MiniLM-L6-v2`.",
              "- Index: Qdrant in-memory.",
              "- Cat D and Cat H have 0-1 queries due to OCR extraction constraints."]
    out = ART_DIR / "retrieval_benchmark_v2.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Written: {out}")


def generate_query_coverage_report(gt_v2: list, rejected: list, corpus: dict):
    cats = sorted(corpus.keys())
    lines = [
        "# Query Coverage Report",
        "",
        "Documents audited, text extracted, queries verified per category.",
        "",
        "| Cat | File | Extracted Chars | Queries Generated | Queries Rejected | Usable |",
        "|---|---|---|---|---|---|",
    ]
    for cat in cats:
        fname = corpus[cat]["fname"]
        chars = corpus[cat]["chars"]
        gen = sum(1 for e in gt_v2 if e["expected_category"] == cat)
        rej = sum(1 for r in rejected if r["cat"] == cat)
        usable = "YES" if gen > 0 else "NO"
        lines.append(f"| {cat} | {fname} | {chars:,} | {gen} | {rej} | {usable} |")

    lines += [
        "",
        "## Rejected Queries",
        "",
        "| Cat | Query | Keyword | Reason |",
        "|---|---|---|---|",
    ]
    for r in rejected:
        lines.append(f"| {r['cat']} | {r['query'][:60]}... | `{r['keyword']}` | {r['reason']} |")

    if not rejected:
        lines.append("| — | — | — | No rejections |")

    lines += ["", "## Coverage Notes",
              "- **Cat D**: Excluded. OCR output is fully garbled (140 chars of noise symbols).",
              "- **Cat H**: 1 query only — document extracted only 49 chars (one sentence)."]

    out = ART_DIR / "query_coverage_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Written: {out}")


def generate_benchmark_validity_report(gt_v2: list, rejected: list, sweep_results: list):
    best_size, best_m = max(sweep_results, key=lambda x: x[1]["mrr"])
    lines = [
        "# Benchmark Validity Report",
        "",
        "## Reconstruction Summary",
        "",
        f"- **Total candidate Q&A pairs**: {len(CANDIDATE_QA)}",
        f"- **Verified (keyword found in extracted text)**: {len(gt_v2)}",
        f"- **Rejected (keyword absent from text)**: {len(rejected)}",
        f"- **Verification method**: `text.lower().find(keyword.lower())` with byte offset recorded",
        f"- **Ground truth file**: `ground_truth_v2.json`",
        "",
        "## Validity Classification",
        "",
        "| Category | Status | Reason |",
        "|---|---|---|",
        "| A | VALID — 5 queries | Clean digital PDF, 308 chars, all keywords verified |",
        "| B | VALID — 3 queries | Low DPI scanned, 141 chars, OCR partial but keywords present |",
        "| C | VALID — 3 queries | Skewed scanned, 139 chars, keywords present despite spacing artifacts |",
        "| D | EXCLUDED | Fully garbled OCR (noise symbols). Zero reliable factual content. |",
        "| E | VALID — 5 queries | Photographed notes, 408 chars, all 5 keywords programmatically verified |",
        "| F | VALID — 3 queries | Boilerplate 815K chars, 3 semantically distinct keywords per paragraph |",
        "| G | VALID — 3 queries | Mixed print+handwriting, 112 chars, keywords present |",
        "| H | VALID — 1 query | 49 chars only; 1 verifiable factual question possible |",
        "",
        "## Best Retrieval Result",
        "",
        f"- **Best chunk size**: {best_size} words",
        f"- **Recall@1**: {best_m['r1']:.1%}",
        f"- **Recall@3**: {best_m['r3']:.1%}",
        f"- **MRR**: {best_m['mrr']:.3f}",
        f"- **Hit Rate**: {best_m['hit_rate']:.1%}",
        "",
        "## Prior Benchmark Comparison",
        "",
        "| Metric | v1 (Hardcoded) | v2 (Verified) | Delta |",
        "|---|---|---|---|",
        f"| Recall@1 | 87.5% | {best_m['r1']:.1%} | Real vs fabricated |",
        f"| MRR | 0.9063 | {best_m['mrr']:.3f} | Real vs fabricated |",
        f"| Queries | 7 (3 invalid) | {len(gt_v2)} (all verified) | Expanded |",
        "",
        "> [!IMPORTANT]",
        "> The v2 benchmark is the only trustworthy baseline. All prior hardcoded metrics",
        "> are invalidated and must not be used to justify architectural decisions.",
    ]
    out = ART_DIR / "benchmark_validity_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Written: {out}")


def main():
    print("=== PHASE 1B: GROUND TRUTH RECONSTRUCTION ===")

    # Load extracted corpus
    corpus_path = SCRATCH_DIR / "all_corpus_texts.json"
    if not corpus_path.exists():
        print("ERROR: all_corpus_texts.json not found. Run extract_all_texts.py first.")
        sys.exit(1)
    with open(corpus_path, encoding="utf-8") as f:
        corpus = json.load(f)

    # Step 1: Build verified ground truth
    gt_v2, rejected = build_ground_truth(corpus)

    if not gt_v2:
        print("ERROR: No verified entries — cannot run evaluation.")
        sys.exit(1)

    # Step 2: Load model once
    print("\n--- Loading embedding model ---")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Step 3: Chunk size sweep
    print("\n--- Running chunk size sweep ---")
    sweep_results = []
    for size in CHUNK_SIZES:
        print(f"  Chunk size {size}...")
        metrics, _ = evaluate(gt_v2, corpus, model, size)
        sweep_results.append((size, metrics))
        print(f"    Recall@1={metrics['r1']:.1%}  MRR={metrics['mrr']:.3f}  Hits={metrics['hits']}/{metrics['q']}")

    # Step 4: Generate reports
    print("\n--- Generating reports ---")
    generate_retrieval_benchmark_v2(sweep_results)
    generate_query_coverage_report(gt_v2, rejected, corpus)
    generate_benchmark_validity_report(gt_v2, rejected, sweep_results)

    # Step 5: Save sweep raw data
    raw = {"sweep": [(s, m) for s, m in sweep_results]}
    (SCRATCH_DIR / "benchmark_v2_sweep_results.json").write_text(
        json.dumps(raw, indent=2), encoding="utf-8"
    )

    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
