# Quick Start - RyxSurf C++ Development

## Current State

✅ **6 of 10 milestones complete**  
✅ **Core browser functionality working**  
✅ **~17,000 lines of code**

## Build & Run

```bash
# Install dependencies (Ubuntu/Debian)
sudo apt-get install -y \
    build-essential meson ninja-build \
    libgtk-4-dev libwebkitgtk-6.0-dev \
    libsqlite3-dev libsecret-1-dev \
    libsodium-dev pkg-config

# Build
cd ryxsurf-cpp
meson setup build
meson compile -C build

# Run
./build/ryxsurf

# Test
meson test -C build
```

## Key Features Working

- ✅ Keyboard shortcuts (Ctrl+T, Ctrl+W, Ctrl+Arrow keys)
- ✅ Lazy WebView loading
- ✅ Tab unload/restore with snapshots
- ✅ Session persistence (encrypted SQLite)
- ✅ Password manager (libsecret + fallback)
- ✅ CSS theming (dark/light)

## Next Steps

See `CONTINUATION_PLAN.md` for detailed roadmap.

**Priority**: Performance tuning (Milestone 10) to meet memory/startup targets.

## Git Branches

- `rewrite/poc` - Current development branch
- `rewrite/cpp` - Base branch with migration map

## Apply All Patches

```bash
cd ryxsurf-cpp
git am patches/*.patch
```
