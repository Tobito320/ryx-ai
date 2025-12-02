# RYX AI - Architecture Overhaul TODO

## Goal: Transform Ryx into a Claude Code / Aider-like Agent

Based on analysis of Claude Code and Aider architectures, Ryx needs these fundamental changes
to stop hallucinating and become actually useful.

---

## 🎯 Core Problem

Ryx halluziniert weil:
- Kein strukturierter Kontext (LLM rät Pfade/Dateien)
- Keine Phasen (alles in einem Prompt)
- Keine echten Tools (freie Textausgabe statt kontrollierte Aktionen)
- Keine Verifikation (keine Feedback-Loops)

---

## 📋 PHASE 1: Repository Explorer & Context Management

### 1.1 RepoExplorer Module
**File: `core/repo_explorer.py`**

- [ ] Scan project directory recursively
- [ ] Build file metadata index:
  - Path, size, extension, last modified
  - File type classification (code, config, asset, doc)
  - Language detection
- [ ] Generate repomap.json with:
  - File tree structure
  - Heuristic tags (theme, config, network, ui, test, etc.)
  - Short summaries for key files
- [ ] Semantic tagging based on:
  - Filename patterns (*.config.*, *theme*, *test*, etc.)
  - Content analysis (imports, exports, class names)
  - Directory conventions (src/, tests/, config/, etc.)

### 1.2 Smart File Selection
**Enhance: `core/ryx_brain.py`**

- [ ] `find_relevant_files(task: str) -> List[str]`
  - Search repomap by keywords from task
  - Rank by relevance (name match > content match > directory)
  - Return top 5-20 files
- [ ] `get_file_context(files: List[str]) -> str`
  - Read selected files
  - Truncate if too large
  - Format for LLM consumption

### 1.3 Project Manifest System
**File: `RYX_MANIFEST.yaml` (per project)**

```yaml
project:
  name: "ryx-ai"
  type: "python"
  
context:
  theme_files:
    - "core/theme.py"
    - "core/printer.py"
  config_files:
    - "configs/*.yaml"
  test_command: "python -m pytest tests/"
  build_command: null
  
critical_paths:
  - "core/ryx_brain.py"  # Core logic, be careful
  - "core/tools.py"      # Tool definitions
  
conventions:
  editor: "nvim"
  terminal: "kitty"
  style: "black"
```

- [ ] Create manifest schema
- [ ] Auto-generate manifest for new projects
- [ ] Load manifest at brain init
- [ ] Use manifest for file selection

---

## 📋 PHASE 2: Agent Phases & State Machine

### 2.1 Phase System
**File: `core/phases.py`**

```python
class Phase(Enum):
    IDLE = "idle"
    EXPLORE = "explore"      # Understanding codebase
    PLAN = "plan"            # Creating action plan
    APPLY = "apply"          # Executing changes
    VERIFY = "verify"        # Testing/validating
    
@dataclass
class AgentState:
    phase: Phase
    task: str
    context_files: List[str]
    plan: Optional[Plan]
    changes: List[Change]
    errors: List[str]
```

- [ ] Implement Phase enum
- [ ] Implement AgentState dataclass
- [ ] Phase transition logic
- [ ] Phase-specific prompts

### 2.2 Phase: EXPLORE
- [ ] Triggered by: new task, unfamiliar codebase
- [ ] Actions:
  - Scan relevant files
  - Build mental model
  - Write notes to memory
- [ ] Output: Context summary, relevant files list
- [ ] Prompt: `PROMPT_EXPLORE`

### 2.3 Phase: PLAN
- [ ] Triggered by: after explore, or simple known tasks
- [ ] Actions:
  - Analyze task requirements
  - List files to modify
  - Create step-by-step plan
- [ ] Output: Structured plan with steps
- [ ] Prompt: `PROMPT_PLAN`
- [ ] User confirmation before proceeding

### 2.4 Phase: APPLY
- [ ] Triggered by: approved plan
- [ ] Actions:
  - Generate diffs for each file
  - Apply changes via tools
  - Track all modifications
- [ ] Output: List of changes made
- [ ] Prompt: `PROMPT_APPLY`

### 2.5 Phase: VERIFY
- [ ] Triggered by: after apply
- [ ] Actions:
  - Run tests if available
  - Run linter/type checker
  - Self-review changes
- [ ] Output: Pass/fail, error details
- [ ] Loop back to PLAN if errors
- [ ] Prompt: `PROMPT_VERIFY`

---

## 📋 PHASE 3: Tool-Based Editing (No Free Writing)

### 3.1 Structured Tool System
**File: `core/agent_tools.py`**

Replace free-form file writing with controlled tools:

```python
class AgentTool(ABC):
    name: str
    description: str
    parameters: Dict
    
    @abstractmethod
    def execute(self, **params) -> ToolResult

# Core Tools
class ReadFileTool(AgentTool):
    """Read file contents - ground truth"""
    
class WriteFileTool(AgentTool):
    """Write entire file (with backup)"""
    
class ApplyDiffTool(AgentTool):
    """Apply unified diff patch"""
    
class SearchCodeTool(AgentTool):
    """Search code with grep/ripgrep"""
    
class RunCommandTool(AgentTool):
    """Execute shell command safely"""
    
class GitCommitTool(AgentTool):
    """Commit current changes"""
    
class GitRevertTool(AgentTool):
    """Revert last commit/changes"""
```

- [ ] Implement base AgentTool class
- [ ] Implement ReadFileTool
- [ ] Implement ApplyDiffTool (unified diff format)
- [ ] Implement SearchCodeTool
- [ ] Implement RunCommandTool (with safety)
- [ ] Implement GitCommitTool
- [ ] Implement GitRevertTool
- [ ] Tool registry with enable/disable

### 3.2 Tool-Only LLM Output
**Enhance: `core/ryx_brain.py`**

- [ ] LLM must output structured JSON/commands, not free text
- [ ] Parse LLM output as tool calls
- [ ] Execute tools and collect results
- [ ] Feed results back to LLM

Example LLM output format:
```json
{
  "thought": "I need to read the theme file first",
  "tool": "read_file",
  "params": {"path": "core/theme.py"}
}
```

### 3.3 Diff-Based Editing
- [ ] Never let LLM write entire files
- [ ] Always use unified diff format
- [ ] Apply diffs with proper validation
- [ ] Automatic backup before changes

---

## 📋 PHASE 4: Git Integration & Safety

### 4.1 Git Safety Layer
**File: `core/git_safety.py`**

- [ ] Auto-commit before major changes
- [ ] Branch management for experiments
- [ ] Easy revert commands
- [ ] Change tracking with descriptions

### 4.2 Undo System
- [ ] `/undo` command - revert last change
- [ ] `/undo all` - revert to session start
- [ ] `/history` - show changes made
- [ ] Automatic git commits per change

---

## 📋 PHASE 5: Specialized Prompts

### 5.1 Prompt Templates
**File: `core/prompts.py`**

Each phase gets its own optimized prompt:

```python
PROMPT_EXPLORE = """
You are exploring a codebase to understand its structure.
Your task: {task}

Available files in this project:
{repomap}

Instructions:
1. Identify which files are relevant to the task
2. List what you need to understand
3. Ask to read specific files if needed

Output format:
- relevant_files: [list of paths]
- questions: [things you need to know]
- summary: [what you understand so far]
"""

PROMPT_PLAN = """
You are creating a plan to: {task}

Context files:
{file_contents}

Instructions:
1. Break down the task into steps
2. List which files need changes
3. Describe each change briefly
4. DO NOT write any code yet

Output format:
- steps: [ordered list of actions]
- files_to_modify: [paths]
- files_to_create: [paths]
- risks: [potential issues]
"""

PROMPT_APPLY = """
You are implementing step {step_num} of the plan:
{step_description}

Current file content:
```{language}
{file_content}
```

Instructions:
1. Generate ONLY a unified diff
2. Change only what's necessary
3. Preserve existing style
4. Add comments only if complex

Output: unified diff only, no explanation
"""

PROMPT_VERIFY = """
You just made changes. Verify they are correct.

Changes made:
{changes_summary}

Test output:
{test_output}

Lint output:
{lint_output}

Instructions:
1. Did we change only intended files?
2. Do tests pass?
3. Any obvious bugs?
4. Should we revert anything?

Output:
- status: pass/fail
- issues: [list of problems]
- recommendations: [next steps]
"""
```

- [ ] Implement PROMPT_EXPLORE
- [ ] Implement PROMPT_PLAN
- [ ] Implement PROMPT_APPLY
- [ ] Implement PROMPT_VERIFY
- [ ] Implement PROMPT_FIX_ERROR
- [ ] Prompt selection based on phase

### 5.2 Prompt Constraints
Every prompt must include:
- [ ] Clear role definition
- [ ] Explicit output format
- [ ] "Do not guess" instructions
- [ ] "Ask if uncertain" instructions
- [ ] Tool usage constraints

---

## 📋 PHASE 6: Self-Critique & Evaluation

### 6.1 Self-Review Step
**Enhance: `core/ryx_brain.py`**

After every change:
- [ ] LLM reviews its own output
- [ ] Checks for hallucinations
- [ ] Validates file paths exist
- [ ] Confirms changes match plan

### 6.2 Error Recovery Loop
- [ ] If verification fails → back to PLAN
- [ ] Max 3 retry attempts
- [ ] Clear error feedback to LLM
- [ ] Human escalation if stuck

---

## 📋 PHASE 7: UI/UX Improvements

### 7.1 Enhanced Chain of Thought
**Enhance: `core/printer.py`**

Show everything happening:
```
→ Understanding request...
▸ Phase: EXPLORE
  · Scanning project files...
  · Found 47 relevant files
  · Key files: theme.py, printer.py, config.yaml
▸ Phase: PLAN  
  · Step 1: Update color definitions in theme.py
  · Step 2: Modify printer output colors
  · Step 3: Test theme changes
▸ Awaiting confirmation...
  Continue with this plan? [y/n]
▸ Phase: APPLY
  · Applying diff to theme.py...
  · ✓ theme.py modified (3 lines changed)
▸ Phase: VERIFY
  · Running tests...
  · ✓ All tests pass
✓ Task completed successfully
```

- [ ] Phase indicator display
- [ ] File operation logging
- [ ] Progress for long operations
- [ ] Clear error display
- [ ] Confirmation prompts

### 7.2 Interactive Plan Approval
- [ ] Show plan before execution
- [ ] Allow editing plan
- [ ] Skip/modify individual steps
- [ ] Abort at any point

---

## 📋 PHASE 8: Integration & Testing

### 8.1 Integration Points
- [ ] Update session_loop.py to use phases
- [ ] Update ryx_brain.py with new architecture
- [ ] Migrate existing tools to new system
- [ ] Backward compatibility for simple queries

### 8.2 Testing
- [ ] Unit tests for each phase
- [ ] Integration tests for full workflows
- [ ] Hallucination detection tests
- [ ] Performance benchmarks

---

## 📅 Implementation Order

### Week 1: Foundation
1. [ ] RepoExplorer basic implementation
2. [ ] Phase enum and state machine
3. [ ] Basic prompt templates

### Week 2: Tools
4. [ ] Tool base class and registry
5. [ ] Core tools (read, diff, search)
6. [ ] Git safety layer

### Week 3: Brain Rewrite
7. [ ] Phase-based execution in brain
8. [ ] Tool-only LLM output parsing
9. [ ] Self-critique integration

### Week 4: Polish
10. [ ] Enhanced UI/chain of thought
11. [ ] Manifest system
12. [ ] Testing and bugfixes

---

## 🎯 Success Metrics

- [ ] No more invented file paths
- [ ] No more fake package names
- [ ] Changes are reversible
- [ ] User sees what's happening
- [ ] Tasks complete successfully >80%
- [ ] Feels like Claude Code locally

---

## 📚 Reference

- Claude Code: https://docs.anthropic.com/claude-code
- Aider: https://aider.chat/docs/
- Agentic Coding: https://www.anthropic.com/engineering/claude-code-best-practices
