# Cache hierarchy configuration

# Time-To-Live (TTL) values in seconds
CACHE_TTL = {
    "embedding": 86400 * 30,  # 30 days
    "retrieval": 3600 * 2,    # 2 hours
    "answer": 86400,          # 24 hours
    "session": 1800           # 30 minutes
}

# Maximum elements in L1 in-memory LRU cache
L1_MAX_SIZE = {
    "embedding": 5000,
    "retrieval": 1000,
    "answer": 500,
    "session": 100
}

# Cache enabling flags
CACHE_ENABLED = {
    "L1": True,
    "L2": False,  # Redis disabled by default
    "L3": True    # Disk persistent fallback
}
