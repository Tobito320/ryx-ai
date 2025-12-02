#!/bin/bash
# Ryx AI - Lightweight preload script for Hyprland autostart
# Only loads the smallest model to minimize resource usage

# Wait for system to stabilize
sleep 5

# Preload only the 1.5B model for instant responses
ollama run qwen2.5:1.5b "warmup" > /dev/null 2>&1 &

# Create marker file
touch /tmp/ryx-preloaded
