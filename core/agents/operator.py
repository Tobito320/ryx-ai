"""
Ryx AI - Operator Agent

The executor that:
1. Receives plans from supervisor
2. Executes steps using tools
3. Handles retries and fallbacks
4. Reports status back
"""

import time
from typing import Optional, Dict, Any, List, Tuple, Callable

from core.planning import (
    Plan, PlanStep, TaskResult, StepResult, OperatorStatus,
    Context, AgentType, ModelSize
)
from .base import BaseAgent, AgentConfig, get_tool_registry


class OperatorAgent(BaseAgent):
    """
    Base operator agent - the executor.
    
    Executes plans step by step:
    1. Runs each step's tool
    2. Handles failures with fallbacks
    3. Reports status
    4. Escalates to supervisor if max retries exceeded
    """
    
    EXECUTION_PROMPT = '''You are an operator agent executing a task on Arch Linux.

TASK: {task}
STEP: {step_description}
TOOL: {tool_name}
TOOL OUTPUT: {tool_output}

Based on the tool output, determine:
1. Was this step successful?
2. What is the result?
3. Should we continue or stop?

OUTPUT ONLY VALID JSON:
{{
  "success": true|false,
  "result": "human readable result",
  "continue": true|false,
  "next_action": null or "what to do next"
}}'''
    
    def __init__(
        self,
        llm_client,
        model: str = "qwen2.5:3b",
        agent_type: AgentType = AgentType.SHELL
    ):
        config = AgentConfig(
            name=f"{agent_type.value.title()}Operator",
            model=model,
            model_size=ModelSize.SMALL,
            max_tokens=300,
            temperature=0.1,
            timeout_seconds=30,
            max_retries=2
        )
        super().__init__(config, llm_client)
        self.agent_type = agent_type
        self.tool_registry = get_tool_registry()
        self.status_callbacks: List[Callable[[OperatorStatus], None]] = []
    
    def execute(self, task: str, context: Context) -> TaskResult:
        """Execute a task directly (without pre-made plan)"""
        # This is for simple single-step execution
        # For complex tasks, use execute_plan
        result = self._execute_simple_task(task, context)
        return TaskResult(
            success=result[0],
            output=result[1],
            operator_iterations=1
        )
    
    def execute_plan(self, plan: Plan, context: Context) -> TaskResult:
        """
        Execute a plan step by step.
        
        Returns TaskResult with full execution details.
        """
        start_time = time.time()
        step_results: List[StepResult] = []
        errors: List[str] = []
        
        for attempt in range(plan.max_retries + 1):
            for step in plan.steps:
                # Report status
                self._report_status(OperatorStatus(
                    step=step.step,
                    status="running",
                    action=step.action,
                    attempts=attempt + 1
                ))
                
                # Execute step
                step_result = self._execute_step(step, context, plan)
                step_results.append(step_result)
                
                if step_result.success:
                    self._report_status(OperatorStatus(
                        step=step.step,
                        status="success",
                        action=step.action,
                        attempts=attempt + 1
                    ))
                else:
                    errors.append(step_result.error or "Unknown error")
                    
                    # Try fallback if available
                    if step.fallback:
                        self._report_status(OperatorStatus(
                            step=step.step,
                            status="retrying",
                            action=step.fallback,
                            attempts=attempt + 1,
                            error=step_result.error
                        ))
                        
                        fallback_step = PlanStep(
                            step=step.step,
                            action=step.fallback,
                            params=step.params,
                            description=f"Fallback: {step.fallback}"
                        )
                        fallback_result = self._execute_step(fallback_step, context, plan)
                        
                        if fallback_result.success:
                            step_results.append(fallback_result)
                            continue
                    
                    # Step failed - break to retry loop
                    self._report_status(OperatorStatus(
                        step=step.step,
                        status="failed",
                        action=step.action,
                        attempts=attempt + 1,
                        error=step_result.error
                    ))
                    break
            
            # Check if all steps succeeded
            if all(sr.success for sr in step_results[-len(plan.steps):]):
                break
        
        # Compile final result
        duration_ms = int((time.time() - start_time) * 1000)
        success = all(sr.success for sr in step_results[-len(plan.steps):])
        
        # Get final output
        output = self._compile_output(step_results, plan)
        
        return TaskResult(
            success=success,
            output=output,
            plan_used=plan,
            steps_completed=sum(1 for sr in step_results if sr.success),
            total_duration_ms=duration_ms,
            operator_iterations=len(step_results),
            errors=errors
        )
    
    def _execute_step(
        self,
        step: PlanStep,
        context: Context,
        plan: Plan
    ) -> StepResult:
        """Execute a single step"""
        start_time = time.time()
        
        # Get tool
        tool = self.tool_registry.get(step.action)
        if not tool:
            # Unknown tool - try as shell command
            tool = self.tool_registry.get("run_command")
            if tool:
                step.params = {"cmd": step.action}
        
        if not tool:
            return StepResult(
                step=step.step,
                success=False,
                error=f"Unknown tool: {step.action}",
                duration_ms=0
            )
        
        # Execute tool
        try:
            success, output = self.tool_registry.execute_tool(
                step.action,
                **step.params
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return StepResult(
                step=step.step,
                success=success,
                output=output,
                error=None if success else output,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return StepResult(
                step=step.step,
                success=False,
                error=str(e),
                duration_ms=duration_ms
            )
    
    def _execute_simple_task(
        self,
        task: str,
        context: Context
    ) -> Tuple[bool, str]:
        """Execute a simple single-step task"""
        # Use LLM to determine what tool to use
        prompt = f'''Task: {task}

Available tools:
- find_files(pattern: str, path: str = "~", max_results: int = 10) - Find files by name
- read_file(path: str, max_lines: int = 100) - Read file contents
- run_command(cmd: str, timeout: int = 30) - Run shell command
- search_content(pattern: str, path: str = ".", max_results: int = 20) - Search file contents

OUTPUT ONLY valid JSON with exact parameter names:
{{"tool": "find_files", "params": {{"pattern": "search_term", "path": "~"}}}}'''
        
        success, response = self._call_llm(prompt)
        if not success:
            return False, f"Failed to understand task: {response}"
        
        try:
            import json
            clean = response.strip()
            start = clean.find('{')
            end = clean.rfind('}') + 1
            if start >= 0 and end > start:
                clean = clean[start:end]
            
            data = json.loads(clean)
            tool_name = data.get("tool", "run_command")
            params = data.get("params", {})
            
            # Normalize common param name mistakes
            if tool_name == "find_files":
                # Handle common LLM mistakes
                if "search_pattern" in params:
                    params["pattern"] = params.pop("search_pattern")
                if "query" in params:
                    params["pattern"] = params.pop("query")
                if "name" in params:
                    params["pattern"] = params.pop("name")
            
            # Execute tool
            return self.tool_registry.execute_tool(tool_name, **params)
            
        except Exception as e:
            return False, str(e)
    
    def _compile_output(
        self,
        step_results: List[StepResult],
        plan: Plan
    ) -> str:
        """Compile step results into final output"""
        outputs = []
        for sr in step_results:
            if sr.output:
                outputs.append(sr.output)
        
        if outputs:
            return "\n".join(outputs)
        
        return plan.understanding
    
    def _report_status(self, status: OperatorStatus):
        """Report status to registered callbacks"""
        for callback in self.status_callbacks:
            try:
                callback(status)
            except Exception:
                pass
    
    def register_status_callback(self, callback: Callable[[OperatorStatus], None]):
        """Register a callback to receive status updates"""
        self.status_callbacks.append(callback)


class FileOperatorAgent(OperatorAgent):
    """Specialized operator for file operations"""
    
    def __init__(self, llm_client, model: str = "qwen2.5:3b"):
        super().__init__(llm_client, model, AgentType.FILE)
        self.config.allowed_tools = ["find_files", "read_file", "search_content"]


class ShellOperatorAgent(OperatorAgent):
    """Specialized operator for shell commands"""
    
    def __init__(self, llm_client, model: str = "qwen2.5:3b"):
        super().__init__(llm_client, model, AgentType.SHELL)
        self.config.allowed_tools = ["run_command", "find_files", "read_file"]


class CodeOperatorAgent(OperatorAgent):
    """Specialized operator for code operations"""
    
    def __init__(self, llm_client, model: str = "qwen2.5-coder:7b"):
        super().__init__(llm_client, model, AgentType.CODE)
        self.config.model_size = ModelSize.MEDIUM
        self.config.max_tokens = 1000
        self.config.allowed_tools = ["read_file", "run_command", "search_content"]
