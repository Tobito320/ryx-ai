# RYX RSI (Recursive Self-Improvement) Roadmap

## Current State: 45% Ready (up from 28%)

### ✅ Completed
- ✅ vLLM running with Qwen2.5-Coder-14B-AWQ
- ✅ SearXNG running for search  
- ✅ Search synthesis working (no more "0 tokens")
- ✅ `/style` command (normal/concise/explanatory/learning/formal)
- ✅ `/sources` command (show sources from last search)
- ✅ Ctrl+C handling (single=interrupt, double=exit)
- ✅ Style persistence across sessions
- ✅ Sources stored after search

### In Progress
- ⏳ Multi-agent parallel search (foundation created)
- ⏳ Agent rating system (metrics framework ready)
- ⏳ Remove remaining Ollama references

### Critical Issues Fixed
1. ~~Ollama references still in code~~ → vLLM wrapper handles this
2. ~~Search doesn't synthesize~~ → Working with synthesis
3. ~~No style system~~ → `/style` command added
4. ~~Ctrl+C handling broken~~ → Double-tap to exit

---

## Phase 1: Multi-Agent Search System (CURRENT FOCUS)

### Architecture
```
User Query: "What is hyprland?"
        ↓
┌─────────────────────────────────────────────────┐
│             SUPERVISOR (7B/8B model)            │
│  - Understands query                            │
│  - Dispatches to search agents                  │
│  - Synthesizes results based on /style          │
└─────────────────────────────────────────────────┘
        ↓ (parallel dispatch)
┌────────┬────────┬────────┬────────┬────────┐
│Agent 1 │Agent 2 │Agent 3 │Agent 4 │Agent 5 │
│1.5B/3B │1.5B/3B │1.5B/3B │1.5B/3B │1.5B/3B │
└────────┴────────┴────────┴────────┴────────┘
        ↓ (results + timing)
┌─────────────────────────────────────────────────┐
│             SUPERVISOR synthesizes              │
│  - Combines results                             │
│  - Applies /style (concise/explanatory/etc)    │
│  - Rates agent performance                      │
└─────────────────────────────────────────────────┘
        ↓
User gets answer (sources saved for /sources)
```

### Models to Load (vLLM multi-model)
- **Supervisor**: Qwen2.5-7B-Instruct (7B, fits in VRAM with agents)
- **Agents**: Qwen2.5-1.5B-Instruct × 5 (parallel, tiny footprint)
- **Coder**: Qwen2.5-Coder-14B (only loaded when needed for code tasks)

### Implementation Steps
1. [ ] Download smaller models for agents
2. [ ] Configure vLLM for multi-model serving
3. [ ] Create SearchAgent class (uses SearXNG + model)
4. [ ] Create SearchSupervisor class (dispatches, synthesizes)
5. [ ] Implement /style command (normal, concise, explanatory, learning, formal)
6. [ ] Implement /sources command (show sources from last search)
7. [ ] Implement agent rating system
8. [ ] Implement /metrics command

---

## Phase 2: Proper Ctrl+C Handling

### Requirements
- Single Ctrl+C: Interrupt current operation
- Double Ctrl+C (within 1s): Exit session
- Ctrl+R: Expand current step details

### Implementation
- Use signal handlers with timestamp tracking
- Async cancellation tokens for operations

---

## Phase 3: vLLM Multi-Model Setup

### Current: Single 14B model (24GB VRAM, 230W)
### Target: Multi-model with dynamic loading

```yaml
models:
  - name: supervisor
    model: Qwen/Qwen2.5-7B-Instruct
    max_model_len: 4096
    gpu_memory: 8GB
    
  - name: agent
    model: Qwen/Qwen2.5-1.5B-Instruct  
    max_model_len: 2048
    gpu_memory: 2GB
    
  - name: coder
    model: Qwen/Qwen2.5-Coder-14B-Instruct-AWQ
    max_model_len: 8192
    gpu_memory: 16GB
    load_on_demand: true
```

---

## Phase 4: Style System

### Available Styles
- `normal`: Balanced response
- `concise`: Shortest possible answer
- `explanatory`: Detailed with examples
- `learning`: Explains like a teacher
- `formal`: Professional/academic tone

### Persistence
- Saved to `~/.config/ryx/style.json`
- Survives session restarts

---

## Phase 5: Agent Rating System

### Metrics Tracked
- Response time (faster = better)
- Quality score (from supervisor evaluation)
- Error rate
- Success rate per task type

### Commands
- `/metrics`: Show agent performance
- Agent auto-replacement: Worst performing gets replaced by best

---

## Phase 6: Full RSI Loop

After search is working perfectly:
1. Benchmark system
2. Self-modification engine
3. Competitive analysis
4. Autonomous improvement loop

---

## Commands Reference

### New Commands to Add
- `/style <name>` - Set response style
- `/sources` - Show sources from last search
- `/metrics` - Show agent performance
- `/agents` - Show active agents and their ratings

### Keyboard Shortcuts
- `Ctrl+C` (single): Interrupt current operation
- `Ctrl+C` (double): Exit session
- `Ctrl+R`: Expand step details
