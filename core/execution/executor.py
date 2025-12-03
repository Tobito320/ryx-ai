"""
Ryx AI - Task Executor

The main orchestrator that:
1. Routes tasks through complexity gate
2. Manages supervisor/operator interaction
3. Handles the full task lifecycle
"""

import time
from typing import Optional, Dict, Any, Callable, List

from core.planning import (
    Plan, TaskResult, Context, OperatorStatus,
    TaskComplexity, AgentType, ModelSize,
    get_complexity_gate
)
from core.agents import (
    SupervisorAgent,
    OperatorAgent,
    FileOperatorAgent,
    ShellOperatorAgent,
    CodeOperatorAgent,
)
from core.progress import Spinner


class TaskExecutor:
    """
    Main task executor - orchestrates the supervisor/operator system.
    
    Flow:
    1. Classify complexity (rule-based, fast)
    2. For trivial/simple: direct to operator
    3. For moderate/complex: supervisor planning first
    4. Execute via appropriate operator
    5. Handle failures with supervisor rescue
    """
    
    def __init__(self, llm_client, verbose: bool = False):
        self.llm = llm_client
        self.verbose = verbose
        
        # Initialize components
        self.complexity_gate = get_complexity_gate()
        self.supervisor: Optional[SupervisorAgent] = None
        self.operators: Dict[AgentType, OperatorAgent] = {}
        
        # Stats
        self.stats = {
            "tasks_executed": 0,
            "supervisor_calls": 0,
            "operator_calls": 0,
            "rescues": 0,
            "failures": 0
        }
        
        # Callbacks
        self.status_callbacks: List[Callable[[str], None]] = []
    
    def _get_supervisor(self) -> SupervisorAgent:
        """Lazy-load supervisor (expensive model)"""
        if self.supervisor is None:
            self.supervisor = SupervisorAgent(self.llm)
        return self.supervisor
    
    def _get_operator(self, agent_type: AgentType, model_size: ModelSize) -> OperatorAgent:
        """Get or create appropriate operator"""
        # Choose model based on size
        model_map = {
            ModelSize.TINY: "qwen2.5:3b",
            ModelSize.SMALL: "qwen2.5:3b",
            ModelSize.MEDIUM: "qwen2.5-coder:7b",
            ModelSize.LARGE: "qwen2.5-coder:14b",
        }
        model = model_map.get(model_size, "qwen2.5:3b")
        
        # Get or create operator
        if agent_type not in self.operators:
            if agent_type == AgentType.FILE:
                self.operators[agent_type] = FileOperatorAgent(self.llm, model)
            elif agent_type == AgentType.CODE:
                self.operators[agent_type] = CodeOperatorAgent(self.llm)
            elif agent_type == AgentType.SHELL:
                self.operators[agent_type] = ShellOperatorAgent(self.llm, model)
            else:
                self.operators[agent_type] = OperatorAgent(self.llm, model, agent_type)
            
            # Register status callback
            self.operators[agent_type].register_status_callback(self._on_operator_status)
        
        return self.operators[agent_type]
    
    def execute(self, query: str, context: Optional[Context] = None) -> TaskResult:
        """
        Execute a task from natural language query.
        
        This is the main entry point.
        """
        context = context or Context()
        self.stats["tasks_executed"] += 1
        start_time = time.time()
        
        # Step 1: Classify complexity
        complexity, suggested_agent = self.complexity_gate.classify(query)
        self._log(f"Complexity: {complexity.value}, Agent: {suggested_agent}")
        
        # Step 2: Route based on complexity
        if complexity == TaskComplexity.TRIVIAL:
            # Direct execution without LLM
            return self._execute_trivial(query, context)
        
        elif complexity == TaskComplexity.SIMPLE:
            # Small operator only
            return self._execute_simple(query, suggested_agent or AgentType.SHELL, context)
        
        else:
            # Supervisor planning + operator
            return self._execute_with_planning(query, context)
    
    def _execute_trivial(self, query: str, context: Context) -> TaskResult:
        """Execute trivial task directly"""
        # Handle known patterns without LLM
        q = query.lower()
        
        # Time/date
        if any(w in q for w in ['time', 'date', 'uhrzeit', 'datum']):
            from datetime import datetime
            now = datetime.now()
            return TaskResult(
                success=True,
                output=now.strftime("%Y-%m-%d %H:%M:%S"),
                operator_iterations=0
            )
        
        # Website opening
        websites = {
            'youtube': 'https://youtube.com',
            'github': 'https://github.com',
            'google': 'https://google.com',
            'reddit': 'https://reddit.com',
        }
        for name, url in websites.items():
            if name in q:
                import subprocess
                subprocess.Popen(['xdg-open', url])
                return TaskResult(
                    success=True,
                    output=f"Opened {url}",
                    operator_iterations=0
                )
        
        # Fallback
        return TaskResult(
            success=False,
            output="Could not handle trivial task",
            errors=["No matching pattern"]
        )
    
    def _execute_simple(
        self,
        query: str,
        agent_type: AgentType,
        context: Context
    ) -> TaskResult:
        """Execute simple task with small operator"""
        self.stats["operator_calls"] += 1
        
        operator = self._get_operator(agent_type, ModelSize.SMALL)
        return operator.execute(query, context)
    
    def _execute_with_planning(self, query: str, context: Context) -> TaskResult:
        """Execute task with supervisor planning"""
        # Step 1: Supervisor creates plan
        self._log("Calling supervisor for planning...")
        self.stats["supervisor_calls"] += 1
        
        supervisor = self._get_supervisor()
        success, plan = supervisor.create_plan(query, context)
        
        if not success:
            self.stats["failures"] += 1
            return TaskResult(
                success=False,
                output="Failed to create plan",
                errors=[supervisor.last_error or "Unknown planning error"],
                supervisor_calls=1
            )
        
        self._log(f"Plan created: {plan.understanding}")
        
        # Step 2: Operator executes plan
        self._log(f"Executing with {plan.agent_type.value} operator...")
        self.stats["operator_calls"] += 1
        
        operator = self._get_operator(plan.agent_type, plan.model_size)
        result = operator.execute_plan(plan, context)
        result.supervisor_calls = 1
        
        # Step 3: Handle failure with rescue
        if not result.success and result.operator_iterations >= plan.max_retries:
            self._log("Operator failed, calling supervisor rescue...")
            self.stats["rescues"] += 1
            self.stats["supervisor_calls"] += 1
            
            action, new_plan, direct_result = supervisor.rescue(
                query=query,
                plan=plan,
                errors=result.errors,
                attempts=result.operator_iterations,
                context=context
            )
            
            if action == "TAKEOVER" and direct_result:
                return TaskResult(
                    success=True,
                    output=direct_result,
                    supervisor_calls=2
                )
            
            elif action == "ADJUST_PLAN" and new_plan:
                # Retry with adjusted plan
                self._log("Retrying with adjusted plan...")
                self.stats["operator_calls"] += 1
                
                result = operator.execute_plan(new_plan, context)
                result.supervisor_calls = 2
            
            elif action == "CHANGE_AGENT" and new_plan:
                # Use different operator
                self._log(f"Switching to {new_plan.agent_type.value} agent...")
                self.stats["operator_calls"] += 1
                
                new_operator = self._get_operator(new_plan.agent_type, new_plan.model_size)
                result = new_operator.execute_plan(new_plan, context)
                result.supervisor_calls = 2
        
        return result
    
    def _on_operator_status(self, status: OperatorStatus):
        """Handle status updates from operators"""
        msg = f"Step {status.step}: {status.status} - {status.action}"
        if status.error:
            msg += f" (error: {status.error})"
        self._log(msg)
        
        for callback in self.status_callbacks:
            callback(msg)
    
    def _log(self, message: str):
        """Log message if verbose"""
        if self.verbose:
            print(f"[Executor] {message}")
    
    def register_status_callback(self, callback: Callable[[str], None]):
        """Register callback for status updates"""
        self.status_callbacks.append(callback)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get executor statistics"""
        return {
            **self.stats,
            "supervisor_stats": self.supervisor.get_stats() if self.supervisor else None,
            "operator_stats": {
                name.value: op.get_stats() 
                for name, op in self.operators.items()
            }
        }


# Singleton instance
_executor: Optional[TaskExecutor] = None

def get_executor(llm_client=None, verbose: bool = False) -> TaskExecutor:
    """Get singleton executor instance"""
    global _executor
    if _executor is None:
        if llm_client is None:
            from core.llm_client import vLLMClient
            from core.model_router import ModelRouter
            router = ModelRouter()
            llm_client = vLLMClient(base_url=router.get_llm_url())
        _executor = TaskExecutor(llm_client, verbose)
    return _executor
