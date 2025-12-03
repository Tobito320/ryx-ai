#!/bin/bash
# Test vLLM server with AMD GPU (RX 7800 XT)

echo "╔══════════════════════════════════════════════════════════╗"
echo "║           RYX AI - vLLM Test Script                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check model
MODEL_DIR="$HOME/vllm-models/qwen2.5-coder-14b-awq"
echo "🔍 Checking model..."

if [ ! -d "$MODEL_DIR" ]; then
    echo "❌ Model not found at $MODEL_DIR"
    echo "   Run the model download first."
    exit 1
fi

MODEL_SIZE=$(du -sh "$MODEL_DIR" 2>/dev/null | cut -f1)
echo "   Model size: $MODEL_SIZE"

# Check if model files exist
if [ ! -f "$MODEL_DIR/config.json" ]; then
    echo "❌ Model incomplete - config.json not found"
    exit 1
fi

# Check for model weights
WEIGHT_COUNT=$(ls "$MODEL_DIR"/*.safetensors 2>/dev/null | wc -l)
if [ "$WEIGHT_COUNT" -eq 0 ]; then
    echo "❌ Model incomplete - no .safetensors files found"
    echo "   Model may still be downloading..."
    exit 1
fi
echo "   Weight files: $WEIGHT_COUNT"
echo "✅ Model looks complete"
echo ""

# Start vLLM
echo "🚀 Starting vLLM container..."
cd /home/tobi/ryx-ai/docker/vllm

# Stop existing container
docker compose down 2>/dev/null

# Start fresh
docker compose up -d

echo ""
echo "⏳ Waiting for vLLM to initialize (this may take 1-2 minutes)..."
echo "   View logs: docker logs -f ryx-vllm"
echo ""

# Wait and check health
for i in {1..30}; do
    sleep 5
    HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null)
    if [ "$HEALTH" = "OK" ] || [ ! -z "$HEALTH" ]; then
        echo "✅ vLLM is healthy!"
        break
    fi
    echo "   Waiting... ($i/30)"
done

# Final check
HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null)
if [ -z "$HEALTH" ]; then
    echo "⚠️ vLLM may still be starting. Check logs:"
    echo "   docker logs -f ryx-vllm"
else
    echo ""
    echo "✅ vLLM is running!"
    echo ""
    echo "🧪 Testing inference..."
    
    # Quick test
    RESPONSE=$(curl -s http://localhost:8000/v1/chat/completions \
        -H "Content-Type: application/json" \
        -d '{
            "model": "/models/qwen2.5-coder-14b-awq",
            "messages": [{"role": "user", "content": "Say hello in Python code"}],
            "max_tokens": 50
        }' 2>/dev/null)
    
    if echo "$RESPONSE" | grep -q "content"; then
        echo "✅ Inference working!"
        echo ""
        echo "Response:"
        echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])" 2>/dev/null || echo "$RESPONSE"
    else
        echo "⚠️ Inference test failed"
        echo "Response: $RESPONSE"
    fi
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "Commands:"
echo "  ryx status              - Check service status"
echo "  ryx benchmark run       - Run coding benchmark"
echo "  docker logs -f ryx-vllm - View vLLM logs"
echo "═══════════════════════════════════════════════════════════"
