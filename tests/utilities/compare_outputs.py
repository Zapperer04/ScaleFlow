#!/usr/bin/env python3
import os
import sys
import argparse
import json
import hashlib
import difflib

DEFAULT_FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fixtures"))
DEFAULT_OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "expected"))
DEFAULT_MANIFEST_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "golden", "manifest.json"))
DEFAULT_REPORT_PATH = "comparison_report.md"

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
    parser = argparse.ArgumentParser(description="Compare Current Outputs against Golden Baseline")
    parser.add_argument("--fixtures", default=DEFAULT_FIXTURES_DIR, help="Path to fixtures folder")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="Path to expected outputs folder")
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST_PATH, help="Path to manifest.json file")
    parser.add_argument("--report", default=DEFAULT_REPORT_PATH, help="Path to write comparison_report.md")
    parser.add_argument("--only", help="Only compare matching document names (comma separated)")
    parser.add_argument("--skip", help="Skip matching document names (comma separated)")
    parser.add_argument("--force", action="store_true", help="Force comparison (unused/CLI matching)")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker threads (unused/CLI matching)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if not os.path.exists(args.manifest):
        print(f"[ERROR] Golden manifest file not found: {args.manifest}")
        sys.exit(1)

    try:
        with open(args.manifest, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load manifest: {e}")
        sys.exit(1)

    golden_hashes = manifest.get("hashes", {})

    only_filter = [x.strip() for x in args.only.split(",")] if args.only else []
    skip_filter = [x.strip() for x in args.skip.split(",")] if args.skip else []

    expected_files = [
        "parser_output.json",
        "document_graph.json",
        "chunks.json",
        "metadata.json",
        "retrieval_queries.json",
        "retrieval_results.json"
    ]

    results = {}
    mismatches = []
    overall_pass = True

    # Get all document subdirectories in output
    for entry in os.scandir(args.output):
        if entry.is_dir():
            doc_name = entry.name
            if only_filter and not any(o in doc_name for o in only_filter):
                continue
            if skip_filter and any(s in doc_name for s in skip_filter):
                continue

            results[doc_name] = {}
            doc_golden = golden_hashes.get(doc_name, {})

            for f_name in expected_files:
                f_path = os.path.join(entry.path, f_name)
                if not os.path.exists(f_path):
                    results[doc_name][f_name] = {"status": "FAIL", "reason": "Missing current file"}
                    overall_pass = False
                    continue

                if f_name not in doc_golden:
                    results[doc_name][f_name] = {"status": "FAIL", "reason": "Missing in golden manifest"}
                    overall_pass = False
                    continue

                try:
                    with open(f_path, "r", encoding="utf-8") as f:
                        curr_data = json.load(f)
                    
                    norm_curr = normalize_data(curr_data)
                    serialized_curr = json.dumps(norm_curr, sort_keys=True, ensure_ascii=False).encode('utf-8')
                    curr_hash = compute_sha256(serialized_curr)
                    gold_hash = doc_golden[f_name]

                    if curr_hash == gold_hash:
                        results[doc_name][f_name] = {"status": "PASS", "hash": curr_hash}
                    else:
                        results[doc_name][f_name] = {
                            "status": "FAIL",
                            "reason": "Hash mismatch",
                            "current_hash": curr_hash,
                            "golden_hash": gold_hash,
                            "current_content": json.dumps(norm_curr, indent=2, sort_keys=True)
                        }
                        overall_pass = False
                        mismatches.append((doc_name, f_name))
                except Exception as e:
                    results[doc_name][f_name] = {"status": "FAIL", "reason": f"Error: {e}"}
                    overall_pass = False

    # Generate md report
    report_lines = []
    report_lines.append("# Golden Dataset Comparison Report")
    report_lines.append(f"Generated at: {datetime.utcnow().isoformat()}Z\n")
    
    if overall_pass:
        report_lines.append("## Status: **PASS** ✅\n")
        report_lines.append("All expected outputs match the golden manifest precisely.")
    else:
        report_lines.append("## Status: **FAIL** ❌\n")
        report_lines.append("Some artifacts mismatched or were missing. Details below.")

    report_lines.append("\n## Summary Table\n")
    report_lines.append("| Document | Parser Output | Graph | Chunks | Metadata | Queries | Results |")
    report_lines.append("| --- | --- | --- | --- | --- | --- | --- |")

    for doc, files in sorted(results.items()):
        status_strs = []
        for f in expected_files:
            info = files.get(f, {"status": "FAIL", "reason": "N/A"})
            if info["status"] == "PASS":
                status_strs.append("✅ PASS")
            else:
                status_strs.append(f"❌ FAIL ({info.get('reason', 'Unknown')})")
        report_lines.append(f"| {doc} | " + " | ".join(status_strs) + " |")

    if mismatches:
        report_lines.append("\n## Detailed Mismatches & Diffs\n")
        for doc, f_name in mismatches:
            report_lines.append(f"### {doc} - {f_name}")
            info = results[doc][f_name]
            report_lines.append(f"- **Golden Hash**: `{info.get('golden_hash')}`")
            report_lines.append(f"- **Current Hash**: `{info.get('current_hash')}`")
            report_lines.append("\n*Note: To resolve this, review the changes below. If the change is correct, regenerate hashes.*")
            report_lines.append("\n```diff")
            
            # Since we only have the current content and the golden hash, we can print that the hashes differ,
            # or try to show what is in current.
            # (Wait, since we updated the expected files in-place or have them on disk, if there is a backup or previous we can diff,
            # or we can print the current content to review).
            report_lines.append(f"Hash changed for {f_name}")
            report_lines.append(f"Current normalized data:\n{info.get('current_content')[:1000]}")
            if len(info.get('current_content', '')) > 1000:
                report_lines.append("... [truncated]")
            report_lines.append("```\n")

    # Write report file
    with open(args.report, "w", encoding="utf-8") as f_rep:
        f_rep.write("\n".join(report_lines))

    # Console output
    print("\n=== COMPARISON SUMMARY ===")
    for doc, files in sorted(results.items()):
        print(f"\nDocument: {doc}")
        for f in expected_files:
            info = files.get(f, {"status": "FAIL", "reason": "N/A"})
            if info["status"] == "PASS":
                print(f"  - {f}: [PASS]")
            else:
                print(f"  - {f}: [FAIL] ({info.get('reason')})")

    print("\n-------------------------------------------")
    if overall_pass:
        print("OVERALL STATUS: PASS ✅")
        sys.exit(0)
    else:
        print("OVERALL STATUS: FAIL ❌")
        print(f"Detailed comparison report written to {args.report}")
        sys.exit(1)

if __name__ == "__main__":
    from datetime import datetime
    main()
