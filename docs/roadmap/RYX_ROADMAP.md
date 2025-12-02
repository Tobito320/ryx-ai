# Ryx AI Development Roadmap

> **Vision**: Ultra-fast, lightweight AI assistant focused on the 1.5B model for instant, natural language system commands with minimal resource usage.

---

## 🎯 Core Principles

1. **Speed First**: Sub-second responses for basic commands
2. **Resource Conscious**: Minimize RAM/VRAM usage, lazy load everything
3. **Smart, Not Mysterious**: Execute commands directly, don't just suggest
4. **Learn & Adapt**: Cache intelligently, learn user preferences with permission
5. **1.5B is King**: Only escalate to larger models when absolutely necessary

---

## 🔴 CRITICAL - System Unusable (Fix Immediately)

### Current Blockers (Commit c5d752a: "errors need to be resolved, system unusable")

- [ ] **Fix psutil dependency**
  - Health Monitor requires psutil for CPU/memory/GPU monitoring
  - Either: Add to requirements.txt OR remove dependency from health_monitor.py
  - File: `/home/user/ryx-ai/requirements.txt`

- [ ] **Fix database schema mismatch**
  - `meta_learning.db` has old schema (key, timestamp, usage_count)
  - Code expects new schema (category, learned_at, times_applied)
  - Causes IndexError when loading preferences
  - File: `/home/user/ryx-ai/core/meta_learner.py`
  - Solution: Schema migration or rebuild database

- [ ] **Test basic functionality**
  - Verify `ryx hello` works
  - Verify model loading (1.5B only)
  - Verify cache system works
  - Run: `python tests/test_v2_integration.py`

---

## 🟠 HIGH PRIORITY - Core 1.5B Functionality

### Command Execution System

- [ ] **Implement natural language file opening**
  - Input: `ryx open hyprland config`
  - Expected: Find `~/.config/hypr/hyprland.conf`, execute `nvim ~/.config/hypr/hyprland.conf`
  - Requirements:
    - Small AI (1.5B) finds file matching description
    - If multiple matches, check file contents to disambiguate
    - Execute instantly with user's preferred editor (nvim)
    - NO terminal output of commands - just execute
  - Files to modify:
    - New: `/home/user/ryx-ai/core/command_executor.py`
    - Modify: `/home/user/ryx-ai/modes/cli_mode.py`

- [ ] **Implement app launching**
  - Input: `ryx open waypaper` OR `ryx please open waypapr` (typo)
  - Expected: Launch waypaper instantly
  - Requirements:
    - Typo tolerance (waypapr → waypaper)
    - Natural language flexibility ("please open", "launch", "run", "start")
    - Execute program directly
    - Response time < 0.5 seconds
  - Files to modify:
    - `/home/user/ryx-ai/core/command_executor.py`
    - `/home/user/ryx-ai/core/model_orchestrator.py` (optimize 1.5B prompts)

### Caching System Fixes

- [ ] **Fix cache misuse**
  - Current Problem: Returns cached wrong answers blindly
  - Example: User asks `ryx open hyperland config`
    - Cached: `nano hyperland/config` (WRONG path, WRONG editor)
    - Should: Check cache, validate path exists, use correct editor preference, execute
  - Requirements:
    - Cache should store VALIDATED knowledge only
    - Cache should be used for speed, not as replacement for intelligence
    - Always verify cached file paths still exist
    - Always apply current user preferences (nvim not nano)
  - Files to modify:
    - `/home/user/ryx-ai/core/rag_system.py`
    - `/home/user/ryx-ai/core/ai_engine_v2.py`

- [ ] **Implement smart memory with user confirmation**
  - After successful command: "Should I memorize that? y/n"
  - Store:
    - File paths (hyprland.conf → ~/.config/hypr/hyprland.conf)
    - App names and locations
    - User preferences (editor, terminal, browser)
    - Common directory shortcuts
  - Files to modify:
    - `/home/user/ryx-ai/core/rag_system.py`
    - New: `/home/user/ryx-ai/core/memory_manager.py`

### Resource Optimization

- [ ] **Optimize startup strategy**
  - Benchmark: Time to load minimal Ryx + 1.5B model
  - Decision Tree:
    - If < 5 seconds: Load at system boot
    - If 5-10 seconds: Load on first `ryx` command
    - If > 10 seconds: Lazy load even 1.5B
  - Current status: ~2s to load 1.5B (GOOD for boot)
  - Files to modify:
    - `/home/user/ryx-ai/ryx` (main entry point)
    - New: `/home/user/ryx-ai/systemd/ryx-preload.service` (if boot approach)

- [ ] **Minimize resource footprint**
  - Target idle state: < 50MB RAM, 0 VRAM (unload 1.5B when truly idle)
  - Only load 1.5B on actual query, not on `ryx` invocation
  - Optimize model_orchestrator.py to free VRAM aggressively
  - Files to modify:
    - `/home/user/ryx-ai/core/model_orchestrator.py`
    - `/home/user/ryx-ai/configs/models_v2.json`

### New Commands

- [ ] **Add `ryx ::recent` command**
  - Show recent activity report
  - Sources:
    - `/home/user/ryx-ai/data/history/commands.log`
    - Last 10 commands with timestamps
    - Success/failure status
    - Model used for each
  - Output: Clean terminal summary
  - Files to modify:
    - `/home/user/ryx-ai/configs/commands.json`
    - `/home/user/ryx-ai/modes/cli_mode.py`

- [ ] **Add `ryx ::health` command**
  - Check system health
  - PC status: Disk, RAM, CPU, GPU
  - Ryx status: Models loaded, cache size, database health
  - Ollama status: Service running, models available
  - Run on: 1.5B model (fast check) or medium model (deep check)
  - Files to modify:
    - `/home/user/ryx-ai/configs/commands.json`
    - `/home/user/ryx-ai/core/health_monitor.py`

### Safety & UX

- [ ] **Implement safety checks**
  - Detect dangerous commands: `ryx please delete all files inside of /ryx-ai/`
  - Response: "No, I can't do that. This will wipe me out."
  - Use existing permission system (DESTROY level)
  - Files to modify:
    - `/home/user/ryx-ai/core/permissions.py`
    - `/home/user/ryx-ai/core/command_executor.py`

- [ ] **Ask for clarification on ambiguous prompts**
  - If confidence < 70%, ask user to clarify
  - Example: `ryx open config` → "Which config? hyprland, nvim, or bash?"
  - Files to modify:
    - `/home/user/ryx-ai/core/command_executor.py`

### Code Cleanup

- [ ] **Remove hardcoded commands that should be LLM-handled**
  - Review `/home/user/ryx-ai/configs/commands.json`
  - Remove any command like "open hyprland config" that's a full task
  - Keep only meta-commands (::session, ::help, ::status, etc.)
  - Let 1.5B LLM handle natural language queries
  - Files to modify:
    - `/home/user/ryx-ai/configs/commands.json`

---

## 🟡 MEDIUM PRIORITY - Smart Model Switching (Future Sprint)

### On-Demand Model Loading

- [ ] **Implement dynamic model switching**
  - User specifies: `ryx edit the hyprland config to add a new keybind that will run a script that shuts off my pc use a higher model for this task`
  - Process:
    1. 1.5B evaluates task complexity
    2. Determines medium model needed
    3. Checks if medium model running
    4. Loads medium model if not running
    5. Executes task on medium model
    6. Returns result
  - Files to modify:
    - `/home/user/ryx-ai/core/model_orchestrator.py` (already has this mostly)
    - `/home/user/ryx-ai/core/ai_engine_v2.py`

- [ ] **Add explicit model shutdown command**
  - Command: `ryx please shut down the higher models`
  - Actions:
    1. Unload medium and powerful models from Ollama
    2. Free VRAM
    3. Clean up Docker images if needed (docker/cleanup.sh)
  - Files to modify:
    - `/home/user/ryx-ai/configs/commands.json`
    - `/home/user/ryx-ai/core/model_orchestrator.py`

- [ ] **Add explicit clean command**
  - Command: `ryx ::clean` (already exists in commands.json)
  - Should:
    - Run docker/cleanup.sh
    - Vacuum databases
    - Clear old cache entries
    - Unload unused models
  - Files to modify:
    - `/home/user/ryx-ai/docker/cleanup.sh`
    - `/home/user/ryx-ai/modes/cli_mode.py`

---

## 🟢 LOW PRIORITY - Advanced Features (Future Sprints)

### Browser Integration

- [ ] **Implement documentation search & open**
  - Input: `ryx find me documentation on arch linux rocm and open to browser`
  - Process:
    1. Search web for sources
    2. List top results
    3. Select best match
    4. Open in Zen browser
  - Requires: Medium/Powerful model
  - Files to modify:
    - `/home/user/ryx-ai/tools/browser.py` (already exists)
    - New: `/home/user/ryx-ai/core/browser_integration.py`

### Multi-Terminal Support

- [ ] **Open files in new terminal**
  - Input: `ryx open hyprland config in new terminal`
  - Expected: Spawn new terminal window, run nvim in it
  - Requires: Terminal detection (Alacritty, Kitty, etc.)
  - Files to modify:
    - `/home/user/ryx-ai/core/command_executor.py`

### Advanced Task Execution

- [ ] **Multi-step complex tasks**
  - Use task_manager.py for resumable multi-step tasks
  - Example: "Refactor this codebase to use dependency injection"
  - Use medium/powerful models
  - Files to modify:
    - `/home/user/ryx-ai/core/task_manager.py`
    - `/home/user/ryx-ai/core/ai_engine_v2.py`

---

## 📦 Infrastructure Improvements

### Testing

- [ ] **Create comprehensive test suite for 1.5B model**
  - Test command execution accuracy
  - Test typo correction
  - Test file finding
  - Test app launching
  - Test cache hit rates
  - Benchmark response times (target < 500ms)
  - Files:
    - New: `/home/user/ryx-ai/tests/test_1.5b_core.py`

### Documentation

- [ ] **User guide for core features**
  - How to use natural language commands
  - How memory/caching works
  - How to confirm memorization
  - How to use different models
  - Files:
    - New: `/home/user/ryx-ai/USAGE_GUIDE.md`

### Configuration

- [ ] **Add user preferences config**
  - Preferred editor (nvim, vim, code, etc.)
  - Preferred terminal (alacritty, kitty, etc.)
  - Preferred browser (zen, firefox, chrome, etc.)
  - Shell (bash, zsh, fish)
  - Files to modify:
    - `/home/user/ryx-ai/configs/settings.json`

---

## 🚫 FUTURE / NOT NOW (Document Only)

These are important but not for immediate implementation:

### Web Scraping
- Complex web scraping tasks
- Multi-page extraction
- Dynamic content handling
- Already has basic implementation in `tools/scraper.py`

### Council/Multi-Model Voting
- Already implemented in `tools/council.py`
- Not critical for 1.5B core functionality
- Keep as-is for now

### Full Model Orchestrator Features
- Advanced complexity analysis
- Performance-based model selection
- Automatic fallback chains
- Already implemented, just needs optimization

---

## 📊 Success Metrics

### Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Startup time (minimal) | < 5s | ~2s ✅ |
| Basic command response | < 0.5s | Unknown |
| File open response | < 1s | Unknown |
| App launch response | < 0.5s | Unknown |
| Cache hit rate | > 60% | Unknown |
| Idle RAM usage | < 50MB | ~50-100MB ✅ |
| Idle VRAM usage | 0 MB | 1.5GB (1.5B loaded) |

### Quality Targets

- [ ] 95% accuracy on file finding (correct path)
- [ ] 90% accuracy on typo correction
- [ ] 100% correct editor preference application
- [ ] 0% cache-based wrong answers
- [ ] 100% dangerous command detection

---

## 🔄 Development Workflow

### Phase 1: Critical Fixes (This Session)
1. Fix psutil dependency
2. Fix database schema
3. Test basic functionality
4. Verify system is usable

### Phase 2: Core Execution (Next Session)
1. Implement command executor
2. Implement file finding
3. Implement app launching
4. Add typo tolerance

### Phase 3: Caching & Memory (Following Session)
1. Fix cache validation
2. Add memory confirmation system
3. Implement smart caching

### Phase 4: Optimization (Following Session)
1. Benchmark and optimize startup
2. Minimize resource usage
3. Add ::recent and ::health commands
4. Remove hardcoded commands

### Phase 5: Advanced Features (Future Sprints)
1. Model switching
2. Browser integration
3. Multi-terminal support
4. Complex tasks

---

## 📝 Notes

- Keep 1.5B model as the absolute core
- Only load larger models when explicitly needed or automatically escalated
- Cache aggressively but validate everything
- Always confirm before memorizing
- Execute commands directly, never just print them
- Speed and resource efficiency are paramount
- User experience > feature complexity

---

**Last Updated**: 2025-11-27
**Status**: Phase 1 (Critical Fixes) - In Progress
