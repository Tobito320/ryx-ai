#!/bin/bash
# ============================================================================
# RyxHub Auto-Start Script
#
# Automatically starts all required services for RyxHub:
# 1. Docker (if not running)
# 2. vLLM (GPU inference server)
# 3. SearXNG (privacy search - optional)
# 4. RyxHub backend API
# 5. RyxHub frontend
#
# Usage: ./start_ryxhub.sh [--no-browser]
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RYXHUB_DIR="$PROJECT_ROOT/ryxhub"
DOCKER_VLLM="$PROJECT_ROOT/docker/vllm/docker-compose.yml"
DOCKER_RYXHUB="$PROJECT_ROOT/docker/ryxhub/docker-compose.yml"

# Service ports
VLLM_PORT=8001
RYXHUB_FRONTEND_PORT=5173
RYXHUB_API_PORT=8420
SEARXNG_PORT=8888

# Options
OPEN_BROWSER=true
if [[ "$1" == "--no-browser" ]]; then
    OPEN_BROWSER=false
fi

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                     RyxHub Launcher                           ║"
echo "║               Ryx AI Web Control Center                       ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Function to check if a port is in use
check_port() {
    local port=$1
    if command -v lsof &> /dev/null; then
        lsof -i ":$port" &> /dev/null
    elif command -v ss &> /dev/null; then
        ss -tuln | grep -q ":$port "
    elif command -v netstat &> /dev/null; then
        netstat -tuln | grep -q ":$port "
    else
        return 1
    fi
}

# Function to wait for a service to be ready
wait_for_service() {
    local name=$1
    local url=$2
    local timeout=$3
    local elapsed=0

    echo -ne "  ${YELLOW}⏳ Waiting for $name...${NC}"

    while [ $elapsed -lt $timeout ]; do
        if curl -s -o /dev/null -w "" "$url" 2>/dev/null; then
            echo -e "\r  ${GREEN}✓ $name is ready${NC}                    "
            return 0
        fi
        sleep 1
        ((elapsed++))
        echo -ne "\r  ${YELLOW}⏳ Waiting for $name... (${elapsed}s)${NC}"
    done

    echo -e "\r  ${RED}✗ $name failed to start (timeout)${NC}"
    return 1
}

# Step 1: Check Docker
echo -e "\n${BLUE}[1/5] Checking Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "  ${RED}✗ Docker is not installed${NC}"
    echo "  Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker info &> /dev/null 2>&1; then
    echo -e "  ${YELLOW}⚠ Docker daemon is not running${NC}"
    echo -e "  ${CYAN}Starting Docker...${NC}"

    # Try to start Docker (systemd)
    if command -v systemctl &> /dev/null; then
        sudo systemctl start docker 2>/dev/null || true
        sleep 2
    fi

    if ! docker info &> /dev/null 2>&1; then
        echo -e "  ${RED}✗ Could not start Docker${NC}"
        echo "  Please start Docker manually: sudo systemctl start docker"
        exit 1
    fi
fi
echo -e "  ${GREEN}✓ Docker is running${NC}"

# Step 2: Start vLLM (GPU inference)
echo -e "\n${BLUE}[2/5] Starting vLLM (GPU inference server)...${NC}"
if check_port $VLLM_PORT; then
    echo -e "  ${GREEN}✓ vLLM already running on port $VLLM_PORT${NC}"
else
    if [ -f "$DOCKER_VLLM" ]; then
        echo -e "  ${CYAN}Starting vLLM container...${NC}"
        docker compose -f "$DOCKER_VLLM" up -d 2>/dev/null

        # Wait for vLLM to load the model (this can take 30-120 seconds)
        echo -e "  ${YELLOW}Loading model... (this may take 1-2 minutes)${NC}"
        if ! wait_for_service "vLLM" "http://localhost:$VLLM_PORT/health" 120; then
            echo -e "  ${YELLOW}⚠ vLLM is still starting. RyxHub will work once it's ready.${NC}"
        fi
    else
        echo -e "  ${YELLOW}⚠ vLLM compose file not found. Skipping.${NC}"
        echo "  Chat will work with mock responses until vLLM is available."
    fi
fi

# Step 3: Start SearXNG (optional)
echo -e "\n${BLUE}[3/5] Checking SearXNG (web search)...${NC}"
if check_port $SEARXNG_PORT; then
    echo -e "  ${GREEN}✓ SearXNG already running on port $SEARXNG_PORT${NC}"
else
    echo -e "  ${YELLOW}ℹ SearXNG not running (optional - web search disabled)${NC}"
    # Uncomment below to auto-start SearXNG
    # docker run -d --name ryx-searxng -p 8888:8080 searxng/searxng:latest 2>/dev/null || true
fi

# Step 4: Start RyxHub Backend API
echo -e "\n${BLUE}[4/5] Starting RyxHub API...${NC}"
if check_port $RYXHUB_API_PORT; then
    echo -e "  ${GREEN}✓ RyxHub API already running on port $RYXHUB_API_PORT${NC}"
else
    echo -e "  ${CYAN}Starting RyxHub API server...${NC}"

    # Start the FastAPI backend directly (not via Docker for dev)
    cd "$PROJECT_ROOT"

    # Check if we're in a venv
    if [ -z "$VIRTUAL_ENV" ] && [ -d ".venv" ]; then
        source .venv/bin/activate 2>/dev/null || true
    fi

    # Start the backend in the background
    VLLM_BASE_URL="http://localhost:$VLLM_PORT" \
    SEARXNG_URL="http://localhost:$SEARXNG_PORT" \
    RYX_API_PORT=$RYXHUB_API_PORT \
    python -m uvicorn ryx_pkg.interfaces.web.backend.main:app \
        --host 0.0.0.0 \
        --port $RYXHUB_API_PORT \
        --reload \
        > "$PROJECT_ROOT/data/ryxhub_api.log" 2>&1 &

    API_PID=$!
    echo $API_PID > "$PROJECT_ROOT/data/ryxhub_api.pid"

    wait_for_service "RyxHub API" "http://localhost:$RYXHUB_API_PORT/api/health" 30
fi

# Step 5: Start RyxHub Frontend
echo -e "\n${BLUE}[5/5] Starting RyxHub Frontend...${NC}"
if check_port $RYXHUB_FRONTEND_PORT; then
    echo -e "  ${GREEN}✓ RyxHub Frontend already running on port $RYXHUB_FRONTEND_PORT${NC}"
else
    echo -e "  ${CYAN}Starting RyxHub Frontend...${NC}"

    cd "$RYXHUB_DIR"

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo -e "  ${YELLOW}Installing dependencies...${NC}"
        npm install --silent 2>/dev/null
    fi

    # Set environment variables for live mode
    export VITE_RYX_API_URL="http://localhost:$RYXHUB_API_PORT"
    export VITE_USE_MOCK_API="false"

    # Start Vite dev server in background
    npm run dev -- --host > "$PROJECT_ROOT/data/ryxhub_frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$PROJECT_ROOT/data/ryxhub_frontend.pid"

    wait_for_service "RyxHub Frontend" "http://localhost:$RYXHUB_FRONTEND_PORT" 30
fi

# Summary
echo -e "\n${GREEN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                  RyxHub is Ready!                             ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
echo -e "║  ${CYAN}Frontend:${GREEN}  http://localhost:$RYXHUB_FRONTEND_PORT                        ║"
echo -e "║  ${CYAN}API:${GREEN}       http://localhost:$RYXHUB_API_PORT                             ║"
echo -e "║  ${CYAN}vLLM:${GREEN}      http://localhost:$VLLM_PORT                             ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Open browser
if $OPEN_BROWSER; then
    echo -e "${CYAN}Opening browser...${NC}"
    sleep 1

    if command -v xdg-open &> /dev/null; then
        xdg-open "http://localhost:$RYXHUB_FRONTEND_PORT" &
    elif command -v open &> /dev/null; then
        open "http://localhost:$RYXHUB_FRONTEND_PORT" &
    elif command -v firefox &> /dev/null; then
        firefox "http://localhost:$RYXHUB_FRONTEND_PORT" &
    fi
fi

echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}"
echo -e "${CYAN}Logs: tail -f $PROJECT_ROOT/data/ryxhub_*.log${NC}\n"

# Keep script running to allow Ctrl+C cleanup
trap cleanup EXIT

cleanup() {
    echo -e "\n${YELLOW}Shutting down RyxHub services...${NC}"

    # Kill frontend
    if [ -f "$PROJECT_ROOT/data/ryxhub_frontend.pid" ]; then
        kill $(cat "$PROJECT_ROOT/data/ryxhub_frontend.pid") 2>/dev/null || true
        rm "$PROJECT_ROOT/data/ryxhub_frontend.pid"
    fi

    # Kill API
    if [ -f "$PROJECT_ROOT/data/ryxhub_api.pid" ]; then
        kill $(cat "$PROJECT_ROOT/data/ryxhub_api.pid") 2>/dev/null || true
        rm "$PROJECT_ROOT/data/ryxhub_api.pid"
    fi

    echo -e "${GREEN}RyxHub stopped.${NC}"
    echo -e "${CYAN}vLLM and Docker containers are still running.${NC}"
    echo -e "${CYAN}To stop them: docker compose -f $DOCKER_VLLM down${NC}"
}

# Wait forever (until Ctrl+C)
wait
