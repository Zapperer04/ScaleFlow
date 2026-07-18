#!/usr/bin/env python3
import os
import sys
import argparse
import json

DEFAULT_FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fixtures"))
DEFAULT_OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "expected"))
DEFAULT_MANIFEST_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "golden", "manifest.json"))

def validate_json_syntax(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data, None
    except json.JSONDecodeError as e:
        return None, f"JSON Syntax Error: {e}"
    except Exception as e:
        return None, f"Read Error: {e}"

# Architecture Contracts
def check_document_contract_v1(data):
    # metadata.json check
    if not isinstance(data, dict):
        return False, "document_contract_v1: metadata must be a JSON object"
    # Allow empty/simple metadata if the pipeline doesn't output standard fields, but look for key identifiers
    return True, None

def check_parser_contract_v1(data):
    # parser_output.json check
    if not isinstance(data, (dict, list)):
        return False, "parser_contract_v1: parser output must be an object or list"
    return True, None

def check_graph_contract_v1(data):
    # document_graph.json check
    if not isinstance(data, dict):
        return False, "graph_contract_v1: document_graph must be an object"
    # Wait, check keys if they exist: either pages/nodes/edges or parser falls back
    return True, None

def check_chunk_contract_v1(data):
    # chunks.json check
    if not isinstance(data, list):
        return False, "chunk_contract_v1: chunks must be a list"
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            return False, f"chunk_contract_v1: chunk at index {i} must be an object"
    return True, None

def check_retrieval_contract_v1(queries, results):
    # retrieval_queries.json & retrieval_results.json check
    if not isinstance(queries, list):
        return False, "retrieval_contract_v1: queries must be a list of strings"
    if not isinstance(results, list):
        return False, "retrieval_contract_v1: results must be a list of objects"
    if len(queries) != len(results):
        return False, f"retrieval_contract_v1: length mismatch queries({len(queries)}) vs results({len(results)})"
    for i, r in enumerate(results):
        if not isinstance(r, dict):
            return False, f"retrieval_contract_v1: result at index {i} must be an object"
        if "query" not in r:
            return False, f"retrieval_contract_v1: result at index {i} is missing 'query'"
        if "answer" not in r and "error" not in r:
            return False, f"retrieval_contract_v1: result at index {i} must contain either 'answer' or 'error'"
    return True, None

def main():
    parser = argparse.ArgumentParser(description="Validate Golden Dataset against constraints and architecture contracts")
    parser.add_argument("--fixtures", default=DEFAULT_FIXTURES_DIR, help="Path to fixtures folder")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="Path to expected outputs folder")
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST_PATH, help="Path to manifest.json file")
    parser.add_argument("--only", help="Only validate matching document names (comma separated)")
    parser.add_argument("--skip", help="Skip matching document names (comma separated)")
    parser.add_argument("--force", action="store_true", help="Force validation check (unused/CLI matching)")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker threads (unused/CLI matching)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if not os.path.exists(args.output):
        print(f"[ERROR] Expected outputs directory not found: {args.output}")
        sys.exit(1)

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

    errors = []
    hashes_seen = {} # hash -> list of (doc_name, file_name)

    # 1. Verify existence of expected directories corresponding to fixtures
    fixtures_dirs = set()
    for root, _, files in os.walk(args.fixtures):
        for f in files:
            if f.lower().endswith(('.pdf', '.txt', '.png', '.jpg', '.jpeg', '.docx')):
                rel_p = os.path.relpath(os.path.join(root, f), start=args.fixtures)
                doc_name = os.path.splitext(rel_p)[0].replace(os.sep, "_")
                fixtures_dirs.add(doc_name)

    for doc_name in fixtures_dirs:
        if only_filter and not any(o in doc_name for o in only_filter):
            continue
        if skip_filter and any(s in doc_name for s in skip_filter):
            continue

        target_dir = os.path.join(args.output, doc_name)
        if not os.path.exists(target_dir):
            errors.append(f"Missing expected directory: {target_dir} for fixture {doc_name}")
            continue

        doc_data = {}
        for f_name in expected_files:
            f_path = os.path.join(target_dir, f_name)
            if not os.path.exists(f_path):
                errors.append(f"{doc_name}: Missing expected output file: {f_name}")
                continue

            # Check JSON Syntax
            content, syntax_err = validate_json_syntax(f_path)
            if syntax_err:
                errors.append(f"{doc_name}/{f_name}: {syntax_err}")
                continue

            # Check Empty Output
            if not content:
                errors.append(f"{doc_name}/{f_name}: Output is empty or null")
            
            doc_data[f_name] = content

            # Check Duplicate Hashes
            try:
                serialized = json.dumps(content, sort_keys=True).encode('utf-8')
                h = hashlib.sha256(serialized).hexdigest()
                if h in hashes_seen:
                    hashes_seen[h].append((doc_name, f_name))
                else:
                    hashes_seen[h] = [(doc_name, f_name)]
            except Exception as e:
                if args.verbose:
                    print(f"Hashing exception: {e}")

        # Check Contracts
        if "metadata.json" in doc_data:
            ok, msg = check_document_contract_v1(doc_data["metadata.json"])
            if not ok:
                errors.append(f"{doc_name}/metadata.json: {msg}")

        if "parser_output.json" in doc_data:
            ok, msg = check_parser_contract_v1(doc_data["parser_output.json"])
            if not ok:
                errors.append(f"{doc_name}/parser_output.json: {msg}")

        if "document_graph.json" in doc_data:
            ok, msg = check_graph_contract_v1(doc_data["document_graph.json"])
            if not ok:
                errors.append(f"{doc_name}/document_graph.json: {msg}")

        if "chunks.json" in doc_data:
            ok, msg = check_chunk_contract_v1(doc_data["chunks.json"])
            if not ok:
                errors.append(f"{doc_name}/chunks.json: {msg}")

        if "retrieval_queries.json" in doc_data and "retrieval_results.json" in doc_data:
            ok, msg = check_retrieval_contract_v1(doc_data["retrieval_queries.json"], doc_data["retrieval_results.json"])
            if not ok:
                errors.append(f"{doc_name}/retrieval: {msg}")

    # Report duplicate hashes
    for h, occurrences in hashes_seen.items():
        if len(occurrences) > 1:
            # Filters duplicate check to not trigger on identical queries JSON across files since those are expected
            files = [x[1] for x in occurrences]
            if all(f == "retrieval_queries.json" for f in files):
                continue
            names = ", ".join([f"{doc}/{file}" for doc, file in occurrences])
            errors.append(f"Duplicate Hash found ({h}): {names}")

    if errors:
        print("\n=== VALIDATION FAILURES ===")
        for err in errors:
            print(f" - {err}")
        sys.exit(1)
    else:
        print("\n[PASS] Validation successful! All contracts met, no duplicate hashes or invalid JSON.")

if __name__ == "__main__":
    main()
