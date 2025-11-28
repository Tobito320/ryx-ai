# Ryx AI - Critical Issues & Redesign Plan

**Created**: 2025-11-28
**Status**: 🚨 **URGENT - Multiple Critical Issues**
**Impact**: System unusable for intended purpose

---

## 🔴 Critical Bugs (FIXED)

### 1. Session Mode Crash ✅
**Status**: FIXED in commit 41d6400
**Issue**: Missing `Optional` import caused crash
**Fix**: Added `from typing import Optional`

### 2. ::models Command Crash ✅
**Status**: FIXED in commit 41d6400
**Issue**: Used non-existent `AIEngine()` class
**Fix**: Removed incorrect call, use subprocess directly

---

## 🔴 Critical Issues (NEED FIXING)

### 1. **Hallucination - Treating Prompts as Bash Commands**

**Problem**: Ryx interprets natural language as literal bash commands

```bash
$ ryx hello
# Tries to execute: hi
✗ hi: command not found

$ ryx wie gehts dir
# Tries to execute: echo ... | notify-send ...
# Should just chat, not execute commands
```

**Root Cause**: The AI model is too eager to generate bash commands. Every prompt gets interpreted as needing command execution.

**Impact**: 🔴 CRITICAL - Makes basic conversation impossible

---

### 2. **Cached Responses Don't Execute**

**Problem**: When a response is cached, it shows the command but doesn't execute it

```bash
$ ryx open hyprland config
▸ Opening /home/tobi/.config/hypr/hyprland.conf
# Works first time

$ ryx open hyprland config
[cached]
nvim /home/tobi/.config/hypr/hyprland.conf
# Second time - just shows command, doesn't execute!
```

**Root Cause**: Cache returns the formatted response text, but the execution logic doesn't run for cached responses.

**Impact**: 🔴 CRITICAL - Makes caching useless

---

### 3. **No Auto-Start for Ollama**

**Problem**: `ryx` alone should wake up Ollama if not running

```bash
$ ryx
# Shows: Ollama: Offline
# Should: Start Ollama automatically
```

**Expected Behavior**:
1. User types `ryx` or `ryx "hello"`
2. Ryx checks if Ollama is running
3. If not, starts it automatically
4. Waits for it to be ready
5. Then processes the query

**Impact**: 🟡 HIGH - Poor user experience

---

### 4. **No Intent-Based Parsing**

**Problem**: Ryx doesn't understand INTENT, only treats everything as commands

**What User Wants**:
```bash
$ ryx hyprland config
# Should: Locate and show path only
# Currently: Tries to execute something random

$ ryx open hyprland config
# Should: Execute nvim in SAME terminal
# Currently: Unreliable, sometimes works

$ ryx open hyprland config in new terminal
# Should: Open in NEW terminal window
# Currently: Sometimes works

$ ryx look up hyprland
# Should: Open browser and search
# Currently: Tries random command
```

**Keywords That Should Determine Action**:
- **No keyword** = Just locate, show path
- **"open"** = Execute nvim in same terminal
- **"open ... new terminal"** = Execute in new window
- **"look up", "browse", "google", "search"** = Use browser
- **"find"** = Search filesystem

**Impact**: 🔴 CRITICAL - Core UX is broken

---

### 5. **No Seamless Model Switching**

**Problem**: User wants to switch models naturally in the prompt

**What User Wants**:
```bash
$ ryx hello, switch to deepseek
# Should: Switch to deepseek-coder:6.7b and respond

$ ryx use fast model please
# Should: Switch to qwen2.5:1.5b

$ ryx this is complex, use the powerful model
# Should: Auto-detect and switch to bigger model
```

**Current State**: No natural language switching, only manual `::` commands

**Impact**: 🟡 HIGH - User wants seamless experience

---

### 6. **No Intelligent Model Selection**

**Problem**: Always uses qwen2.5:1.5b, even for complex queries

**What User Wants**:
- Analyze query complexity (0.0 - 1.0 scale)
- Simple queries (< 0.3): qwen2.5:1.5b (fast, 1.5B params)
- Medium queries (0.3 - 0.7): deepseek-coder:6.7b (balanced)
- Complex queries (> 0.7): Largest available model

**Complexity Indicators**:
- **Low**: "hello", "what time is it", "open file"
- **Medium**: "explain X", "find all Y", "how do I Z"
- **High**: "write code for X", "debug this error", "refactor"

**Impact**: 🟡 MEDIUM - Would improve quality

---

### 7. **Opening Files in Same Terminal Doesn't Work**

**Problem**: When executing `nvim file.txt`, nothing happens or hangs

**Root Cause**: Subprocess execution doesn't properly handle interactive programs

**Fix Needed**: For "open" commands, use `os.execvp()` or proper terminal handling

**Impact**: 🔴 CRITICAL - Core feature broken

---

## 🎯 Redesign Requirements

### Phase 1: Intent-Based Parser (CRITICAL)

**Create**: `core/intent_parser.py`

```python
class IntentParser:
    def parse(self, prompt: str) -> Intent:
        """
        Parse user intent from natural language

        Returns Intent object with:
        - action: "locate" | "execute" | "browse" | "chat"
        - target: What to act on (e.g., "hyprland config")
        - modifiers: ["new_terminal", "fast_model", etc.]
        """
```

**Detection Rules**:
1. Check for action keywords FIRST
2. If no action keyword → default to "chat" (just conversation)
3. Extract target and modifiers

**Keywords**:
- **Execute**: "open", "edit", "run"
- **Browse**: "look up", "browse", "google", "search", "what is"
- **Locate**: "find", "where is", "show me"
- **Chat**: Everything else (default)

---

### Phase 2: Fix Cached Execution

**Problem**: Cache returns text, doesn't trigger execution

**Solution**:
```python
# In cli_mode.py handle_prompt()
cached = self.rag.query_cache(prompt)
if cached:
    # Parse the cached response
    if "▸ Opening" in cached or "▸ Executing" in cached:
        # Extract and execute the command
        cmd = extract_command(cached)
        self.executor.execute(cmd)
    else:
        # Just show the cached text
        print(cached)
```

---

### Phase 3: Auto-Start Ollama

**Create**: `core/ollama_manager.py`

```python
class OllamaManager:
    def ensure_running(self) -> bool:
        """Start Ollama if not running, return True if ready"""
        if self.is_running():
            return True

        print("🚀 Starting Ollama...")
        subprocess.run(['systemctl', '--user', 'start', 'ollama'])

        # Wait up to 10s for it to be ready
        for _ in range(10):
            if self.is_running():
                print("✓ Ollama ready")
                return True
            time.sleep(1)

        return False
```

---

### Phase 4: Intelligent Model Selection

**Enhance**: `core/model_orchestrator.py`

```python
def analyze_complexity(self, prompt: str) -> float:
    """
    Return complexity score 0.0 - 1.0

    Factors:
    - Length (longer = more complex)
    - Keywords ("explain", "debug", "write code" = high)
    - Technical terms (count programming terms)
    - Questions (how, why = medium)
    """

def select_model(self, complexity: float) -> str:
    """
    Select model based on complexity

    < 0.3: qwen2.5:1.5b (fast)
    0.3-0.7: deepseek-coder:6.7b (balanced)
    > 0.7: largest available (powerful)
    """
```

---

### Phase 5: Natural Language Model Switching

**Add to Intent Parser**:
```python
# Detect model switch requests
if "switch to deepseek" in prompt.lower():
    return Intent(
        action="switch_model",
        target="deepseek-coder:6.7b",
        original_prompt=remove_switch_request(prompt)
    )
```

---

## 📋 Implementation Priority

### Must Fix Now (Phase 1)
1. ✅ Session mode crash (FIXED)
2. ✅ ::models crash (FIXED)
3. 🔴 Intent-based parser (CRITICAL)
4. 🔴 Fix cached execution (CRITICAL)
5. 🔴 Fix "open file" in same terminal (CRITICAL)

### Should Fix Soon (Phase 2)
6. 🟡 Auto-start Ollama
7. 🟡 Intelligent model selection
8. 🟡 Natural language model switching

### Nice to Have (Phase 3)
9. 🟢 Enhanced browsing (fix URL scraping)
10. 🟢 Better error messages
11. 🟢 Improved caching logic

---

## 🧪 Test Cases

### Must Pass Before Release

```bash
# 1. Basic conversation (no command execution)
$ ryx hello
> Hello! How can I help you?
# ✓ Should NOT execute any command

# 2. Locate file (show path only)
$ ryx hyprland config
> Found: /home/tobi/.config/hypr/hyprland.conf
# ✓ Should NOT open file

# 3. Open file (same terminal)
$ ryx open hyprland config
# ✓ Should execute: nvim /home/tobi/.config/hypr/hyprland.conf
# ✓ Should open IN same terminal

# 4. Open file (new terminal)
$ ryx open hyprland config in new terminal
# ✓ Should execute: kitty -e nvim /path
# ✓ Should open in NEW terminal

# 5. Web search
$ ryx look up hyprland
# ✓ Should open browser with search

# 6. Auto-start
$ ollama stop
$ ryx hello
# ✓ Should start Ollama automatically
# ✓ Should respond after startup

# 7. Cached execution
$ ryx open waybar config  # First time
$ ryx open waybar config  # Second time (cached)
# ✓ Both should execute nvim, not just show command

# 8. Model switching
$ ryx please use deepseek
# ✓ Should switch to deepseek-coder:6.7b

# 9. Auto complexity detection
$ ryx write a python function to parse JSON
# ✓ Should automatically use deepseek (complex query)
```

---

## 💡 Architecture Changes

### Current Flow (BROKEN)
```
User Prompt → AI Model → Always Generates Bash → Execute/Fail
```

### New Flow (CORRECT)
```
User Prompt
  → Intent Parser (action, target, modifiers)
  → Route to Handler:
     - chat → AI conversation (no execution)
     - locate → Find file, show path
     - execute → Find + run command in terminal
     - browse → Open browser
  → Execute if needed
  → Cache result with intent metadata
```

---

## 🚀 Quick Wins

### Fix Right Now (< 1 hour)
1. Add simple keyword detection before AI query
2. If prompt has no action keywords → skip command execution
3. Fix cached response execution

### Implementation:
```python
# In cli_mode.py, before AI query:
action_keywords = ["open", "edit", "run", "browse", "look up", "find", "search"]
has_action = any(kw in prompt.lower() for kw in action_keywords)

if not has_action:
    # Just chat, no commands
    result = self.ai.query(prompt, context="chat only, no commands")
    print(result.response)
    return
```

---

## 📝 Notes

- User wants **seamless, natural language** experience
- **1.5B model should be default** for speed
- **Auto-upgrade to 6.7B** for complex queries
- **Intent matters more than literal commands**
- **Caching should preserve execution**, not just text

---

**Action Required**: Implement Phase 1 fixes ASAP to make Ryx usable.
