import os
import time
import requests
import json
import logging
import uuid
import sys

# We will need to make sure FPDF is available for generation
try:
    from fpdf import FPDF
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "fpdf2"], check=True)
    from fpdf import FPDF

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
logger = logging.getLogger("validate_pdf_pipeline")

API_URL = "http://localhost:5000"
HEADERS = {"X-API-Key": "dev_secret_api_key"}

# ─────────────────────────────────────────────────────────────────────────────
# 1. GENERATE TEST PDFS FOR 5 CATEGORIES
# ─────────────────────────────────────────────────────────────────────────────
def generate_test_pdfs():
    os.makedirs("test_data", exist_ok=True)
    files = {}

    # Category A: Simple Text PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(w=190, h=10, text="ScaleFlow Category A Test Document", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(10)
    pdf.multi_cell(w=190, h=10, text="This is a simple text PDF designed to test basic parsing capabilities. It has no images, no complex layout, and should be parsed instantly by pypdf without falling back to pdfplumber or OCR.")
    pdf.multi_cell(w=190, h=10, text="The sky is blue and the grass is green. This is a factual statement for retrieval.")
    filepath_a = "test_data/category_A_simple.pdf"
    pdf.output(filepath_a)
    files["A"] = {"path": filepath_a, "desc": "Simple Text PDF"}

    # Category B: Academic (Simulated with columns/formatting)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Times", "B", 16)
    pdf.cell(w=190, h=10, text="Advanced Orchestration in Distributed Systems", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Times", "I", 12)
    pdf.cell(w=190, h=10, text="Jane Doe, John Smith", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(10)
    pdf.set_font("Times", "", 10)
    # Simulate equations and references
    pdf.multi_cell(w=190, h=6, text="Abstract: This paper explores the performance of distributed DAG execution in highly volatile environments. We present ScaleFlow, a novel orchestration engine.")
    pdf.ln(5)
    pdf.set_font("Courier", "", 10)
    pdf.cell(w=190, h=6, text="E = mc^2 + sum(x_i) / N", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.set_font("Times", "", 10)
    pdf.multi_cell(w=190, h=6, text="References:\n[1] Lamport, L. (1978). Time, clocks, and the ordering of events in a distributed system.")
    filepath_b = "test_data/category_B_academic.pdf"
    pdf.output(filepath_b)
    files["B"] = {"path": filepath_b, "desc": "Academic PDF (equations/references)"}

    # Category C: Large PDF (Simulated 50 pages for speed, but repeated content)
    pdf = FPDF()
    pdf.set_font("Helvetica", size=10)
    for i in range(50):
        pdf.add_page()
        pdf.cell(w=190, h=10, text=f"Page {i+1} of Large Document", new_x="LMARGIN", new_y="NEXT", align="C")
        for _ in range(30):
            pdf.multi_cell(w=190, h=6, text="This is a repeated paragraph to simulate a large document and test chunking caps, memory limits, and timeouts. ScaleFlow must gracefully handle this volume. " * 3)
    filepath_c = "test_data/category_C_large.pdf"
    pdf.output(filepath_c)
    files["C"] = {"path": filepath_c, "desc": "Large PDF (50+ pages)"}

    # Category D: Scanned/Image PDF (Simulated by rendering text to an image, then making PDF from image)
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGB', (800, 1000), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((50, 50), "This is an image-based PDF.", fill=(0, 0, 0))
        d.text((50, 100), "pypdf and pdfplumber will fail to extract this text.", fill=(0, 0, 0))
        d.text((50, 150), "It should trigger the OCR fallback.", fill=(0, 0, 0))
        img_path = "test_data/temp_scanned.jpg"
        img.save(img_path)
        
        pdf = FPDF()
        pdf.add_page()
        pdf.image(img_path, x=0, y=0, w=210)
        filepath_d = "test_data/category_D_scanned.pdf"
        pdf.output(filepath_d)
        files["D"] = {"path": filepath_d, "desc": "Scanned/Image PDF"}
    except Exception as e:
        logger.warning(f"Failed to generate Category D (requires Pillow). Using a fallback low-text PDF. Error: {e}")
        pdf = FPDF()
        pdf.add_page()
        # Basically empty to trigger OCR/pdfplumber fallback
        pdf.set_font("Helvetica", size=8)
        pdf.text(10, 10, text="Too short")
        filepath_d = "test_data/category_D_scanned.pdf"
        pdf.output(filepath_d)
        files["D"] = {"path": filepath_d, "desc": "Scanned/Image PDF (fallback generated)"}

    # Category E: Malformed PDF (Corrupted)
    filepath_e = "test_data/category_E_malformed.pdf"
    with open(filepath_e, "wb") as f:
        f.write(b"%PDF-1.4\n%This is a deliberately broken PDF file\n<</Type/Catalog/Pages 1 0 R>>\nEOF")
    files["E"] = {"path": filepath_e, "desc": "Malformed/Corrupted PDF"}

    return files

# ─────────────────────────────────────────────────────────────────────────────
# 2. PIPELINE EXECUTION AND POLLING
# ─────────────────────────────────────────────────────────────────────────────
def upload_and_run(filepath):
    logger.info(f"Uploading file: {filepath}")
    with open(filepath, 'rb') as f:
        files = {'file': (os.path.basename(filepath), f, 'application/pdf')}
        data = {'pipeline_type': 'document_processing_demo'}
        res = requests.post(f"{API_URL}/files/upload", files=files, data=data, headers={"X-API-Key": HEADERS["X-API-Key"]})
    
    if res.status_code not in (200, 201):
        raise RuntimeError(f"Upload failed: {res.text}")
        
    pipeline_id = res.json().get('pipeline_id')
    logger.info(f"Pipeline started: {pipeline_id}")
    return pipeline_id

def wait_for_pipeline(pipeline_id, timeout=300):
    start = time.time()
    while time.time() - start < timeout:
        res = requests.get(f"{API_URL}/pipelines/{pipeline_id}", headers=HEADERS)
        if res.status_code == 200:
            data = res.json()
            status = data.get('pipeline', {}).get('status')
            if status in ('completed', 'failed', 'cancelled'):
                return data
        time.sleep(2)
    raise TimeoutError("Pipeline polling timed out")

def test_retrieval(pipeline_id, queries):
    results = {}
    for q in queries:
        payload = {
            "name": f"Retrieval: {q[:30]}",
            "pipeline_type": "retrieval_answer_demo",
            "initial_payload": {
                "query": q,
                "target_pipeline_id": pipeline_id
            }
        }
        res = requests.post(f"{API_URL}/pipelines", json=payload, headers=HEADERS)
        if res.status_code == 201:
            q_pid = res.json().get('pipeline_id')
            data = wait_for_pipeline(q_pid)
            if data.get('pipeline', {}).get('status') == 'completed':
                for art in data.get('artifacts', []):
                    if art.get('artifact_type') == 'final_answer':
                        answer_data = art.get('metadata_json', {})
                        if isinstance(answer_data, str):
                            answer_data = json.loads(answer_data)
                        results[q] = answer_data.get('answer', str(answer_data))
                        break
    return results

# ─────────────────────────────────────────────────────────────────────────────
# 3. MAIN VALIDATION SCRIPT
# ─────────────────────────────────────────────────────────────────────────────
def main():
    logger.info("Generating test PDFs for all categories...")
    test_files = generate_test_pdfs()
    
    report_lines = []
    report_lines.append("# Document Intelligence Hardening — Validation Report")
    report_lines.append(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("\n## Summary")
    report_lines.append("| Category | File | Parse Status | Parser Used | Duration | Chunks |")
    report_lines.append("|---|---|---|---|---|---|")
    
    details = []

    for cat, info in test_files.items():
        logger.info(f"\n===========================================")
        logger.info(f"Testing Category {cat}: {info['desc']}")
        logger.info(f"===========================================")
        
        start_t = time.time()
        status = "Unknown"
        parser_used = "N/A"
        chunks = 0
        dur_s = 0
        error_reason = ""
        
        try:
            pid = upload_and_run(info['path'])
            data = wait_for_pipeline(pid, timeout=600)
            status = data.get('pipeline', {}).get('status')
            dur_s = round(time.time() - start_t, 2)
            
            if status == "completed":
                # Extract stats from artifacts
                for art in data.get('artifacts', []):
                    if art.get('artifact_type') == 'parsed_text':
                        meta = art.get('metadata_json')
                        if isinstance(meta, str):
                            meta = json.loads(meta)
                        if meta and 'parse_stats' in meta:
                            parser_used = meta['parse_stats'].get('parser', 'unknown')
                    elif art.get('artifact_type') == 'vector_index':
                        meta = art.get('metadata_json')
                        if isinstance(meta, str):
                            meta = json.loads(meta)
                        if meta:
                            chunks = meta.get('vector_count', 0)
                            
                details.append(f"\n### Category {cat}: {info['desc']}")
                details.append(f"- **Status**: SUCCESS")
                details.append(f"- **Parser Used**: {parser_used}")
                details.append(f"- **Chunks Generated**: {chunks}")
                details.append(f"- **Duration**: {dur_s}s")
                
                # Test Retrieval for Category A
                if cat == "A":
                    queries = ["What color is the sky?", "What is this document designed to test?"]
                    ans = test_retrieval(pid, queries)
                    details.append("\n**Retrieval Tests:**")
                    for q, a in ans.items():
                        details.append(f"- *Q: {q}*\n  - *A: {a}*")
                        
            else:
                # Failed (expected for E)
                failed_tasks = [t for t in data.get('tasks', []) if t.get('status') == 'failed']
                if failed_tasks:
                    error_reason = failed_tasks[0].get('error_message', 'Unknown Error')
                else:
                    error_reason = "Pipeline failed without task error."
                    
                details.append(f"\n### Category {cat}: {info['desc']}")
                details.append(f"- **Status**: FAILED (Expected for malformed)")
                details.append(f"- **Error**: {error_reason}")
                
        except Exception as e:
            logger.error(f"Test failed: {e}")
            status = "Error"
            error_reason = str(e)
            details.append(f"\n### Category {cat}: {info['desc']}")
            details.append(f"- **Status**: ERROR")
            details.append(f"- **Exception**: {e}")
            
        report_lines.append(f"| {cat} | {os.path.basename(info['path'])} | {status} | {parser_used} | {dur_s}s | {chunks} |")

    with open("pdf_validation_report.md", "w") as f:
        f.write("\n".join(report_lines))
        f.write("\n")
        f.write("\n".join(details))
        
    logger.info("Validation complete! See pdf_validation_report.md")

if __name__ == "__main__":
    main()
