# Ryx AI - Session Handoff Document

**Date**: 2025-12-02
**Session Goal**: Build Ryx into a Claude Code / Copilot CLI-like local AI assistant

---

## 🎯 CURRENT STATE SUMMARY

Ryx is a local AI terminal assistant using Ollama. UI has been redesigned with color-coded output. Code tasks now actually write files.

### ✅ What Works
- **Code Tasks**: `create file.py` → generates and writes actual code
- **Phase System**: EXPLORE → PLAN → APPLY → VERIFY workflow
- **Color-Coded Output**: Purple=User, Cyan=Steps, Green=Reply, Yellow=Confirm, Red=Error
- **German Filler Words**: "mal", "doch", "halt" ignored in config matching
- **Streaming**: Token output with tok/s stats
- **@ for files**, **! for shell**

### ❌ What's Broken (TODO)
See TODO section below.

---

## 📁 KEY FILES

```
core/
├── cli_ui.py         # UI components (needs fixing for fixed bar)
├── session_loop.py   # Main loop
├── ryx_brain.py      # Intent classification + execution
├── phases.py         # EXPLORE→PLAN→APPLY→VERIFY
├── checkpoints.py    # Undo/rollback system
├── model_router.py   # Model selection by task
├── ollama_client.py  # Ollama API client
└── tools.py          # Tool registry
```

---

## 🚨 TODO: FIXED BOTTOM BAR (HIGH PRIORITY)

### Current Problem
- Bar regeneriert sich jedes Mal neu
- Nicht fixiert am unteren Rand
- Weit vom Ziel entfernt

### Target Design
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ~/ryx-ai [⎇ main*]                              qwen2.5-coder:14b ● 10% ctx│
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ > user prompt here (expands with content)                                   │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ Ctrl+c Exit · Ctrl+r Expand recent                         42 requests left │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Requirements

1. **Fixed Position**
   - Bar bleibt IMMER unten am Terminal fixiert
   - Scrollt nicht mit Content
   - Wie in Claude CLI / Copilot CLI

2. **Top Line (über der Box)**
   - Links: `~/path [⎇ branch*]` (mit * wenn uncommitted changes)
   - Rechts: `model-name ● X% ctx` oder `● Truncated` (rot wenn >90%)

3. **Prompt Box (Mitte)**
   - Expandiert sich mit dem Prompt-Inhalt
   - User tippt innerhalb der Box
   - Box hat Rahmen

4. **Bottom Line (unter der Box)**
   - Links: `Ctrl+c Exit · Ctrl+r Expand recent`
   - Rechts: `N requests left` oder ähnliche Session-Info

5. **Context Indicator**
   - Zeigt Kontext-Auslastung: `10% ctx`, `50% ctx`, `90% ctx`
   - Wird rot + "Truncated" wenn Kontext abgeschnitten wird
   - Warnt User wenn Antworten langsam/schlecht werden

### Implementation Notes
- Wahrscheinlich `rich.Live` oder Terminal escape codes nötig
- Alternativer Ansatz: `prompt_toolkit` für echte fixed UI
- Könnte auch `curses` sein, aber komplexer

---

## 🎨 COLOR SCHEME (Catppuccin Mocha)

```python
COLORS = {
    "user_prompt": "#cba6f7",   # Purple - user input
    "step": "#89dceb",          # Cyan - progress
    "reply": "#a6e3a1",         # Green - AI response
    "confirm": "#f9e2af",       # Yellow - confirmation
    "error": "#f38ba8",         # Red - errors
    "info": "#89b4fa",          # Blue - info
    "muted": "#6c7086",         # Gray - dim text
    "path": "#fab387",          # Peach - file paths
    "branch": "#94e2d5",        # Teal - git branch
    "model": "#f5c2e7",         # Pink - model name
}
```

---

## 🔧 MODELS INSTALLED

```
qwen2.5:1.5b           # Fast - intent classification
qwen2.5:7b             # Balanced - general chat
qwen2.5-coder:14b      # Code generation
deepseek-r1:14b        # Reasoning/thinking
nomic-embed-text       # Embeddings (unused)
```

---

## 📋 OTHER TODOS (Lower Priority)

1. **Diff Preview Before Apply**
   - Show diff in box
   - Ask for confirmation before writing

2. **Better Error Recovery**
   - Retry code generation with more context
   - Fallback to simpler plan

3. **Precision Mode Indicator**
   - Show when using larger model
   - Display in top bar

4. **Context Window Tracking**
   - Count tokens in conversation
   - Warn when approaching limit
   - Auto-summarize old messages

5. **Git Integration**
   - Show uncommitted changes indicator (*)
   - Auto-commit after successful tasks

---

## 🚀 HOW TO TEST

```bash
# Start interactive session
cd /home/tobi/ryx-ai
source venv/bin/activate
python ryx_main.py

# Test cases:
> create hello.py with a greeting function    # Should create file
> öffne hyprland config                       # Should open file
> öffne hyprland config mal                   # "mal" ignored
> erkläre rekursion                           # Should search + respond
```

---

## 📝 SESSION LOG (2025-12-02)

### Done
- ✅ UI color coding (purple/cyan/green/yellow/red)
- ✅ Code tasks write files (`core/phases.py` fixed)
- ✅ German filler words ignored
- ✅ Code task detection before file open detection
- ✅ Phase visualization (EXPLORE→PLAN→APPLY→VERIFY)

### Files Changed
- `core/cli_ui.py` - Color-coded output
- `core/ryx_brain.py` - Code task detection order, filler words
- `core/phases.py` - Actually writes files now
- `core/session_loop.py` - Uses new UI
- `ryx_main.py` - Cleaned up

### Next Priority
- **Fix the bottom bar** - Should be fixed position, not regenerating

