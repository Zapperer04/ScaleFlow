import os
import re
import time
import logging
from functools import wraps
from flask import request, jsonify

logger = logging.getLogger(__name__)

# Security configuration
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'json'}
ALLOWED_MIME_TYPES = {
    'application/pdf', 'text/plain', 'image/png', 'image/jpeg', 'application/json'
}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

# Prompt injection heuristics
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"system\s+override", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a\s+different\s+ai", re.IGNORECASE),
    re.compile(r"you\s+must\s+bypass\s+all\s+safety\s+checks", re.IGNORECASE),
    re.compile(r"new\s+role:\s*", re.IGNORECASE),
    re.compile(r"bypass\s+restrictions", re.IGNORECASE)
]

# Simple In-Memory Rate Limiter
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 60  # requests per window
ip_request_history = {}  # IP -> list of timestamps

def rate_limit_check(ip_address: str) -> bool:
    """Returns True if request is allowed, False if rate limited"""
    now = time.time()
    if ip_address not in ip_request_history:
        ip_request_history[ip_address] = []
    
    # Filter out requests outside window
    ip_request_history[ip_address] = [
        t for t in ip_request_history[ip_address] if now - t < RATE_LIMIT_WINDOW
    ]
    
    if len(ip_request_history[ip_address]) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    
    ip_request_history[ip_address].append(now)
    return True


def detect_prompt_injection(user_input: str) -> bool:
    """Returns True if prompt injection is suspected"""
    if not user_input or not isinstance(user_input, str):
        return False
    for pattern in INJECTION_PATTERNS:
        if pattern.search(user_input):
            logger.warning(f"Prompt injection pattern matched in: {user_input[:100]}")
            return True
    return False


def prevent_path_traversal(filepath: str) -> str:
    """Sanitizes filepath to prevent path traversal, returning baseline name"""
    if not filepath:
        return ""
    # Strip directory path separators and drive specs
    base = os.path.basename(filepath)
    # Remove any sequence of dots and slashes just in case
    clean = re.sub(r'\.+[\\/]+', '', base)
    return clean


def sanitize_query(query: str) -> str:
    """Sanitizes string inputs to prevent injection and malicious formats"""
    if not query or not isinstance(query, str):
        return ""
    # Strip HTML tags
    query = re.sub(r'<[^>]*>', '', query)
    # Strip carriage returns / line breaks to avoid log injections
    query = query.replace('\r', '').replace('\n', ' ')
    # Limit length
    return query[:2000].strip()


def validate_file_upload(filename: str, content_type: str, file_size: int) -> tuple:
    """Validates file properties. Returns (is_valid, error_message)"""
    if file_size > MAX_CONTENT_LENGTH:
        return False, f"File exceeds maximum allowed size of {MAX_CONTENT_LENGTH} bytes."
    
    if content_type not in ALLOWED_MIME_TYPES:
        return False, f"MIME type '{content_type}' is not allowed."
        
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File extension '{ext}' is not allowed."
        
    return True, ""


# Mock JWT validation / Role-based access decorator for Flask routes
def secure_route(role_required: str = "user"):
    """Flask decorator to validate JWT/auth headers and role permission level"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Enforce content length check if body exists
            if request.content_length and request.content_length > MAX_CONTENT_LENGTH:
                return jsonify({"error": "Payload Too Large"}), 413
                
            # Perform Rate Limiting
            client_ip = request.remote_addr or "unknown"
            if not rate_limit_check(client_ip):
                return jsonify({"error": "Too Many Requests"}), 429

            # Header JWT check (Mocking authentication logic matching app.py keys or role checking)
            auth_header = request.headers.get("Authorization", "")
            token = None
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
            
            # Simple dummy validation logic: tokens formatted like "jwt-<role>-token"
            user_role = "user"
            if token:
                if "admin" in token:
                    user_role = "admin"
                elif "user" in token:
                    user_role = "user"
                elif token == "valid-token":
                    user_role = "user"
                else:
                    return jsonify({"error": "Unauthorized: Invalid JWT signature"}), 401
            else:
                # If no token, check if api_key exists (compatible with existing code)
                api_key = request.headers.get("X-API-Key") or request.args.get("api_key")
                if api_key:
                    # Let api key act as admin
                    user_role = "admin"
                else:
                    # Defaulting to guest / public if no keys
                    return jsonify({"error": "Unauthorized: Missing authentication credentials"}), 401

            # Validate role permissions
            if role_required == "admin" and user_role != "admin":
                return jsonify({"error": "Forbidden: Requires Administrator privileges"}), 403

            # Check prompt injection in JSON queries
            if request.is_json:
                data = request.json
                if isinstance(data, dict):
                    q = data.get("query", "")
                    if q and detect_prompt_injection(q):
                        return jsonify({"error": "Malicious payload input detected"}), 400

            return f(*args, **kwargs)
        return decorated_function
    return decorator
