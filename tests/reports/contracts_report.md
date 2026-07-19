# Contract Verification Report

- **Status**: PASS ✅
- **Execution Time**: 1.40s
- **Files Verified**: `tests/regression/contracts/`
- **Output Preview**:
```
============================= test session starts ==============================
platform darwin -- Python 3.10.11, pytest-9.1.1, pluggy-1.6.0 -- /Users/kaustavkumar/Kaustav/Projects/task-schedular/backend/venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/kaustavkumar/Kaustav/Projects/task-schedular
configfile: pytest.ini
testpaths: tests/regression, tests/architecture, tests/contracts
plugins: mock-3.15.1, anyio-4.14.2
collecting ... collected 37 items / 33 deselected / 4 selected

tests/contracts/test_contracts.py::test_metadata_schema_contract PASSED  [ 25%]
tests/contracts/test_contracts.py::test_parser_schema_contract PASSED    [ 50%]
tests/contracts/test_contracts.py::test_chunks_schema_contract PASSED    [ 75%]
tests/contracts/test_contracts.py::test_graph_schema_contract PASSED     [100%]

======================= 4 passed, 33 deselected in 1.10s =======================


```
