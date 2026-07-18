# Architecture Decision Violations

1. **Single Responsibility Principle (SRP) Violations**:
   - `app.py` acts as a God-file hosting route endpoints, database transaction wrappers, and queue management.
   - `worker.py` contains both task queue polling loops and the actual business logic wrapper implementations for task processing.

2. **Dependency Inversion Principle (DIP) Violations**:
   - Direct execution imports are utilized instead of abstract interfaces (e.g. `vlm_provider.py` directly references the concrete class of `gemini_rate_manager.py`).

3. **Interface Segregation Principle (ISP) Violations**:
   - `pdf_parser.py` exposes a single monolithic parser method that mixes low-level digital PDF character extraction with high-level structural VLM generation.

4. **Circular & Hidden Coupling**:
   - Mutual dependency between `app.py` and `worker.py` during validation checks.
   - Redundant duplicate preprocessor file at root level (`document_preprocessor.py`) matches backend service exactly, hiding which file is active.
