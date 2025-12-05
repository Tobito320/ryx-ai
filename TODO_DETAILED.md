# RYX AI - Detailed TODO List
*Generated: 2025-12-05*
*For GitHub Agents: Each task should be a separate PR*

---

## 🔴 CRITICAL - TUI Issues

### 1. Scrolling Not Working
- **File**: `core/tui.py` lines 380-387
- **Issue**: `ScrollablePane` is created but scroll keybindings don't actually scroll
- **Fix needed**: 
  - The `_scroll_chat()` method just calls invalidate, doesn't actually scroll
  - Need to access ScrollablePane's internal scroll position
  - Consider using `Window` with `scroll_offsets` instead
- **Test**: Long chat should scroll with PageUp/PageDown

### 2. Concise Mode Still Too Verbose
- **Files**: 
  - `core/ryx_brain.py` lines 2095-2140
  - `core/council/supervisor.py` lines 58-68
- **Issue**: Even with greeting detection, non-greeting responses too long
- **Fix needed**: 
  - Lower temperature for concise mode (0.3 instead of 0.7)
  - Add more patterns: "what's your name", "who are you", etc.
  - Maybe use smaller/faster model for concise mode
  
### 3. Console.print Still Breaking TUI
- **Issue**: Some methods may still use `print()` directly
- **Fix**: Audit ALL `print()` calls in:
  - `core/session_loop.py`
  - `core/ryx_brain.py`
  - `core/council/*.py`
- **Replace with**: `self.cli.add_system()` or similar

---

## 🔴 CRITICAL - Settings/Model Issues

### 4. Model Loading Shows Wrong Message
- **File**: `ryxhub/src/components/ryxhub/SettingsView.tsx`
- **Issue**: When clicking "Connect" on a model, shows:
  > "To load /models/small/coding/qwen2.5-coder-1.5b, restart vLLM container with this model. vLLM supports one model at a time."
- **Expected behavior**:
  - Show loading progress bar
  - Actually attempt to load model via API
  - Show success/failure notification
- **Backend needed**: `/api/models/load` endpoint that hot-swaps models
- **Files to modify**:
  - `ryxhub/src/components/ryxhub/SettingsView.tsx` - Add loading bar UI
  - `ryx_pkg/interfaces/web/backend/main.py` - Add model swap endpoint
  - Consider using vLLM's model swap feature or restart container

### 5. Active Models Count Wrong
- **File**: `ryxhub/src/components/ryxhub/LeftSidebar.tsx`
- **Issue**: Shows 2 active models but only 1 is actually loaded
- **Fix**: Query actual vLLM `/v1/models` endpoint, not cached state

---

## 🟡 HIGH - RyxHub Dashboard Issues

### 6. Dashboard Uses All Mock Data
- **File**: `ryxhub/src/components/ryxhub/DashboardView.tsx`
- **Lines**: 6, 19, 27, 44
- **Issue**: Imports from `mockData.ts`, displays fake stats
- **Fix needed**:
  - Replace `mockDashboardStats` with real API calls
  - Replace `mockRecentActivity` with actual activity log
  - Replace `mockTopWorkflows` with real workflow stats
- **Backend endpoints needed**:
  - `GET /api/stats/dashboard` - Real-time stats
  - `GET /api/activity/recent` - Last N activities
  - `GET /api/workflows/top` - Most run workflows

### 7. "Active Agents" Card Misleading
- **File**: `ryxhub/src/components/ryxhub/DashboardView.tsx` line 17-23
- **Issue**: Counts models as "agents", confusing terminology
- **Fix**: Either rename to "Active Models" or implement actual agent system

### 8. Quick Actions Not Functional
- **File**: Dashboard has buttons that do nothing
- **Needed actions**:
  - "New Workflow" → Open workflow creator
  - "Import Data" → RAG document upload
  - "Run All" → Execute all active workflows
  - "Export Logs" → Download activity logs

### 9. API Calls Stat is Hardcoded
- **File**: `ryxhub/src/components/ryxhub/DashboardView.tsx` line 44
- **Shows**: "8.2K" always
- **Fix**: Track actual API calls in backend, expose via endpoint

---

## 🟡 HIGH - RAG System Issues

### 10. RAG Status Completely Fake
- **File**: `ryxhub/src/context/RyxHubContext.tsx`
- **Issue**: `ragStatus` is hardcoded mock object
- **Backend needed**:
  - `GET /api/rag/status` - Indexed count, pending, last sync
  - `POST /api/rag/sync` - Trigger re-index
  - `POST /api/rag/upload` - Upload documents
  - `DELETE /api/rag/documents/:id` - Remove document

### 11. RAG Index Button Does Nothing
- **File**: `ryxhub/src/components/ryxhub/LeftSidebar.tsx`
- **Shows**: Document counts but clicking does nothing
- **Fix**: Add modal to view/manage indexed documents

### 12. No Document Upload UI
- **Needed**: Drag-and-drop file upload for RAG
- **Supported formats**: PDF, MD, TXT, code files
- **Backend**: Parse and chunk documents, add to vector store

### 13. No RAG Search Interface
- **Needed**: UI to search indexed documents
- **Show**: Matching chunks with similarity scores
- **Use case**: Debug what context is being retrieved

---

## 🟡 HIGH - Workflow System Issues

### 14. Workflow Canvas is Display-Only
- **File**: `ryxhub/src/components/ryxhub/WorkflowCanvas.tsx`
- **Issue**: Shows nodes but can't:
  - Drag nodes to reposition
  - Connect nodes by drawing lines
  - Edit node configurations
  - Delete nodes
- **Fix**: Implement drag-and-drop with react-dnd or similar

### 15. Add Node Dialog Incomplete
- **File**: `ryxhub/src/components/ryxhub/AddNodeDialog.tsx`
- **Issue**: Creates node but doesn't persist or show on canvas
- **Fix**: 
  - Wire to context/API to actually add node
  - Generate unique position for new node
  - Update canvas immediately

### 16. No Workflow Execution
- **File**: `ryxhub/src/components/ryxhub/WorkflowCanvas.tsx` line 37
- **Issue**: `toggleWorkflowRunning` just toggles a boolean
- **Fix needed**:
  - Backend workflow engine
  - Execute nodes in dependency order
  - Stream execution logs to frontend
  - Handle node failures gracefully

### 17. No Workflow Save/Load
- **Issue**: Workflows disappear on page refresh
- **Backend needed**:
  - `POST /api/workflows` - Save workflow
  - `GET /api/workflows` - List workflows
  - `GET /api/workflows/:id` - Get single workflow
  - `PUT /api/workflows/:id` - Update workflow
  - `DELETE /api/workflows/:id` - Delete workflow

### 18. No Workflow Templates
- **Feature request**: Pre-built workflows for common tasks
- **Examples**:
  - "PR Review" - Code analysis + security scan
  - "Documentation" - Generate docs from code
  - "Test Generation" - Create unit tests
  - "Refactoring" - Suggest improvements

### 19. Node Configuration Not Editable
- **File**: `ryxhub/src/components/ryxhub/RightInspector.tsx` line 22-24
- **Issue**: "Edit Configuration" shows toast, doesn't open editor
- **Fix**: Add modal with form fields based on node type

### 20. Connection Lines Not Interactive
- **Issue**: Can't create new connections by dragging
- **Fix**: Implement connection creation UI
- **Also**: Validate connections (e.g., output can't connect to trigger)

---

## 🟡 HIGH - Chat/Session Issues

### 21. Sessions Not Persisted
- **File**: `ryxhub/src/context/RyxHubContext.tsx`
- **Issue**: Sessions stored in React state only
- **Fix**:
  - Save to localStorage for persistence
  - Better: Save to backend database
  - Sync with CLI sessions

### 22. No Session Delete
- **Issue**: Can create sessions but can't delete them
- **Fix**: Add delete button with confirmation

### 23. No Session Rename
- **Issue**: Sessions have default names, can't rename
- **Fix**: Double-click or context menu to rename

### 24. No Session Export
- **Feature request**: Export chat as markdown/JSON
- **Use case**: Share conversations, documentation

### 25. Model Switching in Chat Broken
- **File**: `ryxhub/src/components/ryxhub/ChatView.tsx`
- **Issue**: Model selector exists but may not switch mid-conversation
- **Fix**: 
  - Verify model switch API works
  - Show which model responded per message
  - Handle model loading if not active

### 26. Message Stats Sometimes Missing
- **File**: `ryxhub/src/components/ryxhub/ChatView.tsx`
- **Issue**: Token count, latency sometimes not shown
- **Fix**: Ensure backend always returns stats

### 27. No Message Edit/Delete
- **Feature request**: Edit or delete messages in chat
- **Note**: May need to regenerate subsequent responses

### 28. No Message Regenerate
- **Feature request**: "Regenerate" button on assistant messages
- **Use case**: Get different response without retyping

---

## 🟡 HIGH - CLI Issues

### 29. /style Command Output Cleanup
- **Issue**: Shows available styles but formatting could be better
- **Fix**: Show as compact list in chat, not multi-line

### 30. Tab Completion No Visual Preview
- **File**: `core/tui.py` `SlashCommandCompleter` class
- **Issue**: Completions work but no dropdown menu visible
- **Fix**: Add `CompletionsMenu` to layout

### 31. Context Percentage Always 0%
- **File**: `core/tui.py` - `self.context_percent`
- **Fix**: Calculate from message history vs model context limit

### 32. SearXNG Async Errors Not Fixed
- **File**: `core/council/searxng.py`
- **Issue**: "Timeout context manager should be used inside a task"
- **Root cause**: Calling async code from sync thread without proper loop
- **Fix**: Use `asyncio.run()` or create new event loop properly

---

## 🟢 MEDIUM - CLI Improvements

### 33. Missing CLI Commands
- `/undo` - Undo last action (not implemented)
- `/checkpoints` - Show/restore checkpoints (not implemented)
- `/fix` - Auto-fix errors (partially implemented)
- `/benchmark` - Run performance tests (not implemented)
- `/cleanup` - Clean temp files (not implemented)
- `/export` - Export session (not implemented)

### 34. No Token/s Display in CLI
- **Wanted**: Show tokens/second during and after streaming
- **File**: `core/tui.py` - `stream_end()` method
- **Fix**: Calculate and display in status bar

### 35. No Model Switching Command
- **File**: `core/session_loop.py`
- **Issue**: `/model` shows models but `/model <name>` doesn't switch
- **Fix**: Implement model switching via vLLM API

### 36. No Chat Save Command
- **Feature request**: `/save [name]` to save session as named chat
- **Sync**: Should appear in RyxHub chats
- **Backend**: `/api/sessions/save` endpoint

### 37. Thinking Steps Too Verbose
- **Issue**: Shows step indicators for every message
- **Fix**: Only show for operations taking >1 second

---

## 🟢 MEDIUM - UI/UX Improvements

### 38. No Loading Animations
- **Issue**: "Processing..." text only
- **Fix**: Spinner animation in hint bar
- **Also**: Skeleton loaders in RyxHub

### 39. No Syntax Highlighting
- **File**: `core/tui.py` - `_get_chat_text()`
- **Fix**: Parse markdown code blocks, apply highlighting
- **Library**: `pygments` for Python

### 40. No Dark/Light Mode Toggle
- **File**: RyxHub settings
- **Issue**: Always dark theme
- **Fix**: Add theme toggle, persist preference

### 41. Mobile Layout Not Optimized
- **Priority**: Low (desktop-focused)
- **But**: At least don't break on mobile

### 42. No Keyboard Shortcuts Help
- **Feature request**: `/keys` or `?` to show all keybindings
- **Also**: Tooltip hints in RyxHub

---

## 🔵 LOW - Nice to Have

### 43. No Conversation Search
- **Feature request**: Search across all sessions
- **Use case**: Find previous conversations

### 44. No Analytics Dashboard
- **Feature request**: Usage stats over time
- **Show**: Tokens used, response times, error rates

### 45. No Multi-Model Comparison
- **Feature request**: Send same prompt to multiple models
- **Use case**: Compare responses side-by-side

### 46. No Prompt Templates
- **Feature request**: Save and reuse prompts
- **Use case**: Common tasks like "review this code"

### 47. No Voice Input
- **Feature request**: Speech-to-text in CLI
- **Library**: `whisper` or system STT

### 48. No Response TTS
- **Feature request**: Text-to-speech for responses
- **Library**: `pyttsx3` or system TTS

---

## 📋 Files Needing Cleanup

### Remove/Refactor These Files
- `ryxhub/src/data/mockData.ts` - Replace with real API calls
- `core/cli_ui.py` - Deprecated, TUI replaces it
- `modes/session_mode.py` - Check if still used
- `test_backend_api.py` - Update or remove outdated tests

### Config Files Missing
- `configs/styles.yaml` - Styles hardcoded in Python
- `configs/models.yaml` - Model configs scattered in code
- `configs/workflows.yaml` - No workflow persistence

---

## ⚡ Quick Wins (15 min each)

1. [ ] Fix scroll keybindings to actually scroll
2. [ ] Add more greeting patterns to concise mode
3. [ ] Remove mock data imports from DashboardView
4. [ ] Add session delete button
5. [ ] Add session rename on double-click
6. [ ] Show actual vLLM model from /v1/models endpoint
7. [ ] Add toast notification when model switch fails
8. [ ] Add loading spinner to model load button
9. [ ] Show tok/s in chat message stats
10. [ ] Add `/save` command skeleton

---

## 🎯 Priority Order for GitHub Agents

### Sprint 1: Core Functionality
1. Fix scrolling in TUI
2. Model loading with progress bar
3. Session persistence (localStorage first)
4. Remove all mock data usage

### Sprint 2: RAG System
5. RAG status endpoint
6. Document upload UI
7. RAG search interface
8. Index management

### Sprint 3: Workflow Engine
9. Workflow save/load
10. Node drag-and-drop
11. Connection creation
12. Basic workflow execution

### Sprint 4: Polish
13. CLI-RyxHub session sync
14. Token/s display
15. Syntax highlighting
16. Keyboard shortcuts help

---

## 🔧 Backend Endpoints Needed

```
# Models
GET  /api/models              - List all models
POST /api/models/load         - Load/swap model (with progress)
GET  /api/models/active       - Currently loaded model

# Sessions
GET  /api/sessions            - List sessions
POST /api/sessions            - Create session
GET  /api/sessions/:id        - Get session with messages
PUT  /api/sessions/:id        - Update session (rename)
DELETE /api/sessions/:id      - Delete session
POST /api/sessions/:id/messages - Add message

# RAG
GET  /api/rag/status          - Index stats
POST /api/rag/upload          - Upload document
GET  /api/rag/documents       - List indexed docs
DELETE /api/rag/documents/:id - Remove document
POST /api/rag/search          - Search index

# Workflows
GET  /api/workflows           - List workflows
POST /api/workflows           - Create workflow
GET  /api/workflows/:id       - Get workflow
PUT  /api/workflows/:id       - Update workflow
DELETE /api/workflows/:id     - Delete workflow
POST /api/workflows/:id/run   - Execute workflow

# Stats
GET  /api/stats/dashboard     - Dashboard stats
GET  /api/activity/recent     - Recent activity log
```

---

*Last updated: 2025-12-05 02:18 UTC*
