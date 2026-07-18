#!/usr/bin/env python3
import os
import sys
import argparse
import json
import hashlib
from datetime import datetime

DEFAULT_FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fixtures"))
DEFAULT_OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "expected"))
DEFAULT_MANIFEST_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "golden", "manifest.json"))

def normalize_data(val):
    if isinstance(val, dict):
        res = {}
        for k in val.keys():
            if k == "document_id":
                res[k] = "constant_doc_id"
            else:
                res[k] = normalize_data(val[k])
        return {k: res[k] for k in sorted(res.keys())}
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

def compute_sha256(content_bytes):
    return hashlib.sha256(content_bytes).hexdigest()

def main():
    parser = argparse.ArgumentParser(description="Generate SHA256 hashes for expected artifacts")
    parser.add_argument("--fixtures", default=DEFAULT_FIXTURES_DIR, help="Path to fixtures folder")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="Path to expected outputs folder")
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST_PATH, help="Path to manifest.json output")
    parser.add_argument("--only", help="Only process matching document names (comma separated)")
    parser.add_argument("--skip", help="Skip matching document names (comma separated)")
    parser.add_argument("--force", action="store_true", help="Force hashing even if no changes")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker threads (unused/placeholder for CLI interface)")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()

    if not os.path.exists(args.output):
        print(f"[ERROR] Expected outputs directory not found: {args.output}")
        sys.exit(1)

    only_filter = [x.strip() for x in args.only.split(",")] if args.only else []
    skip_filter = [x.strip() for x in args.skip.split(",")] if args.skip else []

    # Get all document subdirectories in expected outputs
    doc_dirs = []
    for entry in os.scandir(args.output):
        if entry.is_dir():
            name = entry.name
            if only_filter and not any(o in name for o in only_filter):
                continue
            if skip_filter and any(s in name for s in skip_filter):
                continue
            doc_dirs.append(entry)

    # Load existing manifest if present and force is not set
    manifest_data = {}
    if os.path.exists(args.manifest):
        try:
            with open(args.manifest, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
        except Exception as e:
            print(f"[WARNING] Failed to load existing manifest.json: {e}")

    # Prepare document hashes
    hashes = manifest_data.get("hashes", {})
    
    expected_files = [
        "parser_output.json",
        "document_graph.json",
        "chunks.json",
        "metadata.json",
        "retrieval_queries.json",
        "retrieval_results.json"
    ]

    for d in doc_dirs:
        doc_name = d.name
        if args.verbose:
            print(f"Hashing artifacts for {doc_name}...")
        
        doc_hashes = {}
        missing_any = False
        for f_name in expected_files:
            f_path = os.path.join(d.path, f_name)
            if not os.path.exists(f_path):
                print(f"[WARNING] Missing expected artifact: {f_path}")
                missing_any = True
                continue
            
            try:
                # Read, normalize, and sort keys to guarantee absolute determinism before hashing
                with open(f_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                normalized = normalize_data(data)
                serialized = json.dumps(normalized, sort_keys=True, ensure_ascii=False).encode('utf-8')
                
                # Write back normalized file to guarantee clean git diffs and deterministic comparison
                with open(f_path, "w", encoding="utf-8") as f_out:
                    json.dump(normalized, f_out, indent=2, sort_keys=True)
                
                doc_hashes[f_name] = compute_sha256(serialized)
            except Exception as e:
                print(f"[ERROR] Failed to hash {f_path}: {e}")
                missing_any = True

        if not missing_any or args.force:
            hashes[doc_name] = doc_hashes

    # Output manifest
    new_manifest = {
        "dataset_version": "1.1",
        "pipeline_version": "1.1",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "hashes": hashes
    }

    os.makedirs(os.path.dirname(args.manifest), exist_ok=True)
    with open(args.manifest, "w", encoding="utf-8") as f:
        json.dump(new_manifest, f, indent=2, sort_keys=True)

    print(f"[SUCCESS] Hashed {len(doc_dirs)} documents. Manifest updated at {args.manifest}")

if __name__ == "__main__":
    main()
