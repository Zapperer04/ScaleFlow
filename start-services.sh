#!/usr/bin/env bash
# ScaleFlow Orchestrator Script for macOS

# Color codes
COLOR_INFO="\033[1;36m"
COLOR_SUCCESS="\033[1;32m"
COLOR_WARNING="\033[1;33m"
COLOR_ERROR="\033[1;31m"
COLOR_RESET="\033[0m"

show_menu() {
    clear
    echo -e "${COLOR_INFO}=======================================================================${COLOR_RESET}"
    echo -e "  ⚡ ScaleFlow: Distributed Task Execution Engine (macOS)"
    echo -e "${COLOR_INFO}=======================================================================${COLOR_RESET}"
    echo
    echo "  This script will help you launch all components of the ScaleFlow system."
    echo
    echo "  [1] Start Redis + Qdrant + Postgres + Workers in Docker"
    echo "  [2] Start Flask API Backend locally (Python with Hot-Reload)"
    echo "  [3] Start React Dashboard Frontend locally (Node.js)"
    echo "  [4] Start ALL services locally (requires separate terminal windows)"
    echo "  [5] Start ALL services in Docker Compose"
    echo "  [6] Clean ports and stop all running processes (Ports 3000, 5000)"
    echo "  [7] Exit"
    echo
    echo -e "${COLOR_INFO}=======================================================================${COLOR_RESET}"
    read -p "Select an option (1-7): " opt
    case $opt in
        1) start_docker_workers ;;
        2) start_backend_local ;;
        3) start_frontend_local ;;
        4) start_all_local ;;
        5) start_docker_all ;;
        6) cleanup_ports ;;
        7) exit 0 ;;
        *) echo -e "${COLOR_ERROR}Invalid option.${COLOR_RESET}" && sleep 2 && show_menu ;;
    esac
}

start_docker_workers() {
    echo -e "\n🐳 Starting Redis, Qdrant, Postgres, and Workers via Docker Compose..."
    docker compose up -d redis qdrant postgres worker1 worker2 worker3
    echo -e "${COLOR_SUCCESS}Docker services started!${COLOR_RESET}"
    read -p "Press enter to return to menu..."
    show_menu
}

start_backend_local() {
    echo -e "\n🐍 Starting Flask API Backend locally..."
    if [ ! -d "backend/venv" ]; then
        echo -e "${COLOR_ERROR}[ERROR] Virtual environment 'venv' not found in backend/. Creating one...${COLOR_RESET}"
        python3 -m venv backend/venv
        backend/venv/bin/pip install -r backend/requirements.txt
    fi
    source backend/venv/bin/activate
    python3 backend/app.py
}

start_frontend_local() {
    echo -e "\n⚛️ Starting React Dashboard Frontend..."
    cd frontend
    if [ ! -d "node_modules" ]; then
        echo -e "${COLOR_WARNING}[WARNING] node_modules not found. Running npm install...${COLOR_RESET}"
        npm install
    fi
    npm start
}

start_all_local() {
    echo -e "\n⚡ Starting all services locally..."
    echo "To run all services locally, please open three separate terminal tabs and run:"
    echo "  Tab 1 (Databases): docker compose up -d redis qdrant postgres"
    echo "  Tab 2 (Backend):   source backend/venv/bin/activate && python3 backend/app.py"
    echo "  Tab 3 (Frontend):  cd frontend && npm start"
    read -p "Press enter to return to menu..."
    show_menu
}

start_docker_all() {
    echo -e "\n🐳 Starting all services inside Docker Compose..."
    docker compose up -d --build
    echo -e "${COLOR_SUCCESS}All containers successfully started!${COLOR_RESET}"
    read -p "Press enter to return to menu..."
    show_menu
}

cleanup_ports() {
    echo -e "\n🧹 Cleaning up ports 3000 and 5000..."
    docker compose down
    for port in 3000 5000; do
        pid=$(lsof -t -i:$port)
        if [ ! -z "$pid" ]; then
            echo "Killing process on port $port (PID: $pid)"
            kill -9 $pid
        fi
    done
    echo -e "${COLOR_SUCCESS}Port cleanup complete.${COLOR_RESET}"
    read -p "Press enter to return to menu..."
    show_menu
}

# Run the menu
show_menu
