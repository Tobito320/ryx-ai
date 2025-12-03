# Ryx AI - Current Status

## ✅ Working Features

### vLLM Backend (7B Model)
- **Model**: Qwen2.5-7B-GPTQ
- **VRAM**: ~74% (~12GB) - down from 100% with 14B
- **Power**: ~54W idle - down from 230W
- **Speed**: ~33-45 tok/s

### Session Mode
- `ryx` launches interactive session
- Natural language queries work
- Double Ctrl+C to exit
- Style system (`/style concise|explanatory|learning|formal|normal`)
- Sources tracking (`/sources` after search)

### Search Integration
- Questions like "what is hyprland" auto-search via SearXNG
- Greetings/smalltalk skip search
- Search results synthesized with style-appropriate response
- Sources stored for `/sources` command

### Docker Services
- `ryx-vllm` - vLLM server on port 8001
- `ryx-searxng` - SearXNG on port 8888
- Can be started with: `cd docker/vllm && docker-compose up -d`

## ⚠️ Needs Work

### Multi-Agent System (Partially Implemented)
- `search_agents.py` exists but not integrated
- Agents use same model (need smaller models for parallel work)
- Supervisor pattern not connected to session loop

### Model Management
- Currently only serves ONE model at a time
- Need to implement model hot-swapping or multi-model serving
- Small models (1.5B, 3B) downloaded but not used

### Code Task Handling
- Phase system (EXPLORE→PLAN→APPLY→VERIFY) exists
- Test verification is too aggressive (fails on simple files)
- Rollback loops instead of fixing in place

### RyxHub
- Docker container exists but not integrated
- Need `ryx start ryxhub` command

## 📋 Next Steps

1. **Multi-Agent Search** (Priority)
   - Use small models (1.5B/3B) for parallel search agents
   - Supervisor (7B) synthesizes results
   - Implement agent rating/firing system

2. **Code Task Improvements**
   - Skip tests for simple file creation
   - Better verification logic
   - Fix-in-place instead of rollback

3. **Service Management**
   - `ryx start vllm` / `ryx stop vllm`
   - `ryx start ryxhub` / `ryx start searxng`

4. **Benchmark System**
   - Implement RSI benchmarks
   - Track performance over time
   - Auto-improvement loop

## 🔧 Configuration

Models available in `/home/tobi/vllm-models/`:
- `powerful/general/qwen2.5-14b-gptq`
- `powerful/coding/qwen2.5-coder-14b-gptq`
- `medium/general/qwen2.5-7b-gptq` ← **CURRENT**
- `medium/general/mistral-7b-gptq`
- `medium/coding/qwen2.5-coder-7b-gptq`
- `small/general/qwen2.5-3b`
- `small/general/phi-3.5-mini`
- `small/coding/qwen2.5-coder-1.5b`
