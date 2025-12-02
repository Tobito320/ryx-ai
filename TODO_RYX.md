# Ryx AI - Development TODO

## ✅ COMPLETED

### Core Systems
- [x] Checkpoint system with undo/rollback (`core/checkpoints.py`)
- [x] Rich CLI UI with Claude Code-style design (`core/cli_ui.py`)
- [x] Model router with intelligent model selection (`core/model_router.py`)
- [x] Session loop with slash commands (`core/session_loop.py`)
- [x] Web search tool (SearXNG + DuckDuckGo fallback)
- [x] Scrape tool for webpage content
- [x] **Follow-up context handling** (shorter/kürzer/mehr etc.)

### UI Features
- [x] Token streaming with tok/s display
- [x] Thinking indicators (spinner while processing)
- [x] Phase visualization (⏳ → ✅)
- [x] Claude CLI-style header with path/branch/model
- [x] Footer with hints and stats
- [x] Git-style diff display
- [x] **Minimal, clean output** - less visual noise
- [x] **Compact search results with real domains**
- [x] **Step indicators** (⏳ Loading... → ✓ Loaded)

### Commands
- [x] /undo - Undo last N checkpoints
- [x] /rollback - Rollback to specific checkpoint
- [x] /checkpoints - List checkpoints
- [x] /help, /status, /models, /tools, /themes
- [x] /precision on/off - Use reasoning models

---

## 🔄 IN PROGRESS

### Phase System (EXPLORE → PLAN → APPLY → VERIFY)
- [x] Basic phase executor (`core/phases.py`)
- [ ] Integrate checkpoints into phase execution
- [ ] Show diffs during APPLY phase
- [ ] Run tests during VERIFY phase
- [ ] Automatic rollback on VERIFY failure

### Context Management
- [x] Basic context tracking (last_path, last_intent)
- [x] **Conversation context for follow-ups**
- [ ] Repo explorer for automatic file discovery
- [ ] RYX_MANIFEST.yaml for project-specific config
- [ ] Semantic file search with embeddings

---

## 📋 TODO - HIGH PRIORITY

### 1. Aider-Style Repo Mapping
```
Goal: Automatic understanding of codebase
```
- [ ] Build `RepoExplorer` that scans current directory
- [ ] Generate `repomap.json` with file metadata
  - File path, size, language, short summary
  - Tags (theme, config, network, etc.)
- [ ] Use repomap to find relevant files for tasks
- [ ] Cache repomap, refresh on file changes

### 2. Claude Code-Style Phases
```
Goal: Structured task execution
```
- [ ] EXPLORE phase: Read relevant files, build mental model
- [ ] PLAN phase: Generate step-by-step plan before changes
- [ ] APPLY phase: Generate and apply diffs (not full rewrites)
- [ ] VERIFY phase: Run tests, check for errors
- [ ] Self-critique: "Did we change only intended files?"

### 3. Tool-Only Editing
```
Goal: Controlled, reversible changes
```
- [ ] Implement `tool_read_file(path)` 
- [ ] Implement `tool_write_diff(path, unified_diff)`
- [ ] Implement `tool_git_commit(message)`
- [ ] LLM can ONLY use these tools, never raw shell
- [ ] Every change creates checkpoint automatically

### 4. RYX_MANIFEST.yaml Support
```yaml
# Example manifest
theme_files:
  - "**/*.css"
  - "**/theme*.py"
  - "**/color*.json"
test_commands:
  python: "pytest"
  javascript: "npm test"
critical_paths:
  - "core/ryx_brain.py"
  - "configs/"
allowed_actions:
  - edit
  - create
  - run_tests
```
- [ ] Parse manifest on project start
- [ ] Use for file discovery
- [ ] Use for test command selection
- [ ] Warn when editing critical paths

---

## 📋 TODO - MEDIUM PRIORITY

### 5. Specialized Prompts
```
Goal: Better LLM responses for each phase
```
- [ ] `PROMPT_EXPLORE_REPO` - Understanding codebase
- [ ] `PROMPT_PLAN_CHANGE` - Creating step plans
- [ ] `PROMPT_APPLY_DIFFS` - Generating patches
- [ ] `PROMPT_FIX_TESTS` - Debugging failures
- [ ] Each prompt defines role, format, constraints

### 6. Embeddings & RAG
```
Goal: Semantic search over codebase
```
- [x] nomic-embed-text model installed
- [ ] Generate embeddings for all code files
- [ ] Store in SQLite with vector extension
- [ ] Search by semantic similarity
- [ ] Include relevant code in LLM context

### 7. Git Integration
```
Goal: Safe version control
```
- [ ] Auto-commit after successful tasks
- [ ] Branch creation for experimental changes
- [ ] Easy revert with `/git undo`
- [ ] Show git status in status bar

### 8. Error Recovery
```
Goal: Self-healing on failures
```
- [ ] Parse error messages intelligently
- [ ] Suggest fixes based on error type
- [ ] Auto-retry with different approach
- [ ] Learn from successful fixes

---

## 📋 TODO - LOW PRIORITY

### 9. Learning System
- [ ] Track successful resolutions
- [ ] Build user preference profile
- [ ] Improve over time based on feedback
- [ ] Export/import learned patterns

### 10. Multi-File Editing
- [ ] Handle edits across multiple files
- [ ] Show all changes in unified view
- [ ] Atomic commit of all changes
- [ ] Rollback entire operation

### 11. Interactive Debugging
- [ ] Integrate with Python debugger
- [ ] Step through code with AI assistance
- [ ] Suggest breakpoints
- [ ] Explain variable state

### 12. Documentation Generation
- [ ] Auto-generate docstrings
- [ ] Create README from codebase
- [ ] Update docs when code changes

---

## 🎯 CURRENT MODEL CONFIGURATION

```
Installed Models:
- deepseek-r1:14b      → Reasoning tasks
- qwen2.5-coder:14b    → Code generation
- gemma2:2b            → Fast synthesis
- nomic-embed-text     → Embeddings
- qwen2.5:1.5b         → Intent classification
- qwen2.5:7b           → Balanced tasks
- llama2-uncensored:7b → Fallback
- gpt-oss:20b          → Precision tasks

Model Router:
- FAST: qwen2.5:1.5b, gemma2:2b
- CODE: qwen2.5-coder:14b
- THINK: deepseek-r1:14b
- EMBED: nomic-embed-text
- PRECISION: gpt-oss:20b
```

---

## 🏗️ ARCHITECTURE GOALS

```
User Input
    ↓
┌─────────────────────────────────────┐
│         INTENT CLASSIFIER           │
│  (qwen2.5:1.5b - fast, local)       │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│         SUPERVISOR AGENT            │
│  Routes to appropriate handler      │
└─────────────────────────────────────┘
    ↓
┌─────────────┬─────────────┬─────────┐
│   SIMPLE    │   COMPLEX   │  SEARCH │
│   TASKS     │   CODING    │  FIRST  │
└─────────────┴─────────────┴─────────┘
    ↓               ↓            ↓
Direct       EXPLORE→PLAN   Web Search
Execute      APPLY→VERIFY   + Synthesis
    ↓               ↓            ↓
┌─────────────────────────────────────┐
│         CHECKPOINT SYSTEM           │
│  Tracks all changes for undo        │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│            RICH UI                  │
│  Token streaming, phases, diffs     │
└─────────────────────────────────────┘
    ↓
User Output
```

---

## 📝 NOTES

### Why Search Reduces Hallucination
- LLM trained on old data → doesn't know current facts
- Search provides ground truth → LLM synthesizes
- Always cite sources → user can verify

### Why Phases Reduce Errors
- EXPLORE: LLM sees actual code, not imagined
- PLAN: User can review before changes
- APPLY: Only specific diffs, not rewrites
- VERIFY: Tests catch mistakes immediately

### Why Checkpoints Matter
- Every change is reversible
- User feels safe to experiment
- Builds trust in the system

---

## 🔗 REFERENCES

- Claude Code: https://github.com/anthropics/anthropic-quickstarts
- Aider: https://github.com/paul-gauthier/aider
- Copilot CLI: https://githubnext.com/projects/copilot-cli
