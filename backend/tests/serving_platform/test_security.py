import sys
import os
import pytest
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from backend.platform.security.auth import AuthManager
from backend.platform.security.permissions import PermissionManager
from backend.platform.security.rate_limit import RateLimiter

def test_jwt_auth():
    data = {"sub": "user1", "role": "manager"}
    token = AuthManager.create_access_token(data)
    
    decoded = AuthManager.decode_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user1"
    assert decoded["role"] == "manager"

def test_rbac_permissions():
    # User Permissions
    assert PermissionManager.has_permission("user", "read:document") is True
    assert PermissionManager.has_permission("user", "delete:document") is False
    
    # Manager Permissions
    assert PermissionManager.has_permission("manager", "delete:document") is True
    assert PermissionManager.has_permission("manager", "admin:actions") is False
    
    # Admin Permissions
    assert PermissionManager.has_permission("admin", "delete:document") is True
    assert PermissionManager.has_permission("admin", "admin:actions") is True

def test_rate_limiter():
    limiter = RateLimiter()
    key = "test_ip_1"
    
    # Allow 3 requests per minute
    assert limiter.is_rate_limited(key, max_requests=3, window_seconds=60) is False
    assert limiter.is_rate_limited(key, max_requests=3, window_seconds=60) is False
    assert limiter.is_rate_limited(key, max_requests=3, window_seconds=60) is False
    
    # Fourth request must be rate limited
    assert limiter.is_rate_limited(key, max_requests=3, window_seconds=60) is True
