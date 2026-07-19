# Determinism Verification Report

- **Status**: PASS ✅
- **Execution Time**: 1.41s
- **Files Verified**: `tests/regression/determinism/`
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

tests/regression/determinism/test_determinism.py::test_determinism_twice[digital/large_document.txt] PASSED [ 33%]
tests/regression/determinism/test_determinism.py::test_determinism_twice[scanned/large_document.txt] PASSED [ 66%]
tests/regression/determinism/test_determinism.py::test_determinism_twice[mixed/large_document.txt] PASSED [100%]

======================= 3 passed, 34 deselected in 1.10s =======================


```
