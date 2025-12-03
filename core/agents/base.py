"""
Ryx AI - Base Agent

Abstract base class for all agents (supervisor and operators).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import time

from core.planning import Plan, TaskResult, Context, StepResult, ModelSize


@dataclass
class AgentConfig:
    """Configuration for an agent"""
    name: str
    model: str                      # vLLM model name
    model_size: ModelSize
    max_tokens: int = 500
    temperature: float = 0.3
    timeout_seconds: int = 30
    max_retries: int = 2
    
    # Tool permissions
    allowed_tools: List[str] = field(default_factory=list)
    
    # System prompt additions
    system_prompt_suffix: str = ""


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    
    Agents are specialized components that can:
    - Understand tasks (supervisor)
    - Execute tasks (operators)
    - Use tools
    - Report status
    """
    
    def __init__(self, config: AgentConfig, llm_client):
        self.config = config
        self.llm = llm_client
        self.call_count = 0
        self.total_tokens = 0
        self.last_error: Optional[str] = None
    
    @abstractmethod
    def execute(self, task: str, context: Context) -> TaskResult:
        """
        Execute a task and return result.
        
        Args:
            task: Task description or prompt
            context: Execution context
            
        Returns:
            TaskResult with success/failure and output
        """
        pass
    
    def _call_llm(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        Make an LLM call with error handling.
        
        Returns:
            (success, response_or_error)
        """
        self.call_count += 1
        
        try:
            response = self.llm.generate(
                prompt=prompt,
                model=self.config.model,
                system=system or self._get_system_prompt(),
                max_tokens=max_tokens or self.config.max_tokens,
                temperature=temperature or self.config.temperature
            )
            
            if response.error:
                self.last_error = response.error
                return False, response.error
            
            return True, response.response
            
        except Exception as e:
            self.last_error = str(e)
            return False, str(e)
    
    def _get_system_prompt(self) -> str:
        """Get base system prompt for this agent"""
        base = f"You are {self.config.name}, a specialized AI agent."
        if self.config.system_prompt_suffix:
            base += f"\n{self.config.system_prompt_suffix}"
        return base
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        return {
            "name": self.config.name,
            "model": self.config.model,
            "call_count": self.call_count,
            "total_tokens": self.total_tokens,
            "last_error": self.last_error
        }


class ToolRegistry:
    """Registry of available tools that agents can use"""
    
    def __init__(self):
        self._tools: Dict[str, callable] = {}
        self._descriptions: Dict[str, str] = {}
    
    def register(self, name: str, func: callable, description: str = ""):
        """Register a tool"""
        self._tools[name] = func
        self._descriptions[name] = description
    
    def get(self, name: str) -> Optional[callable]:
        """Get a tool by name"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[Dict[str, str]]:
        """List all registered tools"""
        return [
            {"name": name, "description": self._descriptions.get(name, "")}
            for name in self._tools.keys()
        ]
    
    def execute_tool(self, name: str, **params) -> Tuple[bool, str]:
        """Execute a tool and return result"""
        tool = self._tools.get(name)
        if not tool:
            return False, f"Unknown tool: {name}"
        
        try:
            result = tool(**params)
            return True, str(result)
        except Exception as e:
            return False, str(e)


# Global tool registry
_tool_registry: Optional[ToolRegistry] = None

def get_tool_registry() -> ToolRegistry:
    """Get singleton tool registry"""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
        _register_default_tools(_tool_registry)
    return _tool_registry


def _register_default_tools(registry: ToolRegistry):
    """Register default tools"""
    import subprocess
    import os
    
    def tool_find_files(pattern: str, path: str = "~", max_results: int = 10) -> str:
        """Find files matching pattern"""
        path = os.path.expanduser(path)
        try:
            # Try fd first (faster)
            result = subprocess.run(
                ["fd", "-t", "f", pattern, path],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                files = result.stdout.strip().split('\n')[:max_results]
                return '\n'.join(files)
        except FileNotFoundError:
            pass
        
        # Fall back to find
        try:
            result = subprocess.run(
                ["find", path, "-type", "f", "-name", f"*{pattern}*"],
                capture_output=True, text=True, timeout=10
            )
            files = result.stdout.strip().split('\n')[:max_results]
            return '\n'.join(f for f in files if f)
        except Exception as e:
            return f"Error: {e}"
    
    def tool_read_file(path: str, max_lines: int = 100) -> str:
        """Read file contents"""
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return f"File not found: {path}"
        try:
            with open(path, 'r') as f:
                lines = f.readlines()[:max_lines]
                return ''.join(lines)
        except Exception as e:
            return f"Error reading file: {e}"
    
    def tool_run_command(cmd: str, timeout: int = 30) -> str:
        """Run a shell command"""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR: {result.stderr}"
            return output or "(no output)"
        except subprocess.TimeoutExpired:
            return "Command timed out"
        except Exception as e:
            return f"Error: {e}"
    
    def tool_search_content(pattern: str, path: str = ".", max_results: int = 20) -> str:
        """Search file contents with ripgrep"""
        path = os.path.expanduser(path)
        try:
            result = subprocess.run(
                ["rg", "-l", "--max-count", "1", pattern, path],
                capture_output=True, text=True, timeout=10
            )
            files = result.stdout.strip().split('\n')[:max_results]
            return '\n'.join(f for f in files if f)
        except FileNotFoundError:
            # Fall back to grep
            result = subprocess.run(
                ["grep", "-rl", pattern, path],
                capture_output=True, text=True, timeout=10
            )
            files = result.stdout.strip().split('\n')[:max_results]
            return '\n'.join(f for f in files if f)
        except Exception as e:
            return f"Error: {e}"
    
    # Register tools
    registry.register("find_files", tool_find_files, "Find files by name pattern")
    registry.register("read_file", tool_read_file, "Read file contents")
    registry.register("run_command", tool_run_command, "Run shell command")
    registry.register("search_content", tool_search_content, "Search file contents")
