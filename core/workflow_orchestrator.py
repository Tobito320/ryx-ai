"""
Ryx AI - Workflow Orchestrator
Manages multi-step agentic workflows with plan/execute/validate
"""

import json
import re
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from datetime import datetime

from core.intent_classifier import IntentClassifier, ClassifiedIntent, IntentType
from core.model_router_v2 import ModelRouter, ModelResponse
from core.tool_registry import ToolRegistry, get_tool_registry, ToolResult, SafetyLevel


class WorkflowStatus(Enum):
    """Status of a workflow"""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """A step in a workflow"""
    step_id: int
    description: str
    tool_name: Optional[str] = None
    tool_params: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class Workflow:
    """A multi-step workflow"""
    workflow_id: str
    description: str
    intent: ClassifiedIntent
    steps: List[WorkflowStep] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    plan: str = ""
    summary: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    total_latency_ms: int = 0


class WorkflowOrchestrator:
    """
    Orchestrates multi-step agentic workflows
    
    For TASK intents:
    1. PLAN: LLM produces numbered plan, show to user
    2. EXECUTE: Call tools, feed outputs back to LLM
    3. VALIDATE: Run tests/linters if applicable
    4. SUMMARIZE: Bullet list of changes, TODOs, next steps
    """
    
    def __init__(self, model_router: ModelRouter = None, tool_registry: ToolRegistry = None):
        """Initialize orchestrator"""
        self.router = model_router or ModelRouter()
        self.tools = tool_registry or get_tool_registry()
        self.classifier = IntentClassifier()
        self.current_workflow: Optional[Workflow] = None
        self.workflow_history: List[Workflow] = []
        
        # Status icons
        self.icons = {
            'plan': '📋',
            'search': '🔍',
            'browse': '🌐',
            'files': '📂',
            'edit': '🛠️',
            'test': '🧪',
            'commit': '💾',
            'done': '✅',
            'error': '❌',
            'warning': '⚠️',
            'thinking': '💭'
        }
    
    def process_request(self, prompt: str, stream_output: Callable[[str], None] = None) -> str:
        """
        Process a user request through the full pipeline
        
        Args:
            prompt: User's natural language request
            stream_output: Optional callback for streaming output
            
        Returns:
            Final response string
        """
        start_time = time.time()
        
        # Classify intent
        intent = self.classifier.classify(prompt, self.router.ollama)
        
        # Handle tier override
        if intent.tier_override:
            self.router.set_tier(intent.tier_override)
            return f"🟣 Switched to {intent.tier_override} tier"
        
        # Handle greeting
        if intent.flags.get('is_greeting'):
            return self._handle_greeting(prompt)
        
        # Simple chat - no workflow needed
        if intent.intent_type == IntentType.CHAT and intent.complexity < 0.5:
            return self._handle_simple_chat(prompt, intent)
        
        # Task-based intents - create workflow
        if intent.intent_type in [IntentType.CODE_EDIT, IntentType.CONFIG_EDIT, 
                                  IntentType.SYSTEM_TASK, IntentType.FILE_OPS]:
            return self._handle_task_workflow(prompt, intent, stream_output)
        
        # Web research
        if intent.intent_type == IntentType.WEB_RESEARCH or intent.needs_web:
            return self._handle_web_research(prompt, intent, stream_output)
        
        # Personal chat (uncensored)
        if intent.intent_type == IntentType.PERSONAL_CHAT:
            return self._handle_personal_chat(prompt, intent)
        
        # Default to chat
        return self._handle_simple_chat(prompt, intent)
    
    def _handle_greeting(self, prompt: str) -> str:
        """Handle simple greetings without AI"""
        greetings = {
            'hello': 'Hello! How can I help you today?',
            'hi': 'Hi there! What can I do for you?',
            'hey': 'Hey! Ready to help.',
            'sup': "What's up! Ask me anything.",
            'good morning': 'Good morning! How can I assist?',
            'good evening': 'Good evening! What do you need?',
        }
        
        prompt_lower = prompt.lower().strip().rstrip('!.,?')
        for greeting, response in greetings.items():
            if greeting in prompt_lower:
                return response
        
        return "Hello! How can I help?"
    
    def _handle_simple_chat(self, prompt: str, intent: ClassifiedIntent) -> str:
        """Handle simple conversation without workflow"""
        tier = self.router.get_tier_for_intent(intent.intent_type.value)
        
        system_context = """You are a helpful assistant. Be concise - respond in 1-3 sentences for simple questions.
Do NOT generate bash commands or code unless explicitly asked."""
        
        response = self.router.query(prompt, tier=tier, system_context=system_context)
        
        if response.error:
            return f"❌ {response.error_message}"
        
        return response.response
    
    def _handle_task_workflow(self, prompt: str, intent: ClassifiedIntent, 
                             stream_output: Callable = None) -> str:
        """Handle task-based requests with full workflow"""
        workflow_id = f"wf_{int(time.time())}"
        workflow = Workflow(
            workflow_id=workflow_id,
            description=prompt,
            intent=intent
        )
        self.current_workflow = workflow
        
        output_lines = []
        
        def emit(line: str):
            output_lines.append(line)
            if stream_output:
                stream_output(line + "\n")
        
        # Step 1: Planning
        emit(f"{self.icons['plan']} Planning...")
        workflow.status = WorkflowStatus.PLANNING
        
        plan = self._generate_plan(prompt, intent)
        workflow.plan = plan
        emit(f"\n{plan}\n")
        
        # Step 2: Execute each step
        emit(f"\n{self.icons['thinking']} Executing plan...")
        workflow.status = WorkflowStatus.EXECUTING
        
        for step in workflow.steps:
            step.started_at = datetime.now()
            step.status = "running"
            
            if step.tool_name:
                emit(f"  {self._get_step_icon(step.tool_name)} Step {step.step_id}: {step.description}")
                result = self.tools.execute_tool(step.tool_name, step.tool_params)
                step.result = result.output
                step.status = "completed" if result.success else "failed"
                step.error = result.error
                
                if not result.success:
                    emit(f"    {self.icons['error']} Failed: {result.error}")
                else:
                    emit(f"    {self.icons['done']} Done")
            else:
                # LLM-based step
                step_response = self._execute_llm_step(step, intent)
                step.result = step_response
                step.status = "completed"
                emit(f"  {self.icons['done']} {step.description}")
            
            step.completed_at = datetime.now()
        
        # Step 3: Summary
        emit(f"\n{self.icons['done']} Completed")
        workflow.status = WorkflowStatus.COMPLETED
        workflow.completed_at = datetime.now()
        
        summary = self._generate_summary(workflow)
        workflow.summary = summary
        emit(f"\n{summary}")
        
        self.workflow_history.append(workflow)
        return "\n".join(output_lines)
    
    def _generate_plan(self, prompt: str, intent: ClassifiedIntent) -> str:
        """Generate a numbered plan for the task"""
        tier = "balanced"  # Use balanced tier for planning
        
        system_context = f"""You are a task planner. Generate a numbered plan for this task.
Keep it to 3-5 steps maximum. Be specific.
Available tools: {', '.join(self.tools.list_tools())}

Format:
1. [Step description]
2. [Step description]
...
"""
        
        response = self.router.query(prompt, tier=tier, system_context=system_context)
        
        if response.error:
            return f"Could not generate plan: {response.error_message}"
        
        # Parse plan into steps
        plan_text = response.response
        lines = plan_text.strip().split('\n')
        
        step_id = 1
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                # Extract step description
                desc = line.lstrip('0123456789.-) ').strip()
                if desc:
                    step = WorkflowStep(
                        step_id=step_id,
                        description=desc,
                        tool_name=self._infer_tool_for_step(desc),
                        tool_params=self._infer_params_for_step(desc, intent)
                    )
                    self.current_workflow.steps.append(step)
                    step_id += 1
        
        return plan_text
    
    def _infer_tool_for_step(self, step_desc: str) -> Optional[str]:
        """Infer which tool to use for a step"""
        step_lower = step_desc.lower()
        
        if any(w in step_lower for w in ['read', 'view', 'check', 'look at']):
            return 'file_read'
        elif any(w in step_lower for w in ['write', 'create', 'save']):
            return 'file_write'
        elif any(w in step_lower for w in ['edit', 'modify', 'change', 'update', 'patch']):
            return 'file_patch'
        elif any(w in step_lower for w in ['find', 'search', 'locate']):
            return 'file_search'
        elif any(w in step_lower for w in ['run', 'execute', 'test', 'build']):
            return 'shell_command'
        elif any(w in step_lower for w in ['browse', 'web', 'fetch', 'download']):
            return 'web_fetch'
        elif any(w in step_lower for w in ['git', 'commit', 'diff']):
            return 'git_status'
        
        return None  # LLM-based step
    
    def _infer_params_for_step(self, step_desc: str, intent: ClassifiedIntent) -> Dict:
        """Infer parameters for a step"""
        params = {}
        
        # Try to extract path from step
        path_match = re.search(r'[~/\w]+\.\w+|~?/[\w/]+', step_desc)
        if path_match:
            params['path'] = path_match.group()
        elif intent.target:
            # Use target from intent
            params['path'] = intent.target
            params['pattern'] = intent.target
        
        return params
    
    def _execute_llm_step(self, step: WorkflowStep, intent: ClassifiedIntent) -> str:
        """Execute a step using LLM"""
        tier = self.router.get_tier_for_intent(intent.intent_type.value)
        
        context = f"""You are executing step {step.step_id} of a workflow.
Task: {self.current_workflow.description}
Step: {step.description}

Previous results:
{self._get_previous_results()}

Provide the specific implementation or action needed."""
        
        response = self.router.query(step.description, tier=tier, system_context=context)
        return response.response
    
    def _get_previous_results(self) -> str:
        """Get results from previous steps"""
        results = []
        for step in self.current_workflow.steps:
            if step.status == "completed" and step.result:
                result_str = str(step.result)[:500]  # Limit size
                results.append(f"Step {step.step_id}: {result_str}")
        return "\n".join(results) if results else "None yet"
    
    def _generate_summary(self, workflow: Workflow) -> str:
        """Generate workflow summary"""
        completed = sum(1 for s in workflow.steps if s.status == "completed")
        failed = sum(1 for s in workflow.steps if s.status == "failed")
        
        summary = f"**Summary**\n"
        summary += f"- Completed: {completed}/{len(workflow.steps)} steps\n"
        
        if failed > 0:
            summary += f"- Failed: {failed} steps\n"
            for step in workflow.steps:
                if step.status == "failed":
                    summary += f"  - Step {step.step_id}: {step.error}\n"
        
        return summary
    
    def _get_step_icon(self, tool_name: str) -> str:
        """Get icon for a tool"""
        icon_map = {
            'file_search': self.icons['search'],
            'file_read': self.icons['files'],
            'file_write': self.icons['edit'],
            'file_patch': self.icons['edit'],
            'shell_command': self.icons['test'],
            'web_fetch': self.icons['browse'],
            'web_search': self.icons['search'],
            'git_status': self.icons['commit'],
            'git_diff': self.icons['commit'],
        }
        return icon_map.get(tool_name, self.icons['thinking'])
    
    def _handle_web_research(self, prompt: str, intent: ClassifiedIntent, 
                            stream_output: Callable = None) -> str:
        """Handle web research requests"""
        output_lines = []
        
        def emit(line: str):
            output_lines.append(line)
            if stream_output:
                stream_output(line + "\n")
        
        emit(f"{self.icons['browse']} Searching...")
        
        # Do web search
        result = self.tools.execute_tool('web_search', {'query': intent.target or prompt})
        
        if not result.success:
            return f"❌ Search failed: {result.error}"
        
        results = result.output
        if not results:
            return "No results found."
        
        emit(f"\n{self.icons['done']} Found {len(results)} results:\n")
        
        for i, r in enumerate(results[:5], 1):
            emit(f"{i}. **{r['title']}**")
            emit(f"   {r['url']}")
            if r.get('snippet'):
                emit(f"   {r['snippet'][:150]}...")
            emit("")
        
        return "\n".join(output_lines)
    
    def _handle_personal_chat(self, prompt: str, intent: ClassifiedIntent) -> str:
        """Handle personal/uncensored chat"""
        # Use uncensored tier
        self.router.set_tier('uncensored')
        
        system_context = """You are having a personal conversation. 
Be honest and direct. No corporate-speak or excessive warnings.
Speak naturally like a trusted friend."""
        
        response = self.router.query(prompt, system_context=system_context)
        
        # Reset tier after
        self.router.clear_override()
        
        if response.error:
            return f"❌ {response.error_message}"
        
        return f"⚠️ (uncensored mode)\n\n{response.response}"
    
    def get_current_status(self) -> Dict:
        """Get current orchestrator status"""
        return {
            "current_workflow": self.current_workflow.workflow_id if self.current_workflow else None,
            "workflows_completed": len(self.workflow_history),
            "router_status": self.router.get_status(),
            "tools_available": self.tools.list_tools()
        }
