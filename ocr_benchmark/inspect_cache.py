import os, sys, time, json, traceback
from pathlib import Path

def get_cache_dir():
    # Huggingface cache is typically in ~/.cache/huggingface/hub
    return Path.home() / ".cache" / "huggingface" / "hub" / "models--BAAI--bge-base-en-v1.5"

def check_cache():
    print("=== Cache Inspection ===")
    cache_dir = get_cache_dir()
    print(f"Cache Path: {cache_dir}")
    
    if not cache_dir.exists():
        print("Model not found in cache.")
        return False
        
    total_size = 0
    files_found = []
    
    for root, dirs, files in os.walk(cache_dir):
        for f in files:
            path = Path(root) / f
            size = path.stat().st_size
            total_size += size
            files_found.append(str(path.relative_to(cache_dir)))
            
    print(f"Total Size: {total_size / (1024*1024):.2f} MB")
    
    important_files = [
        "config.json",
        "pytorch_model.bin", # or model.safetensors
        "tokenizer.json",
        "vocab.txt",
        "modules.json"
    ]
    
    print("\nFiles found:")
    has_weights = False
    for f in sorted(files_found):
        print(f" - {f}")
        if "pytorch_model.bin" in f or "model.safetensors" in f:
            has_weights = True
            
    if not has_weights:
        print("\nWARNING: No model weights found!")
        return False
    return True
        
def test_load():
    print("\n=== Model Load Test ===")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(Path.home() / ".cache" / "torch" / "sentence_transformers")
    # Actually wait, sentence_transformers caches directly under ~/.cache/torch/sentence_transformers sometimes.
    
    st_cache = Path.home() / ".cache" / "torch" / "sentence_transformers" / "BAAI_bge-base-en-v1.5"
    if st_cache.exists():
        print(f"SentenceTransformers Cache found at: {st_cache}")
        
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    try:
        from sentence_transformers import SentenceTransformer
        t0 = time.time()
        print("Initializing SentenceTransformer...")
        model = SentenceTransformer("BAAI/bge-base-en-v1.5")
        t1 = time.time()
        print(f"Loaded successfully in {t1-t0:.2f}s")
    except Exception as e:
        print(f"Failed to load: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    check_cache()
    test_load()
