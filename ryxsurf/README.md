# RyxSurf - AI-Integrated Minimalist Browser

A keyboard-driven browser for Hyprland users with full AI integration.

## Features

- **Fullscreen by default** - No distractions, toggle UI with keybinds
- **Tab sessions** - Save and switch between session groups (school/work/chill)
- **AI integration** - Summarize pages, dismiss popups, click with natural language
- **Firefox extensions** - WebExtensions API support (planned)
- **Memory efficient** - Auto-unload inactive tabs after 5 minutes
- **Synced with Ryx** - Shares context with ryx CLI and RyxHub
- **History tracking** - SQLite-based history with URL bar suggestions
- **Download manager** - Progress tracking, auto-save to ~/Downloads
- **Bookmarks** - Quick bookmark with Ctrl+D, bookmark bar toggle
- **Find in page** - Ctrl+F with match count and navigation
- **Zoom** - Per-tab zoom levels with Ctrl++/-/0
- **Page security** - HTTPS lock icon in URL bar

## Keybinds

### Navigation
| Key | Action |
|-----|--------|
| Ctrl + L/G | Focus URL bar |
| Ctrl + R | Reload page |
| Ctrl + Shift + R | Hard reload |
| Ctrl + F | Find in page |
| Super + j/k | Scroll down/up |
| Super + h/l | Back/forward |
| Super + f | Hint mode (click links with keyboard) |

### Tabs
| Key | Action |
|-----|--------|
| Ctrl + T | New tab |
| Ctrl + W | Close tab |
| Ctrl + 1-9 | Go to tab N |
| Ctrl + Tab | Next tab |
| Ctrl + Shift + Tab | Previous tab |
| Middle-click | Close tab (in sidebar) |

### UI
| Key | Action |
|-----|--------|
| Ctrl + B | Toggle tab sidebar |
| Ctrl + Shift + B | Toggle bookmarks bar |
| Ctrl + D | Bookmark current page |
| Ctrl + , | Open settings |
| Escape | Close overlays / unfocus URL bar |

### Zoom
| Key | Action |
|-----|--------|
| Ctrl + + | Zoom in |
| Ctrl + - | Zoom out |
| Ctrl + 0 | Reset zoom (100%) |

### AI
| Key | Action |
|-----|--------|
| Ctrl + Shift + A | Toggle AI sidebar |
| !command | AI command in URL bar |

## New Features

### Tab Management
- Tab count displayed in URL bar
- Full tab title shown on hover
- Middle-click tabs in sidebar to close
- Visual indicator for unloaded tabs `[z]`

### Session Persistence
- Auto-saves session on browser close
- Auto-restores session on startup
- Sessions stored in `~/.config/ryxsurf/sessions/`

### Smart Tab Unloading
- Automatically unloads tabs inactive for 5+ minutes
- Saves memory by loading tabs on-demand
- Scroll position preserved when reloading
- Configure timeout in settings

### History
- Tracks all visited URLs in SQLite database
- Location: `~/.config/ryxsurf/history.db`
- Autocomplete suggestions in URL bar
- Sorted by visit frequency and recency

### Bookmarks
- Quick bookmark with Ctrl+D (toggle)
- Bookmark bar with Ctrl+Shift+B
- Star icon in URL bar shows bookmark status
- Stored in `~/.config/ryxsurf/bookmarks.json`
- Right-click bookmarks to remove

### Find in Page
- Ctrl+F opens find bar
- Live search with match highlighting
- Match count displayed (e.g., "3/15")
- Enter/Shift+Enter to navigate matches
- Escape to close

### Zoom
- Per-tab zoom levels (preserved across sessions)
- Ctrl++ to zoom in (max 300%)
- Ctrl+- to zoom out (min 30%)
- Ctrl+0 to reset to 100%

### Context Menu
- Right-click for context-sensitive menu
- Open link in new tab
- Copy link address
- Save image as
- Inspect element

### Page Security
- Lock icon (🔒) for HTTPS pages
- Warning icon (⚠️) for HTTP pages
- Page title shown in window title

### Downloads
- Automatic download handling
- Progress notification at bottom-right
- Files saved to `~/Downloads`
- Supports all common file types

## Requirements

- Arch Linux (or any Linux with GTK4)
- Python 3.11+
- WebKitGTK 6.0
- vLLM running (for AI features)

### Install Dependencies

```bash
# Arch Linux
sudo pacman -S webkit2gtk-5.0 python-gobject gtk4

# Or with yay for webkit2gtk 6.0
yay -S webkitgtk-6.0
```

## Usage

```bash
# Start browser
cd /home/tobi/ryx-ai
python -m ryxsurf.main

# Or with ryx (once integrated)
ryx surf
ryxsurf
```

## Architecture

```
ryxsurf/
├── main.py              # Entry point
├── keybinds.py          # All keybind definitions
├── src/
│   ├── core/            # Browser engine (WebKitGTK)
│   │   ├── browser.py   # Main browser class
│   │   ├── history.py   # SQLite history manager
│   │   ├── downloads.py # Download manager
│   │   ├── memory.py    # Tab memory manager
│   │   └── config.py    # Configuration
│   ├── ai/              # AI integration
│   │   └── agent.py     # Browser control agent
│   ├── ui/              # UI components
│   ├── sessions/        # Tab groups/sessions
│   └── extensions/      # Firefox extension support
```

## Configuration

Settings stored in `~/.config/ryxsurf/settings.json`:

```json
{
  "homepage": "https://www.google.com",
  "url_bar_auto_hide": true,
  "smooth_scrolling": true,
  "gpu_acceleration": true,
  "tab_unload_timeout_seconds": 300,
  "max_loaded_tabs": 10,
  "restore_session_on_startup": true
}
```

## AI Commands

The AI can understand natural language:

- "summarize this page"
- "click the login button"
- "dismiss this popup"
- "fill in my email"
- "search for python tutorials"
- "go to github"

## Sessions

Save your tabs as named sessions:

```
Super + s          -> Save current session
Super + Shift+s    -> Switch session menu
                      - school (lecture tabs)
                      - work (project tabs)
                      - chill (youtube, reddit)
```

Sessions are stored in `~/.config/ryxsurf/sessions/`

## Roadmap

- [x] Basic browser with WebKitGTK
- [x] Keybind system
- [x] Tab management
- [x] Session save/restore
- [x] Tab count in URL bar
- [x] Tab title on hover
- [x] Middle-click to close tabs
- [x] Smart tab unloading (5 min timeout)
- [x] History tracking with SQLite
- [x] URL bar suggestions
- [x] Download manager with progress
- [x] Bookmarks (Ctrl+D, bookmark bar)
- [x] Find in page (Ctrl+F)
- [x] Per-tab zoom (Ctrl++/-/0)
- [x] Context menu (right-click)
- [x] Page security indicator (HTTPS lock)
- [ ] AI summarization
- [ ] AI popup dismissal
- [ ] Hint mode (vimium-style)
- [ ] Firefox extension support
- [ ] Sync with RyxHub
- [ ] Drag to reorder tabs
