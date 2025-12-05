# RYX AI - Detailed TODO List
*Generated: 2025-12-05*

## 🔴 CRITICAL - TUI Issues

### Scrolling Not Working
- **File**: `core/tui.py` lines 380-387
- **Issue**: `ScrollablePane` is created but scroll keybindings not added
- **Fix needed**: Add `page-up`, `page-down`, `up`, `down` key bindings when focus is on chat
- **Also**: Mouse scroll events may not be properly captured

### Concise Mode Still Too Verbose
- **Files**: 
  - `core/ryx_brain.py` lines 2095-2100
  - `core/council/supervisor.py` lines 58-68
- **Issue**: Style prompts say "ONE sentence" but model ignores it
- **Fix needed**: 
  - Add `max_tokens=50` for concise mode greetings
  - Detect greetings ("hi", "hello", "hey") and force ultra-short response
  - Example mapping: "hi" → "Hey!", "how are you" → "Good, you?"
  
### Console.print Still Breaking TUI
- **Issue**: Some methods may still use `print()` directly
- **Fix**: Audit ALL `print()` calls in:
  - `core/session_loop.py`
  - `core/ryx_brain.py`
  - `core/council/*.py`
- **Replace with**: `self.cli.add_system()` or similar

---

## 🟡 HIGH - RyxHub Issues

### Still Using Mock Data
- **Files**:
  - `ryxhub/src/data/mockData.ts` - 383 lines of fake data
  - `ryxhub/src/context/RyxHubContext.tsx` - Uses `mockSessions`
  - `ryxhub/src/components/ryxhub/DashboardView.tsx` - Uses mock stats
- **Fix**: Replace all mock data with real API calls

### Sessions Not Persisted
- **File**: `ryxhub/src/context/RyxHubContext.tsx`
- **Issue**: Sessions created in frontend disappear on refresh
- **Fix**: Save to backend API, sync with CLI sessions

### RAG Index - No Functionality
- **File**: `ryxhub/src/components/ryxhub/DashboardView.tsx`
- **Shows**: `mockRAGStatus` with fake numbers
- **Fix**: Implement real RAG status endpoint in backend

### Quick Actions - No Functionality
- **File**: Dashboard shows action buttons that do nothing
- **Fix**: Wire up to actual backend endpoints

### Model Loading Notifications Missing
- **Issue**: Starting session with offline model should show notification
- **File**: `ryxhub/src/components/ryxhub/NewSessionDialog.tsx`
- **Fix**: Check model status before creating session, show toast if needs loading

### Workflow Canvas - Placeholder Only
- **File**: `ryxhub/src/components/ryxhub/WorkflowCanvas.tsx`
- **Issue**: Displays mock nodes, no actual workflow execution
- **Priority**: Low (not core feature)

---

## 🟡 HIGH - CLI Issues

### /style Command Display
- **Issue**: Shows available styles but output still breaks TUI sometimes
- **Fix**: Ensure `_set_style()` only uses `self.cli.console.print()`

### Tab Completion Not Showing Preview
- **File**: `core/tui.py` `SlashCommandCompleter` class
- **Issue**: Completions work but no visual dropdown preview
- **Fix**: Add `CompletionsMenu` to layout

### Context Percentage Not Updating
- **Issue**: Shows 0% always, never updates based on actual token usage
- **File**: `core/tui.py` - `self.context_percent`
- **Fix**: Calculate from `len(messages) * avg_tokens / model_context_limit`

### SearXNG Async Errors (Suppressed but not fixed)
- **File**: `core/council/searxng.py`
- **Issue**: "Timeout context manager should be used inside a task"
- **Root cause**: Calling async code from sync thread
- **Fix**: Use `asyncio.run()` or proper event loop in background thread

---

## 🟢 MEDIUM - Improvements

### Missing CLI Commands
- `/undo` - Not implemented
- `/checkpoints` - Not implemented  
- `/fix` - Partially implemented
- `/benchmark` - Not implemented
- `/cleanup` - Not implemented

### No Token/s Display in CLI
- **Wanted**: Show tokens/second during streaming
- **File**: `core/tui.py` - `stream_end()` method
- **Fix**: Calculate and display in status bar or after response

### No Model Switching in CLI
- **File**: `core/session_loop.py`
- **Issue**: `/model` command shows models but can't switch mid-session
- **Fix**: Implement `/model <name>` to switch active model

### Chat Sync Between CLI and RyxHub
- **Feature request**: Save CLI session as chat accessible from RyxHub
- **Files**: 
  - `core/session_loop.py` - Add `/save` command
  - `ryx_pkg/interfaces/web/backend/main.py` - Add sync endpoint
  - `ryxhub/src/` - Fetch synced sessions

---

## 🔵 LOW - Nice to Have

### Thinking Steps Too Verbose
- **Issue**: Shows "● Analyzing query" → "● Response ready" for every message
- **Fix**: Only show for queries that take >1 second

### No Loading Animation
- **Issue**: Just shows "Processing..." text
- **Fix**: Add spinner character animation in hint bar

### No Syntax Highlighting in Responses
- **File**: `core/tui.py` - `_get_chat_text()`
- **Fix**: Parse markdown code blocks and apply syntax highlighting

### RyxHub Dark Mode Toggle
- **Issue**: Always dark, no light mode option
- **File**: Should be in settings but missing

### RyxHub Responsive Issues
- **Issue**: Mobile layout not optimized
- **Priority**: Very low (desktop focused)

---

## 📋 Files Needing Cleanup

### Remove/Update These Files
- `core/cli_ui.py` - Old CLI, partially replaced by TUI
- `ryxhub/src/data/mockData.ts` - Should be empty or removed
- `modes/session_mode.py` - Deprecated?
- `test_backend_api.py` - Outdated tests

### Config Files Missing
- No `configs/styles.yaml` - Styles hardcoded in Python
- No config for default model per task type

---

## ⚡ Quick Wins (Can fix in <10 min each)

1. [ ] Add scroll keybindings to TUI
2. [ ] Reduce `max_tokens` for concise mode greetings
3. [ ] Add greeting detection → instant short response
4. [ ] Update context_percent calculation
5. [ ] Remove mock data usage in DashboardView
6. [ ] Add toast notification for offline model selection

---

## 🎯 Priority Order

1. **Fix scrolling** - Core usability
2. **Fix concise mode** - User explicitly requested
3. **Remove mock data from RyxHub** - Makes it actually functional
4. **Session persistence** - Core feature
5. **CLI-RyxHub sync** - Key feature request
6. **Token/s display** - User requested metrics
7. **Model switching** - Core feature
