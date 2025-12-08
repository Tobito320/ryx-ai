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

---

## 🚨 SESSION 2025-12-08 (21:35 UTC) - CRITICAL FEEDBACK

### Tobi's Feedback - READ THIS FIRST

**Current State**: Ryx is ~10% as good as Claude Code CLI. NOT acceptable.

**Problems Identified**:
1. ❌ Ollama references still in codebase - WE USE VLLM NOT OLLAMA
2. ❌ RyxSurf is slow, not resource efficient
3. ❌ Top URL bar too tall, has useless buttons (home, star, reload)
4. ❌ Left sidebar too fat (should be 10-20% of screen, toggle-able)
5. ❌ Can't interact with websites sometimes
6. ❌ YouTube search hangs, doesn't load
7. ❌ New tab opens with unknown/no URL (looks bad)
8. ❌ Ryx not autonomous - needs explicit prompts

### PRIORITY 1 - RyxSurf Fixes (IMMEDIATE)

**Left Sidebar**:
- Make minimal, 10-20% screen width max
- Toggle-able (show/hide)
- Clean, no clutter

**Top URL Bar**:
- Make compact, minimal height
- Remove useless buttons (home, star, reload)
- Focus on URL input only

**Keyboard Shortcuts** (MUST WORK):
```
Ctrl+L          Focus URL bar, type to search
                - Type "youtube" → show youtube.com in suggestions
                - Press Enter → go to youtube.com directly
                - Settings option to disable auto-go-to-site
Ctrl+W          Close current tab
Ctrl+T          New tab + focus URL bar (Google search preferred)
Ctrl+↓/↑        Navigate between tabs (1st, 2nd, 3rd...)
                OR Ctrl+Shift+↓/↑ if conflicts
Ctrl+1-9        Jump to tab by number
```

**New Tab Behavior**:
- Show clean URL (google.com or blank)
- Auto-focus URL bar
- Ready to type immediately

### PRIORITY 2 - Make Ryx Autonomous

**Goal**: Say "resume work on ryxsurf" and Ryx does EVERYTHING:
- Finds files automatically
- Reads context it needs
- Makes changes
- Verifies changes work
- Continues to next task

**What Ryx Must Do Automatically**:
1. Explore codebase to understand structure
2. Find relevant files for the task
3. Read file contents for context
4. Plan the changes needed
5. Execute changes
6. Verify changes work
7. Self-heal if errors occur
8. Continue to next logical task

**Key Insight**: Claude Code CLI works because it:
- Has deep codebase understanding
- Uses RepoMap/tree-sitter for code structure
- Fuzzy matches for edits (diff_match_patch)
- Self-corrects on errors
- Maintains task context across turns

### PRIORITY 3 - Clean Up Ollama References

Files with Ollama references to fix:
- scripts/local_verify.sh
- scripts/system_diagnostics.py
- modes/session_mode.py
- modes/cli_mode.py
- tools/council.py
- docs/architecture/*.md
- README.md
- ryx_pkg/agents/*.py
- dev/experiments/*.py

**Rule**: Replace ALL Ollama with vLLM (localhost:8001)

### Repos to Study for Patterns

Located at `/home/tobi/cloned_repositorys/`:

**Priority 1 - Autonomous Coding**:
- **aider** - RepoMap, fuzzy edit matching, git-aware editing
- **SWE-agent** - Autonomous software engineering
- **OpenDevin** / **openhands-ai** - Multi-agent sandbox
- **gpt-engineer** - Codebase understanding
- **gpt-pilot** - Task decomposition, developer agent

**Priority 2 - Self-Healing**:
- **healing-agent** - Self-healing decorator pattern
- **SelfImprovingAgent** - Execute→Evaluate→Refine loop
- **self_improving_coding_agent** - Self-improvement patterns
- **RepairAgent** - Code repair patterns

**Priority 3 - Agent Orchestration**:
- **AutoGPT** - Autonomous goal decomposition
- **babyagi** - Task-driven autonomy
- **swarm** - Multi-agent handoffs
- **crewAI** - Role-based agents
- **langchain** / **langgraph** - Tool orchestration, state machines
- **autogen** - Multi-agent conversations

**Priority 4 - Browser Automation**:
- **browser-use** - AI browser automation
- **LaVague** - AI web agent
- **playwright-python** - Browser automation

**Priority 5 - Memory & Context**:
- **MemGPT** / **letta-code** - Long-term memory
- **anthropic-cookbook** - Claude patterns

**Other Useful**:
- **build-your-claude-code-from-scratch** - Claude Code architecture
- **AgentGPT** - Self-improvement loops
- **devika** - AI software engineer
- **plandex** - Coding with planning
- **pr-agent** - PR review patterns
- **dgm** - Unknown (check it)

### Ollama→vLLM Migration TODO

**Core files with Ollama code**:
- [ ] `core/startup_optimizer.py` - Ollama references
- [ ] `core/ryx_engine.py` - Ollama references
- [ ] `core/embeddings.py` - Ollama references

**Mode files with Ollama code**:
- [ ] `modes/session_mode.py:648,656,663` - ollama list/pull commands
- [ ] `modes/cli_mode.py:65,73,508,525` - ollama list/pull commands

**Other files**:
- [ ] `scripts/local_verify.sh`
- [ ] `scripts/system_diagnostics.py`
- [ ] `tools/council.py`
- [ ] `README.md`
- [ ] `ryx_pkg/agents/orchestrator.py`
- [ ] `ryx_pkg/agents/worker_pool.py`
- [ ] `dev/experiments/*.py`

**Fix**: Replace all Ollama with vLLM API calls to localhost:8001

### The Autonomous Loop

```
1. Supervisor (Copilot CLI) gives Ryx a natural language prompt
   Example: "continue working on ryxsurf"

2. Ryx automatically:
   - Reads MISSION.md / TODO list
   - Explores codebase
   - Picks next task
   - Executes it
   - Verifies it works

3. If Ryx fails:
   - Ryx tries to self-heal (3 attempts)
   - If still fails, Supervisor improves Ryx's code
   - Then retry the task

4. If Ryx succeeds:
   - Continue to next task
   - Update progress

5. Repeat forever
```

### Technical Reminders

- **vLLM**: localhost:8001 (NOT Ollama 11434)
- **Model**: qwen2.5-coder-14b-awq for coding
- **Context**: 16K or 32K (16K is fine for most tasks)
- **GPU**: 90% max utilization (screen flickers above)
- **No FP8 KV cache on RDNA3** (causes crashes)

### What NOT to Do

1. ❌ Don't use Ollama - use vLLM
2. ❌ Don't do Ryx's work - prompt Ryx to do it
3. ❌ Don't give explicit file paths - Ryx finds them
4. ❌ Don't copy-paste code - understand WHY it works
5. ❌ Don't make RyxSurf slow - efficiency is critical

### Success Criteria

- [ ] Ryx works with "resume work on ryxsurf" prompt
- [ ] Ryx finds files automatically
- [ ] Ryx self-heals from errors
- [ ] RyxSurf sidebar is minimal (10-20% width)
- [ ] RyxSurf URL bar is compact
- [ ] All keyboard shortcuts work
- [ ] RyxSurf loads pages fast
- [ ] No Ollama references in code

---

**STATUS**: 🔴 NEEDS WORK - Ryx only 10% as good as Claude Code
**NEXT SESSION**: Focus on Ryx autonomy + RyxSurf UI fixes

