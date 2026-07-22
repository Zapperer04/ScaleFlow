# Resource limits and configuration flags

MAX_DOCUMENT_SIZE_MB = 50
MAX_UPLOAD_PAGES = 500

# Feature Flags for experiments and modular retrieval paths
FEATURE_FLAGS = {
    "enable_graph": True,
    "enable_layout": True,
    "enable_entity": True,
    "enable_reranker": True,
    "enable_multihop": True,
    "enable_reflection": True
}
