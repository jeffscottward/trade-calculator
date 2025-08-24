#!/bin/bash

# Automated Earnings Volatility Trading System - Development Startup Script
# Starts all necessary services for development

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (parent of scripts)
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
# Change to project root
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}Starting Development Environment${NC}"
echo -e "${BLUE}=====================================${NC}"

# Function to check if a port is in use
check_port() {
    lsof -ti:$1 > /dev/null 2>&1
    return $?
}

# Function to kill process on port
kill_port() {
    if check_port $1; then
        echo -e "${YELLOW}Port $1 is in use. Killing existing process...${NC}"
        lsof -ti:$1 | xargs kill -9 2>/dev/null
        sleep 1
    fi
}

# Clean up function for graceful shutdown
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    
    # Kill all background processes
    jobs -p | xargs kill -9 2>/dev/null
    
    # Kill processes on specific ports
    kill_port 3000
    kill_port 3001
    kill_port 5001
    
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

# Set up trap for cleanup on script exit
trap cleanup EXIT INT TERM

# Check and kill existing processes on required ports
echo -e "${BLUE}Checking ports...${NC}"
kill_port 3000  # FastAPI backend
kill_port 3001  # Next.js frontend
kill_port 5001  # IB Client Portal

# Start IB Client Portal Gateway
echo -e "\n${GREEN}Starting IB Client Portal Gateway on port 5001...${NC}"
if [ -d "backend/clientportal.gw" ]; then
    cd backend/clientportal.gw
    if [ -f "bin/run.sh" ]; then
        chmod +x bin/run.sh
        ./bin/run.sh root/conf.yaml &
        IB_PID=$!
        cd "$PROJECT_ROOT"
        echo -e "${GREEN}IB Client Portal started (PID: $IB_PID)${NC}"
        echo -e "${YELLOW}⚠️  IMPORTANT: Manual browser login required!${NC}"
        echo -e "${YELLOW}1. Open your browser and go to: https://localhost:5001${NC}"
        echo -e "${YELLOW}2. Accept the self-signed certificate warning${NC}"
        echo -e "${YELLOW}3. Log in with IB credentials from .env:${NC}"
        echo -e "${YELLOW}   - See IB_BROWSER_USERNAME and IB_BROWSER_PASSWORD${NC}"
        echo -e "${YELLOW}4. After login, you should see 'Client login succeeds'${NC}"
        echo -e "${YELLOW}5. Keep the browser tab open during development${NC}"
    else
        echo -e "${RED}IB Client Portal run script not found!${NC}"
        echo -e "${YELLOW}Please download from: https://www.interactivebrokers.com/en/index.php?f=5041${NC}"
    fi
else
    echo -e "${RED}IB Client Portal directory not found!${NC}"
    echo -e "${YELLOW}Please download from: https://www.interactivebrokers.com/en/index.php?f=5041${NC}"
fi

# Start FastAPI backend
echo -e "\n${GREEN}Starting FastAPI backend on port 3000...${NC}"
if [ -f "backend/venv/bin/activate" ]; then
    source backend/venv/bin/activate
    cd backend/api
    python main.py &
    API_PID=$!
    cd ../../scripts
    echo -e "${GREEN}FastAPI backend started (PID: $API_PID)${NC}"
else
    echo -e "${RED}Virtual environment not found!${NC}"
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd api
    python main.py &
    API_PID=$!
    cd ../../scripts
    echo -e "${GREEN}FastAPI backend started (PID: $API_PID)${NC}"
fi

# Start Next.js frontend
echo -e "\n${GREEN}Starting Next.js frontend on port 3001...${NC}"
cd frontend
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    pnpm install
fi
pnpm dev &
FRONTEND_PID=$!
cd "$PROJECT_ROOT"
echo -e "${GREEN}Next.js frontend started (PID: $FRONTEND_PID)${NC}"

# Wait a moment for services to start
sleep 3

# Display status
echo -e "\n${BLUE}=====================================${NC}"
echo -e "${GREEN}All services started successfully!${NC}"
echo -e "${BLUE}=====================================${NC}"
echo -e "\n${YELLOW}Service URLs:${NC}"
echo -e "  📊 Frontend: ${GREEN}http://localhost:3001${NC}"
echo -e "  🔧 Backend API: ${GREEN}http://localhost:3000${NC}"
echo -e "  💼 IB Client Portal: ${GREEN}https://localhost:5001${NC}"
echo -e "\n${YELLOW}To stop all services, press Ctrl+C${NC}\n"

# Display logs in real-time
echo -e "${BLUE}Showing combined logs (press Ctrl+C to stop all services):${NC}\n"

# Keep script running and show logs
wait