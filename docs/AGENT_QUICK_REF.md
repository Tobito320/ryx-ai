# 🎯 Ryx AI - Agent Quick Reference Card

> Quick reference for AI agent invocation, tech stack, and parallel execution rules

---

## Agent Invocation

### GitHub Copilot Agent

```bash
# In GitHub Issues/PRs - mention the agent
@copilot implement task 1.1
@ryx-ai create the FastAPI endpoints from task 1.3

# In VS Code - use Copilot Chat
# Press Cmd+I (Mac) or Ctrl+I (Windows/Linux)
# Type your request
```

**Best for**: Scaffolding, React components, TypeScript, boilerplate code

### Claude Opus Agent

```bash
# Via GitHub Copilot CLI
copilot chat --model claude-opus-4.5

# Then in the chat session:
> Please implement task 2.1 (LLMRouter) following the spec in docs/tasks/task-2.1-llm-router.md
```

**Best for**: Complex implementations, architecture decisions, full-stack logic, unit tests

---

## Tech Stack Summary

### Backend (Python)

| Component | Technology |
|-----------|------------|
| Framework | FastAPI |
| CLI | Typer |
| Async | asyncio, aiofiles |
| LLM Client | Ollama (via httpx) |
| Data Validation | Pydantic |
| Testing | pytest, pytest-asyncio |

### Frontend (TypeScript)

| Component | Technology |
|-----------|------------|
| Framework | React 18+ |
| Language | TypeScript (.tsx only) |
| Styling | Tailwind CSS |
| Flow Visualization | React Flow |
| State | React Hooks (useState, useEffect) |
| WebSocket | native WebSocket API |

### Theme: Dracula

```css
/* Dracula Color Palette */
--bg-primary: #282a36;      /* Background */
--bg-secondary: #44475a;    /* Current Line */
--fg-primary: #f8f8f2;      /* Foreground */
--cyan: #8be9fd;            /* Cyan (info) */
--green: #50fa7b;           /* Green (success) */
--orange: #ffb86c;          /* Orange (warning) */
--pink: #ff79c6;            /* Pink (accent) */
--purple: #bd93f9;          /* Purple (highlight) */
--red: #ff5555;             /* Red (error) */
--yellow: #f1fa8c;          /* Yellow (pending) */
```

### Models (Ollama)

| Intent | Model | Use Case |
|--------|-------|----------|
| find/search | qwen2.5:3b | Quick lookups |
| code/debug | qwen2.5-coder:14b | Code generation |
| chat/creative | gpt-oss-abliterated:20b | Creative tasks |
| shell/docker | mistral:7b | System commands |

---

## Code Standards Checklist

### Python

- [ ] Type hints on all function parameters and returns
- [ ] Docstrings on all public functions/classes (Google style)
- [ ] Async/await for I/O operations
- [ ] Custom exceptions for error handling
- [ ] Pydantic models for data validation
- [ ] Unit tests with pytest (>80% coverage)

```python
# Example
async def route_query(self, query: str, context: Optional[str] = None) -> ModelResponse:
    """
    Route a query to the appropriate LLM model.
    
    Args:
        query: The user's input query
        context: Optional context for the query
        
    Returns:
        ModelResponse with the LLM's response
        
    Raises:
        ModelUnavailableError: If no model is available
    """
    pass
```

### TypeScript/React

- [ ] Props interfaces defined for all components
- [ ] Functional components only (no class components)
- [ ] Tailwind CSS for styling (no inline styles)
- [ ] Dracula theme colors
- [ ] Event handlers typed properly
- [ ] JSDoc comments on complex functions

```typescript
// Example
interface WorkflowNodeProps {
  id: string;
  label: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  latency?: number;
  onSelect?: (id: string) => void;
}

export const WorkflowNode: React.FC<WorkflowNodeProps> = ({
  id,
  label,
  status,
  latency,
  onSelect
}) => {
  // Component implementation
};
```

---

## Parallel Execution Rules

### ✅ Can Run in Parallel

These tasks touch **different files** and have **no dependencies**:

```
Phase 1 (All together):
├── Task 1.1: workflow_orchestrator.py
├── Task 1.2: React components (*.tsx)
├── Task 1.3: FastAPI backend/main.py
└── Task 1.4: CLI cli/main.py

Phase 2 (First batch):
├── Task 2.1: llm_router.py
├── Task 2.2: permission_manager.py
└── Task 2.6: rag_manager.py

Phase 3 (First batch):
├── Task 3.1: WorkflowCanvas.tsx
├── Task 3.2: ExecutionMonitor.tsx
├── Task 3.3: ToolResults.tsx
└── Task 3.5: hyprland keybind script
```

### ❌ Must Run Sequentially

These tasks have **file conflicts** or **dependencies**:

```
Sequential Chain 1 (Same file: workflow_orchestrator.py):
Task 1.1 (scaffold) → Task 2.5 (implementation)

Sequential Chain 2 (Dependencies):
Task 2.2 (PermissionManager) → Task 2.3 (ToolExecutor part 1)
Task 2.3 → Task 2.4 (ToolExecutor part 2)

Sequential Chain 3 (Integration dependencies):
Tasks 2.1-2.4 → Task 2.5 (WorkflowExecutor needs all components)

Sequential Chain 4 (Frontend integration):
Tasks 3.1, 3.2, 3.3 → Task 3.4 (WebSocket integration)
```

---

## Task Execution Workflow

### Starting a Task

1. **Read the task file**: `docs/tasks/task-X.X-*.md`
2. **Check dependencies**: Verify prerequisite tasks are complete
3. **Create/modify files**: Follow the output file paths exactly
4. **Run linting**: `ruff check` for Python, `npm run lint` for TypeScript
5. **Run tests**: `pytest` for Python, `npm test` for TypeScript
6. **Mark complete**: Update the task file and `EXECUTION_PLAN.md`

### Task File Location

```
docs/tasks/
├── task-1.1-workflow-executor-scaffold.md
├── task-1.2-react-components-scaffold.md
├── task-1.3-fastapi-endpoints.md
├── task-1.4-typer-cli-structure.md
├── task-2.1-llm-router.md
├── task-2.2-permission-manager.md
├── task-2.3-tool-executor-part1.md
├── task-2.4-tool-executor-part2.md
├── task-2.5-workflow-executor.md
├── task-2.6-rag-manager.md
├── task-3.1-react-flow-visualization.md
├── task-3.2-execution-monitor.md
├── task-3.3-tool-results-panel.md
├── task-3.4-websocket-integration.md
└── task-3.5-hyprland-keybind.md
```

---

## Common Commands

### Python Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run linting
ruff check ryx/

# Run tests
pytest tests/ -v

# Run specific test
pytest tests/test_llm_router.py -v

# Type checking
mypy ryx/
```

### Frontend Development

```bash
# Navigate to web directory
cd ryx/interfaces/web

# Install dependencies
npm install

# Run development server
npm run dev

# Run linting
npm run lint

# Run tests
npm test

# Build for production
npm run build
```

### Ollama

```bash
# Start Ollama server
ollama serve

# List available models
ollama list

# Pull a model
ollama pull qwen2.5-coder:14b

# Test model
ollama run qwen2.5-coder:14b "Hello"
```

---

## Troubleshooting

### Agent Not Responding

1. Check if Ollama is running: `curl http://localhost:11434/api/tags`
2. Verify model is pulled: `ollama list`
3. Check logs: `tail -f ~/.config/ryx/logs/ryx.log`

### TypeScript Errors

1. Run `npm install` to ensure dependencies
2. Check `tsconfig.json` for correct settings
3. Verify Tailwind is configured in `tailwind.config.js`

### Python Import Errors

1. Ensure virtual environment is activated
2. Run `pip install -e .` for local package
3. Check `PYTHONPATH` includes project root

---

## Quick Links

- [Execution Plan](./EXECUTION_PLAN.md)
- [Architecture](./ARCHITECTURE.md)
- [Setup Guide](./SETUP.md)
- [Task Files](./tasks/)

---

*Print this card and keep it handy during development!*

*Last Updated: 2025*
