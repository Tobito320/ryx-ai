# Architecture Documentation

## Overview

Minimal Browser is built on GTK4 and WebKit6, using modern C++17 with a focus on resource efficiency and keyboard-first navigation.

## Core Components

### 1. BrowserWindow (`browser_window.h/cpp`)

The main GTK4 window that orchestrates the UI. Responsibilities:
- Window management
- UI layout (tab bar, address bar, session indicator, notebook)
- Integration with SessionManager and KeyboardHandler
- WebView container management

**Ownership**: Owns SessionManager and KeyboardHandler instances.

### 2. SessionManager (`session_manager.h/cpp`)

Root of the session hierarchy. Manages:
- Workspaces (named persistent containers)
- Current workspace/session/tab tracking
- Tab and session operations (new, close, switch)

**Data Model**:
```
SessionManager
  └─ Workspace[] (e.g., "School", "Work", "Gaming")
      └─ Session[] (workspace subcontexts)
          └─ Tab[] (browser tabs)
              └─ WebKitWebView* (nullable, lazy-loaded)
```

### 3. Workspace (`workspace.h/cpp`)

Named persistent container for sessions. Examples: "School", "Work", "Gaming".

**Ownership**: Owns Session objects.

### 4. Session (`session.h/cpp`)

Workspace subcontext containing tabs. Similar to Hyprland workspaces.

**Features**:
- Can be empty (shows Overview placeholder)
- Overview session is persistent and cannot be deleted
- Tracks active tab index

**Ownership**: Owns Tab objects.

### 5. Tab (`tab.h/cpp`)

Single browser tab with metadata and optional WebView.

**Lazy Loading**:
- Created with metadata only (URL, title)
- WebKitWebView instantiated only when:
  - Tab becomes active (focused)
  - User explicitly loads the tab
- WebView can be destroyed (unloaded) while keeping metadata

**Ownership**: Owns WebKitWebView when loaded, but view is managed by GTK container hierarchy.

### 6. KeyboardHandler (`keyboard_handler.h/cpp`)

Global keyboard shortcut handler. All shortcuts handled at application level for immediate response.

**Shortcuts**:
- `Ctrl+T`: New tab
- `Ctrl+W`: Close tab
- `Ctrl+↑/↓`: Navigate tabs
- `Ctrl+←/→`: Navigate sessions
- `Ctrl+L`: Focus address bar (delegated to window)
- `Ctrl+Tab`: Fallback tab navigation

## Data Flow

### Tab Creation Flow

```
User presses Ctrl+T
  → KeyboardHandler::on_key_pressed()
  → SessionManager::new_tab()
  → Session::add_tab()
  → Tab constructor (metadata only, no WebView)
  → BrowserWindow::refresh_ui()
  → Tab bar updated
```

### Tab Focus Flow

```
User navigates to tab (Ctrl+↓)
  → KeyboardHandler::on_key_pressed()
  → SessionManager::next_tab()
  → Session::set_active_tab()
  → BrowserWindow::refresh_ui()
  → BrowserWindow::show_tab()
  → Tab::get_webview() (lazy creation)
  → Tab::create_webview() (if not loaded)
  → WebKitWebView created and added to notebook
```

### Tab Unload Flow (Future)

```
Tab inactive for 5 minutes
  → UnloadTimer::timeout()
  → Tab::destroy_webview()
  → Snapshot saved to disk
  → Tab metadata retained
  → Memory freed
```

## Memory Management

### Ownership Semantics

- **Unique Ownership**: Use `std::unique_ptr` for owned objects
- **Non-owning References**: Use raw pointers for non-owned references
- **GTK Objects**: Managed by GTK's reference counting (g_object_ref/unref)

### Memory Efficiency Strategies

1. **Lazy Loading**: WebViews created only when needed
2. **Unloading**: Inactive tabs can be unloaded (future)
3. **Metadata Only**: Unloaded tabs keep only lightweight metadata
4. **Move Semantics**: Use move constructors/assignments to avoid copies
5. **RAII**: Automatic resource management via destructors

## Threading Model

Currently single-threaded (GTK main thread). Future considerations:
- Background thread for persistence operations
- Background thread for snapshot generation
- Async I/O for network operations (handled by WebKit)

## Error Handling

- **GTK Errors**: Check return values, use GError where applicable
- **C++ Exceptions**: Avoid exceptions across C API boundaries
- **Resource Errors**: Use RAII to ensure cleanup on errors

## Extension Points

### Future Additions

1. **Persistence Layer**: `PersistenceManager` for SQLite operations
2. **Password Manager**: `PasswordManager` for credential storage
3. **History/Bookmarks**: `HistoryManager`, `BookmarkManager`
4. **IPC Interface**: D-Bus or UNIX socket for external control
5. **Unload Manager**: `UnloadManager` for tab lifecycle

## Build System

Meson build system with:
- Dependency detection (pkg-config)
- Compiler flags (C++17, optimizations)
- Test integration (optional Catch2)
- Sanitizer support (ASAN, TSAN, UBSAN)

## Testing Strategy

1. **Unit Tests**: Test individual components (SessionManager, Tab, etc.)
2. **Integration Tests**: Test component interactions
3. **Performance Tests**: Measure startup time, memory usage
4. **UI Tests**: Manual testing for keyboard shortcuts and UI behavior

## Security Considerations

- WebKit process sandboxing
- No telemetry by default
- Encrypted password storage (future)
- Content Security Policies enabled
- Input validation on all user input
