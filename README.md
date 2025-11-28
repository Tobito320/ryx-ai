# 🚀 Ryx AI - Ultra-Fast Local LLM Assistant

Your intelligent terminal companion for Arch Linux, powered by local AI models with **zero-latency responses**.

## ✨ Features

### 🎯 Dual Operating Modes
- **CLI Mode** (`ryx "prompt"`): Ultra-fast one-shot commands with 0ms cache hits
- **Session Mode** (`ryx ::session`): Full interactive Gemini CLI-like experience

### ⚡ Zero-Latency Intelligence
- **3-Layer Cache System**: Hot (in-memory) → Warm (SQLite) → Cold (AI query)
- **RAG Knowledge Base**: Learns file locations and system structure
- **Smart Model Selection**: Automatically chooses fast/balanced/powerful models

### 🛡️ Safety First
- **3-Level Permissions**:
  - `SAFE`: Read-only operations (auto-approved)
  - `MODIFY`: File edits in safe directories (auto-approved)
  - `DESTROY`: Dangerous operations (always requires confirmation)
- **Command Filtering**: Blocks catastrophic commands automatically

### 🧠 Self-Improving
- Analyzes its own codebase
- Suggests improvements
- Tracks missing features
- AI-powered fix suggestions

### 🔧 Advanced Tools
- **Web Scraper** (`::scrape`): Legal web content extraction
- **Web Browser** (`::browse`): Search and analyze web content
- **Council** (`::council`): Multi-model consensus for code review

### 📦 Minimal Resources
- **Idle**: 50-100MB RAM, 0% GPU
- **Active**: Only when querying
- **Auto-Cleanup**: Daily optimization
- **Smart Caching**: Reduces repeated queries

## 📋 Requirements

- **OS**: Arch Linux (or any Linux)
- **Python**: 3.11+
- **Docker**: Latest version
- **Ollama**: For AI models
- **RAM**: 8GB minimum, 16GB+ recommended
- **Storage**: 20GB for models + cache

## 🚀 Quick Start Installation

### Step 1: Download Files

All artifacts have been created. Download them to `~/Downloads`.

### Step 2: Run Installation

```bash
# Create project directory
mkdir -p ~/ryx-ai
cd ~/ryx-ai

# Copy downloaded files (detailed steps below)
# ... (see Installation Guide section)

# Run installer
chmod +x install.sh
./install.sh
```

### Step 3: Test

```bash
# Quick test
ryx 'hello'

# Open a file
ryx 'open hyprland config'

# Start session
ryx ::session
```

## 📖 Usage Guide

### Basic Commands

```bash
# Direct prompts
ryx "how do i reload hyprland?"
ryx "open waybar config"
ryx "find all themes in my system"

# Session mode (interactive)
ryx ::session
  You: show me my keybinds
  Ryx: [shows keybinds]
  You: add super+t for kitty
  Ryx: [generates command]
  You: /exec
  [executes]

# System commands
ryx ::status        # Show system status
ryx ::help          # Full command list
ryx ::config        # View configuration
ryx ::models        # List AI models
ryx ::clean         # Run cleanup
```

### Advanced Tools

```bash
# Web scraping (legal, educational use)
ryx ::scrape https://docs.python.org/3/tutorial/

# Web search and browse
ryx ::browse "arch linux subnetting tutorial"

# Multi-model consensus (experimental)
ryx ::council "review my code: <paste code>"

# Self-improvement
ryx ::improve analyze      # Analyze codebase
ryx ::improve interactive  # Get AI suggestions
```

### Session Mode Commands

```
/quit, /exit        Exit session
/clear              Clear conversation
/exec [number|all]  Execute pending commands
/undo               Undo last exchange
/save [filename]    Save conversation
/status             Show session info
/help               Show help
```

## 🎨 Configuration

All configs in `~/ryx-ai/configs/`:

### `settings.json` - Main Settings

```json
{
  "ai": {
    "default_model": "fast",
    "temperature": 0.3,
    "compact_responses": true
  },
  "cache": {
    "enabled": true,
    "ttl_seconds": 86400,
    "max_entries": 10000
  }
}
```

### `permissions.json` - Safety Rules

Customize what Ryx can do automatically:

```json
{
  "levels": {
    "SAFE": {
      "auto_approve": true,
      "allowed_commands": ["ls", "cat", "grep", ...]
    },
    "MODIFY": {
      "auto_approve": true,
      "safe_directories": ["~/.config", ...]
    },
    "DESTROY": {
      "auto_approve": false,
      "always_confirm": true
    }
  }
}
```

### `models.json` - AI Models

```json
{
  "models": {
    "fast": {
      "name": "deepseek-coder:6.7b",
      "use_case": "quick_commands"
    },
    "balanced": {
      "name": "qwen2.5-coder:14b",
      "use_case": "complex_reasoning"
    }
  }
}
```

## 🏗️ Architecture

```
~/ryx-ai/
├── core/               # Core AI engine
│   ├── ai_engine.py    # Model management
│   ├── rag_system.py   # Zero-latency cache
│   ├── permissions.py  # Safety system
│   └── self_improve.py # Self-analysis
│
├── tools/              # Advanced tools
│   ├── scraper.py
│   ├── browser.py
│   └── council.py
│
├── modes/              # Operating modes
│   ├── cli_mode.py
│   └── session_mode.py
│
├── configs/            # Configuration
├── data/               # Cache & knowledge
└── docker/             # Container setup
```

## 🔬 How It Works

### Zero-Latency System

```
User Query
    ↓
[Hot Cache]  ← In-memory (0ms)
    ↓ miss
[Warm Cache] ← SQLite (<10ms)
    ↓ miss
[RAG Context] ← Knowledge base
    ↓
[AI Model]   ← 500-2000ms
    ↓
[Cache & Learn]
```

### RAG Knowledge Base

First time:
```bash
ryx "open hyprland config"
→ Searches filesystem
→ Finds ~/.config/hyprland/hyprland.conf
→ Opens in nvim
→ Saves location to knowledge base
```

Next time:
```bash
ryx "open hyprland config"
→ Instant recall from knowledge base (0ms)
→ Opens directly
```

### Permission System

```python
Command: "cp config.conf backup.conf"
→ Level: MODIFY
→ Directory: ~/.config (safe)
→ Action: Auto-approved ✓

Command: "rm config.conf"
→ Level: DESTROY
→ Action: Ask confirmation ⚠️
```

## 🧹 Maintenance

### Auto-Cleanup

```bash
# Manual cleanup
ryx ::clean

# Schedule daily (auto-prompted during install)
# Runs at 3 AM daily
# - Clears old cache
# - Removes unused Docker images
# - Optimizes database
# - Compresses logs
```

### Utility Scripts

Comprehensive maintenance scripts in `scripts/`:

```bash
# System Diagnostics - Complete health check
python scripts/system_diagnostics.py
  → Checks Ollama status, databases, disk usage
  → Detects common issues with fix suggestions
  → Shows performance metrics
  → Saves report to data/diagnostics_report.json

# Database Maintenance - Optimize and clean databases
python scripts/database_maintenance.py analyze   # Analyze all databases
python scripts/database_maintenance.py optimize  # Optimize and VACUUM
python scripts/database_maintenance.py cleanup   # Remove old data (30 days)
python scripts/database_maintenance.py all       # Run all operations

# Backup & Restore - Protect your data
python scripts/backup_restore.py create             # Create backup
python scripts/backup_restore.py create --include-logs  # With logs
python scripts/backup_restore.py list               # List backups
python scripts/backup_restore.py restore --backup-file <file> --confirm
python scripts/backup_restore.py cleanup --keep 5   # Keep only 5 recent

# Code Quality Check - AST-based analysis
python scripts/code_quality_check.py
  → Checks for missing docstrings
  → Identifies long functions (>100 lines)
  → Calculates quality score
  → Saves report to data/code_quality_report.txt

# Database Optimization - Quick database tune-up
python scripts/optimize_databases.py
  → Adds indexes for faster queries
  → Runs VACUUM to reclaim space
  → Runs ANALYZE for query optimization
```

### Database Management

```bash
# View stats
ryx ::status

# View cache
cat ~/ryx-ai/data/rag_knowledge.db

# Clear cache
rm ~/ryx-ai/data/cache/*

# Advanced database operations
python scripts/database_maintenance.py analyze
```

## 🐛 Troubleshooting

### Ollama not running

```bash
ollama serve
# or add to ~/.config/hyprland/hyprland.conf:
exec-once = ollama serve
```

### Slow responses

```bash
# Check which model is being used
ryx ::models

# Download faster model
ollama pull deepseek-coder:6.7b

# Set as default in configs/settings.json
```

### Permission denied

```bash
# Make sure ryx is executable
chmod +x ~/ryx-ai/ryx

# Recreate symlink
sudo ln -sf ~/ryx-ai/ryx /usr/local/bin/ryx
```

### Cache not working

```bash
# Check database
sqlite3 ~/ryx-ai/data/rag_knowledge.db "SELECT COUNT(*) FROM quick_responses;"

# Reset cache
rm ~/ryx-ai/data/rag_knowledge.db
# Will be recreated on next run
```

## 🤝 Contributing

Ryx is designed to improve itself! Use:

```bash
ryx ::improve analyze
```

This will:
1. Analyze all code
2. Find issues
3. Suggest improvements
4. Generate implementation plan

See `~/ryx-ai/data/improvement_plan.md` for details.

## 📝 License

MIT License - Use freely!

## 🙏 Acknowledgments

- Built with [Ollama](https://ollama.ai)
- Powered by [DeepSeek-Coder](https://github.com/deepseek-ai/DeepSeek-Coder)
- UI with [Rich](https://github.com/Textualize/rich)

## 🎯 Roadmap

- [ ] Plugin system for custom tools
- [ ] Voice input support
- [ ] Clipboard integration
- [ ] System-wide hotkey
- [ ] Mobile companion app
- [ ] Collaborative mode (share sessions)

---

**Made with ❤️ for the Arch Linux community**

*"AI so fast, it feels like telepathy"*