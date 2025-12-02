# Ryx AI - Supervisor/Operator Agent Architecture

**Status**: Design Document
**Created**: 2025-12-02
**Author**: Based on original idea by Tobi, refined by Copilot CLI

---

## 1. Executive Summary

This document describes a two-stage agent architecture for Ryx AI:
- **Supervisor** (10B+): Strategic planning, error recovery, task delegation
- **Operator** (3B-7B): Fast execution, tool use, iteration

The goal is to minimize large model usage (1-2 calls per task) while maintaining high task success rates through intelligent planning and fast iteration.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        USER INPUT                           │
│                    "find great wave file"                   │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     COMPLEXITY GATE                         │
│    Is this trivial? → Skip supervisor, direct to operator   │
│    Is this complex? → Route to supervisor                   │
└────────────────────────────┬────────────────────────────────┘
                             │
          ┌──────────────────┴──────────────────┐
          │ TRIVIAL                             │ COMPLEX
          ▼                                     ▼
┌─────────────────────┐            ┌─────────────────────────┐
│   FAST PATH         │            │      SUPERVISOR         │
│   (3B model)        │            │      (14B model)        │
│                     │            │                         │
│   Direct execution  │            │   1. Analyze context    │
│   No planning       │            │   2. Create plan        │
│                     │            │   3. Select operator    │
└─────────┬───────────┘            │   4. Generate prompt    │
          │                        └───────────┬─────────────┘
          │                                    │
          │                                    ▼
          │                        ┌─────────────────────────┐
          │                        │      OPERATOR           │
          │                        │      (3B-7B model)      │
          │                        │                         │
          │                        │   1. Execute plan       │
          │                        │   2. Use tools          │
          │                        │   3. Iterate/retry      │
          │                        │   4. Report status      │
          │                        └───────────┬─────────────┘
          │                                    │
          │         ┌──────────────────────────┤
          │         │ SUCCESS                  │ FAILURE (2-3x)
          │         ▼                          ▼
          │    ┌─────────┐          ┌─────────────────────┐
          │    │ RESULT  │          │ SUPERVISOR RESCUE   │
          │    │         │          │                     │
          │    └────┬────┘          │ 1. Analyze failure  │
          │         │               │ 2. Adjust plan      │
          │         │               │ 3. Retry OR takeover│
          │         │               └──────────┬──────────┘
          │         │                          │
          └─────────┴──────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                       FINAL OUTPUT                          │
│                    Result + explanations                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Component Details

### 3.1 Complexity Gate

**Purpose**: Determine if supervisor planning is needed

**Classification Heuristics** (no LLM needed):
```python
class TaskComplexity(Enum):
    TRIVIAL = "trivial"     # Direct commands: "open youtube", "time"
    SIMPLE = "simple"       # Single tool: "find file.txt", "git status"
    MODERATE = "moderate"   # Multi-step: "find and open config"
    COMPLEX = "complex"     # Reasoning: "refactor this module"

def classify_complexity(query: str, context: Context) -> TaskComplexity:
    # Rule-based classification (fast, no LLM)
    
    # Trivial patterns
    if is_website_request(query):
        return TaskComplexity.TRIVIAL
    if is_time_date_request(query):
        return TaskComplexity.TRIVIAL
    
    # Simple patterns
    if is_single_file_operation(query):
        return TaskComplexity.SIMPLE
    if is_single_tool_query(query):
        return TaskComplexity.SIMPLE
    
    # Moderate: multiple entities or steps mentioned
    if has_multiple_targets(query):
        return TaskComplexity.MODERATE
    
    # Complex: reasoning, analysis, creation
    if requires_reasoning(query):
        return TaskComplexity.COMPLEX
    
    # Default to moderate (supervisor will optimize)
    return TaskComplexity.MODERATE
```

**Routing**:
- TRIVIAL → Direct tool execution (no LLM)
- SIMPLE → Small operator only (3B)
- MODERATE → Supervisor planning + operator
- COMPLEX → Full supervisor + larger operator (7B+)

---

### 3.2 Supervisor Agent

**Model**: 14B (qwen2.5-coder:14b recommended)
**Role**: Strategic planner, error analyst, task delegator

**Called Only**:
1. Once at task start (planning)
2. Optionally on repeated failures (rescue)

**Supervisor Prompt Template**:
```
You are a task planning supervisor for Ryx AI on Arch Linux + Hyprland.

CONTEXT:
- Working directory: {cwd}
- Recent commands: {recent_commands}
- Last result: {last_result}
- Available tools: {tools}
- User language: {language}

TASK: {user_query}

INSTRUCTIONS:
1. Analyze what the user wants
2. Estimate complexity (1-5)
3. Create a step-by-step plan
4. Choose the right agent type
5. Generate an optimized prompt for the operator

OUTPUT FORMAT (JSON):
{
  "understanding": "What the user wants in one sentence",
  "complexity": 1-5,
  "confidence": 0.0-1.0,
  "plan": [
    {"step": 1, "action": "search_files", "params": {...}, "fallback": "..."},
    {"step": 2, "action": "open_file", "params": {...}, "fallback": "..."}
  ],
  "agent_type": "file|code|web|shell|rag",
  "model_size": "3b|7b|14b",
  "operator_prompt": "Precise prompt for the operator...",
  "timeout_seconds": 30,
  "max_retries": 2
}
```

---

### 3.3 Operator Agent

**Model**: 3B-7B (task-dependent)
**Role**: Fast executor, tool user, iteration

**Agent Types**:

| Type | Model | Tools | Use Case |
|------|-------|-------|----------|
| `file` | 3B | fd, rg, find, cat | File search/read |
| `code` | 7B | read, write, patch | Code changes |
| `web` | 3B | curl, scrape, search | Web operations |
| `shell` | 7B | bash (sandboxed) | System commands |
| `rag` | 3B | vector search | Knowledge retrieval |

**Operator Execution Loop**:
```python
def operator_execute(plan: Plan, context: Context) -> Result:
    for attempt in range(plan.max_retries):
        for step in plan.steps:
            try:
                result = execute_step(step, context)
                if result.success:
                    continue
                else:
                    # Try fallback
                    result = execute_step(step.fallback, context)
            except ToolError as e:
                # Log and continue to next attempt
                log_error(step, e)
                break
        
        if all_steps_succeeded():
            return Result.success(...)
    
    # All retries failed - escalate to supervisor
    return Result.failure(errors=collected_errors)
```

**Status Reporting** (to supervisor):
```json
{
  "step": 2,
  "status": "failed",
  "action": "search_files",
  "error": "No files matching 'wave' in ~/Pictures",
  "attempts": 2,
  "context": {
    "searched_paths": ["~/Pictures", "~/Downloads"],
    "patterns_tried": ["*wave*", "*Wave*"]
  }
}
```

---

### 3.4 Supervisor Rescue Mode

**Triggered**: After operator fails 2-3 times

**Rescue Prompt Template**:
```
The operator failed to complete the task.

ORIGINAL TASK: {user_query}
ORIGINAL PLAN: {plan}

FAILURE REPORT:
{failure_details}

ANALYSIS REQUEST:
1. What specifically went wrong?
2. Was the plan flawed or execution?
3. Should we: ADJUST_PLAN | CHANGE_AGENT | TAKEOVER

If ADJUST_PLAN: Provide corrected plan
If CHANGE_AGENT: Which agent type is better?
If TAKEOVER: Execute the task directly (one-shot)

OUTPUT FORMAT (JSON):
{
  "analysis": "What went wrong",
  "action": "ADJUST_PLAN|CHANGE_AGENT|TAKEOVER",
  "adjusted_plan": {...} | null,
  "new_agent": "..." | null,
  "direct_result": "..." | null
}
```

---

## 4. Data Structures

### 4.1 Core Types

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

class AgentType(Enum):
    FILE = "file"
    CODE = "code"
    WEB = "web"
    SHELL = "shell"
    RAG = "rag"

class ModelSize(Enum):
    SMALL = "3b"
    MEDIUM = "7b"
    LARGE = "14b"

@dataclass
class PlanStep:
    step: int
    action: str
    params: Dict[str, Any]
    fallback: Optional[str] = None
    timeout_seconds: int = 10

@dataclass
class Plan:
    understanding: str
    complexity: int  # 1-5
    confidence: float  # 0.0-1.0
    steps: List[PlanStep]
    agent_type: AgentType
    model_size: ModelSize
    operator_prompt: str
    timeout_seconds: int = 30
    max_retries: int = 2

@dataclass
class StepResult:
    step: int
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    duration_ms: int = 0

@dataclass
class OperatorStatus:
    step: int
    status: str  # "running", "success", "failed"
    action: str
    attempts: int
    error: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TaskResult:
    success: bool
    output: str
    plan_used: Plan
    steps_completed: int
    total_duration_ms: int
    supervisor_calls: int
    operator_iterations: int
```

### 4.2 Context Object

```python
@dataclass
class Context:
    # Current state
    cwd: str
    git_branch: Optional[str]
    git_status: Optional[str]
    
    # History
    recent_commands: List[str]
    recent_files: List[str]
    last_result: Optional[str]
    
    # User preferences
    language: str  # "de" | "en"
    editor: str
    terminal: str
    
    # Tool states
    enabled_tools: Dict[str, bool]
    
    # Session
    session_id: str
    turn_count: int
```

---

## 5. Communication Protocol

### 5.1 Message Types

```python
class MessageType(Enum):
    PLAN_REQUEST = "plan_request"
    PLAN_RESPONSE = "plan_response"
    OPERATOR_START = "operator_start"
    OPERATOR_STATUS = "operator_status"
    OPERATOR_RESULT = "operator_result"
    RESCUE_REQUEST = "rescue_request"
    RESCUE_RESPONSE = "rescue_response"

@dataclass
class Message:
    type: MessageType
    timestamp: float
    payload: Dict[str, Any]
    
    def to_json(self) -> str:
        return json.dumps({
            "type": self.type.value,
            "timestamp": self.timestamp,
            "payload": self.payload
        })
```

### 5.2 Event Flow

```
User Input
    │
    ├─► [PLAN_REQUEST] ─► Supervisor
    │                         │
    │   [PLAN_RESPONSE] ◄─────┘
    │         │
    │         ├─► [OPERATOR_START] ─► Operator
    │         │                           │
    │         │   [OPERATOR_STATUS] ◄─────┤ (periodic)
    │         │   [OPERATOR_STATUS] ◄─────┤
    │         │   [OPERATOR_STATUS] ◄─────┤
    │         │                           │
    │         │   [OPERATOR_RESULT] ◄─────┘
    │         │         │
    │         │         ├─► SUCCESS ─► Output
    │         │         │
    │         │         └─► FAILURE
    │         │               │
    │         ├─► [RESCUE_REQUEST] ─► Supervisor
    │         │                           │
    │         │   [RESCUE_RESPONSE] ◄─────┘
    │         │         │
    │         │         ├─► ADJUST_PLAN ─► Retry operator
    │         │         ├─► CHANGE_AGENT ─► New operator
    │         │         └─► TAKEOVER ─► Direct output
    │
    └─► Final Output
```

---

## 6. Module Structure

```
core/
├── agents/
│   ├── __init__.py
│   ├── base.py           # BaseAgent, AgentConfig
│   ├── supervisor.py     # SupervisorAgent
│   ├── operator.py       # OperatorAgent (base)
│   ├── file_agent.py     # FileOperatorAgent
│   ├── code_agent.py     # CodeOperatorAgent
│   ├── web_agent.py      # WebOperatorAgent
│   ├── shell_agent.py    # ShellOperatorAgent
│   └── rag_agent.py      # RAGOperatorAgent
├── planning/
│   ├── __init__.py
│   ├── complexity.py     # ComplexityGate
│   ├── planner.py        # PlanGenerator
│   └── schemas.py        # Plan, Step, Result dataclasses
├── execution/
│   ├── __init__.py
│   ├── executor.py       # TaskExecutor (orchestrates all)
│   ├── tool_runner.py    # Tool execution
│   └── status.py         # Status tracking, reporting
└── comms/
    ├── __init__.py
    ├── protocol.py       # Message types, serialization
    └── events.py         # Event bus for status updates
```

---

## 7. Implementation Plan

### Phase 1: Foundation (Week 1)
1. Create `core/agents/` directory structure
2. Implement `ComplexityGate` (rule-based, no LLM)
3. Implement `Plan` and `PlanStep` dataclasses
4. Create message protocol

### Phase 2: Supervisor (Week 2)
1. Implement `SupervisorAgent` with planning prompt
2. Add plan parsing and validation
3. Integrate with existing `RyxBrain`
4. Test plan generation quality

### Phase 3: Operators (Week 3)
1. Implement base `OperatorAgent`
2. Create `FileOperatorAgent` (fd, rg, find)
3. Create `ShellOperatorAgent` (bash)
4. Add retry logic and status reporting

### Phase 4: Rescue Mode (Week 4)
1. Implement failure detection
2. Add rescue prompt to supervisor
3. Implement plan adjustment
4. Implement direct takeover mode

### Phase 5: Integration (Week 5)
1. Wire into existing session loop
2. Add progress indicators
3. Optimize model loading
4. Performance testing

---

## 8. Optimizations

### 8.1 Latency Reduction
- **Model preloading**: Keep 3B model always loaded
- **Async planning**: Start operator while plan finalizes
- **Caching**: Cache common plans (e.g., "open youtube")

### 8.2 Token Efficiency
- **Compressed status**: Operator sends minimal updates
- **Truncated context**: Only include relevant history
- **Plan reuse**: Cache plans for similar queries

### 8.3 Failure Recovery
- **Timeout cascade**: 5s → 10s → 30s
- **Tool fallbacks**: fd → find → locate
- **Graceful degradation**: Return partial results

---

## 9. Example Walkthrough

**User Input**: `"find me the great wave file"`

### Step 1: Complexity Gate
```python
classify_complexity("find me the great wave file", context)
# → TaskComplexity.SIMPLE (single file operation)
```

### Step 2: Supervisor Planning
```json
{
  "understanding": "User wants to find a file named 'great wave'",
  "complexity": 2,
  "confidence": 0.9,
  "plan": [
    {
      "step": 1,
      "action": "search_files",
      "params": {
        "pattern": "*great*wave*",
        "paths": ["~", "~/Pictures", "~/Downloads"],
        "type": "file"
      },
      "fallback": "broaden to all home directories"
    },
    {
      "step": 2,
      "action": "present_results",
      "params": {"max_results": 10}
    }
  ],
  "agent_type": "file",
  "model_size": "3b",
  "operator_prompt": "Search for files matching 'great wave'. Try ~/Pictures first, then ~/Downloads, then ~. Use fd if available, fall back to find.",
  "timeout_seconds": 15,
  "max_retries": 2
}
```

### Step 3: Operator Execution
```
[OPERATOR_START] FileAgent started
[OPERATOR_STATUS] Step 1: Searching ~/Pictures...
[OPERATOR_STATUS] Step 1: Found 0 results, trying fallback...
[OPERATOR_STATUS] Step 1: Searching ~/Downloads...
[OPERATOR_STATUS] Step 1: Found 1 result: great_wave.jpg
[OPERATOR_STATUS] Step 2: Presenting results...
[OPERATOR_RESULT] Success: Found great_wave.jpg in ~/Downloads
```

### Step 4: Output
```
Found:
1. great_wave.jpg: ~/Downloads/great_wave.jpg

Open it? (y/n)
```

---

## 10. Comparison with Current Ryx

| Aspect | Current | New Architecture |
|--------|---------|------------------|
| LLM calls per task | 1-2 | 1-2 (same) |
| Task success rate | ~60% | Target: 90%+ |
| Complex task handling | Poor | Good |
| Error recovery | None | Automatic |
| Latency | Variable | Predictable |
| Extensibility | Limited | Plugin agents |

---

## 11. Conclusion

This architecture:
1. **Keeps LLM usage minimal** - Supervisor only called 1-2 times
2. **Enables complex tasks** - Multi-step planning with fallbacks
3. **Adds robustness** - Automatic retry and rescue
4. **Maintains speed** - Small models do iteration
5. **Is extensible** - New agent types plug in easily

The design respects your original idea while adding:
- Rule-based complexity gate (faster routing)
- Structured JSON communication (cleaner interface)
- Typed dataclasses (maintainable code)
- Phased implementation plan (incremental delivery)

---

**Next Steps**: Review this design, provide feedback, then begin Phase 1 implementation.
