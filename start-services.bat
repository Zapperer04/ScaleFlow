@echo off
TITLE ScaleFlow Orchestrator
COLOR 0B

:MENU
cls
echo =======================================================================
echo   ⚡ ScaleFlow: Distributed Task Execution Engine
echo =======================================================================
echo.
echo   This orchestrator script will help you launch all components
echo   of the ScaleFlow system on your Windows machine.
echo.
echo   [1] Start Redis + 3 Worker Containers (Docker Compose with Watch)
echo   [2] Start Flask API Backend (Python with Hot-Reload)
echo   [3] Start React Dashboard Frontend (Node.js)
echo   [4] Start all of the above (Separate CMD Windows with Watch/Hot-Reload)
echo   [5] Start ALL services in Docker Compose (with Watch/Hot-Reload)
echo   [6] Start a single Worker Node locally (No Docker)
echo   [7] Clean ports and stop all running processes (Free Ports 3000/3001/5000)
echo   [8] Exit
echo.
echo =======================================================================
set /p opt="Select an option (1-8): "

if "%opt%"=="1" goto DOCKER
if "%opt%"=="2" goto BACKEND
if "%opt%"=="3" goto FRONTEND
if "%opt%"=="4" goto START_ALL
if "%opt%"=="5" goto DOCKER_ALL
if "%opt%"=="6" goto LOCAL_WORKER
if "%opt%"=="7" goto CLEANUP
if "%opt%"=="8" goto EXIT
goto INVALID

:DOCKER
echo.
echo 🐳 Starting Redis and 3 Workers using Docker Compose...
docker info >nul 2>&1
if %errorlevel% equ 0 goto DOCKER_ONLINE_1

echo   [INFO] Docker is not running. Starting Docker Desktop...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
echo   [INFO] Waiting for Docker Engine to initialize (this may take a minute)...
set /a docker_retry=0

:WAIT_DOCKER_1
set /a docker_retry+=1
if %docker_retry% gtr 12 (
    echo.
    echo   [ERROR] Docker Engine failed to start after 60 seconds.
    echo   Please open Docker Desktop manually, make sure it is running, and try again.
    pause
    goto MENU
)
C:\Windows\System32\timeout.exe /t 5 >nul
docker info >nul 2>&1
if %errorlevel% neq 0 goto WAIT_DOCKER_1
echo   [SUCCESS] Docker Engine is now online.

:DOCKER_ONLINE_1
docker compose up redis worker1 worker2 worker3 qdrant postgres --watch
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
for /f "tokens=1,2 delims==" %%a in (.env) do set %%a=%%b
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

:: Check backend virtual environment first to prevent silent backend launch failures
if not exist backend\venv (
    echo [ERROR] Virtual environment 'venv' not found in backend directory.
    echo Please run 'python -m venv venv' and install 'requirements.txt' inside 'backend' folder first.
    pause
    goto MENU
)

echo - Cleaning up conflicting local processes first...
python scripts\cleanup_services.py

:: 1. Launch Redis and Workers in Docker (in a new window if docker is available)
echo - Checking Docker daemon...
docker info >nul 2>&1
if %errorlevel% equ 0 goto DOCKER_ONLINE_4

echo   [INFO] Docker is not running. Starting Docker Desktop...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
echo   [INFO] Waiting for Docker Engine to initialize (this may take a minute)...
set /a docker_retry=0

:WAIT_DOCKER_4
set /a docker_retry+=1
if %docker_retry% gtr 12 (
    echo.
    echo   [ERROR] Docker Engine failed to start after 60 seconds.
    echo   Please open Docker Desktop manually, make sure it is running, and try again.
    pause
    goto MENU
)
C:\Windows\System32\timeout.exe /t 5 >nul
docker info >nul 2>&1
if %errorlevel% neq 0 goto WAIT_DOCKER_4
echo   [SUCCESS] Docker Engine is now online.

:DOCKER_ONLINE_4
echo - Starting containers...
start "ScaleFlow - Docker Workers & Redis" cmd /c "docker compose up redis worker1 worker2 worker3 qdrant postgres --watch"

:: 2. Launch Flask API Backend (load .env first so API_KEY matches)
echo - Launching Flask API Backend...
start "ScaleFlow - Flask API Backend" cmd /c "cd backend && for /f "tokens=1,2 delims==" %%a in (.env) do set %%a=%%b && venv\Scripts\python.exe app.py"

:: 3. Launch React Dashboard Frontend
echo - Launching React Dashboard Frontend...
start "ScaleFlow - React Frontend" cmd /c "cd frontend && npm start"

echo.
echo [SUCCESS] ScaleFlow orchestration initiated!
echo Check the newly opened command prompt windows for service logs.
echo.
pause
goto EXIT

:DOCKER_ALL
echo.
echo 🐳 Starting ALL services inside Docker Compose (with watch/reload)...
docker info >nul 2>&1
if %errorlevel% equ 0 goto DOCKER_ONLINE_ALL

echo   [INFO] Docker is not running. Starting Docker Desktop...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
echo   [INFO] Waiting for Docker Engine to initialize (this may take a minute)...
set /a docker_retry=0

:WAIT_DOCKER_ALL
set /a docker_retry+=1
if %docker_retry% gtr 12 (
    echo.
    echo   [ERROR] Docker Engine failed to start after 60 seconds.
    echo   Please open Docker Desktop manually, make sure it is running, and try again.
    pause
    goto MENU
)
C:\Windows\System32\timeout.exe /t 5 >nul
docker info >nul 2>&1
if %errorlevel% neq 0 goto WAIT_DOCKER_ALL
echo   [SUCCESS] Docker Engine is now online.

:DOCKER_ONLINE_ALL
docker compose up --watch
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
echo   [INFO] Loading API_KEY from backend/.env...
for /f "tokens=1,2 delims==" %%a in (.env) do set %%a=%%b
echo   [INFO] API_KEY loaded. Starting worker...
venv\Scripts\python.exe worker.py
pause
goto MENU

:CLEANUP
echo.
echo 🧹 Cleaning up services and freeing ports...
python scripts\cleanup_services.py
echo   [SUCCESS] Services cleaned and ports freed.
pause
goto MENU

:INVALID
echo Invalid choice. Exiting.
pause
:EXIT
exit
