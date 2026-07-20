# Worker Lifecycle Report

- **Status**: PASS ✅
- **Execution Time**: 1.74s
- **Files Verified**: `tests/regression/worker/`
- **Output Preview**:
```
============================= test session starts ==============================
platform darwin -- Python 3.10.11, pytest-9.1.1, pluggy-1.6.0 -- /Users/kaustavkumar/Kaustav/Projects/task-schedular/backend/venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/kaustavkumar/Kaustav/Projects/task-schedular
configfile: pytest.ini
testpaths: tests/regression, tests/architecture, tests/contracts, tests/providers, tests/repositories, tests/storage, tests/cache, tests/vector, tests/checkpoints, tests/compatibility, tests/persistence_migration
plugins: mock-3.15.1, anyio-4.14.2
collecting ... collected 59 items / 56 deselected / 3 selected

tests/regression/worker/test_worker.py::test_worker_registration_real_lifecycle PASSED [ 33%]
tests/regression/worker/test_worker.py::test_worker_get_next_task_real_redis PASSED [ 66%]
tests/regression/worker/test_worker.py::test_lease_expiration_and_recovery_real PASSED [100%]

=============================== warnings summary ===============================
backend/models.py:147
backend/models.py:147
  /Users/kaustavkumar/Kaustav/Projects/task-schedular/backend/models.py:147: MovedIn20Warning: The ``declarative_base()`` function is now available as sqlalchemy.orm.declarative_base(). (deprecated since: 2.0) (Background on SQLAlchemy 2.0 at: https://sqlalche.me/e/b8d9)
    Base = declarative_base()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================= 3 passed, 56 deselected, 2 warnings in 1.29s ==============
... [truncated]
```
