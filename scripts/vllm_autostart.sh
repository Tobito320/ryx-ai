#!/bin/bash
# ============================================================================
# vLLM Auto-Start for Hyprland
#
# Add to your Hyprland config:
#   exec-once = /path/to/ryx-ai/scripts/vllm_autostart.sh
#
# This script:
# 1. Ensures Docker is running
# 2. Starts vLLM with NO model preloaded (lazy loading)
# 3. vLLM will load the model on first request
#
# For RX 7800 XT with 16GB VRAM:
# - Recommended models: 7B GPTQ/AWQ models
# - Max context: 8192 tokens at 70% GPU utilization
# ============================================================================

set -e

# Project paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_VLLM="$PROJECT_ROOT/docker/vllm/docker-compose.yml"
LOG_FILE="$PROJECT_ROOT/data/vllm_autostart.log"

# Ensure log directory exists
mkdir -p "$PROJECT_ROOT/data"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log "=== vLLM Autostart Begin ==="

# Wait for Docker to be ready (with timeout)
wait_for_docker() {
    local timeout=60
    local elapsed=0

    while [ $elapsed -lt $timeout ]; do
        if docker info &> /dev/null 2>&1; then
            log "Docker is ready"
            return 0
        fi
        sleep 2
        ((elapsed+=2))
    done

    log "ERROR: Docker not available after ${timeout}s"
    return 1
}

# Wait for network (important for early boot)
sleep 5

# Ensure Docker is running
log "Waiting for Docker..."
if ! wait_for_docker; then
    log "Failed to connect to Docker. Trying to start..."
    systemctl --user start docker 2>/dev/null || sudo systemctl start docker 2>/dev/null || true
    sleep 5

    if ! wait_for_docker; then
        log "ERROR: Could not start Docker"
        exit 1
    fi
fi

# Check if vLLM container already running
if docker ps --format '{{.Names}}' | grep -q 'ryx-vllm'; then
    log "vLLM container already running"
    exit 0
fi

# Start vLLM via docker-compose
if [ -f "$DOCKER_VLLM" ]; then
    log "Starting vLLM container..."
    cd "$PROJECT_ROOT"

    # Pull latest image if needed (background)
    docker compose -f "$DOCKER_VLLM" pull --quiet &

    # Start container
    if docker compose -f "$DOCKER_VLLM" up -d 2>> "$LOG_FILE"; then
        log "vLLM container started successfully"
        log "Model will be loaded on first request (lazy loading)"
        log "Access at: http://localhost:8001"
    else
        log "ERROR: Failed to start vLLM container"
        exit 1
    fi
else
    log "ERROR: Docker compose file not found: $DOCKER_VLLM"
    exit 1
fi

log "=== vLLM Autostart Complete ==="

# Send notification if notify-send available
if command -v notify-send &> /dev/null; then
    notify-send "Ryx AI" "vLLM is starting...\nPort: 8001" --icon=computer 2>/dev/null || true
fi
