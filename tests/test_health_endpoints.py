import pytest
import json
from backend.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_live_endpoint(client):
    res = client.get('/v1/live')
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "alive"

def test_ready_endpoint(client):
    res = client.get('/v1/ready')
    # Since DB might be online, status code can be 200 or 503 if offline in tests
    assert res.status_code in (200, 503)

def test_health_endpoint(client):
    res = client.get('/v1/health')
    assert res.status_code in (200, 503)
    data = json.loads(res.data)
    assert "status" in data
    assert "database" in data
    assert "redis" in data
