# RYX AI - Master Instruction File
**Last Updated**: 2025-12-08 23:10 UTC
**Author**: Tobi
**Supervisor**: GitHub Copilot CLI

---

## 🎯 Vision

**Ryx AI** = Local Jarvis that replaces Claude Code CLI, Copilot CLI, Aider, and all other AI coding tools.

**Core Principles**:
- **100% Local** - Ollama only, no cloud, no data leaving machine
- **Self-Healing** - 3 retries with reflection on errors
- **Self-Improving** - Extracts patterns from cloned repos, improves itself
- **Self-Aware** - Knows codebase, learns user patterns, predicts intent
- **Memory** - Remembers successes/failures, learns over time
- **Autonomous** - "resume work on X" triggers full autonomous loop
- **Better than Claude Code** - 1:1 UI/UX copy, same reliability

---

## 🔄 The Supervisor Loop

```
1. Supervisor (Copilot CLI) prompts Ryx: "continue working on ryxsurf"

2. Ryx autonomously:
   - Reads MISSION.md for context
   - Explores codebase (auto_context.py, repo_map.py)
   - Finds relevant files without being told
   - Plans changes (EXPLORE → PLAN → APPLY → VERIFY)
   - Executes changes
   - Verifies changes work

3. If Ryx fails:
   - Self-heal (3 attempts with error reflection)
   - If still fails → Supervisor improves Ryx's code
   - Retry task

4. If Ryx succeeds → Continue to next task

5. Repeat forever
```

**KEY RULE**: Supervisor NEVER codes RyxSurf directly. Supervisor improves Ryx, Ryx codes RyxSurf.

---

## ⚡ Technical Stack

### Backend: Ollama ONLY
- **URL**: localhost:11434
- **NO vLLM** - Completely removed
- **GPU**: AMD RX 7800 XT (16GB VRAM, ROCm)
- **Max GPU**: 90% (screen flickers above)
- **Context**: 12-16K optimal, up to 32K possible
- **CPU Offload**: Enabled for large contexts

### Models (Currently Installed)
```
mistral-nemo:12b    → Chat, 128K context, uncensored-friendly
dolphin-mistral:7b  → Fast chat, uncensored
qwen2.5:1.5b        → Ultra-fast intent detection
```

### Models (To Download)
```bash
ollama pull qwen2.5-coder:14b   # Main coding model (~8GB, ~5 min)
ollama pull qwen2.5-coder:7b    # Faster coding alternative
```

### Model Routing
| Task | Model | Speed |
|------|-------|-------|
| Intent Detection | qwen2.5:1.5b | 150 tok/s |
| Fast Chat | dolphin-mistral:7b | 100 tok/s |
| General Chat | mistral-nemo:12b | 60 tok/s |
| Coding | qwen2.5-coder:14b | 50 tok/s |
| RyxSurf AI | qwen2.5:1.5b | 150 tok/s |

### Performance Mode
Activate via: `Alt+Shift+P` → Select PERFORMANCE
Location: `~/.config/hypr/power-modes.sh`

---

## 🌐 RyxSurf Goals

Replace Firefox + Zen Browser completely.

### Design
- **Sidebar** (left): 10-20% width, toggle-able, minimal
- **URL bar** (top): Compact, no useless buttons (home, star, reload)
- **Both bars**: Toggle-able with keybind (hide both for fullscreen)
- **AI Sidebar**: Manual activation only (not always loaded)

### Behavior
- 90% usage WITHOUT AI - fast, lightweight, resource efficient
- AI loads ONLY on manual activation
- Session management that works (unlike Zen)
- Automatic tab unloading (memory efficient)

### Keybinds (MUST WORK)
```
Ctrl+L          Focus URL bar
Ctrl+T          New tab + focus URL bar
Ctrl+W          Close current tab
Ctrl+1-9        Jump to tab N
Ctrl+↓/↑        Navigate tabs
Ctrl+Shift+B    Toggle sidebar
Ctrl+Shift+U    Toggle URL bar
F11             True fullscreen (hide all)
```

### URL Bar Intelligence
- Type "youtube" → suggest youtube.com
- Press Enter → go directly
- Option to disable auto-complete

---

## 📚 Cloned Repositories

Location: `/home/tobi/cloned_repositorys/`

### Priority 1 - Autonomous Coding
| Repo | Extract |
|------|---------|
| **aider** | RepoMap, fuzzy edit, git-aware, SEARCH/REPLACE format |
| **SWE-agent** | Autonomous software engineering |
| **openhands-ai** | Multi-agent sandbox |
| **gpt-pilot** | Task decomposition |

### Priority 2 - Self-Healing
| Repo | Extract |
|------|---------|
| **healing-agent** | @healing decorator, error context capture |
| **SelfImprovingAgent** | Execute→Evaluate→Refine loop |
| **RepairAgent** | Code repair patterns |

### Priority 3 - Memory
| Repo | Extract |
|------|---------|
| **MemGPT/letta-code** | Long-term memory architecture |
| **anthropic-cookbook** | Claude patterns |

### Priority 4 - Browser
| Repo | Extract |
|------|---------|
| **browser-use** | AI browser automation |
| **LaVague** | AI web agent |
| **playwright-python** | Automation APIs |

**Rule**: Can take 100% of code. Personal hobby project, no commercial use.

---

## 🧠 Ryx Core Features

### Implemented
- ✅ **AutoContextBuilder** (`core/auto_context.py`): Auto file discovery
- ✅ **RepoMap** (`core/repo_map.py`): Codebase structure via tree-sitter
- ✅ **SelfHealer** (`core/self_healer.py`): AI-driven cache cleanup
- ✅ **SelfAnalyzer** (`core/self_improve.py`): Codebase analysis
- ✅ **ExperienceMemory** (`core/memory/experience.py`): Learn from past
- ✅ **PhaseExecutor** (`core/phases.py`): EXPLORE→PLAN→APPLY→VERIFY
- ✅ **OllamaClient** (`core/ollama_client.py`): Native async Ollama
- ✅ **ModelRouter** (`core/model_router.py`): Task → Model routing

### Needs Improvement
- ❌ File discovery not as good as Aider
- ❌ Edit matching not fuzzy (fails on whitespace)
- ❌ Self-healing doesn't capture enough context
- ❌ Memory not persistent across sessions
- ❌ Not truly autonomous yet

---

## 🎨 Ryx CLI Design

**Copy 1:1 from Claude Code CLI**:
- Same visual feedback (🤔 thinking, 🔍 searching, etc.)
- Same response streaming
- Same concise output
- Same tool calling patterns
- Same error recovery

---

## 🚫 Rules

1. ❌ Never ask Tobi for permission - just do it
2. ❌ Never use vLLM - Ollama only
3. ❌ Never code RyxSurf directly - prompt Ryx
4. ❌ Never exceed 90% GPU - causes screen flicker
5. ❌ Never create summary/planning files - work in memory
6. ❌ Never write dead code - only genius-level useful code

---

## ✅ Success Criteria

- [ ] "resume work on ryxsurf" works autonomously
- [ ] Ryx finds files without being told paths
- [ ] Ryx self-heals from errors (3 retries)
- [ ] RyxSurf replaces Firefox/Zen as daily driver
- [ ] RyxSurf works fast WITHOUT AI
- [ ] All keybinds work
- [ ] No need for Claude Code/Copilot/Aider

---

## 📊 Current Status

**Date**: 2025-12-09 00:45 UTC
**Phase**: Ryx Fully Operational with qwen2.5-coder:14b

### Completed This Session
- ✅ Ollama backend fully working (5 models loaded)
- ✅ vLLM references cleaned from ALL core files
- ✅ qwen2.5-coder:14b installed and configured as PRIMARY
- ✅ Model configs updated for optimal performance
- ✅ MISSION.md consolidated (single source of truth)
- ✅ Ryx tested with 14B coder - works great (18s/response)
- ✅ RyxSurf sidebar reduced to 180px
- ✅ RyxSurf URL bar made compact (no nav buttons)
- ✅ RyxSurf keybinds added: Ctrl+↓/↑, Ctrl+Shift+U, F11
- ✅ RyxSurf URL suggestions with quick domains

### Models Available
```
qwen2.5-coder:14b   → PRIMARY (coding, 18s latency)
qwen2.5-coder:7b    → Fast coding fallback
mistral-nemo:12b    → Chat, reasoning
dolphin-mistral:7b  → Uncensored
qwen2.5:1.5b        → Ultra-fast intent
```

### Performance
- 14B Coder: ~18 seconds per response, HumanEval 88%
- 7B Coder: ~8 seconds per response
- 1.5B Fast: ~1 second per response

### RyxSurf Keybinds Working
- Ctrl+L: Focus URL bar ✅
- Ctrl+T: New tab + focus ✅
- Ctrl+W: Close tab ✅
- Ctrl+1-9: Jump to tab ✅
- Ctrl+↓/↑: Navigate tabs ✅
- Ctrl+B: Toggle sidebar ✅
- Ctrl+Shift+U: Toggle URL bar ✅
- F11: True fullscreen ✅

### Next Actions
1. Test RyxSurf in real usage
2. Implement true autonomous loop for Ryx
3. Add @healing decorator from healing-agent
4. Add diff_match_patch fuzzy editing from Aider
5. Improve PhaseExecutor with memory persistence

