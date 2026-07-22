import logging
from backend.platform.runtime.app_state import app_state
from backend.platform.scheduler.retry_worker import stop_worker_thread

logger = logging.getLogger(__name__)

def platform_shutdown():
    logger.info("Executing platform shutdown sequence...")
    
    # 1. Stop background workers
    stop_worker_thread()
    
    # 2. Flush active memory caches
    if app_state.cache_hierarchy:
        app_state.cache_hierarchy.flush_all()
        
    # 3. Close SQLite DB Connection
    if app_state.db_conn:
        try:
            app_state.db_conn.commit()
            app_state.db_conn.close()
            logger.info("Closed platform SQLite database connection.")
        except Exception as e:
            logger.error(f"Error closing DB connection during shutdown: {e}")
            
    logger.info("Platform shutdown completed.")
