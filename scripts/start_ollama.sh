#!/bin/bash
# Ryx AI - Ollama GPU Startup Script
# Created 2024-12-10

# Kill any existing ollama
pkill -9 ollama 2>/dev/null
sleep 1

# Set environment for GPU
export LD_LIBRARY_PATH=/opt/rocm/lib:/usr/lib/ollama:$LD_LIBRARY_PATH
export OLLAMA_MAX_LOADED_MODELS=3
export OLLAMA_NUM_PARALLEL=2

# Start ollama
echo "Starting Ollama with GPU support..."
nohup ollama serve > ~/.ollama/ollama.log 2>&1 &

sleep 3

# Verify GPU
if grep -q "AMD Radeon" ~/.ollama/ollama.log 2>/dev/null; then
    echo "✓ GPU detected: AMD Radeon RX 7800 XT"
    echo "✓ Multi-model: up to 3 models in VRAM"
else
    echo "⚠ GPU not detected, running on CPU"
fi

echo "Ollama started (PID: $(pgrep ollama | head -1))"
