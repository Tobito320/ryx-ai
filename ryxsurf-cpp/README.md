# RyxSurf C++

Minimal, keyboard-first, resource-efficient desktop browser based on GTK4 + WebKit6.

## Status: PoC Complete ✅

Proof-of-concept implementation demonstrating:
- GTK4 window with minimal UI
- WebKit6 integration with lazy WebView loading
- Keyboard shortcuts (Ctrl+T, Ctrl+W, Ctrl+Arrow keys)
- Tab management with lazy instantiation

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
cd ryxsurf-cpp
meson setup build
meson compile -C build
```

### Run

```bash
./build/ryxsurf
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+T` | Open new tab |
| `Ctrl+W` | Close current tab |
| `Ctrl+↑` | Previous tab |
| `Ctrl+↓` | Next tab |
| `Ctrl+1-9` | Jump to tab N |
| `Ctrl+←` | Previous session |
| `Ctrl+→` | Next session |
| `Ctrl+B` | Toggle sidebar visibility |
| `Ctrl+Tab` | Next tab (fallback) |
| `Ctrl+Shift+Tab` | Previous tab (fallback) |
| `Ctrl+L` | Focus address bar |
| `Ctrl+Shift+S` | Save session snapshot (placeholder) |

All shortcuts are handled globally at the application level for immediate, non-blocking response.

## Architecture

```
BrowserWindow (GTK4)
  ├─ Tab[] (lazy WebView loading)
  ├─ KeyboardHandler (global shortcuts)
  └─ UI Components (tab bar, address bar, notebook)
```

### Lazy Loading

Tabs are created with metadata only. WebKitWebView is instantiated only when:
1. Tab becomes active (focused)
2. User explicitly loads the tab

Unloaded tabs maintain:
- URL
- Title
- Last active timestamp

## Performance Targets

- **Cold Start**: < 500ms (on modern NVMe desktop)
- **Idle RSS**: < 200MB (with 3 unloaded tabs + 1 loaded tab)

See `perf/run_perf.sh` for performance testing.

## Next Steps

See `plan.md` for detailed development roadmap.

## License

MIT License
