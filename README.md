# 🟣 Ryx AI - Local AI Agent for Arch Linux

Your intelligent terminal companion, powered by local AI models.

**Primary Interaction**: Just run `ryx` to start an interactive session.

## ✨ Key Features

- **Natural Language First**: No weird syntax - just type what you want
- **Intelligent Model Routing**: Automatically selects fast/balanced/powerful models
- **Tool Orchestration**: Filesystem, web, shell, and RAG tools with safety controls
- **Modern Terminal UI**: Themed output with Dracula/Nord/Catppuccin themes
- **Graceful Interrupts**: Ctrl+C saves state, continue where you left off
- **Context Aware**: Remembers conversation and learns preferences

## 🚀 Quick Start

```bash
# Start interactive session (recommended)
ryx

# Or run a single command
ryx "open hyprland config"
ryx "refactor the intent parser"
```

## 📋 Requirements

- **OS**: Arch Linux (or any Linux with Hyprland)
- **Python**: 3.11+
- **Ollama**: Running locally
- **RAM**: 16GB+ recommended
- **GPU**: AMD RX 7800 XT or similar (16GB VRAM ideal for larger models)

### Hardware Optimization (AMD 5900X + 7800 XT)

With your hardware, you can run:
- **qwen2.5-coder:14b** - Fits entirely in VRAM (14GB), fast inference
- **mistral:7b** - Ultra-fast, leaves room for other models
- **deepseek-coder-v2:16b** - Maximum capability, uses full VRAM

```bash
# Optimal model setup for 7800 XT (16GB VRAM)
ollama pull qwen2.5-coder:14b    # Primary coding model
ollama pull qwen2.5:3b           # Ultra-fast for simple tasks
ollama pull mistral:7b           # Fast general model

# Optional: For maximum capability (will use more VRAM)
ollama pull deepseek-coder-v2:16b
```

### ROCm Setup (AMD GPU)
```bash
# Ensure ROCm is properly configured
export HSA_OVERRIDE_GFX_VERSION=11.0.0  # For RDNA3 GPUs
```

## 🎯 Model Tiers

| Tier | Model | Best For |
|------|-------|----------|
| `fast` | mistral:7b | Quick tasks, chat |
| `balanced` | qwen2.5-coder:14b | Coding (default) |
| `powerful` | deepseek-coder-v2:16b | Complex code |
| `ultra` | Qwen3-Coder:30B | Architecture |
| `uncensored` | gpt-oss:20b | Personal chat |

Switch tiers in session: `/tier fast` or `ryx --tier powerful "prompt"`

## 📖 Usage

### Interactive Session (Recommended)
```bash
ryx
```

Shows:
```
╭────────────────────────────────────────────────────────────╮
│ 🟣 ryx – Local AI Agent
│
│ Tier: balanced (qwen2.5-coder:14b)
│ Repo: ~/ryx-ai
│ Safety: normal
╰────────────────────────────────────────────────────────────╯

ℹ️  Type naturally. Use /help for commands.

>
```

### Session Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/status` | Show current status |
| `/tier <name>` | Switch model tier |
| `/models` | List available models |
| `/tools` | List available tools |
| `/tool <name> on/off` | Toggle a tool |
| `/theme <name>` | Switch theme (dracula/nord/catppuccin) |
| `/themes` | List available themes |
| `/clear` | Clear conversation |
| `/save <title>` | Save conversation as note |
| `/quit` | Exit session |

### Direct Prompts
```bash
ryx "open hyprland config"          # File operation
ryx "refactor the intent parser"    # Coding task
ryx "search AI coding assistants"   # Web research
ryx --tier fast "what time is it"   # Quick query
```

### Safety Modes
```bash
ryx --strict   # Confirm all risky operations
ryx --loose    # Auto-approve most operations
```

## 🎨 UI Indicators

| Emoji | Meaning |
|-------|---------|
| 📋 | Plan |
| 🔍 | Search |
| 🌐 | Browse |
| 📂 | Files |
| 🛠️ | Edit |
| 🧪 | Test |
| 💾 | Commit |
| ✅ | Done |
| ❌ | Error |
| ⚠️ | Warning |

## 🔧 Configuration

### Environment Variables
```bash
export OLLAMA_BASE_URL=http://localhost:11434  # Default
export OLLAMA_BASE_URL=http://docker-host:11434  # Docker
```

### Config Files (`~/ryx-ai/configs/`)

- `models.json` - Model tiers and settings
- `safety.json` - Safety levels and blocked commands
- `settings.json` - General preferences

## 🏗️ Architecture

```
User Input
    ↓
Intent Classifier (LLM-based)
    ↓
Model Router (tier selection)
    ↓
Tool Registry (filesystem/web/shell/RAG)
    ↓
Ollama Client (streaming, retry)
    ↓
UI (purple theme, emoji)
```

See `docs/ARCHITECTURE.md` for details.

## 🧹 Maintenance

```bash
# Check health
/status              # In session
ryx "check health"   # Direct

# Cleanup
ryx "cleanup cache"
```

## 🔧 Troubleshooting

### Ollama not running
```bash
# Start Ollama
ollama serve
# Or set OLLAMA_BASE_URL for Docker
```

### Model not available
```bash
ollama pull qwen2.5-coder:14b
```

### Permission issues
```bash
chmod +x ~/ryx-ai/ryx
```

## 📝 License

MIT License

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai) - Local LLM runtime
- Powered by Qwen, DeepSeek, Mistral models

---

**Made with 🟣 for the Arch Linux community**
