# 🏗️ Ryx AI - Architecture Documentation

## System Overview

Ryx AI is built on a **modular, layered architecture** optimized for speed, safety, and intelligence.

```
┌─────────────────────────────────────────────────┐
│               User Interface                     │
│  CLI Mode (ryx "prompt") | Session (::session)  │
└────────────┬────────────────────────┬────────────┘
             │                        │
             ▼                        ▼
┌────────────────────┐    ┌──────────────────────┐
│   Request Router   │    │  Command Parser      │
└─────────┬──────────┘    └──────────┬───────────┘
          │                          │
          ▼                          ▼
┌─────────────────────────────────────────────────┐
│              Core Engine Layer                   │
├─────────────────────────────────────────────────┤
│  • AI Engine (model selection & inference)      │
│  • RAG System (zero-latency cache)              │
│  • Permission Manager (safety layer)            │
│  • Command Executor (action handler)            │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│              Data Layer                          │
├─────────────────────────────────────────────────┤
│  • SQLite (knowledge & cache)                   │
│  • JSON configs (settings & permissions)        │
│  • File system (logs & history)                 │
└─────────────────────────────────────────────────┘
```

## Layer Breakdown

### 1. User Interface Layer

**Purpose**: Handle user input and display responses

**Components**:
- **CLI Mode** (`modes/cli_mode.py`)
  - Parses command-line arguments
  - Routes to appropriate handler
  - Formats output for terminal
  - Handles special commands (`::xxx`)

- **Session Mode** (`modes/session_mode.py`)
  - Interactive REPL
  - Conversation history management
  - Multi-turn context
  - Session commands (`/xxx`)

**Key Features**:
- Beautiful terminal formatting (via Rich)
- Syntax highlighting for code blocks
- Progress indicators
- Error handling with helpful messages

### 2. Core Engine Layer

#### A. AI Engine (`core/ai_engine.py`)

**Purpose**: Manage AI models and inference

**Key Classes**:
- `AIEngine`: Main interface to Ollama
- `ResponseFormatter`: Format AI responses
- `ModelSpec`: Model specifications

**Features**:
- **Smart Model Selection**
  ```python
  query = "simple command"
  → selects fast model (deepseek-6.7b)
  
  query = "complex analysis"
  → selects powerful model (qwen-32b)
  ```

- **Complexity Analysis**
  - Query length
  - Keywords (explain, analyze vs. open, show)
  - Context size
  - Returns score 0.0-1.0

- **Response Compaction**
  - Removes filler phrases
  - Extracts essential information
  - Optimizes for speed

#### B. RAG System (`core/rag_system.py`)

**Purpose**: Provide zero-latency responses through intelligent caching

**Key Classes**:
- `RAGSystem`: Main RAG interface
- `FileFinder`: Smart file location

**Cache Architecture**:

```
User Query
    ↓
┌───────────────┐
│  Hot Cache    │  In-memory dict (top 100 queries)
│   0ms         │  → Instant response
└───────┬───────┘
        │ miss
        ▼
┌───────────────┐
│  Warm Cache   │  SQLite database
│   <10ms       │  → Very fast response
└───────┬───────┘
        │ miss
        ▼
┌───────────────┐
│  RAG Context  │  Knowledge base lookup
│   10-50ms     │  → Contextual info
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  AI Query     │  Full model inference
│   500-2000ms  │  → Complete response
└───────────────┘
        ↓
    [Cache & Learn]
```

**Database Schema**:

```sql
-- Quick response cache
CREATE TABLE quick_responses (
    prompt_hash TEXT UNIQUE,
    response TEXT,
    model_used TEXT,
    created_at TIMESTAMP,
    use_count INTEGER,
    ttl_seconds INTEGER
);

-- Knowledge base
CREATE TABLE knowledge (
    query_hash TEXT UNIQUE,
    file_type TEXT,
    file_path TEXT,
    content_preview TEXT,
    confidence REAL,
    access_count INTEGER
);

-- Command history
CREATE TABLE command_history (
    command TEXT,
    result TEXT,
    success BOOLEAN,
    timestamp TIMESTAMP
);
```

**Learning Mechanism**:

```python
# First time user asks for hyprland config
query = "open hyprland config"
→ Searches filesystem
→ Finds ~/.config/hyprland/hyprland.conf
→ Stores in knowledge table:
   {
     query_hash: "abc123",
     file_type: "config",
     file_path: "~/.config/hyprland/hyprland.conf",
     confidence: 1.0
   }

# Next time
query = "open hyprland config"
→ Hash query → "abc123"
→ Lookup in knowledge table → Found!
→ Return file path instantly (0ms)
```

#### C. Permission Manager (`core/permissions.py`)

**Purpose**: Ensure safe command execution

**Key Classes**:
- `PermissionManager`: Analyze commands
- `CommandExecutor`: Execute safely
- `InteractiveConfirm`: User confirmation UI

**Permission Levels**:

```python
SAFE = {
    # Read-only operations
    "commands": ["ls", "cat", "grep", "find", ...],
    "auto_approve": True,
    "risk": "none"
}

MODIFY = {
    # File modifications
    "commands": ["cp", "mv", "mkdir", "nvim", ...],
    "auto_approve": True,  # In safe dirs only
    "safe_directories": ["~/.config", "~/Documents"],
    "blocked_directories": ["/etc", "/sys", "/usr"]
}

DESTROY = {
    # Dangerous operations
    "commands": ["rm", "rmdir", "dd", "shred"],
    "auto_approve": False,  # Always ask
    "confirmation_required": True
}
```

**Analysis Flow**:

```python
def analyze_command(cmd):
    # 1. Check global blocks
    if "rm -rf /" in cmd:
        return BLOCKED
    
    # 2. Extract base command
    base = cmd.split()[0]
    
    # 3. Check permission level
    if base in DESTROY_COMMANDS:
        return DESTROY  # Requires confirmation
    elif base in MODIFY_COMMANDS:
        if in_safe_directory(cmd):
            return MODIFY  # Auto-approved
        else:
            return DESTROY  # System files
    else:
        return SAFE  # Auto-approved
```

#### D. Self-Improvement System (`core/self_improve.py`)

**Purpose**: Allow Ryx to analyze and improve itself

**Key Classes**:
- `SelfAnalyzer`: Code analysis
- `SelfImprover`: Improvement suggestions

**Features**:
- **Code Analysis**
  - Parses Python AST
  - Detects missing docstrings
  - Finds TODO/FIXME comments
  - Identifies large files (>500 lines)
  - Checks for syntax errors

- **Missing Feature Detection**
  - Analyzes failed command history
  - Finds NotImplementedError
  - Tracks incomplete implementations

- **AI-Powered Suggestions**
  - Uses AI to suggest fixes
  - Generates implementation plans
  - Prioritizes by severity

**Workflow**:

```bash
$ ryx ::improve analyze
→ Scans all .py files
→ Runs AST analysis
→ Checks command history
→ Generates report

$ cat ~/ryx-ai/data/improvement_plan.md
# Issues Found: 5
# Suggestions: 12
# Missing Features: 3

$ ryx ::improve interactive
→ Shows top issues
→ AI suggests fixes
→ User approves changes
```

### 3. Tools Layer

#### A. Web Scraper (`tools/scraper.py`)

**Purpose**: Legal web content extraction for learning

**Features**:
- Respects robots.txt
- Caches results
- Extracts text, links, metadata
- Rate limiting
- Educational use only

**Usage**:
```bash
ryx ::scrape https://docs.python.org
→ Fetches page
→ Extracts content
→ Caches locally
→ Displays summary
```

#### B. Web Browser (`tools/browser.py`)

**Purpose**: Search and analyze web content

**Features**:
- DuckDuckGo search (privacy-friendly)
- Result summarization
- Interactive scraping
- No tracking

**Usage**:
```bash
ryx ::browse "arch linux subnetting"
→ Shows search results
→ Offers to scrape
→ Extracts useful info
```

#### C. Council (`tools/council.py`)

**Purpose**: Multi-model consensus for code review

**Features**:
- Runs prompt through multiple models
- Collects ratings/reviews
- Shows consensus
- Useful for critical decisions

**Usage**:
```bash
ryx ::council "review my code: <code>"
→ Queries all small models (<10GB)
→ Collects ratings
→ Shows average + individual reviews
→ Highlights common issues
```

### 4. Data Layer

**Locations**:
```
~/ryx-ai/data/
├── rag_knowledge.db      # SQLite database
├── cache/                # Scraped web content
│   └── scraped/
├── history/              # Command logs
│   └── commands.log
├── code_analysis.json    # Self-analysis results
├── improvements.json     # Improvement tracking
└── improvement_plan.md   # Generated plans
```

## Configuration System

### Config Files (`~/ryx-ai/configs/`)

**1. models.json** - AI model specifications

```json
{
  "models": {
    "fast": {
      "name": "deepseek-coder:6.7b",
      "size": "3.8GB",
      "use_case": "quick_commands",
      "max_latency_ms": 500,
      "priority": 1
    },
    ...
  },
  "auto_select": true,
  "preload_on_boot": false
}
```

**2. permissions.json** - Safety rules

**3. commands.json** - Custom command definitions

**4. settings.json** - User preferences

## Performance Characteristics

### Latency Breakdown

```
Cache Hit (Hot):      0-1ms     ████
Cache Hit (Warm):    5-10ms     ████████
RAG Context:        10-50ms     ████████████
AI Query (Fast):   500-1000ms  ████████████████████████
AI Query (Power): 2000-5000ms  ████████████████████████████████████
```

### Memory Usage

```
Idle State:
- Python daemon:    50MB
- Hot cache:        50MB
- Total:           100MB

Active State (Fast Model):
- Model (VRAM):   4-5GB
- Model (RAM):    2-3GB
- System:         100MB
- Total:          ~6GB

Active State (Powerful Model):
- Model (VRAM):  12-16GB
- Model (RAM):    8-10GB
- System:         100MB
- Total:          ~20GB
```

### Cache Hit Rates

After 1 week of use:
- Hot cache: ~40% hit rate
- Warm cache: ~30% hit rate
- AI query: ~30% (new queries)

## Security Features

### Input Validation
- Command sanitization
- Path traversal prevention
- Injection attack prevention

### Permission Checks
- Three-level system
- Whitelist-based
- User confirmation for destructive ops

### Sandboxing (Docker)
- Non-root user
- Resource limits
- Read-only mounts for configs

## Extensibility

### Adding New Models

Edit `configs/models.json`:
```json
{
  "models": {
    "my_model": {
      "name": "custom-model:latest",
      "size": "15GB",
      "use_case": "specialized_task",
      "max_latency_ms": 3000,
      "priority": 2
    }
  }
}
```

### Adding New Commands

Edit `configs/commands.json`:
```json
{
  "commands": {
    "my_command": {
      "aliases": ["::mycmd", "::mc"],
      "description": "My custom command",
      "category": "tools"
    }
  }
}
```

Then implement in `modes/cli_mode.py`:
```python
elif command == "::mycmd":
    my_custom_function(args)
```

### Adding New Tools

Create `tools/my_tool.py`:
```python
class MyTool:
    def __init__(self):
        pass
    
    def run(self, args):
        # Implementation
        pass
```

Update `tools/__init__.py`:
```python
from .my_tool import MyTool
__all__ = [..., 'MyTool']
```

## Development Workflow

### Testing Changes

```bash
# Edit code
nvim ~/ryx-ai/core/ai_engine.py

# Test directly
python3 ~/ryx-ai/ryx "test prompt"

# Check logs
tail -f ~/ryx-ai/data/history/commands.log
```

### Debugging

```python
# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Or use breakpoint
breakpoint()
```

### Self-Analysis

```bash
# Run analysis
ryx ::improve analyze

# Check report
cat ~/ryx-ai/data/improvement_plan.md
```

## Deployment

### Docker (Recommended)

```bash
cd ~/ryx-ai
docker-compose up -d
docker exec -it ryx-ai python3 /app/ryx "test"
```

### Native (Faster)

```bash
# Already set up!
ryx "test"
```

## Monitoring

### System Status

```bash
ryx ::status
```

Shows:
- AI engine status
- Cache statistics
- Known files
- Model info

### Logs

```bash
# Command history
cat ~/ryx-ai/data/history/commands.log

# Database queries
sqlite3 ~/ryx-ai/data/rag_knowledge.db "SELECT * FROM quick_responses ORDER BY use_count DESC LIMIT 10;"
```

## Maintenance

### Daily Auto-Cleanup

Scheduled via cron (3 AM):
- Remove old cache (>30 days)
- Prune Docker images
- Compress logs
- Optimize database (VACUUM)

### Manual Cleanup

```bash
ryx ::clean
```

---

## Design Principles

1. **Speed First**: Cache everything possible
2. **Safety Always**: Confirm destructive operations
3. **Learn Continuously**: Build knowledge base
4. **Fail Gracefully**: Never crash, always helpful error messages
5. **Privacy Focused**: All local, no telemetry
6. **Minimal Resources**: Efficient when idle
7. **User Control**: Always transparent about actions

---

**This architecture enables Ryx to be fast, safe, and continuously improving!**