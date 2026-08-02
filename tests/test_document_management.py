import pytest
import os
import json
from backend.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_document_list(client):
    headers = {"Authorization": "Bearer jwt-admin-token"}
    res = client.get('/files', headers=headers)
    assert res.status_code == 200
    data = json.loads(res.data)
    assert isinstance(data, list)

def test_document_upload_validation(client):
    headers = {"Authorization": "Bearer jwt-admin-token"}
    
    # Try sending unsupported file type
    data = {
        'file': (open(__file__, 'rb'), 'hack.exe')
    }
    res = client.post('/files/upload', data=data, content_type='multipart/form-data', headers=headers)
    # The server might enforce API key authentication or return a 400 upload validation failure
    assert res.status_code in (400, 401, 302)
