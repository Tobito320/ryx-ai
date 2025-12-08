# RyxSurf Development Session Handoff
**Date:** 2025-12-07
**Session:** 1

## 🎯 Project Goal
Create RyxSurf - a minimalist, efficient browser with integrated AI (ryx) that:
- Has Firefox-like features but faster/cleaner
- Full AI integration (sidebar, page summarization, element hiding, automation)
- Session/tab groups (school/work/chill)
- Hyprland-optimized (keyboard-first, keybinds over mouse)
- Fullscreen by default, toggle UI with keybinds

## 🔑 CRITICAL RULES
1. **NEVER write code directly** - Only prompt ryx to write/fix code
2. **If ryx makes mistakes** - Improve ryx prompts/self-healing, don't fix code yourself
3. **Goal:** Make ryx smarter than Claude Code - self-healing, precise, reliable

## ✅ Completed This Session

### Infrastructure
- Created `/home/tobi/ryx-ai/ryxsurf/` browser structure
- GTK4 + WebKit 6.0 browser framework
- `ryx start ryxsurf` / `ryx surf` commands work
- Beautiful startup visual feedback (4-step progress)
- Model switching: Browser uses fast 7B model, coding uses 14B

### Ryx Improvements Made
- Fixed pkill killing itself (now excludes own PID)
- Fixed WebKit version check (was WebKit2, now WebKit 6.0)
- Fixed import path issues for dependency checks

### Files Created/Modified
- `/home/tobi/ryx-ai/ryxsurf/` - Full browser package
- `/home/tobi/ryx-ai/ryxsurf/src/core/browser.py` - Main GTK4 browser
- `/home/tobi/ryx-ai/ryxsurf/src/core/keybindings.py` - Keybind manager
- `/home/tobi/ryx-ai/ryxsurf/src/ui/sidebar.py` - AI sidebar (needs work)
- `/home/tobi/ryx-ai/ryxsurf/src/ui/url_bar.py` - URL bar overlay
- `/home/tobi/ryx-ai/ryx_main.py` - Added ryxsurf startup commands
- `/home/tobi/ryx-ai/.github/copilot-instructions.md` - Project guidelines

## ❌ Current Issues (MUST FIX)

### 1. Search Not Working
**Symptom:** Searching from Google goes white, nothing happens
**Cause:** URL loading or navigation not properly connected
**Fix:** Have ryx debug the WebView navigation signals

### 2. Keybinds Not Working  
**Symptom:** Ctrl+L, Ctrl+B, Ctrl+T do nothing
**Cause:** Key event controller not properly connected in GTK4
**Fix:** Have ryx fix keybind registration in browser.py

### 3. No Visible UI
**Symptom:** Only see webpage, no sidebar/tabs/url bar
**Cause:** UI elements exist but aren't visible by default
**Fix:** Have ryx make URL bar visible by default at top

### 4. Gdk Portal Warnings
**Symptom:** Portal settings errors on startup
**Cause:** Missing xdg-desktop-portal-hyprland
**Fix:** `sudo pacman -S xdg-desktop-portal-hyprland` (harmless warning)

## 📋 TODO List (Priority Order)

### Immediate Fixes
1. Fix URL bar visibility - should show by default at top
2. Fix keybinds (Ctrl+L, Ctrl+B, Ctrl+T, Ctrl+W)
3. Fix Google search / navigation
4. Add tab bar (can be toggled)

### Core Features Needed
1. Tab management (Ctrl+T new, Ctrl+W close, Ctrl+Tab switch)
2. Session groups (school/work/chill) with saved tabs
3. AI sidebar integration
4. Tab unloading for memory optimization
5. Settings page

### AI Integration
1. Connect sidebar to vLLM (7B fast model)
2. Page summarization
3. "Hide this element" functionality
4. Search and open websites by voice/text command
5. Full browser automation

### UI Polish
1. Dark theme (Hyprland aesthetic)
2. Animations for sidebar toggle
3. Tab previews
4. Favicon loading

## 🛠 How to Continue

### Start Browser
```bash
ryx surf
# or
ryx start ryxsurf
```

### Start Coding Model (for ryx to code)
```bash
vllm serve /home/tobi/vllm-models/powerful/coding/qwen2.5-coder-14b-awq \
  --gpu-memory-utilization 0.85 \
  --max-model-len 32768 \
  --port 8000
```

### Available Models
- **Coding:** `/home/tobi/vllm-models/powerful/coding/qwen2.5-coder-14b-awq`
- **Fast/Browser:** `qwen2.5-7b-awq` (for AI sidebar)

### Example Prompts for Ryx
```
# Fix keybindings
"Fix the keybindings in /home/tobi/ryx-ai/ryxsurf/src/core/browser.py - 
Ctrl+L should show URL bar, Ctrl+B toggle sidebar, Ctrl+T new tab.
Use GTK4 EventControllerKey properly."

# Fix navigation
"The WebView in ryxsurf is not loading URLs when submitted from URL bar.
Debug and fix the navigation in browser.py."

# Add visible URL bar
"Make the URL bar in ryxsurf visible by default at the top of the window.
It should be a thin bar with the current URL, expandable on Ctrl+L."
```

## 🧠 Ryx Self-Improvement Notes

### What Works Well
- Ryx can create files and edit code
- Ryx understands project context when given file paths
- Ryx follows specific instructions

### What Needs Improvement
- Ryx sometimes creates duplicate code blocks
- Ryx needs explicit file paths to be reliable
- Ryx should verify its own changes work
- Add self-healing: if code fails, ryx should auto-debug

### Suggested Ryx Improvements
1. Add verification step after each code change
2. Add rollback capability if changes break things
3. Add diff-based editing for large files
4. Add context loading from multiple files

## 📁 Key File Locations

```
/home/tobi/ryx-ai/
├── ryxsurf/
│   ├── main.py              # Entry point
│   ├── src/
│   │   ├── core/
│   │   │   ├── browser.py   # Main browser class (GTK4)
│   │   │   ├── keybindings.py
│   │   │   └── tab_manager.py
│   │   ├── ui/
│   │   │   ├── sidebar.py   # AI sidebar
│   │   │   └── url_bar.py   # URL overlay
│   │   └── ai/
│   │       └── assistant.py # vLLM connection
│   └── config/
│       └── settings.json
├── ryx_main.py              # CLI entry (has start ryxsurf)
├── core/                    # Ryx AI core
└── configs/                 # Ryx configs
```

## 🚀 Prompt for Next Session

Copy this to start the next session:

---

**Continue RyxSurf browser development. Read /home/tobi/ryx-ai/docs/SESSION_HANDOFF.md first.**

Key rules:
1. You control ryx AI to write code - NEVER write code yourself
2. If ryx makes mistakes, improve ryx (prompts, self-healing) - don't fix code directly
3. Goal: Make ryx smarter than Claude Code

Current status: Browser starts but has issues:
- Keybinds don't work (Ctrl+L, Ctrl+B, etc.)
- Search goes white (navigation broken)
- No visible UI elements by default

Start the coding model first:
```bash
vllm serve /home/tobi/vllm-models/powerful/coding/qwen2.5-coder-14b-awq --gpu-memory-utilization 0.85 --max-model-len 32768
```

Then prompt ryx to fix the keybind and navigation issues.

---
