# Claude Opus - Ryx Quick Start Guide

**Current Status**: 28% ready for self-improvement | **Target**: 100%

**Your Mission**: Make Ryx a fully autonomous, self-improving agent system.

---

## 🎯 What You'll Build

An AI system that:
1. **Refines vague prompts** into precise agent instructions
2. **Assigns specialized agents** in parallel based on task complexity
3. **Aggregates results** from multiple agents intelligently
4. **Measures performance** with benchmarks
5. **Learns from failures** and improves automatically
6. **Improves itself** by testing changes before deploying

**Not** a coding-focused system. **Focus on search + analysis + orchestration.**

---

## 📁 Codebase Layout

```
ryx-ai/
├── core/
│   ├── ryx_brain.py              ← Main entry point (session mode)
│   ├── supervisor.py             ← Needs work: should refine prompts
│   ├── agents/
│   │   ├── base.py              ← Agent base class
│   │   ├── operator.py          ← Individual agent implementations
│   │   └── supervisor.py        ← Council coordinator
│   ├── search_agents.py         ← Multi-agent search (partially done)
│   ├── vllm_client.py           ← vLLM interface (working)
│   ├── docker_services.py       ← Service management (needs work)
│   └── benchmarks/              ← Metrics system (empty, needs build)
├── configs/
│   ├── models.json              ← Model registry
│   └── services.json            ← Docker service configs
├── data/
│   ├── session_state.json       ← Session persistence
│   ├── model_metrics.json       ← Performance tracking
│   └── benchmarks/              ← Benchmark results
├── docker/
│   ├── vllm/                    ← vLLM container
│   ├── searxng/                 ← Search engine container
│   └── ryxhub/                  ← Web interface container
└── TODO_COMPREHENSIVE.md        ← 11-phase roadmap (your guide)
```

---

## 🚀 Key Priorities (Week 1-2)

### Priority 1: Supervisor Prompt Refinement
**File**: `core/supervisor.py`

Current: Supervisor just passes user input to agents as-is.

Needed:
```python
class Supervisor:
    async def refine_prompt(self, user_prompt: str) -> str:
        """
        Turn vague prompt into precise agent instruction.
        Example:
          Input: "what is ipv6"
          Output: "Search for IPv6 definition, explain it in 2-3 sentences, 
                   include key differences from IPv4"
        """
        pass
```

### Priority 2: True Async Multi-Agent Execution
**File**: `core/agents/supervisor.py`

Current: Agents run sequentially.

Needed:
```python
async def assign_and_execute(self, task: str) -> AgentResult:
    """
    1. Classify task complexity (simple/medium/complex)
    2. Select N agents based on complexity
    3. Execute ALL agents in parallel (asyncio.gather)
    4. Aggregate results by quality score
    """
    pass
```

### Priority 3: Benchmark System
**Directory**: `core/benchmarks/`

Current: No benchmarks exist.

Needed:
```
50 test questions:
- 15 educational (axioms, definitions, theories)
- 15 technical (how-to, analysis)
- 10 factual (facts, statistics)
- 10 synthesis (combine concepts)

Metrics per query:
- Response correctness (%)
- Speed (ms)
- Token usage
- Hallucination score
- Agent performance (which agents helped?)
```

---

## 🔧 How to Approach This

### Step 1: Read & Understand
- [ ] Read `TODO_COMPREHENSIVE.md` entirely
- [ ] Read `STRUCTURE.md` (architecture overview)
- [ ] Check `configs/models.json` (available models)
- [ ] Trace a search query: `ryx` → `ryx_brain.py` → `search_agents.py`

### Step 2: Set Up Local Testing
```bash
cd /home/tobi/ryx-ai

# Start services
ryx start

# Run with debug mode (when implemented)
ryx --debug "what is ipv6"

# Check metrics
ryx /metrics
```

### Step 3: Implement Phase 1 (Multi-Agent Council)

**Week 1 Tasks**:
1. [ ] Add prompt refinement to supervisor
2. [ ] Implement async agent assignment
3. [ ] Add result aggregation logic
4. [ ] Create benchmark framework
5. [ ] Run first benchmark (baseline)
6. [ ] Fix obvious bugs (unclosed sessions, timeouts)

**Week 2 Tasks**:
1. [ ] Test with 50 benchmark questions
2. [ ] Measure baseline metrics
3. [ ] Implement alternative strategy generation
4. [ ] Add failure classification
5. [ ] Build model rating system

---

## 📊 What Good Looks Like

### Before (Current State)
```
User: "what is ipv6"
↓
Supervisor (no refinement) passes straight to agents
↓
Agents run one-by-one
↓
First agent finishes, returns result
↓
Response: Hallucinated, missing context
Time: 15s
Quality: 50/100
```

### After (Phase 1 Complete)
```
User: "what is ipv6"
↓
Supervisor refines: "Search for IPv6 definition, include key differences 
                     from IPv4, explain in 2-3 sentences, cite sources"
↓
Supervisor assigns: Task is "medium" complexity → use 3 agents
↓
All 3 agents run in parallel: SearXNG, Wikipedia, Technical Docs
↓
Results aggregated: Best answer chosen, hallucination checked
↓
Response: Accurate, cited, complete
Time: 3s
Quality: 85/100
```

---

## 🔑 Key Files to Modify

### Core Agent System
- `core/supervisor.py` - Add prompt refinement + agent assignment
- `core/agents/operator.py` - Make agents proper async
- `core/search_agents.py` - Parallelize search execution

### Benchmarking
- `core/benchmarks/__init__.py` - Create framework
- `core/benchmarks/questions.json` - 50 test questions
- `core/benchmarks/scorer.py` - Calculate metrics

### Infrastructure
- `core/docker_services.py` - Add service lifecycle commands
- `ryx` (CLI entry point) - Add new commands
- `configs/services.json` - Service definitions

---

## 💡 Quick Reference

### Model Selection
- **Supervisor**: Mistral-7B or Qwen-7B (decision making)
- **Search Agents**: 1.5B-3B (lightweight, parallel, 5x agents)
- **Analysis Agents**: 3B-7B (reading, comprehension)
- **Coding Agents**: 7B-14B (only when explicitly asked, lower priority)

### Async Pattern
```python
# Always use this pattern for parallel agent execution
results = await asyncio.gather(
    agent_a.execute(task),
    agent_b.execute(task),
    agent_c.execute(task),
    return_exceptions=True  # Don't crash if 1 agent fails
)

# Filter out failures
valid_results = [r for r in results if not isinstance(r, Exception)]
```

### Benchmarking Template
```python
benchmark = {
    "question": "What is IPv6?",
    "expected_answer": "...",
    "category": "technical",
    "ground_truth": ["IPv6 is...", "It uses 128-bit addresses"],
    "sources": ["rfc", "wikipedia"]
}

score = await evaluate(
    response=agent_response,
    benchmark=benchmark,
    metrics=["accuracy", "hallucination", "completeness"]
)
```

---

## ⚠️ Common Pitfalls to Avoid

1. **Don't block on vLLM startup**
   - Load model async, don't wait for it
   - Use timeout: 60s max

2. **Don't run agents sequentially**
   - Use `asyncio.gather()` for all parallel tasks
   - Set per-agent timeout (30s default)

3. **Don't forget error handling**
   - If 1 agent fails, continue with others
   - Log failure for metrics
   - Return best partial result

4. **Don't hardcode decisions**
   - Use configuration files
   - Make everything environment-variable overrideable

5. **Don't measure before implementing**
   - First: Get system working
   - Then: Measure baseline
   - Then: Improve and compare

---

## 🎓 Learning Resources from Cloned Repos

**For Agent Patterns**: `self_improving_coding_agent/base_agent/`
- How to structure agent classes
- How to implement agent specialization
- Benchmark framework pattern

**For Error Handling**: `RepairAgent/repair_agent/`
- Error classification system
- Recovery strategies
- Rollback patterns

**For CLI Design**: `Aider/`
- Interactive session patterns
- Command structure
- User experience design

**For Orchestration**: `healing-agent/`
- Multi-component coordination
- State management between components
- Health check patterns

---

## 🧪 Testing Strategy

### Unit Tests
- Test supervisor prompt refinement separately
- Test agent assignment logic
- Test result aggregation

### Integration Tests
- Test full pipeline with 1 query
- Test with 5 parallel agents
- Test timeout handling

### Benchmark Tests
- Run 50-query benchmark
- Compare to baseline
- Track metrics per model/agent

### User Tests (After Phase 1)
- Have actual users test the system
- Collect feedback on hallucinations
- Test response styles (concise vs explanatory)

---

## 📈 Success Milestones

- **Day 3**: Prompt refinement working, can see supervisor decision-making
- **Day 5**: Multi-agent execution working in parallel, latency <10s
- **Day 7**: Benchmark system complete, baseline metrics established
- **Day 10**: Result aggregation smart (best answer chosen automatically)
- **Day 14**: Alternative strategy generation, error recovery working

---

## 🆘 If You Get Stuck

1. **Check `TODO_COMPREHENSIVE.md`** - Detailed specs for each phase
2. **Look at test data**: `data/benchmarks/` - See what's expected
3. **Debug mode**: Add `--debug` flag to see decision-making
4. **Check logs**: `tail -f logs/*.log`
5. **Inspect prompts**: Print what supervisor sends to agents
6. **Measure everything**: Add timing/token counts to trace issues

---

## 🚢 Deployment Readiness

When Phase 1 is complete, the system should:
- [ ] Not require manual vLLM start
- [ ] Not crash on bad input
- [ ] Not hallucinate on search queries
- [ ] Show decision-making in debug mode
- [ ] Have metrics dashboard (`/metrics` command)
- [ ] Support style customization (`/style` command)
- [ ] Save session state automatically

---

## 📞 What to Tell Tobi

After completing Phase 1:

> "Ryx can now refine vague prompts into precise instructions, assigns 3-5 specialized agents in parallel based on task complexity, aggregates results intelligently, and measures performance with a 50-question benchmark. Average latency improved from 15s to 3s. Hallucination rate dropped from 20% to <5%. The supervisor has decision-making transparency in debug mode."

---

**Good luck! You're building the foundation for a self-improving AI agent. 🚀**
