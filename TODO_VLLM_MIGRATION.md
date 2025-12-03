# vLLM Migration Status

## ✅ Completed

1. **vLLM Backend Setup**
   - ROCm Docker container running with qwen2.5-7b-gptq
   - SearXNG running for web search
   - OpenAI-compatible API on port 8001

2. **Removed Ollama Dependencies**
   - `configs/models.json` updated to use vLLM paths
   - `core/ryx_brain.py` - renamed `self.ollama` to `self.llm`
   - `core/ryx_brain.py` - ModelManager now uses vLLM models only
   - No more fallback to Ollama

3. **Search with Web Grounding**
   - SearXNG integration working
   - Automatic search detection for factual queries
   - Sources stored for `/sources` command
   - Style-aware synthesis (concise, explanatory, etc.)

4. **Session Features**
   - `/style` - Set response style (persisted)
   - `/sources` - Show last search sources
   - `show sources` - Natural language version
   - Double Ctrl+C to exit

## 🔄 In Progress

1. **Multi-Agent Search System** (`core/search_agents.py`)
   - Framework exists but not connected
   - Need to enable parallel agents for search

2. **Model Performance Metrics** (`/metrics`)
   - Track agent performance
   - Fire worst performers

## ⏳ TODO

1. **Download More Models for Multi-Agent**
   ```bash
   # Small models (1.5-3B) for agents
   huggingface-cli download Qwen/Qwen2.5-1.5B-Instruct-GPTQ-Int4 --local-dir ~/vllm-models/small/qwen2.5-1.5b
   huggingface-cli download TheBloke/Mistral-7B-Instruct-v0.2-GPTQ --local-dir ~/vllm-models/small/mistral-7b
   ```

2. **vLLM Multi-Model Support**
   - Current: vLLM serves ONE model at a time
   - Need: Either multiple vLLM instances or model switching

3. **Start/Stop Commands**
   - `ryx start vllm` - Start vLLM container
   - `ryx start searxng` - Start SearXNG container
   - `ryx stop all` - Stop all services

4. **Cleanup Command**
   - `/cleanup` - Remove dangling Docker images

5. **Benchmark System**
   - Test search quality
   - Test response accuracy
   - Compare model performance
