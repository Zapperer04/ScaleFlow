import sys
import os
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from backend.platform.api.routes import app

client = TestClient(app)

def test_api_versioning_and_healthz():
    # Liveness check
    response = client.get("/api/v1/healthz/liveness")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
    
    # Readiness check (requires active DB state initialization)
    response = client.get("/api/v1/healthz/readiness")
    assert response.status_code == 200 or response.status_code == 503
