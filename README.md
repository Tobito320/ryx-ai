# 🟣 Ryx AI V2 - Local Agentic CLI

Your intelligent terminal companion powered by local AI models. Production-grade redesign with LLM-based intent classification, configurable model tiers, and agentic workflows.

## ✨ What's New in V2

### 🎯 Single Interactive Experience
```bash
ryx                           # Start interactive session
ryx "refactor the parser"     # One-shot query
ryx --tier powerful "..."     # Use specific model tier
```

**No more weird `ryx ::command` syntax** - just type naturally!

### 🧠 LLM-Based Intent Classification
- **Replaces brittle keyword lists** with intelligent classification
- Automatic detection of: CHAT, CODE_EDIT, CONFIG_EDIT, FILE_OPS, WEB_RESEARCH, SYSTEM_TASK
- Minimal rule layer for obvious patterns, LLM for ambiguous cases

### ⚡ Configurable Model Tiers
| Tier | Model | Use Case |
|------|-------|----------|
| `fast` | mistral:7b | Quick responses |
| `balanced` | qwen2.5-coder:14b | Default coding (primary) |
| `powerful` | deepseek-coder-v2:16b | Complex tasks |
| `ultra` | Qwen3-Coder:30B | Heavy reasoning |
| `uncensored` | gpt-oss:20b | Personal reflection |

### 🔧 Agentic Workflows
For complex tasks, Ryx automatically:
1. 📋 **Plan**: Generate numbered plan
2. 🔍 **Execute**: Call tools, feed outputs back
3. 🧪 **Validate**: Run tests/linters
4. ✅ **Summarize**: Bullet list of changes

### 🎨 Purple-Themed UI
```
🟣 ryx – Local AI Agent | Tier: balanced (qwen2.5-coder:14b)

📋 Planning...
  🔍 Step 1: Search for files
  🛠️ Step 2: Apply changes
  ✅ Done
```

## 🚀 Quick Start

### Installation
```bash
git clone https://github.com/Tobito320/ryx-ai
cd ryx-ai
pip install -r requirements.txt
chmod +x ryx
sudo ln -sf $(pwd)/ryx /usr/local/bin/ryx
```

### Usage
```bash
# Start interactive session
ryx

# One-shot queries
ryx "how do I reload hyprland?"
ryx "refactor the intent parser"
ryx "edit my waybar config"

# Use specific tier
ryx --tier powerful "design a REST API"
ryx --tier ultra "analyze this architecture"

# Session commands
/help       Show help
/status     Current status
/tier fast  Switch tier
/clear      Clear history
/quit       Exit
```

## 📖 Examples

### Refactoring Code
```bash
ryx "refactor the intent parser to use LLM classification"

📋 Planning...
  1. Read current intent_parser.py
  2. Design new LLM-based classification
  3. Implement changes
  4. Run tests

  🔍 Step 1: Reading file...
  🛠️ Step 2: Applying changes...
  🧪 Step 3: Running tests...
  ✅ Done

**Summary**
- Replaced keyword lists with LLM classification
- Added IntentType enum
- All 29 tests passing
```

### Config Editing
```bash
ryx "analyze my Hyprland config, research best practices, update it"

🌐 Searching for Hyprland best practices...
📂 Reading ~/.config/hypr/hyprland.conf...
📋 Generating improvements...

Suggested changes:
1. Add workspace animation settings
2. Optimize window rules
3. Add screenshot keybinds

Apply changes? [y/N]
```

### Web Research
```bash
ryx "research AI coding assistants, scrape and store comparison note"

🔍 Searching: AI coding assistants comparison
🌐 Found 5 results

1. **Top AI Coding Assistants 2024**
   https://example.com/...
   
💾 Saved note to knowledge base
```

### Uncensored Conversation
```bash
ryx --tier uncensored "have an honest conversation about..."

⚠️ (uncensored mode)

[Response without filters]
```

## 🛠️ Configuration

### Model Tiers (`configs/model_tiers.json`)
```json
{
  "ollama_base_url": "http://localhost:11434",
  "tiers": {
    "fast": {"model": "mistral:7b", ...},
    "balanced": {"model": "qwen2.5-coder:14b", ...},
    "powerful": {"model": "deepseek-coder-v2:16b", ...}
  },
  "default_tier": "balanced"
}
```

### Safety Settings (`configs/ryx_config.json`)
```json
{
  "safety": {
    "level": "normal",
    "require_confirmation": ["rm -rf", "chmod -R"],
    "block": ["rm -rf /", "dd if=/dev"]
  }
}
```

## 🏗️ Architecture

```
ryx (main entry)
    │
    ├─► SessionLoop (UI/Input)
    │       │
    │       ├─► IntentClassifier (LLM-based)
    │       │       └─► Returns: CHAT, CODE_EDIT, CONFIG_EDIT, etc.
    │       │
    │       ├─► ModelRouter (Tier selection)
    │       │       └─► fast/balanced/powerful/ultra/uncensored
    │       │
    │       └─► WorkflowOrchestrator (Complex tasks)
    │               └─► Plan → Execute → Validate → Summary
    │
    ├─► ToolRegistry
    │       ├─► Filesystem (search, read, write, patch)
    │       ├─► Web (fetch, search)
    │       ├─► Shell (with safety controls)
    │       └─► Git (status, diff)
    │
    └─► RAGSystem (Caching)
```

See [docs/ARCHITECTURE_V2.md](docs/ARCHITECTURE_V2.md) for detailed documentation.

## 📋 Requirements

- **OS**: Linux (Arch Linux recommended)
- **Python**: 3.11+
- **Ollama**: Running locally or in Docker
- **GPU**: AMD RX 7800 XT (16 GB VRAM) or equivalent
- **RAM**: 32 GB recommended

### Recommended Models
```bash
ollama pull qwen2.5-coder:14b      # Default coding
ollama pull deepseek-coder-v2:16b  # Complex tasks
ollama pull mistral:7b             # Fast responses
```

## 🧪 Testing
```bash
# Run all tests
python -m pytest tests/ -v

# Run new V2 architecture tests
python -m pytest tests/test_v2_architecture.py -v
```

## 🔧 Troubleshooting

### Ollama not running
```bash
# Start Ollama
ollama serve

# Or set custom URL
export OLLAMA_BASE_URL=http://localhost:11434
```

### Model not available
```bash
# List available models
ollama list

# Pull missing model
ollama pull qwen2.5-coder:14b
```

### Slow responses
```bash
# Switch to faster tier
/tier fast

# Or use --tier flag
ryx --tier fast "quick question"
```

## 📝 License

MIT License - Use freely!

## 🙏 Acknowledgments

- Built with [Ollama](https://ollama.ai)
- Models: Qwen2.5-Coder, DeepSeek-Coder, Mistral
- Designed for Arch Linux with Hyprland

---

**🟣 Ryx AI V2** - *Local AI that just works*