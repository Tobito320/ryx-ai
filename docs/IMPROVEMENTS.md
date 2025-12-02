# Ryx AI - Future Improvements Roadmap

**Created**: 2025-12-02
**Status**: Planning

---

## 🎯 Priority 1: Core Enhancements

### 1.1 Context Awareness System
- [ ] **Working Directory Context**: Track CWD, recent files, project type detection
- [ ] **Git Integration**: Know current branch, uncommitted changes, recent commits
- [ ] **Process Awareness**: Track running processes, detect dev servers
- [ ] **Session Memory**: Remember user preferences, common tasks across sessions
- [ ] **File Content Cache**: Cache recently viewed/edited files for quick reference

### 1.2 Tool System Enhancement
- [ ] **Tool Registry**: Formal registry with capability descriptions
- [ ] **Tool Chaining**: Allow tools to call other tools
- [ ] **Tool Sandboxing**: Safety controls for dangerous operations
- [ ] **Custom Tools**: User-defined tools via simple YAML/JSON
- [ ] **Tool Metrics**: Track success rate, latency per tool

### 1.3 Model Routing Improvements
- [ ] **Dynamic Model Selection**: Choose model based on task complexity
- [ ] **Model Warmup**: Pre-load likely models based on context
- [ ] **Fallback Chains**: Automatic fallback if primary model fails
- [ ] **Cost Tracking**: Track VRAM usage, inference time per model

---

## 🎯 Priority 2: Agent Architecture (Supervisor/Operator)

### 2.1 Two-Stage Agent System
- [ ] **Supervisor Agent**: Large model (10B+) for planning and error recovery
- [ ] **Operator Agent**: Small model (3B-7B) for fast execution
- [ ] **Plan Generation**: Structured multi-step plans
- [ ] **Status Monitoring**: Compressed status updates from operator
- [ ] **Rescue Mode**: Supervisor takeover on repeated failures

### 2.2 Agent Types
- [ ] **File Agent**: fd, rg, find operations
- [ ] **Code Agent**: Refactoring, generation, analysis
- [ ] **Web Agent**: Search, scrape, browse
- [ ] **Shell Agent**: Command execution with safety
- [ ] **RAG Agent**: Knowledge retrieval and synthesis

### 2.3 Communication Protocol
- [ ] **JSON Schema**: Formal plan/status message format
- [ ] **Event System**: Async status events
- [ ] **Timeout Handling**: Per-step timeouts with escalation
- [ ] **Error Taxonomy**: Categorized error types for smart recovery

---

## 🎯 Priority 3: UI/UX Improvements

### 3.1 Enhanced Terminal UI
- [ ] **Progress Indicators**: Spinner, progress bars for long operations
- [ ] **Live Streaming**: Token-by-token response streaming
- [ ] **Multi-pane View**: Split view for command + output
- [ ] **History Browser**: Interactive command history
- [ ] **Keyboard Shortcuts**: Vi-style navigation

### 3.2 Additional Themes
- [ ] **Tokyo Night**: Popular dark theme
- [ ] **Gruvbox**: Retro warm colors
- [ ] **Solarized**: Light/dark variants
- [ ] **Custom Theme**: User-defined color schemes

### 3.3 Output Formatting
- [ ] **Syntax Highlighting**: Code blocks with language detection
- [ ] **Markdown Rendering**: Rich markdown in terminal
- [ ] **Table Formatting**: Pretty tables for structured data
- [ ] **Image Preview**: ASCII art preview for images (optional)

---

## 🎯 Priority 4: Integration & Extensibility

### 4.1 MCP (Model Context Protocol)
- [ ] **MCP Client**: Connect to MCP servers
- [ ] **GitHub MCP**: PR, issue, code search integration
- [ ] **Filesystem MCP**: Enhanced file operations
- [ ] **Custom MCP**: User-defined MCP tools

### 4.2 External Integrations
- [ ] **tmux Integration**: Session management, pane control
- [ ] **Neovim Plugin**: Direct integration with editor
- [ ] **VS Code Extension**: Sidebar chat integration
- [ ] **Waybar Widget**: Status indicator for Hyprland

### 4.3 API & Automation
- [ ] **REST API**: HTTP API for external control
- [ ] **Unix Socket**: IPC for local automation
- [ ] **Webhook Support**: Trigger actions from external events
- [ ] **Cron Integration**: Scheduled tasks

---

## 🎯 Priority 5: Performance & Reliability

### 5.1 Caching System
- [ ] **Response Cache**: Cache common query responses
- [ ] **Embedding Cache**: Pre-computed embeddings for RAG
- [ ] **Model State Cache**: Save/restore model states
- [ ] **Cache Invalidation**: Smart cache expiry

### 5.2 Error Handling
- [ ] **Graceful Degradation**: Work without Ollama (cached responses only)
- [ ] **Retry Logic**: Exponential backoff for transient failures
- [ ] **Error Reporting**: Optional telemetry for debugging
- [ ] **Self-Healing**: Auto-restart crashed components

### 5.3 Resource Management
- [ ] **VRAM Monitoring**: Track GPU memory usage
- [ ] **Model Eviction**: Unload unused models
- [ ] **CPU Fallback**: Use CPU when VRAM exhausted
- [ ] **Batch Processing**: Queue multiple requests

---

## 🎯 Priority 6: Knowledge & Learning

### 6.1 RAG Enhancements
- [ ] **Auto-Indexing**: Index project files automatically
- [ ] **Semantic Search**: Better embedding models
- [ ] **Source Attribution**: Track where knowledge came from
- [ ] **Knowledge Graphs**: Relationship-aware retrieval

### 6.2 Learning System
- [ ] **Preference Learning**: Learn user style over time
- [ ] **Command Prediction**: Suggest likely next commands
- [ ] **Error Pattern Learning**: Avoid repeated mistakes
- [ ] **Feedback Loop**: User corrections improve future responses

### 6.3 Documentation
- [ ] **Auto-Generated Docs**: Generate docs from codebase
- [ ] **Man Page Integration**: Access system man pages
- [ ] **Arch Wiki Integration**: Direct Arch Wiki search
- [ ] **Stack Overflow Search**: Programming Q&A integration

---

## 🔧 Hardware-Specific Optimizations (5900X + 7800 XT)

### ROCm Optimization
- [ ] **GPU Layer Tuning**: Optimize layers offloaded to GPU
- [ ] **Memory Bandwidth**: Batch tokens for better throughput
- [ ] **Concurrent Inference**: Run small model while loading large
- [ ] **Flash Attention**: Enable if supported

### Model Recommendations
- [ ] **qwen2.5:3b**: Intent classification, simple queries (<100ms)
- [ ] **qwen2.5-coder:7b**: Code completion, refactoring (~500ms)
- [ ] **qwen2.5-coder:14b**: Complex reasoning, architecture (~2s)
- [ ] **Model Preloading**: Keep 3b always loaded, swap 7b/14b

---

## 📝 Implementation Notes

### Quick Wins (Can do now)
1. Add progress spinners during model inference
2. Implement response streaming
3. Add more themes
4. Basic git status awareness

### Medium Effort
1. Tool registry formalization
2. Model warmup/preloading
3. Enhanced error messages
4. Session persistence improvements

### Large Effort
1. Full supervisor/operator architecture
2. MCP integration
3. Multi-pane TUI
4. Neovim/VS Code plugins

---

## 🚀 Next Steps

1. **Stabilize Core**: Fix any bugs in current implementation
2. **Add Streaming**: Token-by-token response display
3. **Git Awareness**: Basic git status in context
4. **Progress Indicators**: Spinners for long operations
5. **Then**: Begin supervisor/operator architecture

---

*This document will be updated as features are implemented.*
