"""
Ryx AI - Workflow Executor
Streaming workflow execution with 8-step pipeline
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

from datetime import datetime


class EventType(str, Enum):
    """Event types for workflow execution."""

    WORKFLOW_START = "workflow_start"
    WORKFLOW_COMPLETE = "workflow_complete"
    WORKFLOW_ERROR = "workflow_error"
    STEP_START = "step_start"
    STEP_COMPLETE = "step_complete"
    STEP_ERROR = "step_error"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    LLM_TOKEN = "llm_token"


@dataclass
class WorkflowEvent:
    """
    Event emitted during workflow execution.

    Attributes:
        event: Event type (step_start, step_complete, error, etc.)
        step: Current workflow step name
        node: Associated node identifier
        message: Human-readable message
        latency: Time taken in milliseconds
        data: Additional event data
        timestamp: When the event was created
    """

    event: str
    step: str
    node: Optional[str] = None
    message: str = ""
    latency: Optional[float] = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class WorkflowState:
    """Internal state for workflow execution."""

    user_input: str = ""
    processed_input: str = ""
    intent: str = "unknown"
    intent_confidence: float = 0.0
    selected_model: str = "mistral:7b"
    selected_tools: List[str] = field(default_factory=list)
    tool_results: Dict[str, Any] = field(default_factory=dict)
    rag_context: str = ""
    llm_response: str = ""
    final_response: str = ""
    errors: List[str] = field(default_factory=list)


class WorkflowExecutor:
    """
    Executes Ryx AI workflows with streaming events.

    The workflow consists of 8 steps:
    1. Input Reception - Parse and validate user input
    2. Intent Detection - Classify user intent
    3. Model Selection - Choose appropriate LLM
    4. Tool Selection - Determine required tools
    5. Tool Execution - Run selected tools
    6. RAG Context - Retrieve relevant context
    7. LLM Response - Generate response
    8. Post Processing - Format and finalize output
    """

    # Timeouts
    STEP_TIMEOUT = 60.0  # seconds per step
    TOTAL_TIMEOUT = 300.0  # seconds total
    MAX_RETRIES = 3

    def __init__(self) -> None:
        """Initialize the WorkflowExecutor."""
        # Lazy imports to avoid circular dependencies
        self._router = None
        self._tools = None
        self._rag = None

    @property
    def router(self):
        """Lazy load LLM router."""
        if self._router is None:
            from ryx.core.llm_router import LLMRouter

            self._router = LLMRouter()
        return self._router

    @property
    def tools(self):
        """Lazy load tool executor."""
        if self._tools is None:
            from ryx.core.tool_executor import ToolExecutor

            self._tools = ToolExecutor()
        return self._tools

    @property
    def rag(self):
        """Lazy load RAG manager."""
        if self._rag is None:
            from ryx.core.rag_manager import RAGManager

            self._rag = RAGManager()
        return self._rag

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

        yield WorkflowEvent(
            event=EventType.WORKFLOW_START,
            step="workflow",
            message="Starting workflow execution",
            data={"input": user_input[:100]},
        )

        try:
            # Validate input
            if not user_input or not user_input.strip():
                yield WorkflowEvent(
                    event=EventType.WORKFLOW_ERROR,
                    step="workflow",
                    message="Empty input provided",
                )
                return

            # Step 1: Input Reception
            async for event in self.input_reception(state):
                yield event

            # Step 2: Intent Detection
            async for event in self.intent_detection(state):
                yield event

            # Step 3: Model Selection
            async for event in self.model_selection(state):
                yield event

            # Step 4: Tool Selection
            async for event in self.tool_selection(state):
                yield event

            # Step 5: Tool Execution
            async for event in self.tool_execution(state):
                yield event

            # Step 6: RAG Context
            async for event in self.rag_context(state):
                yield event

            # Step 7: LLM Response
            async for event in self.llm_response(state):
                yield event

            # Step 8: Post Processing
            async for event in self.post_processing(state):
                yield event

            total_latency = (time.time() - start_time) * 1000

            yield WorkflowEvent(
                event=EventType.WORKFLOW_COMPLETE,
                step="workflow",
                message="Workflow completed successfully",
                latency=total_latency,
                data={
                    "response": (
                        state.final_response[:500] if state.final_response else ""
                    )
                },
            )

        except asyncio.TimeoutError:
            yield WorkflowEvent(
                event=EventType.WORKFLOW_ERROR,
                step="workflow",
                message="Workflow timed out",
            )
        except Exception as e:
            yield WorkflowEvent(
                event=EventType.WORKFLOW_ERROR,
                step="workflow",
                message=f"Workflow error: {str(e)}",
                data={"error": str(e)},
            )

    async def input_reception(
        self, state: WorkflowState
    ) -> AsyncGenerator[WorkflowEvent, None]:
        """
        Step 1: Receive and preprocess user input.

        Args:
            state: Workflow state object

        Yields:
            WorkflowEvent objects for input processing
        """
        start_time = time.time()

        yield WorkflowEvent(
            event=EventType.STEP_START,
            step="input_reception",
            node="input",
            message="Processing user input...",
        )

        # Clean and normalize input
        state.processed_input = state.user_input.strip()

        latency = (time.time() - start_time) * 1000

        yield WorkflowEvent(
            event=EventType.STEP_COMPLETE,
            step="input_reception",
            node="input",
            message=f"Input processed: {len(state.processed_input)} chars",
            latency=latency,
            data={"processed_length": len(state.processed_input)},
        )

    async def intent_detection(
        self, state: WorkflowState
    ) -> AsyncGenerator[WorkflowEvent, None]:
        """
        Step 2: Detect user intent from processed input.

        Args:
            state: Workflow state object

        Yields:
            WorkflowEvent objects for intent detection
        """
        start_time = time.time()

        yield WorkflowEvent(
            event=EventType.STEP_START,
            step="intent_detection",
            node="intent",
            message="Detecting intent...",
        )

        # Use router for intent detection
        try:
            intent, confidence = self.router._detect_intent(state.processed_input)
            state.intent = intent.value
            state.intent_confidence = confidence
        except Exception:
            state.intent = "unknown"
            state.intent_confidence = 0.0

        latency = (time.time() - start_time) * 1000

        yield WorkflowEvent(
            event=EventType.STEP_COMPLETE,
            step="intent_detection",
            node="intent",
            message=f"Intent: {state.intent} (confidence: {state.intent_confidence:.2f})",
            latency=latency,
            data={"intent": state.intent, "confidence": state.intent_confidence},
        )

    async def model_selection(
        self, state: WorkflowState
    ) -> AsyncGenerator[WorkflowEvent, None]:
        """
        Step 3: Select appropriate LLM based on intent.

        Args:
            state: Workflow state object

        Yields:
            WorkflowEvent objects for model selection
        """
        start_time = time.time()

        yield WorkflowEvent(
            event=EventType.STEP_START,
            step="model_selection",
            node="model",
            message="Selecting model...",
        )

        # Route to appropriate model
        try:
            routing_result = await self.router.route(state.processed_input)
            state.selected_model = routing_result.model
            fallback_used = routing_result.fallback_used
        except Exception:
            state.selected_model = "mistral:7b"
            fallback_used = True

        latency = (time.time() - start_time) * 1000

        yield WorkflowEvent(
            event=EventType.STEP_COMPLETE,
            step="model_selection",
            node="model",
            message=f"Selected: {state.selected_model}"
            + (" (fallback)" if fallback_used else ""),
            latency=latency,
            data={"model": state.selected_model, "fallback_used": fallback_used},
        )

    async def tool_selection(
        self, state: WorkflowState
    ) -> AsyncGenerator[WorkflowEvent, None]:
        """
        Step 4: Select tools required for the task.

        Args:
            state: Workflow state object

        Yields:
            WorkflowEvent objects for tool selection
        """
        start_time = time.time()

        yield WorkflowEvent(
            event=EventType.STEP_START,
            step="tool_selection",
            node="tools",
            message="Selecting tools...",
        )

        # Select tools based on intent
        tool_map = {
            "search": ["search_local", "search_web"],
            "code": ["read_file", "edit_file"],
            "chat": [],  # No tools needed
            "shell": ["launch_app"],
            "unknown": ["read_file"],
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

    async def tool_execution(
        self, state: WorkflowState
    ) -> AsyncGenerator[WorkflowEvent, None]:
        """
        Step 5: Execute selected tools.

        Args:
            state: Workflow state object

        Yields:
            WorkflowEvent objects for each tool execution
        """
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
                    from ryx.core.tool_executor import ToolResult

                    result = ToolResult(success=True, output="", tool_name="read_file")
                else:
                    from ryx.core.tool_executor import ToolResult

                    result = ToolResult(
                        success=False,
                        output=None,
                        error="Unknown tool",
                        tool_name=tool_name,
                    )

                state.tool_results[tool_name] = result

                yield WorkflowEvent(
                    event=EventType.TOOL_RESULT,
                    step="tool_execution",
                    node=tool_name,
                    message=f"{'✓' if result.success else '✗'} {tool_name}",
                    latency=result.latency_ms,
                    data={
                        "success": result.success,
                        "output": str(result.output)[:100] if result.output else "",
                    },
                )

            except Exception as e:
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
            message="Tool execution complete",
            latency=latency,
        )

    async def rag_context(
        self, state: WorkflowState
    ) -> AsyncGenerator[WorkflowEvent, None]:
        """
        Step 6: Retrieve RAG context for the query.

        Args:
            state: Workflow state object

        Yields:
            WorkflowEvent objects for RAG processing
        """
        start_time = time.time()

        yield WorkflowEvent(
            event=EventType.STEP_START,
            step="rag_context",
            node="rag",
            message="Retrieving context...",
        )

        # Get context from RAG manager
        try:
            state.rag_context = await self.rag.get_context(state.processed_input)
        except Exception:
            state.rag_context = ""

        latency = (time.time() - start_time) * 1000

        yield WorkflowEvent(
            event=EventType.STEP_COMPLETE,
            step="rag_context",
            node="rag",
            message=f"Retrieved {len(state.rag_context)} chars of context",
            latency=latency,
        )

    async def llm_response(
        self, state: WorkflowState
    ) -> AsyncGenerator[WorkflowEvent, None]:
        """
        Step 7: Generate LLM response.

        Args:
            state: Workflow state object

        Yields:
            WorkflowEvent objects for LLM response streaming
        """
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
        state.llm_response = (
            f"Response from {state.selected_model} for: {state.processed_input}"
        )

        latency = (time.time() - start_time) * 1000

        yield WorkflowEvent(
            event=EventType.STEP_COMPLETE,
            step="llm_response",
            node="llm",
            message="Response generated",
            latency=latency,
            data={"model": state.selected_model},
        )

    async def post_processing(
        self, state: WorkflowState
    ) -> AsyncGenerator[WorkflowEvent, None]:
        """
        Step 8: Post-process the LLM response.

        Args:
            state: Workflow state object

        Yields:
            WorkflowEvent objects for post-processing
        """
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
