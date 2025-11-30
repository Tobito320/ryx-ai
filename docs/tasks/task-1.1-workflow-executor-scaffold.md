# Task 1.1: WorkflowExecutor Scaffold

**Time:** 30 min | **Priority:** HIGH | **Agent:** Copilot

## Objective

Create the `WorkflowExecutor` class scaffold in `ryx/core/workflow_orchestrator.py` with 8 async workflow step methods and a `WorkflowEvent` dataclass for streaming events.

## Output File(s)

`ryx/core/workflow_orchestrator.py`

## Requirements

1. Create a `WorkflowEvent` dataclass with the following fields:
   - `event: str` - Event type (e.g., "step_start", "step_complete", "error")
   - `step: str` - Current workflow step name
   - `node: Optional[str]` - Associated node identifier
   - `message: str` - Human-readable message
   - `latency: Optional[float]` - Time taken in milliseconds
   - `data: Optional[Dict[str, Any]]` - Additional event data

2. Create a `WorkflowExecutor` class with these 8 async methods:
   - `async def input_reception(self, user_input: str) -> AsyncGenerator[WorkflowEvent, None]`
   - `async def intent_detection(self, processed_input: str) -> AsyncGenerator[WorkflowEvent, None]`
   - `async def model_selection(self, intent: str) -> AsyncGenerator[WorkflowEvent, None]`
   - `async def tool_selection(self, intent: str, context: Dict) -> AsyncGenerator[WorkflowEvent, None]`
   - `async def tool_execution(self, tools: List[str], params: Dict) -> AsyncGenerator[WorkflowEvent, None]`
   - `async def rag_context(self, query: str) -> AsyncGenerator[WorkflowEvent, None]`
   - `async def llm_response(self, prompt: str, model: str, context: str) -> AsyncGenerator[WorkflowEvent, None]`
   - `async def post_processing(self, response: str) -> AsyncGenerator[WorkflowEvent, None]`

3. Create the main `execute` method:
   - `async def execute(self, user_input: str) -> AsyncGenerator[WorkflowEvent, None]`
   - Should call all 8 steps in order, yielding events from each

4. Add full docstrings (Google style) for all classes and methods

5. Add complete type hints for all parameters and return types

6. Structure only - methods should contain `pass` or a single placeholder `yield` statement

## Code Template

```python
"""
Ryx AI - Workflow Executor
Streaming workflow execution with 8-step pipeline
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, AsyncGenerator
from datetime import datetime


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
    """
    event: str
    step: str
    node: Optional[str] = None
    message: str = ""
    latency: Optional[float] = None
    data: Optional[Dict[str, Any]] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


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
    
    def __init__(self):
        """Initialize the WorkflowExecutor."""
        pass
    
    async def execute(self, user_input: str) -> AsyncGenerator[WorkflowEvent, None]:
        """
        Execute the full workflow pipeline.
        
        Args:
            user_input: The user's input query or command
            
        Yields:
            WorkflowEvent objects for each step and sub-step
        """
        # TODO: Implement full workflow orchestration
        yield WorkflowEvent(event="start", step="workflow", message="Starting workflow")
    
    async def input_reception(self, user_input: str) -> AsyncGenerator[WorkflowEvent, None]:
        """
        Step 1: Receive and preprocess user input.
        
        Args:
            user_input: Raw user input string
            
        Yields:
            WorkflowEvent objects for input processing
        """
        pass
    
    async def intent_detection(self, processed_input: str) -> AsyncGenerator[WorkflowEvent, None]:
        """
        Step 2: Detect user intent from processed input.
        
        Args:
            processed_input: Preprocessed input string
            
        Yields:
            WorkflowEvent objects for intent detection
        """
        pass
    
    async def model_selection(self, intent: str) -> AsyncGenerator[WorkflowEvent, None]:
        """
        Step 3: Select appropriate LLM based on intent.
        
        Args:
            intent: Detected intent type
            
        Yields:
            WorkflowEvent objects for model selection
        """
        pass
    
    async def tool_selection(self, intent: str, context: Dict[str, Any]) -> AsyncGenerator[WorkflowEvent, None]:
        """
        Step 4: Select tools required for the task.
        
        Args:
            intent: Detected intent type
            context: Additional context for tool selection
            
        Yields:
            WorkflowEvent objects for tool selection
        """
        pass
    
    async def tool_execution(self, tools: List[str], params: Dict[str, Any]) -> AsyncGenerator[WorkflowEvent, None]:
        """
        Step 5: Execute selected tools.
        
        Args:
            tools: List of tool names to execute
            params: Parameters for tool execution
            
        Yields:
            WorkflowEvent objects for each tool execution
        """
        pass
    
    async def rag_context(self, query: str) -> AsyncGenerator[WorkflowEvent, None]:
        """
        Step 6: Retrieve RAG context for the query.
        
        Args:
            query: Query string for context retrieval
            
        Yields:
            WorkflowEvent objects for RAG processing
        """
        pass
    
    async def llm_response(self, prompt: str, model: str, context: str) -> AsyncGenerator[WorkflowEvent, None]:
        """
        Step 7: Generate LLM response.
        
        Args:
            prompt: The prompt to send to the LLM
            model: The model identifier to use
            context: Context to include with the prompt
            
        Yields:
            WorkflowEvent objects for LLM response streaming
        """
        pass
    
    async def post_processing(self, response: str) -> AsyncGenerator[WorkflowEvent, None]:
        """
        Step 8: Post-process the LLM response.
        
        Args:
            response: Raw LLM response
            
        Yields:
            WorkflowEvent objects for post-processing
        """
        pass
```

## Acceptance Criteria

- [ ] `WorkflowEvent` dataclass created with all 6 fields + timestamp
- [ ] `WorkflowExecutor` class created with constructor
- [ ] All 8 async step methods implemented as scaffolds
- [ ] `execute()` method that orchestrates all steps
- [ ] All methods have complete type hints
- [ ] All methods have Google-style docstrings
- [ ] File can be imported without errors (`python -c "from ryx.core.workflow_orchestrator import WorkflowExecutor"`)
- [ ] No implementation logic (structure only)

## Notes

- This is a scaffold task - do NOT implement business logic
- The existing `workflow_orchestrator.py` file can be extended or replaced
- Ensure AsyncGenerator is imported from typing
- Use `Optional` for nullable fields
- The `data` field should use `field(default_factory=dict)` to avoid mutable default
