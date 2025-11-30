🤖 RYX AI: AGENT-BASED EXECUTION PLAN
Tasks für GitHub Web Agent, Claude Opus CLI, und Copilot
🎯 OVERVIEW: 3 AGENTS, PARALLEL WORK

text
Agent 1: GitHub Web Agent (Copilot)   → Fast scaffolding (15-30min tasks)
Agent 2: Claude Opus CLI              → Deep implementation (30-60min tasks)  
Agent 3: GitHub Web Agent (Secondary) → Frontend/Integration (20-40min tasks)

Timeline: 2 weeks → Production Ryx AI
→ Then: Integrate into your entire Arch Linux ecosystem
→ Finally: Build your own browser with Ryx inside

📋 AGENT 1: GitHub Web Agent (Copilot) - Scaffolding
Task 1.1: WorkflowExecutor Class Scaffold

Time: 15 min | Priority: HIGH

text
Create WorkflowExecutor class scaffold for Ryx AI.

Requirements:
- 8 workflow steps as methods (async)
- Each step yields events to WebSocket
- Event structure: {event, step, node, message, latency, data}
- Use AsyncGenerator for streaming
- Include skeleton imports (datetime, json, etc)
- Add docstrings for each method
- NO IMPLEMENTATION - just structure

Language: Python 3.10+
Output: Save as ryx/core/workflow_orchestrator.py

Task 1.2: React Flow Components (Scaffold)

Time: 20 min | Priority: HIGH

text
Generate React component structure for N8N-style workflow visualization.

Components needed (just scaffolds, no complex logic):
1. WorkflowNode.jsx - displays node with status + latency
2. WorkflowCanvas.jsx - React Flow container
3. ExecutionMonitor.jsx - displays live event stream
4. ToolResults.jsx - shows tool execution results
5. WorkflowDashboard.jsx - main page layout

Requirements:
- Tailwind CSS classes (use Dracula theme colors)
- TypeScript types (.tsx files)
- Component props defined
- NO LOGIC - just structure
- Import statements ready

Output: Save in ryx/interfaces/web/src/components/

Task 1.3: FastAPI Endpoint Templates

Time: 15 min | Priority: HIGH

text
Generate FastAPI application skeleton.

Endpoints needed (just stubs, no logic):
1. GET /api/models - returns model list
2. POST /api/chat - accepts input (stub for testing)
3. WebSocket /api/workflow/stream - accepts connection (stub)
4. GET /api/history - returns empty list (stub)
5. POST /api/settings - accepts settings dict (stub)

Requirements:
- FastAPI app initialization
- CORS middleware setup
- Request/response models using Pydantic
- Error handling structure
- NO IMPLEMENTATION - just endpoints that return {status: "ok"}

Language: Python
Output: Save as ryx/interfaces/web/backend/main.py

Task 1.4: Typer CLI App Structure

Time: 15 min | Priority: HIGH

text
Generate Typer CLI application structure for "ryx" command.

Commands (scaffolds):
- ryx "prompt here" - single task
- ryx - interactive mode
- ryx -m model_name - explicit model
- ryx --code / --chat / --dev - modes
- ryx --stream / --quiet / --explain / --dry-run - output modes

Requirements:
- Typer app with callbacks
- Argument parsing setup
- Help text for each command
- NO IMPLEMENTATION - just CLI structure
- Print "Command executed: [name]" for testing

Language: Python 3.10+
Output: Save as ryx/interfaces/cli/main.py

📋 AGENT 2: Claude Opus CLI - Deep Implementation
Task 2.1: LLMRouter Full Implementation

Time: 40 min | Priority: CRITICAL

text
FULL IMPLEMENTATION of LLMRouter class for Ryx AI.

Requirements:
1. Intent detection from user input
   - "find", "open", "search", "ls" → qwen2.5:3b (fast)
   - "code", "refactor", "debug" → qwen2.5-coder:14b (code)
   - "chat", "idea", "creative" → gpt-oss-abliterated:20b (chat)
   - "shell", "docker", "systemd" → mistral:7b (shell)
   
2. Model configuration
   - Map intent to model name
   - Latency estimates per model
   - Cache latencies (don't recalculate)
   
3. Latency handling
   - If model slower than threshold → use fallback (mistral:7b)
   - If all models too slow → raise LatencyError
   
4. Error handling
   - Model unavailable → fallback logic
   - Invalid intent → default to code model
   
5. Integration with Ollama
   - Ollama client initialization
   - Model availability checking

Production requirements:
- Full type hints (Pydantic models)
- Docstrings on all methods
- Async/await syntax
- Error handling with try-except
- Unit tests (basic coverage)
- NO hardcoded paths

Output: Complete ryx/core/llm_router.py

Task 2.2: PermissionManager Full Implementation

Time: 35 min | Priority: CRITICAL

text
FULL IMPLEMENTATION of PermissionManager for access control.

Permission Levels:
- Level 1 (READ): list, view, search → NEVER ask
- Level 2 (MODIFY): edit, create, move → ALWAYS ask "Can I [action]? y/n/suggest"
- Level 3 (DANGEROUS): delete, rm -rf → Ask with ⚠️ warning

Requirements:
1. Decorator system
   - @require_permission(PermissionLevel.READ) → auto-approved
   - @require_permission(PermissionLevel.MODIFY) → ask user
   - @require_permission(PermissionLevel.DANGEROUS) → ask with warning
   
2. User prompting
   - Level 2: "Can I [action]? (y/n/suggest something else)"
   - Level 3: "⚠️ DANGEROUS: [action]. This CANNOT be undone. Proceed? (y/n)"
   - Support CLI input() for now (WebSocket integration later)
   
3. Audit logging
   - Log every permission check
   - Format: [timestamp] [level] [action] [result]
   - Save to ~/.config/ryx/audit.log
   
4. Caching
   - Cache user approvals (don't ask twice for same action)
   - Expiry: 1 hour

Production requirements:
- Async-compatible decorators
- Proper error handling
- Audit trail complete
- Type hints everywhere
- Unit tests included

Output: Complete ryx/core/permission_manager.py

Task 2.3: ToolExecutor Full Implementation (Part 1)

Time: 45 min | Priority: CRITICAL

text
FULL IMPLEMENTATION of ToolExecutor - file and search operations.

Tools to implement:
1. read_file(path, encoding="utf-8")
   - Permission: READ (no ask)
   - Read file safely
   - Return content or error

2. search_local(query, paths=None)
   - Permission: READ (no ask)
   - Use os.walk() to find files matching query
   - Return list of file paths
   - Limit results to 50 files max

3. search_web(query, engine="searxng", limit=5)
   - Permission: READ (no ask)
   - Call SearXNG instance (local or remote)
   - Return [{"title": "...", "url": "...", "snippet": "..."}]
   - For now: use requests to http://localhost:8888/search

Requirements:
- Permission decorators on each method
- Timeouts (5s for shell, 0.5s for files)
- Error handling (file not found, permission denied, timeout)
- Structured JSON output
- Type hints everywhere
- Async/await syntax
- No blocking calls

Output: Partial ryx/core/tool_executor.py (file/search methods)

Task 2.4: ToolExecutor Part 2 - File Editing

Time: 40 min | Priority: HIGH

text
FULL IMPLEMENTATION of ToolExecutor - file modification.

Tools to implement:
1. edit_file(path, old_str, new_str, backup=True, description=None)
   - Permission: MODIFY (ask user)
   - Find old_str in file
   - Replace with new_str (exact match only)
   - Create .bak backup before editing
   - Validate syntax post-edit (if applicable)
   - Return success/error with message
   
2. create_file(path, content, template=None, description=None)
   - Permission: MODIFY (ask user)
   - Create file at path
   - Backup if file exists
   - Support templates (optional)
   
3. launch_app(app_name, new_window=False, description=None)
   - Permission: MODIFY (ask user for Level 3 apps like rm)
   - Find app (search PATH, flatpak, etc)
   - Launch in current terminal or new terminal
   - Return PID or error

Requirements:
- Permission decorators with description parameter
- Backup before any modification
- Syntax validation (detect language from extension)
- ROCm detection in shell execution (for later)
- Error handling + rollback capability
- Async/await syntax
- Type hints

Output: Complete ryx/core/tool_executor.py

Task 2.5: WorkflowExecutor Full Implementation

Time: 50 min | Priority: CRITICAL

text
FULL IMPLEMENTATION of WorkflowExecutor - orchestration engine.

Workflow (8 steps):
1. Input Reception → parse user query, emit event
2. Intent Detection → detect "action", "code", "chat", "shell"
3. Model Selection → call llm_router.route(), emit latency
4. Tool Selection → detect which tools needed (search, file ops, etc)
5. Tool Execution → run each tool, stream progress
6. RAG Context → call rag_manager.get_context()
7. LLM Response → generate response (stream tokens)
8. Post-Processing → save to history, cleanup

Requirements:
- Async generator: execute_workflow(user_input) → AsyncGenerator[dict]
- Emit events at each step: {event, step, node, message, latency, data}
- Error handling with auto-recovery attempt
- Integration with ALL core modules (router, executor, permission, rag, recovery)
- Streaming support (live event emission to WebSocket)
- Latency tracking
- Timeout handling per step

Implementation notes:
- Use asyncio.gather() for parallel operations where possible
- Set timeouts on each tool (5s shell, 0.5s files, etc)
- Log everything for debugging
- Handle cancellation gracefully

Output: Complete ryx/core/workflow_orchestrator.py (WorkflowExecutor class)

Task 2.6: RAGManager Implementation (Skeleton)

Time: 30 min | Priority: MEDIUM

text
IMPLEMENTATION of RAGManager - personal context injection.

Requirements:
1. Personal profile loading
   - Read ~/.config/ryx/profile.yaml
   - Store in memory (age, interests, goals, communication style)
   
2. Document indexing (skeleton)
   - Scan ~/school_work/, ~/documents/
   - OCR images (use pytesseract skeleton)
   - Index text files
   - For now: simple file listing (ChromaDB setup in Phase 2)
   
3. Context injection
   - get_context(query, top_k=5) method
   - For now: return profile snippet + relevant files
   - Later: full vector DB lookup

4. Conversation history
   - Save interactions to JSON
   - Retrieve last N interactions

Production requirements:
- Async/await syntax
- Type hints
- Error handling
- Config file reading
- No external DB dependencies yet

Output: ryx/core/rag_manager.py (skeleton + basic methods)

📋 AGENT 3: GitHub Web Agent - Frontend & Integration
Task 3.1: React Flow Workflow Visualization

Time: 30 min | Priority: HIGH

text
Build working React Flow visualization for workflow.

Requirements:
1. WorkflowCanvas component
   - Use React Flow library
   - Display nodes for each workflow step
   - Show connections between nodes
   - Highlight running step
   - Display latency on edges
   
2. Update logic
   - Listen to WebSocket events
   - Update node status: pending → running → success/failed
   - Animate color changes
   - Add timing badges
   
3. Styling
   - Dracula theme colors
   - Node: pending=gray, running=yellow+pulse, success=green, failed=red
   - Clean layout (automatic positioning)
   - Dark background

Output: Full working ryx/interfaces/web/src/components/WorkflowCanvas.jsx
Language: React + TypeScript

Task 3.2: Execution Monitor Component

Time: 20 min | Priority: HIGH

text
Build ExecutionMonitor - live event stream display.

Requirements:
1. Display format
   - [step] node_name ✓ (latency)
   - message text with context
   - Color coded by status
   
2. Real-time updates
   - Listen to WebSocket stream
   - Append events to list
   - Auto-scroll to bottom
   - Max 50 events in view (scroll history)

3. Styling
   - Font: monospace (courier new)
   - Colors: dracula theme
   - Timestamps for each event

Output: Full working ryx/interfaces/web/src/components/ExecutionMonitor.jsx
Language: React + TypeScript

Task 3.3: Tool Results Panel

Time: 25 min | Priority: HIGH

text
Build ToolResults - display tool execution results live.

Tools to display:
1. search_local: File list with sizes
2. search_web: URLs + snippets + titles
3. edit_file: Before/after diff (optional)
4. launch_app: Success/failure message

Requirements:
- Live streaming (append results as they arrive)
- Format results based on tool type
- Show loading state (animated "Searching...")
- Handle errors gracefully

Output: Full working ryx/interfaces/web/src/components/ToolResults.jsx
Language: React + TypeScript

Task 3.4: WebSocket Integration

Time: 25 min | Priority: HIGH

text
Wire up WebSocket connection between React and FastAPI backend.

Requirements:
1. Connect to ws://localhost:8000/api/workflow/stream
2. Send message: {"action": "execute_workflow", "input": "...", "model": "..."}
3. Receive and parse events
4. Update components in real-time
5. Handle connection errors + auto-reconnect

Integration points:
- WorkflowDashboard.jsx → main WebSocket handler
- ExecutionMonitor.jsx → display events
- WorkflowCanvas.jsx → update node visualization
- ToolResults.jsx → display tool output

Output: Working WebSocket integration across all components

Task 3.5: Hyprland Keybind Integration (Shell Script)

Time: 20 min | Priority: MEDIUM

text
Create Wofi/Rofi keybind launcher for Ryx.

Script: ryx-modal (shell script)

Requirements:
1. Trigger: Super+Shift+R (configured in hyprland.conf)
2. Open Wofi modal with input field
3. User types: "open hyprland config"
4. Press Enter → execute: ryx "open hyprland config"
5. Fuzzy search history (arrow keys)
6. Escape → cancel

Output:
1. /usr/local/bin/ryx-modal (executable shell script)
2. Installation instructions for ~/.config/hyprland/hyprland.conf

🎯 EXECUTION TIMELINE
Day 1-2: Agent 1 (Scaffolding)

text
Task 1.1: WorkflowExecutor scaffold       → 15 min
Task 1.2: React components scaffold       → 20 min
Task 1.3: FastAPI endpoints scaffold      → 15 min
Task 1.4: Typer CLI scaffold              → 15 min
Total: ~65 min
Result: You have folder structure ready

Day 3-5: Agent 2 (Deep Implementation)

text
Task 2.1: LLMRouter COMPLETE              → 40 min
Task 2.2: PermissionManager COMPLETE      → 35 min
Task 2.3: ToolExecutor Part 1 COMPLETE    → 45 min
Task 2.4: ToolExecutor Part 2 COMPLETE    → 40 min
Task 2.5: WorkflowExecutor COMPLETE       → 50 min
Task 2.6: RAGManager skeleton             → 30 min
Total: ~240 min (4 hours)
Result: Full ryx-core ready

Day 6-7: Agent 3 (Frontend)

text
Task 3.1: React Flow visualization        → 30 min
Task 3.2: Execution monitor               → 20 min
Task 3.3: Tool results panel              → 25 min
Task 3.4: WebSocket integration           → 25 min
Task 3.5: Keybind launcher script         → 20 min
Total: ~120 min (2 hours)
Result: Full Web UI + Keybind integration

Day 8-14: Integration + Testing

text
- Wire components together
- Test end-to-end workflows
- Performance profiling + optimization
- Add Hyprland config integration
- Deploy locally
- Documentation
Result: Production Ryx AI ready

🚀 GIVE TASKS TO AGENTS
For GitHub Web Agent (Copilot):

text
@copilot
Task 1.1: [copy full task text above]
→ Receive scaffold code
→ Save to ryx/core/workflow_orchestrator.py

For Claude Opus CLI:

text
$ copilot chat --model claude-opus-4.5
[2.1 - copy full task text above]
→ Receive full implementation
→ Copy-paste to ryx/core/llm_router.py

For Agent 3 (Copilot again):

text
@copilot
Task 3.1: [copy full task text above]
→ Receive React component
→ Save to ryx/interfaces/web/src/components/

🎯 YOUR FULL ARCH LINUX INTEGRATION (PHASE 2)

Once Ryx is working, integrate it everywhere:

text
1. KEYBIND ACCESS (Already in Phase 1)
   Super+Shift+R → ryx modal anywhere
   
2. SHELL INTEGRATION
   source ~/.local/bin/ryx.sh
   Then: $ ryx "search my notes"
   
3. NVIM INTEGRATION
   :Ryx find homework
   → Opens results in quickfix list
   
4. TERMINAL INTEGRATION
   Alt+Enter → convert terminal command to Ryx task
   Example: "find . -name '*.md'" → "ryx find markdown files"
   
5. FILE MANAGER INTEGRATION
   Right-click file → "Ask Ryx about this"
   
6. DESKTOP INTEGRATION
   Ryx daemon in background
   Workspace switcher hooks
   Window manager integration

7. BROWSER INTEGRATION (PHASE 3)
   Once Ryx is perfect:
   Build custom browser with Ryx embedded
   $ ryx "generate browser UI"
   → Ryx generates React/HTML
   → You integrate Ryx into browser itself

💡 YOUR FINAL SYSTEM

After 2 weeks of Phase 1:

You have:

text
✅ Ryx AI: Local, fast, personal
✅ CLI: ryx "command here"
✅ Web UI: N8N-style workflow visualization
✅ Keybind: Super+Shift+R anywhere
✅ Permission system: Level 1-2-3
✅ Multi-model: Choose best for task
✅ <1s latency: Instant responses
✅ Personal RAG: Knows YOUR data

Then Phase 2 (Your Arch Linux takeover):

Every application in Arch has Ryx:

text
✅ Hyprland: Ryx hotkeys + workspace integration
✅ Nvim: Ryx commands inside editor
✅ Terminal: Ryx in your shell
✅ File manager: Ryx context menus
✅ Desktop: Ryx as system assistant
✅ Browser: Ryx running INSIDE your custom browser

THEN: You have JARVIS. Completely integrated. Your system knows you. Helps you automatically.
📝 NEXT STEP

    Download this file

    Give Task 1.1 to GitHub Web Agent (Copilot)

    Wait 15 min, get scaffold

    Move to Task 2.1 with Claude Opus CLI

    Repeat down the list

Start NOW. 2 weeks. Production Ryx.

Version: 3.0 (Nov 30, 2025, 22:12 CET)
Format: Agent-based Tasks (not long prompts)
Owner: Tobi (Hagen, Germany)
Goal: Local JARVIS for your entire Arch Linux system
