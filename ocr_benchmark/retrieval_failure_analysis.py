"""
retrieval_failure_analysis.py
Forensic analysis of retrieval failures -- captures raw extracted text,
all chunks, top-5 retrieved results with similarity scores for every
ground truth query, and saves evidence to JSON + Markdown.
"""

import io
import os
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import json
from pathlib import Path
import logging

# Suppress noisy INFO from parser
logging.basicConfig(level=logging.WARNING, format='%(message)s')

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

POPPLER_BIN = r"C:\Users\Kaustav\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin"
os.environ["PREPROCESS_POPPLER_PATH"] = POPPLER_BIN

import config
from services.pdf_parser import parse_pdf
from services.chunking_service import chunk_text

try:
    from sentence_transformers import SentenceTransformer
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
except ImportError as e:
    print(f"Missing dependency: {e}")
    sys.exit(1)

TEST_DATA_DIR = REPO_ROOT / "backend" / "test_data"
GROUND_TRUTH_PATH = Path(__file__).parent / "ground_truth.json"
SCRATCH_DIR = Path(r"C:\Users\Kaustav\.gemini\antigravity-ide\brain\07e03dee-9a3c-44ae-8e91-51b22b0f52ae\scratch")
ART_DIR = Path(r"C:\Users\Kaustav\.gemini\antigravity-ide\brain\07e03dee-9a3c-44ae-8e91-51b22b0f52ae")

# Use 400 words as the representative chunk size (previous claimed-optimal)
CHUNK_SIZE = 400

TEST_DOCS = {
    "B": "category_B_low_dpi.pdf",
    "C": "category_C_skewed.pdf",
    "D": "category_D_noisy.pdf",
    "E": "photographed_notes.pdf",
    "F": "category_F_large_doc.pdf",
    "G": "category_G_handwritten_names.pdf",
    "H": "category_H_handwritten.pdf",
}


def extract_corpus_texts():
    print("--- Phase 1: Extracting corpus texts ---")
    texts = {}
    for cat, fname in TEST_DOCS.items():
        fpath = TEST_DATA_DIR / fname
        if not fpath.exists():
            print(f"  MISSING: {fname}")
            texts[cat] = ""
            continue
        print(f"  Parsing {fname}...")
        res = parse_pdf(str(fpath), document_type="MIXED", routing_confidence=1.0)
        texts[cat] = res.text
        print(f"    -> {len(res.text)} chars extracted")
    return texts


def build_index(corpus_texts, model):
    print(f"\n--- Phase 2: Chunking (target={CHUNK_SIZE} words) and indexing ---")
    config.CHUNK_TARGET_WORDS = CHUNK_SIZE

    points = []
    chunk_map = {}  # id -> {"cat": str, "text": str, "chunk_index": int}
    point_id = 0

    all_chunks_by_cat = {}
    for cat, text in corpus_texts.items():
        if not text.strip():
            print(f"  Cat {cat}: EMPTY TEXT — no chunks generated")
            all_chunks_by_cat[cat] = []
            continue
        chunks = chunk_text(text)
        all_chunks_by_cat[cat] = chunks
        print(f"  Cat {cat}: {len(chunks)} chunks from {len(text)} chars")
        for i, chunk in enumerate(chunks):
            vec = model.encode(chunk, show_progress_bar=False).tolist()
            points.append(PointStruct(id=point_id, vector=vec, payload={"cat": cat, "chunk_index": i}))
            chunk_map[point_id] = {"cat": cat, "text": chunk, "chunk_index": i}
            point_id += 1

    print(f"  Total points indexed: {point_id}")

    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name="eval",
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )
    if points:
        client.upsert(collection_name="eval", points=points)

    return client, chunk_map, all_chunks_by_cat


def run_forensic_analysis():
    with open(GROUND_TRUTH_PATH) as f:
        ground_truth = json.load(f)

    corpus_texts = extract_corpus_texts()

    print("\n--- Phase 3: Loading embedding model ---")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    client, chunk_map, all_chunks_by_cat = build_index(corpus_texts, model)

    print("\n--- Phase 4: Running forensic query analysis ---")

    per_query_results = []

    for gt in ground_truth:
        query = gt["query"]
        exp_cat = gt["expected_category"]
        exp_kw = gt["expected_keyword"].lower()

        q_vec = model.encode(query, show_progress_bar=False).tolist()
        hits = client.query_points(collection_name="eval", query=q_vec, limit=5).points

        top5 = []
        for i, hit in enumerate(hits):
            rec = chunk_map.get(hit.id, {"cat": "?", "text": "", "chunk_index": -1})
            chunk_text_lower = rec["text"].lower()
            kw_in_chunk = exp_kw in chunk_text_lower
            cat_match = rec["cat"] == exp_cat
            top5.append({
                "rank": i + 1,
                "score": round(hit.score, 4),
                "cat": rec["cat"],
                "chunk_index": rec["chunk_index"],
                "cat_match": cat_match,
                "kw_match": kw_in_chunk,
                "text_snippet": rec["text"][:300].replace("\n", " "),
                "full_text": rec["text"],
            })

        # Check if keyword is actually present in ANY chunk of expected category
        expected_cat_chunks = all_chunks_by_cat.get(exp_cat, [])
        kw_in_any_expected_chunk = any(exp_kw in c.lower() for c in expected_cat_chunks)
        kw_in_raw_text = exp_kw in corpus_texts.get(exp_cat, "").lower()
        expected_cat_chunk_count = len(expected_cat_chunks)

        # Determine if query succeeded
        success = any(r["cat_match"] and r["kw_match"] for r in top5)

        per_query_results.append({
            "query": query,
            "expected_category": exp_cat,
            "expected_keyword": exp_kw,
            "success": success,
            "kw_in_raw_text": kw_in_raw_text,
            "kw_in_any_expected_chunk": kw_in_any_expected_chunk,
            "expected_cat_chunk_count": expected_cat_chunk_count,
            "raw_text_length": len(corpus_texts.get(exp_cat, "")),
            "top5": top5,
        })

        status = "[HIT]" if success else "[MISS]"
        print(f"  {status} '{query}'")
        print(f"         Expected: Cat={exp_cat}, KW='{exp_kw}'")
        print(f"         KW in raw text: {kw_in_raw_text} | KW in any chunk: {kw_in_any_expected_chunk}")
        print(f"         Top result: Cat={top5[0]['cat']}, Score={top5[0]['score']}, KW={top5[0]['kw_match']}")

    return per_query_results, corpus_texts, all_chunks_by_cat


def save_raw_evidence(per_query_results, corpus_texts, all_chunks_by_cat):
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

    # Save raw extracted texts
    raw_texts_export = {cat: {"length": len(t), "preview": t[:500]} for cat, t in corpus_texts.items()}

    evidence = {
        "chunk_size_used": CHUNK_SIZE,
        "raw_texts": raw_texts_export,
        "chunks_per_cat": {cat: len(chunks) for cat, chunks in all_chunks_by_cat.items()},
        "per_query_results": per_query_results,
    }

    out_path = SCRATCH_DIR / "retrieval_failure_evidence.json"
    # Remove full_text from JSON export to keep it readable (keep snippet)
    export = json.loads(json.dumps(evidence))
    for r in export["per_query_results"]:
        for t in r["top5"]:
            del t["full_text"]

    out_path.write_text(json.dumps(export, indent=2), encoding="utf-8")
    print(f"\nRaw evidence saved: {out_path}")
    return evidence


def generate_failure_report(per_query_results, corpus_texts, all_chunks_by_cat):
    """Generate the Markdown failure analysis report."""
    lines = [
        "# Retrieval Failure Analysis Report",
        "",
        f"**Chunk size**: {CHUNK_SIZE} words | **Embedding model**: all-MiniLM-L6-v2 | **Index**: Qdrant (in-memory)",
        "",
    ]

    failure_causes = {
        "OCR Extraction Failure": 0,
        "Chunking Issue": 0,
        "Embedding Mismatch": 0,
        "Ground-Truth Problem": 0,
    }

    for r in per_query_results:
        status = "HIT" if r["success"] else "MISS"
        status_icon = "PASS" if r["success"] else "FAIL"
        lines += [
            f"---",
            f"## Query: \"{r['query']}\"",
            f"**Expected source**: Category `{r['expected_category']}` | **Expected keyword**: `{r['expected_keyword']}`  ",
            f"**Result**: {status}",
            "",
            "### Evidence: Raw Extraction",
            f"- Raw text extracted from Cat `{r['expected_category']}`: **{r['raw_text_length']} chars**",
            f"- Keyword `{r['expected_keyword']}` present in raw text: **{r['kw_in_raw_text']}**",
            f"- Keyword present in any chunk of Cat `{r['expected_category']}`: **{r['kw_in_any_expected_chunk']}**",
            f"- Chunks generated from Cat `{r['expected_category']}`: **{r['expected_cat_chunk_count']}**",
            "",
            "### Top-5 Retrieved Chunks",
            "",
            "| Rank | Score | Cat | KW Match | Snippet |",
            "|---|---|---|---|---|",
        ]
        for t in r["top5"]:
            cat_mark = "[CAT-OK]" if t["cat_match"] else "[CAT-WRONG]"
            kw_mark = "[KW-FOUND]" if t["kw_match"] else "[KW-MISSING]"
            snippet = t["text_snippet"][:120].replace("|", "\\|")
            lines.append(f"| {t['rank']} | {t['score']} | {t['cat']} {cat_mark} | {kw_mark} | {snippet} |")

        lines.append("")

        # Failure classification
        if not r["success"]:
            lines.append("### Failure Classification")

            if r["raw_text_length"] < 50:
                cause = "OCR Extraction Failure"
                reason = f"Only {r['raw_text_length']} chars extracted from source document. OCR produced near-empty output."
                failure_causes[cause] += 1
            elif not r["kw_in_raw_text"]:
                cause = "OCR Extraction Failure"
                reason = f"Keyword `{r['expected_keyword']}` is absent from all {r['raw_text_length']} chars of extracted text. The expected content was not recovered by OCR."
                failure_causes[cause] += 1
            elif not r["kw_in_any_expected_chunk"]:
                cause = "Chunking Issue"
                reason = f"Keyword `{r['expected_keyword']}` is in the raw text but absent from all {r['expected_cat_chunk_count']} chunks. The chunker discarded or truncated the relevant passage."
                failure_causes[cause] += 1
            else:
                # Keyword IS in a chunk — but retrieval failed to rank it top-5
                # Check if Cat F match was retrieved but wrong cat ranked higher
                top_cat = r["top5"][0]["cat"] if r["top5"] else "?"
                top_score = r["top5"][0]["score"] if r["top5"] else 0
                cause = "Embedding Mismatch"
                reason = (
                    f"Keyword `{r['expected_keyword']}` IS present in chunks from Cat `{r['expected_category']}`, "
                    f"but none appeared in the top-5 results. "
                    f"Top result was Cat `{top_cat}` with score {top_score:.4f}. "
                    f"The semantic embedding of the query did not map close enough to the relevant chunk vector."
                )
                failure_causes[cause] += 1

            lines += [
                f"- **Cause**: {cause}",
                f"- **Evidence**: {reason}",
                "",
            ]

    # Confusion matrix
    lines += [
        "---",
        "## Failure Cause Confusion Matrix",
        "",
        "| Failure Cause | Count | Proportion |",
        "|---|---|---|",
    ]
    total_fails = sum(failure_causes.values())
    for cause, count in failure_causes.items():
        pct = f"{count/total_fails:.0%}" if total_fails > 0 else "0%"
        lines.append(f"| {cause} | {count} | {pct} |")

    lines += [
        "",
        f"**Total failures**: {total_fails} / {len(per_query_results)} queries",
    ]

    out_path = ART_DIR / "retrieval_failure_analysis.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report generated: {out_path}")


def main():
    per_query_results, corpus_texts, all_chunks_by_cat = run_forensic_analysis()
    save_raw_evidence(per_query_results, corpus_texts, all_chunks_by_cat)
    generate_failure_report(per_query_results, corpus_texts, all_chunks_by_cat)
    print("\nDone.")


if __name__ == "__main__":
    main()
