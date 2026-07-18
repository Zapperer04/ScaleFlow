#!/usr/bin/env python3
import os
import sys
import re

# Define a fallback whoosh escape function to bypass version-specific Whoosh import bugs
def whoosh_escape(text):
    return re.sub(r'([\\+\-\!\(\)\{\}\[\]\^\"~\*\?\:\/])', r'\\\1', text)

# Patch Whoosh qparser escape at runtime
try:
    import whoosh.qparser
    whoosh.qparser.escape = whoosh_escape
    sys.modules['whoosh.qparser'].escape = whoosh_escape
except ImportError:
    pass

# Patch chunking service to handle chunk_id fallback for plain-text nodes
try:
    # Add backend directory to sys.path first
    backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    import services.chunking_service
    original_build_node_map = services.chunking_service._build_node_map

    def patched_build_node_map(pages):
        if pages:
            for page in pages:
                if isinstance(page, dict):
                    for node in page.get("nodes", []):
                        if isinstance(node, dict):
                            if "chunk_id" in node and "node_id" not in node and "id" not in node:
                                node["node_id"] = node["chunk_id"]
        return original_build_node_map(pages)

    services.chunking_service._build_node_map = patched_build_node_map
    print("Chunking service successfully patched.", flush=True)
except Exception as e:
    print(f"Failed to patch chunking service: {e}", flush=True)

# Patch Qdrant upserts to succeed locally without a running Qdrant daemon
try:
    import services.vector_store
    services.vector_store.upsert_document_chunks = lambda *args, **kwargs: (True, 0.0, 0.0)
    print("Vector store upserts successfully mocked to run offline.", flush=True)
except Exception as e:
    print(f"Failed to patch vector store: {e}", flush=True)

if __name__ == "__main__":
    import worker
    print("WORKER RUNNER STARTED WITH WHOOSH PATCH AND QDRANT MOCK", flush=True)
    try:
        from services.embedding_service import get_embedding_model
        get_embedding_model()
        from services.reranker_service import get_reranker
        get_reranker()
    except Exception as e:
        print(f"Startup warning: {e}")
    worker.worker_loop()
