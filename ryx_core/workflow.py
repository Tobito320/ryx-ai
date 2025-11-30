"""
RYX Core - Workflow Engine

Provides workflow execution engine for N8N-style workflows:
- Node-based execution
- Event streaming for live UI updates
- Error handling and recovery
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Generator
from enum import Enum
from datetime import datetime
import time
import uuid
import logging

from .interfaces import (
    BaseWorkflow,
    WorkflowNode,
    WorkflowEdge,
    ExecutionContext,
    NodeStatus,
    BaseTool,
    ToolResult,
)

logger = logging.getLogger(__name__)


class WorkflowState(Enum):
    """Overall workflow state"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EventType(Enum):
    """Types of execution events"""
    WORKFLOW_START = "workflow_start"
    WORKFLOW_COMPLETE = "workflow_complete"
    WORKFLOW_FAILED = "workflow_failed"
    NODE_START = "node_start"
    NODE_PROGRESS = "node_progress"
    NODE_COMPLETE = "node_complete"
    NODE_FAILED = "node_failed"
    NODE_SKIPPED = "node_skipped"
    EDGE_TRAVERSED = "edge_traversed"


@dataclass
class ExecutionEvent:
    """
    Event emitted during workflow execution
    
    Use these events to update the N8N-style UI in real-time.
    """
    event_type: EventType
    workflow_id: str
    node_id: Optional[str] = None
    edge_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "event_type": self.event_type.value,
            "workflow_id": self.workflow_id,
            "node_id": self.node_id,
            "edge_id": self.edge_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class WorkflowResult:
    """Result of workflow execution"""
    success: bool
    output: Any
    error: Optional[str] = None
    node_results: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    events: List[ExecutionEvent] = field(default_factory=list)


class WorkflowEngine:
    """
    Workflow execution engine with event streaming
    
    Features:
    - Execute workflows with node-by-node tracking
    - Stream events for real-time UI updates
    - Handle errors gracefully
    - Support conditional branching
    """
    
    def __init__(
        self,
        tools: Optional[Dict[str, BaseTool]] = None,
        model_executor: Optional[Callable[[str, str], str]] = None,
    ):
        """
        Initialize the workflow engine
        
        Args:
            tools: Dictionary of available tools
            model_executor: Function to execute model prompts
        """
        self.tools = tools or {}
        self.model_executor = model_executor
        self._current_workflow: Optional[BaseWorkflow] = None
        self._state = WorkflowState.IDLE
        self._events: List[ExecutionEvent] = []
    
    @property
    def state(self) -> WorkflowState:
        """Current engine state"""
        return self._state
    
    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool for use in workflows"""
        self.tools[tool.name] = tool
    
    def execute(
        self,
        workflow: BaseWorkflow,
        context: Optional[ExecutionContext] = None,
        stream_events: bool = True,
    ) -> Generator[ExecutionEvent, None, WorkflowResult]:
        """
        Execute a workflow, yielding events as execution progresses
        
        Args:
            workflow: Workflow to execute
            context: Execution context (created if not provided)
            stream_events: Whether to yield events
            
        Yields:
            ExecutionEvent for each state change
            
        Returns:
            WorkflowResult with final output
        """
        # Initialize
        self._current_workflow = workflow
        self._state = WorkflowState.RUNNING
        self._events = []
        start_time = time.time()
        
        # Create context if not provided
        if context is None:
            context = ExecutionContext(
                workflow_id=str(uuid.uuid4())[:8]
            )
        
        # Emit workflow start
        start_event = ExecutionEvent(
            event_type=EventType.WORKFLOW_START,
            workflow_id=context.workflow_id,
            data={"nodes": len(workflow.nodes), "edges": len(workflow.edges)},
        )
        self._events.append(start_event)
        if stream_events:
            yield start_event
        
        try:
            # Get entry node
            entry_id = workflow.entry_node_id
            if not entry_id and workflow.nodes:
                entry_id = list(workflow.nodes.keys())[0]
            
            if not entry_id:
                raise ValueError("Workflow has no entry node")
            
            # Execute starting from entry node
            final_output = yield from self._execute_from_node(
                workflow, entry_id, context, stream_events
            )
            
            # Complete
            self._state = WorkflowState.COMPLETED
            
            complete_event = ExecutionEvent(
                event_type=EventType.WORKFLOW_COMPLETE,
                workflow_id=context.workflow_id,
                data={"output": str(final_output)[:500]},
            )
            self._events.append(complete_event)
            if stream_events:
                yield complete_event
            
            return WorkflowResult(
                success=True,
                output=final_output,
                node_results=context.node_outputs,
                execution_time_ms=(time.time() - start_time) * 1000,
                events=self._events,
            )
            
        except Exception as e:
            self._state = WorkflowState.FAILED
            
            fail_event = ExecutionEvent(
                event_type=EventType.WORKFLOW_FAILED,
                workflow_id=context.workflow_id,
                data={"error": str(e)},
            )
            self._events.append(fail_event)
            if stream_events:
                yield fail_event
            
            return WorkflowResult(
                success=False,
                output=None,
                error=str(e),
                node_results=context.node_outputs,
                execution_time_ms=(time.time() - start_time) * 1000,
                events=self._events,
            )
    
    def _execute_from_node(
        self,
        workflow: BaseWorkflow,
        node_id: str,
        context: ExecutionContext,
        stream_events: bool,
    ) -> Generator[ExecutionEvent, None, Any]:
        """Execute workflow starting from a specific node"""
        node = workflow.nodes.get(node_id)
        if not node:
            raise ValueError(f"Node not found: {node_id}")
        
        # Execute this node
        result = yield from self._execute_node(workflow, node, context, stream_events)
        
        # Store result
        context.set_node_output(node_id, result)
        
        # Get outgoing edges
        outgoing = workflow.get_outgoing_edges(node_id)
        
        if not outgoing:
            # Terminal node
            return result
        
        # Traverse edges
        for edge in outgoing:
            # Check condition if present
            if edge.condition and edge.edge_type == "conditional":
                if not self._evaluate_condition(edge.condition, context):
                    continue
            
            # Only traverse success/failure edges based on result
            if edge.edge_type == "success" and node.status != NodeStatus.COMPLETED:
                continue
            if edge.edge_type == "failure" and node.status != NodeStatus.FAILED:
                continue
            
            # Emit edge traversal event
            edge_event = ExecutionEvent(
                event_type=EventType.EDGE_TRAVERSED,
                workflow_id=context.workflow_id,
                edge_id=f"{edge.source_id}->{edge.target_id}",
                data={"source": edge.source_id, "target": edge.target_id},
            )
            self._events.append(edge_event)
            if stream_events:
                yield edge_event
            
            # Execute next node
            result = yield from self._execute_from_node(
                workflow, edge.target_id, context, stream_events
            )
        
        return result
    
    def _execute_node(
        self,
        workflow: BaseWorkflow,
        node: WorkflowNode,
        context: ExecutionContext,
        stream_events: bool,
    ) -> Generator[ExecutionEvent, None, Any]:
        """Execute a single node"""
        node_start_time = time.time()
        node.status = NodeStatus.RUNNING
        node.started_at = datetime.now()
        
        # Emit node start
        start_event = ExecutionEvent(
            event_type=EventType.NODE_START,
            workflow_id=context.workflow_id,
            node_id=node.id,
            data={"name": node.name, "type": node.node_type},
        )
        self._events.append(start_event)
        if stream_events:
            yield start_event
        
        try:
            result = None
            
            # Execute based on node type
            if node.node_type == "input":
                result = self._execute_input_node(node, context)
            
            elif node.node_type == "tool":
                result = self._execute_tool_node(node, context)
            
            elif node.node_type == "model":
                result = self._execute_model_node(node, context)
            
            elif node.node_type == "router":
                result = self._execute_router_node(node, context)
            
            elif node.node_type == "output":
                result = self._execute_output_node(node, context)
            
            elif node.node_type == "condition":
                result = self._execute_condition_node(node, context)
            
            else:
                # Default action node
                result = self._execute_action_node(node, context)
            
            # Success
            node.status = NodeStatus.COMPLETED
            node.result = result
            node.completed_at = datetime.now()
            node.execution_time_ms = (time.time() - node_start_time) * 1000
            
            complete_event = ExecutionEvent(
                event_type=EventType.NODE_COMPLETE,
                workflow_id=context.workflow_id,
                node_id=node.id,
                data={
                    "result": str(result)[:200] if result else None,
                    "execution_time_ms": node.execution_time_ms,
                },
            )
            self._events.append(complete_event)
            if stream_events:
                yield complete_event
            
            return result
            
        except Exception as e:
            node.status = NodeStatus.FAILED
            node.error = str(e)
            node.completed_at = datetime.now()
            node.execution_time_ms = (time.time() - node_start_time) * 1000
            
            fail_event = ExecutionEvent(
                event_type=EventType.NODE_FAILED,
                workflow_id=context.workflow_id,
                node_id=node.id,
                data={"error": str(e)},
            )
            self._events.append(fail_event)
            if stream_events:
                yield fail_event
            
            raise
    
    def _execute_input_node(
        self, node: WorkflowNode, context: ExecutionContext
    ) -> Any:
        """Execute an input node"""
        # Input nodes typically pass through user input
        return node.config.get("input") or context.get_variable("user_input")
    
    def _execute_tool_node(
        self, node: WorkflowNode, context: ExecutionContext
    ) -> Any:
        """Execute a tool node"""
        tool_name = node.config.get("tool_name")
        if not tool_name:
            raise ValueError(f"Tool node {node.id} missing tool_name config")
        
        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        
        # Get parameters, resolving any variable references
        params = {}
        for key, value in node.config.get("params", {}).items():
            if isinstance(value, str) and value.startswith("$"):
                # Variable reference
                var_name = value[1:]
                params[key] = context.get_variable(var_name)
            else:
                params[key] = value
        
        result = tool.execute(**params)
        return result.output if result.success else result.error
    
    def _execute_model_node(
        self, node: WorkflowNode, context: ExecutionContext
    ) -> Any:
        """Execute a model node"""
        if not self.model_executor:
            raise ValueError("Model executor not configured")
        
        prompt = node.config.get("prompt", "")
        system_prompt = node.config.get("system_prompt", "")
        
        # Resolve variable references in prompt
        for var_name, var_value in context.variables.items():
            prompt = prompt.replace(f"${{{var_name}}}", str(var_value))
        
        return self.model_executor(prompt, system_prompt)
    
    def _execute_router_node(
        self, node: WorkflowNode, context: ExecutionContext
    ) -> Any:
        """Execute a router node (model selection)"""
        # Router nodes analyze input and determine best model
        input_data = context.get_variable("user_input") or ""
        
        # Simple routing logic - can be enhanced
        route_result = {
            "selected_model": node.config.get("default_model", "balanced"),
            "reason": "Default routing",
        }
        
        return route_result
    
    def _execute_output_node(
        self, node: WorkflowNode, context: ExecutionContext
    ) -> Any:
        """Execute an output node"""
        # Collect all outputs from previous nodes
        output_data = {}
        for node_id, output in context.node_outputs.items():
            output_data[node_id] = output
        
        # Format output
        format_type = node.config.get("format", "raw")
        if format_type == "json":
            import json
            return json.dumps(output_data, indent=2)
        
        return output_data
    
    def _execute_condition_node(
        self, node: WorkflowNode, context: ExecutionContext
    ) -> bool:
        """Execute a condition node"""
        condition = node.config.get("condition", "true")
        return self._evaluate_condition(condition, context)
    
    def _execute_action_node(
        self, node: WorkflowNode, context: ExecutionContext
    ) -> Any:
        """Execute a generic action node"""
        # Default implementation - can be overridden
        return node.config.get("value")
    
    def _evaluate_condition(self, condition: str, context: ExecutionContext) -> bool:
        """Evaluate a condition string"""
        # Simple condition evaluation
        # In production, use a proper expression parser
        if condition.lower() == "true":
            return True
        if condition.lower() == "false":
            return False
        
        # Check variable-based conditions
        if "==" in condition:
            parts = condition.split("==")
            if len(parts) == 2:
                left = parts[0].strip()
                right = parts[1].strip().strip("'\"")
                
                if left.startswith("$"):
                    left_val = str(context.get_variable(left[1:], ""))
                else:
                    left_val = left
                
                return left_val == right
        
        return True


class SimpleWorkflow(BaseWorkflow):
    """
    Simple implementation of BaseWorkflow for basic use cases
    """
    
    def execute(
        self,
        context: ExecutionContext,
        on_node_start: Optional[Callable[[WorkflowNode], None]] = None,
        on_node_complete: Optional[Callable[[WorkflowNode], None]] = None,
    ) -> Dict[str, Any]:
        """Execute the workflow (simplified, non-streaming version)"""
        engine = WorkflowEngine()
        
        # Consume the generator
        result = None
        gen = engine.execute(self, context, stream_events=False)
        try:
            while True:
                event = next(gen)
                if on_node_start and event.event_type == EventType.NODE_START:
                    node = self.nodes.get(event.node_id)
                    if node:
                        on_node_start(node)
                if on_node_complete and event.event_type == EventType.NODE_COMPLETE:
                    node = self.nodes.get(event.node_id)
                    if node:
                        on_node_complete(node)
        except StopIteration as e:
            result = e.value
        
        return {
            "success": result.success if result else False,
            "output": result.output if result else None,
            "error": result.error if result else "Unknown error",
        }
