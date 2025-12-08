#!/bin/bash
# Start vLLM in background for RyxSurf AI features
# This runs on Hyprland startup

VLLM_CONTAINER="ryx-vllm"

# Check if already running
if docker ps --format '{{.Names}}' | grep -q "^${VLLM_CONTAINER}$"; then
    exit 0
fi

# Start vLLM with fast mode config (8K context, 90% GPU)
cd /home/tobi/ryx-ai/docker/vllm/modes
docker compose -f fast.yml up -d 2>/dev/null &

exit 0
