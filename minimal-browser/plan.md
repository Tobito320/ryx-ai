# Development Plan

## Milestone 1: PoC (✅ Complete)

**Status**: Complete

**Deliverables**:
- [x] Basic GTK4 window
- [x] WebKit6 integration
- [x] Keyboard shortcuts
- [x] Lazy WebView instantiation
- [x] In-memory session manager
- [x] Tab and session navigation

**Complexity**: Low-Medium

---

## Milestone 2: Session Persistence

**Status**: Pending

**Tasks**:
1. Design SQLite schema for workspaces/sessions/tabs
   - Workspace table (id, name, created_at, updated_at)
   - Session table (id, workspace_id, name, is_overview, created_at)
   - Tab table (id, session_id, url, title, favicon_path, snapshot_path, last_active, is_loaded, position)
   - Use WAL mode for better concurrency

2. Implement persistence layer
   - `PersistenceManager` class
   - Save/load workspaces, sessions, tabs
   - Handle migrations
   - Encrypted storage for sensitive data (future)

3. Integrate with SessionManager
   - Auto-save on changes
   - Load on startup
   - Periodic autosave (every 30s)

4. Add snapshot support (basic)
   - Save tab metadata
   - Store URL and title
   - Prepare for image snapshot (future)

**Complexity**: Medium

**Estimated Time**: 2-3 days

---

## Milestone 3: Tab Unload/Restore

**Status**: Pending

**Tasks**:
1. Implement auto-unload timer
   - Configurable timeout (default: 5 minutes)
   - Track last active time per tab
   - Unload inactive tabs

2. Snapshot generation
   - Capture rendered image (PNG) using WebKit snapshot API
   - Save to disk with metadata
   - Store snapshot path in tab metadata

3. Restore mechanism
   - Show snapshot placeholder when tab unloaded
   - Restore WebView on focus
   - Load URL and restore scroll position (if possible)

4. Aggressive unloading mode
   - Unload all tabs except active
   - Configurable threshold

**Complexity**: Medium-High

**Estimated Time**: 3-4 days

---

## Milestone 4: Password Manager

**Status**: Pending

**Tasks**:
1. libsecret integration
   - Primary credential store
   - Store/retrieve passwords
   - Handle Secret Service API

2. Encrypted SQLite fallback
   - Use libsodium for encryption
   - Argon2id for key derivation
   - Master password support (optional)

3. Autofill engine
   - Form field detection
   - Origin-based matching
   - Per-site allowlist/denylist

4. Password generator
   - Configurable length and character sets
   - Secure random generation

5. UI for credential management
   - View/edit credentials
   - Secure password entry
   - Export/import functionality

**Complexity**: High

**Estimated Time**: 5-7 days

---

## Milestone 5: History & Bookmarks

**Status**: Pending

**Tasks**:
1. History storage
   - SQLite backend
   - Compact indexing
   - LRU eviction (configurable retention)

2. Bookmarks
   - SQLite storage
   - Folder organization
   - Import/export (HTML format)

3. QuickOpen integration
   - Fuzzy search algorithm
   - Search history, bookmarks, open tabs, sessions
   - Keyboard-driven UI

**Complexity**: Medium

**Estimated Time**: 3-4 days

---

## Milestone 6: Performance & Optimization

**Status**: Pending

**Tasks**:
1. Memory profiling
   - Identify memory hotspots
   - Optimize allocations
   - Use memory pools for small objects

2. Startup optimization
   - Lazy initialization
   - Parallel loading where safe
   - Minimize I/O on startup

3. WebKit process model tuning
   - Configure process reuse
   - Limit process count
   - Monitor process memory

4. Benchmark suite
   - Automated performance tests
   - CI regression detection
   - Performance report generation

**Complexity**: Medium-High

**Estimated Time**: 4-5 days

---

## Milestone 7: Security Hardening

**Status**: Pending

**Tasks**:
1. WebKit security settings
   - Enable CSP
   - Disable unnecessary features
   - Configure sandboxing

2. Process isolation
   - seccomp filters (if available)
   - Resource limits
   - Network restrictions

3. Private browsing mode
   - Ephemeral sessions
   - No persistent storage
   - Clear on exit

4. Security audit
   - Code review
   - Dependency audit
   - Penetration testing (basic)

**Complexity**: Medium

**Estimated Time**: 3-4 days

---

## Milestone 8: IPC & Automation

**Status**: Pending

**Tasks**:
1. D-Bus interface
   - Open URL in workspace/session/tab
   - List sessions
   - Export session
   - Control browser remotely

2. UNIX socket fallback
   - Simple protocol
   - JSON messages
   - Authentication (basic)

3. Example scripts
   - Open URL in specific workspace
   - Export session to JSON
   - Batch operations

**Complexity**: Low-Medium

**Estimated Time**: 2-3 days

---

## Milestone 9: Testing & CI

**Status**: Pending

**Tasks**:
1. Unit tests
   - Session manager
   - Tab manager
   - Snapshot/restore
   - Keyboard shortcuts

2. Integration tests
   - Headless mode harness
   - Workspace/session/tab creation
   - Unload/restore verification

3. Performance tests
   - Automated benchmark scripts
   - Memory profiling
   - Startup time measurement

4. CI configuration
   - GitHub Actions / GitLab CI
   - Build matrix (Ubuntu/Arch)
   - Test execution
   - Linting (clang-format, clang-tidy)

**Complexity**: Medium

**Estimated Time**: 4-5 days

---

## Milestone 10: Packaging & Distribution

**Status**: Pending

**Tasks**:
1. Desktop file
   - .desktop entry
   - Icon
   - MIME types

2. Systemd user service
   - Autostart option
   - Service unit file

3. Package builds
   - Arch PKGBUILD
   - Debian/Ubuntu .deb
   - AppImage (optional)
   - Flatpak (optional)

4. Documentation
   - User manual
   - Developer guide
   - API documentation

**Complexity**: Low-Medium

**Estimated Time**: 2-3 days

---

## Total Estimated Time

**Minimum**: ~30 days (focused development)
**Realistic**: ~45-60 days (with testing and refinement)

## Priority Order

1. Milestone 2 (Session Persistence) - Foundation for everything else
2. Milestone 3 (Tab Unload/Restore) - Core memory efficiency feature
3. Milestone 6 (Performance) - Validate resource efficiency goals
4. Milestone 4 (Password Manager) - Security feature
5. Milestone 5 (History & Bookmarks) - User convenience
6. Milestone 7 (Security Hardening) - Production readiness
7. Milestone 9 (Testing & CI) - Quality assurance
8. Milestone 8 (IPC) - Advanced feature
9. Milestone 10 (Packaging) - Distribution
