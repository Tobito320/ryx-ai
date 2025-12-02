# Ryx AI - Project Structure

```
ryx-ai/
├── ryx_main.py          # Main entry point - handles CLI args, starts session
├── install.sh           # System installation script
├── install_models.sh    # Ollama model installation
├── pyproject.toml       # Python package config
├── requirements.txt     # Python dependencies
│
├── core/                # Core AI engine (Python)
│   ├── ryx_brain.py     # Main brain - supervisor/operator architecture
│   ├── session_loop.py  # Interactive session handling
│   ├── ai_engine.py     # Ollama interface
│   ├── model_router.py  # Dynamic model selection
│   ├── intent_parser.py # Natural language understanding
│   ├── rag_system.py    # RAG knowledge management
│   ├── memory.py        # Episodic + persistent memory
│   ├── permissions.py   # Safety and permission system
│   └── ...              # Other core modules
│
├── ryx/                 # Ryx package (importable modules)
│   ├── core/            # Core components
│   │   ├── llm_router.py
│   │   ├── tool_executor.py
│   │   ├── workflow_orchestrator.py
│   │   ├── rag_manager.py
│   │   └── permission_manager.py
│   └── interfaces/      # User interfaces
│       ├── cli/         # CLI interface
│       └── web/         # RyxHub web interface (React)
│
├── ryx_core/            # Alternative core imports
│
├── modes/               # Operating modes
│   ├── cli_mode.py      # One-shot CLI mode
│   └── session_mode.py  # Interactive session mode
│
├── tools/               # Tool implementations
│   ├── browser.py       # Web browser control
│   ├── scraper.py       # Web scraping
│   ├── rag_ingest.py    # RAG ingestion
│   └── cache_validator.py
│
├── configs/             # Configuration files
│   ├── ryx_config.json  # Main config
│   ├── models.json      # Model definitions
│   ├── model_tiers.json # Model tier mappings
│   ├── safety.json      # Safety settings
│   └── permissions.json # Permission rules
│
├── data/                # Runtime data (gitignored)
│   ├── cache/           # Smart cache
│   ├── rag/             # RAG vector store
│   ├── knowledge/       # Learned knowledge
│   ├── scrape/          # Scraped content
│   ├── exports/         # Exported sessions
│   ├── sessions/        # Session history
│   └── *.db             # SQLite databases
│
├── docs/                # Documentation
│   ├── architecture/    # System design docs
│   ├── setup/           # Installation guides
│   ├── reference/       # Quick references
│   └── roadmap/         # Future plans
│
├── dev/                 # Development folder
│   ├── tests/           # Test files
│   ├── test_results/    # Test outputs
│   ├── handoffs/        # Context handoff docs
│   ├── experiments/     # Old versions, experiments
│   └── benchmarks/      # Performance benchmarks
│
├── scripts/             # Utility scripts
│   ├── local_verify.sh  # Local verification
│   └── ryx-preload.sh   # Preload for Hyprland
│
├── docker/              # Docker configs
├── logs/                # Runtime logs (gitignored)
└── venv/                # Python virtual environment
```

## Key Entry Points

- `ryx` command → `ryx_main.py` → `core/session_loop.py`
- RyxHub web → `ryx/interfaces/web/`
- Tests → `dev/tests/`

## Data Flow

1. User input → `ryx_main.py`
2. Intent parsing → `core/intent_parser.py`
3. Model selection → `core/model_router.py`
4. Execution → `core/ryx_brain.py` (supervisor) → tools
5. Response → user
