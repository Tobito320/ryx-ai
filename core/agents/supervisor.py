"""
Ryx AI - Supervisor Agent

The strategic planner that:
1. Understands user intent deeply
2. Creates execution plans
3. Delegates to operators
4. Handles failures and recovery
"""

import json
from typing import Optional, Dict, Any, Tuple

from core.planning import (
    Plan, PlanStep, TaskResult, Context,
    AgentType, ModelSize, TaskComplexity
)
from .base import BaseAgent, AgentConfig


class SupervisorAgent(BaseAgent):
    """
    Supervisor agent - the strategic planner.
    
    Called only:
    1. Once at task start (planning)
    2. Optionally on repeated failures (rescue)
    
    Uses larger model (14B+) for better understanding.
    """
    
    PLANNING_PROMPT = '''You are a task planning supervisor for Ryx AI on Arch Linux + Hyprland.

CONTEXT:
- Working directory: {cwd}
- Recent commands: {recent_commands}
- Last result: {last_result}
- User language: {language}

USER REQUEST: {query}

AVAILABLE TOOLS:
- find_files: Search for files by name
- read_file: Read file contents
- run_command: Execute shell command
- search_content: Search file contents with ripgrep

INSTRUCTIONS:
1. Analyze what the user wants
2. Estimate complexity (1-5)
3. Create a step-by-step plan (max 5 steps)
4. Choose the right agent type: file|code|web|shell|rag
5. Generate an optimized prompt for the operator

OUTPUT ONLY VALID JSON:
{{
  "understanding": "What the user wants in one sentence",
  "complexity": 1-5,
  "confidence": 0.0-1.0,
  "steps": [
    {{"step": 1, "action": "tool_name", "params": {{}}, "description": "what this does"}}
  ],
  "agent_type": "file|code|web|shell|rag",
  "model_size": "small|medium|large",
  "operator_prompt": "Precise instruction for the operator"
}}'''

    RESCUE_PROMPT = '''The operator failed to complete the task after {attempts} attempts.

ORIGINAL TASK: {query}
ORIGINAL PLAN: {plan}

FAILURE DETAILS:
{errors}

ANALYZE:
1. What specifically went wrong?
2. Was the plan flawed or was it execution?
3. Should we: ADJUST_PLAN | CHANGE_AGENT | TAKEOVER

OUTPUT ONLY VALID JSON:
{{
  "analysis": "What went wrong",
  "action": "ADJUST_PLAN|CHANGE_AGENT|TAKEOVER",
  "adjusted_plan": null or {{new plan}},
  "new_agent": null or "agent_type",
  "direct_result": null or "direct answer if TAKEOVER"
}}'''

    def __init__(self, ollama_client, model: str = "qwen2.5-coder:14b"):
        config = AgentConfig(
            name="Supervisor",
            model=model,
            model_size=ModelSize.LARGE,
            max_tokens=800,
            temperature=0.2,
            timeout_seconds=60,
            system_prompt_suffix="You output ONLY valid JSON. No explanations."
        )
        super().__init__(config, ollama_client)
    
    def create_plan(self, query: str, context: Context) -> Tuple[bool, Plan]:
        """
        Create an execution plan for the given query.
        
        Returns:
            (success, Plan)
        """
        prompt = self.PLANNING_PROMPT.format(
            cwd=context.cwd or "~",
            recent_commands=", ".join(context.recent_commands[-3:]) or "none",
            last_result=(context.last_result or "none")[:200],
            language=context.language,
            query=query
        )
        
        success, response = self._call_llm(prompt)
        
        if not success:
            return False, self._fallback_plan(query, context)
        
        return self._parse_plan_response(response, query)
    
    def rescue(
        self,
        query: str,
        plan: Plan,
        errors: list,
        attempts: int,
        context: Context
    ) -> Tuple[str, Optional[Plan], Optional[str]]:
        """
        Analyze failure and decide on recovery action.
        
        Returns:
            (action, adjusted_plan_or_none, direct_result_or_none)
            action is: "ADJUST_PLAN", "CHANGE_AGENT", or "TAKEOVER"
        """
        prompt = self.RESCUE_PROMPT.format(
            attempts=attempts,
            query=query,
            plan=plan.to_json(),
            errors="\n".join(errors)
        )
        
        success, response = self._call_llm(prompt, max_tokens=600)
        
        if not success:
            return "TAKEOVER", None, f"Unable to complete: {query}"
        
        return self._parse_rescue_response(response, query)
    
    def execute(self, task: str, context: Context) -> TaskResult:
        """Execute = create plan (supervisor doesn't execute directly)"""
        success, plan = self.create_plan(task, context)
        
        if success:
            return TaskResult(
                success=True,
                output=plan.to_json(),
                plan_used=plan,
                supervisor_calls=1
            )
        else:
            return TaskResult(
                success=False,
                output="Failed to create plan",
                errors=[self.last_error or "Unknown error"],
                supervisor_calls=1
            )
    
    def _parse_plan_response(self, response: str, query: str) -> Tuple[bool, Plan]:
        """Parse LLM response into Plan object"""
        try:
            # Clean response
            clean = response.strip()
            if '```' in clean:
                # Extract from code block
                parts = clean.split('```')
                for part in parts:
                    if part.strip().startswith('json'):
                        clean = part[4:].strip()
                        break
                    elif part.strip().startswith('{'):
                        clean = part.strip()
                        break
            
            # Find JSON object
            start = clean.find('{')
            end = clean.rfind('}') + 1
            if start >= 0 and end > start:
                clean = clean[start:end]
            
            data = json.loads(clean)
            
            # Build Plan
            steps = []
            for s in data.get("steps", []):
                steps.append(PlanStep(
                    step=s.get("step", 0),
                    action=s.get("action", "run_command"),
                    params=s.get("params", {}),
                    description=s.get("description", "")
                ))
            
            # Map agent type
            agent_map = {
                "file": AgentType.FILE,
                "code": AgentType.CODE,
                "web": AgentType.WEB,
                "shell": AgentType.SHELL,
                "rag": AgentType.RAG
            }
            agent_type = agent_map.get(
                data.get("agent_type", "shell"),
                AgentType.SHELL
            )
            
            # Map model size
            size_map = {
                "tiny": ModelSize.TINY,
                "small": ModelSize.SMALL,
                "medium": ModelSize.MEDIUM,
                "large": ModelSize.LARGE
            }
            model_size = size_map.get(
                data.get("model_size", "small"),
                ModelSize.SMALL
            )
            
            plan = Plan(
                understanding=data.get("understanding", query),
                complexity=data.get("complexity", 3),
                confidence=data.get("confidence", 0.7),
                steps=steps,
                agent_type=agent_type,
                model_size=model_size,
                operator_prompt=data.get("operator_prompt", query)
            )
            
            return True, plan
            
        except (json.JSONDecodeError, KeyError) as e:
            self.last_error = f"Failed to parse plan: {e}"
            return False, self._fallback_plan(query, Context())
    
    def _parse_rescue_response(
        self,
        response: str,
        query: str
    ) -> Tuple[str, Optional[Plan], Optional[str]]:
        """Parse rescue response"""
        try:
            clean = response.strip()
            start = clean.find('{')
            end = clean.rfind('}') + 1
            if start >= 0 and end > start:
                clean = clean[start:end]
            
            data = json.loads(clean)
            
            action = data.get("action", "TAKEOVER")
            
            adjusted_plan = None
            if action == "ADJUST_PLAN" and data.get("adjusted_plan"):
                # Parse adjusted plan
                _, adjusted_plan = self._parse_plan_response(
                    json.dumps(data["adjusted_plan"]),
                    query
                )
            
            direct_result = data.get("direct_result")
            
            return action, adjusted_plan, direct_result
            
        except (json.JSONDecodeError, KeyError):
            return "TAKEOVER", None, f"Unable to complete: {query}"
    
    def _fallback_plan(self, query: str, context: Context) -> Plan:
        """Create a simple fallback plan when parsing fails"""
        return Plan(
            understanding=query,
            complexity=3,
            confidence=0.3,
            steps=[
                PlanStep(
                    step=1,
                    action="run_command",
                    params={"cmd": "echo 'Unable to understand request'"},
                    description="Fallback"
                )
            ],
            agent_type=AgentType.SHELL,
            model_size=ModelSize.SMALL,
            operator_prompt=query
        )
