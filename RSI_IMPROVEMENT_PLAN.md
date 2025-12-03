# 🟣 RYX → RSI (Recursive Self-Improving) Agent Plan

> **Goal:** Transform Ryx into a fully autonomous self-improving agent
> **Status:** 85% ready → Target: 100%
> **Concept:** Recursive Self-Improving Agent (RSI) / Meta-Learning Agent

---

## ✅ Implementation Complete (as of Dec 3, 2024)

### Core RSI Components Built:

| Component | Files | Lines | Status |
|-----------|-------|-------|--------|
| **Benchmark System** | 6 | ~2000 | ✅ Complete |
| **Self-Healing** | 3 | ~850 | ✅ Complete |
| **Overseer** | 1 | ~450 | ✅ Complete |
| **Experience Memory** | 2 | ~450 | ✅ Complete |
| **RSI Loop** | 2 | ~550 | ✅ Complete |
| **Docker Services** | 3 | ~500 | ✅ Complete |
| **vLLM Client** | 1 | ~420 | ✅ Complete |
| **LLM Backend Abstraction** | 1 | ~250 | ✅ Complete |
| **Async Orchestrator** | 1 | ~450 | ✅ Complete |

### New in this Session:

1. **vLLM Running on AMD GPU**
   - ROCm 6.4.1 with vLLM 0.9.1
   - Qwen2.5-Coder-14B-AWQ loaded (~9.5GB VRAM)
   - Port 8001, health endpoint working
   - Benchmark: 2/2 coding tasks passed

2. **LLM Backend Abstraction** (`core/llm_backend.py`)
   - `VLLMBackend` - async vLLM with sync wrapper
   - `OllamaBackendWrapper` - backwards compatibility
   - `get_llm()` - auto-selects best backend

3. **Async Multi-Agent Orchestrator** (`core/orchestrator.py`)
   - `AsyncOrchestrator` - parallel worker execution
   - `SupervisorOrchestrator` - planning + delegation
   - Task dependencies support
   - Automatic retry with backoff

4. **Session Mode Improvements**
   - `/fix` command - self-healing on errors
   - `/memory` command - show experience stats
   - `/benchmark` command - quick benchmark access
   - vLLM integration working

### CLI Commands Added:

```bash
# Service Management
ryx start vllm         # Start GPU inference
ryx start ryxhub       # Start web dashboard  
ryx stop vllm          # Stop vLLM
ryx status             # Show all service status

# Benchmarking
ryx benchmark list     # List available benchmarks (35 problems)
ryx benchmark run      # Run a benchmark
ryx benchmark history  # Show past runs
ryx benchmark compare  # Compare two runs

# Self-Improvement
ryx rsi status         # Show RSI status
ryx rsi iterate        # Run one improvement iteration
ryx rsi loop [n]       # Run n improvement iterations
```

---

## 🐳 Docker Architecture

All heavy services run as Docker containers, started on demand:

```
┌─────────────────────────────────────────────────────────────┐
│                      RYX ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │   vLLM      │     │   RyxHub    │     │  RyxSurf    │   │
│  │  (ROCm)     │     │  (Web UI)   │     │ (Browser)   │   │
│  │  :8000      │     │  :5173      │     │  :9000      │   │
│  │  GPU Accel  │     │  Dashboard  │     │  Browsing   │   │
│  └──────┬──────┘     └──────┬──────┘     └──────┬──────┘   │
│         │                   │                   │           │
│         └───────────────────┴───────────────────┘           │
│                             │                               │
│                    ┌────────┴────────┐                      │
│                    │    Ryx CLI      │                      │
│                    │   (Native)      │                      │
│                    │   Always On     │                      │
│                    └─────────────────┘                      │
│                                                             │
│  Commands:                                                  │
│    ryx start vllm      - Start GPU inference               │
│    ryx start ryxhub    - Start Web UI                      │
│    ryx start ryxsurf   - Start browser agent (future)      │
│    ryx stop <service>  - Stop a service                    │
│    ryx status          - Show all service status           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Service Details:

| Service | Container | Port | Purpose | Start Command |
|---------|-----------|------|---------|---------------|
| vLLM | ryx-vllm | 8000 | GPU inference with ROCm | `ryx start vllm` |
| RyxHub | ryx-hub | 5173 | Web dashboard | `ryx start ryxhub` |
| RyxSurf | ryx-surf | 9000 | Browser automation | `ryx start ryxsurf` |
| SearXNG | ryx-searxng | 8888 | Privacy search | `ryx start searxng` |

---

## 📚 Repository Analysis Complete

### Repositories Analyzed:
1. **SelfImprovingAgent** - Simple generate→test→refine loop
2. **healing-agent** - Runtime exception catching + AI fix + hot reload
3. **RepairAgent** - AutoGPT-based code repair with ANTLR parsing
4. **dgm (Darwin Gödel Machine)** - Evolutionary self-improvement with benchmarks
5. **self_improving_coding_agent** - Full async agent with oversight system
6. **build-your-claude-code-from-scratch** - Clean Claude Code architecture
7. **Aider** - Production-grade code editing with RepoMap
8. **letta-code** - Skills-based agent with CLAUDE.md patterns

---

## 🎯 PHASE 1: Benchmark System (Week 1-2)
**Priority:** CRITICAL - Without this, we can't measure improvement

### Learning From: `self_improving_coding_agent/base_agent/src/benchmarks/`

```
core/benchmarks/
├── __init__.py
├── base.py              # BaseBenchmark class
├── coding_tasks.py      # Code generation benchmarks
├── fix_tasks.py         # Bug fixing benchmarks
├── planning_tasks.py    # Multi-step planning
├── tool_usage.py        # Tool calling accuracy
├── self_healing.py      # Recovery from errors
├── runner.py            # BenchmarkRunner
└── results/
    └── baseline.json    # Current scores
```

### Key Code to Adapt:
```python
# FROM: self_improving_coding_agent/base_agent/src/benchmarks/base.py
@dataclass
class Problem:
    problem_id: str
    statement: str
    answer: Any
    answer_discussion: str | None

@dataclass
class ProblemResult:
    problem_id: str
    score: float | None = None
    tokens_used: int | None = None
    wall_time: float | None = None
    timed_out: bool = False
```

### Tasks:
- [ ] Create `core/benchmarks/base.py` - Problem, ProblemResult, BaseBenchmark
- [ ] Create `core/benchmarks/coding_tasks.py` - 20 coding problems
- [ ] Create `core/benchmarks/runner.py` - Async benchmark execution
- [ ] Create `data/benchmarks/baseline.json` - Capture current performance
- [ ] Add `ryx ::benchmark run` command
- [ ] Add `ryx ::benchmark compare` command

---

## 🎯 PHASE 2: Async Agent System (Week 2-3)
**Priority:** CRITICAL - Current system is synchronous

### Learning From: `self_improving_coding_agent/base_agent/agent.py`

The key insight: Their Agent class uses asyncio for everything:
```python
# FROM: self_improving_coding_agent/base_agent/agent.py
async def exec(self, problem: str, timeout: int, cost_threshold: float):
    # Create monitors
    time_monitor_task = asyncio.create_task(time_monitor(...))
    cost_monitor_task = asyncio.create_task(cost_monitor(...))
    
    # Main execution with cancellation support
    done, pending = await asyncio.wait(
        task_list, return_when=asyncio.FIRST_COMPLETED
    )
```

### Tasks:
- [ ] Create `core/async_brain.py` - Async version of RyxBrain
- [ ] Create `core/async_executor.py` - Parallel tool execution
- [ ] Modify `core/session_loop.py` - Async main loop
- [ ] Add timeout/cost monitoring (inspired by their system)
- [ ] Add graceful shutdown with signal handlers

---

## 🎯 PHASE 3: Oversight System (Week 3-4)
**Priority:** HIGH - Autonomous monitoring

### Learning From: `self_improving_coding_agent/base_agent/src/oversight/overseer.py`

Key concepts:
1. **OverseerJudgement** - Structured analysis of agent state
2. **Notification System** - Can alert/redirect agents
3. **Force Cancellation** - Can kill stuck agents
4. **Dynamic Scheduling** - Next check based on progress

```python
# FROM: self_improving_coding_agent overseer.py
class OverseerJudgement(BaseModel):
    making_progress: bool
    is_looping: bool
    currently_running_agent: str
    needs_notification: bool
    force_cancel_agent: bool
```

### Tasks:
- [ ] Create `core/overseer.py` - Async oversight monitor
- [ ] Create `core/agent_health.py` - Health metrics tracking
- [ ] Add loop detection algorithm
- [ ] Add notification injection to agents
- [ ] Add forced cancellation support

---

## 🎯 PHASE 4: Self-Healing Exception Handler (Week 4-5)
**Priority:** HIGH - Core RSI capability

### Learning From: `healing-agent/healing_agent/`

Their key pattern - decorator that catches, fixes, and hot-reloads:
```python
# FROM: healing-agent/healing_agent.py
@healing_agent
def my_function():
    # If this crashes, AI analyzes, generates fix, 
    # replaces code in file, reloads module, retries
    pass
```

Key components:
- `exception_handler.py` - Captures full context (locals, globals, traceback)
- `ai_code_fixer.py` - Generates fix with LLM
- `code_replacer.py` - AST-safe code replacement
- Hot module reload with `importlib`

### Tasks:
- [ ] Create `core/healing/exception_handler.py` - Context capture
- [ ] Create `core/healing/ai_fixer.py` - AI-powered fix generation
- [ ] Create `core/healing/code_replacer.py` - Safe code replacement
- [ ] Create `core/healing/decorator.py` - @self_healing decorator
- [ ] Integrate with `core/error_classifier.py`

---

## 🎯 PHASE 5: Self-Modification Engine (Week 5-6)
**Priority:** CRITICAL - Core RSI capability

### Learning From: `dgm/self_improve_step.py`

Their pattern:
1. Diagnose problem (what's failing?)
2. Generate improvement (code patch)
3. Apply in Docker sandbox
4. Run benchmarks
5. Keep if better, rollback if worse

```python
# FROM: dgm/self_improve_step.py
def self_improve(
    parent_commit='initial',
    entry=None,  # The problem to improve on
    test_task_list=None,
):
    # Diagnose the problem
    problem_statement = diagnose_problem(entry, ...)
    
    # Generate improvement in sandboxed container
    container.exec_run("python /dgm/coding_agent.py --self_improve")
    
    # Run benchmarks
    run_harness_swe(...)
    
    # Return metadata with scores
```

### Tasks:
- [ ] Create `core/self_mod/sandbox.py` - Docker-based execution sandbox
- [ ] Create `core/self_mod/patcher.py` - Safe patch application
- [ ] Create `core/self_mod/rollback.py` - Git-based rollback
- [ ] Create `core/self_mod/validator.py` - Post-modification validation
- [ ] Create `core/self_mod/engine.py` - Self-modification orchestration

---

## 🎯 PHASE 6: Experience Memory & Learning (Week 6-7)
**Priority:** HIGH - Learn from past

### Current: Ryx has basic caching but no true learning

### New Architecture:
```
core/memory/
├── experience.py        # Experience replay buffer
├── patterns.py          # Pattern recognition
├── success_library.py   # Successful solutions
├── failure_library.py   # What didn't work
└── skills.py            # Learned skills (like letta-code)
```

### Tasks:
- [ ] Create `core/memory/experience.py` - Experience storage with embeddings
- [ ] Create `core/memory/patterns.py` - Pattern matching for similar problems
- [ ] Create `core/memory/skills.py` - Skill accumulation (inspired by letta)
- [ ] Modify `core/ryx_brain.py` - Query experience before new attempt
- [ ] Add experience-based temperature adjustment

---

## 🎯 PHASE 7: Competitive Analysis Agent (Week 7-8)
**Priority:** MEDIUM - Learn from competitors

### New Component:
```python
# core/competitive/analyzer.py
class CompetitorAnalyzer:
    """Browse competitor repos, extract features, identify gaps"""
    
    async def analyze_repo(self, repo_url: str) -> FeatureSet:
        # Clone/fetch repo
        # Parse code structure
        # Extract capabilities
        # Compare with ryx
        pass
    
    async def identify_gaps(self) -> List[Gap]:
        # What can they do that we can't?
        pass
    
    async def plan_implementation(self, gap: Gap) -> ImplementationPlan:
        # How to add this capability to ryx
        pass
```

### Targets to Monitor:
- Claude Code (anthropics)
- Aider
- Copilot CLI
- OpenHands/OpenDevin
- Cline

### Tasks:
- [ ] Create `core/competitive/analyzer.py`
- [ ] Create `core/competitive/feature_extractor.py`
- [ ] Create `core/competitive/gap_analysis.py`
- [ ] Add `ryx ::analyze-competitors` command

---

## 🎯 PHASE 8: Multi-Agent Orchestration (Week 8-9)
**Priority:** HIGH - Parallel execution

### Learning From: `build-your-claude-code-from-scratch/chapter7_sub_agent/`

Their pattern:
- Main orchestrator delegates to sub-agents
- Sub-agents have specific roles
- Async parallel execution

### Current Ryx: Has supervisor/operator pattern but synchronous

### Tasks:
- [ ] Make `core/agents/supervisor.py` fully async
- [ ] Add parallel operator execution
- [ ] Add inter-agent messaging
- [ ] Add load balancing
- [ ] Add failure isolation (one crash doesn't kill all)

---

## 🎯 PHASE 9: Full RSI Loop (Week 9-10)
**Priority:** CRITICAL - The main goal

### The Complete Loop:
```
┌─────────────────────────────────────────────────────────────┐
│                    RSI MAIN LOOP                            │
├─────────────────────────────────────────────────────────────┤
│  1. BENCHMARK                                               │
│     └─ Run all benchmarks, capture baseline                 │
│                                                             │
│  2. ANALYZE                                                 │
│     ├─ Where are we weakest?                               │
│     ├─ What do competitors do better?                       │
│     └─ What patterns from experience help?                  │
│                                                             │
│  3. PLAN IMPROVEMENT                                        │
│     ├─ Generate improvement hypothesis                      │
│     ├─ Create implementation plan                           │
│     └─ Estimate expected score improvement                  │
│                                                             │
│  4. IMPLEMENT (in sandbox)                                  │
│     ├─ Apply code changes                                   │
│     ├─ Run tests                                            │
│     └─ Validate no regressions                              │
│                                                             │
│  5. RE-BENCHMARK                                            │
│     └─ Run all benchmarks again                             │
│                                                             │
│  6. DECIDE                                                  │
│     ├─ If score > baseline: ACCEPT changes                  │
│     ├─ If score < baseline: REJECT, try alternative         │
│     └─ Update baseline if accepted                          │
│                                                             │
│  7. LOOP                                                    │
│     └─ Return to step 2                                     │
└─────────────────────────────────────────────────────────────┘
```

### Tasks:
- [ ] Create `core/rsi/loop.py` - Main RSI controller
- [ ] Create `core/rsi/hypothesis.py` - Improvement hypothesis generation
- [ ] Create `core/rsi/acceptance.py` - Accept/reject logic
- [ ] Add long-running process support
- [ ] Add checkpoint/resume capability

---

## 📊 Ollama vs vLLM Decision

### For RSI Multi-Agent System:

| Factor | Ollama | vLLM |
|--------|--------|------|
| **Parallel Requests** | Limited | Excellent |
| **Token Throughput** | ~30 tok/s | ~100+ tok/s |
| **Multi-GPU** | Limited | Full support |
| **Production Ready** | Yes | Yes |
| **Setup Complexity** | Easy | Medium |
| **Continuous Batching** | No | Yes |

### Recommendation:
**For Session Mode (user interaction):** Keep Ollama - simpler, works fine  
**For RSI Loop (autonomous improvement):** Switch to vLLM

```python
# Hybrid approach in core/model_router.py
class ModelRouter:
    def get_inference_backend(self, mode: str) -> Backend:
        if mode == "session":
            return OllamaBackend()
        elif mode == "rsi":
            return VLLMBackend()  # Higher throughput for parallel agents
```

---

## 📋 Master Checklist: What Ryx Needs

### 🔴 CRITICAL (Blocks RSI)
- [ ] Benchmark System
- [ ] Async Agent System
- [ ] Self-Modification Engine
- [ ] RSI Main Loop

### 🟡 HIGH (Severely Limits RSI)
- [ ] Oversight System
- [ ] Self-Healing Exception Handler
- [ ] Experience Memory
- [ ] Multi-Agent Orchestration

### 🟢 MEDIUM (Enhances RSI)
- [ ] Competitive Analysis
- [ ] vLLM Backend Option
- [ ] Advanced Pattern Recognition

---

## 🧪 Testing Strategy: ryxsurf

When you say "we're ready for ryxsurf", here's the criteria:

### Prerequisites:
1. ✅ Benchmark system working
2. ✅ RSI loop running for 10+ iterations without crash
3. ✅ At least 3 self-improvements accepted
4. ✅ No benchmark regression over 24 hours

### ryxsurf Test:
A real project where ryx must:
1. Understand requirements from human language
2. Explore existing codebase (if any)
3. Plan implementation
4. Execute with self-correction
5. Verify results
6. Handle "fix it please" style feedback

---

## 📅 Timeline Summary

| Week | Focus | Deliverable |
|------|-------|-------------|
| 1-2 | Benchmarks | `ryx ::benchmark` command working |
| 2-3 | Async | Full async agent execution |
| 3-4 | Oversight | Autonomous monitoring |
| 4-5 | Self-Healing | Exception auto-fix |
| 5-6 | Self-Mod | Safe code modification |
| 6-7 | Memory | Experience-based learning |
| 7-8 | Competitive | Gap analysis working |
| 8-9 | Multi-Agent | Parallel execution |
| 9-10 | RSI Loop | Full autonomous improvement |

**Total:** ~10 weeks to full RSI capability

---

## 🚀 Next Steps (Immediate)

1. **Today:** Start `core/benchmarks/base.py`
2. **This Week:** Complete benchmark system
3. **First Milestone:** Run baseline benchmarks, save to `data/benchmarks/baseline.json`

---

*This plan will be updated as we progress through each phase.*
*Document generated: 2024-12-03*
