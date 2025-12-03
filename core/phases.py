"""
Ryx AI - Agent Phases

Implements a state machine for agent execution phases.
Inspired by Claude Code's explore → plan → apply → verify workflow.

Each phase has:
- Specific purpose
- Dedicated prompt template
- Clear inputs/outputs
- Transition logic

Now integrated with:
- ryx_pkg/repo: Automatic file discovery (RepoExplorer)
- ryx_pkg/git: Git integration (GitManager, GitSafety)
- ryx_pkg/editing: Diff-based editing (DiffEditor)
- ryx_pkg/testing: Test execution (TestRunner)
- core/memory: Experience-based learning
- core/healing: Self-healing on exceptions
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

# Import new Aider-based modules
try:
    from ryx_pkg.repo import RepoExplorer
    from ryx_pkg.git import GitManager, GitSafety
    from ryx_pkg.editing import DiffEditor, SearchReplace
    from ryx_pkg.testing import TestRunner, detect_framework
    AIDER_MODULES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Aider-based modules not available: {e}")
    AIDER_MODULES_AVAILABLE = False

# Import P1 modules
try:
    from core.hallucination_detector import HallucinationDetector, detect_hallucinations
    from core.error_classifier import ErrorClassifier, ErrorRecoveryLoop, ErrorType
    from core.lint_runner import LintRunner, lint_files
    from core.manifest import ManifestLoader, load_manifest
    from core.history_manager import HistoryManager, ContextManager, Message, Role
    P1_MODULES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"P1 modules not available: {e}")
    P1_MODULES_AVAILABLE = False

# Import RSI modules (experience memory, healing)
try:
    from core.memory import get_memory, ExperienceType
    from core.healing import ExceptionHandler
    RSI_MODULES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"RSI modules not available: {e}")
    RSI_MODULES_AVAILABLE = False


class Phase(Enum):
    """Agent execution phases"""
    IDLE = "idle"           # Waiting for task
    EXPLORE = "explore"     # Understanding codebase/context
    PLAN = "plan"           # Creating action plan
    APPLY = "apply"         # Executing changes
    VERIFY = "verify"       # Testing/validating results
    COMPLETE = "complete"   # Task finished
    ERROR = "error"         # Unrecoverable error


@dataclass
class PlanStep:
    """A single step in an execution plan"""
    id: int
    description: str
    file_path: Optional[str] = None
    action: str = "modify"  # modify, create, delete, run
    details: str = ""
    completed: bool = False
    result: str = ""


@dataclass
class ExecutionPlan:
    """Complete plan for a task"""
    task: str
    steps: List[PlanStep] = field(default_factory=list)
    files_to_read: List[str] = field(default_factory=list)
    files_to_modify: List[str] = field(default_factory=list)
    files_to_create: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    approved: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_step(self, description: str, file_path: str = None, action: str = "modify") -> PlanStep:
        step = PlanStep(
            id=len(self.steps) + 1,
            description=description,
            file_path=file_path,
            action=action
        )
        self.steps.append(step)
        return step
    
    def get_next_step(self) -> Optional[PlanStep]:
        for step in self.steps:
            if not step.completed:
                return step
        return None
    
    def mark_step_complete(self, step_id: int, result: str = ""):
        for step in self.steps:
            if step.id == step_id:
                step.completed = True
                step.result = result
                break
    
    def is_complete(self) -> bool:
        return all(step.completed for step in self.steps)
    
    def to_text(self) -> str:
        """Convert plan to readable text"""
        lines = [f"Plan for: {self.task}", ""]
        
        if self.files_to_read:
            lines.append("Files to read:")
            for f in self.files_to_read:
                lines.append(f"  - {f}")
            lines.append("")
        
        if self.files_to_modify:
            lines.append("Files to modify:")
            for f in self.files_to_modify:
                lines.append(f"  - {f}")
            lines.append("")
        
        if self.files_to_create:
            lines.append("Files to create:")
            for f in self.files_to_create:
                lines.append(f"  - {f}")
            lines.append("")
        
        lines.append("Steps:")
        for step in self.steps:
            status = "✓" if step.completed else "○"
            file_info = f" ({step.file_path})" if step.file_path else ""
            lines.append(f"  {status} {step.id}. {step.description}{file_info}")
        
        if self.risks:
            lines.append("")
            lines.append("Risks:")
            for risk in self.risks:
                lines.append(f"  ⚠ {risk}")
        
        return "\n".join(lines)


@dataclass
class Change:
    """A single change made during execution"""
    file_path: str
    action: str  # modified, created, deleted
    diff: str = ""
    backup_path: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    reverted: bool = False


@dataclass
class AgentState:
    """
    Complete state of the agent during task execution.
    Tracks phase, context, plan, and changes.
    """
    phase: Phase = Phase.IDLE
    task: str = ""
    
    # Context from exploration
    context_files: List[str] = field(default_factory=list)
    context_summary: str = ""
    relevant_files: List[str] = field(default_factory=list)
    
    # Execution plan
    plan: Optional[ExecutionPlan] = None
    current_step: int = 0
    
    # Changes made
    changes: List[Change] = field(default_factory=list)
    checkpoint_ids: List[str] = field(default_factory=list)
    
    # Verification
    test_output: str = ""
    lint_output: str = ""
    verification_passed: bool = False
    
    # Error handling
    errors: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    
    # Timestamps
    started_at: str = ""
    completed_at: str = ""
    
    def start_task(self, task: str):
        """Initialize state for a new task"""
        self.phase = Phase.EXPLORE
        self.task = task
        self.context_files = []
        self.context_summary = ""
        self.relevant_files = []
        self.plan = None
        self.current_step = 0
        self.changes = []
        self.errors = []
        self.retry_count = 0
        self.started_at = datetime.now().isoformat()
        self.completed_at = ""
    
    def transition_to(self, phase: Phase):
        """Transition to a new phase with validation"""
        valid_transitions = {
            Phase.IDLE: [Phase.EXPLORE],
            Phase.EXPLORE: [Phase.PLAN, Phase.ERROR],
            Phase.PLAN: [Phase.APPLY, Phase.EXPLORE, Phase.ERROR],
            Phase.APPLY: [Phase.VERIFY, Phase.PLAN, Phase.ERROR],
            Phase.VERIFY: [Phase.COMPLETE, Phase.PLAN, Phase.ERROR],
            Phase.COMPLETE: [Phase.IDLE],
            Phase.ERROR: [Phase.IDLE, Phase.PLAN],
        }
        
        if phase in valid_transitions.get(self.phase, []):
            self.phase = phase
            if phase == Phase.COMPLETE:
                self.completed_at = datetime.now().isoformat()
            return True
        return False
    
    def add_error(self, error: str):
        """Add an error and potentially transition to error phase"""
        self.errors.append(error)
        self.retry_count += 1
        
        if self.retry_count >= self.max_retries:
            self.transition_to(Phase.ERROR)
    
    def add_change(self, file_path: str, action: str, diff: str = "", backup: str = ""):
        """Record a change"""
        self.changes.append(Change(
            file_path=file_path,
            action=action,
            diff=diff,
            backup_path=backup
        ))
    
    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries
    
    def get_status(self) -> str:
        """Get human-readable status"""
        status_lines = [
            f"Phase: {self.phase.value}",
            f"Task: {self.task[:50]}..." if len(self.task) > 50 else f"Task: {self.task}",
        ]
        
        if self.plan:
            completed = sum(1 for s in self.plan.steps if s.completed)
            total = len(self.plan.steps)
            status_lines.append(f"Progress: {completed}/{total} steps")
        
        if self.changes:
            status_lines.append(f"Changes: {len(self.changes)} files modified")
        
        if self.errors:
            status_lines.append(f"Errors: {len(self.errors)}")
        
        return "\n".join(status_lines)


# ─────────────────────────────────────────────────────────────
# Phase-Specific Prompts
# ─────────────────────────────────────────────────────────────

PROMPTS = {
    Phase.EXPLORE: """You are exploring a codebase to understand its structure.
Task: {task}

Repository structure:
{repo_tree}

Available files by relevance:
{relevant_files}

Instructions:
1. Identify which files are most relevant to this task
2. List what you need to understand before making changes
3. Note any dependencies or related files

Output as JSON:
{{
    "files_to_read": ["path1", "path2"],
    "understanding": "what you understand so far",
    "questions": ["things you need to clarify"],
    "ready_to_plan": true/false
}}""",

    Phase.PLAN: """You are creating a plan for: {task}

Files you've read:
{file_contents}

Instructions:
1. Break down the task into specific steps
2. List exactly which files need changes
3. Describe each change briefly
4. Identify any risks
5. DO NOT write any code yet

Output as JSON:
{{
    "steps": [
        {{"description": "what to do", "file": "path or null", "action": "modify/create/delete/run"}}
    ],
    "files_to_modify": ["paths"],
    "files_to_create": ["paths"],
    "risks": ["potential issues"],
    "confidence": 0.0-1.0
}}""",

    Phase.APPLY: """You are implementing step {step_num}: {step_description}

Target file: {file_path}
Current content:
```
{file_content}
```

Instructions:
1. Generate ONLY a unified diff for this change
2. Change only what's necessary for this step
3. Preserve existing code style
4. Add comments only if the change is complex

Output the diff only, no explanation. Format:
```diff
--- a/{file_path}
+++ b/{file_path}
@@ -line,count +line,count @@
 context
-removed line
+added line
 context
```""",

    Phase.VERIFY: """You just made changes. Critically review them as if you're a senior code reviewer.

Changes made:
{changes_summary}

Test output (if any):
{test_output}

Lint output (if any):
{lint_output}

SELF-CRITIQUE CHECKLIST:
1. Does the change actually solve the original task?
2. Are there any bugs, edge cases, or security issues?
3. Did we accidentally break existing functionality?
4. Is the code clean and follows best practices?
5. Are there any obvious improvements we should make?

Be CRITICAL. If something looks wrong, flag it.

Output as JSON:
{{
    "status": "pass/fail/warning",
    "issues": ["list of problems found - be specific"],
    "suggestions": ["concrete improvements to make"],
    "confidence": 0.0-1.0,
    "should_revert": true/false,
    "ready_to_complete": true/false
}}""",
}


def get_phase_prompt(phase: Phase, **kwargs) -> str:
    """Get the prompt template for a phase with variables filled in"""
    template = PROMPTS.get(phase, "")
    try:
        return template.format(**kwargs)
    except KeyError as e:
        return f"Missing variable in prompt: {e}"


# ─────────────────────────────────────────────────────────────
# Phase Executor
# ─────────────────────────────────────────────────────────────

class PhaseExecutor:
    """
    Executes agent phases with proper state management.
    Uses LLM for planning and agent tools for execution.
    Uses Rich UI for Claude CLI-style output.
    
    Now integrated with:
    - RepoExplorer for automatic file discovery
    - GitManager for commit/undo
    - DiffEditor for safe editing
    - TestRunner for verification
    """
    
    def __init__(self, brain, ui=None, working_dir=None):
        self.brain = brain
        # Support both old printer and new ui parameter
        if ui is None:
            from core.rich_ui import get_ui
            self.ui = get_ui()
        else:
            self.ui = ui
        self.state = AgentState()
        self._tools = None
        
        # Track the working directory where ryx was started
        # This ensures files are created in the right place
        self.working_dir = working_dir or os.getcwd()
        
        # Initialize Aider-based modules
        self._init_aider_modules()
    
    def _init_aider_modules(self):
        """Initialize the Aider-based infrastructure modules"""
        if not AIDER_MODULES_AVAILABLE:
            self.repo_explorer = None
            self.git_manager = None
            self.git_safety = None
            self.diff_editor = None
            self.test_runner = None
            return
        
        try:
            self.repo_explorer = RepoExplorer(verbose=False)
            self.git_manager = GitManager()
            self.git_safety = GitSafety(self.git_manager)
            self.diff_editor = DiffEditor(create_backups=True)
            self.test_runner = TestRunner()
            logger.debug("Aider-based modules initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Aider modules: {e}")
            self.repo_explorer = None
            self.git_manager = None
            self.git_safety = None
            self.diff_editor = None
            self.test_runner = None
    
    @property
    def tools(self):
        if self._tools is None:
            from core.agent_tools import get_agent_tools
            self._tools = get_agent_tools()
        return self._tools
    
    def start(self, task: str):
        """Start a new task"""
        self.state.start_task(task)
        self.ui.task_start("Starting task", task[:60])
        
        # Check for similar past experiences
        self._check_past_experiences(task)
    
    def _check_past_experiences(self, task: str):
        """Check for similar past experiences and use insights"""
        if not RSI_MODULES_AVAILABLE:
            return
        
        try:
            memory = get_memory()
            
            # Find similar experiences
            matches = memory.find_similar(task, limit=3, category="code_task")
            
            if matches:
                # Log what we found
                for match in matches:
                    if match.similarity > 0.3:
                        exp = match.experience
                        if exp.experience_type == ExperienceType.SUCCESS:
                            logger.info(f"Found similar success: {exp.task_description[:50]}")
                            self.ui.substep(f"💡 Similar task succeeded before")
                        elif exp.experience_type == ExperienceType.FAILURE:
                            logger.info(f"Found similar failure: {exp.error_if_any}")
                            self.ui.warn(f"⚠️ Similar task failed: {exp.error_if_any[:50]}...")
        except Exception as e:
            logger.warning(f"Failed to check experiences: {e}")
    
    def execute_phase(self) -> bool:
        """Execute the current phase and transition to next"""
        phase = self.state.phase
        
        if phase == Phase.EXPLORE:
            return self._execute_explore()
        elif phase == Phase.PLAN:
            return self._execute_plan()
        elif phase == Phase.APPLY:
            return self._execute_apply()
        elif phase == Phase.VERIFY:
            return self._execute_verify()
        elif phase == Phase.COMPLETE:
            return self._execute_complete()
        elif phase == Phase.ERROR:
            return self._handle_error()
        
        return False
    
    def _execute_explore(self) -> bool:
        """Explore phase: understand the codebase using RepoExplorer"""
        self.ui.phase_start("EXPLORE", "Scanning codebase...")
        
        # Use new RepoExplorer if available (Aider-based)
        if self.repo_explorer:
            try:
                # Scan repository
                stats = self.repo_explorer.scan()
                self.ui.substep(f"Found {stats.total_files} files")
                
                # Find relevant files for the task
                relevant = self.repo_explorer.find_for_task(self.state.task, max_files=15)
                self.state.relevant_files = relevant
                
                # Get context for LLM
                context = self.repo_explorer.get_context_for_llm(relevant, include_content=True)
                self.state.context_summary = context
                
                self.ui.phase_done("EXPLORE", f"Found {len(relevant)} relevant files")
                
                # Show top files
                if relevant[:3]:
                    top = [f.split('/')[-1] for f in relevant[:3]]
                    self.ui.substep(f"Top files: {', '.join(top)}")
                
                # Read the most relevant files to build context
                self.state.context_files = []
                for path in relevant[:5]:
                    result = self.tools.execute("read_file", path=path)
                    if result.success:
                        self.state.context_files.append({
                            "path": path,
                            "content": result.output[:2000]
                        })
                
                self.state.transition_to(Phase.PLAN)
                return True
                
            except Exception as e:
                logger.warning(f"RepoExplorer failed: {e}, using fallback")
        
        # Fallback: Try semantic search first if available, fall back to keyword
        try:
            from core.embeddings import get_semantic_search
            search = get_semantic_search()
            results = search.search(self.state.task, limit=15)
            self.state.relevant_files = [path for path, _ in results]
            self.ui.phase_done("EXPLORE", f"Found {len(results)} files (semantic)")
        except Exception:
            # Fallback to keyword search
            from core.repo_explorer import get_explorer
            explorer = get_explorer()
            explorer.scan()
            relevant = explorer.find_relevant(self.state.task, limit=15)
            self.state.relevant_files = [f.path for f in relevant]
            self.ui.phase_done("EXPLORE", f"Found {len(relevant)} files (keyword)")
        
        # Show top files (reduced noise)
        if self.state.relevant_files[:3]:
            self.ui.substep(f"Top files: {', '.join([f.split('/')[-1] for f in self.state.relevant_files[:3]])}")
        
        # Read the most relevant files to build context (silently)
        self.state.context_files = []
        for path in self.state.relevant_files[:3]:
            result = self.tools.execute("read_file", path=path)
            if result.success:
                self.state.context_files.append({
                    "path": path,
                    "content": result.output[:2000]  # Limit size
                })
        
        self.state.transition_to(Phase.PLAN)
        return True
    
    def _execute_plan(self) -> bool:
        """Plan phase: create execution plan using LLM"""
        self.ui.phase_start("PLAN", "Creating action plan...")
        
        # Build context for LLM
        file_contents = ""
        for fc in self.state.context_files[:3]:
            file_contents += f"\n--- {fc['path']} ---\n{fc['content'][:1500]}\n"
        
        # Get prompt
        prompt = get_phase_prompt(
            Phase.PLAN,
            task=self.state.task,
            file_contents=file_contents
        )
        
        # Get the CODE model for planning
        from core.model_router import get_router, ModelRole
        router = get_router()
        model_config = router.get_model_by_role(ModelRole.CODE)
        model_name = model_config.name
        
        # Call LLM if brain is available
        if self.brain and hasattr(self.brain, 'llm'):
            self.ui.phase_start("PLAN", f"Asking {model_name}...")
            
            response = self.brain.llm.generate(
                prompt=prompt,
                model=model_name,
                system="You are a code planning assistant. Output valid JSON only.",
                max_tokens=1000,
                temperature=0.3
            )
            
            if response.response:
                # Try to parse JSON from response
                plan_data = self._parse_json(response.response)
                if plan_data:
                    self._build_plan_from_json(plan_data)
                    self.ui.phase_done("PLAN", f"{len(self.state.plan.steps)} steps")
                else:
                    self._build_simple_plan()
                    self.ui.phase_done("PLAN", "simple plan")
            else:
                self._build_simple_plan()
                self.ui.phase_done("PLAN", "fallback", success=False)
        else:
            self._build_simple_plan()
        
        # Show plan and get user approval (P1.6)
        if self.state.plan and self.state.plan.steps:
            # Convert plan steps to format expected by UI
            plan_steps = [
                {
                    "action": step.action,
                    "file_path": step.file_path or "",
                    "description": step.description,
                    "details": step.details
                }
                for step in self.state.plan.steps
            ]
            
            # Check if UI supports plan approval
            if hasattr(self.ui, 'plan_approval_prompt'):
                choice = self.ui.plan_approval_prompt(plan_steps, self.state.task)
                
                if choice == 'n':
                    self.ui.warn("Plan cancelled by user")
                    self.state.transition_to(Phase.ERROR)
                    return False
                
                elif choice == 'e':
                    # Interactive plan editing
                    if hasattr(self.ui, 'edit_plan_interactive'):
                        edited_steps = self.ui.edit_plan_interactive(plan_steps)
                        # Rebuild plan from edited steps
                        self.state.plan = ExecutionPlan(task=self.state.task)
                        for s in edited_steps:
                            self.state.plan.add_step(
                                description=s.get('description', ''),
                                file_path=s.get('file_path', s.get('file')),
                                action=s.get('action', 'modify')
                            )
                
                elif choice.startswith('s') and len(choice) > 1:
                    # Skip specific step
                    try:
                        skip_idx = int(choice[1:]) - 1
                        if 0 <= skip_idx < len(self.state.plan.steps):
                            self.state.plan.steps[skip_idx].completed = True
                            self.ui.substep(f"Skipped step {skip_idx + 1}")
                    except ValueError:
                        pass
                
                # 'y' or empty = approve
                self.state.plan.approved = True
            else:
                # Fallback: auto-approve
                self.ui.substep(f"Plan: {len(self.state.plan.steps)} steps")
                self.state.plan.approved = True
        
        # Optional: Create branch for task (P1.4)
        if self.git_manager and self.git_manager.is_repo:
            # Check if user wants a branch (could be a config option)
            # For now, only create branch for tasks with "branch" in command
            if "branch" in self.state.task.lower() or getattr(self, '_use_branch', False):
                branch_name = self._generate_branch_name(self.state.task)
                if self.git_manager.create_branch(branch_name):
                    self.ui.substep(f"Created branch: {branch_name}")
        
        self.state.transition_to(Phase.APPLY)
        return True
    
    def _generate_branch_name(self, task: str) -> str:
        """Generate a branch name from task description"""
        import re
        from datetime import datetime
        
        # Clean task text
        clean = re.sub(r'[^a-zA-Z0-9\s-]', '', task.lower())
        words = clean.split()[:4]
        slug = '-'.join(words) if words else 'task'
        timestamp = datetime.now().strftime('%m%d%H%M')
        
        return f"ryx/{slug}-{timestamp}"
    
    def _build_plan_from_json(self, data: dict):
        """Build execution plan from LLM JSON response"""
        self.state.plan = ExecutionPlan(task=self.state.task)
        
        # Extract steps
        steps = data.get('steps', [])
        for s in steps:
            if isinstance(s, dict):
                self.state.plan.add_step(
                    description=s.get('description', str(s)),
                    file_path=s.get('file'),
                    action=s.get('action', 'modify')
                )
            else:
                self.state.plan.add_step(description=str(s))
        
        # Extract file lists
        self.state.plan.files_to_modify = data.get('files_to_modify', [])
        self.state.plan.files_to_create = data.get('files_to_create', [])
        self.state.plan.risks = data.get('risks', [])
    
    def _build_simple_plan(self):
        """Build a simple plan when LLM fails - tries to infer file name from task"""
        import re
        
        self.state.plan = ExecutionPlan(task=self.state.task)
        
        task = self.state.task.lower()
        
        # Try to extract filename from task
        # e.g. "create login.py" -> "login.py"
        file_match = re.search(r'(\w+\.(?:py|js|ts|go|rs|java|c|cpp|h|sh|yaml|json|md))', task)
        
        if file_match:
            filename = file_match.group(1)
            self.state.plan.files_to_create = [filename]
            self.state.plan.add_step(
                description=f"Create {filename} with requested functionality",
                file_path=filename,
                action="create"
            )
        else:
            # Try to infer from keywords
            if any(word in task for word in ['login', 'auth', 'authentication']):
                self.state.plan.files_to_create = ['auth.py']
                self.state.plan.add_step(
                    description="Create authentication module",
                    file_path="auth.py",
                    action="create"
                )
            elif any(word in task for word in ['test', 'testing']):
                self.state.plan.files_to_create = ['test_module.py']
                self.state.plan.add_step(
                    description="Create test module",
                    file_path="test_module.py",
                    action="create"
                )
            elif any(word in task for word in ['api', 'endpoint', 'rest']):
                self.state.plan.files_to_create = ['api.py']
                self.state.plan.add_step(
                    description="Create API module",
                    file_path="api.py",
                    action="create"
                )
            else:
                # Generic fallback - use 'module.py'
                name = re.sub(r'[^a-z0-9]+', '_', task.split()[0] if task else 'module')[:20]
                filename = f"{name}.py"
                self.state.plan.files_to_create = [filename]
                self.state.plan.add_step(
                    description=f"Create {filename} for: {self.state.task[:50]}",
                    file_path=filename,
                    action="create"
                )
    
    def _parse_json(self, text: str) -> Optional[dict]:
        """Try to parse JSON from LLM response"""
        import json
        
        # Try direct parse
        try:
            return json.loads(text)
        except:
            pass
        
        # Try to find JSON in text
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        
        return None
    
    def _execute_apply(self) -> bool:
        """Apply phase: execute changes - ACTUALLY WRITE FILES"""
        if not self.state.plan:
            self.state.add_error("No plan to execute")
            return False
        
        step = self.state.plan.get_next_step()
        if step:
            self.ui.phase_start("APPLY", f"Step {step.id}: {step.description[:30]}...")
            
            # Determine action type
            action = (step.action.lower() if hasattr(step, 'action') and step.action else 'create').lower()
            desc_lower = step.description.lower() if step.description else ''
            
            # Check if this step should create/modify code
            should_generate = (
                step.file_path or 
                action in ['create', 'write', 'generate', 'implement', 'add', 'modify'] or
                any(word in desc_lower for word in ['create', 'implement', 'add', 'write', 'generate', 'build'])
            )
            
            if should_generate:
                # If no file_path specified, try to infer from description
                file_path = step.file_path
                if not file_path:
                    # Try to extract file path from description
                    import re
                    match = re.search(r'(\w+\.(?:py|js|ts|go|rs|java|c|cpp|h|sh|yaml|json|md))', step.description)
                    if match:
                        file_path = match.group(1)
                        step.file_path = file_path
                
                if file_path:
                    success = self._generate_code_for_step(step)
                    if success:
                        self.ui.phase_done("APPLY", f"✓ Created {step.file_path}")
                        # Track created file in brain context
                        if hasattr(self.brain, 'ctx'):
                            if not hasattr(self.brain.ctx, 'created_files'):
                                self.brain.ctx.created_files = []
                            self.brain.ctx.created_files.append(step.file_path)
                    else:
                        self.ui.phase_done("APPLY", f"✗ Failed {step.file_path}", success=False)
                else:
                    # No file path - just mark as analyzed
                    self.ui.phase_done("APPLY", f"○ {step.description[:40]}")
            else:
                self.ui.phase_done("APPLY", f"○ Step {step.id} analyzed")
            
            self.state.plan.mark_step_complete(step.id, "Completed")
        
        # Check if there are more steps
        next_step = self.state.plan.get_next_step()
        if next_step:
            # Continue applying
            return self._execute_apply()
        
        # All steps done, move to verify
        self.state.transition_to(Phase.VERIFY)
        return True
    
    def _generate_code_for_step(self, step) -> bool:
        """Actually generate code for a step using LLM and write to disk"""
        from core.model_router import get_router, ModelRole
        import os
        
        router = get_router()
        model_config = router.get_model_by_role(ModelRole.CODE)
        model_name = model_config.name
        
        # Build context from explored files
        context = ""
        if self.state.context_files:
            context = "Existing code context:\n"
            for cf in self.state.context_files[:2]:
                context += f"\n--- {cf['path']} ---\n{cf['content'][:800]}\n"
        
        # Detect language from file extension
        ext = os.path.splitext(step.file_path)[1] if step.file_path else '.py'
        lang_hints = {
            '.py': 'Python 3',
            '.js': 'JavaScript (ES6+)',
            '.ts': 'TypeScript',
            '.go': 'Go',
            '.rs': 'Rust',
            '.java': 'Java',
            '.sh': 'Bash',
            '.json': 'JSON (valid JSON only, no comments)',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.html': 'HTML5',
            '.css': 'CSS3',
            '.md': 'Markdown',
            '.toml': 'TOML',
            '.xml': 'XML',
        }
        lang = lang_hints.get(ext, 'appropriate language')
        
        prompt = f"""Task: {self.state.task}
Step: {step.description}
Target file: {step.file_path}
Language: {lang}

{context}

Generate COMPLETE, WORKING code for {step.file_path}.
Requirements:
- Include all necessary imports
- Add docstrings/comments for complex logic
- Follow {lang} best practices
- Make it production-ready

Output ONLY the code. No explanations, no markdown fences."""

        if self.brain and hasattr(self.brain, 'llm'):
            self.ui.step_start(f"Generating {step.file_path}")
            
            response = self.brain.llm.generate(
                prompt=prompt,
                model=model_name,
                system=f"You are a senior {lang} developer. Output only valid, complete code. No markdown, no explanations.",
                max_tokens=2000,
                temperature=0.3
            )
            
            if response.response:
                # Clean the response (remove markdown fences if present)
                code = response.response.strip()
                if code.startswith('```'):
                    lines = code.split('\n')
                    # Remove first line (```python) and last line (```)
                    if lines[-1].strip() == '```':
                        code = '\n'.join(lines[1:-1])
                    else:
                        code = '\n'.join(lines[1:])
                
                # Validate we got actual content
                # JSON files can be very short (e.g., "[]" or "{}")
                min_length = 2 if ext == '.json' else 10
                if len(code) < min_length:
                    self.state.add_error(f"Generated content too short for {step.file_path}")
                    return False
                
                # For JSON files, validate it's valid JSON
                if ext == '.json':
                    import json
                    try:
                        json.loads(code)
                    except json.JSONDecodeError as e:
                        self.state.add_error(f"Invalid JSON generated for {step.file_path}: {e}")
                        return False
                
                # Create the file
                try:
                    file_path = step.file_path
                    # Handle relative paths - use executor's working_dir, not current dir
                    if not os.path.isabs(file_path):
                        file_path = os.path.join(self.working_dir, file_path)
                    
                    # Check if file exists for diff
                    old_content = ""
                    if os.path.exists(file_path):
                        try:
                            with open(file_path, 'r') as f:
                                old_content = f.read()
                        except:
                            pass
                    
                    # Show diff if modifying existing file
                    if old_content and hasattr(self.ui, 'show_diff'):
                        self.ui.show_diff(
                            os.path.basename(file_path), 
                            old_content.splitlines(), 
                            code.splitlines()
                        )
                    
                    # Create checkpoint
                    try:
                        from core.checkpoints import get_checkpoint_manager
                        cp_mgr = get_checkpoint_manager()
                        from core.checkpoints import ChangeType
                        
                        action_name = "Modify" if os.path.exists(file_path) else "Create"
                        cp_id = cp_mgr.start_checkpoint(
                            name=f"{action_name} {os.path.basename(file_path)}",
                            task_context=self.state.task
                        )
                        
                        if os.path.exists(file_path):
                            cp_mgr.track_modify(file_path, old_content, code)
                        else:
                            cp_mgr.track_create(file_path, code)
                            
                        cp_mgr.commit_checkpoint()
                        if hasattr(self.state, 'checkpoint_ids'):
                            self.state.checkpoint_ids.append(cp_id)
                    except Exception as e:
                        # self.ui.warn(f"Checkpoint failed: {e}")
                        pass
                    
                    # Create directory if needed
                    dir_path = os.path.dirname(file_path)
                    if dir_path:
                        os.makedirs(dir_path, exist_ok=True)
                    
                    # Write the file
                    with open(file_path, 'w') as f:
                        f.write(code)
                    
                    # Validate file was written correctly
                    if not os.path.exists(file_path):
                        self.state.add_error(f"File {file_path} was not created")
                        return False
                    
                    # Verify content matches what we wrote
                    with open(file_path, 'r') as f:
                        written_content = f.read()
                    if written_content != code:
                        self.state.add_error(f"File {file_path} content mismatch after write")
                        return False
                    
                    # Track the change
                    self.state.add_change(
                        file_path=file_path,
                        action="created",
                        diff=f"Created {file_path} ({len(code)} chars)"
                    )
                    
                    self.ui.step_done(f"Created {os.path.basename(file_path)}", f"{len(code.split(chr(10)))} lines")
                    return True
                    
                except Exception as e:
                    self.state.add_error(f"Failed to write {file_path}: {e}")
                    self.ui.step_fail(f"Write {step.file_path}", str(e))
                    return False
        
        return False
    
    def _detect_test_command(self) -> Optional[str]:
        """Detect test command based on project files - uses TestRunner if available"""
        # Use new TestRunner if available
        if self.test_runner:
            framework = detect_framework()
            if framework and framework.test_command:
                return ' '.join(framework.test_command)
        
        # Fallback detection
        if os.path.exists("package.json"):
            return "npm test"
        if os.path.exists("Cargo.toml"):
            return "cargo test"
        if os.path.exists("go.mod"):
            return "go test ./..."
        if os.path.exists("pytest.ini") or os.path.exists("pyproject.toml") or os.path.exists("requirements.txt"):
            return "python -m pytest"
        # Fallback for python
        if any(f.endswith(".py") for f in os.listdir(".")):
             return "python -m pytest"
        return None

    def _revert_changes(self):
        """Revert all changes made in this session"""
        if not hasattr(self.state, 'checkpoint_ids') or not self.state.checkpoint_ids:
            return
            
        from core.checkpoints import get_checkpoint_manager
        cp_mgr = get_checkpoint_manager()
        
        self.ui.warn(f"Reverting {len(self.state.checkpoint_ids)} changes...")
        
        # Rollback in reverse order
        for cp_id in reversed(self.state.checkpoint_ids):
            cp_mgr.rollback(cp_id)
            
        self.state.checkpoint_ids = []

    def _is_simple_task(self) -> bool:
        """
        Check if this is a simple task that doesn't need testing.
        
        Simple tasks:
        - Single file creation (create X.py)
        - Greeting/hello world scripts
        - Demo files with no dependencies
        - Configuration files
        """
        task = self.state.task.lower()
        
        # Simple task patterns
        simple_patterns = [
            # Single file creation
            'create a file', 'create file', 'erstelle eine datei', 'erstelle datei',
            'make a file', 'make file', 'new file',
            # Hello world / greetings
            'hello world', 'hallo welt', 'print hello', 'greet', 'greeting',
            # Simple demos
            'simple', 'basic', 'example', 'demo', 'test file',
            # Quick scripts
            'that prints', 'das printed', 'die ausgibt', 'ausgeben'
        ]
        
        for pattern in simple_patterns:
            if pattern in task:
                return True
        
        # Also check: only 1 file created, file is small, no imports of project code
        if len(self.state.changes) == 1:
            change = self.state.changes[0]
            if change.action in ['create', 'created']:
                # Read file content to check simplicity
                try:
                    with open(change.file_path, 'r') as f:
                        content = f.read()
                    
                    # Simple if under 50 lines and no complex imports
                    lines = content.count('\n')
                    has_complex_import = 'from core' in content or 'from ryx' in content
                    
                    if lines < 50 and not has_complex_import:
                        return True
                except:
                    pass
        
        return False

    def _execute_verify(self) -> bool:
        """Verify phase: check results using TestRunner, LintRunner, HallucinationDetector"""
        # Get the REASON model for verification
        from core.model_router import get_router, ModelRole
        router = get_router()
        model_config = router.get_model_by_role(ModelRole.REASON)
        
        self.ui.phase_start("VERIFY", f"Using {model_config.name}...")
        
        # Check if any changes were made
        has_changes = bool(self.state.changes)
        changed_files = [c.file_path for c in self.state.changes] if has_changes else []
        
        verification_issues = []
        
        # 1. Hallucination Detection (P1.2)
        if P1_MODULES_AVAILABLE and has_changes:
            self.ui.substep("Checking for hallucinated paths...")
            detector = HallucinationDetector()
            for change in self.state.changes:
                report = detector.check_paths([change.file_path])
                if report.has_issues:
                    verification_issues.append(f"Hallucination: {report.summary()}")
        
        # 2. Lint Check (P1.5)
        if P1_MODULES_AVAILABLE and has_changes and changed_files:
            self.ui.substep("Running linter...")
            try:
                lint_runner = LintRunner()
                lint_result = lint_runner.lint_files(changed_files)
                self.state.lint_output = lint_result.raw_output
                if lint_result.has_errors:
                    verification_issues.append(f"Lint errors: {lint_result.error_count}")
                    self.ui.substep(f"⚠️ {lint_result.summary()}")
                elif lint_result.has_warnings:
                    self.ui.substep(f"○ {lint_result.summary()}")
            except Exception as e:
                logger.debug(f"Lint check failed: {e}")
        
        # 3. Cross-File Consistency Check (NEW)
        if has_changes and len(changed_files) > 1:
            self.ui.substep("Checking cross-file consistency...")
            consistency_issues = self._check_cross_file_consistency(changed_files)
            if consistency_issues:
                for issue in consistency_issues:
                    verification_issues.append(f"Consistency: {issue}")
                    self.ui.substep(f"⚠️ {issue}")
        
        # 4. Test Execution - SKIP for simple tasks
        # Simple tasks: single file creation, greeting scripts, demos, etc.
        is_simple = self._is_simple_task()
        
        if has_changes and not is_simple:
            # Use new TestRunner if available
            if self.test_runner and self.test_runner.framework:
                self.ui.substep(f"Running tests ({self.test_runner.framework})...")
                
                test_result = self.test_runner.run_for_files(changed_files)
                self.state.test_output = test_result.output
                
                if test_result.success:
                    self.ui.substep(f"✓ {test_result.summary}")
                else:
                    verification_issues.append(f"Tests failed: {test_result.summary}")
                    self.ui.substep(f"✗ {test_result.summary}")
                    
                    # Error classification for better recovery (P1.3)
                    if P1_MODULES_AVAILABLE:
                        classifier = ErrorClassifier()
                        error_ctx = classifier.classify_from_output(test_result.output)
                        if error_ctx.suggested_fix:
                            self.ui.substep(f"Suggestion: {error_ctx.suggested_fix}")
            else:
                # Fallback to command-based testing
                test_cmd = self._detect_test_command()
                if test_cmd:
                    self.ui.substep(f"Running tests ({test_cmd})...")
                    test_result = self.tools.execute("run_command", command=f"{test_cmd} 2>/dev/null || true", timeout=30)
                    if test_result.success:
                        self.state.test_output = test_result.output
                        if "failed" in test_result.output.lower() or "error" in test_result.output.lower():
                            verification_issues.append("Tests failed")
                        else:
                            self.ui.substep("✓ Tests passed")
                    else:
                        verification_issues.append("Test execution failed")
        
        # Determine final verification status
        if verification_issues:
            self.state.verification_passed = False
            self.ui.phase_done("VERIFY", f"Issues: {len(verification_issues)}", success=False)
            for issue in verification_issues:
                self.ui.warn(f"  - {issue}")
        else:
            self.state.verification_passed = True
            self.ui.phase_done("VERIFY", "All checks passed")
            
            # Auto-commit if git is available
            if self.git_manager and self.git_manager.is_repo and changed_files:
                commit_msg = f"ryx: {self.state.task[:50]}"
                commit_hash = self.git_manager.safe_commit(commit_msg, files=changed_files)
                if commit_hash:
                    self.ui.substep(f"Committed: {commit_hash}")
        
        # Handle verification result
        if self.state.verification_passed:
            self.state.transition_to(Phase.COMPLETE)
        else:
            self.ui.warn("Verification failed")
            
            # Store verification issues for the retry
            if verification_issues and not hasattr(self.state, 'last_verification_issues'):
                self.state.last_verification_issues = verification_issues
            
            if self.state.can_retry():
                # Determine if we should rollback or just fix
                # For consistency issues (ID mismatches), don't rollback - just fix in place
                is_consistency_issue = any('Consistency' in str(i) for i in verification_issues)
                is_minor_fix = all('Consistency' in str(i) or 'mismatch' in str(i).lower() for i in verification_issues)
                
                if is_minor_fix:
                    # Don't rollback - just generate fix plan
                    self.ui.warn("Minor issues detected - fixing in place...")
                else:
                    self.ui.warn("Rolling back changes to retry...")
                    self._revert_changes()
                
                # Augment the task with specific fix instructions
                if verification_issues:
                    fix_hints = self._generate_fix_hints(verification_issues)
                    if fix_hints:
                        # Prepend fix hints to the original task
                        self.state.task = f"{fix_hints}\n\nOriginal task: {self.state.task}"
                
                self.state.transition_to(Phase.PLAN)
            else:
                # P1.3.3: Supervisor Rescue on repeated failures
                if self._try_supervisor_rescue():
                    # Supervisor provided a new plan, retry
                    self.state.retry_count = 0  # Reset retries for new plan
                    self.state.transition_to(Phase.PLAN)
                else:
                    self.state.transition_to(Phase.ERROR)
        
        return True
    
    def _generate_fix_hints(self, issues: List[str]) -> str:
        """Generate specific fix hints from verification issues"""
        import re
        hints = []
        
        for issue in issues:
            if 'ID mismatch' in issue:
                # Extract the IDs from the message
                match = re.search(r"JS uses '([^']+)' but HTML has '([^']+)'", issue)
                if match:
                    js_id, html_id = match.groups()
                    hints.append(f"WICHTIG: Benutze '{html_id}' (nicht '{js_id}') in JavaScript getElementById()")
            elif 'Missing ID' in issue:
                match = re.search(r"JS references '([^']+)'", issue)
                if match:
                    missing_id = match.group(1)
                    hints.append(f"WICHTIG: HTML braucht ein Element mit id='{missing_id}'")
            elif 'Field mismatch' in issue:
                match = re.search(r"JS uses '([^']+)' but HTML has '([^']+)'", issue)
                if match:
                    js_field, html_field = match.groups()
                    hints.append(f"WICHTIG: Benutze '{html_field}' (nicht '{js_field}') in formData.get()")
        
        if hints:
            return "FIX DIESE FEHLER:\n" + "\n".join(f"- {h}" for h in hints)
        return ""
    
    def _try_supervisor_rescue(self) -> bool:
        """
        P1.3.3: Attempt supervisor rescue after max retries exhausted.
        
        Supervisor analyzes the failure and decides:
        - ADJUST_PLAN: Modify the plan and retry
        - CHANGE_AGENT: Try different approach
        - TAKEOVER: Give up with explanation
        
        Returns True if rescue succeeded and we should retry.
        """
        try:
            from core.agents.supervisor import SupervisorAgent
            from core.planning import Context
        except ImportError:
            logger.debug("Supervisor agent not available for rescue")
            return False
        
        if not self.brain or not hasattr(self.brain, 'llm'):
            return False
        
        self.ui.warn("Max retries exhausted - calling Supervisor for rescue...")
        
        try:
            # Create supervisor
            supervisor = SupervisorAgent(self.brain.llm)
            
            # Build context
            context = Context(
                cwd=os.getcwd(),
                language="de" if any(c in self.state.task for c in "äöüß") else "en",
                recent_commands=[],
                last_result=self.state.test_output or ""
            )
            
            # Get current plan as JSON
            plan_json = ""
            if self.state.plan:
                steps = [{"step": s.id, "action": s.action, "description": s.description} 
                         for s in self.state.plan.steps]
                plan_json = str(steps)
            
            # Create a simple plan object for rescue
            from core.planning import Plan, PlanStep as PlanningStep, AgentType, ModelSize
            rescue_plan = Plan(
                understanding=self.state.task,
                complexity=3,
                confidence=0.5,
                steps=[],
                agent_type=AgentType.CODE,
                model_size=ModelSize.MEDIUM,
                operator_prompt=self.state.task
            )
            
            # Call rescue
            action, adjusted_plan, direct_result = supervisor.rescue(
                query=self.state.task,
                plan=rescue_plan,
                errors=self.state.errors,
                attempts=self.state.retry_count,
                context=context
            )
            
            self.ui.substep(f"Supervisor decision: {action}")
            
            if action == "ADJUST_PLAN" and adjusted_plan:
                # Rebuild plan from supervisor's adjusted plan
                self.state.plan = ExecutionPlan(task=self.state.task)
                for step in adjusted_plan.steps:
                    self.state.plan.add_step(
                        description=step.description,
                        file_path=step.params.get('file') if step.params else None,
                        action=step.action
                    )
                self.ui.success("Supervisor provided adjusted plan")
                return True
            
            elif action == "CHANGE_AGENT":
                # Try simpler approach - just create a basic plan
                self.state.plan = ExecutionPlan(task=self.state.task)
                self.state.plan.add_step(
                    description="Simplified approach based on supervisor guidance",
                    action="modify"
                )
                return True
            
            elif action == "TAKEOVER" and direct_result:
                # Supervisor gave up but provided explanation
                self.ui.warn(f"Supervisor takeover: {direct_result}")
                return False
            
        except Exception as e:
            logger.warning(f"Supervisor rescue failed: {e}")
        
        return False
    
    def _execute_complete(self) -> bool:
        """Complete phase: finish up"""
        self.ui.success("Task completed successfully")
        self.state.transition_to(Phase.IDLE)
        return True
    
    def _handle_error(self) -> bool:
        """Handle error state"""
        error_msg = self.state.errors[-1] if self.state.errors else 'Unknown error'
        self.ui.error(f"Task failed: {error_msg}")
        return False
    
    def _generate_auto_fix_prompt(self, issues: List[str]) -> str:
        """
        Generate an automatic fix prompt based on detected issues.
        This enables autonomous self-healing without human intervention.
        """
        # Collect information about what went wrong
        issue_descriptions = []
        for issue in issues:
            issue_descriptions.append(f"- {issue}")
        
        # Get list of created/modified files
        changed_files = [c.file_path for c in self.state.changes] if self.state.changes else []
        
        # Check for specific issue types to give better guidance
        has_id_mismatch = any('ID mismatch' in i or 'Missing ID' in i for i in issues)
        has_field_mismatch = any('Field mismatch' in i for i in issues)
        
        specific_guidance = ""
        if has_id_mismatch:
            specific_guidance += """
CRITICAL: HTML IDs and JavaScript selectors MUST match exactly!
- If HTML has id="reservationForm", JS must use getElementById('reservationForm')
- If HTML has id="reservation-form", JS must use getElementById('reservation-form')
Pick ONE naming convention and use it consistently everywhere.
"""
        if has_field_mismatch:
            specific_guidance += """
CRITICAL: Form field names in HTML must match the names used in JavaScript!
- If HTML has name="people", JS must use formData.get('people')
- If HTML has name="persons", JS must use formData.get('persons')
"""
        
        prompt = f"""Fix the following issues in the code:

Issues detected:
{chr(10).join(issue_descriptions)}

{specific_guidance}

Files that were modified:
{chr(10).join(f'- {f}' for f in changed_files)}

IMPORTANT: 
1. Use CONSISTENT ID naming between HTML and JavaScript
2. All getElementById() calls in JS must reference IDs that exist in HTML
3. All form field names in HTML must match what JavaScript expects
4. Do NOT mix naming conventions like 'reservation-form' and 'reservationForm'
"""
        return prompt
    
    def _check_cross_file_consistency(self, changed_files: List[str]) -> List[str]:
        """
        Check for consistency issues between related files.
        
        Detects:
        - HTML id/class references that don't match JS selectors
        - Missing script/css file references
        - Broken import paths
        """
        issues = []
        
        # Separate files by type
        html_files = [f for f in changed_files if f.endswith('.html')]
        js_files = [f for f in changed_files if f.endswith('.js')]
        css_files = [f for f in changed_files if f.endswith('.css')]
        
        # Read file contents
        file_contents = {}
        for f in changed_files:
            try:
                if os.path.exists(f):
                    with open(f, 'r') as fp:
                        file_contents[f] = fp.read()
            except:
                pass
        
        # Check HTML->JS consistency
        import re
        
        # First, collect ALL IDs from ALL HTML files
        all_html_ids = set()
        for html_file in html_files:
            if html_file not in file_contents:
                continue
            html_content = file_contents[html_file]
            html_ids = set(re.findall(r'id=["\']([^"\']+)["\']', html_content))
            all_html_ids.update(html_ids)
        
        # Check each JS file's getElementById calls against ALL HTML IDs
        for js_file in js_files:
            if js_file not in file_contents:
                continue
            js_content = file_contents[js_file]
            
            # Find getElementById calls
            js_ids = set(re.findall(r'getElementById\(["\']([^"\']+)["\']\)', js_content))
            
            # Find querySelector calls with IDs
            js_ids.update(re.findall(r'querySelector\(["\']#([^"\']+)["\']\)', js_content))
            
            # Check for mismatches - only flag if ID doesn't exist in ANY HTML file
            for js_id in js_ids:
                if js_id not in all_html_ids:
                    # Check if it's a close match (typo)
                    close_matches = [h for h in all_html_ids if self._is_similar(js_id, h)]
                    if close_matches:
                        issues.append(
                            f"ID mismatch: JS uses '{js_id}' but HTML has '{close_matches[0]}'"
                        )
                    else:
                        issues.append(
                            f"Missing ID: JS references '{js_id}' but it's not in any HTML file"
                        )
        
        # Check each HTML file for script/CSS references
        for html_file in html_files:
            if html_file not in file_contents:
                continue
            html_content = file_contents[html_file]
            
            # Check for script references
            script_refs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html_content)
            for ref in script_refs:
                ref_path = os.path.join(os.path.dirname(html_file), ref)
                if not os.path.exists(ref_path) and ref not in [os.path.basename(f) for f in js_files]:
                    issues.append(f"Missing script: {ref} referenced in {os.path.basename(html_file)}")
            
            # Check for CSS references
            css_refs = re.findall(r'<link[^>]+href=["\']([^"\']+\.css)["\']', html_content)
            for ref in css_refs:
                ref_path = os.path.join(os.path.dirname(html_file), ref)
                if not os.path.exists(ref_path) and ref not in [os.path.basename(f) for f in css_files]:
                    issues.append(f"Missing CSS: {ref} referenced in {os.path.basename(html_file)}")
        
        # Check JS for form field references - collect all form field names from all HTML
        all_html_names = set()
        for html_file in html_files:
            if html_file not in file_contents:
                continue
            html_content = file_contents[html_file]
            html_names = set(re.findall(r'name=["\']([^"\']+)["\']', html_content))
            all_html_names.update(html_names)
        
        # Check JS FormData.get() calls against all HTML form fields
        for js_file in js_files:
            if js_file not in file_contents:
                continue
            js_content = file_contents[js_file]
            
            # Find FormData.get() calls
            form_fields = set(re.findall(r"\.get\(['\"]([^'\"]+)['\"]\)", js_content))
            
            for field in form_fields:
                if field not in all_html_names:
                    close_matches = [n for n in all_html_names if self._is_similar(field, n)]
                    if close_matches:
                        issues.append(
                            f"Field mismatch: JS uses '{field}' but HTML has '{close_matches[0]}'"
                        )
        
        return issues
    
    def _is_similar(self, s1: str, s2: str) -> bool:
        """Check if two strings are similar (for typo detection)"""
        # Simple similarity: same length, differ by 1-2 chars, or one is subset of other
        s1, s2 = s1.lower(), s2.lower()
        if s1 == s2:
            return True
        
        # Check if one contains the other (e.g., 'reservation-form' vs 'reservationForm')
        s1_clean = s1.replace('-', '').replace('_', '')
        s2_clean = s2.replace('-', '').replace('_', '')
        if s1_clean == s2_clean:
            return True
        
        # Check edit distance (allow up to 2 differences for short strings)
        if abs(len(s1) - len(s2)) <= 2:
            differences = sum(1 for a, b in zip(s1, s2) if a != b)
            differences += abs(len(s1) - len(s2))
            return differences <= 2
        
        return False
    
    def run_to_completion(self, autonomous_retries: int = 3) -> bool:
        """
        Run all phases until complete or error.
        
        With autonomous_retries > 0, will automatically attempt to fix issues
        without requiring human intervention.
        
        Now integrated with experience memory to learn from successes/failures.
        """
        auto_retry_count = 0
        original_task = self.state.task
        start_time = datetime.now()
        
        while self.state.phase not in [Phase.IDLE, Phase.ERROR, Phase.COMPLETE]:
            if not self.execute_phase():
                # Check if we can do an autonomous retry
                if auto_retry_count < autonomous_retries and self.state.phase == Phase.ERROR:
                    auto_retry_count += 1
                    self.ui.warn(f"Autonomous retry {auto_retry_count}/{autonomous_retries}...")
                    
                    # Generate fix prompt from errors
                    fix_prompt = self._generate_auto_fix_prompt(self.state.errors)
                    
                    # Reset state for retry
                    self.state.errors = []
                    self.state.phase = Phase.EXPLORE
                    self.state.task = fix_prompt
                    self.state.plan = None
                    
                    continue
                
                # Store failure experience
                self._store_experience(
                    original_task,
                    success=False,
                    errors=self.state.errors,
                    duration=(datetime.now() - start_time).total_seconds()
                )
                return False
        
        # Store success experience
        if self.state.phase == Phase.COMPLETE:
            self._store_experience(
                original_task,
                success=True,
                changes=self.state.changes,
                duration=(datetime.now() - start_time).total_seconds()
            )
        
        return self.state.phase == Phase.COMPLETE
    
    def _store_experience(
        self,
        task: str,
        success: bool,
        errors: List[str] = None,
        changes: List[str] = None,
        duration: float = 0.0
    ):
        """Store task experience for learning"""
        if not RSI_MODULES_AVAILABLE:
            return
        
        try:
            memory = get_memory()
            
            if success:
                memory.store_success(
                    task=task,
                    approach=f"Phase execution with {len(changes or [])} changes",
                    result="\n".join(changes or []),
                    category="code_task",
                    tags=["phase-executor", "autonomous"],
                    time=duration
                )
            else:
                memory.store_failure(
                    task=task,
                    error="\n".join(errors or ["Unknown error"]),
                    approach="Phase execution",
                    category="code_task",
                    tags=["phase-executor", "autonomous"],
                    time=duration
                )
        except Exception as e:
            logger.warning(f"Failed to store experience: {e}")
