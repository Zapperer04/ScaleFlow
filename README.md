<div align="center">

# ⚡ ScaleFlow
### Distributed Task Execution Engine

A production-grade distributed task orchestration system built for horizontal scalability, automatic load balancing, and fault tolerance.


![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-18-61dafb?style=for-the-badge&logo=react&logoColor=black)
![Docker](https://img.shields.io/badge/Docker-Enabled-2496ed?style=for-the-badge&logo=docker&logoColor=white)



</div>

---

## 📖 About The Project

**ScaleFlow** is a robust engine designed to handle heavy background processing loads. Unlike simple cron jobs, ScaleFlow distributes tasks across multiple containerized worker nodes, ensuring that your application remains responsive even under heavy load. It features a real-time React dashboard for monitoring queue depths, worker health, and task throughput.

### 🌟 Key Enhancements in V2
- **Environment Configuration**: Secure `.env` files for production readiness.
- **API Key Security**: Endpoints protected via headers to prevent unauthorized task injection.
- **Relational Dependencies**: Tasks dependencies are stored in a relational `task_dependencies` SQL table rather than JSON strings.
- **Pagination**: The API now paginates task history to prevent out-of-memory errors on large databases.
- **Stuck Task Recovery**: The backend automatically detects worker crashes and reaps/requeues tasks stuck in the `running` state.
- **Componentized UI**: React dashboard refactored into modular components.
- **Operational Dashboard**: New features including detailed task modal, real-time queue depth charts, rich worker states, manual retry, and cancellation controls.
- **Audit Logging**: Comprehensive chronological event logging per task for debugging.

## ✨ Key Features

* **🌐 Distributed Architecture** — Seamlessly scale horizontally by adding more worker nodes.
* **📨 FIFO Priority Queues** — Reliable Redis-based queuing guarantees task ordering by high, medium, and low priority.
* **💾 Persistent State & Logging** — PostgreSQL ensures no task data is lost, along with a full chronological audit trail of all task events.
* **📊 Real-time Monitoring** — Live dashboard with interactive modals, queue stats, and active worker telemetry.
* **🛡️ Fault Tolerance & Control** — Automatic stuck-task recovery plus API endpoints for manual task retry and cancellation.
* **🐳 Container Native** — Fully orchestrated with Docker Compose.

---

## 🏗️ System Architecture

The system utilizes a producer-consumer model where the API produces tasks and multiple worker nodes consume them concurrently.

```text
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │─────▶│  Flask API   │─────▶│ PostgreSQL  │
│ UI (React)  │      │  (Producer)  │      │ (Persistence)│
└─────────────┘      └──────┬───────┘      └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │ Redis Queue  │
                     │  (Broker)    │
                     └──────┬───────┘
                            │
             ┌──────────────┼─────────────┐
             ▼              ▼             ▼
        ┌─────────┐    ┌─────────┐    ┌─────────┐
        │ Worker 1│    │ Worker 2│    │ Worker 3│
        └─────────┘    └─────────┘    └─────────┘
```

---

## 🚀 Setup & Installation

### 1. Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL
- Docker Desktop (for Redis and Workers)

### 2. Database Configuration
Create a database in PostgreSQL named `task_schedular`.
```sql
CREATE DATABASE task_schedular;
```

### 3. Environment Variables
Copy the `.env.example` files in both the `frontend` and `backend` directories and rename them to `.env`.

**Backend `.env`:**
```ini
API_PORT=5000
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/task_schedular
REDIS_HOST=localhost
REDIS_PORT=6379
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
API_KEY=dev_secret_api_key
TASK_RUNNING_TIMEOUT_SECONDS=300
```

**Frontend `.env`:**
```ini
REACT_APP_API_URL=http://localhost:5000
REACT_APP_POLL_INTERVAL_MS=3000
REACT_APP_API_KEY=dev_secret_api_key
```

### 4. Running the Application
The easiest way to start everything on Windows is to run the provided orchestrator script:
```powershell
./start-services.bat
```
Select **Option 4** to launch the Docker Workers, Flask Backend, and React Frontend in separate windows.

---

## 🧠 Interview Guide

If you are presenting this project, here is how you can explain it:

**Simple Explanation:** "I built a system that handles heavy background jobs. Instead of a server trying to do everything at once and crashing, my system puts tasks in a line (queue) and has multiple background 'workers' that take turns doing the jobs. I built a live dashboard to watch them work."

**Technical Explanation:** "ScaleFlow is a distributed task orchestration engine. I built a Flask REST API that acts as a producer, storing task states in PostgreSQL and pushing jobs into Redis priority queues. Containerized worker nodes consume these queues concurrently, execute the payload, and update the database. The React frontend provides real-time telemetry on system throughput."

**Possible Questions & Answers:**
* *Q: Why use Redis instead of just reading from the PostgreSQL database?*
  * **A:** Databases use row-locks and are slow for highly concurrent queue operations. Redis operates in memory and handles atomic pop operations (`brpop`), preventing two workers from grabbing the same task.
* *Q: What happens if a worker crashes while processing a task?*
  * **A:** The Flask backend has a stuck-task reaping mechanism. During periodic polling, the API checks for tasks that have been in the `running` state longer than the configured timeout (e.g., 300 seconds). It automatically marks them as failed and re-queues them if retries are available. All of this is documented via the `task_logs` table for full observability.
* *Q: How does the dependency system work?*
  * **A:** Tasks can have relationships stored in the `task_dependencies` table. When a task completes, the worker triggers an API endpoint that checks if any pending tasks were waiting on the completed task. If all dependencies are met, the pending task is pushed into Redis.
* *Q: How do you handle operational control when things go wrong?*
  * **A:** We have dedicated endpoints (`POST /tasks/<id>/retry` and `POST /tasks/<id>/cancel`). If a system failure happens, operators can use the frontend Task Detail Modal to force-retry a task, which clears its error state and places it back in the appropriate priority queue. If a pending task is no longer needed, it can be cancelled, and workers will automatically skip it when fetching from the broker.
* *Q: How do you monitor worker utilization?*
  * **A:** Workers run a daemon thread that sends a richer heartbeat every 10 seconds containing their current execution state (`busy` or `idle`), the ID of the task they are working on, and their lifetime success/failure counts. The dashboard combines this with the `/queues/stats` endpoint to provide a complete picture of cluster health and bottleneck locations.

## 📡 API Reference (New in V3)
* `GET /tasks/<id>/details` - Returns full task payload including a chronological timeline of `TaskLog` events.
* `POST /tasks/<id>/retry` - Requires API key. Resets a failed task and requeues it. Accepts `{"force": true}`.
* `POST /tasks/<id>/cancel` - Requires API key. Cancels a pending/running task.
* `GET /queues/stats` - Returns atomic LLEN counts of all Redis queues.

---

## 🛠️ Troubleshooting
- **Redis Connection Errors:** Ensure Docker Desktop is running and the `scaleflow-redis` container is up.
- **PostgreSQL Connection Errors:** Verify your local username and password match the `DATABASE_URL` in `backend/.env`.
- **CORS Errors:** Ensure your frontend URL (e.g., `http://localhost:3000`) is listed in the `ALLOWED_ORIGINS` of the `backend/.env` file.
