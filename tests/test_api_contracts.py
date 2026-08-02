import pytest
import json
from backend.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_openapi_swagger_spec(client):
    res = client.get('/swagger')
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["openapi"] == "3.0.0"
    assert "paths" in data
    assert "/v1/query" in data["paths"]
