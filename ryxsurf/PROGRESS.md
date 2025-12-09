# RyxSurf Development Progress

## Session: 2024-12-09 (02:40 CET)

### Current Status: **Analysis Complete - Ready for Fixes**

## Code Analysis Summary

### Files Analyzed:
- `browser.py` - 3920 lines, main browser class
- `keybinds.py` - 121 lines, keybind definitions (not fully integrated)

### Code Structure Findings:
1. **Duplicate methods** - `_focus_url_bar` defined twice (lines 1680 and 2307)
2. **Keybinds in 3 places** - `_setup_app_actions`, `_setup_keybinds`, `_on_webview_key_press`
3. **WebView key capture** - Already has `EventControllerKey` with CAPTURE phase (line 1591)
4. **Tab titles** - Truncated to 15 chars (lines 1851, 1856)
5. **Sidebar CSS** - Set to 120px but may be overridden by widget sizing

### Log Analysis:
- Old log showed infinite load event loop (STARTED/FINISHED repeating)
- Log code was removed but old log file remained
- Cleared stale log file

### Navigation Flow (Verified):
1. `_on_url_entry_activate` (line 1038) - handles Enter key
2. Quick domain check (yt→youtube, etc.) - lines 1051-1067  
3. `_navigate_current` (line 2140) - loads URL
4. URL bar update + history add

### Keybind Flow (Verified):
1. `_setup_app_actions` sets GIO actions with accelerators
2. `_setup_keybinds` adds ShortcutController + EventControllerKey
3. `_on_webview_key_press` (line 1154) - captures keys from WebView
4. Returns `Gdk.EVENT_STOP` to prevent propagation

## Issues to Fix (Prioritized)

### P0 - Critical
- [ ] **Keybinds not working** after page loads
  - EventControllerKey IS attached on WebView creation (line 1591)
  - Handler logic IS correct (lines 1154-1206)
  - **Hypothesis**: WebKit steals focus before GTK can capture
  - **Fix**: May need to use a different approach (e.g., window-level grab)

- [ ] **URL navigation not working**
  - Code path looks correct
  - Need live testing with fresh log to see actual error

### P1 - High
- [ ] **Sidebar too wide** (appears ~40% but CSS says 120px)
  - CSS: `min-width: 120px; max-width: 120px;`
  - May be GTK widget sizing issue
  
- [ ] **Workspaces in wrong location**
  - Currently in sidebar, should be in URL bar

### P2 - Medium  
- [ ] Remove duplicate `_focus_url_bar` method
- [ ] Integrate keybinds.py properly (currently unused)
- [ ] Tab title display (15 chars may be too short)

## Next Steps (Priority Order)
1. Test browser with fresh log to see actual errors
2. Fix keybinds by testing different capture methods
3. Fix sidebar width with explicit widget sizing
4. Move workspaces to URL bar
5. Test navigation with logging

## Design Requirements (User Specified)
- Dark mode (#0a0a0c base)
- Minimalist - no unnecessary UI
- 10-15% sidebar width
- Keyboard-first (Ctrl+L, Ctrl+T, Ctrl+W, etc.)
- Workspaces in URL bar (chill/school/work/research/private)
- No AI unless manually activated
- Fast startup, efficient memory

### High Priority (P1)
- [ ] **Sidebar too wide** - Should be 10-15% (currently ~40% visually)
  - CSS says 120px but something overrides it
  
- [ ] **Workspaces in wrong location**
  - Currently in left sidebar, should be in URL bar (after reload button)
  - Layout: [Back][Forward][Reload] [Workspaces] [URL Entry] [Bookmark][Menu]

- [ ] **Layout breaks when URL bar hidden**
  - Sidebar expands to fill space incorrectly

### Medium Priority (P2)
- [ ] Dark mode enforcement on all pages
- [ ] Performance optimization (4s load time → instant)
- [ ] Session restore reliability
- [ ] Bookmark sync

## Completed Today
- [x] Created PROGRESS.md for tracking
- [x] Analyzed browser.py structure (~3900 lines)
- [x] Identified keybind issues
- [x] Identified layout issues

## Feature Roadmap

### Phase 1: Core Browser (Current)
- Basic browsing works
- Tab management
- Session save/restore
- Dark theme

### Phase 2: Polish & UX
- Reliable keybinds (like Firefox)
- Minimal sidebar (10-15%)
- Quick domain shortcuts (yt→youtube.com)
- Smooth animations

### Phase 3: Advanced Features
- Workspaces (chill/school/work)
- Reader mode
- Auto-clean pages
- Per-site settings

### Phase 4: AI Integration (Manual only)
- AI sidebar (Super+A to activate)
- Page summarization
- Popup dismissal
- Form filling

## Architecture Notes

### File Structure
```
ryxsurf/
├── main.py              # Entry point
├── keybinds.py          # Keybind definitions (not used properly)
├── src/
│   ├── core/
│   │   ├── browser.py   # Main browser (~3900 lines, needs refactor)
│   │   ├── history.py   # History manager
│   │   ├── downloads.py # Download manager
│   │   └── bookmarks.py # Bookmark manager
│   ├── ui/
│   │   ├── hints.py     # Keyboard hints (f for links)
│   │   ├── find_bar.py  # Find in page
│   │   └── bookmarks_bar.py
│   ├── ai/              # AI integration
│   └── extensions/      # Extension support
```

### Key Technical Details
- **GTK4 + WebKit6** - Modern stack
- **Keybind problem**: GTK4 ShortcutController doesn't capture keys when WebView is focused
- **Solution needed**: Use `EventControllerKey` with CAPTURE phase on window, but WebView still steals focus

## Design Goals
- **Minimalist** - Only essential UI elements
- **Dark by default** - Pure dark theme (#0a0a0c)
- **Keyboard-first** - Everything accessible via keybinds
- **Fast** - Instant startup, efficient memory
- **No AI by default** - AI features are manual activation only

## Keybind Reference (Target)
```
Ctrl+L          Focus URL bar
Ctrl+T          New tab
Ctrl+W          Close tab
Ctrl+Tab        Next tab
Ctrl+Shift+Tab  Previous tab
Ctrl+R / F5     Reload
Ctrl+Shift+R    Hard reload
Ctrl+B          Toggle sidebar
Ctrl+D          Bookmark page
Ctrl+F          Find in page
Ctrl+1-9        Jump to tab N
F11             Fullscreen
Escape          Cancel/close overlays
```

## Notes for Next Session
1. Fix keybinds first - this blocks all testing
2. Then fix URL navigation
3. Then fix sidebar width
4. Move workspaces to URL bar
5. Test everything works before adding features
