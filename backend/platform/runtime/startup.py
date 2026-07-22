import os
import sqlite3
import logging
from backend.platform.config.settings import settings
from backend.platform.runtime.app_state import app_state

logger = logging.getLogger(__name__)

def initialize_directories():
    dirs = [
        settings.BASE_STORAGE_PATH,
        settings.DOCUMENTS_DIR,
        settings.ARTIFACTS_DIR,
        settings.INDEXES_DIR,
        settings.EMBEDDINGS_DIR,
        settings.GRAPHS_DIR,
        settings.CONVERSATIONS_DIR,
        settings.CACHE_DIR,
        settings.LOGS_DIR,
        settings.REPORTS_DIR
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    logger.info("Initialized platform storage subdirectories.")

def initialize_database():
    db_path = settings.SQLITE_DB_PATH
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Documents Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        filepath TEXT NOT NULL,
        state TEXT NOT NULL,
        parser_version TEXT,
        embedding_version TEXT,
        chunk_version TEXT,
        graph_version TEXT,
        index_version TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 2. Conversations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 3. Conversation State
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversation_state (
        conversation_id TEXT PRIMARY KEY,
        state_json TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 4. Conversation Turns
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversation_turns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        user_message TEXT NOT NULL,
        assistant_message TEXT NOT NULL,
        citations_json TEXT,
        metrics_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 5. Cost Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cost_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        user_id TEXT,
        document_id TEXT,
        provider TEXT NOT NULL,
        model TEXT NOT NULL,
        prompt_tokens INTEGER NOT NULL,
        completion_tokens INTEGER NOT NULL,
        cost REAL NOT NULL
    )
    """)
    
    # 6. Job Queue
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS job_queue (
        id TEXT PRIMARY KEY,
        task_type TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        status TEXT NOT NULL,
        worker_id TEXT,
        attempts INTEGER DEFAULT 0,
        max_attempts INTEGER DEFAULT 3,
        error TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 7. Workers Lifecycle Registry
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS worker_registry (
        worker_id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    app_state.db_conn = conn
    logger.info("Initialized platform SQLite database schema.")

def start_services():
    # Initialize cache hierarchy
    from backend.platform.cache.hierarchy import CacheHierarchy
    app_state.cache_hierarchy = CacheHierarchy()
    
    # Initialize pluggable queue
    from backend.platform.scheduler.indexing_queue import IndexingQueue
    app_state.queue = IndexingQueue()
    
    # Initialize Prometheus metrics collector
    from backend.platform.observability.metrics import MetricsCollector
    app_state.metrics = MetricsCollector()
    
    # Initialize OpenTelemetry tracer
    from backend.platform.observability.tracing import TelemetryTracer
    app_state.tracer = TelemetryTracer()
    
    # Start worker process/thread
    from backend.platform.scheduler.retry_worker import start_worker_thread
    app_state.worker = start_worker_thread()
    logger.info("Background indexing worker thread started.")

def platform_startup():
    initialize_directories()
    initialize_database()
    start_services()
    logger.info("Platform startup sequence completed successfully.")
