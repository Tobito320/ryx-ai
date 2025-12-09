# Ryx AI - Memory & Self-Improvement System

This document describes the persistent memory system, VRAM guard, and doctor command that enable Ryx AI to learn, remember, and self-improve across sessions.

## Overview

The memory system consists of three main components:

1. **PersistentMemory** - Encrypted SQLite storage for facts, preferences, and session context
2. **VRAMGuard & ModelManager** - GPU memory monitoring and safe model loading
3. **Doctor** - Health checking and self-healing command

## Persistent Memory System

### Features

- **Encrypted Storage**: All memory entries are encrypted using a machine-specific key
- **User Preferences**: Persistent user preferences (language, VRAM limits, theme, etc.)
- **Session Continuity**: Session stitching for seamless memory across reboots
- **Error Pattern Learning**: Learn from errors and recall fixes for self-healing
- **Importance-Based Recall**: Keyword matching with recency and importance weighting

### Usage

```python
from core.memory import get_persistent_memory, MemoryType

# Get the memory singleton
memory = get_persistent_memory()

# Store facts
memory.store_fact("user_name", "Tobi")
memory.store_fact("home_dir", "/home/tobi", importance=2.0)

# Store preferences (higher importance)
memory.store_preference("ai_sidebar_auto_load", False)
memory.store_preference("max_vram_percent", 90.0)

# Retrieve values
name = memory.get("user_name")  # "Tobi"

# Recall by keywords
results = memory.recall("config hyprland")
for entry in results:
    print(f"{entry.key}: {entry.value}")
```

### User Preferences

```python
# Get preferences (cached)
prefs = memory.get_preferences()

# Available preferences:
# - language: str = "de"
# - device: str = "arch-linux"
# - vram_mb: int = 16000
# - max_vram_percent: float = 90.0
# - ai_sidebar_auto_load: bool = False
# - concise_responses: bool = True
# - theme: str = "dark"
# - keyboard_first: bool = True

# Modify and save
prefs.language = "en"
prefs.max_vram_percent = 85.0
memory.save_preferences(prefs)
```

### Session Management

```python
# Start a new session
session_id = memory.start_session()

# Track progress
memory.update_session_stats(session_id, tasks_completed=5, tasks_failed=1)

# End session with summary
memory.end_session(session_id, summary="Implemented feature X")

# Get last session for continuity
last = memory.get_last_session()
```

### Error Pattern Learning

```python
# Learn from an error
error_sig = "ModuleNotFoundError: No module named 'requests'"
fix = "pip install requests"
memory.learn_error_fix(error_sig, fix, success=True)

# Recall fix when error occurs again
fix = memory.find_error_fix(error_sig)  # Returns "pip install requests"
```

### Maintenance

```python
# Compact old, low-importance memories
deleted = memory.compact(days_threshold=30, min_importance=0.3)

# Get statistics
stats = memory.get_stats()
# {
#   "total_memories": 42,
#   "by_type": {"fact": 30, "preference": 12},
#   "total_sessions": 5,
#   "error_patterns": 3,
#   "db_size_mb": 1.2
# }
```

## VRAM Guard

Monitors GPU VRAM usage to prevent system instability. Designed for AMD RX 7800 XT (16GB VRAM) with max 90% usage.

### Features

- **VRAM Monitoring**: Uses ROCm tools or sysfs for AMD GPUs
- **Model VRAM Estimation**: Estimates VRAM requirements per model
- **Safe Loading**: Refuses to load models that would exceed 90% VRAM
- **User Feedback**: Suggests unloading models or CPU offload

### Usage

```python
from core.vram_guard import get_vram_guard, get_model_manager, LoadAction

# Check VRAM status
guard = get_vram_guard()
status = guard.get_vram_status()

print(f"VRAM: {status.used_mb}MB / {status.total_mb}MB ({status.usage_percent:.1f}%)")
print(f"Safe: {status.is_safe}")
print(f"Available: {status.available_mb}MB")

# Check if model can be loaded
decision = guard.can_load("qwen2.5-coder:14b")
if decision.action == LoadAction.LOAD:
    print("Safe to load")
elif decision.action == LoadAction.UNLOAD_FIRST:
    print(f"Unload first: {decision.models_to_unload}")
elif decision.action == LoadAction.REFUSE:
    print(f"Cannot load: {decision.suggestion}")
```

### Model Manager

Higher-level API for model management:

```python
manager = get_model_manager()

# Safe model loading with auto-unload
success, message = manager.load_model("qwen2.5-coder:14b", auto_unload=True)

# Get comprehensive status
status = manager.get_status()
# {
#   "vram": {"total_mb": 16384, "used_mb": 8000, ...},
#   "loaded_models": [...],
#   "available_models": [...]
# }
```

## Doctor Command

Comprehensive health check and self-healing system.

### Features

- Checks Ollama connectivity and models
- Checks database integrity
- Checks memory system health
- Checks VRAM and disk space
- Runs self-healing routines
- Generates actionable fix suggestions

### CLI Usage

```bash
# Run health check
ryx /doctor

# Or programmatically
python -m core.doctor
```

### Programmatic Usage

```python
from core.doctor import run_doctor, Doctor

# Run all checks
report = run_doctor(auto_heal=True)

# Print summary
print(report.summary())

# Check status
if report.is_healthy:
    print("System is healthy")
else:
    print(f"Issues: {report.total_issues} ({report.critical_issues} critical)")

# Get individual checks
for check in report.checks:
    print(f"{check.name}: {check.status.value} - {check.message}")
    if check.fix_suggestion:
        print(f"  Fix: {check.fix_suggestion}")
```

### Health Checks Performed

| Check | Description |
|-------|-------------|
| Ollama Service | Checks connectivity to Ollama |
| Ollama Models | Checks for recommended models |
| Databases | Checks SQLite database integrity |
| Memory System | Checks persistent memory health |
| Configuration | Validates JSON config files |
| Paths | Checks directory permissions |
| VRAM | Checks GPU memory usage |
| Disk Space | Checks available disk space |
| Cache | Checks cache size |
| Self-Healing | Runs cleanup routines |

## Memory Types

| Type | Description | Default Importance |
|------|-------------|-------------------|
| FACT | Learned facts about user/system | 1.0 |
| PREFERENCE | User preferences | 2.0 |
| SESSION | Session context and history | 1.0 |
| SKILL | Learned skills and patterns | 1.5 |
| ERROR | Error patterns and fixes | 1.0 |

## Best Practices

1. **Store Important Facts**: Store facts that help Ryx understand the user's environment
2. **Use Preferences**: Store user preferences to personalize behavior
3. **Learn from Errors**: Always store error fixes to enable self-healing
4. **Run Doctor Regularly**: Run `/doctor` to check system health
5. **Monitor VRAM**: Check VRAM before loading large models
6. **Compact Memory**: Run compaction periodically to clean old entries

## Integration with Self-Improvement Loop

The memory system integrates with the EXPLORE → PLAN → APPLY → VERIFY loop:

1. **EXPLORE**: Check memory for similar past tasks
2. **PLAN**: Use learned patterns to improve planning
3. **APPLY**: Track changes for recovery
4. **VERIFY**: Store success/failure for future learning

## Security Notes

- Memory is encrypted with a machine-specific key
- XOR encryption provides basic obfuscation (not cryptographically strong)
- For production, consider using `cryptography.fernet`
- Database is stored in `~/.ryx-ai/data/persistent_memory.db`
