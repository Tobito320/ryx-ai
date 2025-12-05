# Multi-Model vLLM Setup

This guide explains how to run multiple vLLM models simultaneously for dynamic model switching without restarts.

## Overview

**What Changed:**
- vLLM **CAN** handle multiple requests like a pro ✅
- vLLM **CAN** serve multiple models, but requires multiple instances
- Each model runs in its own vLLM container on a different port
- The backend automatically routes requests to the correct instance
- **Zero manual intervention** - models switch dynamically!

## Architecture

```
┌─────────────────┐
│   RyxHub Web    │
│  (Port 8080)    │
└────────┬────────┘
         │
┌────────▼────────┐
│  Ryx Backend    │  Routes to correct instance
│  (Port 8420)    │
└────────┬────────┘
         │
    ┌────┴───────┬─────────────┐
    │            │             │
┌───▼───┐   ┌───▼───┐    ┌───▼───┐
│ vLLM  │   │ vLLM  │    │ vLLM  │
│ 7B    │   │ 7B    │    │ 3B    │
│ Gen   │   │ Code  │    │ Gen   │
│ 8001  │   │ 8002  │    │ 8003  │
└───────┘   └───────┘    └───────┘
```

## Quick Start

### 1. Start Multi-Model Instances

```bash
# Start all configured models at once
cd /home/tobi/ryx-ai
docker-compose -f docker/vllm/model-router.yml up -d

# Or start specific models
docker-compose -f docker/vllm/model-router.yml up -d vllm-medium-general vllm-medium-coding
```

This starts:
- **Port 8001**: Qwen 2.5 7B GPTQ (General) - Primary
- **Port 8002**: Qwen 2.5 Coder 7B GPTQ (Coding)
- **Port 8003**: Qwen 2.5 3B (General, lightweight)

### 2. Restart RyxHub with Rebuild

```bash
# This now automatically rebuilds the frontend!
ryx restart ryxhub
```

The restart command now:
- ✅ Stops all services
- ✅ Clears build caches
- ✅ Runs `npm run build` (full rebuild)
- ✅ Restarts API and frontend
- ✅ Zero manual steps!

### 3. Use Multiple Models

Go to RyxHub → Settings → Available Models

You'll now see:
- ✅ **3 models loaded** (green status)
- Switch between them instantly in chat
- No restarts needed!

## Configuration

### Adding More Models

Edit `/home/tobi/ryx-ai/docker/vllm/model-router.yml`:

```yaml
  # Add a new model instance
  vllm-powerful-general:
    image: vllm/vllm-openai:latest
    container_name: ryx-vllm-powerful-general
    environment:
      - MODEL=/models/powerful/general/qwen2.5-14b-gptq
      - CUDA_VISIBLE_DEVICES=0
    volumes:
      - /home/tobi/vllm-models:/models:ro
    ports:
      - "8004:8000"  # New port
    command: >
      --model /models/powerful/general/qwen2.5-14b-gptq
      --host 0.0.0.0
      --port 8000
      --gpu-memory-utilization 0.6
      --max-model-len 4096
      --trust-remote-code
```

Then register it in `/home/tobi/ryx-ai/ryx_pkg/core/model_router.py`:

```python
"/models/powerful/general/qwen2.5-14b-gptq": ModelInstance(
    model_id="/models/powerful/general/qwen2.5-14b-gptq",
    name="Qwen 2.5 14B GPTQ",
    base_url="http://localhost:8004",
    port=8004,
    category="general",
    size="powerful"
),
```

## GPU Memory Management

### Option 1: Time-share GPU (Recommended for 1 GPU)

Run models one at a time, switch dynamically:
- Start only the model you need: `docker-compose -f docker/vllm/model-router.yml up -d vllm-medium-general`
- Switch: Stop current, start new: `docker stop ryx-vllm-medium-general && docker-compose -f docker/vllm/model-router.yml up -d vllm-medium-coding`

### Option 2: Fractional GPU Memory (All models loaded)

Allocate memory fractions (requires enough VRAM):
```yaml
--gpu-memory-utilization 0.3  # 30% of VRAM per model
```

For 3 models on 16GB GPU:
- 3 × 30% = 90% VRAM used
- Each model gets ~5GB

### Option 3: Multi-GPU (If you have multiple GPUs)

Assign different GPUs:
```yaml
# Model 1
environment:
  - CUDA_VISIBLE_DEVICES=0

# Model 2
environment:
  - CUDA_VISIBLE_DEVICES=1
```

## Monitoring

### Check Model Status

```bash
# Check which models are running
docker ps | grep ryx-vllm

# Check model health
curl http://localhost:8001/health  # Medium general
curl http://localhost:8002/health  # Medium coding
curl http://localhost:8003/health  # Small general
```

### View Logs

```bash
# All models
docker-compose -f docker/vllm/model-router.yml logs -f

# Specific model
docker logs -f ryx-vllm-medium-general
```

## Performance Tips

1. **GPU Memory**: Adjust `--gpu-memory-utilization` based on your GPU:
   - 8GB VRAM: Use 0.4 per model (2 models max)
   - 16GB VRAM: Use 0.3 per model (3 models)
   - 24GB+ VRAM: Use 0.5+ per model (multiple models)

2. **Model Size**: Smaller models load faster and use less memory:
   - **3B models**: Fast, low memory (~3GB)
   - **7B models**: Balanced (~6GB)
   - **14B models**: Powerful, high memory (~12GB)

3. **Context Length**: Reduce `--max-model-len` if memory is tight:
   - 2048 tokens: ~30% less memory
   - 4096 tokens: Standard
   - 8192+ tokens: Large context, needs more VRAM

## Troubleshooting

### "Model not loading"

Check logs:
```bash
docker logs ryx-vllm-medium-general
```

Common issues:
- **OOM**: Reduce `--gpu-memory-utilization` or use smaller model
- **Model not found**: Check path in `/home/tobi/vllm-models`
- **Port conflict**: Ensure ports 8001-8003 are available

### "Backend shows 0 models"

1. Ensure multi-model containers are running:
   ```bash
   docker ps | grep ryx-vllm
   ```

2. Restart backend:
   ```bash
   ryx restart ryxhub
   ```

3. Check backend logs:
   ```bash
   tail -f /home/tobi/ryx-ai/data/ryxhub_api.log
   ```

### "Search not working"

Ensure SearXNG is running:
```bash
docker ps | grep searxng
docker-compose -f docker/searxng/docker-compose.yml up -d
```

## API Usage

The backend automatically routes to the correct instance:

```python
# POST /api/sessions/{session_id}/messages
{
  "content": "Explain Python async",
  "model": "/models/medium/coding/qwen2.5-coder-7b-gptq",  # Routes to port 8002
  "stream": false
}
```

Switch models mid-conversation:
```python
# First message to general model
{"content": "Hi!", "model": "/models/medium/general/qwen2.5-7b-gptq"}

# Next message to coding model
{"content": "Write a function", "model": "/models/medium/coding/qwen2.5-coder-7b-gptq"}
```

## Comparison: Single vs Multi-Model

| Feature | Single Instance | Multi-Model |
|---------|----------------|-------------|
| Models loaded | 1 | 3+ |
| Switch models | Restart (~2 min) | Instant |
| Memory usage | 1x model | N × model |
| Concurrent requests | ✅ Yes | ✅ Yes (per model) |
| Setup complexity | Simple | Moderate |

## Sources

Based on vLLM's architecture and community discussions:
- [vLLM Multi-Model Discussion](https://github.com/vllm-project/vllm/issues/3326)
- [vLLM Forums - Multiple Models](https://discuss.vllm.ai/t/run-multiple-models/1181)
- [Scalable Multi-Model LLM Serving](https://medium.com/@kimdoil1211/scalable-multi-model-llm-serving-with-vllm-and-nginx-f586912e17da)

---

**TL;DR:**
```bash
# Start all models
docker-compose -f docker/vllm/model-router.yml up -d

# Restart RyxHub (auto-rebuilds!)
ryx restart ryxhub

# Switch models instantly in the UI - no restarts!
```
