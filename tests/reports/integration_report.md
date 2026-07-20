# Integration Regression Report

- **Status**: PASS ✅
- **Execution Time**: 1.91s
- **Files Verified**: `tests/regression/integration/`
- **Output Preview**:
```
============================= test session starts ==============================
platform darwin -- Python 3.10.11, pytest-9.1.1, pluggy-1.6.0 -- /Users/kaustavkumar/Kaustav/Projects/task-schedular/backend/venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/kaustavkumar/Kaustav/Projects/task-schedular
configfile: pytest.ini
testpaths: tests/regression, tests/architecture, tests/contracts, tests/providers, tests/repositories, tests/storage, tests/cache, tests/vector, tests/checkpoints, tests/compatibility, tests/persistence_migration
plugins: mock-3.15.1, anyio-4.14.2
collecting ... collected 59 items / 50 deselected / 9 selected

tests/regression/integration/test_integration.py::test_full_integration_golden[digital_large_document] PASSED [ 11%]
tests/regression/integration/test_integration.py::test_full_integration_golden[forms_large_document] PASSED [ 22%]
tests/regression/integration/test_integration.py::test_full_integration_golden[images_large_document] PASSED [ 33%]
tests/regression/integration/test_integration.py::test_full_integration_golden[mixed_large_document] PASSED [ 44%]
tests/regression/integration/test_integration.py::test_full_integration_golden[multicolumn_large_document] PASSED [ 55%]
tests/regression/integration/test_integration.py::test_full_integration_golden[scanned_large_document] PASSED [ 66%]
tests/regression/integration/test_integration.py::test_full_integration_golden[tables_large_document] PASSED [ 77%]
tests/regression/integration/test_integr
... [truncated]
```
