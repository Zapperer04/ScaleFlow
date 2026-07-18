#!/usr/bin/env python3
import os
import sys
import argparse
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor

# Default config
DEFAULT_API_URL = "http://localhost:5000"
DEFAULT_FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fixtures"))
DEFAULT_OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "expected"))

DEFAULT_QUERIES = [
    "What skills does the candidate have?",
    "What internships has the candidate completed?",
    "What projects are listed?"
]

def get_headers():
    # Attempt to load api key from backend/.env or environment
    api_key = os.environ.get("API_KEY")
    if not api_key:
        env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env"))
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if line.startswith("API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break
    if not api_key:
        api_key = "local_only_secret_key"
    return {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }

def normalize_data(val):
    if isinstance(val, dict):
        return {k: normalize_data(val[k]) for k in sorted(val.keys())}
    elif isinstance(val, list):
        normalized_list = [normalize_data(x) for x in val]
        try:
            def sort_key(item):
                if isinstance(item, dict):
                    for k in ['chunk_id', 'chunk_index', 'id', 'node_id', 'name', 'page_number', 'page']:
                        if k in item and item[k] is not None:
                            return (0, str(item[k]))
                    return (1, str(sorted(item.items())))
                return (2, str(item))
            normalized_list.sort(key=sort_key)
        except Exception:
            pass
        return normalized_list
    elif isinstance(val, float):
        return round(val, 4)
    else:
        return val

def process_file(file_path, output_dir, api_url, force, verbose):
    relative_path = os.path.relpath(file_path, start=DEFAULT_FIXTURES_DIR)
    doc_name = os.path.splitext(relative_path)[0].replace(os.sep, "_")
    target_dir = os.path.join(output_dir, doc_name)

    # Check if exists and force is not set
    expected_files = [
        "parser_output.json",
        "document_graph.json",
        "chunks.json",
        "metadata.json",
        "retrieval_queries.json",
        "retrieval_results.json"
    ]
    if not force and os.path.exists(target_dir):
        all_exist = all(os.path.exists(os.path.join(target_dir, f)) for f in expected_files)
        if all_exist:
            if verbose:
                print(f"[SKIP] Outputs already exist for {relative_path} in {target_dir}")
            return True

    print(f"[PROCESS] Processing {relative_path} ...")
    headers = get_headers()
    
    # 1. Upload file
    upload_url = f"{api_url}/files/upload"
    if verbose:
        print(f"Uploading file to {upload_url}...")
    try:
        with open(file_path, "rb") as f:
            r = requests.post(upload_url, files={"file": f}, headers={"X-API-Key": headers["X-API-Key"]})
    except Exception as e:
        print(f"[ERROR] Connection to API failed: {e}")
        return False

    if r.status_code not in (200, 201):
        print(f"[ERROR] Upload failed for {relative_path}: HTTP {r.status_code} - {r.text}")
        return False

    pipeline_id = r.json().get("pipeline_id")
    if not pipeline_id:
        print(f"[ERROR] No pipeline ID returned for {relative_path}: {r.json()}")
        return False

    if verbose:
        print(f"Pipeline #{pipeline_id} created. Polling status...")

    # 2. Poll for completion
    pipeline_url = f"{api_url}/pipelines/{pipeline_id}"
    completed = False
    for attempt in range(120):
        time.sleep(2)
        try:
            r_status = requests.get(pipeline_url, headers=headers)
            if r_status.status_code == 200:
                data = r_status.json()
                status = data.get("pipeline", {}).get("status") or data.get("status")
                if status == "completed":
                    completed = True
                    break
                elif status == "failed":
                    print(f"[ERROR] Pipeline #{pipeline_id} failed: {data}")
                    return False
        except Exception as e:
            if verbose:
                print(f"Polling warning: {e}")

    if not completed:
        print(f"[ERROR] Pipeline #{pipeline_id} timed out for {relative_path}")
        return False

    if verbose:
        print(f"Pipeline #{pipeline_id} completed. Downloading artifacts...")

    # 3. Retrieve artifacts
    try:
        r_pipeline = requests.get(pipeline_url, headers=headers)
        pipeline_data = r_pipeline.json()
    except Exception as e:
        print(f"[ERROR] Failed to fetch pipeline details: {e}")
        return False

    artifacts = pipeline_data.get("artifacts", [])
    
    parser_output = {}
    document_graph = {}
    chunks = []
    metadata = {}

    for art in artifacts:
        art_id = art.get("id")
        art_type = art.get("artifact_type")
        if verbose:
            print(f"Found artifact type: {art_type}")
        try:
            r_content = requests.get(f"{api_url}/artifacts/{art_id}/content", headers=headers)
            if r_content.status_code == 200:
                content = r_content.json().get("content")
                if art_type in ("parsed_text", "preprocessing_report"):
                    parser_output = content
                elif art_type == "document_graph":
                    document_graph = content
                elif art_type in ("graph_chunks", "text_chunks"):
                    chunks = content
        except Exception as e:
            print(f"[WARNING] Failed to load content for artifact #{art_id}: {e}")

    # Fallbacks
    if not parser_output and document_graph:
        parser_output = document_graph
    if not document_graph and parser_output:
        document_graph = parser_output

    # Fetch metadata
    try:
        r_meta = requests.get(f"{api_url}/pipelines/{pipeline_id}/metadata", headers=headers)
        if r_meta.status_code == 200:
            metadata = r_meta.json()
    except Exception as e:
        if verbose:
            print(f"Metadata endpoint warning: {e}")

    # 4. Retrieval queries & results
    retrieval_results = []
    for q in DEFAULT_QUERIES:
        if verbose:
            print(f"Running retrieval query: '{q}'")
        try:
            r_query = requests.post(f"{api_url}/query-pipelines", json={
                "query": q,
                "top_k": 5,
                "pipeline_id_filter": pipeline_id
            }, headers=headers)
            if r_query.status_code == 201:
                qid = r_query.json().get("pipeline_id")
                # Poll answer
                query_completed = False
                for qa_attempt in range(40):
                    time.sleep(1.5)
                    r_ans = requests.get(f"{api_url}/query-pipelines/{qid}/answer", headers=headers)
                    if r_ans.status_code == 200:
                        ans_data = r_ans.json()
                        if ans_data.get("status") == "completed":
                            retrieval_results.append({
                                "query": q,
                                "answer": ans_data.get("answer") or ans_data.get("final_answer", {}).get("answer"),
                                "sources": ans_data.get("sources"),
                                "retrieved_context": ans_data.get("retrieved_context")
                            })
                            query_completed = True
                            break
                        elif ans_data.get("status") == "failed":
                            break
                if not query_completed:
                    retrieval_results.append({"query": q, "error": "Query pipeline timed out or failed"})
            else:
                retrieval_results.append({"query": q, "error": f"Failed to submit: HTTP {r_query.status_code}"})
        except Exception as e:
            retrieval_results.append({"query": q, "error": f"Exception: {e}"})

    # Save to disk with deterministic normalization
    os.makedirs(target_dir, exist_ok=True)
    
    outputs_map = {
        "parser_output.json": parser_output,
        "document_graph.json": document_graph,
        "chunks.json": chunks,
        "metadata.json": metadata,
        "retrieval_queries.json": DEFAULT_QUERIES,
        "retrieval_results.json": retrieval_results
    }

    for name, content in outputs_map.items():
        norm_content = normalize_data(content)
        file_out = os.path.join(target_dir, name)
        with open(file_out, "w", encoding="utf-8") as out_f:
            json.dump(norm_content, out_f, indent=2, sort_keys=True)

    print(f"[SUCCESS] Saved outputs for {relative_path} in {target_dir}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Generate Golden Dataset Baseline")
    parser.add_argument("--fixtures", default=DEFAULT_FIXTURES_DIR, help="Path to fixtures folder")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="Path to output expected folder")
    parser.add_argument("--only", help="Only process matching document/fixture names (comma separated)")
    parser.add_argument("--skip", help="Skip matching document/fixture names (comma separated)")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing baseline files")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker threads")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="Base API URL of the running task scheduler")

    args = parser.parse_args()

    if not os.path.exists(args.fixtures):
        print(f"[ERROR] Fixtures directory not found: {args.fixtures}")
        sys.exit(1)

    fixtures_files = []
    for root, _, files in os.walk(args.fixtures):
        for f in files:
            if f.lower().endswith(('.pdf', '.txt', '.png', '.jpg', '.jpeg', '.docx')):
                fixtures_files.append(os.path.join(root, f))

    only_filter = [x.strip() for x in args.only.split(",")] if args.only else []
    skip_filter = [x.strip() for x in args.skip.split(",")] if args.skip else []

    filtered_files = []
    for f in fixtures_files:
        name = os.path.basename(f)
        if only_filter and not any(o in name or o in f for o in only_filter):
            continue
        if skip_filter and any(s in name or s in f for s in skip_filter):
            continue
        filtered_files.append(f)

    if not filtered_files:
        print("No fixture files found matching criteria.")
        return

    print(f"Starting Golden Dataset generation for {len(filtered_files)} fixtures...")

    if args.workers > 1:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(process_file, f, args.output, args.api_url, args.force, args.verbose) for f in filtered_files]
            results = [fut.result() for fut in futures]
    else:
        results = [process_file(f, args.output, args.api_url, args.force, args.verbose) for f in filtered_files]

    success_count = sum(1 for r in results if r)
    print(f"Completed dataset generation. {success_count}/{len(filtered_files)} succeeded.")

if __name__ == "__main__":
    main()
