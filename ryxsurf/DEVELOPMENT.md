# RyxSurf Development Prompt

You are helping build RyxSurf, a minimalist AI-integrated browser.

## Context

RyxSurf is located at `/home/tobi/ryx-ai/ryxsurf/` and uses:
- **WebKitGTK 6.0** for rendering (GTK4-based)
- **Python** with PyGObject for the UI
- **vLLM** at localhost:8001 for AI features
- **Dracula theme** for styling

## Architecture

```
ryxsurf/
├── main.py              # Entry point
├── keybinds.py          # All keybind definitions
├── config.default.json  # Default configuration
└── src/
    ├── core/
    │   ├── browser.py   # Main browser class with WebKitGTK
    │   ├── config.py    # Configuration loader
    │   └── memory.py    # Tab memory management
    ├── ai/
    │   ├── agent.py     # AI browser control agent
    │   ├── vision.py    # Page understanding/analysis
    │   └── actions.py   # JavaScript action generators
    ├── ui/
    │   ├── bar.py       # URL/command input bar
    │   ├── tabs.py      # Tab sidebar component
    │   └── hints.py     # Keyboard hint mode (vimium-style)
    ├── sessions/
    │   └── manager.py   # Session save/load/switch
    └── extensions/
        └── loader.py    # Firefox extension support
```

## Key Features to Implement

1. **Fullscreen by default** - No UI chrome unless toggled
2. **Keyboard-first** - All actions via keybinds (Super + key)
3. **Tab sessions** - Named groups (school/work/chill)
4. **AI integration** - Summarize, dismiss popups, click by description
5. **Memory efficient** - Auto-unload inactive tabs
6. **Firefox extensions** - Basic WebExtensions support

## User's Environment

- Arch Linux with Hyprland
- vim/neovim user (hjkl navigation)
- Prefers keyboard over mouse
- Dark theme (Dracula colors)

## When Coding

1. Follow existing patterns in the codebase
2. Use type hints
3. Keep UI minimal and keyboard-focused
4. Test with WebKitGTK 6.0 / GTK4
5. Use Dracula color palette:
   - Background: #282a36
   - Current: #44475a
   - Foreground: #f8f8f2
   - Comment: #6272a4
   - Purple: #bd93f9
   - Green: #50fa7b
   - Pink: #ff79c6

## Current TODOs

- [ ] Complete URL bar overlay (bar.py)
- [ ] Implement hint mode fully (hints.py)
- [ ] Add session switcher UI
- [ ] Connect AI agent to browser
- [ ] Add tab unloading trigger
- [ ] Test extension loading
