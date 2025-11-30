# 🟣 Ryx AI - Master Execution Plan

> **Goal**: Production-ready Ryx AI in 2 weeks with parallel AI agent development

---

## Timeline Overview

| Week | Focus | Agents |
|------|-------|--------|
| Week 1 (Days 1-7) | Scaffolding + Core Implementation | Copilot + Claude Opus |
| Week 2 (Days 8-14) | Frontend + Integration + Polish | Copilot + Claude Opus |

---

## Phase Breakdown

### Phase 1: Scaffolding (Days 1-2)
**Agent**: Copilot (`@copilot` or `@ryx-ai`)

Create structural scaffolds with type hints and docstrings, no implementation.

| Task | File | Time | Status |
|------|------|------|--------|
| 1.1 | `ryx/core/workflow_orchestrator.py` | 30 min | ⬜ |
| 1.2 | `ryx/interfaces/web/src/components/*.tsx` | 45 min | ⬜ |
| 1.3 | `ryx/interfaces/web/backend/main.py` | 30 min | ⬜ |
| 1.4 | `ryx/interfaces/cli/main.py` | 20 min | ⬜ |

**Parallel**: All Phase 1 tasks can run simultaneously

### Phase 2: Core Implementation (Days 3-7)
**Agent**: Claude Opus (`copilot chat --model claude-opus-4.5`)

Full implementations with tests, error handling, and integration.

| Task | File | Time | Dependencies | Status |
|------|------|------|--------------|--------|
| 2.1 | `ryx/core/llm_router.py` | 60 min | None | ⬜ |
| 2.2 | `ryx/core/permission_manager.py` | 45 min | None | ⬜ |
| 2.3 | `ryx/core/tool_executor.py` (part 1) | 45 min | 2.2 | ⬜ |
| 2.4 | `ryx/core/tool_executor.py` (part 2) | 45 min | 2.3 | ⬜ |
| 2.5 | `ryx/core/workflow_orchestrator.py` | 90 min | 1.1, 2.1-2.4 | ⬜ |
| 2.6 | `ryx/core/rag_manager.py` | 45 min | None | ⬜ |

**Parallel**: 2.1, 2.2, 2.6 can run together (different files)

### Phase 3: Frontend & Integration (Days 8-12)
**Agent**: Copilot (`@copilot` or `@ryx-ai`)

Full React components and backend integration.

| Task | File | Time | Dependencies | Status |
|------|------|------|--------------|--------|
| 3.1 | `WorkflowCanvas.tsx` | 60 min | 1.2 | ⬜ |
| 3.2 | `ExecutionMonitor.tsx` | 45 min | 1.2 | ⬜ |
| 3.3 | `ToolResults.tsx` | 30 min | 1.2 | ⬜ |
| 3.4 | WebSocket integration | 60 min | 3.1-3.3 | ⬜ |
| 3.5 | Hyprland keybind script | 20 min | None | ⬜ |

**Parallel**: 3.1, 3.2, 3.3, 3.5 can run together

### Phase 4: Polish (Days 13-14)
- Integration testing
- Bug fixes
- Documentation updates
- Performance optimization

---

## Task Checklist

### Phase 1: Scaffolding
- [ ] **Task 1.1**: WorkflowExecutor scaffold with 8 async methods
- [ ] **Task 1.2**: React component scaffolds (5 components)
- [ ] **Task 1.3**: FastAPI endpoints skeleton (5 endpoints)
- [ ] **Task 1.4**: Typer CLI structure with all commands

### Phase 2: Core Implementation
- [ ] **Task 2.1**: LLMRouter with intent detection and model routing
- [ ] **Task 2.2**: PermissionManager with 3 permission levels
- [ ] **Task 2.3**: ToolExecutor read operations (read_file, search_local, search_web)
- [ ] **Task 2.4**: ToolExecutor write operations (edit_file, create_file, launch_app)
- [ ] **Task 2.5**: WorkflowExecutor full implementation
- [ ] **Task 2.6**: RAGManager skeleton with profile loading

### Phase 3: Frontend & Integration
- [ ] **Task 3.1**: React Flow workflow visualization
- [ ] **Task 3.2**: ExecutionMonitor live event display
- [ ] **Task 3.3**: ToolResults panel with formatting
- [ ] **Task 3.4**: WebSocket integration for real-time updates
- [ ] **Task 3.5**: Hyprland keybind modal script

---

## Agent Assignment Instructions

### For Copilot Agent (`@copilot` or `@ryx-ai`)

1. Navigate to the task file in `docs/tasks/`
2. Read the requirements carefully
3. Create/modify the specified files
4. Ensure TypeScript/Python type hints are complete
5. Add docstrings to all functions/classes
6. Run linting before marking complete

**Copilot Tasks**: 1.1, 1.2, 1.3, 1.4, 3.1, 3.2, 3.3, 3.4, 3.5

### For Claude Opus (`copilot chat --model claude-opus-4.5`)

1. Navigate to the task file in `docs/tasks/`
2. Read the requirements and acceptance criteria
3. Implement full functionality with error handling
4. Write unit tests in `tests/` directory
5. Ensure all tests pass before marking complete
6. Document any design decisions

**Claude Opus Tasks**: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6

---

## Daily Standup Template

```markdown
## Day X Standup

### Completed Yesterday
- [ ] Task X.X: [Description]

### Today's Focus
- [ ] Task X.X: [Description]
- [ ] Task X.X: [Description]

### Blockers
- [List any blockers]

### Parallel Work
- Agent 1: Task X.X
- Agent 2: Task X.X
```

---

## Success Criteria

### Week 1 Complete When:
- [ ] All scaffolds created (Phase 1)
- [ ] LLMRouter working with Ollama
- [ ] PermissionManager with audit logging
- [ ] ToolExecutor with basic read/write operations
- [ ] Unit tests passing for core modules

### Week 2 Complete When:
- [ ] All React components functional
- [ ] WebSocket streaming working
- [ ] Full workflow execution pipeline
- [ ] Hyprland integration complete
- [ ] End-to-end tests passing

### Production Ready When:
- [ ] All acceptance criteria met
- [ ] No critical bugs
- [ ] Documentation complete
- [ ] Performance targets met (<500ms response time)

---

## File Structure After Completion

```
ryx/
├── core/
│   ├── workflow_orchestrator.py  # Task 1.1, 2.5
│   ├── llm_router.py             # Task 2.1
│   ├── permission_manager.py     # Task 2.2
│   ├── tool_executor.py          # Task 2.3, 2.4
│   └── rag_manager.py            # Task 2.6
├── interfaces/
│   ├── cli/
│   │   └── main.py               # Task 1.4
│   └── web/
│       ├── backend/
│       │   └── main.py           # Task 1.3
│       └── src/
│           └── components/
│               ├── WorkflowNode.tsx
│               ├── WorkflowCanvas.tsx    # Task 3.1
│               ├── ExecutionMonitor.tsx  # Task 3.2
│               ├── ToolResults.tsx       # Task 3.3
│               └── WorkflowDashboard.tsx
└── tests/
    ├── test_llm_router.py
    ├── test_permission_manager.py
    └── test_tool_executor.py
```

---

*Last Updated: 2025*
