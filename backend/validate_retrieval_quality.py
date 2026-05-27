import os
import sys
import time
import requests
import json
from datetime import datetime

API_URL = "http://localhost:5000"
# Ensure the uploads directory exists
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Generate a complex text document for testing Retrieval Quality
TEST_DOC_CONTENT = """
=========================================
Project TITAN - Internal Technical Specification
=========================================
Date: October 2024
Author: System Architecture Team

1. Introduction
Project TITAN is a distributed AI orchestration engine designed to process up to 100,000 documents per day. 
The core philosophy of TITAN relies on deterministic worker allocation and robust fallback mechanisms to ensure 99.9% uptime.

2. Component Architecture
The system consists of three main modules:
- API Gateway (Port 5000): Handles incoming requests and orchestrates DAG generation.
- Redis Message Broker: Acts as the state-locking and queuing mechanism for the distributed workers.
- Qdrant Vector Store: Stores the semantic embeddings for the RAG pipeline. It utilizes an HNSW index for fast nearest-neighbor searches.

3. Failure Modes & Recovery
If a worker crashes during chunking, the orchestrator detects the heartbeat timeout after 15 seconds. 
The task is then automatically re-queued and a different worker claims it. This guarantees zero orphaned tasks.
In the event of a parser failure (e.g., pypdf fails on a corrupted page), the system falls back to pdfplumber, and ultimately to Tesseract OCR.

4. Infrastructure Costs
The current monthly budget for Project TITAN is $4,500. This includes $2,000 for GPU compute instances (for embeddings), $1,500 for the Qdrant managed cluster, and $1,000 for standard application servers.
"""

TEST_DOC_PATH = os.path.join(UPLOAD_DIR, "titan_spec_retrieval_test.txt")

def print_header(title):
    print(f"\n{'='*60}")
    print(f"{title.center(60)}")
    print(f"{'='*60}")

def wait_for_pipeline(pipeline_id, timeout=120):
    start = time.time()
    while time.time() - start < timeout:
        res = requests.get(f"{API_URL}/pipelines/{pipeline_id}")
        if res.status_code == 200:
            status = res.json().get("pipeline", {}).get("status")
            if status == "completed":
                return True
            if status == "failed":
                return False
        time.sleep(2)
    return False

def evaluate_retrieval():
    print_header("RETRIEVAL QUALITY VALIDATION SUITE")

    # 1. Setup Test Document
    with open(TEST_DOC_PATH, "w", encoding="utf-8") as f:
        f.write(TEST_DOC_CONTENT)
    print(f"[SETUP] Created test document: {TEST_DOC_PATH}")

    # 2. Upload Document
    print("[UPLOAD] Submitting document to ingestion pipeline...")
    with open(TEST_DOC_PATH, "rb") as f:
        files = {"file": f}
        data = {"pipeline_type": "document_processing_demo"}
        res = requests.post(f"{API_URL}/files/upload", files=files, data=data)
        
    if res.status_code != 200:
        print(f"[ERROR] Upload failed: {res.text}")
        sys.exit(1)
        
    pipeline_id = res.json().get("pipeline_id")
    print(f"[UPLOAD] Success. Pipeline ID: {pipeline_id}")

    # 3. Wait for Ingestion
    print(f"[WAIT] Waiting for Pipeline #{pipeline_id} to complete indexing...")
    if not wait_for_pipeline(pipeline_id):
        print("[ERROR] Pipeline failed or timed out.")
        sys.exit(1)
    
    print("[WAIT] Indexing complete! Initiating queries...")
    time.sleep(2) # brief buffer for Qdrant sync

    # 4. Evaluation Queries
    queries = [
        {
            "type": "Factual",
            "query": "What is the monthly budget for Project TITAN?",
            "expected_keywords": ["$4,500", "budget"]
        },
        {
            "type": "Semantic",
            "query": "How does the system handle a situation where a worker node crashes unexpectedly?",
            "expected_keywords": ["heartbeat timeout", "re-queued", "15 seconds"]
        },
        {
            "type": "Contextual",
            "query": "Which vector database is used and what indexing algorithm does it rely on?",
            "expected_keywords": ["Qdrant", "HNSW"]
        }
    ]

    report_lines = [
        "# Retrieval Quality Evaluation Report",
        f"**Date:** {datetime.utcnow().isoformat()}Z",
        f"**Pipeline ID:** {pipeline_id}",
        "---"
    ]

    success_count = 0

    for q in queries:
        print(f"\n[QUERY] Type: {q['type']}")
        print(f"        Q: {q['query']}")
        
        payload = {
            "query": q["query"],
            "pipeline_id": pipeline_id
        }
        
        res = requests.post(f"{API_URL}/pipelines/retrieval", json=payload)
        if res.status_code != 200:
            print(f"[ERROR] Query failed: {res.text}")
            continue
            
        retrieval_pipeline_id = res.json().get("pipeline_id")
        
        # Poll for answer
        answer_data = None
        for _ in range(15):
            time.sleep(1)
            ans_res = requests.get(f"{API_URL}/pipelines/{retrieval_pipeline_id}/answer")
            if ans_res.status_code == 200:
                data = ans_res.json()
                if "final_answer" in data:
                    answer_data = data["final_answer"]
                    break
        
        if not answer_data:
            print("[ERROR] Failed to synthesize answer.")
            continue
            
        answer_text = answer_data.get("answer", "")
        confidence = answer_data.get("confidence", "low")
        chunks = answer_data.get("retrieved_context", {}).get("results", [])
        
        print(f"        A: {answer_text}")
        print(f"        Confidence: {confidence.upper()} | Chunks used: {len(chunks)}")
        
        # Validate expectations
        matched = all(k.lower() in answer_text.lower() for k in q["expected_keywords"])
        status = "PASSED" if matched else "FAILED"
        if matched:
            success_count += 1
            
        report_lines.append(f"### Query Type: {q['type']}")
        report_lines.append(f"**Question:** {q['query']}")
        report_lines.append(f"**Expected Keywords:** {', '.join(q['expected_keywords'])}")
        report_lines.append(f"**Result Status:** {status}")
        report_lines.append(f"**Confidence:** {confidence}")
        report_lines.append(f"**Synthesized Answer:**\n> {answer_text}\n")
        report_lines.append("**Top Retrieved Chunk:**")
        if chunks:
            report_lines.append(f"> {chunks[0]['chunk_text']} (Score: {chunks[0].get('score', 0):.2f})\n")
        report_lines.append("---\n")

    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "retrieval_quality_report.md")
    with open(report_path, "w") as f:
        f.write("\n".join(report_lines))
        
    print_header("EVALUATION COMPLETE")
    print(f"Score: {success_count}/{len(queries)} passed.")
    print(f"Report saved to: {report_path}")

if __name__ == "__main__":
    evaluate_retrieval()
