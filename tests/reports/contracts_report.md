# Contract Verification Report

- **Status**: PASS ✅
- **Execution Time**: 1.62s
- **Files Verified**: `tests/regression/contracts/`
- **Output Preview**:
```
============================= test session starts ==============================
platform darwin -- Python 3.10.11, pytest-9.1.1, pluggy-1.6.0 -- /Users/kaustavkumar/Kaustav/Projects/task-schedular/backend/venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/kaustavkumar/Kaustav/Projects/task-schedular
configfile: pytest.ini
testpaths: tests/regression, tests/architecture, tests/contracts, tests/providers, tests/repositories, tests/storage, tests/cache, tests/vector, tests/checkpoints, tests/compatibility, tests/persistence_migration
plugins: mock-3.15.1, anyio-4.14.2
collecting ... collected 59 items / 53 deselected / 6 selected

tests/contracts/test_contracts.py::test_metadata_schema_contract PASSED  [ 16%]
tests/contracts/test_contracts.py::test_parser_schema_contract PASSED    [ 33%]
tests/contracts/test_contracts.py::test_chunks_schema_contract PASSED    [ 50%]
tests/contracts/test_contracts.py::test_graph_schema_contract PASSED     [ 66%]
tests/contracts/test_phase2_contracts.py::test_generated_schemas_exist PASSED [ 83%]
tests/contracts/test_phase2_contracts.py::test_chunk_schema_validation PASSED [100%]

=============================== warnings summary ===============================
backend/models.py:147
backend/models.py:147
  /Users/kaustavkumar/Kaustav/Projects/task-schedular/backend/models.py:147: MovedIn20Warning: The ``declarative_base()`` function is now available as sqlalchemy.orm.declarative_base(). (deprecated since: 2.0) (Background on SQLAlchemy 2.0 a
... [truncated]
```
