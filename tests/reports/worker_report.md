# Worker Lifecycle Report

- **Status**: PASS ✅
- **Execution Time**: 1.40s
- **Files Verified**: `tests/regression/worker/`
- **Output Preview**:
```
============================= test session starts ==============================
platform darwin -- Python 3.10.11, pytest-9.1.1, pluggy-1.6.0 -- /Users/kaustavkumar/Kaustav/Projects/task-schedular/backend/venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/kaustavkumar/Kaustav/Projects/task-schedular
configfile: pytest.ini
testpaths: tests/regression, tests/architecture, tests/contracts
plugins: mock-3.15.1, anyio-4.14.2
collecting ... collected 37 items / 34 deselected / 3 selected

tests/regression/worker/test_worker.py::test_worker_registration_real_lifecycle PASSED [ 33%]
tests/regression/worker/test_worker.py::test_worker_get_next_task_real_redis PASSED [ 66%]
tests/regression/worker/test_worker.py::test_lease_expiration_and_recovery_real PASSED [100%]

======================= 3 passed, 34 deselected in 1.10s =======================


```
