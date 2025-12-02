# RYX AI - Complete Handoff Document for Next Session

**Generated:** 2025-12-02T03:47 UTC
**Purpose:** Complete context transfer for continuing Ryx development

---

## 1. USER PROFILE: TOBI

### Environment
- **OS:** Arch Linux
- **WM:** Hyprland (Wayland compositor)
- **Terminal:** Kitty
- **Editor:** Neovim (nvim)
- **Browser:** Zen Browser (default), also uses Firefox, Brave
- **Shell:** Zsh
- **Theme:** Dark (Dracula/Gruvbox style with purple accents)

### User Preferences
- **NO HARDCODED COMMANDS** - Everything must be AI-interpreted
- **Action over explanation** - Ryx should DO things, not tell user how
- **Precision over speed** - Quality matters more than response time
- **Bilingual** - German and English, understands both naturally
- **Minimal output** - Concise responses, no verbose explanations
- **Never "Could you be more specific?"** - Ask concrete questions instead

### Common Tasks
- Opening config files (hyprland, waybar, kitty, nvim, etc.)
- Opening websites (youtube, reddit, github, etc.)
- Searching for files
- Web scraping and learning from content
- Creating study materials ("Lernzettel" in German)
- System management (Arch Linux, pacman/yay)

---

## 2. PROJECT STRUCTURE

```
/home/tobi/ryx-ai/
├── ryx_cli_v3.py          # Main CLI entry point (currently used)
├── core/
│   ├── ryx_session.py     # Interactive session handler (OLD - uses ryx_engine.py)
│   ├── session_loop_v4.py # NEW session loop (uses ryx_brain_v4.py)
│   ├── ryx_engine.py      # OLD engine (pattern matching + LLM)
│   ├── ryx_brain_v4.py    # NEW brain with Supervisor/Operator architecture
│   ├── ollama_client.py   # Ollama API client
│   ├── model_router.py    # Model selection logic
│   ├── paths.py           # Path utilities
│   ├── service_manager.py # Start/stop RyxHub
│   ├── ui.py              # Terminal UI helpers
│   └── rag_system.py      # RAG vector storage
├── data/
│   ├── knowledge/
│   │   ├── arch_linux.json   # Config paths, websites, aliases
│   │   ├── websites.json     # Learned websites
│   │   └── cache.json        # Cached Q&A pairs
│   ├── scrape/               # Scraped web content
│   ├── rag/                  # Vector embeddings
│   ├── smart_cache_v4.db     # SQLite cache for resolutions
│   └── session_state_v4.json # Persisted session state
├── ryx/
│   └── interfaces/           # RyxHub React frontend
└── docs/                     # Documentation
```

---

## 3. CURRENT ARCHITECTURE (BROKEN - NEEDS FIX)

### Problem
The CLI currently uses **ryx_session.py** which imports **ryx_engine.py**. This is the OLD pattern-matching approach that:
- Says "Could you be more specific?" constantly
- Doesn't understand follow-up questions
- Doesn't use conversation context
- Can't do multi-action prompts
- Doesn't have precision mode
- Doesn't properly route to different models

### What Was Started But Not Connected
I created **ryx_brain_v4.py** and **session_loop_v4.py** with the new architecture, but they're NOT being used by the CLI. The CLI still imports the old modules.

### Required Fix
Change `ryx_cli_v3.py` line 58 from:
```python
from core.ryx_session import run_session
```
to:
```python
from core.session_loop_v4 import SessionLoopV4
```

And modify the session call to use the new class.

---

## 4. INTENDED ARCHITECTURE (Supervisor/Operator)

### Two-Stage Agent System

```
┌─────────────────────────────────────────────────────────────┐
│                    USER PROMPT                               │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  STAGE 1: SUPERVISOR                         │
│  Model: 10B+ (gpt-oss:20b or qwen2.5:7b)                    │
│  Tasks:                                                      │
│   - Deep intent understanding                                │
│   - Plan creation                                            │
│   - Model selection for operator                             │
│   - Error recovery when operator fails                       │
│  Called: 1-2 times per task                                  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  STAGE 2: OPERATOR                           │
│  Model: 3B-7B (qwen2.5:3b or qwen2.5:7b)                    │
│  Tasks:                                                      │
│   - Execute plan steps                                       │
│   - Use tools (file search, web scrape, etc.)               │
│   - Try multiple strategies                                  │
│   - Report status to supervisor                              │
│  Called: Multiple times, does the actual work                │
└─────────────────────────────────────────────────────────────┘
```

### Fast Path (No LLM)
For cached/known queries, skip LLM entirely:
1. Check SmartCache (SQLite) for previous successful resolution
2. Check KnowledgeBase for known configs/websites
3. Pattern match simple queries (date, time, model list)

### Escalation Logic
```
fail_count >= 2 → Switch to bigger model
fail_count >= 4 → Supervisor takes over directly
```

---

## 5. MODEL TIERS

### Available Models (Check with `ollama list`)
```
TIER        MODEL                  USE CASE
────────────────────────────────────────────────────
tiny        qwen2.5:1.5b          Cached lookups only
fast        qwen2.5:3b            Intent classification, simple tasks
balanced    qwen2.5:7b            General use, chat
smart       qwen2.5-coder:14b     Complex reasoning (DON'T USE FOR CHAT)
precision   gpt-oss:20b           Learning mode, document creation
```

### Important Rules
- **DON'T use coding models (qwen2.5-coder) for general chat** - They produce verbose, code-focused output
- **Use gpt-oss:20b for precision mode** - User specifically requested this
- **Tiny model only for cache hits** - Never for actual reasoning

---

## 6. KEY FEATURES TO IMPLEMENT/FIX

### Currently Broken
1. **Follow-up questions** - "open it" after showing a path doesn't work
2. **Context awareness** - Doesn't remember what was just discussed
3. **y/n fast responses** - Should be instant, currently goes to LLM
4. **Precision mode** - `/precision on` doesn't exist
5. **Browsing toggle** - `/browsing on/off` doesn't work
6. **Model switching** - "use gpt 20b as default" doesn't work
7. **Scraping flow** - Says "I don't know wislearn" instead of offering to search

### User Requested Features (Not Yet Implemented)
1. **Supervisor/Operator architecture** - Partially in ryx_brain_v4.py but not connected
2. **SearXNG auto-start** - Ask "Should I start it?" instead of just failing
3. **Multi-action prompts** - "find cuno, scrape it, make a summary"
4. **Learning mode** - Big models only, for training/feeding knowledge
5. **HTML/CSS scraping** - Separate from content scraping
6. **Hyprland autostart** - Add `exec-once = ryx` to hyprland.conf
7. **Restart command** - `ryx restart all` with confirmation

### Conversation Flow Examples

**Expected:**
```
> hyprland config
✅ Opened: ~/.config/hypr/hyprland.conf

> where is it
~/.config/hypr/hyprland.conf

> open it in new terminal
✅ Opened in new terminal
```

**Currently Broken:**
```
> hyprland config
✅ Opened: ~/.config/hypr/hyprland.conf

> where is it
Could you be more specific?   ← WRONG

> open it
Could you be more specific?   ← WRONG
```

---

## 7. DATA STRUCTURES

### ConversationContext (from ryx_brain_v4.py)
```python
@dataclass
class ConversationContext:
    last_query: str = ""
    last_result: str = ""
    last_path: str = ""           # Last file/URL referenced
    last_intent: Optional[Intent] = None
    pending_items: List[Dict] = [] # For selection (multiple results)
    pending_plan: Optional[Plan] = None
    awaiting_confirmation: bool = False
    awaiting_selection: bool = False
    last_scraped: Optional[Dict] = None
    language: str = "auto"        # 'de' or 'en'
    turn_count: int = 0
```

### Plan (from ryx_brain_v4.py)
```python
@dataclass
class Plan:
    intent: Intent
    target: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)
    steps: List[str] = field(default_factory=list)
    question: Optional[str] = None  # Clarifying question
    confidence: float = 1.0
    requires_confirmation: bool = False
    fallback_intents: List[Intent] = field(default_factory=list)
```

### Intent Enum
```python
class Intent(Enum):
    OPEN_FILE = "open_file"
    OPEN_URL = "open_url"
    FIND_FILE = "find_file"
    FIND_PATH = "find_path"
    SEARCH_WEB = "search_web"
    SCRAPE = "scrape"
    SCRAPE_HTML = "scrape_html"
    RUN_COMMAND = "run_command"
    SET_PREFERENCE = "set_pref"
    SWITCH_MODEL = "switch_model"
    CREATE_DOCUMENT = "create_doc"
    START_SERVICE = "start_svc"
    STOP_SERVICE = "stop_svc"
    RESTART = "restart"
    GET_INFO = "get_info"
    LIST_MODELS = "list_models"
    CHAT = "chat"
    CONFIRM = "confirm"
    SELECT = "select"
    UNCLEAR = "unclear"
```

---

## 8. KNOWLEDGE BASE (data/knowledge/arch_linux.json)

### Config Paths
```json
{
  "hyprland": "~/.config/hypr/hyprland.conf",
  "hyprlock": "~/.config/hypr/hyprlock.conf",
  "hypridle": "~/.config/hypr/hypridle.conf",
  "waybar": "~/.config/waybar/config",
  "kitty": "~/.config/kitty/kitty.conf",
  "nvim": "~/.config/nvim/init.lua",
  "zsh": "~/.zshrc",
  ...
}
```

### Aliases (Typo Handling)
```json
{
  "hyperland": "hyprland",
  "hyperion": "hyprland",
  "hypr": "hyprland",
  ...
}
```

### Websites
```json
{
  "youtube": "https://youtube.com",
  "github": "https://github.com",
  "archwiki": "https://wiki.archlinux.org",
  ...
}
```

---

## 9. SLASH COMMANDS (Session Mode Only)

### Currently Defined
```
/help, /hilfe        Show help
/quit, /beenden      Exit session
/clear, /neu         Clear context
/status              Show stats
/models, /modelle    List models
/precision on/off    Toggle precision mode
/browsing on/off     Toggle web browsing
/scrape <url>        Scrape webpage
/learn, /digest      Learn from scraped content
/search <query>      Web search (SearXNG)
/smarter             Self-improvement
/restart all         Restart Ryx
/export              Export session to markdown
```

### Special Syntax
```
@path/to/file        Include file in context
!command             Run shell command directly
```

---

## 10. CRITICAL FIXES NEEDED

### Fix 1: Connect New Brain to CLI
```python
# In ryx_cli_v3.py, change:
from core.ryx_session import run_session
# To:
from core.session_loop_v4 import SessionLoopV4

# And in main():
def main():
    ...
    if not remaining:
        session = SessionLoopV4(safety_mode=safety_mode)
        session.run()
        return
```

### Fix 2: Model Settings
```python
# In ryx_brain_v4.py, update MODELS:
MODELS = {
    "fast": ["qwen2.5:1.5b", "qwen2.5:3b"],
    "balanced": ["gpt-oss:20b", "qwen2.5:7b"],  # Use gpt-oss as default
    "smart": ["gpt-oss:20b"],                    # NOT coding models
    "precision": ["gpt-oss:20b", "huihui_ai/gpt-oss-abliterated:20b"],
}
```

### Fix 3: Never Say "Could you be more specific?"
The phrase "Could you be more specific?" should NEVER appear. Instead:
- If config unknown: "Welche Config? (hyprland, waybar, kitty...)"
- If URL unknown: "I don't know that site. Want me to search for it?"
- If action unclear: "Soll ich [X] öffnen oder [Y] anzeigen?"

### Fix 4: Context Reference Handling
```python
def _handle_context_reference(self, prompt: str) -> Optional[Plan]:
    p = prompt.lower()
    
    # "open it", "show it", "edit it"
    if any(x in p for x in ['open it', 'edit it', 'öffne es']):
        if self.ctx.last_path and os.path.exists(self.ctx.last_path):
            return Plan(intent=Intent.OPEN_FILE, target=self.ctx.last_path)
    
    # "where is it" - just show the path
    if any(x in p for x in ['where is it', 'wo ist es', 'the path']):
        if self.ctx.last_path:
            return Plan(intent=Intent.FIND_PATH, target=self.ctx.last_path)
```

### Fix 5: Quick Y/N Responses (No LLM)
```python
def _is_quick_response(self, prompt: str) -> bool:
    p = prompt.lower().strip()
    quick = {'y', 'yes', 'ja', 'n', 'no', 'nein', 'ok', 'klar', '1', '2', '3', '4', '5'}
    return p in quick or p.isdigit()
```

---

## 11. TESTING CHECKLIST

### Basic Operations
- [ ] `ryx` starts interactive session
- [ ] `ryx youtube` opens YouTube
- [ ] `ryx hyprland config` opens config file
- [ ] `ryx hyperland config` (typo) still works
- [ ] `ryx find great wave` searches files
- [ ] Date/time queries work

### Follow-up Questions
- [ ] After "hyprland config", "open it in new terminal" works
- [ ] After "where is hyprland config", context is remembered
- [ ] "y" and "n" responses are instant

### Precision Mode
- [ ] `/precision on` switches to bigger models
- [ ] Document creation uses precision models
- [ ] Learning mode stays on bigger models

### Scraping Flow
- [ ] `/scrape https://example.com` works
- [ ] `/learn` processes last scrape
- [ ] "scrape arch wiki" resolves to correct URL
- [ ] Unknown sites prompt for search

### Services
- [ ] `ryx start ryxhub` works
- [ ] `ryx stop ryxhub` works
- [ ] `/restart all` asks confirmation

---

## 12. HYPRLAND AUTOSTART

Add to `~/.config/hypr/hyprland.conf`:
```
exec-once = ryx --daemon
```

Or for minimal startup:
```
exec-once = ollama serve &
```

---

## 13. ENVIRONMENT VARIABLES

```bash
export RYX_PROJECT_ROOT="/home/tobi/ryx-ai"
export OLLAMA_BASE_URL="http://localhost:11434"
export EDITOR="nvim"
export BROWSER="zen"
export TERMINAL="kitty"
```

---

## 14. NEXT SESSION PRIORITIES

1. **FIX CLI CONNECTION** - Wire ryx_cli_v3.py to use session_loop_v4.py + ryx_brain_v4.py
2. **TEST EVERYTHING** - Run through checklist above
3. **FIX RESPONSES** - Eliminate "Could you be more specific?"
4. **IMPLEMENT PRECISION MODE** - Properly toggle and use bigger models
5. **IMPLEMENT SEARCH FLOW** - SearXNG integration with auto-start offer
6. **TEST MULTI-ACTION** - "find X and scrape it" type prompts
7. **COMMIT AND PUSH** - Clean up git branches, push to main

---

## 15. GIT STATUS

```bash
# Check current state
cd /home/tobi/ryx-ai
git status
git branch -a

# Clean up branches (delete all except main)
git checkout main
git branch | grep -v main | xargs git branch -D

# Commit and push
git add -A
git commit -m "Major Ryx v4 architecture update - Supervisor/Operator pattern"
git push origin main
```

---

## 16. SUMMARY FOR AI ASSISTANT

**You are continuing development of Ryx AI for user Tobi on Arch Linux.**

**Key Rules:**
1. NO hardcoded patterns - AI interprets everything
2. NEVER say "Could you be more specific?" - Ask concrete questions
3. Action over explanation - DO things, don't explain how
4. Use conversation context - Remember what was just discussed
5. Precision mode uses gpt-oss:20b, NOT coding models
6. Support German and English naturally

**Current State:**
- New architecture (ryx_brain_v4.py) exists but is NOT connected to CLI
- CLI still uses old broken engine
- Need to wire up new system and test thoroughly

**User's Priorities:**
1. Working follow-up questions ("open it", "where is it")
2. Precision mode for learning tasks
3. Web scraping that actually works
4. Multi-action prompts
5. No verbose/useless responses

**Start by reading this document fully, then fix the CLI connection and test.**
