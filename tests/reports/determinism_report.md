# Determinism Verification Report

- **Status**: PASS ✅
- **Execution Time**: 1.61s
- **Files Verified**: `tests/regression/determinism/`
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

tests/regression/determinism/test_determinism.py::test_determinism_twice[digital/large_document.txt] PASSED [ 33%]
tests/regression/determinism/test_determinism.py::test_determinism_twice[scanned/large_document.txt] PASSED [ 66%]
tests/regression/determinism/test_determinism.py::test_determinism_twice[mixed/large_document.txt] PASSED [100%]

=============================== warnings summary ===============================
backend/models.py:147
backend/models.py:147
  /Users/kaustavkumar/Kaustav/Projects/task-schedular/backend/models.py:147: MovedIn20Warning: The ``declarative_base()`` function is now available as sqlalchemy.orm.declarative_base(). (deprecated since: 2.0) (Background on SQLAlchemy 2.0 at: https://sqlalche.me/e/b8d9)
    Base = declarative_base()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=============
... [truncated]
```
