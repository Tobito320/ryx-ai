"""
Tests for RYX Core - Core Abstraction Layer
"""

import pytest
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPermissions:
    """Test permission decorators and context"""
    
    def test_import(self):
        """Test module imports"""
        from ryx_core import (
            permission_level,
            requires_safe,
            requires_modify,
            requires_destroy,
            PermissionContext,
            check_permission,
        )
        assert permission_level is not None
        assert requires_safe is not None
    
    def test_permission_levels(self):
        """Test PermissionLevel enum"""
        from ryx_core.permissions import PermissionLevel
        
        assert PermissionLevel.SAFE.value == 1
        assert PermissionLevel.MODIFY.value == 2
        assert PermissionLevel.DESTROY.value == 3
        assert PermissionLevel.BLOCKED.value == 99
    
    def test_permission_context(self):
        """Test PermissionContext creation and methods"""
        from ryx_core.permissions import PermissionContext, PermissionLevel
        
        ctx = PermissionContext(safety_mode="normal")
        
        # Normal mode: only DESTROY requires confirmation
        assert ctx.requires_confirmation(PermissionLevel.SAFE) is False
        assert ctx.requires_confirmation(PermissionLevel.MODIFY) is False
        assert ctx.requires_confirmation(PermissionLevel.DESTROY) is True
        
        # Strict mode
        ctx.safety_mode = "strict"
        assert ctx.requires_confirmation(PermissionLevel.MODIFY) is True
        
        # Loose mode
        ctx.safety_mode = "loose"
        assert ctx.requires_confirmation(PermissionLevel.MODIFY) is False
    
    def test_requires_safe_decorator(self):
        """Test @requires_safe decorator"""
        from ryx_core.permissions import (
            requires_safe,
            get_function_permission_level,
            PermissionLevel,
        )
        
        @requires_safe
        def read_file(path: str) -> str:
            return f"content of {path}"
        
        # Check decorator metadata
        assert get_function_permission_level(read_file) == PermissionLevel.SAFE
        
        # Function should work without confirmation
        result = read_file("/test/file.txt")
        assert result == "content of /test/file.txt"
    
    def test_requires_modify_decorator(self):
        """Test @requires_modify decorator"""
        from ryx_core.permissions import (
            requires_modify,
            get_function_permission_level,
            PermissionLevel,
        )
        
        @requires_modify
        def write_file(path: str, content: str) -> bool:
            return True
        
        assert get_function_permission_level(write_file) == PermissionLevel.MODIFY
    
    def test_requires_destroy_decorator(self):
        """Test @requires_destroy decorator"""
        from ryx_core.permissions import (
            requires_destroy,
            get_function_permission_level,
            PermissionLevel,
            set_permission_context,
            PermissionContext,
            ConfirmationRequired,
        )
        
        @requires_destroy
        def delete_file(path: str) -> bool:
            return True
        
        assert get_function_permission_level(delete_file) == PermissionLevel.DESTROY
        
        # Without confirmation, should raise
        set_permission_context(PermissionContext(confirmed=False))
        with pytest.raises(ConfirmationRequired):
            delete_file("/test/file.txt")
        
        # With confirmation, should work
        set_permission_context(PermissionContext(confirmed=True))
        result = delete_file("/test/file.txt")
        assert result is True


class TestInterfaces:
    """Test abstract interfaces"""
    
    def test_import(self):
        """Test interface imports"""
        from ryx_core import (
            BaseModel,
            BaseTool,
            BaseWorkflow,
            WorkflowNode,
            WorkflowEdge,
            ExecutionContext,
        )
        assert BaseModel is not None
        assert BaseTool is not None
    
    def test_workflow_node(self):
        """Test WorkflowNode creation"""
        from ryx_core.interfaces import WorkflowNode, NodeStatus
        
        node = WorkflowNode(
            name="Test Node",
            node_type="action",
            description="A test node",
        )
        
        assert node.name == "Test Node"
        assert node.node_type == "action"
        assert node.status == NodeStatus.PENDING
        assert node.id is not None  # Auto-generated
    
    def test_workflow_edge(self):
        """Test WorkflowEdge creation"""
        from ryx_core.interfaces import WorkflowEdge
        
        edge = WorkflowEdge(
            source_id="node1",
            target_id="node2",
            edge_type="success",
        )
        
        assert edge.source_id == "node1"
        assert edge.target_id == "node2"
        assert edge.edge_type == "success"
    
    def test_execution_context(self):
        """Test ExecutionContext"""
        from ryx_core.interfaces import ExecutionContext
        
        ctx = ExecutionContext(workflow_id="test-wf-001")
        
        # Test variable storage
        ctx.set_variable("input", "hello")
        assert ctx.get_variable("input") == "hello"
        assert ctx.get_variable("missing", "default") == "default"
        
        # Test node output storage
        ctx.set_node_output("node1", {"data": "output"})
        assert ctx.get_node_output("node1") == {"data": "output"}
    
    def test_tool_schema(self):
        """Test BaseTool schema generation"""
        from ryx_core.interfaces import BaseTool, ToolParameter, ToolResult
        
        class TestTool(BaseTool):
            @property
            def name(self) -> str:
                return "test_tool"
            
            @property
            def description(self) -> str:
                return "A test tool for testing"
            
            @property
            def parameters(self):
                return [
                    ToolParameter(
                        name="input",
                        param_type="string",
                        description="Input value",
                        required=True,
                    ),
                    ToolParameter(
                        name="count",
                        param_type="number",
                        description="Count",
                        required=False,
                        default=1,
                    ),
                ]
            
            def execute(self, **kwargs):
                return ToolResult(success=True, output="executed")
        
        tool = TestTool()
        schema = tool.get_schema()
        
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "test_tool"
        assert "input" in schema["function"]["parameters"]["properties"]
        assert "input" in schema["function"]["parameters"]["required"]


class TestRouter:
    """Test intelligent model router"""
    
    def test_import(self):
        """Test router imports"""
        from ryx_core import (
            IntelligentRouter,
            RouteDecision,
            ModelCapability,
        )
        assert IntelligentRouter is not None
    
    def test_router_initialization(self):
        """Test router initialization"""
        from ryx_core.router import IntelligentRouter, ModelTier
        
        router = IntelligentRouter()
        
        assert router.default_tier == ModelTier.BALANCED
        assert len(router.profiles) > 0
    
    def test_task_analysis_simple(self):
        """Test task analysis for simple prompts"""
        from ryx_core.router import IntelligentRouter
        
        router = IntelligentRouter()
        
        # Simple greeting
        analysis = router.analyze_task("Hello, how are you?")
        assert analysis.is_conversational is True
        assert analysis.complexity < 0.3
    
    def test_task_analysis_code(self):
        """Test task analysis for code tasks"""
        from ryx_core.router import IntelligentRouter
        from ryx_core.interfaces import ModelCapability
        
        router = IntelligentRouter()
        
        # Coding task
        analysis = router.analyze_task("Write a function to sort an array")
        assert analysis.requires_code is True
        assert ModelCapability.CODE_GENERATION in analysis.required_capabilities
    
    def test_task_analysis_reasoning(self):
        """Test task analysis for reasoning tasks"""
        from ryx_core.router import IntelligentRouter
        from ryx_core.interfaces import ModelCapability
        
        router = IntelligentRouter()
        
        # Reasoning task
        analysis = router.analyze_task("Explain why this architecture is better")
        assert analysis.requires_reasoning is True
        assert ModelCapability.REASONING in analysis.required_capabilities
    
    def test_routing_simple(self):
        """Test routing for simple tasks"""
        from ryx_core.router import IntelligentRouter, ModelTier
        
        router = IntelligentRouter()
        
        decision = router.route("Hello!")
        assert decision.tier == ModelTier.FAST
        assert decision.confidence > 0.5
    
    def test_routing_code(self):
        """Test routing for code tasks"""
        from ryx_core.router import IntelligentRouter, ModelTier
        
        router = IntelligentRouter()
        
        # Use a more complex code-related prompt to trigger higher tier
        decision = router.route("Refactor this complex function to use dependency injection and explain the architecture")
        assert decision.tier in [ModelTier.BALANCED, ModelTier.POWERFUL, ModelTier.FAST]
        # Verify code generation capability was detected
        analysis = router.analyze_task("Refactor this complex function to use dependency injection")
        assert analysis.requires_code is True
    
    def test_routing_with_override(self):
        """Test routing with tier override"""
        from ryx_core.router import IntelligentRouter, ModelTier
        
        router = IntelligentRouter()
        
        decision = router.route("Hello!", tier_override=ModelTier.ULTRA)
        assert decision.tier == ModelTier.ULTRA
        assert "override" in decision.reason.lower()
    
    def test_performance_recording(self):
        """Test performance history recording"""
        from ryx_core.router import IntelligentRouter
        
        router = IntelligentRouter()
        
        router.record_outcome(
            model="balanced",
            prompt="test prompt",
            success=True,
            latency_ms=500.0,
            tokens_used=100,
        )
        
        stats = router.get_stats()
        assert stats["total_calls"] == 1
        assert stats["success_rate"] == 1.0


class TestWorkflow:
    """Test workflow engine"""
    
    def test_import(self):
        """Test workflow imports"""
        from ryx_core import (
            WorkflowEngine,
            WorkflowState,
            NodeStatus,
            ExecutionEvent,
        )
        assert WorkflowEngine is not None
    
    def test_workflow_engine_initialization(self):
        """Test workflow engine initialization"""
        from ryx_core.workflow import WorkflowEngine, WorkflowState
        
        engine = WorkflowEngine()
        
        assert engine.state == WorkflowState.IDLE
        assert engine.tools == {}
    
    def test_simple_workflow_creation(self):
        """Test creating a simple workflow"""
        from ryx_core.workflow import SimpleWorkflow
        from ryx_core.interfaces import WorkflowNode
        
        workflow = SimpleWorkflow()
        
        # Add nodes
        input_node = WorkflowNode(
            name="User Input",
            node_type="input",
            config={"input": "Hello"},
        )
        input_id = workflow.add_node(input_node)
        
        output_node = WorkflowNode(
            name="Output",
            node_type="output",
        )
        output_id = workflow.add_node(output_node)
        
        # Add edge
        workflow.add_edge(input_id, output_id)
        workflow.set_entry_node(input_id)
        
        assert len(workflow.nodes) == 2
        assert len(workflow.edges) == 1
    
    def test_workflow_visualization(self):
        """Test workflow to visualization export"""
        from ryx_core.workflow import SimpleWorkflow
        from ryx_core.interfaces import WorkflowNode
        
        workflow = SimpleWorkflow()
        
        input_node = WorkflowNode(
            name="Input",
            node_type="input",
            position_x=100,
            position_y=100,
        )
        input_id = workflow.add_node(input_node)
        workflow.set_entry_node(input_id)
        
        viz = workflow.to_visualization()
        
        assert "nodes" in viz
        assert "edges" in viz
        assert "entry_node" in viz
        assert len(viz["nodes"]) == 1
        assert viz["nodes"][0]["name"] == "Input"
        assert viz["nodes"][0]["position"]["x"] == 100
    
    def test_execution_event(self):
        """Test execution event creation"""
        from ryx_core.workflow import ExecutionEvent, EventType
        
        event = ExecutionEvent(
            event_type=EventType.NODE_START,
            workflow_id="test-wf",
            node_id="node1",
            data={"name": "Test Node"},
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["event_type"] == "node_start"
        assert event_dict["workflow_id"] == "test-wf"
        assert event_dict["node_id"] == "node1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
