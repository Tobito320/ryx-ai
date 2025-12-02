# Task 2.5: WorkflowExecutor Full Implementation

**Time:** 90 min | **Priority:** HIGH | **Agent:** Claude Opus

## Objective

Complete the full implementation of `WorkflowExecutor` with the 8-step workflow pipeline, integrating `LLMRouter`, `PermissionManager`, `ToolExecutor`, and `RAGManager`. Include proper error handling, auto-recovery, and latency tracking.

## Output File(s)

- `ryx/core/workflow_orchestrator.py` (extend from Task 1.1)
- `tests/test_workflow_executor.py`

## Dependencies

- Task 1.1: `WorkflowExecutor` scaffold with `WorkflowEvent`
- Task 2.1: `LLMRouter` for model selection
- Task 2.2: `PermissionManager` for permission checks
- Task 2.3/2.4: `ToolExecutor` for tool execution
- Task 2.6: `RAGManager` for context retrieval

## Requirements

### Full 8-Step Workflow

```
User Input
    │
    ▼
┌──────────────────┐
│ 1. Input         │  Parse, validate, preprocess
│    Reception     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 2. Intent        │  Detect intent type (SEARCH, CODE, etc.)
│    Detection     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 3. Model         │  Select LLM based on intent
│    Selection     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 4. Tool          │  Determine required tools
│    Selection     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 5. Tool          │  Execute selected tools
│    Execution     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 6. RAG           │  Retrieve relevant context
│    Context       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 7. LLM           │  Generate response
│    Response      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 8. Post          │  Format, validate, finalize
│    Processing    │
└──────────────────┘
         │
         ▼
    Final Response
```

### Event Types

```python
class EventType(Enum):
    STEP_START = "step_start"
    STEP_PROGRESS = "step_progress"
    STEP_COMPLETE = "step_complete"
    STEP_ERROR = "step_error"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    LLM_TOKEN = "llm_token"
    WORKFLOW_START = "workflow_start"
    WORKFLOW_COMPLETE = "workflow_complete"
    WORKFLOW_ERROR = "workflow_error"
```

### Integration Points

| Component | Usage |
|-----------|-------|
| LLMRouter | Step 2 (intent), Step 3 (model), Step 7 (response) |
| PermissionManager | Step 5 (tool permissions) |
| ToolExecutor | Step 5 (tool execution) |
| RAGManager | Step 6 (context retrieval) |

### Error Handling & Recovery

- Each step should catch exceptions and emit error events
- Auto-recovery: retry failed steps up to 3 times
- Fallback: if model unavailable, use fallback chain
- Timeout: 60 seconds per step, 300 seconds total

## Code Template

```python
"""
Ryx AI - Workflow Executor (Full Implementation)
Streaming workflow execution with 8-step pipeline
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, AsyncGenerator
import time

from ryx.core.llm_router import LLMRouter, Intent, RoutingResult, ModelUnavailableError
from ryx.core.permission_manager import PermissionManager, PermissionDeniedError
from ryx.core.tool_executor import ToolExecutor, ToolResult, ToolExecutionError
from ryx.core.rag_manager import RAGManager


class EventType(Enum):
    """Types of workflow events."""
    STEP_START = "step_start"
    STEP_PROGRESS = "step_progress"
    STEP_COMPLETE = "step_complete"
    STEP_ERROR = "step_error"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    LLM_TOKEN = "llm_token"
    WORKFLOW_START = "workflow_start"
    WORKFLOW_COMPLETE = "workflow_complete"
    WORKFLOW_ERROR = "workflow_error"


@dataclass
class WorkflowEvent:
    """Event emitted during workflow execution."""
    event: EventType
    step: str
    node: Optional[str] = None
    message: str = ""
    latency: Optional[float] = None
    data: Optional[Dict[str, Any]] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class WorkflowState:
    """Internal state of a workflow execution."""
    user_input: str
    processed_input: str = ""
    intent: Optional[Intent] = None
    intent_confidence: float = 0.0
    selected_model: str = ""
    selected_tools: List[str] = field(default_factory=list)
    tool_results: Dict[str, ToolResult] = field(default_factory=dict)
    rag_context: str = ""
    llm_response: str = ""
    final_response: str = ""
    errors: List[str] = field(default_factory=list)
    total_latency_ms: float = 0.0


class WorkflowExecutor:
    """
    Executes Ryx AI workflows with streaming events.
    
    Integrates:
        - LLMRouter for intent detection and model selection
        - PermissionManager for operation permissions
        - ToolExecutor for tool execution
        - RAGManager for context retrieval
    
    Example:
        executor = WorkflowExecutor()
        async for event in executor.execute("find my config files"):
            print(f"[{event.step}] {event.message}")
    """
    
    # Configuration
    MAX_RETRIES = 3
    STEP_TIMEOUT = 60.0  # seconds
    TOTAL_TIMEOUT = 300.0  # seconds
    
    def __init__(
        self,
        llm_router: Optional[LLMRouter] = None,
        permission_manager: Optional[PermissionManager] = None,
        tool_executor: Optional[ToolExecutor] = None,
        rag_manager: Optional[RAGManager] = None,
    ):
        """
        Initialize the WorkflowExecutor.
        
        Args:
            llm_router: LLM routing instance
            permission_manager: Permission management instance
            tool_executor: Tool execution instance
            rag_manager: RAG context instance
        """
        self.router = llm_router or LLMRouter()
        self.permissions = permission_manager or PermissionManager()
        self.tools = tool_executor or ToolExecutor()
        self.rag = rag_manager or RAGManager()
    
    async def execute(self, user_input: str) -> AsyncGenerator[WorkflowEvent, None]:
        """
        Execute the full workflow pipeline.
        
        Args:
            user_input: The user's input query or command
            
        Yields:
            WorkflowEvent objects for each step and sub-step
        """
        start_time = time.time()
        state = WorkflowState(user_input=user_input)
        
        # Emit workflow start
        yield WorkflowEvent(
            event=EventType.WORKFLOW_START,
            step="workflow",
            message=f"Starting workflow for: {user_input[:50]}...",
        )
        
        try:
            # Step 1: Input Reception
            async for event in self._step_with_retry(
                self.input_reception, state, "input_reception"
            ):
                yield event
            
            # Step 2: Intent Detection
            async for event in self._step_with_retry(
                self.intent_detection, state, "intent_detection"
            ):
                yield event
            
            # Step 3: Model Selection
            async for event in self._step_with_retry(
                self.model_selection, state, "model_selection"
            ):
                yield event
            
            # Step 4: Tool Selection
            async for event in self._step_with_retry(
                self.tool_selection, state, "tool_selection"
            ):
                yield event
            
            # Step 5: Tool Execution
            async for event in self._step_with_retry(
                self.tool_execution, state, "tool_execution"
            ):
                yield event
            
            # Step 6: RAG Context
            async for event in self._step_with_retry(
                self.rag_context, state, "rag_context"
            ):
                yield event
            
            # Step 7: LLM Response
            async for event in self._step_with_retry(
                self.llm_response, state, "llm_response"
            ):
                yield event
            
            # Step 8: Post Processing
            async for event in self._step_with_retry(
                self.post_processing, state, "post_processing"
            ):
                yield event
            
            # Calculate total latency
            state.total_latency_ms = (time.time() - start_time) * 1000
            
            # Emit workflow complete
            yield WorkflowEvent(
                event=EventType.WORKFLOW_COMPLETE,
                step="workflow",
                message="Workflow completed successfully",
                latency=state.total_latency_ms,
                data={"response": state.final_response},
            )
            
        except Exception as e:
            yield WorkflowEvent(
                event=EventType.WORKFLOW_ERROR,
                step="workflow",
                message=f"Workflow failed: {str(e)}",
                data={"error": str(e), "errors": state.errors},
            )
    
    async def _step_with_retry(
        self,
        step_func,
        state: WorkflowState,
        step_name: str,
    ) -> AsyncGenerator[WorkflowEvent, None]:
        """Execute a step with retry logic."""
        for attempt in range(self.MAX_RETRIES):
            try:
                async with asyncio.timeout(self.STEP_TIMEOUT):
                    async for event in step_func(state):
                        yield event
                return  # Success, exit retry loop
            except asyncio.TimeoutError:
                error_msg = f"Step {step_name} timed out (attempt {attempt + 1})"
                state.errors.append(error_msg)
                if attempt == self.MAX_RETRIES - 1:
                    yield WorkflowEvent(
                        event=EventType.STEP_ERROR,
                        step=step_name,
                        message=error_msg,
                    )
            except Exception as e:
                error_msg = f"Step {step_name} failed: {str(e)} (attempt {attempt + 1})"
                state.errors.append(error_msg)
                if attempt == self.MAX_RETRIES - 1:
                    yield WorkflowEvent(
                        event=EventType.STEP_ERROR,
                        step=step_name,
                        message=error_msg,
                    )
                    raise
    
    async def input_reception(self, state: WorkflowState) -> AsyncGenerator[WorkflowEvent, None]:
        """Step 1: Receive and preprocess user input."""
        start_time = time.time()
        
        yield WorkflowEvent(
            event=EventType.STEP_START,
            step="input_reception",
            node="input",
            message="Processing input...",
        )
        
        # Preprocess input
        state.processed_input = state.user_input.strip()
        
        # Basic validation
        if not state.processed_input:
            raise ValueError("Empty input")
        
        latency = (time.time() - start_time) * 1000
        
        yield WorkflowEvent(
            event=EventType.STEP_COMPLETE,
            step="input_reception",
            node="input",
            message=f"Input processed: {len(state.processed_input)} chars",
            latency=latency,
        )
    
    async def intent_detection(self, state: WorkflowState) -> AsyncGenerator[WorkflowEvent, None]:
        """Step 2: Detect user intent from processed input."""
        start_time = time.time()
        
        yield WorkflowEvent(
            event=EventType.STEP_START,
            step="intent_detection",
            node="intent",
            message="Detecting intent...",
        )
        
        # Use LLMRouter to detect intent
        routing_result = await self.router.route(state.processed_input)
        state.intent = routing_result.intent
        state.intent_confidence = routing_result.confidence
        
        latency = (time.time() - start_time) * 1000
        
        yield WorkflowEvent(
            event=EventType.STEP_COMPLETE,
            step="intent_detection",
            node="intent",
            message=f"Intent: {state.intent.value} (confidence: {state.intent_confidence:.2f})",
            latency=latency,
            data={"intent": state.intent.value, "confidence": state.intent_confidence},
        )
    
    async def model_selection(self, state: WorkflowState) -> AsyncGenerator[WorkflowEvent, None]:
        """Step 3: Select appropriate LLM based on intent."""
        start_time = time.time()
        
        yield WorkflowEvent(
            event=EventType.STEP_START,
            step="model_selection",
            node="model",
            message="Selecting model...",
        )
        
        # Get model from routing result (already determined in intent detection)
        routing_result = await self.router.route(state.processed_input)
        state.selected_model = routing_result.model
        
        latency = (time.time() - start_time) * 1000
        
        yield WorkflowEvent(
            event=EventType.STEP_COMPLETE,
            step="model_selection",
            node="model",
            message=f"Selected model: {state.selected_model}",
            latency=latency,
            data={"model": state.selected_model, "fallback_used": routing_result.fallback_used},
        )
    
    async def tool_selection(self, state: WorkflowState) -> AsyncGenerator[WorkflowEvent, None]:
        """Step 4: Select tools required for the task."""
        start_time = time.time()
        
        yield WorkflowEvent(
            event=EventType.STEP_START,
            step="tool_selection",
            node="tools",
            message="Selecting tools...",
        )
        
        # Select tools based on intent
        tool_map = {
            Intent.SEARCH: ["search_local", "search_web"],
            Intent.CODE: ["read_file", "edit_file"],
            Intent.CHAT: [],  # No tools needed
            Intent.SHELL: ["launch_app"],
            Intent.UNKNOWN: ["read_file"],
        }
        
        state.selected_tools = tool_map.get(state.intent, [])
        
        latency = (time.time() - start_time) * 1000
        
        yield WorkflowEvent(
            event=EventType.STEP_COMPLETE,
            step="tool_selection",
            node="tools",
            message=f"Selected {len(state.selected_tools)} tools",
            latency=latency,
            data={"tools": state.selected_tools},
        )
    
    async def tool_execution(self, state: WorkflowState) -> AsyncGenerator[WorkflowEvent, None]:
        """Step 5: Execute selected tools."""
        start_time = time.time()
        
        yield WorkflowEvent(
            event=EventType.STEP_START,
            step="tool_execution",
            node="execute",
            message=f"Executing {len(state.selected_tools)} tools...",
        )
        
        for tool_name in state.selected_tools:
            yield WorkflowEvent(
                event=EventType.TOOL_CALL,
                step="tool_execution",
                node=tool_name,
                message=f"Calling {tool_name}...",
            )
            
            try:
                # Execute tool (simplified - would parse actual params from input)
                if tool_name == "search_local":
                    result = await self.tools.search_local("*", ".")
                elif tool_name == "search_web":
                    result = await self.tools.search_web(state.processed_input)
                elif tool_name == "read_file":
                    # Would extract file path from input
                    result = ToolResult(success=True, output="", tool_name="read_file")
                else:
                    result = ToolResult(success=False, output=None, error="Unknown tool")
                
                state.tool_results[tool_name] = result
                
                yield WorkflowEvent(
                    event=EventType.TOOL_RESULT,
                    step="tool_execution",
                    node=tool_name,
                    message=f"{'✓' if result.success else '✗'} {tool_name}",
                    latency=result.latency_ms,
                    data={"success": result.success, "output": str(result.output)[:100]},
                )
                
            except ToolExecutionError as e:
                yield WorkflowEvent(
                    event=EventType.TOOL_RESULT,
                    step="tool_execution",
                    node=tool_name,
                    message=f"✗ {tool_name}: {str(e)}",
                )
        
        latency = (time.time() - start_time) * 1000
        
        yield WorkflowEvent(
            event=EventType.STEP_COMPLETE,
            step="tool_execution",
            node="execute",
            message=f"Tool execution complete",
            latency=latency,
        )
    
    async def rag_context(self, state: WorkflowState) -> AsyncGenerator[WorkflowEvent, None]:
        """Step 6: Retrieve RAG context for the query."""
        start_time = time.time()
        
        yield WorkflowEvent(
            event=EventType.STEP_START,
            step="rag_context",
            node="rag",
            message="Retrieving context...",
        )
        
        # Get context from RAG manager
        state.rag_context = await self.rag.get_context(state.processed_input)
        
        latency = (time.time() - start_time) * 1000
        
        yield WorkflowEvent(
            event=EventType.STEP_COMPLETE,
            step="rag_context",
            node="rag",
            message=f"Retrieved {len(state.rag_context)} chars of context",
            latency=latency,
        )
    
    async def llm_response(self, state: WorkflowState) -> AsyncGenerator[WorkflowEvent, None]:
        """Step 7: Generate LLM response."""
        start_time = time.time()
        
        yield WorkflowEvent(
            event=EventType.STEP_START,
            step="llm_response",
            node="llm",
            message=f"Generating response with {state.selected_model}...",
        )
        
        # Build prompt with context
        prompt = self._build_prompt(state)
        
        # TODO: Call LLM (simplified for now)
        # In full implementation, would stream tokens
        state.llm_response = f"Response from {state.selected_model} for: {state.processed_input}"
        
        latency = (time.time() - start_time) * 1000
        
        yield WorkflowEvent(
            event=EventType.STEP_COMPLETE,
            step="llm_response",
            node="llm",
            message="Response generated",
            latency=latency,
            data={"model": state.selected_model},
        )
    
    async def post_processing(self, state: WorkflowState) -> AsyncGenerator[WorkflowEvent, None]:
        """Step 8: Post-process the LLM response."""
        start_time = time.time()
        
        yield WorkflowEvent(
            event=EventType.STEP_START,
            step="post_processing",
            node="output",
            message="Post-processing response...",
        )
        
        # Clean up and format response
        state.final_response = state.llm_response.strip()
        
        latency = (time.time() - start_time) * 1000
        
        yield WorkflowEvent(
            event=EventType.STEP_COMPLETE,
            step="post_processing",
            node="output",
            message="Response ready",
            latency=latency,
            data={"response_length": len(state.final_response)},
        )
    
    def _build_prompt(self, state: WorkflowState) -> str:
        """Build the final prompt for the LLM."""
        parts = []
        
        # Add context if available
        if state.rag_context:
            parts.append(f"Context:\n{state.rag_context}\n")
        
        # Add tool results if available
        if state.tool_results:
            parts.append("Tool Results:")
            for tool, result in state.tool_results.items():
                if result.success:
                    parts.append(f"- {tool}: {str(result.output)[:500]}")
            parts.append("")
        
        # Add user query
        parts.append(f"User Query: {state.processed_input}")
        
        return "\n".join(parts)
```

## Unit Tests

```python
import pytest
from ryx.core.workflow_orchestrator import (
    WorkflowExecutor,
    WorkflowEvent,
    EventType,
    WorkflowState,
)


@pytest.fixture
def executor():
    return WorkflowExecutor()


class TestWorkflowExecution:
    @pytest.mark.asyncio
    async def test_full_workflow(self, executor):
        events = []
        async for event in executor.execute("find python files"):
            events.append(event)
        
        # Check workflow start and complete events
        assert events[0].event == EventType.WORKFLOW_START
        assert events[-1].event == EventType.WORKFLOW_COMPLETE
    
    @pytest.mark.asyncio
    async def test_all_steps_executed(self, executor):
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
        async for event in executor.execute("test"):
            if event.event == EventType.STEP_COMPLETE:
                assert event.latency is not None
                assert event.latency >= 0


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_empty_input_error(self, executor):
        events = []
        async for event in executor.execute("   "):
            events.append(event)
        
        # Should have error event
        error_events = [e for e in events if e.event == EventType.WORKFLOW_ERROR]
        assert len(error_events) > 0
```

## Acceptance Criteria

- [ ] All 8 workflow steps implemented with real logic
- [ ] Integration with `LLMRouter` for intent detection and model selection
- [ ] Integration with `PermissionManager` for tool permissions
- [ ] Integration with `ToolExecutor` for tool execution
- [ ] Integration with `RAGManager` for context retrieval
- [ ] `EventType` enum with all event types
- [ ] `WorkflowState` dataclass for internal state tracking
- [ ] `WorkflowEvent` dataclass with all fields
- [ ] AsyncGenerator streaming for all events
- [ ] Error handling with retry logic (3 retries)
- [ ] Per-step timeout (60 seconds)
- [ ] Total workflow timeout (300 seconds)
- [ ] Latency tracking per step
- [ ] Unit tests passing

## Notes

- Extend the scaffold from Task 1.1
- The LLM call in step 7 is simplified - full implementation would stream tokens
- Tool selection is simplified - full implementation would use LLM to determine tools
- State is passed through all steps for data sharing
- Each step emits START and COMPLETE events minimum
