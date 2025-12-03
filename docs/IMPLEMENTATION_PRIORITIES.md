# RYX AI - Implementation Priorities

**Based on**: Architecture Evaluation (2025-12-03)  
**Current Score**: 58/150 (39% complete toward Claude Code level)  
**Target**: Transform RYX into production-grade agentic CLI

---

## Executive Priority Matrix

| Priority | Item | Impact | Effort | Time | Status |
|----------|------|--------|--------|------|--------|
| 🔴 P0 | Agent System Integration | CRITICAL | Medium | 3d | ❌ TODO |
| 🔴 P0 | Phase System Activation | CRITICAL | Medium | 3d | ❌ TODO |
| 🔴 P0 | Test Execution Tools | CRITICAL | Low | 2d | ❌ TODO |
| 🟠 P1 | Self-Healing / Rescue Mode | HIGH | High | 4d | ❌ TODO |
| 🟠 P1 | Diff-Based Editing | HIGH | Medium | 3d | ❌ TODO |
| 🟠 P1 | Git Auto-Commit | HIGH | Low | 2d | ❌ TODO |
| 🟡 P2 | UI/UX Fixes | MEDIUM | Low | 3d | ❌ TODO |
| 🟡 P2 | Repo Explorer | MEDIUM | Medium | 3d | ❌ TODO |
| 🟡 P2 | Planning Documentation | MEDIUM | Low | 2d | ❌ TODO |
| 🟢 P3 | Test Coverage | LOW | High | 4d | ❌ TODO |
| 🟢 P3 | Linting & CI | LOW | Low | 2d | ❌ TODO |
| 🟢 P3 | Refactor God Classes | LOW | High | 3d | ❌ TODO |

---

## 🔴 Phase 1: Critical Foundation (Week 1-2, ~8 days)

### Goal
Get supervisor/operator architecture working and enable phase-based execution

### Tasks

#### 1. Integrate Supervisor Agent (3 days)
**Why**: Currently RyxBrain is monolithic (1800 lines). Need separation of planning vs execution.

**What to Do**:
```python
# core/ryx_brain.py - Add supervisor integration
from core.agents.supervisor import SupervisorAgent
from core.agents.operator import OperatorAgent
from core.planning.complexity import ComplexityGate

class RyxBrain:
    def __init__(self, ollama: OllamaClient):
        self.ollama = ollama
        self.supervisor = SupervisorAgent(ollama, model="qwen2.5-coder:14b")
        self.operator = OperatorAgent(ollama, model="qwen2.5:3b")
        self.complexity_gate = ComplexityGate()
    
    def understand(self, user_input: str) -> Plan:
        # Route based on complexity
        complexity = self.complexity_gate.assess(user_input)
        
        if complexity.is_trivial():
            # Direct execution, no planning needed
            return self._create_simple_plan(user_input)
        else:
            # Use supervisor for complex tasks
            plan = self.supervisor.plan_task(user_input, self.context)
            return plan
    
    def execute(self, plan: Plan) -> TaskResult:
        # Delegate to operator
        result = self.operator.execute_plan(plan, self.context)
        
        if not result.success and result.attempts >= plan.max_retries:
            # Escalate to supervisor rescue mode
            rescue = self.supervisor.rescue(plan, result.errors)
            if rescue.action == "TAKEOVER":
                # Supervisor executes directly
                return self.supervisor.execute(plan)
        
        return result
```

**Files to Modify**:
- `core/ryx_brain.py`: Add supervisor/operator integration
- `core/agents/supervisor.py`: Complete implementation
- `core/agents/operator.py`: Complete implementation
- `core/planning/complexity.py`: Create complexity gate

**Success Criteria**:
- [ ] Complex tasks routed to supervisor
- [ ] Supervisor creates structured plans
- [ ] Operator executes plans step-by-step
- [ ] Failed tasks escalate to supervisor rescue

---

#### 2. Activate Phase System (3 days)
**Why**: Phase system (EXPLORE → PLAN → APPLY → VERIFY) exists but isn't used. Need to wire it in.

**What to Do**:
```python
# core/session_loop.py - Wire in phase executor
from core.phases import PhaseExecutor, Phase

class SessionLoop:
    def __init__(self, safety_mode: str = "normal"):
        # ... existing init ...
        self.phase_executor = PhaseExecutor(self.brain, self.cli)
    
    def _process(self, user_input: str):
        # Detect if this is a code task
        intent = self.brain.classify_intent(user_input)
        
        if intent == Intent.CODE_TASK:
            # Use phase system for code tasks
            result = self.phase_executor.run_to_completion(user_input)
            self._show_result(result)
        else:
            # Simple tasks: direct execution
            plan = self.brain.understand(user_input)
            success, result = self.brain.execute(plan)
            self._show_result(result)
```

**UI Changes**:
```python
# core/cli_ui.py - Show phase progress
def show_phase(phase: Phase, status: str):
    """Show current phase with status"""
    emoji = {
        Phase.EXPLORE: '🔍',
        Phase.PLAN: '📋',
        Phase.APPLY: '🛠️',
        Phase.VERIFY: '🧪'
    }[phase]
    
    status_symbol = {
        'running': '⏳',
        'done': '✅',
        'failed': '❌'
    }[status]
    
    print(f"{emoji} {phase.value.upper()} {status_symbol}")
```

**Files to Modify**:
- `core/session_loop.py`: Wire phase executor into main loop
- `core/phases.py`: Ensure all phases work
- `core/cli_ui.py`: Add phase visualization

**Success Criteria**:
- [ ] Code tasks trigger phase system
- [ ] Each phase shown in UI with progress
- [ ] User can see EXPLORE → PLAN → APPLY → VERIFY flow
- [ ] Can abort between phases

---

#### 3. Add Test Execution Tools (2 days)
**Why**: VERIFY phase cannot work without ability to run tests.

**What to Do**:
```python
# core/tool_registry.py - Add test tools
@dataclass
class TestResult:
    """Structured test result"""
    total: int
    passed: int
    failed: int
    errors: int
    duration_seconds: float
    failures: List[TestFailure]  # With stack traces

class ToolRegistry:
    def _register_test_tools(self):
        # Python tests
        self.register_tool(Tool(
            name="run_pytest",
            description="Run Python tests with pytest",
            category=ToolCategory.TEST,
            safety_level=SafetyLevel.SAFE,
            handler=self._run_pytest
        ))
        
        # JavaScript tests
        self.register_tool(Tool(
            name="run_npm_test",
            description="Run JavaScript tests with npm test",
            category=ToolCategory.TEST,
            safety_level=SafetyLevel.SAFE,
            handler=self._run_npm_test
        ))
    
    def _run_pytest(self, path: str = ".", args: str = "") -> TestResult:
        """Run pytest and parse output"""
        cmd = f"pytest {path} {args} --json-report --json-report-file=/tmp/pytest.json"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        # Parse JSON output
        with open('/tmp/pytest.json') as f:
            data = json.load(f)
        
        return TestResult(
            total=data['summary']['total'],
            passed=data['summary']['passed'],
            failed=data['summary']['failed'],
            errors=data['summary']['errors'],
            duration_seconds=data['duration'],
            failures=[
                TestFailure(
                    test_name=f['nodeid'],
                    error_message=f['call']['longrepr'],
                    stack_trace=f['call']['traceback']
                )
                for f in data['tests'] if f['outcome'] == 'failed'
            ]
        )
```

**Files to Modify**:
- `core/tool_registry.py`: Add test execution tools
- `core/phases.py`: Use test tools in VERIFY phase

**Success Criteria**:
- [ ] Can run `pytest` and get structured results
- [ ] Can run `npm test` and get structured results
- [ ] VERIFY phase runs appropriate tests
- [ ] Test failures trigger rescue mode

---

## 🟠 Phase 2: Error Recovery & Quality (Week 3-4, ~9 days)

### Goal
Add self-healing capabilities and improve code quality

### Tasks

#### 4. Implement Rescue Mode (4 days)
**Why**: Users shouldn't have to manually fix every error. Agent should try alternative approaches.

**What to Do**:
```python
# core/agents/supervisor.py - Implement rescue
class SupervisorAgent(BaseAgent):
    def rescue(self, plan: Plan, errors: List[str]) -> RescueAction:
        """Analyze failure and determine recovery strategy"""
        
        # Build rescue prompt
        prompt = self.RESCUE_PROMPT.format(
            query=plan.original_query,
            plan=json.dumps(plan.to_dict()),
            errors="\n".join(errors)
        )
        
        # Ask LLM what went wrong and how to fix
        response = self.ollama.chat(
            messages=[{"role": "user", "content": prompt}],
            model=self.config.model
        )
        
        rescue_data = json.loads(response.response)
        
        if rescue_data['action'] == 'ADJUST_PLAN':
            # Create new plan with fixes
            new_plan = Plan.from_dict(rescue_data['adjusted_plan'])
            return RescueAction(action='ADJUST_PLAN', new_plan=new_plan)
        
        elif rescue_data['action'] == 'CHANGE_AGENT':
            # Try different agent type
            return RescueAction(action='CHANGE_AGENT', new_agent=rescue_data['new_agent'])
        
        else:  # TAKEOVER
            # Supervisor executes directly
            return RescueAction(action='TAKEOVER', direct_result=rescue_data['direct_result'])
```

**Files to Modify**:
- `core/agents/supervisor.py`: Complete rescue implementation
- `core/agents/operator.py`: Add failure detection
- `core/ryx_brain.py`: Wire rescue mode into execution

**Success Criteria**:
- [ ] Failed tasks automatically analyzed
- [ ] Supervisor proposes alternative approaches
- [ ] Retry with different strategy (max 3 attempts)
- [ ] Human escalation after max retries

---

#### 5. Add Diff-Based Editing (3 days)
**Why**: Currently RYX rewrites entire files. Should use diffs like Aider/Claude Code.

**What to Do**:
```python
# core/tool_registry.py - Add diff tool
class ToolRegistry:
    def _register_diff_tool(self):
        self.register_tool(Tool(
            name="apply_diff",
            description="Apply unified diff to a file",
            category=ToolCategory.FILESYSTEM,
            safety_level=SafetyLevel.RISKY,
            handler=self._apply_diff
        ))
    
    def _apply_diff(self, file_path: str, diff: str) -> ToolResult:
        """Apply unified diff to file"""
        import tempfile
        import shutil
        
        # Create backup
        backup_path = f"{file_path}.backup"
        shutil.copy(file_path, backup_path)
        
        # Write diff to temp file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(diff)
            diff_path = f.name
        
        # Apply diff using patch command
        result = subprocess.run(
            f"patch {file_path} < {diff_path}",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            # Restore backup
            shutil.copy(backup_path, file_path)
            return ToolResult(success=False, error=f"Patch failed: {result.stderr}")
        
        return ToolResult(success=True, output=f"Applied diff to {file_path}")
```

**Update APPLY Phase Prompt**:
```python
PROMPT_APPLY = """
You are implementing step {step_num}: {step_description}

Current file content:
```{language}
{file_content}
```

IMPORTANT: Generate ONLY a unified diff, NOT the entire file.
Format: 
--- a/path/to/file
+++ b/path/to/file
@@ -10,7 +10,8 @@
 context line
-old line
+new line
 context line

Output ONLY the diff, no explanation.
"""
```

**Files to Modify**:
- `core/tool_registry.py`: Add `apply_diff` tool
- `core/phases.py`: Update APPLY phase to use diffs
- `core/cli_ui.py`: Show diffs before applying

**Success Criteria**:
- [ ] Code changes use unified diff format
- [ ] User sees diff before applying
- [ ] Can review and approve/reject diffs
- [ ] Backups created automatically

---

#### 6. Improve Git Integration (2 days)
**Why**: Need safer git operations - auto-commit before changes, proper status checking.

**What to Do**:
```python
# core/git_safety.py - NEW FILE
class GitSafety:
    """Safe git operations for Ryx"""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
    
    def is_repo_clean(self) -> Tuple[bool, str]:
        """Check if repo has uncommitted changes"""
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            return False, "Uncommitted changes exist"
        return True, "Clean"
    
    def auto_commit_before_task(self, task_description: str):
        """Create checkpoint before major changes"""
        if not self.is_repo_clean()[0]:
            # User has uncommitted work - warn them
            print("⚠️  Warning: Uncommitted changes exist")
            confirm = input("Create checkpoint commit before proceeding? [Y/n] ")
            if confirm.lower() != 'n':
                self.commit(f"[ryx checkpoint] Before: {task_description}")
    
    def commit(self, message: str) -> bool:
        """Commit current changes"""
        subprocess.run(["git", "add", "."], cwd=self.repo_path)
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=self.repo_path,
            capture_output=True
        )
        return result.returncode == 0
    
    def undo_last_commit(self):
        """Undo last commit (soft reset)"""
        subprocess.run(
            ["git", "reset", "--soft", "HEAD~1"],
            cwd=self.repo_path
        )
```

**Files to Create**:
- `core/git_safety.py`: New git operations module

**Files to Modify**:
- `core/phases.py`: Add auto-commit before APPLY phase
- `core/session_loop.py`: Implement `/undo` command properly
- `core/cli_ui.py`: Show git status in status bar

**Success Criteria**:
- [ ] Auto-commit before major changes
- [ ] `/undo` command works reliably
- [ ] Git status shown in status bar
- [ ] Can revert failed changes

---

## 🟡 Phase 3: UX & Polish (Week 5-6, ~8 days)

### Goal
Improve user experience and add missing features

### Tasks

#### 7. Fix UI Issues (3 days)
**Why**: Current UI has positioning issues, duplicate headers, too much noise.

**What to Do**:
- Fix status bar positioning (should be at top, always)
- Remove duplicate header calls
- Reduce visual noise (fewer substeps, more summaries)
- Consistent emoji indicators
- Add phase progress bars

**Files to Modify**:
- `core/cli_ui.py`: Consolidate UI code, fix positioning
- `core/session_loop.py`: Remove duplicate UI calls
- Delete: `core/cli_ui_modern.py`, `core/rich_ui.py` (keep only one UI)

**Success Criteria**:
- [ ] Status bar always at top
- [ ] No duplicate output
- [ ] Clean, minimal output
- [ ] Phase progress clearly shown

---

#### 8. Add Repo Explorer (3 days)
**Why**: Need automatic codebase understanding for better file selection.

**What to Do**:
```python
# core/repo_explorer.py - NEW FILE
class RepoExplorer:
    """Scan and index project files"""
    
    def scan_project(self, root_path: str) -> RepoMap:
        """Scan project and build file index"""
        files = []
        
        for path in Path(root_path).rglob("*"):
            if path.is_file() and not self._should_ignore(path):
                files.append(FileMetadata(
                    path=str(path),
                    size=path.stat().st_size,
                    language=self._detect_language(path),
                    type=self._classify_file_type(path),
                    tags=self._generate_tags(path)
                ))
        
        return RepoMap(files=files)
    
    def find_relevant_files(self, task: str, repomap: RepoMap) -> List[str]:
        """Find files relevant to task"""
        # Use keyword matching + embeddings
        keywords = self._extract_keywords(task)
        
        scored_files = []
        for file in repomap.files:
            score = 0
            # Name match
            if any(kw in file.path.lower() for kw in keywords):
                score += 10
            # Tag match
            if any(kw in file.tags for kw in keywords):
                score += 5
            
            if score > 0:
                scored_files.append((file, score))
        
        # Return top 20 files
        scored_files.sort(key=lambda x: x[1], reverse=True)
        return [f.path for f, _ in scored_files[:20]]
```

**Files to Create**:
- `core/repo_explorer.py`: New repo scanning module

**Files to Modify**:
- `core/ryx_brain.py`: Use repo explorer for file selection
- `core/phases.py`: Use repo explorer in EXPLORE phase

**Success Criteria**:
- [ ] Project scanned on startup
- [ ] `repomap.json` generated and cached
- [ ] Relevant files found automatically
- [ ] Better context for code tasks

---

#### 9. Add Planning Documentation (2 days)
**Why**: Complex tasks should generate written plans for review.

**What to Do**:
```python
# core/phases.py - Enhance PLAN phase
class PhaseExecutor:
    def _run_plan_phase(self, task: str) -> Plan:
        """PLAN phase - with written output"""
        
        # Get plan from supervisor
        plan = self.supervisor.plan_task(task, self.context)
        
        # Write plan to file
        plan_file = Path.cwd() / "ryx_plan.md"
        with open(plan_file, 'w') as f:
            f.write(f"# Task: {task}\n\n")
            f.write(f"## Understanding\n{plan.understanding}\n\n")
            f.write(f"## Steps\n")
            for i, step in enumerate(plan.steps, 1):
                status = "[ ]"  # Not done yet
                f.write(f"{status} **Step {i}**: {step.description}\n")
                f.write(f"   - Action: `{step.action}`\n")
                f.write(f"   - Params: {step.params}\n\n")
        
        # Show plan to user
        self.cli.show_file_preview(plan_file)
        
        # Ask for approval
        if not self.cli.confirm("Execute this plan?"):
            raise UserAborted("Plan rejected by user")
        
        return plan
```

**Files to Modify**:
- `core/phases.py`: Write plans to `ryx_plan.md`
- `core/cli_ui.py`: Add file preview and approval UI

**Success Criteria**:
- [ ] Complex tasks generate `ryx_plan.md`
- [ ] User can review plan before execution
- [ ] Plan updated as steps complete
- [ ] Can abort before execution

---

## 🟢 Phase 4: Quality & Maintenance (Week 7-8, ~9 days)

### Goal
Improve code quality, testing, and maintainability

### Tasks

#### 10. Increase Test Coverage (4 days)
**Why**: Only ~30% test coverage. Need tests for critical components.

**What to Do**:
```python
# dev/tests/test_ryx_brain.py - NEW FILE
import pytest
from core.ryx_brain import RyxBrain, Intent, Plan
from core.ollama_client import OllamaClient

@pytest.fixture
def brain():
    ollama = OllamaClient(base_url="http://localhost:11434")
    return RyxBrain(ollama)

def test_intent_classification(brain):
    """Test intent classification"""
    # Open file intent
    plan = brain.understand("open config.yaml")
    assert plan.intent == Intent.OPEN_FILE
    assert "config.yaml" in plan.target
    
    # Search web intent
    plan = brain.understand("search for python tutorials")
    assert plan.intent == Intent.SEARCH_WEB
    assert "python tutorials" in plan.target

def test_context_reference(brain):
    """Test context reference handling"""
    # First query creates context
    plan1 = brain.understand("find theme.py")
    brain.execute(plan1)
    
    # Second query references context
    plan2 = brain.understand("open that")
    assert plan2.intent == Intent.OPEN_FILE
    assert "theme.py" in plan2.target
```

**Files to Create**:
- `dev/tests/test_ryx_brain.py`
- `dev/tests/test_session_loop.py`
- `dev/tests/test_model_router.py`
- `dev/tests/test_ollama_client.py`
- `dev/tests/test_phases.py`
- `dev/tests/test_git_safety.py`

**Success Criteria**:
- [ ] Test coverage >60%
- [ ] All critical paths tested
- [ ] Integration tests for full workflows
- [ ] Tests pass consistently

---

#### 11. Add Linting & CI (2 days)
**Why**: Need code quality enforcement and automated testing.

**What to Do**:
```toml
# pyproject.toml - Add linter config
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

**GitHub Actions**:
```yaml
# .github/workflows/ci.yml - NEW FILE
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov ruff mypy
      - run: ruff check .
      - run: mypy core/
      - run: pytest --cov=core --cov-report=term-missing
```

**Files to Create**:
- `.github/workflows/ci.yml`: GitHub Actions CI
- `Makefile`: Add lint, format, typecheck targets

**Files to Modify**:
- `pyproject.toml`: Add ruff and mypy config

**Success Criteria**:
- [ ] CI runs on every push
- [ ] Linting enforced
- [ ] Type checking enforced
- [ ] Tests must pass to merge

---

#### 12. Refactor God Classes (3 days)
**Why**: `ryx_brain.py` is 1800+ lines. Need to split into modules.

**What to Do**:
```
core/
├── brain/
│   ├── __init__.py
│   ├── ryx_brain.py        # Main orchestration (400 lines)
│   ├── intent_classifier.py  # Intent detection (200 lines)
│   ├── context_manager.py    # Context tracking (300 lines)
│   ├── plan_executor.py      # Plan execution (400 lines)
│   └── knowledge_base.py     # Pre-loaded knowledge (300 lines)
```

**Extract Intent Classifier**:
```python
# core/brain/intent_classifier.py - NEW FILE
class IntentClassifier:
    """Classify user intent from natural language"""
    
    def classify(self, user_input: str, context: Context) -> Intent:
        """Determine what the user wants to do"""
        # Rule-based classification with LLM fallback
        
        # Website patterns
        if self._is_website(user_input):
            return Intent.OPEN_URL
        
        # File patterns
        if self._is_file_request(user_input):
            return Intent.OPEN_FILE
        
        # Search patterns
        if self._is_search_request(user_input):
            return Intent.SEARCH_WEB
        
        # Code task patterns
        if self._is_code_task(user_input):
            return Intent.CODE_TASK
        
        # Fallback to LLM classification
        return self._classify_with_llm(user_input, context)
```

**Files to Create**:
- `core/brain/intent_classifier.py`
- `core/brain/context_manager.py`
- `core/brain/plan_executor.py`
- `core/brain/knowledge_base.py`

**Files to Modify**:
- `core/ryx_brain.py`: Reduce to ~400 lines, use new modules

**Success Criteria**:
- [ ] `ryx_brain.py` under 500 lines
- [ ] Clear module boundaries
- [ ] No circular dependencies
- [ ] Easier to test and maintain

---

## Quick Wins (Can Do Anytime, <1 day each)

### 1. Fix UI Footer Position (30 min)
```python
# core/cli_ui.py
def header():
    """Print header ONCE at session start"""
    # ... existing header code ...

# core/session_loop.py
def run(self):
    self.cli.header()  # Only called once
    
    while self.running:
        user_input = self.cli.prompt()
        self._process(user_input)
        # NO footer here
```

### 2. Add `--dry-run` Flag (1 hour)
```python
# ryx_main.py
def cli_main():
    args = sys.argv[1:]
    dry_run = '--dry-run' in args
    
    if dry_run:
        print("[DRY RUN MODE] No changes will be made")
        os.environ['RYX_DRY_RUN'] = '1'
```

### 3. Structured Logging (2 hours)
```python
# core/logging_config.py
import json
import logging
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'component': record.name,
            'message': record.getMessage(),
            'data': getattr(record, 'data', {})
        })

# Use JSON logs for machine parsing
session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
json_handler = logging.FileHandler(f'logs/session_{session_id}.json')
json_handler.setFormatter(JSONFormatter())
```

### 4. Profile Support (2 hours)
```python
# configs/profiles.json - NEW FILE
{
  "profiles": {
    "conservative": {
      "safety_mode": "strict",
      "auto_commit": true,
      "require_approval": true
    },
    "aggressive": {
      "safety_mode": "loose",
      "auto_commit": false,
      "require_approval": false
    }
  },
  "active": "conservative"
}

# core/config.py - Load profiles
def load_profile(name: str) -> ProfileConfig:
    with open('configs/profiles.json') as f:
        data = json.load(f)
    return ProfileConfig(**data['profiles'][name])
```

### 5. Consolidate Package Structure (3 hours)
```bash
# Choose ONE package root: core/
# Move everything there
mv ryx_core/* core/
mv ryx_pkg/core/* core/
rm -rf ryx_core ryx_pkg ryx

# Update imports everywhere
find . -name "*.py" -exec sed -i 's/from ryx_core/from core/g' {} \;
find . -name "*.py" -exec sed -i 's/from ryx_pkg/from core/g' {} \;
```

---

## Implementation Schedule

### Sprint 1 (Week 1-2): Critical Foundation
```
Day 1-3:   Integrate Supervisor Agent
Day 4-6:   Activate Phase System
Day 7-8:   Add Test Execution Tools
```

### Sprint 2 (Week 3-4): Error Recovery
```
Day 9-12:  Implement Rescue Mode
Day 13-15: Add Diff-Based Editing
Day 16-17: Improve Git Integration
```

### Sprint 3 (Week 5-6): UX & Polish
```
Day 18-20: Fix UI Issues
Day 21-23: Add Repo Explorer
Day 24-25: Add Planning Documentation
```

### Sprint 4 (Week 7-8): Quality
```
Day 26-29: Increase Test Coverage
Day 30-31: Add Linting & CI
Day 32-34: Refactor God Classes
```

---

## Success Metrics

### After Phase 1 (Week 2):
- [ ] Supervisor agent working
- [ ] Phase system activated
- [ ] Tests can run in VERIFY phase
- **Target Score**: 70/150 (47%)

### After Phase 2 (Week 4):
- [ ] Self-healing works
- [ ] Diff-based editing works
- [ ] Git integration safe
- **Target Score**: 85/150 (57%)

### After Phase 3 (Week 6):
- [ ] UI clean and polished
- [ ] Repo explorer working
- [ ] Plans documented
- **Target Score**: 100/150 (67%)

### After Phase 4 (Week 8):
- [ ] Test coverage >60%
- [ ] CI enforces quality
- [ ] Code well-structured
- **Target Score**: 120/150 (80%)

---

## Risk Mitigation

### Risk: Breaking Existing Functionality
**Mitigation**:
- Add tests BEFORE refactoring
- Make changes incrementally
- Keep old code until new code proven

### Risk: Supervisor/Operator Integration Too Complex
**Mitigation**:
- Start with simple delegation
- Add complexity gradually
- Keep fallback to monolithic mode

### Risk: Timeline Too Optimistic
**Mitigation**:
- Focus on P0 items first
- P1-P3 can slip if needed
- Quick wins keep momentum

---

## Conclusion

**Current State**: 58/150 (39%)  
**Target State**: 120/150 (80%)  
**Time**: 8 weeks  
**Effort**: ~35 days of focused work

**Key Success Factors**:
1. Do Phase 1 first - it unlocks everything else
2. Test as you go - don't accumulate technical debt
3. Keep changes minimal - surgical edits only
4. Document as you build - future you will thank you

**Ready to Start**: Begin with integrating the supervisor agent!

---

**Created**: 2025-12-03  
**Author**: GitHub Copilot Agent  
**Based On**: RYX_ARCHITECTURE_EVALUATION.md
