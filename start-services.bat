@echo off
TITLE ScaleFlow Orchestrator
COLOR 0B

echo =======================================================================
echo   ⚡ ScaleFlow: Distributed Task Execution Engine
echo =======================================================================
echo.
echo   This orchestrator script will help you launch all components
echo   of the ScaleFlow system on your Windows machine.
echo.
echo   [1] Start Redis + 3 Worker Containers (Docker Compose)
echo   [2] Start Flask API Backend (Python)
echo   [3] Start React Dashboard Frontend (Node.js)
echo   [4] Start all of the above (Separate CMD Windows)
echo   [5] Start a single Worker Node locally (No Docker)
echo   [6] Exit
echo.
echo =======================================================================
set /p opt="Select an option (1-6): "

if "%opt%"=="1" goto DOCKER
if "%opt%"=="2" goto BACKEND
if "%opt%"=="3" goto FRONTEND
if "%opt%"=="4" goto START_ALL
if "%opt%"=="5" goto LOCAL_WORKER
if "%opt%"=="6" goto EXIT
goto INVALID

:DOCKER
echo.
echo 🐳 Starting Redis and 3 Workers using Docker Compose...
docker compose up
pause
goto EXIT

:BACKEND
echo.
echo 🐍 Starting Flask API Backend...
cd backend
if not exist venv (
    echo [ERROR] Virtual environment 'venv' not found in backend directory.
    echo Please run 'python -m venv venv' and install 'requirements.txt' first.
    pause
    exit /b
)
venv\Scripts\python.exe app.py
pause
goto EXIT

:FRONTEND
echo.
echo ⚛️ Starting React Dashboard Frontend...
cd frontend
if not exist node_modules (
    echo [WARNING] node_modules not found. Attempting 'npm install'...
    call npm install
)
npm start
pause
goto EXIT

:START_ALL
echo.
echo ⚡ Orchestrating ScaleFlow Startup Sequence...
echo.

:: 1. Launch Redis and Workers in Docker (in a new window if docker is available)
echo - Checking Docker daemon and starting containers...
start "ScaleFlow - Docker Workers & Redis" cmd /c "docker compose up"

:: 2. Launch Flask API Backend
echo - Launching Flask API Backend...
start "ScaleFlow - Flask Backend API" cmd /c "cd backend && venv\Scripts\python.exe app.py"

:: 3. Launch React Frontend
echo - Launching React Dashboard Frontend...
start "ScaleFlow - React Frontend" cmd /c "cd frontend && npm start"

echo.
echo [SUCCESS] ScaleFlow orchestration initiated!
echo Check the newly opened command prompt windows for service logs.
echo.
pause
goto EXIT

:LOCAL_WORKER
echo.
echo 👷 Starting Local Worker Node...
cd backend
if not exist venv (
    echo [ERROR] Virtual environment 'venv' not found in backend directory.
    pause
    exit /b
)
venv\Scripts\python.exe worker.py
pause
goto EXIT

:INVALID
echo Invalid choice. Exiting.
pause
:EXIT
exit
