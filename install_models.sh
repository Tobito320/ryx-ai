#!/bin/bash
# Ryx AI V2 - Model Installation Script
# Installs and verifies all required AI models

set -e

echo "🤖 Ryx AI V2 - Model Installation"
echo "================================="
echo ""

# Check Ollama
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama not installed"
    echo "Install with: curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
fi

echo "✅ Ollama found"
echo ""

# Check if Ollama is running
if ! ollama list &> /dev/null; then
    echo "⚠️  Ollama service not running"
    echo "Starting Ollama..."
    ollama serve &
    sleep 3
fi

# Model tiers for V2
declare -A models=(
    ["qwen2.5:1.5b"]="Tier 1 - Ultra Fast (Always Loaded)"
    ["deepseek-coder:6.7b"]="Tier 2 - Balanced (On-Demand)"
    ["qwen2.5-coder:14b"]="Tier 3 - Powerful (Rare Use)"
)

# Check and install models
for model in "${!models[@]}"; do
    description="${models[$model]}"
    echo "📦 Checking $model - $description"

    if ollama list | grep -q "^$model"; then
        echo "   ✅ Already installed"
    else
        echo "   📥 Installing $model..."
        if ollama pull "$model"; then
            echo "   ✅ Installation successful"
        else
            echo "   ❌ Installation failed"
            exit 1
        fi
    fi
    echo ""
done

# Test each model
echo "🧪 Testing Models"
echo "================="
echo ""

for model in "${!models[@]}"; do
    echo "Testing $model..."

    if echo "test" | ollama run "$model" &> /dev/null; then
        echo "✅ $model works"
    else
        echo "❌ $model failed"
        exit 1
    fi
done

echo ""
echo "✅ All models installed and tested successfully!"
echo ""
echo "Model Configuration:"
echo "  - Tier 1 (qwen2.5:1.5b): ~1.5GB VRAM, 50ms latency"
echo "  - Tier 2 (deepseek-coder:6.7b): ~4GB VRAM, 500ms latency"
echo "  - Tier 3 (qwen2.5-coder:14b): ~9GB VRAM, 2000ms latency"
echo ""
echo "🚀 Ready to use Ryx AI V2!"
