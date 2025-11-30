"""
RYX Core - Core Abstraction Layer

Provides clean abstractions for:
- Permission decorators (Level 1-2-3)
- Model routing interfaces
- Workflow orchestration
- Tool registration
"""

from .permissions import (
    permission_level,
    requires_safe,
    requires_modify,
    requires_destroy,
    PermissionContext,
    check_permission,
)

from .interfaces import (
    BaseModel,
    BaseTool,
    BaseWorkflow,
    WorkflowNode,
    WorkflowEdge,
    ExecutionContext,
)

from .router import (
    IntelligentRouter,
    RouteDecision,
    ModelCapability,
)

from .workflow import (
    WorkflowEngine,
    WorkflowState,
    NodeStatus,
    ExecutionEvent,
)

__all__ = [
    # Permissions
    "permission_level",
    "requires_safe",
    "requires_modify", 
    "requires_destroy",
    "PermissionContext",
    "check_permission",
    
    # Interfaces
    "BaseModel",
    "BaseTool",
    "BaseWorkflow",
    "WorkflowNode",
    "WorkflowEdge",
    "ExecutionContext",
    
    # Router
    "IntelligentRouter",
    "RouteDecision",
    "ModelCapability",
    
    # Workflow
    "WorkflowEngine",
    "WorkflowState",
    "NodeStatus",
    "ExecutionEvent",
]

__version__ = "0.1.0"
