"""
Phase 3 — Warm vs Cold Start + Peak Memory Benchmark
Measures per-engine:
  - Cold Start: time to import + model instantiation from disk cache
  - First Inference: latency on first document (Category B)
  - Warm Inference: latency on second document (Category C, model already loaded)
  - Peak RSS: max RSS during session, polled at 0.1s intervals in a side thread
Writes warm_vs_cold_benchmark.md.
"""

import os, sys, time, threading
from pathlib import Path
import psutil

REPO_ROOT    = Path(__file__).resolve().parent.parent
RENDERED_DIR = Path(__file__).parent / "rendered"
PROCESS      = psutil.Process(os.getpid())


def _peak_rss_poller(stop_event: threading.Event, samples: list):
    """Background thread: records RSS (bytes) every 0.1 s until stop_event set."""
    while not stop_event.is_set():
        samples.append(PROCESS.memory_info().rss)
        time.sleep(0.1)


def measure_engine(engine_name: str, img_b: str, img_c: str) -> dict:
    result = {
        "engine": engine_name,
        "cold_start_s": None,
        "init_memory_delta_mb": None,
        "first_inference_s": None,
        "warm_inference_s": None,
        "peak_rss_mb": None,
        "init_error": None,
    }

    sys.path.insert(0, str(Path(__file__).parent))
    from benchmark_wrappers import (
        TesseractWrapper, PaddleWrapper, EasyOCRWrapper, DocTRWrapper, SuryaWrapper
    )
    mapping = {
        "Tesseract": TesseractWrapper,
        "PaddleOCR": PaddleWrapper,
        "EasyOCR":   EasyOCRWrapper,
        "DocTR":     DocTRWrapper,
        "Surya":     SuryaWrapper,
    }

    # ── Start RSS poller ──────────────────────────────────────────────────────
    rss_samples = [PROCESS.memory_info().rss]
    stop_event  = threading.Event()
    poller      = threading.Thread(target=_peak_rss_poller, args=(stop_event, rss_samples), daemon=True)
    poller.start()

    mem_before = PROCESS.memory_info().rss

    # ── Cold Start ────────────────────────────────────────────────────────────
    try:
        t0 = time.perf_counter()
        wrapper = mapping[engine_name]()
        cold_s  = time.perf_counter() - t0
        mem_after = PROCESS.memory_info().rss

        result["cold_start_s"]        = round(cold_s, 3)
        result["init_memory_delta_mb"] = round((mem_after - mem_before) / 1024 / 1024, 1)
    except Exception as e:
        result["init_error"] = str(e)
        stop_event.set()
        return result

    # ── First Inference (Warm-up) ─────────────────────────────────────────────
    if img_b:
        try:
            t0 = time.perf_counter()
            wrapper.extract_text(img_b)
            result["first_inference_s"] = round(time.perf_counter() - t0, 3)
        except Exception as e:
            result["first_inference_error"] = str(e)

    # ── Warm Inference ────────────────────────────────────────────────────────
    if img_c:
        try:
            t0 = time.perf_counter()
            wrapper.extract_text(img_c)
            result["warm_inference_s"] = round(time.perf_counter() - t0, 3)
        except Exception as e:
            result["warm_inference_error"] = str(e)

    # ── Stop poller & compute peak ────────────────────────────────────────────
    stop_event.set()
    result["peak_rss_mb"] = round(max(rss_samples) / 1024 / 1024, 1)

    return result


def generate_report(results: list) -> str:
    lines = [
        "# Phase 3 — Warm vs Cold Start + Peak Memory Benchmark",
        "",
        "> **Cold Start** = time to load model weights from local disk cache into RAM.",
        "> **First Inference** = extraction on the first document (model warm-up).",
        "> **Warm Inference** = extraction on the second document (model already resident).",
        "> **Peak RSS** = maximum resident memory observed during the full session.",
        "",
        "| Engine | Cold Start (s) | Init ΔMem (MB) | First Inference (s) | Warm Inference (s) | Peak RSS (MB) |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for r in results:
        eng   = r["engine"]
        cold  = str(r["cold_start_s"]) if r["cold_start_s"] is not None else "FAILED"
        dmem  = str(r["init_memory_delta_mb"]) if r["init_memory_delta_mb"] is not None else "N/A"
        first = str(r["first_inference_s"]) if r["first_inference_s"] is not None else "N/A"
        warm  = str(r["warm_inference_s"]) if r["warm_inference_s"] is not None else "N/A"
        peak  = str(r["peak_rss_mb"]) if r["peak_rss_mb"] is not None else "N/A"
        lines.append(f"| {eng} | {cold} | {dmem} | {first} | {warm} | {peak} |")

    lines += [
        "",
        "## Analysis",
        "",
        "Warm inference latency is the production-relevant metric for a pre-loaded microservice.",
        "Cold start latency is the production-relevant metric for ephemeral/autoscaled worker nodes.",
        "",
        "Engines with Cold Start > 30s cannot be embedded in on-demand ingest workers without",
        "degrading ingestion SLA. They require persistent pre-loaded service deployment.",
    ]
    return "\n".join(lines)


def main():
    print("=== Phase 3: Warm vs Cold Start + Peak Memory ===")
    engines = ["Tesseract", "PaddleOCR", "EasyOCR", "DocTR", "Surya"]

    img_b = str(RENDERED_DIR / "cat_B.png") if (RENDERED_DIR / "cat_B.png").exists() else None
    img_c = str(RENDERED_DIR / "cat_C.png") if (RENDERED_DIR / "cat_C.png").exists() else None

    results = []
    for eng in engines:
        print(f"\n  Testing {eng}...")
        r = measure_engine(eng, img_b, img_c)
        results.append(r)
        if r["init_error"]:
            print(f"    ❌ Init failed: {r['init_error']}")
        else:
            print(f"    Cold: {r['cold_start_s']}s | First: {r['first_inference_s']}s | Warm: {r['warm_inference_s']}s | Peak RSS: {r['peak_rss_mb']} MB")

    report = generate_report(results)
    out = Path(__file__).parent / "warm_vs_cold_benchmark.md"
    out.write_text(report, encoding="utf-8")
    print(f"\nReport written: {out}")
    return results


if __name__ == "__main__":
    main()
