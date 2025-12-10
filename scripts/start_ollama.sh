#!/bin/bash
# Ryx AI - Ollama GPU Startup Script
# Created 2024-12-10

# Kill any existing ollama (ignore errors)
pkill -9 ollama 2>/dev/null
sleep 2

# Set environment for GPU
export LD_LIBRARY_PATH=/opt/rocm/lib:/usr/lib/ollama:$LD_LIBRARY_PATH
export OLLAMA_MAX_LOADED_MODELS=3
export OLLAMA_NUM_PARALLEL=2

# Start ollama
echo "Starting Ollama with GPU support..."
ollama serve > ~/.ollama/ollama.log 2>&1 &

sleep 4

# Verify GPU
if grep -q "AMD Radeon\|gfx1101" ~/.ollama/ollama.log 2>/dev/null; then
    echo "✓ GPU detected: AMD Radeon RX 7800 XT"
    echo "✓ Multi-model: up to 3 models in VRAM"
elif curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✓ Ollama running (GPU detection in log may be delayed)"
else
    echo "⚠ Ollama may not have started correctly"
    tail -5 ~/.ollama/ollama.log
fi

echo "Ollama started (PID: $(pgrep -f 'ollama serve' | head -1))"
