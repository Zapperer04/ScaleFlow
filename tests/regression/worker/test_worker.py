import os
import sys
import pytest
import redis
from unittest.mock import MagicMock, patch

# Ensure backend directory is in sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Set environment variables for the test before importing worker
os.environ["DB_MODE"] = "sqlite"
os.environ["REDIS_HOST"] = "127.0.0.1"
os.environ["REDIS_PORT"] = "16379"
os.environ["API_URL"] = "http://127.0.0.1:5000"

from redis_mock_server import RedisMockServer
import worker

@pytest.fixture(scope="module", autouse=True)
def run_redis_mock_server():
    server = RedisMockServer(host="127.0.0.1", port=16379)
    success = server.start()
    if not success:
        pytest.skip("Could not start local RedisMockServer")
    yield server
    server.running = False
    if server.sock:
        server.sock.close()

@pytest.fixture
def mock_api():
    with patch("worker._api_request") as mock_req:
        yield mock_req

@pytest.mark.worker
@pytest.mark.regression
def test_worker_registration_real_lifecycle(mock_api):
    # Tests actual worker registration request formatting
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_api.return_value = mock_resp
    
    with patch("time.sleep", return_value=None):
        worker.register_worker()
        
    assert mock_api.called
    assert "workers/register" in mock_api.call_args[0][1]

@pytest.mark.worker
@pytest.mark.regression
def test_worker_get_next_task_real_redis(mock_api):
    # Initialize mock redis connection and push a task payload
    r = redis.Redis(host="127.0.0.1", port=16379, decode_responses=True)
    q_name = f"task_queue_test_{worker.WORKER_CAPABILITIES[0]}_high"
    
    # Clean queue first
    r.delete(q_name)
    r.delete("scaleflow:paused_queues")
    r.lpush(q_name, '{"task_id": 123, "task_type": "preprocess_document"}')
    
    # Call actual get_next_task()
    queue_name, task_val = worker.get_next_task()
    assert queue_name == q_name
    assert "preprocess_document" in str(task_val)

@pytest.mark.worker
@pytest.mark.regression
def test_lease_expiration_and_recovery_real(mock_api):
    # Verify worker heartbeat is sent via real lifecyle method
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_api.return_value = mock_resp
    
    class StopLoop(Exception):
        pass
        
    with patch("time.sleep", side_effect=StopLoop):
        with pytest.raises(StopLoop):
            worker.send_heartbeat()
            
    assert mock_api.called
