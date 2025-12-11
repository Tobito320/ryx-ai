# Development Progress

## Completed Milestones

### ✅ Milestone 1: PoC
- Basic GTK4 window
- WebKit6 integration
- Keyboard shortcuts (Ctrl+T, Ctrl+W, Ctrl+Arrow keys)
- Lazy WebView instantiation
- Tab management
- Meson build system
- Unit tests skeleton
- Performance test script

### ✅ Milestone 2: Core Data Models
- Workspace class (named persistent container)
- Session class (workspace subcontext)
- Enhanced Tab with unload/restore
- SessionManager with workspace/session/tab hierarchy
- Overview placeholder session
- Auto-close empty sessions
- Timestamp tracking

### ✅ Milestone 5: Tab Unload/Restore & Snapshot
- TabUnloadManager (automatic unloading, 5 min timeout)
- SnapshotManager (PNG + HTML snapshots)
- Configurable timeout and max loaded tabs
- Periodic check every 60 seconds
- Restore from snapshot on focus

### ✅ Milestone 6: Persistence
- Crypto class (Argon2id + ChaCha20-Poly1305)
- PersistenceManager (encrypted SQLite with WAL mode)
- Database schema (workspaces, sessions, tabs)
- Autosave (periodic + graceful exit)
- Restore on startup

### ✅ Milestone 7: Password Manager
- PasswordManager with dual backend (libsecret + SQLite fallback)
- Encrypted SQLite storage for passwords
- Password generator utility
- Autofill detection per origin
- Last used timestamp tracking

### ✅ Milestone 9: UI Polish & CSS
- ThemeManager class for theme/layout/animation management
- Minimal CSS theme (dark/light variants)
- GPU-accelerated animations (optional)
- Tab layout modes (horizontal/vertical)
- Compact mode support
- Session indicator styling

## Current Status

**Total Files**: 32 C++ source/header files + 1 CSS file
**Commits**: 11 (analysis, PoC, docs, core models, unload/restore, persistence, password manager, UI polish)
**Test Coverage**: Tab, Session, Workspace, SessionManager, UnloadManager, Crypto, PersistenceManager, PasswordManager

## Next Steps

### Milestone 3: Session/Tab Manager + Tests (Partially Complete)
- ✅ SessionManager implemented
- ✅ Tab navigation
- ⏳ Additional integration tests needed

### Milestone 4: Lazy WebView Factory
- ✅ Basic lazy loading implemented in Tab
- ⏳ Dedicated WebViewFactory for better control

### Milestone 6: Persistence ✅ Complete
- ✅ Encrypted SQLite schema
- ✅ Argon2id KDF + libsodium encryption
- ✅ Autosave & graceful exit restore

### Milestone 7: Password Manager ✅ Complete
- ✅ libsecret integration (primary)
- ✅ Encrypted SQLite fallback
- ✅ Password generator utility
- ⏳ UI for credential management (basic API ready)

## Performance Targets

- **Cold Start**: < 500ms (target)
- **Idle RSS**: < 200MB (with 3 unloaded + 1 loaded tab) (target)
- **Tab Switch**: < 50ms (when tab already loaded) (target)

*Note: Actual measurements pending full implementation*

## Build Status

```bash
cd ryxsurf-cpp
meson setup build
meson compile -C build
./build/ryxsurf
```

## Test Status

```bash
meson test -C build
```

## Git Branches

- `rewrite/cpp`: Base branch with migration map
- `rewrite/poc`: Active development branch

## Patches

All commits available as patches in `ryxsurf-cpp/patches/`
