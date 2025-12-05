"""
Tests for Workflow Orchestrator module.
"""

import pytest

from ryx_pkg.core.workflow_orchestrator import (
    WorkflowExecutor,
    WorkflowEvent,
    EventType,
    WorkflowState,
)


@pytest.fixture
def executor():
    """Create a workflow executor for testing."""
    return WorkflowExecutor()


class TestWorkflowExecution:
    """Tests for workflow execution."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, executor):
        """Test that full workflow executes."""
        events = []
        async for event in executor.execute("find python files"):
            events.append(event)
        
        # Check workflow start and complete events
        assert events[0].event == EventType.WORKFLOW_START
        assert events[-1].event == EventType.WORKFLOW_COMPLETE
    
    @pytest.mark.asyncio
    async def test_all_steps_executed(self, executor):
        """Test that all steps are executed."""
        steps = set()
        async for event in executor.execute("test query"):
            if event.event == EventType.STEP_COMPLETE:
                steps.add(event.step)
        
        expected_steps = {
            "input_reception",
            "intent_detection",
            "model_selection",
            "tool_selection",
            "tool_execution",
            "rag_context",
            "llm_response",
            "post_processing",
        }
        assert steps == expected_steps
    
    @pytest.mark.asyncio
    async def test_latency_tracked(self, executor):
        """Test that latency is tracked for steps."""
        async for event in executor.execute("test"):
            if event.event == EventType.STEP_COMPLETE:
                assert event.latency is not None
                assert event.latency >= 0


class TestErrorHandling:
    """Tests for error handling."""
    
    @pytest.mark.asyncio
    async def test_empty_input_error(self, executor):
        """Test empty input produces error."""
        events = []
        async for event in executor.execute("   "):
            events.append(event)
        
        # Should have error event
        error_events = [e for e in events if e.event == EventType.WORKFLOW_ERROR]
        assert len(error_events) > 0
    
    @pytest.mark.asyncio
    async def test_workflow_start_event(self, executor):
        """Test workflow starts with WORKFLOW_START event."""
        async for event in executor.execute("test"):
            assert event.event == EventType.WORKFLOW_START
            break


class TestWorkflowEvent:
    """Tests for WorkflowEvent dataclass."""
    
    def test_event_structure(self):
        """Test WorkflowEvent has expected structure."""
        event = WorkflowEvent(
            event=EventType.STEP_START,
            step="test_step",
            node="test_node",
            message="Test message",
            latency=10.5,
            data={"key": "value"},
        )
        
        assert event.event == EventType.STEP_START
        assert event.step == "test_step"
        assert event.node == "test_node"
        assert event.message == "Test message"
        assert event.latency == 10.5
        assert event.data == {"key": "value"}
        assert event.timestamp is not None
    
    def test_event_defaults(self):
        """Test WorkflowEvent default values."""
        event = WorkflowEvent(
            event=EventType.STEP_START,
            step="test",
        )
        
        assert event.node is None
        assert event.message == ""
        assert event.latency is None
        assert event.data == {}


class TestWorkflowState:
    """Tests for WorkflowState dataclass."""
    
    def test_state_defaults(self):
        """Test WorkflowState default values."""
        state = WorkflowState()
        
        assert state.user_input == ""
        assert state.processed_input == ""
        assert state.intent == "unknown"
        assert state.selected_tools == []
        assert state.tool_results == {}


class TestEventTypes:
    """Tests for EventType enum."""
    
    def test_all_event_types_defined(self):
        """Test all event types are defined."""
        expected_types = [
            "WORKFLOW_START",
            "WORKFLOW_COMPLETE",
            "WORKFLOW_ERROR",
            "STEP_START",
            "STEP_COMPLETE",
            "STEP_ERROR",
            "TOOL_CALL",
            "TOOL_RESULT",
            "LLM_TOKEN",
        ]
        
        for event_type in expected_types:
            assert hasattr(EventType, event_type)
