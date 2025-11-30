"""
RYX Core - Abstract Interfaces

Provides base classes for extensible components:
- BaseModel: Abstract model interface
- BaseTool: Abstract tool interface
- BaseWorkflow: Workflow with nodes and edges (N8N-style)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Generator, Callable
from enum import Enum
from datetime import datetime
import uuid


class ModelCapability(Enum):
    """Capabilities a model can have"""
    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    CODE_ANALYSIS = "code_analysis"
    REASONING = "reasoning"
    PLANNING = "planning"
    TOOL_USE = "tool_use"
    LONG_CONTEXT = "long_context"
    FAST_INFERENCE = "fast_inference"


@dataclass
class ModelResponse:
    """Response from a model"""
    content: str
    model_name: str
    finish_reason: str = "stop"
    tokens_used: int = 0
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseModel(ABC):
    """
    Abstract base class for AI models
    
    Implement this to add new model providers (Ollama, OpenAI, etc.)
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Model name/identifier"""
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> List[ModelCapability]:
        """List of model capabilities"""
        pass
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> ModelResponse:
        """
        Generate a response
        
        Args:
            prompt: User prompt
            system_prompt: Optional system context
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional model-specific parameters
            
        Returns:
            ModelResponse with generated content
        """
        pass
    
    @abstractmethod
    def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Generator[str, None, None]:
        """
        Stream a response token by token
        
        Args:
            prompt: User prompt
            system_prompt: Optional system context
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional model-specific parameters
            
        Yields:
            Tokens as they are generated
        """
        pass
    
    def is_available(self) -> bool:
        """Check if model is available"""
        return True


@dataclass
class ToolParameter:
    """Parameter definition for a tool"""
    name: str
    param_type: str  # 'string', 'number', 'boolean', 'object', 'array'
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolResult:
    """Result of tool execution"""
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    """
    Abstract base class for tools
    
    Implement this to add new tools for the AI to use.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description for the LLM"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """List of parameters the tool accepts"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute the tool
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            ToolResult with output or error
        """
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for the tool (OpenAI function format)"""
        properties = {}
        required = []
        
        for param in self.parameters:
            properties[param.name] = {
                "type": param.param_type,
                "description": param.description,
            }
            if param.default is not None:
                properties[param.name]["default"] = param.default
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                }
            }
        }


class NodeStatus(Enum):
    """Status of a workflow node"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowNode:
    """
    A node in the workflow graph (N8N-style)
    
    Represents a single operation in a workflow:
    - User Input
    - LLM Router
    - Model Selection
    - Tool Execution
    - Output
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    node_type: str = "action"  # 'input', 'router', 'model', 'tool', 'output', 'condition'
    description: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    status: NodeStatus = NodeStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_ms: float = 0.0
    
    # Position for visualization (N8N-style)
    position_x: int = 0
    position_y: int = 0


@dataclass
class WorkflowEdge:
    """
    An edge connecting two nodes in the workflow
    """
    source_id: str
    target_id: str
    edge_type: str = "default"  # 'default', 'success', 'failure', 'conditional'
    condition: Optional[str] = None  # For conditional edges
    label: Optional[str] = None


@dataclass
class ExecutionContext:
    """
    Context passed through workflow execution
    """
    workflow_id: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    node_outputs: Dict[str, Any] = field(default_factory=dict)  # node_id -> output
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def set_variable(self, name: str, value: Any) -> None:
        """Set a workflow variable"""
        self.variables[name] = value
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a workflow variable"""
        return self.variables.get(name, default)
    
    def set_node_output(self, node_id: str, output: Any) -> None:
        """Store output from a node"""
        self.node_outputs[node_id] = output
    
    def get_node_output(self, node_id: str) -> Optional[Any]:
        """Get output from a previous node"""
        return self.node_outputs.get(node_id)


class BaseWorkflow(ABC):
    """
    Abstract base class for workflows
    
    Workflows are directed graphs of nodes connected by edges.
    This enables N8N-style visual workflow representation.
    """
    
    def __init__(self):
        self.nodes: Dict[str, WorkflowNode] = {}
        self.edges: List[WorkflowEdge] = []
        self.entry_node_id: Optional[str] = None
    
    def add_node(self, node: WorkflowNode) -> str:
        """Add a node to the workflow"""
        self.nodes[node.id] = node
        return node.id
    
    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str = "default",
        condition: Optional[str] = None,
    ) -> None:
        """Add an edge between nodes"""
        edge = WorkflowEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            condition=condition,
        )
        self.edges.append(edge)
    
    def set_entry_node(self, node_id: str) -> None:
        """Set the entry point of the workflow"""
        self.entry_node_id = node_id
    
    def get_outgoing_edges(self, node_id: str) -> List[WorkflowEdge]:
        """Get all edges originating from a node"""
        return [e for e in self.edges if e.source_id == node_id]
    
    def get_incoming_edges(self, node_id: str) -> List[WorkflowEdge]:
        """Get all edges targeting a node"""
        return [e for e in self.edges if e.target_id == node_id]
    
    @abstractmethod
    def execute(
        self,
        context: ExecutionContext,
        on_node_start: Optional[Callable[[WorkflowNode], None]] = None,
        on_node_complete: Optional[Callable[[WorkflowNode], None]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the workflow
        
        Args:
            context: Execution context with variables
            on_node_start: Callback when node starts
            on_node_complete: Callback when node completes
            
        Returns:
            Final workflow output
        """
        pass
    
    def to_visualization(self) -> Dict[str, Any]:
        """
        Export workflow as visualization data (for N8N-style UI)
        
        Returns a structure that can be rendered by the frontend.
        """
        return {
            "nodes": [
                {
                    "id": node.id,
                    "name": node.name,
                    "type": node.node_type,
                    "description": node.description,
                    "status": node.status.value,
                    "position": {"x": node.position_x, "y": node.position_y},
                    "result": str(node.result)[:100] if node.result else None,
                    "error": node.error,
                    "execution_time_ms": node.execution_time_ms,
                }
                for node in self.nodes.values()
            ],
            "edges": [
                {
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "type": edge.edge_type,
                    "label": edge.label,
                }
                for edge in self.edges
            ],
            "entry_node": self.entry_node_id,
        }
