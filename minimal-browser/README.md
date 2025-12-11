# Minimal Browser

A minimal, keyboard-first, resource-efficient desktop browser based on GTK4 + WebKit6.

## Architecture

```
┌─────────────────────────────────────────┐
│         BrowserWindow (GTK4)            │
│  ┌───────────────────────────────────┐  │
│  │   Session Indicator (Workspaces)  │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │        Tab Bar (Keyboard)         │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │         Address Bar (Ctrl+L)      │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │    Notebook (WebView Container)   │  │
│  │         ┌──────────────┐           │  │
│  │         │ WebKitWebView│           │  │
│  │         │  (Lazy Load) │           │  │
│  │         └──────────────┘           │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│         SessionManager                  │
│  ┌───────────────────────────────────┐ │
│  │  Workspace[]                      │ │
│  │    └─ Session[]                   │ │
│  │         └─ Tab[]                  │ │
│  │            └─ WebKitWebView*      │ │
│  │               (null if unloaded)   │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### Data Model

- **Workspace**: Named persistent container (e.g., "School", "Work", "Gaming")
- **Session**: Workspace subcontext (like Hyprland workspaces), contains tabs
- **Tab**: Single browser tab with metadata and optional WebKitWebView

### Lazy Loading

Tabs are created with metadata only. WebKitWebView is instantiated only when:
1. Tab becomes active (focused)
2. User explicitly loads the tab

Unloaded tabs maintain:
- URL
- Title
- Last active timestamp
- Snapshot path (future: for restore)

## Build Instructions

### Dependencies

- GTK4 (>= 4.0)
- WebKitGTK6 (>= 2.40)
- SQLite3
- libsecret-1
- libsodium
- Meson (>= 0.60)
- Ninja
- C++17 compiler (GCC 8+ or Clang 8+)

### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    meson \
    ninja-build \
    libgtk-4-dev \
    libwebkitgtk-6.0-dev \
    libsqlite3-dev \
    libsecret-1-dev \
    libsodium-dev \
    pkg-config
```

### Arch Linux

```bash
sudo pacman -S \
    base-devel \
    meson \
    ninja \
    gtk4 \
    webkitgtk \
    sqlite \
    libsecret \
    libsodium \
    pkgconf
```

### Build

```bash
cd minimal-browser
meson setup build
meson compile -C build
```

### Run

```bash
./build/minimal-browser
```

### Debug Build with Sanitizers

```bash
meson setup build -Dbuildtype=debug -Dsanitize=address
meson compile -C build
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+T` | Open new tab in current session |
| `Ctrl+W` | Close current tab |
| `Ctrl+↑` | Move focus to previous tab (vertical order) |
| `Ctrl+↓` | Move focus to next tab (vertical order) |
| `Ctrl+←` | Switch to previous session |
| `Ctrl+→` | Switch to next session |
| `Ctrl+Tab` | Next tab (fallback) |
| `Ctrl+Shift+Tab` | Previous tab (fallback) |
| `Ctrl+L` | Focus address bar / quick open |
| `Ctrl+Shift+S` | Save current session snapshot (TODO) |

All shortcuts are handled globally at the application level for immediate, non-blocking response.

## Features (PoC Status)

### ✅ Implemented (PoC)

- [x] GTK4 window with minimal UI
- [x] WebKit6 integration
- [x] Keyboard shortcuts (Ctrl+T, Ctrl+W, Ctrl+Arrow keys)
- [x] Lazy WebView instantiation
- [x] Session/workspace model (in-memory)
- [x] Tab management
- [x] Overview placeholder session

### 🚧 Planned

- [ ] Session persistence (SQLite)
- [ ] Tab unload/restore with snapshots
- [ ] Password manager (libsecret + encrypted SQLite)
- [ ] Autofill integration
- [ ] History and bookmarks
- [ ] QuickOpen (fuzzy search)
- [ ] Performance optimizations
- [ ] Security hardening
- [ ] IPC/D-Bus interface
- [ ] Unit and integration tests

## Performance Targets

- **Cold start**: < 500ms (on modern NVMe desktop)
- **Idle RSS**: < 200MB (with 3 unloaded tabs + 1 loaded tab)
- **Tab switch**: < 50ms (when tab already loaded)

See `perf/run_perf.sh` for performance testing scripts.

## Security

- WebKit process sandboxing enabled
- No telemetry by default
- No remote calls unless user-initiated
- Content Security Policies enabled
- Plugins disabled by default

See `security.md` for detailed security documentation.

## License

MIT License - see LICENSE file.

## Development Roadmap

See `plan.md` for detailed development milestones and task breakdown.
