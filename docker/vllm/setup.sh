#!/bin/bash
# vLLM Setup Script for RYX AI
# GPU: AMD RX 7800 XT (gfx1101 / RDNA3)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="$HOME/vllm-models"
HF_CACHE="$HOME/.cache/huggingface"
VLLM_IMAGE="rocm/vllm:rocm6.4.1_vllm_0.9.1_20250702"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║           RYX AI - vLLM ROCm Setup                       ║"
echo "║           GPU: AMD RX 7800 XT (16GB VRAM)                ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Create directories
mkdir -p "$MODELS_DIR"
mkdir -p "$HF_CACHE"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Cannot connect to Docker. Make sure Docker is running."
    exit 1
fi

# Check ROCm Docker image availability
echo "🔍 Checking vLLM ROCm Docker image..."
if ! docker images | grep -q "rocm/vllm"; then
    echo "📥 Pulling vLLM ROCm image (~15GB, this may take a while)..."
    docker pull "$VLLM_IMAGE"
else
    echo "✅ vLLM ROCm image already available"
fi

# Function to download a model
download_model() {
    local model_name=$1
    local local_name=$2
    
    echo ""
    echo "📥 Downloading $model_name..."
    docker run --rm \
        -v "$MODELS_DIR:/models" \
        -v "$HF_CACHE:/root/.cache/huggingface" \
        -e HF_HOME=/models \
        python:3.11-slim \
        bash -c "pip install -q huggingface_hub && huggingface-cli download $model_name --local-dir /models/$local_name"
}

# Download recommended models for RSI system
echo ""
echo "📦 Downloading models for RSI Multi-Agent System..."
echo ""
echo "Recommended models:"
echo "  1. Qwen2.5-Coder-14B-Instruct-AWQ (Main coding agent) - ~9GB"
echo "  2. Qwen2.5-7B-Instruct-AWQ (Fast agent) - ~4GB"
echo "  3. Qwen2.5-1.5B-Instruct (Supervisor routing) - ~2GB"
echo ""

read -p "Download all recommended models? [Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
    # AWQ quantized models (4-bit, fast)
    download_model "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ" "qwen2.5-coder-14b-awq"
    download_model "Qwen/Qwen2.5-7B-Instruct-AWQ" "qwen2.5-7b-awq"
    download_model "Qwen/Qwen2.5-1.5B-Instruct" "qwen2.5-1.5b"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 To start vLLM server:"
echo "   cd $VLLM_DIR && docker-compose up -d"
echo ""
echo "🔗 API will be available at:"
echo "   http://localhost:8000/v1"
echo ""
echo "📝 Test with:"
echo '   curl http://localhost:8000/v1/chat/completions \'
echo '     -H "Content-Type: application/json" \'
echo '     -d '"'"'{"model": "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ", "messages": [{"role": "user", "content": "Hello!"}]}'"'"
echo ""
