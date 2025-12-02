"""
Ryx AI - Planning Schemas

Data structures for task planning and execution.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import json


class TaskComplexity(Enum):
    """Complexity level for routing decisions"""
    TRIVIAL = "trivial"     # Direct execution, no LLM (e.g., "open youtube")
    SIMPLE = "simple"       # Single tool, small LLM (e.g., "find file.txt")
    MODERATE = "moderate"   # Multi-step, needs planning (e.g., "find and open config")
    COMPLEX = "complex"     # Reasoning required, large LLM (e.g., "refactor this module")


class AgentType(Enum):
    """Types of specialized agents"""
    FILE = "file"       # File operations: fd, rg, find, cat, read
    CODE = "code"       # Code operations: read, write, patch, refactor
    WEB = "web"         # Web operations: search, scrape, browse
    SHELL = "shell"     # Shell commands: bash (sandboxed)
    RAG = "rag"         # Knowledge retrieval: vector search, memory


class ModelSize(Enum):
    """Model size tiers"""
    TINY = "tiny"       # 1-3B, instant responses
    SMALL = "small"     # 3-7B, fast general use
    MEDIUM = "medium"   # 7-14B, balanced
    LARGE = "large"     # 14B+, complex reasoning


@dataclass
class PlanStep:
    """A single step in an execution plan"""
    step: int
    action: str                     # Tool/action to execute
    params: Dict[str, Any]          # Parameters for the action
    description: str = ""           # Human-readable description
    fallback: Optional[str] = None  # Alternative action if this fails
    timeout_seconds: int = 10       # Max time for this step
    requires_output: bool = True    # Whether to capture output
    
    def to_dict(self) -> Dict:
        return {
            "step": self.step,
            "action": self.action,
            "params": self.params,
            "description": self.description,
            "fallback": self.fallback,
            "timeout_seconds": self.timeout_seconds
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PlanStep":
        return cls(
            step=data.get("step", 0),
            action=data.get("action", ""),
            params=data.get("params", {}),
            description=data.get("description", ""),
            fallback=data.get("fallback"),
            timeout_seconds=data.get("timeout_seconds", 10)
        )


@dataclass
class Plan:
    """Complete execution plan from supervisor"""
    understanding: str              # What the user wants (one sentence)
    complexity: int                 # 1-5 complexity score
    confidence: float               # 0.0-1.0 confidence in understanding
    steps: List[PlanStep]           # Ordered steps to execute
    agent_type: AgentType           # Which agent should execute
    model_size: ModelSize           # What model size the agent should use
    operator_prompt: str            # Optimized prompt for the operator
    timeout_seconds: int = 30       # Total timeout for plan execution
    max_retries: int = 2            # Max retry attempts
    
    def to_dict(self) -> Dict:
        return {
            "understanding": self.understanding,
            "complexity": self.complexity,
            "confidence": self.confidence,
            "steps": [s.to_dict() for s in self.steps],
            "agent_type": self.agent_type.value,
            "model_size": self.model_size.value,
            "operator_prompt": self.operator_prompt,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Plan":
        return cls(
            understanding=data.get("understanding", ""),
            complexity=data.get("complexity", 3),
            confidence=data.get("confidence", 0.5),
            steps=[PlanStep.from_dict(s) for s in data.get("steps", [])],
            agent_type=AgentType(data.get("agent_type", "shell")),
            model_size=ModelSize(data.get("model_size", "small")),
            operator_prompt=data.get("operator_prompt", ""),
            timeout_seconds=data.get("timeout_seconds", 30),
            max_retries=data.get("max_retries", 2)
        )


@dataclass
class StepResult:
    """Result of executing a single step"""
    step: int
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    duration_ms: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "step": self.step,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms
        }


@dataclass
class OperatorStatus:
    """Status update from operator to supervisor"""
    step: int
    status: str                     # "running", "success", "failed", "retrying"
    action: str
    attempts: int = 1
    error: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "step": self.step,
            "status": self.status,
            "action": self.action,
            "attempts": self.attempts,
            "error": self.error,
            "context": self.context
        }


@dataclass 
class TaskResult:
    """Final result of task execution"""
    success: bool
    output: str
    plan_used: Optional[Plan] = None
    steps_completed: int = 0
    total_duration_ms: int = 0
    supervisor_calls: int = 0
    operator_iterations: int = 0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "output": self.output,
            "steps_completed": self.steps_completed,
            "total_duration_ms": self.total_duration_ms,
            "supervisor_calls": self.supervisor_calls,
            "operator_iterations": self.operator_iterations,
            "errors": self.errors
        }


@dataclass
class Context:
    """Execution context passed between components"""
    # Current state
    cwd: str = ""
    git_branch: Optional[str] = None
    git_status: Optional[str] = None
    
    # History
    recent_commands: List[str] = field(default_factory=list)
    recent_files: List[str] = field(default_factory=list)
    last_result: Optional[str] = None
    
    # User preferences
    language: str = "en"  # "de" | "en"
    editor: str = "nvim"
    terminal: str = "kitty"
    
    # Tool states
    enabled_tools: Dict[str, bool] = field(default_factory=dict)
    
    # Session
    session_id: str = ""
    turn_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "cwd": self.cwd,
            "git_branch": self.git_branch,
            "recent_commands": self.recent_commands[-5:],  # Last 5
            "recent_files": self.recent_files[-5:],
            "last_result": (self.last_result or "")[:200],  # Truncate
            "language": self.language,
            "turn_count": self.turn_count
        }
