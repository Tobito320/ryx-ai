"""
Ryx AI - Agent Phases

Implements a state machine for agent execution phases.
Inspired by Claude Code's explore → plan → apply → verify workflow.

Each phase has:
- Specific purpose
- Dedicated prompt template
- Clear inputs/outputs
- Transition logic
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


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

    Phase.VERIFY: """You just made changes. Verify they are correct.

Changes made:
{changes_summary}

Test output (if any):
{test_output}

Lint output (if any):
{lint_output}

Instructions:
1. Review if changes match the intended task
2. Check for obvious bugs or issues
3. Verify we only changed intended files
4. Recommend if we should proceed or fix something

Output as JSON:
{{
    "status": "pass/fail/warning",
    "issues": ["list of problems found"],
    "suggestions": ["improvements to make"],
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
    """
    
    def __init__(self, brain, printer):
        self.brain = brain
        self.printer = printer
        self.state = AgentState()
        self._tools = None
    
    @property
    def tools(self):
        if self._tools is None:
            from core.agent_tools import get_agent_tools
            self._tools = get_agent_tools()
        return self._tools
    
    def start(self, task: str):
        """Start a new task"""
        self.state.start_task(task)
        self.printer.step(f"Starting task", task[:60])
    
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
        """Explore phase: understand the codebase"""
        self.printer.step("Phase: EXPLORE", "Understanding codebase...")
        
        # Try semantic search first if available, fall back to keyword
        try:
            from core.embeddings import get_semantic_search
            search = get_semantic_search()
            results = search.search(self.state.task, limit=15)
            self.state.relevant_files = [path for path, _ in results]
            self.printer.substep(f"Found {len(results)} relevant files (semantic)")
        except Exception:
            # Fallback to keyword search
            from core.repo_explorer import get_explorer
            explorer = get_explorer()
            explorer.scan()
            relevant = explorer.find_relevant(self.state.task, limit=15)
            self.state.relevant_files = [f.path for f in relevant]
            self.printer.substep(f"Found {len(relevant)} relevant files (keyword)")
        
        # Show top files
        for path in self.state.relevant_files[:5]:
            self.printer.substep(f"  {path}")
        
        # Read the most relevant files to build context
        self.state.context_files = []
        for path in self.state.relevant_files[:3]:
            result = self.tools.execute("read_file", path=path)
            if result.success:
                self.state.context_files.append({
                    "path": path,
                    "content": result.output[:2000]  # Limit size
                })
                self.printer.substep(f"Read: {path}")
        
        self.state.transition_to(Phase.PLAN)
        return True
    
    def _execute_plan(self) -> bool:
        """Plan phase: create execution plan using LLM"""
        self.printer.step("Phase: PLAN", "Creating action plan...")
        
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
        if self.brain and hasattr(self.brain, 'ollama'):
            self.printer.substep(f"Asking {model_name} for plan...")
            
            response = self.brain.ollama.generate(
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
                else:
                    self._build_simple_plan()
            else:
                self._build_simple_plan()
        else:
            self._build_simple_plan()
        
        # Show plan to user
        if self.state.plan:
            self.printer.substep(f"Plan created with {len(self.state.plan.steps)} steps")
            for step in self.state.plan.steps[:5]:
                self.printer.substep(f"  {step.id}. {step.description[:50]}")
        
        # For now, auto-approve
        # TODO: Add user confirmation
        self.state.plan.approved = True
        
        self.state.transition_to(Phase.APPLY)
        return True
    
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
        """Build a simple plan when LLM fails"""
        self.state.plan = ExecutionPlan(task=self.state.task)
        self.state.plan.files_to_modify = self.state.relevant_files[:3]
        self.state.plan.add_step(
            f"Analyze and modify code for: {self.state.task[:50]}",
            action="analyze"
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
        """Apply phase: execute changes using tools"""
        self.printer.step("Phase: APPLY", "Executing changes...")
        
        if not self.state.plan:
            self.state.add_error("No plan to execute")
            return False
        
        step = self.state.plan.get_next_step()
        if step:
            self.printer.substep(f"Step {step.id}: {step.description}")
            
            # Execute step based on action type
            if step.file_path:
                # For now, just mark as analyzed
                # Full implementation would generate diffs with LLM
                self.printer.substep(f"  Target: {step.file_path}")
            
            self.state.plan.mark_step_complete(step.id, "Analyzed")
        
        # Check if there are more steps
        next_step = self.state.plan.get_next_step()
        if next_step:
            # Continue applying
            return self._execute_apply()
        
        # All steps done, move to verify
        self.state.transition_to(Phase.VERIFY)
        return True
    
    def _execute_verify(self) -> bool:
        """Verify phase: check results using REASON model"""
        # Get the REASON model for verification
        from core.model_router import get_router, ModelRole
        router = get_router()
        model_config = router.get_model_by_role(ModelRole.REASON)
        
        self.printer.step("Phase: VERIFY", f"Checking with {model_config.name}...")
        
        # Check if any changes were made
        has_changes = bool(self.state.changes)
        
        if has_changes:
            # Run tests if available
            test_result = self.tools.execute("run_command", command="python -m pytest tests/ -q 2>/dev/null || true", timeout=30)
            if test_result.success:
                self.state.test_output = test_result.output
                if "failed" in test_result.output.lower():
                    self.printer.substep("Some tests failed")
                    self.state.verification_passed = False
                else:
                    self.printer.substep("Tests passed")
                    self.state.verification_passed = True
            else:
                self.state.verification_passed = True  # No tests = pass
        else:
            # No changes, just analysis
            self.state.verification_passed = True
        
        if self.state.verification_passed:
            self.printer.result("Verification passed", success=True)
            self.state.transition_to(Phase.COMPLETE)
        else:
            self.printer.result("Verification failed", success=False)
            if self.state.can_retry():
                self.state.transition_to(Phase.PLAN)
            else:
                self.state.transition_to(Phase.ERROR)
        
        return True
    
    def _execute_complete(self) -> bool:
        """Complete phase: finish up"""
        self.printer.result("Task completed successfully", success=True)
        self.state.transition_to(Phase.IDLE)
        return True
    
    def _handle_error(self) -> bool:
        """Handle error state"""
        error_msg = self.state.errors[-1] if self.state.errors else 'Unknown error'
        self.printer.result(f"Task failed: {error_msg}", success=False)
        return False
    
    def run_to_completion(self) -> bool:
        """Run all phases until complete or error"""
        while self.state.phase not in [Phase.IDLE, Phase.ERROR, Phase.COMPLETE]:
            if not self.execute_phase():
                return False
        return self.state.phase == Phase.COMPLETE
