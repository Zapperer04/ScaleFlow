# Retrieval Regression Report

- **Status**: PASS ✅
- **Execution Time**: 2.22s
- **Files Verified**: `tests/regression/retrieval/`
- **Output Preview**:
```
============================= test session starts ==============================
platform darwin -- Python 3.10.11, pytest-9.1.1, pluggy-1.6.0 -- /Users/kaustavkumar/Kaustav/Projects/task-schedular/backend/venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/kaustavkumar/Kaustav/Projects/task-schedular
configfile: pytest.ini
testpaths: tests/regression, tests/architecture, tests/contracts, tests/providers, tests/repositories, tests/storage, tests/cache, tests/vector, tests/checkpoints, tests/compatibility, tests/persistence_migration
plugins: mock-3.15.1, anyio-4.14.2
collecting ... collected 59 items / 51 deselected / 8 selected

tests/regression/retrieval/test_retrieval.py::test_retrieval_golden_regression[digital_large_document] PASSED [ 12%]
tests/regression/retrieval/test_retrieval.py::test_retrieval_golden_regression[forms_large_document] PASSED [ 25%]
tests/regression/retrieval/test_retrieval.py::test_retrieval_golden_regression[images_large_document] PASSED [ 37%]
tests/regression/retrieval/test_retrieval.py::test_retrieval_golden_regression[mixed_large_document] PASSED [ 50%]
tests/regression/retrieval/test_retrieval.py::test_retrieval_golden_regression[multicolumn_large_document] PASSED [ 62%]
tests/regression/retrieval/test_retrieval.py::test_retrieval_golden_regression[scanned_large_document] PASSED [ 75%]
tests/regression/retrieval/test_retrieval.py::test_retrieval_golden_regression[tables_large_document] PASSED [ 87%]
tests/regression/retrieval/test_retrieva
... [truncated]
```
