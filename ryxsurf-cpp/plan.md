# Development Plan

## Milestone 1: PoC ✅ Complete

**Status**: Complete

**Deliverables**:
- [x] Basic GTK4 window
- [x] WebKit6 integration
- [x] Keyboard shortcuts
- [x] Lazy WebView instantiation
- [x] Tab management
- [x] Meson build system
- [x] Unit tests skeleton
- [x] Performance test script

**Complexity**: Low-Medium

---

## Milestone 2: Core Data Models

**Status**: Pending

**Tasks**:
1. Implement Workspace struct
2. Implement Session struct
3. Implement TabMeta struct (enhanced)
4. Update SessionManager with workspace/session hierarchy

**Complexity**: Low

**Estimated Time**: 1 day

---

## Milestone 3: Session/Tab Manager + Tests

**Status**: Pending

**Tasks**:
1. Implement SessionManager with in-memory operations
2. Unit tests for create/destroy/switch
3. Auto-close empty sessions (except Overview)
4. Tab navigation within sessions

**Complexity**: Medium

**Estimated Time**: 2-3 days

---

## Milestone 4: Lazy WebView Factory

**Status**: Pending

**Tasks**:
1. Implement WebViewFactory for on-demand instantiation
2. Snapshot placeholder renderer
3. Memory-efficient WebView creation

**Complexity**: Medium

**Estimated Time**: 2 days

---

## Milestone 5: Tab Unload/Restore & Snapshot

**Status**: Pending

**Tasks**:
1. Implement unload logic (configurable timeout, default 5 min)
2. Snapshot PNG + minimal HTML generation
3. Restore logic with URL and history state
4. Tests for unload/restore behavior

**Complexity**: Medium-High

**Estimated Time**: 3-4 days

---

## Milestone 6: Persistence

**Status**: Pending

**Tasks**:
1. Encrypted SQLite schema for metadata
2. Argon2id KDF + libsodium encryption wrapper
3. Autosave & graceful exit restore
4. CLI export/import

**Complexity**: Medium-High

**Estimated Time**: 4-5 days

---

## Milestone 7: Password Manager

**Status**: Pending

**Tasks**:
1. Integrate libsecret (primary)
2. Encrypted SQLite fallback
3. UI for credential management (secure dialog)
4. Autofill integration

**Complexity**: High

**Estimated Time**: 5-7 days

---

## Milestone 8: IPC / Automation

**Status**: Pending

**Tasks**:
1. UNIX socket + simple JSON RPC
2. Open URL, list sessions, export commands
3. Sample scripts in examples/

**Complexity**: Low-Medium

**Estimated Time**: 2-3 days

---

## Milestone 9: UI Polish & CSS

**Status**: Pending

**Tasks**:
1. Minimal CSS theme
2. GPU animations (optional flag)
3. Tab visuals (vertical/horizontal modes)
4. Session separators (persistent)

**Complexity**: Medium

**Estimated Time**: 3-4 days

---

## Milestone 10: Performance Tuning

**Status**: Pending

**Tasks**:
1. LTO, custom allocators (optional)
2. WebKit tuning (cache size, process reuse)
3. Measure and optimize hotspots
4. Performance regression tests

**Complexity**: Medium-High

**Estimated Time**: 4-5 days

---

## Total Estimated Time

**Minimum**: ~30 days (focused development)
**Realistic**: ~45-60 days (with testing and refinement)

## Priority Order

1. Milestone 2 (Core Data Models) - Foundation
2. Milestone 3 (Session/Tab Manager) - Core functionality
3. Milestone 4 (WebView Factory) - Memory efficiency
4. Milestone 5 (Unload/Restore) - Core memory efficiency feature
5. Milestone 6 (Persistence) - Data persistence
6. Milestone 7 (Password Manager) - Security feature
7. Milestone 9 (UI Polish) - User experience
8. Milestone 10 (Performance) - Validate resource efficiency
9. Milestone 8 (IPC) - Advanced feature
