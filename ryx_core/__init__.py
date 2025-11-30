"""
RYX Core - Core Abstraction Layer

Provides clean abstractions for:
- Permission decorators (Level 1-2-3)
- Model routing interfaces
- Workflow orchestration
- Tool registration
- FastAPI backend with WebSocket streaming
- Typer CLI
"""

from .permissions import (
    permission_level,
    requires_safe,
    requires_modify,
    requires_destroy,
    PermissionContext,
    check_permission,
    PermissionLevel,
)

from .interfaces import (
    BaseModel,
    BaseTool,
    BaseWorkflow,
    WorkflowNode,
    WorkflowEdge,
    ExecutionContext,
    ModelCapability,
    NodeStatus,
)

from .router import (
    IntelligentRouter,
    RouteDecision,
    ModelTier,
)

from .workflow import (
    WorkflowEngine,
    WorkflowState,
    ExecutionEvent,
    SimpleWorkflow,
)

__all__ = [
    # Permissions
    "permission_level",
    "requires_safe",
    "requires_modify", 
    "requires_destroy",
    "PermissionContext",
    "check_permission",
    "PermissionLevel",
    
    # Interfaces
    "BaseModel",
    "BaseTool",
    "BaseWorkflow",
    "WorkflowNode",
    "WorkflowEdge",
    "ExecutionContext",
    "ModelCapability",
    "NodeStatus",
    
    # Router
    "IntelligentRouter",
    "RouteDecision",
    "ModelTier",
    
    # Workflow
    "WorkflowEngine",
    "WorkflowState",
    "ExecutionEvent",
    "SimpleWorkflow",
]

__version__ = "0.2.0"
