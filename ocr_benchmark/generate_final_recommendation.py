"""
Phase 6 — Final Recommendation Generator
Loads outputs from Phases 3–5, computes a weighted score per engine, and
writes final_ocr_architecture_recommendation.md with a justified Option A/B/C decision.

Weighted Score Matrix:
  Recovery Rate (avg across cats)  25%
  WER (inverted — lower is better) 20%
  Retrieval Success Rate           20%
  Warm Inference Latency (inv)     15%
  Peak Memory (inv)                10%
  Table Cell Recovery (Cat F)      10%
"""

import json, math
from pathlib import Path

ENGINES = ["Tesseract", "PaddleOCR", "EasyOCR", "DocTR", "Surya"]

WEIGHTS = {
    "recovery_rate":     0.25,
    "wer_inv":           0.20,   # 1 - WER (capped to [0,1])
    "retrieval_success": 0.20,
    "warm_latency_inv":  0.15,   # 1 / (1 + warm_s)  normalised
    "peak_mem_inv":      0.10,   # 1 / peak_rss_mb   normalised
    "table_recovery":    0.10,
}


def _safe(v, default=0.0):
    return v if (v is not None and not (isinstance(v, float) and math.isnan(v))) else default


# ── Data loaders — parse the markdown tables written by prior phases ───────────

def load_phase3(path: Path) -> dict:
    """Parse warm_vs_cold_benchmark.md → {engine: {cold_start_s, warm_inference_s, peak_rss_mb}}"""
    data = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or line.startswith("| Engine") or line.startswith("| :"):
            continue
        cols = [c.strip() for c in line.split("|")[1:-1]]
        if len(cols) < 6:
            continue
        eng = cols[0]
        try:
            data[eng] = {
                "cold_start_s":    float(cols[1]) if cols[1] not in ("FAILED", "N/A") else None,
                "warm_inference_s": float(cols[4]) if cols[4] != "N/A" else None,
                "peak_rss_mb":      float(cols[5]) if cols[5] != "N/A" else None,
            }
        except Exception:
            pass
    return data


def load_phase4(path: Path) -> dict:
    """Parse retrieval_quality_validation.md → {engine: retrieval_success_rate}"""
    data = {eng: {"successes": 0, "total": 0} for eng in ENGINES}
    if not path.exists():
        return {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or line.startswith("| Engine") or line.startswith("| :"):
            continue
        cols = [c.strip() for c in line.split("|")[1:-1]]
        if len(cols) < 6:
            continue
        eng = cols[0]
        if eng not in data:
            continue
        data[eng]["total"] += 1
        if "✅" in cols[4]:  # Correct col
            data[eng]["successes"] += 1
    result = {}
    for eng, v in data.items():
        result[eng] = v["successes"] / v["total"] if v["total"] > 0 else 0.0
    return result


def load_phase5(path: Path) -> dict:
    """Parse recovery_rate_report.md → {engine: {avg_recovery, avg_wer, table_recovery}}"""
    # Two sections: recovery table and WER table; parse both
    data = {eng: {"recoveries": [], "wers": [], "table_recovery": None} for eng in ENGINES}
    if not path.exists():
        return {}
    section = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if "Recovery Rate by Engine" in line:
            section = "recovery"
        elif "WER / CER" in line:
            section = "wer"
        elif "Table Recovery" in line:
            section = "table"

        if not line.startswith("| ") or line.startswith("| Engine") or line.startswith("| :") or line.startswith("| >"):
            continue
        cols = [c.strip() for c in line.split("|")[1:-1]]
        if len(cols) < 2:
            continue

        eng = cols[0]
        if eng not in data:
            continue

        if section == "recovery" and len(cols) >= 4:
            try:
                pct = cols[3].replace("%", "").strip()
                data[eng]["recoveries"].append(float(pct) / 100.0)
            except Exception:
                pass
        elif section == "wer" and len(cols) >= 3:
            try:
                wer_val = cols[2]
                if wer_val != "N/A":
                    data[eng]["wers"].append(float(wer_val))
            except Exception:
                pass
        elif section == "table" and len(cols) >= 3:
            try:
                score_str = cols[2].replace("%", "").strip()
                if score_str != "N/A":
                    data[eng]["table_recovery"] = float(score_str) / 100.0
            except Exception:
                pass

    result = {}
    for eng, v in data.items():
        result[eng] = {
            "avg_recovery":   sum(v["recoveries"]) / len(v["recoveries"]) if v["recoveries"] else 0.0,
            "avg_wer":        sum(v["wers"]) / len(v["wers"]) if v["wers"] else None,
            "table_recovery": v["table_recovery"] if v["table_recovery"] is not None else 0.0,
        }
    return result


def compute_scores(p3: dict, p4: dict, p5: dict) -> dict:
    """Compute normalised [0,1] weighted composite score per engine."""

    # ── Gather raw metrics ────────────────────────────────────────────────────
    raw = {}
    for eng in ENGINES:
        e3 = p3.get(eng, {})
        e5 = p5.get(eng, {})
        raw[eng] = {
            "recovery_rate":    _safe(e5.get("avg_recovery")),
            "avg_wer":          e5.get("avg_wer"),          # may be None
            "retrieval_success": _safe(p4.get(eng)),
            "warm_s":           e3.get("warm_inference_s"),  # may be None
            "peak_rss_mb":      e3.get("peak_rss_mb"),       # may be None
            "table_recovery":   _safe(e5.get("table_recovery")),
        }

    # ── Normalise latency and memory ─────────────────────────────────────────
    warm_vals = [v["warm_s"] for v in raw.values() if v["warm_s"] is not None]
    mem_vals  = [v["peak_rss_mb"] for v in raw.values() if v["peak_rss_mb"] is not None]

    max_warm  = max(warm_vals) if warm_vals else 1.0
    max_mem   = max(mem_vals)  if mem_vals  else 1.0

    scores = {}
    for eng, m in raw.items():
        wer_inv = (1.0 - min(_safe(m["avg_wer"], 1.0), 1.0)) if m["avg_wer"] is not None else 0.0
        warm_inv = (1.0 - (m["warm_s"] / max_warm)) if m["warm_s"] is not None else 0.0
        mem_inv  = (1.0 - (m["peak_rss_mb"] / max_mem)) if m["peak_rss_mb"] is not None else 0.0

        composite = (
            m["recovery_rate"]     * WEIGHTS["recovery_rate"]     +
            wer_inv                * WEIGHTS["wer_inv"]           +
            m["retrieval_success"] * WEIGHTS["retrieval_success"] +
            warm_inv               * WEIGHTS["warm_latency_inv"]  +
            mem_inv                * WEIGHTS["peak_mem_inv"]       +
            m["table_recovery"]    * WEIGHTS["table_recovery"]
        )

        scores[eng] = {
            "composite":        round(composite, 4),
            "recovery_rate":    round(m["recovery_rate"], 4),
            "wer_inv":          round(wer_inv, 4),
            "retrieval_success": round(m["retrieval_success"], 4),
            "warm_latency_inv": round(warm_inv, 4),
            "peak_mem_inv":     round(mem_inv, 4),
            "table_recovery":   round(m["table_recovery"], 4),
            # Raw extras for table
            "avg_wer":          round(m["avg_wer"], 4) if m["avg_wer"] is not None else None,
            "warm_s":           m["warm_s"],
            "peak_rss_mb":      m["peak_rss_mb"],
        }
    return scores


def decide_option(scores: dict) -> tuple:
    """Choose Option A/B/C based on composite scores."""
    ranked = sorted(scores.items(), key=lambda x: x[1]["composite"], reverse=True)
    best_eng, best_sc = ranked[0]

    tesseract_sc = scores.get("Tesseract", {}).get("composite", 0.0)
    best_composite = best_sc["composite"]

    # All engines failed (all zeros)
    all_zero = all(v["composite"] == 0.0 for v in scores.values())
    if all_zero:
        return "BENCHMARK FAILURE", "ALL engines produced zero composite scores. Extraction validation failed. No recommendation can be made.", ranked

    # Tesseract is best or within 5% of best
    if best_eng == "Tesseract" or (tesseract_sc > 0 and best_composite - tesseract_sc < 0.05):
        option = "A"
        rationale = (
            f"Tesseract achieves a competitive composite score ({tesseract_sc:.4f}) "
            f"with near-zero cold-start latency. The marginal quality improvement offered by "
            f"deep-learning engines does not justify the >30s cold-start overhead and >1 GB RAM penalty."
        )
    elif best_sc["warm_s"] is not None and best_sc["warm_s"] > 30:
        # Best engine has high quality but unacceptable warm latency — Hybrid
        option = "C"
        rationale = (
            f"{best_eng} achieves the highest composite score ({best_composite:.4f}) "
            f"but has a warm inference latency of {best_sc['warm_s']}s, which is too high "
            f"for inline synchronous ingest workers. A Hybrid Architecture is recommended: "
            f"Tesseract for simple typed scans, {best_eng} as a background microservice for difficult documents."
        )
    else:
        # Best engine clearly wins and is acceptably fast — replace Tesseract
        option = "B"
        rationale = (
            f"{best_eng} achieves the highest composite score ({best_composite:.4f}) "
            f"vs Tesseract ({tesseract_sc:.4f}), with an acceptable warm inference latency "
            f"of {best_sc['warm_s']}s. Replacing Tesseract with {best_eng} is recommended."
        )

    return option, rationale, ranked


def generate_report(scores: dict, option: str, rationale: str, ranked: list) -> str:
    lines = [
        "# Phase 6 — Final OCR Architecture Recommendation",
        "",
        "## Weighted Score Matrix",
        "",
        "| Weight | Metric |",
        "| :--- | :--- |",
    ]
    for metric, w in WEIGHTS.items():
        lines.append(f"| {w:.0%} | {metric.replace('_', ' ').title()} |")

    lines += [
        "",
        "## Engine Composite Scores",
        "",
        "| Rank | Engine | Composite | Recovery | WER⁻¹ | Retrieval | Latency⁻¹ | Memory⁻¹ | Table |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for rank, (eng, sc) in enumerate(ranked, 1):
        lines.append(
            f"| {rank} | **{eng}** | **{sc['composite']:.4f}** | {sc['recovery_rate']:.2%} | "
            f"{sc['wer_inv']:.2%} | {sc['retrieval_success']:.2%} | "
            f"{sc['warm_latency_inv']:.2%} | {sc['peak_mem_inv']:.2%} | {sc['table_recovery']:.2%} |"
        )

    lines += [
        "",
        "## Raw Metrics Reference",
        "",
        "| Engine | Avg WER | Warm Infer (s) | Peak RSS (MB) |",
        "| :--- | :--- | :--- | :--- |",
    ]
    for eng, sc in scores.items():
        wer = f"{sc['avg_wer']:.4f}" if sc["avg_wer"] is not None else "N/A"
        warm = str(sc["warm_s"]) if sc["warm_s"] is not None else "N/A"
        mem  = str(sc["peak_rss_mb"]) if sc["peak_rss_mb"] is not None else "N/A"
        lines.append(f"| {eng} | {wer} | {warm} | {mem} |")

    if option == "BENCHMARK FAILURE":
        lines += [
            "",
            "---",
            "",
            "## ❌ BENCHMARK FAILURE",
            "",
            f"> {rationale}",
            "",
            "No architectural recommendation can be made. Resolve extraction pipeline failures first.",
        ]
    else:
        option_labels = {
            "A": "Option A — Continue with Tesseract",
            "B": "Option B — Replace Tesseract",
            "C": "Option C — Hybrid Architecture",
        }
        lines += [
            "",
            "---",
            "",
            f"## ✅ Recommendation: {option_labels[option]}",
            "",
            f"> {rationale}",
        ]

    return "\n".join(lines)


def main():
    print("=== Phase 6: Final Recommendation ===")
    base = Path(__file__).parent

    p3 = load_phase3(base / "warm_vs_cold_benchmark.md")
    p4 = load_phase4(base / "retrieval_quality_validation.md")
    p5 = load_phase5(base / "recovery_rate_report.md")

    scores = compute_scores(p3, p4, p5)
    option, rationale, ranked = decide_option(scores)

    print(f"\n  Composite scores:")
    for eng, sc in sorted(scores.items(), key=lambda x: x[1]["composite"], reverse=True):
        print(f"    {eng}: {sc['composite']:.4f}")
    print(f"\n  → {option}: {rationale[:80]}...")

    report = generate_report(scores, option, rationale, ranked)
    out = base / "final_ocr_architecture_recommendation.md"
    out.write_text(report, encoding="utf-8")
    print(f"\nReport written: {out}")


if __name__ == "__main__":
    main()
