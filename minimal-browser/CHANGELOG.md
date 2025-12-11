# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-01-XX

### Added - PoC Release

- Initial proof-of-concept implementation
- GTK4 window with minimal UI
- WebKit6 integration
- Keyboard shortcuts:
  - `Ctrl+T`: New tab
  - `Ctrl+W`: Close tab
  - `Ctrl+↑/↓`: Navigate tabs
  - `Ctrl+←/→`: Navigate sessions
  - `Ctrl+L`: Focus address bar
- Lazy WebView instantiation (tabs only load when focused)
- In-memory session/workspace model
- Tab and session management
- Overview placeholder session
- Basic address bar navigation

### Technical Details

- C++17 codebase
- Meson build system
- Single-process model with WebKit shared secondary process
- Memory-efficient tab management
- Clean separation of concerns (Tab, Session, Workspace, SessionManager)

## [Unreleased]

### Planned

- Session persistence (SQLite)
- Tab unload/restore with snapshots
- Password manager (libsecret + encrypted SQLite)
- Autofill integration
- History and bookmarks
- QuickOpen (fuzzy search)
- Performance optimizations
- Security hardening
- IPC/D-Bus interface
- Unit and integration tests
- Packaging and distribution
