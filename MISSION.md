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
1. Integrate AI summarization with vLLM
2. Add Firefox extension support
3. Extract self-healing patterns from healing-agent repo
4. Continue polishing UI

---

### Session 2025-12-07 (23:25 UTC) - UI POLISH

**Accomplished:**
- ✅ Zen Browser style layout (sidebar left, URL top)
- ✅ Complete CSS overhaul - Dracula theme, polished
- ✅ Tab sidebar with header, scrollable list, + New Tab button
- ✅ Individual tab rows with close button (X appears on hover)
- ✅ Windowed by default (start_fullscreen: false)
- ✅ Fixed GTK4 CSS compatibility issues
- ✅ Super key shortcuts wired (Super+Shift+A, Super+x)

**RyxSurf Now Has:**
- Left sidebar with vertical tabs
- Top URL bar with security icon, tab count, bookmark button
- Keyboard navigation (Ctrl+t, Ctrl+w, Ctrl+l, etc.)
- AI features (Super+Shift+A summarize, Super+x dismiss popups)
- Middle-click to close tabs
- Tooltips on tab hover

---

### Session 2025-12-08 (00:00 UTC) - STRATEGY DECISION

**Decision: Option 3 - Fast Direct Work + Structured Ryx Training**

Tobi needs RyxSurf usable ASAP (work tomorrow). We chose:
1. **Tonight**: I (Copilot) fix UI directly - fast, quality
2. **Next sessions**: Structured Ryx training loop

**Why Option 3:**
- Tobi gets working browser tonight
- Ryx gets BETTER training via deliberate stress tests vs random prompts
- Complex edge cases properly solved, not half-fixed

**RyxSurf Design Goals:**
- Combine best of Zen (minimalism) + Firefox (reliable tab restore/session)
- Ultra-compact UI, keyboard-driven
- Resource efficient - replace Firefox, Chrome, Zen as daily driver
- Session management that WORKS (unlike Zen's issues)

**Ryx Training Loop (Next Sessions):**
1. File discovery stress tests (ambiguous prompts, nested dirs)
2. Edit precision tests (multi-line, indentation edge cases)
3. Context limit handling (huge files, prioritization)
4. Self-healing extraction from healing-agent repo
5. Memory persistence across sessions

**KEY RULE - Weakness Detection:**
When ANY weakness is found in Ryx:
1. Search GitHub for repos that excel at that weakness
2. Clone and analyze the code
3. Extract patterns and integrate into Ryx
4. Test until Ryx handles it better than Claude Code

**Repos to mine for patterns:**
- `aider` - Edit formats, file discovery
- `SWE-agent` - Autonomous coding
- `OpenHands` - Multi-agent orchestration  
- `healing-agent` - Self-healing patterns
- `mem0` / `Letta` - Memory management
- `browser-use` - Browser automation
- `Zen-Nebula` - UI/CSS patterns

---

**Status**: 🟢 ACTIVE - Building RyxSurf, Training Ryx
**Supervisor**: Tobi, I got you. You can rely on me.

## UI DESIGN TODO
- [ ] Redesign to ultra-minimal like Zen Browser
- [ ] Thinner sidebar (icon-only mode option)
- [ ] Compact URL bar
- [ ] Hide-able UI elements
- [ ] Clean Catppuccin/Nord theme

