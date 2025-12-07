# RYX AI - Mission Directive
**Created**: 2025-12-07
**Author**: Tobi
**Supervisor**: GitHub Copilot CLI

---

## 🎯 The Mission

Transform **Ryx AI** into a Jarvis-like autonomous agent that:
- Is **better than Claude Code CLI, Aider, Gemini CLI, Copilot CLI** - completely replaces them all
- Is **self-healing, autonomous, self-improving, self-aware**
- Knows Tobi's persona better than himself - predicts needs before being asked
- **Never asks for confirmation** - just does it with confidence
- Develops **RyxSurf** browser autonomously (Ryx codes RyxSurf, not the supervisor)

---

## 🔄 The Loop

```
Supervisor (Copilot CLI)
    ↓
Improves Ryx (extracts code from cloned repos)
    ↓
Ryx becomes smarter
    ↓
Ryx develops RyxSurf (via prompts, not direct coding)
    ↓
RyxSurf becomes better
    ↓
Supervisor notices Ryx lacks → back to step 1
```

**Key Rule**: The supervisor NEVER codes RyxSurf directly. The supervisor prompts Ryx to do it. If Ryx fails, the supervisor improves Ryx first.

---

## 🌐 RyxSurf Goals

Replace **Zen Browser + Firefox** completely:
- Session management (remember everything)
- Smart automatic tab unloading (more efficient than all browsers)
- Works perfectly WITHOUT AI (fast, lightweight)
- **AI Layer 1**: Small model for smart browser features (toggle on/off)
- **AI Layer 2**: Big model in sidebar for complex tasks (toggle on/off)
- Extremely fast startup, efficient memory usage
- Keyboard-first (Hyprland/vim style)

---

## 📚 Resource Repositories

Located at `/home/tobi/cloned_repositorys/`:

| Repo | Extract For |
|------|-------------|
| **aider** | Git-aware editing, minimal diffs, RepoMap, coder strategies |
| **build-your-claude-code-from-scratch** | Claude Code architecture |
| **healing-agent** | Self-healing decorator, error context capture |
| **SelfImprovingAgent** | Execute→Evaluate→Refine loop |
| **swarm** | Multi-agent orchestration |
| **AutoGPT** | Autonomous goal decomposition |
| **babyagi** | Task-driven autonomy |
| **SWE-agent** | Software engineering patterns |
| **OpenDevin** | Sandbox execution |
| **MemGPT/letta-code** | Long-term memory |
| **langgraph** | State machines for agents |
| **gpt-engineer** | Codebase understanding |
| **AgentGPT** | Self-improvement loops |
| **langchain** | Tool orchestration |
| **crewAI** | Role-based agents |
| **playwright-python** | Browser automation |
| **LaVague** | AI web agent |
| **RepairAgent** | Code repair patterns |

**Rule**: Can take 100% of code from these repos. Personal hobby project, no commercial use ever.

---

## 🧠 Ryx Personality

- Knows Tobi's preferences (keyboard > mouse, vim keybinds, dark themes)
- Learns patterns over time (UserPersona)
- Predicts intent before asked
- Takes action, doesn't explain
- Concise responses
- German/English bilingual
- Self-heals from errors (3 retries with reflection)

---

## ⚡ Technical Stack

- **OS**: Arch Linux + Hyprland
- **GPU**: AMD RX 7800 XT (16GB VRAM, ROCm)
- **Inference**: vLLM at localhost:8001
- **Models**: 
  - Fast: qwen2.5-7b-awq (browser AI layer 1)
  - Coding: qwen2.5-coder-14b-awq (Ryx main, RyxSurf development)
- **Browser Engine**: WebKitGTK 6.0 (GTK4)

---

## 🚫 What NOT To Do

1. ❌ Don't ask Tobi for permission - just do it
2. ❌ Don't code RyxSurf directly - prompt Ryx to do it
3. ❌ Don't copy-paste blindly - understand WHY the code works
4. ❌ Don't write bad code - aim for genius-level quality
5. ❌ Don't make things slow - efficiency is critical

---

## ✅ What TO Do

1. ✅ Extract patterns from cloned repos
2. ✅ Implement into Ryx core
3. ✅ Test by prompting Ryx to do tasks
4. ✅ If Ryx fails, improve Ryx first
5. ✅ Clone more repos if needed
6. ✅ Make Ryx better than Claude Code CLI

---

## 📊 Success Metrics

- [ ] Ryx can autonomously complete coding tasks
- [ ] Ryx self-heals from errors without human intervention
- [ ] Ryx predicts what Tobi wants
- [ ] RyxSurf replaces Zen Browser + Firefox
- [ ] RyxSurf works perfectly without AI
- [ ] RyxSurf AI layers can be toggled independently
- [ ] No need for Claude Code CLI, Aider, or any other tool

---

## 📝 Session Log

### Session 2025-12-07 (22:24 UTC) - CONTINUED

**Accomplished:**
- ✅ Fixed vLLM FP8 crash (RDNA3 doesn't support fp8e4nv)
- ✅ Created `core/auto_context.py` - automatic file discovery
- ✅ Enhanced DirectExecutor with keyword-based context detection
- ✅ Fixed literal `\n` handling in edit parsing
- ✅ Ryx added ZOOM action to ryxsurf agent
- ✅ Ryx added HintMode import and instance to browser.py
- ✅ Ryx implemented `_hint_mode()` method with JS injection
- ✅ Smart truncation for large files (1800+ lines)
- ✅ Prioritized term extraction (specific terms like _hint_mode first)
- ✅ Ryx added `_summarize_page()` method with callback
- ✅ Ryx added `_dismiss_popup()` with comprehensive selectors
- ✅ Improved system prompt to prevent LLM hallucination

**Solved Issues:**
- CODE_TASK now uses auto-context path (bypasses old approval system)
- Large files (browser.py 69KB) now correctly extract relevant sections
- Search terms with underscores now properly matched

**RyxSurf Features Added by Ryx:**
- `_hint_mode()` - Keyboard link navigation (Super+f)
- `_summarize_page()` - Get page text for AI summary
- `_dismiss_popup()` - Remove modals/cookies/overlays + restore scroll

**GPU Config:**
- vLLM: 92% memory utilization, 16K context
- Model: qwen2.5-coder-14b-awq
- Idle: 3% GPU, 15.3GB VRAM used (spikes during inference)

**Next Steps:**
1. Wire keybinds for new methods (Super+a for summarize, Super+x for dismiss)
2. Integrate AI summarization with vLLM
3. Add Firefox extension support
4. Extract self-healing patterns from healing-agent repo

---

**Status**: 🟢 ACTIVE - Ryx autonomously developing RyxSurf!
**Supervisor**: Taking over. Tobi can rely on me.
