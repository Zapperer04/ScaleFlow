# Codebase Hotspot Analysis

Ranked list of the top files in terms of maintainability risk, LOC, and dependency coupling:

1. **[backend/app.py](file:///Users/kaustavkumar/Kaustav/Projects/task-schedular/backend/app.py)**
   - *LOC*: 5,425 | *Complexity (Est)*: 767 | *Imports*: 23
   - *Issue*: Massive monolithic Flask server handling all endpoints, database queries, and helper validations. High regression risk on change.

2. **[backend/worker.py](file:///Users/kaustavkumar/Kaustav/Projects/task-schedular/backend/worker.py)**
   - *LOC*: 2,104 | *Complexity (Est)*: 378 | *Imports*: 19
   - *Issue*: Custom polling loop mixed with task-handling definitions and LeaseRenewer thread execution.

3. **[backend/services/document_preprocessor.py](file:///Users/kaustavkumar/Kaustav/Projects/task-schedular/backend/services/document_preprocessor.py)**
   - *LOC*: 1,847 | *Complexity (Est)*: 273 | *Imports*: 12
   - *Issue*: Complex OpenCV/imaging scripts, duplicated at root level.

4. **[backend/services/gemini_rate_manager.py](file:///Users/kaustavkumar/Kaustav/Projects/task-schedular/backend/services/gemini_rate_manager.py)**
   - *LOC*: 1,622 | *Complexity (Est)*: 256 | *Imports*: 8
   - *Issue*: Holds global lock rates for Gemini API calls.
