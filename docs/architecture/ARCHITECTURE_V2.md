# Ryx AI V2 - Architecture Documentation

## Overview

Ryx is a production-grade local AI assistant designed to run entirely on local hardware using Ollama. It provides an interactive CLI experience similar to Claude Code / Gemini CLI, with automatic intent detection, model routing, and agentic workflows.

## System Requirements

- **CPU**: AMD Ryzen 9 5900X or equivalent
- **GPU**: AMD RX 7800 XT (16 GB VRAM) or equivalent
- **RAM**: 32 GB
- **OS**: Arch Linux with Hyprland (or any Linux with terminal)
- **Runtime**: Ollama (Docker or native)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        ryx (main entry)                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐ │
│  │ SessionLoop  │────▶│IntentClassif │────▶│ModelRouter   │ │
│  │ (UI/Input)   │     │ (LLM-based)  │     │ (Tiers)      │ │
│  └──────────────┘     └──────────────┘     └──────────────┘ │
│         │                    │                    │          │
│         ▼                    ▼                    ▼          │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐ │
│  │ Workflow     │────▶│ToolRegistry  │────▶│OllamaClient  │ │
│  │ Orchestrator │     │ (Tools)      │     │ (API)        │ │
│  └──────────────┘     └──────────────┘     └──────────────┘ │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────┐     ┌──────────────┐                      │
│  │ RAGSystem    │     │ MetaLearner  │                      │
│  │ (Caching)    │     │ (Preferences)│                      │
│  └──────────────┘     └──────────────┘                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Module Descriptions

### Core Modules

#### `core/intent_classifier.py`
LLM-based intent classification replacing brittle keyword lists.

**Intent Types:**
- `CHAT`: General conversation, Q&A
- `CODE_EDIT`: Refactoring, features, bugs
- `CONFIG_EDIT`: System configs (Hyprland, Waybar, etc.)
- `FILE_OPS`: Find/open/create/move files
- `WEB_RESEARCH`: Web search, scraping
- `SYSTEM_TASK`: Tests, diagnostics
- `KNOWLEDGE`: RAG notes management
- `PERSONAL_CHAT`: Uncensored conversation

**Strategy:**
1. Minimal rule layer for obvious patterns (greetings, short commands)
2. LLM classification for ambiguous cases
3. Returns intent type, confidence, and flags

#### `core/model_router_v2.py`
Intelligent model selection based on configurable tiers.

**Tiers:**
- `fast`: mistral:7b - Quick responses
- `balanced`: qwen2.5-coder:14b - Default coding (primary)
- `powerful`: deepseek-coder-v2:16b - Complex tasks
- `ultra`: Qwen3-Coder:30B - Heavy reasoning
- `uncensored`: gpt-oss:20b - Personal reflection

**Features:**
- Configurable via `configs/model_tiers.json`
- Docker-aware via `OLLAMA_BASE_URL` environment variable
- Automatic fallback chains
- Streaming support
- User overrides via `--tier` flag or `/tier` command

#### `core/tool_registry.py`
Unified interface for all tools available to the agent.

**Tool Categories:**
- **Filesystem**: search, read, write, patch, list
- **Web**: fetch, search (DuckDuckGo)
- **Shell**: command execution with safety controls
- **Git**: status, diff
- **System**: info, health checks

**Safety Levels:**
- `SAFE`: Auto-execute
- `RISKY`: Warn user
- `DANGEROUS`: Require confirmation

#### `core/workflow_orchestrator.py`
Manages multi-step agentic workflows.

**Workflow Steps:**
1. **Plan**: LLM produces numbered plan, shown to user
2. **Execute**: Call tools, feed outputs back to LLM
3. **Validate**: Run tests/linters if applicable
4. **Summary**: Bullet list of changes, TODOs

#### `core/session_loop.py`
Main interactive session handler.

**Features:**
- Natural language input
- Automatic intent detection
- Session persistence (survives Ctrl+C)
- Purple-themed UI with emoji indicators
- Slash commands (`/help`, `/status`, `/tier`, etc.)

#### `core/ui.py`
Purple-themed CLI interface.

**Components:**
- Color constants (ANSI codes)
- Emoji status indicators
- Formatted prompts and responses
- Progress indicators

### Configuration Files

#### `configs/model_tiers.json`
Model tier configuration:
```json
{
  "ollama_base_url": "http://localhost:11434",
  "tiers": {
    "fast": {"model": "mistral:7b", ...},
    "balanced": {"model": "qwen2.5-coder:14b", ...}
  },
  "default_tier": "balanced"
}
```

#### `configs/ryx_config.json`
UI and safety configuration:
```json
{
  "theme": {"primary_color": "purple", ...},
  "safety": {"level": "normal", ...},
  "session": {"max_history": 50, ...}
}
```

## Data Flow

### One-Shot Query
```
User Input → Intent Classification → Model Selection → Query → Response
                     ↓
              (Check Cache)
```

### Interactive Session
```
                    ┌──────────────┐
                    │  User Input  │
                    └──────┬───────┘
                           ▼
                    ┌──────────────┐
                    │ Parse Command│
                    └──────┬───────┘
                           ▼
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
       ┌──────────┐            ┌──────────────┐
       │ /command │            │ Natural Lang │
       └────┬─────┘            └──────┬───────┘
            │                         │
            ▼                         ▼
       ┌──────────┐            ┌──────────────┐
       │ Execute  │            │ Classify     │
       │ Command  │            │ Intent       │
       └────┬─────┘            └──────┬───────┘
            │                         │
            ▼                         ▼
       ┌──────────┐       ┌───────────┴───────────┐
       │ Response │       │                       │
       └──────────┘       ▼                       ▼
                    ┌──────────┐          ┌──────────────┐
                    │ Simple   │          │ Workflow     │
                    │ Query    │          │ (Complex)    │
                    └────┬─────┘          └──────┬───────┘
                         │                       │
                         ▼                       ▼
                    ┌──────────┐          ┌──────────────┐
                    │ Response │          │ Plan/Execute │
                    └──────────┘          └──────────────┘
```

## Ollama Docker Integration

Ryx supports Ollama running in Docker:

```bash
# Set Ollama URL for Docker
export OLLAMA_BASE_URL=http://localhost:11434

# Or via config file
# configs/model_tiers.json: "ollama_base_url": "http://host.docker.internal:11434"
```

## Available Models

**Primary Models (7B+ only):**
- `qwen2.5-coder:14b` - Main coding model (default)
- `SimonPu/Qwen3-Coder:30B-Instruct_Q4_K_XL` - Heavy reasoning
- `deepseek-coder-v2:16b` - Strong coder alternative
- `mistral:7b` - Medium general
- `llama2-uncensored:7b` - Medium uncensored
- `huihui_ai/gpt-oss-abliterated:20b` - Uncensored reflection

**DO NOT use as primary:**
- qwen2.5:3b, qwen2.5:1.5b, phi3:mini, llama3.2:1b, deepseek-coder:6.7b

## Safety Controls

### Command Execution
- **Blocked**: `rm -rf /`, `dd if=/dev`, fork bombs
- **Require Confirmation**: `rm -rf`, `chmod -R`, `git reset --hard`
- **Auto-Execute**: Read-only commands, safe operations

### Safety Levels
- `strict`: Maximum confirmation, minimum auto-execute
- `normal`: Balanced (default)
- `loose`: Minimal confirmation

## Extension Points

### Adding New Tools
```python
from core.tool_registry import BaseTool, ToolDefinition, ToolResult

class MyTool(BaseTool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="my_tool",
            description="My custom tool",
            category=ToolCategory.SYSTEM,
            parameters={...}
        )
    
    def execute(self, **kwargs) -> ToolResult:
        # Implementation
        return ToolResult(success=True, output="...")

# Register
registry = get_tool_registry()
registry.register(MyTool())
```

### Adding New Model Tiers
Edit `configs/model_tiers.json`:
```json
{
  "tiers": {
    "my_tier": {
      "model": "my-model:version",
      "fallbacks": ["fallback:model"],
      "description": "My custom tier",
      "max_tokens": 4096,
      "timeout_seconds": 60,
      "use_cases": ["custom"]
    }
  }
}
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_intent_parser_comprehensive.py -v
```

## Troubleshooting

### Ollama Connection Failed
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Or via Docker
docker run -p 11434:11434 ollama/ollama
```

### Model Not Available
```bash
# List available models
ollama list

# Pull a model
ollama pull qwen2.5-coder:14b
```

### Cache Issues
```bash
# Clear cache
ryx ::cache-check --fix

# Or manually
rm -rf data/rag_knowledge.db
```
