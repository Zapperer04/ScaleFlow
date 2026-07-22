import os

class Settings:
    API_VERSION_PREFIX = "/api/v1"
    
    # Storage settings
    BASE_STORAGE_PATH = os.getenv("PLATFORM_STORAGE_PATH", "./storage")
    DOCUMENTS_DIR = os.path.join(BASE_STORAGE_PATH, "documents")
    ARTIFACTS_DIR = os.path.join(BASE_STORAGE_PATH, "artifacts")
    INDEXES_DIR = os.path.join(BASE_STORAGE_PATH, "indexes")
    EMBEDDINGS_DIR = os.path.join(BASE_STORAGE_PATH, "embeddings")
    GRAPHS_DIR = os.path.join(BASE_STORAGE_PATH, "graphs")
    CONVERSATIONS_DIR = os.path.join(BASE_STORAGE_PATH, "conversations")
    CACHE_DIR = os.path.join(BASE_STORAGE_PATH, "cache")
    LOGS_DIR = os.path.join(BASE_STORAGE_PATH, "logs")
    REPORTS_DIR = os.path.join(BASE_STORAGE_PATH, "reports")
    
    # DB paths
    SQLITE_DB_PATH = os.path.join(CONVERSATIONS_DIR, "platform.db")
    
    # Security
    JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-change-in-prod")
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60
    
    # Rate Limiting
    DEFAULT_RATE_LIMIT_RPM = 60 # Requests per minute
    
    # Queue settings
    QUEUE_BACKEND = os.getenv("QUEUE_BACKEND", "sqlite") # sqlite, redis, memory
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

settings = Settings()
