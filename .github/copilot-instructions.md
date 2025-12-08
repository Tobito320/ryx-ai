# Copilot Instructions for Ryx AI

## Project Overview

**Ryx AI** is a local, privacy-first AI terminal assistant for Arch Linux, designed to rival Claude Code CLI while being 100% self-hosted. It uses vLLM with AMD GPU (ROCm) for inference.

### Core Philosophy
- **Privacy first**: Everything runs locally, no data leaves the machine
- **Self-improving**: Ryx learns from mistakes and improves itself
- **Keyboard-driven**: Designed for Hyprland/tiling WM users who prefer keybinds
- **Minimal but powerful**: Clean UI, no bloat, maximum functionality

## Architecture

```
User → ryx CLI → Brain → vLLM (localhost:8001)
                    ↓
              Supervisor (7B) → Agents → Tools
                    ↓
              SearXNG (search) / Browser / Shell / Files
```

### Key Components
- **ryx**: Main bash entrypoint (`/home/tobi/ryx-ai/ryx`)
- **ryx_main.py**: Python entry point with command routing
- **core/session_loop.py**: Interactive CLI session
- **core/ryx_brain.py**: Central brain for understanding & execution
- **core/council/supervisor.py**: Intelligent query dispatch
- **ryxhub/**: React + Vite web interface

### Inference Backend
- **vLLM** via Docker with ROCm 6.4.1
- Models stored in `/home/tobi/vllm-models/`
- API endpoint: `http://localhost:8001/v1/` (OpenAI-compatible)
- GPU: AMD RX 7800 XT (16GB VRAM)

### Model Configuration
| Mode | Model | Context | Use Case |
|------|-------|---------|----------|
| **coding** | qwen2.5-coder-14b-awq | 32K | RyxSurf development, complex code |
| **general** | qwen2.5-14b-gptq | 16K | CLI chat, documents, letters |
| **fast** | qwen2.5-7b-awq | 32K | Quick browser actions, summarization |

**32K context on 14B** achieved via:
- FP8 KV cache (`--kv-cache-dtype fp8`)
- 95% GPU utilization (`--gpu-memory-utilization 0.95`)
- Chunked prefill (`--enable-chunked-prefill`)

## Agent Architecture

### Supervisor-Worker Pattern
```
User Query
    ↓
Supervisor (7B model)
    ├── Parses intent
    ├── Breaks into tasks
    ├── Assigns to workers
    ↓
Worker Pool (parallel)
    ├── Search Worker → SearXNG
    ├── Summarize Worker
    ├── Extract Worker
    └── Validate Worker
    ↓
Supervisor aggregates → Response
```

### Key Classes

**Supervisor** (`core/council/supervisor.py`):
- Orchestrates all queries
- Uses 7B model for routing decisions
- Applies response styles (concise/normal/explanatory/learning/formal)
- Aggregates worker results

**Worker** (`core/council/worker.py`):
- Specialized agents for specific tasks
- Types: SEARCH, SUMMARIZE, EXTRACT, VALIDATE, GENERAL
- Run in parallel via WorkerPool
- Use smaller models for speed

**Brain** (`core/ryx_brain.py`):
- Core intelligence for understanding & execution
- Manages conversation context
- Intent classification (OPEN_FILE, SEARCH_WEB, CODE_TASK, etc.)
- Tool-Only Mode for structured outputs

**BaseAgent** (`core/agents/base.py`):
- Abstract base for all agents
- Tool registry integration
- LLM call handling with retries

### Intent Types
```python
Intent.OPEN_FILE      # Open file in editor
Intent.SEARCH_WEB     # Web search via SearXNG
Intent.CODE_TASK      # Complex coding (EXPLORE→PLAN→APPLY→VERIFY)
Intent.RUN_COMMAND    # Shell execution
Intent.SCRAPE         # Scrape URL content
Intent.CHAT           # General conversation
```

### Tools Registry
Built-in tools agents can use:
- `find_files` - Find files by pattern (uses fd/find)
- `read_file` - Read file contents
- `run_command` - Execute shell commands
- `search_content` - Search in files (uses ripgrep)

## Coding Standards

### Python
- Use type hints everywhere
- Prefer `pathlib.Path` over `os.path`
- Use `async/await` for I/O-bound operations
- Keep functions small and focused
- Error handling: catch specific exceptions, provide context

### Style
- Minimal comments - code should be self-documenting
- Use meaningful variable names
- Follow existing patterns in codebase
- No unnecessary abstractions

### File Organization
```
ryx-ai/
├── core/           # Core logic (brain, agents, tools)
├── configs/        # JSON configuration files
├── data/           # Runtime data, sessions, cache
├── docker/         # Docker compose for vLLM, SearXNG
├── ryxhub/         # Web interface (React + TypeScript)
├── ryx_core/       # Alternative CLI module (Typer-based)
├── ryx_pkg/        # Package for web API
└── tools/          # Standalone tools
```

## User Context

### Environment
- **OS**: Arch Linux
- **WM**: Hyprland (tiling, keyboard-focused)
- **Shell**: zsh
- **Editor**: neovim
- **Terminal**: kitty
- **GPU**: AMD RX 7800 XT (16GB VRAM, ROCm)
- **CPU**: AMD Ryzen 9 5900X

### Preferences
- Keyboard over mouse
- Keybinds over clicking
- Concise responses
- Action over explanation
- Dark themes (Dracula/Nord/Catppuccin)

## Current Projects

### RyxSurf (Browser) - In Development
A minimalist, AI-integrated browser:
- Firefox extension support (WebExtensions API)
- Hyprland-style (fullscreen default, keybind toggles)
- Tab sessions/groups (school/work/chill)
- AI can click, summarize, dismiss popups
- Auto-unload inactive tabs
- Synced with ryx CLI and RyxHub

#### RyxSurf Keybind Conventions
Following Hyprland/vim philosophy:
```
# Navigation
Super + j/k         Scroll down/up
Super + h/l         Back/forward in history
Super + g           Go to URL (opens bar)
Super + /           Search in page
Super + f           Hint mode (click links with keyboard)

# Tabs
Super + t           New tab
Super + w           Close tab
Super + 1-9         Switch to tab N
Super + Tab         Next tab
Super + Shift+Tab   Previous tab
Super + s           Save session
Super + Shift+s     Switch session (school/work/chill)

# UI Toggle
Super + b           Toggle sidebar (tabs list)
Super + Shift+b     Toggle bookmarks bar
Super + Escape      Toggle all UI (true fullscreen)

# AI Commands
Super + a           Open AI command bar
Super + Shift+a     AI: Summarize this page
Super + x           AI: Dismiss popup/overlay
Super + r           AI: Read mode (extract article)

# Quick Actions
Super + y           Yank (copy) URL
Super + p           Paste and go
Super + o           Open file
Super + d           Download manager
```

#### RyxSurf Architecture
```
ryxsurf/
├── src/
│   ├── core/           # Browser engine integration
│   ├── ai/             # AI integration layer
│   │   ├── agent.py    # Browser control agent
│   │   ├── actions.py  # Click, scroll, type, etc.
│   │   └── vision.py   # Page understanding
│   ├── ui/             # Minimal UI components
│   │   ├── bar.py      # URL/command bar
│   │   ├── tabs.py     # Tab sidebar
│   │   └── hints.py    # Keyboard hint overlay
│   ├── sessions/       # Tab groups/sessions
│   └── extensions/     # Firefox extension support
├── keybinds.py         # All keybind definitions
└── main.py             # Entry point
```

### Model Management
Different models for different tasks:
- **coding**: qwen2.5-coder-14b-awq @ 32K context (RyxSurf development)
- **general**: qwen2.5-14b-gptq @ 16K context (CLI chat, documents)
- **fast**: qwen2.5-7b-awq @ 32K context (browser quick actions)

Commands for mode switching:
```bash
ryx start ryx              # Start CLI with general model
ryx restart all for coding # Restart with coding model (32K context)
ryx restart all for ryxhub # Restart with RyxHub-optimized config
ryx restart all for ryxsurf # Restart with browser-optimized config
```

#### vLLM Configuration by Mode
```yaml
# Coding mode (qwen2.5-coder-14b-awq)
--model /models/powerful/coding/qwen2.5-coder-14b-awq
--max-model-len 32768
--gpu-memory-utilization 0.95
--kv-cache-dtype fp8
--enable-chunked-prefill

# Fast mode (qwen2.5-7b-awq)
--model /models/fast/general/qwen2.5-7b-awq
--max-model-len 32768
--gpu-memory-utilization 0.85
```

## Self-Improvement Protocol

Ryx is designed to be self-healing and self-improving. When Ryx makes a mistake:

### The Rule
**Don't fix the output directly - fix Ryx's understanding.**

### Process
1. **Identify root cause**: Is it a prompt issue? Missing context? Wrong model?
2. **Fix the system**: Update prompts, improve context gathering, fix reasoning
3. **Update memory**: Add to experience memory for future reference
4. **Verify**: Run similar task to confirm fix works

### Self-Healing Components

**SelfHealer** (`core/self_healer.py`):
- Cleans stale/invalid cache entries
- Removes hallucinated knowledge
- Consolidates duplicate memories
- Run via `/heal` or `/heal aggressive`

**SelfAnalyzer** (`core/self_improve.py`):
- Analyzes codebase for issues
- Generates improvement plans
- Tracks code quality over time
- Run via `/improve` or `/improve plan`

### Experience Memory
Ryx learns from interactions:
```python
# Stored in data/memory.db
- Successful patterns (what worked)
- Failed patterns (what didn't)
- User preferences (learned over time)
- Domain knowledge (accumulated facts)
```

### Commands
- `/heal` - Run self-healing on knowledge base
- `/heal aggressive` - Deep clean (removes more)
- `/improve` - Quick codebase analysis
- `/improve plan` - Generate full improvement plan
- `/doctor` - Run health diagnostics
- `/fix` - Auto-fix last error

## Testing

```bash
# Run tests
python -m pytest tests/

# Quick health check
ryx status
ryx /doctor
```

## Common Tasks

### Starting Services
```bash
ryx                    # Interactive CLI
ryx ryxhub             # Web interface
ryx start vllm         # Start vLLM container
ryx start searxng      # Start search engine
ryx status             # Check all services
```

### Development
```bash
# Edit and test
cd /home/tobi/ryx-ai
source venv/bin/activate
python ryx_main.py

# Rebuild RyxHub frontend
cd ryxhub && npm run build
```

## Important Notes

1. **vLLM over Ollama**: This project uses vLLM, not Ollama (despite README mentioning it)
2. **ROCm specifics**: Always set `HSA_OVERRIDE_GFX_VERSION=11.0.0` for RDNA3
3. **Port 8001**: vLLM API (not 11434 which is Ollama)
4. **Port 8420**: RyxHub API
5. **Port 8080**: RyxHub frontend
6. **Port 8888**: SearXNG search

## Response Guidelines

When helping with this project:
- Be concise and direct
- Show code, not explanations
- Use existing patterns from codebase
- Prefer small, surgical changes
- Test changes before suggesting
- Consider Hyprland/keyboard-first UX
- Remember: this aims to be as good as Claude Code CLI, but local

---

## 🚨 CRITICAL: Session State (2025-12-08)

### Current Status
**Ryx is ~10% as good as Claude Code CLI** - Major improvements needed.

### The Autonomous Loop (YOUR JOB)

```
1. Give Ryx natural language prompts (like "resume work on ryxsurf")
2. Ryx should automatically:
   - Find files it needs
   - Read context
   - Make changes
   - Verify they work
3. If Ryx fails → Improve Ryx's code (NOT do the work for it)
4. If Ryx succeeds → Continue to next task
5. Repeat
```

**KEY RULE**: Don't do Ryx's work. Prompt Ryx, and if it fails, fix Ryx.

### RyxSurf Priority Fixes

1. **Sidebar**: Make 10-20% width, toggle-able
2. **URL bar**: Compact, remove useless buttons
3. **Keybinds**: Ctrl+L (focus URL), Ctrl+W (close tab), Ctrl+T (new tab), Ctrl+↓/↑ (navigate tabs), Ctrl+1-9 (jump to tab)
4. **Performance**: Make fast, resource efficient
5. **New tab**: Clean URL, auto-focus search

### Ryx Autonomy Improvements Needed

Study these repos at `/home/tobi/cloned_repositorys/`:
- **aider**: RepoMap, fuzzy edit matching
- **SWE-agent**: Autonomous coding
- **healing-agent**: Self-healing patterns

Ryx must:
- Explore codebase automatically
- Find files without being told paths
- Self-heal from errors (3 retries)
- Maintain task context
- Continue working autonomously

### Technical Stack

- **Inference**: vLLM at localhost:8001 (NOT OLLAMA)
- **Model**: qwen2.5-coder-14b-awq
- **GPU**: AMD RX 7800 XT, 90% max utilization
- **Context**: 16K-32K tokens

### Files to Clean (Ollama→vLLM)

Many files still reference Ollama. Clean these:
- modes/session_mode.py, cli_mode.py
- scripts/*.py
- ryx_pkg/agents/*.py
- README.md

### Read MISSION.md

Full details in `/home/tobi/ryx-ai/MISSION.md` - read it first!
