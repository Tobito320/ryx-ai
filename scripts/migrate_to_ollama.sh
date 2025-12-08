#!/bin/bash
# Ryx AI - Complete vLLM to Ollama Migration
# This script removes ALL vLLM traces and sets up Ollama

set -e

echo "🗑️  PHASE 1: Removing vLLM (34GB models + containers)..."

# Stop any vLLM containers
echo "Stopping vLLM containers..."
docker stop ryx-vllm 2>/dev/null || true
docker rm ryx-vllm 2>/dev/null || true

# Remove vLLM Docker images
echo "Removing vLLM Docker images..."
docker rmi $(docker images | grep vllm | awk '{print $3}') 2>/dev/null || true

# Remove vLLM models (34GB!)
echo "Removing vLLM model files (this will free 34GB)..."
sudo rm -rf /home/tobi/vllm-models

# Remove vLLM docker configs
echo "Removing vLLM Docker configs..."
rm -rf /home/tobi/ryx-ai/docker/vllm

echo "✅ vLLM removed completely!"

echo ""
echo "📥 PHASE 2: Download Ollama Models..."
echo "Run these commands manually (downloads take time):"
echo ""
echo "  ollama pull qwen2.5-coder:14b      # Coding (8GB)"
echo "  ollama pull mistral-nemo:12b       # Chat (7GB)"
echo "  ollama pull qwen2.5:1.5b           # Fast (1GB)"
echo "  ollama pull deepseek-r1:7b         # Reasoning (4GB)"
echo ""
echo "Total download: ~20GB"
echo ""
echo "⚙️  PHASE 3: Ollama is already configured with GPU support"
echo "Service: systemctl --user status ollama"
echo ""
echo "✅ Migration complete! Start downloading models now."
