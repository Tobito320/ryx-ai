# RYX AI - SELF-IMPROVEMENT CYCLE
**Created**: 2025-12-10
**Purpose**: Ryx improves itself autonomously. Copilot only intervenes when Ryx fails.

---

## 🔄 THE CYCLE

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      RYX SELF-IMPROVEMENT LOOP                          │
│                                                                         │
│  ┌─────────────┐                                                        │
│  │  BENCHMARK  │◄─────────────────────────────────────┐                 │
│  │   BEFORE    │                                      │                 │
│  └──────┬──────┘                                      │                 │
│         │                                             │                 │
│         ▼                                             │                 │
│  ┌─────────────────────────────────────────────┐      │                 │
│  │  RYX SELF-ANALYSIS                          │      │                 │
│  │  - Read reference repos (aider, SWE-agent)  │      │                 │
│  │  - Identify improvement to make             │      │                 │
│  │  - Create implementation plan               │      │                 │
│  └──────┬──────────────────────────────────────┘      │                 │
│         │                                             │                 │
│         ▼                                             │                 │
│  ┌─────────────────────────────────────────────┐      │                 │
│  │  RYX ATTEMPTS (3 tries)                     │      │                 │
│  │  Try 1 → Fail? → Try 2 → Fail? → Try 3     │      │                 │
│  └──────┬──────────────────────────────────────┘      │                 │
│         │                                             │                 │
│         ├── Success ─────────────────────────────────►│                 │
│         │                                             │                 │
│         ▼ (Failed 3x)                                 │                 │
│  ┌─────────────────────────────────────────────┐      │                 │
│  │  CYCLE 2: RYX TRIES AGAIN (3 more tries)    │      │                 │
│  │  With error reflection from previous fails  │      │                 │
│  └──────┬──────────────────────────────────────┘      │                 │
│         │                                             │                 │
│         ├── Success ─────────────────────────────────►│                 │
│         │                                             │                 │
│         ▼ (Failed 6x total)                           │                 │
│  ┌─────────────────────────────────────────────┐      │                 │
│  │  CYCLE 3: RYX FINAL ATTEMPTS (3 more)       │      │                 │
│  │  With accumulated error patterns            │      │                 │
│  └──────┬──────────────────────────────────────┘      │                 │
│         │                                             │                 │
│         ├── Success ─────────────────────────────────►│                 │
│         │                                             │                 │
│         ▼ (Failed 9x total)                           │                 │
│  ┌─────────────────────────────────────────────┐      │                 │
│  │  COPILOT INTERVENTION                       │      │                 │
│  │  - Analyze WHY Ryx failed                   │      │                 │
│  │  - Fix Ryx's code (NOT do Ryx's task)       │      │                 │
│  │  - Improve: prompts, logic, self-healing    │      │                 │
│  │  - Ryx tries again from start               │      │                 │
│  └──────┬──────────────────────────────────────┘      │                 │
│         │                                             │                 │
│         ▼                                             │                 │
│  ┌─────────────┐                                      │                 │
│  │  BENCHMARK  │──── Better? ─── Yes ────────────────►│                 │
│  │   AFTER     │                                      │                 │
│  └──────┬──────┘                                      │                 │
│         │                                             │                 │
│         └── Worse/Same ──► ROLLBACK + Log failure     │                 │
│                                                       │                 │
└───────────────────────────────────────────────────────┴─────────────────┘
```

---

## 📊 BENCHMARK SYSTEM (Points, Not Percentages)

### Scoring Categories

| Category | Max Points | How to Measure |
|----------|------------|----------------|
| **Edit Success** | 30 | 10 test edits, 3 points each |
| **File Discovery** | 20 | 10 file searches, 2 points each |
| **Task Completion** | 30 | 10 autonomous tasks, 3 points each |
| **Self-Healing** | 10 | Recovers from 5 induced errors, 2 points each |
| **Speed** | 10 | Bonus points for fast responses |
| **TOTAL** | 100 | |

### Comparison Baseline

| System | Expected Score |
|--------|---------------|
| **Claude Code CLI** | 95/100 (our target) |
| **Aider** | 85/100 |
| **Current Ryx** | ~40/100 (estimate) |
| **Goal Ryx** | 90/100 |

### Success/Failure Definition

- **SUCCESS**: Score AFTER > Score BEFORE (any improvement)
- **FAILURE**: Score AFTER <= Score BEFORE (same or worse)

---

## 📁 REFERENCE REPOS

Location: `/home/tobi/cloned_repositorys/`

| Repo | What Ryx Should Learn |
|------|----------------------|
| **aider** | RepoMap, fuzzy edit matching, SEARCH/REPLACE format |
| **SWE-agent** | Autonomous task execution patterns |
| **healing-agent** | @healing decorator, error context capture |
| **gpt-pilot** | Task decomposition, planning |
| **openhands-ai** | Multi-agent sandbox patterns |

---

## 🎯 IMPROVEMENT PRIORITIES

1. **Edit Quality** - Biggest pain point, most impact
2. **File Discovery** - Helps everything else
3. **Self-Healing** - Reduces manual intervention
4. **Task Planning** - Complex task breakdown
5. **Memory** - Persistent learning

---

## 📝 CYCLE LOG FORMAT

Each improvement attempt is logged to `data/improvement_logs/`:

```yaml
cycle_id: "2025-12-10_001"
timestamp: "2025-12-10T16:00:00Z"
task: "Improve edit accuracy using aider's fuzzy matching"
source_repo: "aider"

benchmark_before:
  edit_success: 18/30
  file_discovery: 14/20
  task_completion: 12/30
  self_healing: 4/10
  speed: 6/10
  total: 54/100

ryx_attempts:
  - attempt: 1
    action: "Added fuzzy line matching"
    result: "FAIL"
    error: "Import error in reliable_editor.py"
  - attempt: 2
    action: "Fixed import, retry fuzzy matching"
    result: "FAIL"
    error: "Matching too loose, wrong lines edited"
  - attempt: 3
    action: "Added line number tolerance ±3"
    result: "FAIL"
    error: "Still matching wrong anchor text"
  # ... up to 9 attempts across 3 cycles

copilot_intervention:
  reason: "Ryx failed 9x - lacks understanding of diff algorithms"
  fix: "Implemented Levenshtein distance for anchor matching"
  files_changed:
    - "core/reliable_editor.py"
    - "core/edit_strategies.py"

benchmark_after:
  edit_success: 24/30  # +6
  file_discovery: 14/20
  task_completion: 15/30  # +3
  self_healing: 4/10
  speed: 6/10
  total: 63/100  # +9 points

result: "SUCCESS"
improvement: "+9 points"
```

---

## 🚀 HOW TO START THE CYCLE

### Manual Start
```bash
ryx self-improve
```

### Or via Copilot
```
"Start the self-improvement cycle"
```

### Cycle Steps

1. **Ryx runs benchmark** → Establishes BEFORE score
2. **Ryx analyzes repos** → Picks one improvement
3. **Ryx attempts improvement** → 3 tries
4. **If fail** → 3 more tries (cycle 2)
5. **If fail** → 3 more tries (cycle 3)
6. **If fail 9x** → Copilot intervenes, fixes Ryx
7. **Ryx runs benchmark** → Establishes AFTER score
8. **Compare** → Log result
9. **Repeat** → Next improvement

---

## ⚠️ RULES FOR COPILOT

1. **NEVER do Ryx's task** - Only fix Ryx's code
2. **Brief explanations** - Show what you're fixing, don't over-explain
3. **Show results** - Before/after scores
4. **Log everything** - All interventions go to cycle log
5. **Prioritize** - Fix things that reduce future interventions

---

## 📈 GOAL

**Ryx takes over Copilot's job.**

Eventually:
- Ryx benchmarks itself
- Ryx identifies improvements
- Ryx implements improvements
- Ryx validates improvements
- Copilot only watches

---

## 🔧 CURRENT STATUS

**Date**: 2025-12-10
**GPU**: ✅ Working (AMD RX 7800 XT, 16GB VRAM)
**Multi-Model**: ✅ Working (3B + 14B in VRAM)
**Speed**: ✅ Fast (0.2s - 0.4s inference)
**Benchmark**: ⏳ Not run yet

---

## 📋 SESSION NOTES (2025-12-10)

### What Was Done This Session

1. **Fixed GPU acceleration** - ROCm/HIP now working
2. **Fixed multi-model loading** - 3B + 14B both stay in VRAM
3. **Optimized model config** - phi4 for reasoning, qwen-coder for code
4. **Fixed `ryx stop all`** - Now properly stops Ollama and frees RAM
5. **Updated model routing** - Code/reason keywords checked first
6. **Designed this cycle** - The self-improvement loop

### Models Installed

```
qwen2.5:3b          2GB   FAST/CHAT (always loaded)
qwen2.5-coder:14b   9GB   CODE (always loaded)
qwen2.5-coder:7b    5GB   FALLBACK
phi4                9GB   REASON (on demand)
nomic-embed-text    0.3GB EMBED
dolphin-mistral:7b  4GB   UNCENSORED
```

### Key Files Changed

- `core/model_router.py` - Model config + routing logic
- `core/ollama_client.py` - Model mappings
- `scripts/start_ollama.sh` - GPU startup script
- `ryx` - Stop all now stops Ollama

### Performance

- 3B inference: **0.2 seconds**
- 14B inference: **0.4 seconds**
- Model swap: **2-3 seconds** (rare, both usually loaded)

---

## 🔮 NEXT SESSION

When Tobi says "PHOENIX" or starts a new session:

1. Read this file + MISSION.md
2. Run the benchmark to establish baseline
3. Start the self-improvement cycle
4. Ryx tries to improve itself
5. Copilot intervenes only on 9x failure
