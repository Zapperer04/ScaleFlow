import os, sys, time, json, traceback
from pathlib import Path

def get_cache_dir():
    return Path.home() / ".cache" / "huggingface" / "hub" / "models--BAAI--bge-base-en-v1.5"

def get_snapshot_path():
    cache_dir = get_cache_dir()
    snapshots_dir = cache_dir / "snapshots"
    if not snapshots_dir.exists():
        return None
    subdirs = list(snapshots_dir.iterdir())
    if not subdirs:
        return None
    return subdirs[0]

def test_load_local():
    print("\n=== Model Load Test (Absolute Path) ===")
    snapshot = get_snapshot_path()
    if not snapshot:
        print("No snapshot found.")
        return
        
    print(f"Loading directly from: {snapshot}")
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    try:
        from sentence_transformers import SentenceTransformer
        t0 = time.time()
        # Load from absolute path to bypass HuggingFace hub resolution entirely
        model = SentenceTransformer(str(snapshot))
        t1 = time.time()
        print(f"Loaded successfully in {t1-t0:.2f}s")
    except Exception as e:
        print(f"Failed to load: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_load_local()
