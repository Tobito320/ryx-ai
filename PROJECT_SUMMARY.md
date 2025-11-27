# Ryx AI - Complete Project Summary for Opus

## Current File Structure
```
~/ryx-ai/
├── ryx (main entry point - Python script)
├── core/
│   ├── __init__.py
│   ├── ai_engine.py (AI model interface)
│   ├── rag_system.py (cache & knowledge)
│   ├── permissions.py (3-level safety)
│   └── self_improve.py (self-analysis)
├── tools/
│   ├── __init__.py
│   ├── scraper.py
│   ├── browser.py
│   └── council.py
├── modes/
│   ├── __init__.py
│   ├── cli_mode.py (one-shot commands)
│   └── session_mode.py (interactive)
├── configs/
│   ├── settings.json
│   ├── permissions.json
│   ├── models.json
│   └── commands.json
└── data/
    ├── rag_knowledge.db (SQLite)
    └── cache/
```

## Key Issues Found During Usage
1. 404 errors from Ollama (random, no error handling)
2. Preferences not remembered (uses nano, should use nvim)
3. Knowledge base not persisting (shows 0 learned files)
4. Ctrl+C interrupts crash the session
5. No true multi-model orchestration
6. Cache works but not semantic

## Current Database Schema
```sql
CREATE TABLE knowledge (
    query_hash TEXT,
    file_path TEXT,
    confidence REAL
);

CREATE TABLE quick_responses (
    prompt_hash TEXT,
    response TEXT,
    model_used TEXT,
    ttl_seconds INTEGER
);
```

## Current Models Available
- deepseek-coder:6.7b (fast)
- Qwen3-Coder:30B (balanced)
- llama2-uncensored:7b (chat)

## Installation Context
- Python 3.11 in venv at ~/ryx-ai/.venv/
- Entry via /usr/local/bin/ryx wrapper script
- Ollama at localhost:11434
- All configs in ~/ryx-ai/configs/
