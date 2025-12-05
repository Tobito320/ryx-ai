# RYX AI - Detailed TODO List
*Generated: 2025-12-05*
*For GitHub Agents: Each task should be a separate PR. Work directly in the repository.*

---

## 📍 Repository Structure for Agents

```
/home/tobi/ryx-ai/
├── core/                    # Python CLI core
│   ├── tui.py              # Terminal UI (prompt_toolkit)
│   ├── session_loop.py     # Main session handler
│   ├── ryx_brain.py        # AI brain/reasoning
│   ├── council/            # Multi-agent supervisor
│   └── model_router.py     # Model selection
├── ryxhub/                  # React frontend
│   ├── src/components/     # UI components
│   ├── src/hooks/          # API hooks
│   └── src/context/        # State management
├── ryx_pkg/interfaces/web/  # FastAPI backend
│   └── backend/main.py     # API endpoints
├── docker/                  # Container configs
└── configs/                 # Configuration files
```

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

# Git Integration
GET  /api/git/status          - Repository status
GET  /api/git/diff            - Current changes
POST /api/git/commit          - Create commit
GET  /api/git/branches        - List branches
POST /api/git/pr              - Create PR

# MCP (Model Context Protocol)
GET  /api/mcp/servers         - List configured MCP servers
POST /api/mcp/connect         - Connect to MCP server
GET  /api/mcp/tools           - Available tools from servers
```

---

## 🚀 NEW FEATURES - Inspired by Copilot CLI & Claude Code

### Git Integration (Like Copilot CLI)

#### 49. `/git status` Command
- **Feature**: Show git status in chat
- **File**: `core/session_loop.py`
- **Implementation**: Parse `git status --porcelain` output
- **Display**: Colored file lists (green=staged, red=modified)

#### 50. `/git diff` Command
- **Feature**: Show current diff with syntax highlighting
- **File**: `core/session_loop.py`
- **Implementation**: Run `git diff`, highlight with pygments
- **Also**: Support `/git diff <file>` for specific files

#### 51. `/git commit` Command
- **Feature**: AI-generated commit message
- **Flow**: 
  1. Show staged changes
  2. Generate commit message from diff
  3. User approves or edits
  4. Execute commit
- **Backend**: Use LLM to summarize changes

#### 52. `/git pr` Command
- **Feature**: Create PR from current branch
- **Integration**: Use `gh` CLI if available
- **Generate**: PR title and description from commits
- **Preview**: Show PR before creating

#### 53. `/git blame` Command
- **Feature**: Show blame for file/line
- **Use case**: "Who wrote this code?"
- **Display**: Author, date, commit message

#### 54. Git Context Awareness
- **Feature**: Auto-detect git repo on startup
- **Show**: Branch name in prompt (already done)
- **Add**: Show uncommitted changes count
- **Add**: Show behind/ahead of remote

---

### MCP Server Support (Like Copilot CLI)

#### 55. MCP Server Configuration
- **Feature**: Support Model Context Protocol servers
- **Config file**: `~/.ryx/mcp-config.json`
- **Format**:
```json
{
  "servers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@anthropics/mcp-filesystem"]
    }
  }
}
```

#### 56. `/mcp connect` Command
- **Feature**: Connect to configured MCP server
- **List**: Available servers from config
- **Status**: Show connected servers

#### 57. MCP Tool Discovery
- **Feature**: Discover tools from connected servers
- **Display**: Available tools and their descriptions
- **Invoke**: Call tools from chat

#### 58. Built-in MCP Servers
- **Filesystem**: Read/write files
- **Git**: Git operations
- **Web**: Fetch URLs
- **Database**: Query databases

---

### Custom Slash Commands (Like Claude Code)

#### 59. User-Defined Commands
- **Feature**: Custom slash commands from markdown files
- **Location**: `.ryx/commands/` in project or `~/.ryx/commands/` global
- **Format**: Markdown files with frontmatter
```markdown
---
name: review
description: Review code for issues
---
Review this code for:
1. Security vulnerabilities
2. Performance issues
3. Best practices violations

$ARGUMENTS
```

#### 60. Command Arguments
- **Feature**: Pass arguments to custom commands
- **Syntax**: `/review src/main.py` → `$ARGUMENTS` = `src/main.py`
- **Also**: Support `$FILE`, `$SELECTION` variables

#### 61. Project-Specific Commands
- **Feature**: Commands scoped to project
- **Location**: `.ryx/commands/` in repo root
- **Use case**: Team-shared coding standards

#### 62. Command Marketplace/Sharing
- **Feature**: Share commands via RyxHub
- **Browse**: Popular community commands
- **Install**: One-click add to project

---

### Agent System (Like Claude Code /agents)

#### 63. Sub-Agent Support
- **Feature**: Spawn specialized agents for tasks
- **Command**: `/agent code-review`, `/agent security`, `/agent docs`
- **Parallel**: Run multiple agents simultaneously
- **Aggregate**: Combine agent outputs

#### 64. Agent Definitions
- **Feature**: Define custom agents
- **Config**: `.ryx/agents/` directory
- **Properties**: System prompt, model, tools, temperature

#### 65. Agent Memory
- **Feature**: Persistent agent memory across sessions
- **Store**: Key facts learned during interactions
- **Recall**: Reference previous context

---

### Code Actions (Like Copilot CLI)

#### 66. `/explain` Command
- **Feature**: Explain selected code or file
- **Input**: File path or piped code
- **Output**: Line-by-line explanation
- **Levels**: Simple, detailed, expert

#### 67. `/refactor` Command  
- **Feature**: Suggest refactoring improvements
- **Detect**: Code smells, anti-patterns
- **Show**: Before/after diff
- **Apply**: One-click apply changes

#### 68. `/test` Command
- **Feature**: Generate unit tests
- **Detect**: Testing framework (pytest, jest, etc.)
- **Create**: Test file with cases
- **Cover**: Edge cases, error handling

#### 69. `/debug` Command
- **Feature**: Analyze error and suggest fixes
- **Input**: Paste error message
- **Output**: Explanation + fix suggestions
- **Apply**: Auto-fix if possible

#### 70. `/fix` Command Enhancement
- **Current**: Partially implemented
- **Add**: Parse error from last command
- **Add**: Show diff before applying
- **Add**: Rollback capability

#### 71. `/docs` Command
- **Feature**: Generate documentation
- **Types**: README, API docs, inline comments
- **Format**: Markdown, JSDoc, docstrings
- **Update**: Keep docs in sync with code

---

### Session Management (Like Claude Code)

#### 72. `/compact` Command
- **Feature**: Summarize and compact conversation
- **Reduce**: Token count while keeping context
- **Show**: Summary of what was compacted
- **Use case**: Long sessions hitting context limit

#### 73. `/context` Command
- **Feature**: Show current context usage
- **Display**: Token count, percentage of limit
- **List**: Loaded files, RAG chunks
- **Clear**: Option to clear specific items

#### 74. `/cost` Command
- **Feature**: Show session cost/usage
- **Track**: Tokens used, API calls
- **Estimate**: Cost if using paid API
- **Export**: Usage report

#### 75. `/export` Command
- **Feature**: Export conversation
- **Formats**: Markdown, JSON, HTML
- **Options**: With/without system messages
- **Destination**: File or clipboard

#### 76. Session Checkpoints
- **Feature**: Save named checkpoints
- **Command**: `/checkpoint save "before refactor"`
- **Restore**: `/checkpoint restore "before refactor"`
- **List**: `/checkpoints` to see all

---

### IDE Integration

#### 77. VS Code Extension
- **Feature**: Ryx sidebar in VS Code
- **Show**: Chat history, sessions
- **Actions**: Send selection to Ryx
- **Sync**: With CLI sessions

#### 78. Neovim Plugin
- **Feature**: Ryx integration for Neovim
- **Keybinds**: Send buffer/selection to Ryx
- **Float**: Response in floating window
- **Complete**: AI code completion

#### 79. Cursor-Style Inline
- **Feature**: Inline AI suggestions in editor
- **Trigger**: Tab to accept
- **Show**: Ghost text completion
- **Multi-line**: Full function generation

---

### Security Features

#### 80. `/security-review` Command
- **Feature**: Security audit of codebase
- **Check**: Common vulnerabilities (OWASP)
- **Report**: Severity levels, fix suggestions
- **CI**: Run in CI pipeline

#### 81. Secrets Detection
- **Feature**: Detect hardcoded secrets
- **Scan**: API keys, passwords, tokens
- **Block**: Prevent committing secrets
- **Replace**: Suggest env variable usage

#### 82. Permission System
- **Feature**: Approve actions before execution
- **Levels**: Auto, ask, deny per action type
- **Trust**: Remember decisions per project
- **Audit**: Log all executed actions

---

### Performance & Monitoring

#### 83. `/benchmark` Command
- **Feature**: Benchmark model performance
- **Test**: Response time, tokens/s
- **Compare**: Different models
- **Report**: Performance summary

#### 84. Background Tasks
- **Feature**: Long-running tasks in background
- **Command**: `/bashes` to list running tasks
- **Stream**: Output to separate pane
- **Kill**: Terminate background task

#### 85. Health Check
- **Feature**: `/doctor` command
- **Check**: vLLM status, SearXNG, disk space
- **Fix**: Suggest solutions for issues
- **Report**: System health summary

---

### Collaboration Features

#### 86. Share Session Link
- **Feature**: Share conversation via link
- **Generate**: Unique URL for session
- **Access**: View-only or editable
- **Expire**: Optional expiration

#### 87. Team Workspaces
- **Feature**: Shared sessions in RyxHub
- **Invite**: Team members to workspace
- **Share**: Workflows, prompts, agents
- **Audit**: Activity log

#### 88. PR Comments Integration
- **Feature**: Comment on PRs with AI assistance
- **Command**: `/pr-comment <pr_number>`
- **Suggest**: Review comments
- **Post**: Comment directly to GitHub

---

### Advanced Features

#### 89. Multiline Input
- **Feature**: Write prompts across multiple lines
- **Trigger**: Shift+Enter for new line
- **Submit**: Enter on empty line
- **Paste**: Support multi-line paste

#### 90. Output Styles
- **Feature**: `/output-style` command
- **Modes**: Normal, compact, verbose, JSON
- **Persist**: Remember preference
- **Toggle**: Quick switch hotkey

#### 91. Vim Mode
- **Feature**: Vim keybindings in input
- **Command**: `/vim` to toggle
- **Support**: Basic motions, editing
- **Status**: Show mode in prompt

#### 92. Hooks System
- **Feature**: Run code on events
- **Events**: Before/after response, on error
- **Use case**: Auto-format code, log to file
- **Config**: `.ryx/hooks/` directory

#### 93. Plugin System
- **Feature**: Extend Ryx with plugins
- **Install**: `/plugin install <name>`
- **List**: `/plugins` to see installed
- **Create**: Plugin development guide

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
11. [ ] Add `/git status` basic implementation
12. [ ] Add `/explain` for file explanation
13. [ ] Add `/doctor` health check
14. [ ] Add context percentage calculation
15. [ ] Add multiline input (Shift+Enter)

---

## 🎯 Priority Order for GitHub Agents

### Sprint 1: Core Functionality (Week 1)
1. Fix scrolling in TUI
2. Model loading with progress bar
3. Session persistence (localStorage first)
4. Remove all mock data usage
5. Basic `/git status` and `/git diff`

### Sprint 2: RAG System (Week 2)
6. RAG status endpoint
7. Document upload UI
8. RAG search interface
9. Index management
10. Vector store optimization

### Sprint 3: Workflow Engine (Week 3)
11. Workflow save/load
12. Node drag-and-drop
13. Connection creation
14. Basic workflow execution
15. Workflow templates

### Sprint 4: Git Integration (Week 4)
16. `/git commit` with AI message
17. `/git pr` create PR
18. Git context in prompt
19. Branch management
20. Conflict resolution helper

### Sprint 5: Advanced CLI (Week 5)
21. Custom slash commands
22. MCP server support
23. `/explain`, `/refactor`, `/test`
24. Session checkpoints
25. Export/import sessions

### Sprint 6: Polish & Collaboration (Week 6)
26. CLI-RyxHub session sync
27. Token/s display
28. Syntax highlighting
29. VS Code extension basics
30. Security review feature

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
POST /api/sessions/:id/export - Export session

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
GET  /api/stats/usage         - Token usage stats

# Git Integration
GET  /api/git/status          - Repository status
GET  /api/git/diff            - Current changes
POST /api/git/commit          - Create commit
GET  /api/git/branches        - List branches
POST /api/git/pr              - Create PR

# MCP (Model Context Protocol)
GET  /api/mcp/servers         - List configured MCP servers
POST /api/mcp/connect         - Connect to MCP server
GET  /api/mcp/tools           - Available tools from servers

# Commands
GET  /api/commands            - List custom commands
POST /api/commands            - Create custom command
GET  /api/commands/marketplace - Browse shared commands

# Health
GET  /api/health              - System health check
GET  /api/health/vllm         - vLLM status
GET  /api/health/searxng      - SearXNG status
```

---

## 🏗️ Architecture Notes for Agents

### CLI Flow
```
User Input → TUI → SessionLoop → Brain/Supervisor → LLM → Response → TUI
```

### RyxHub Flow
```
React UI → API Hooks → FastAPI Backend → vLLM/Services → Response
```

### Key Integration Points
- `core/session_loop.py` - Add new slash commands here
- `ryx_pkg/interfaces/web/backend/main.py` - Add API endpoints here
- `ryxhub/src/hooks/useRyxApi.ts` - Add React Query hooks here
- `core/tui.py` - Modify UI behavior here

---

*Last updated: 2025-12-05 02:22 UTC*
*Total tasks: 93*
