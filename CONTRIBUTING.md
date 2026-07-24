# Contributing to ScaleFlow

We welcome contributions to ScaleFlow! Follow these guidelines to submit bugs, propose optimizations, or add documentation.

## Codebase Freeze Notice (v1.0)
The architecture and engine code for ScaleFlow v1.0 is **frozen**. No new features or core engine refactors will be accepted. Contributions should focus on:
- Documentation clarity and typo fixes.
- Performance tuning parameters.
- Benchmark helper scripts.
- Bug and crash fixes.

## Pull Request Process
1. Fork the repository and create your branch from `main`.
2. Ensure all Pytest tests pass:
   ```bash
   backend/venv/bin/pytest backend/tests/
   ```
3. Run the benchmarks to verify no performance regressions occurred:
   ```bash
   backend/venv/bin/python benchmark/run_benchmark.py
   ```
4. Submit your PR with a clear summary of changes and validation logs.
5. All updates must maintain the standard of the platform being **Production Qualified under the evaluated benchmark suite**.
