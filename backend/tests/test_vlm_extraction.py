import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.pdf_parser import parse_pdf

def trace(msg):
    print(f"[TRACE] {msg}")

filepath = r"d:\Projects\task-schedular\backend\storage\uploads\176_PBL_Patent.pdf"
print(f"Filepath exists: {os.path.exists(filepath)}")

try:
    res = parse_pdf(filepath, task_id="test_run", trace_fn=trace)
    print("VLM Success:", res.stats.get("vlm_pages", 0) > 0)
    print("Stats:", res.stats)
    if res.document_graph.get("pages"):
        page = res.document_graph["pages"][0]
        nodes = page.get("nodes", [])
        print(f"Page 1 nodes count: {len(nodes)}")
        if nodes:
            print("First node chunk_id:", nodes[0]["chunk_id"])
            print("First node text:", nodes[0]["text"][:200])
except Exception as e:
    import traceback
    print(f"Exception: {type(e).__name__}: {e}")
    traceback.print_exc()
