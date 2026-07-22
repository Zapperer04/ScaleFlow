import os
import time
import logging
from backend.platform.config.settings import settings

class AuditLogger:
    def __init__(self):
        os.makedirs(settings.LOGS_DIR, exist_ok=True)
        log_file = os.path.join(settings.LOGS_DIR, "audit.log")
        self.logger = logging.getLogger("platform.audit")
        self.logger.setLevel(logging.INFO)
        
        # Avoid duplicating handlers if already set up
        if not self.logger.handlers:
            handler = logging.FileHandler(log_file)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_action(self, user_id: str, action: str, resource_id: str, status: str, details: str = ""):
        message = f"User: {user_id} | Action: {action} | Resource: {resource_id} | Status: {status} | Details: {details}"
        self.logger.info(message)

audit_logger = AuditLogger()
