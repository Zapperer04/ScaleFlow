#!/usr/bin/env python
"""
ScaleFlow Dev Cleanup Script
----------------------------
This is a local development utility to clear Qdrant test vector data.
Do NOT run this script in production. It is intended for local demo/development cleanup only.

Usage:
  python cleanup_test_data.py [--clear-all]

Options:
  --clear-all   Purge ALL vector points in the collection (default is only test files).
"""

import os
import sys

def load_env():
    try:
        with open('.env') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, val = line.strip().split('=', 1)
                    os.environ.setdefault(key.strip(), val.strip())
    except FileNotFoundError:
        pass

if __name__ == "__main__":
    load_env()
    
    # Check if env is production
    is_production = os.getenv("ENV", "development").lower() == "production"
    if is_production:
        print("[ERROR] Cleanup script is disabled in production environments.", file=sys.stderr)
        sys.exit(1)
        
    clear_all = "--clear-all" in sys.argv
    
    # Qdrant client imports
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as qmodels
    except ImportError:
        print("[ERROR] qdrant-client package is not installed. Run 'pip install qdrant-client'", file=sys.stderr)
        sys.exit(1)
        
    QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.environ.get("QDRANT_PORT", 6333))
    collection_name = "scaleflow_chunks"
    
    print(f"Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}...")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    try:
        collections = client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)
        if not exists:
            print(f"Collection '{collection_name}' does not exist. Nothing to clean.")
            sys.exit(0)
            
        if clear_all:
            print(f"Purging ALL vector points from '{collection_name}'...")
            client.delete(
                collection_name=collection_name,
                points_selector=qmodels.Filter(must=[])
            )
            print("[OK] Re-created/cleared all points in the collection successfully.")
        else:
            print(f"Deleting test points (test_*) from '{collection_name}'...")
            res = client.delete(
                collection_name=collection_name,
                points_selector=qmodels.Filter(
                    should=[
                        qmodels.FieldCondition(
                            key="original_filename",
                            match=qmodels.MatchText(text="test_")
                        ),
                        qmodels.FieldCondition(
                            key="original_filename",
                            match=qmodels.MatchValue(value="test_retrieval_doc.txt")
                        ),
                        qmodels.FieldCondition(
                            key="original_filename",
                            match=qmodels.MatchValue(value="test_ingestion_file.txt")
                        ),
                        qmodels.FieldCondition(
                            key="original_filename",
                            match=qmodels.MatchValue(value="test_vector_search_doc.txt")
                        )
                    ]
                )
            )
            print("[OK] Test points deleted successfully.")
            
    except Exception as e:
        print(f"[ERROR] Failed to clean collection: {e}", file=sys.stderr)
        sys.exit(1)
