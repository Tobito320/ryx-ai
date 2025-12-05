# RyxHub Workflow Mode & Chat Enhancements

## Overview

This document describes the new workflow mode and chat enhancements implemented in RyxHub, inspired by n8n's visual workflow editor and modern AI chat interfaces.

## Table of Contents

- [Chat Mode Enhancements](#chat-mode-enhancements)
- [Workflow Mode Features](#workflow-mode-features)
- [Workflow Templates](#workflow-templates)
- [Node Configuration](#node-configuration)
- [Visual Execution](#visual-execution)
- [Scraping Visualization](#scraping-visualization)
- [Backend Integration](#backend-integration)

---

## Chat Mode Enhancements

### Tool Toggles

Chat sessions now include a dedicated tools panel for fine-grained control over which tools the AI can use.

**Location**: Right sidebar in Chat View

**Available Tools**:
1. **Web Search** (SearXNG) - Search the web for information
2. **RAG Database** - Query indexed documents
3. **Web Scraper** - Extract content from websites
4. **File System** - Read and write local files

**Features**:
- Toggle tools on/off per session
- Visual indicators for active tools
- Instant feedback when tools are enabled/disabled
- Persistent state within session (requires backend)

**Usage**:
```typescript
// Tools can be toggled individually
handleToolToggle(toolId: string, enabled: boolean)
```

---

## Workflow Mode Features

### Visual Workflow Editor

A powerful node-based workflow editor using ReactFlow for professional-grade visual programming.

**Key Features**:
- **Drag-and-Drop**: Move nodes freely on canvas
- **Connection Drawing**: Click and drag to connect nodes
- **MiniMap**: Overview of entire workflow
- **Zoom & Pan**: Navigate large workflows
- **Background Grid**: Visual alignment aid
- **Auto-Layout**: Intelligent node positioning

### Node Types

#### 1. Trigger Nodes 🟡
Start points for workflows

**Types**:
- Manual - User-initiated
- Scheduled - Cron-based timing
- Webhook - HTTP endpoint
- File Watch - Filesystem monitoring

**Configuration**:
```json
{
  "triggerType": "schedule",
  "cron": "0 0 * * *"
}
```

#### 2. Agent Nodes 🟣
AI model interactions

**Supported Models**:
- qwen2.5-coder:14b
- mistral:7b
- deepseek-coder-v2:16b

**Configuration**:
```json
{
  "model": "qwen2.5-coder:14b",
  "prompt": "Your system prompt here",
  "temperature": 0.7
}
```

#### 3. Tool Nodes 🟢
Utility operations

**Tool Types**:
- Web Search (SearXNG)
- Web Scraper
- RAG Query
- File System
- Shell Command

**Configuration**:
```json
{
  "toolType": "websearch",
  "params": {
    "query": "search term",
    "maxResults": 10
  }
}
```

#### 4. Output Nodes 🔵
Results and data export

**Output Formats**:
- JSON
- Plain Text
- Markdown
- HTML

**Configuration**:
```json
{
  "format": "markdown",
  "destination": "/path/to/output.md"
}
```

---

## Workflow Templates

### Pre-built Workflows

#### 1. AI Code Review 🔍
**Purpose**: Multi-agent code quality and security review

**Nodes**:
- Git Push Trigger
- Code Quality Agent
- Security Audit Agent
- Result Aggregator
- PR Comment Output

**Use Case**: Automatic PR reviews with quality and security feedback

---

#### 2. Documentation Generator 📚
**Purpose**: Generate comprehensive docs from codebase

**Nodes**:
- Manual Trigger
- Codebase Scanner
- RAG Context
- Documentation Agent
- Markdown Output

**Use Case**: Auto-generate API documentation and README files

---

#### 3. Research Assistant 🔬
**Purpose**: Multi-source research synthesis

**Nodes**:
- Research Query Trigger
- Web Search Tool
- Scraper Tool
- RAG Lookup Tool
- Synthesis Agent
- Report Output

**Use Case**: Comprehensive research reports with citations

---

#### 4. Data Processing Pipeline 📊
**Purpose**: ETL workflows

**Nodes**:
- Scheduled Trigger
- Data Fetch Tool
- Transform Agent
- Database Output

**Use Case**: Daily data processing and transformations

---

#### 5. Security Scanner 🛡️
**Purpose**: Vulnerability detection and fixes

**Nodes**:
- PR Opened Trigger
- Code Scanner
- Vulnerability Detection Agent
- Fix Generator Agent
- Security Report Output

**Use Case**: Automated security audits

---

#### 6. Test Suite Generator ✅
**Purpose**: Automated test generation

**Nodes**:
- Code Commit Trigger
- Code Analyzer
- Test Generator Agent
- Test File Output

**Use Case**: Generate comprehensive unit tests

---

## Node Configuration

### Configuration Dialog

Access by double-clicking any node.

**Tabs**:

#### General
- Node name
- Description
- Enabled/disabled toggle

#### Configuration
Type-specific settings:
- **Triggers**: Type, schedule, webhook config
- **Agents**: Model selection, prompt, temperature
- **Tools**: Tool type, parameters
- **Outputs**: Format, destination

#### Advanced
- Timeout (seconds)
- Retry attempts
- Continue on error
- Custom error handler

**Example Configuration**:
```json
{
  "name": "Code Review Agent",
  "description": "Reviews code for quality issues",
  "enabled": true,
  "model": "qwen2.5-coder:14b",
  "prompt": "Review this code for quality, security, and best practices",
  "temperature": 0.7,
  "timeout": 60,
  "retries": 3,
  "continueOnError": false
}
```

---

## Visual Execution

### Real-time Feedback

**Execution Phases**:
1. **Idle** (Gray) - Node not running
2. **Running** (Purple, animated) - Node executing
3. **Success** (Green) - Completed successfully
4. **Error** (Red) - Failed with error

**Visual Elements**:
- **Animated Edges**: Flow animation during execution
- **Status Badges**: Current state of each node
- **Progress Indicators**: Per-node execution progress
- **Emoji Indicators**: Quick visual status
  - 🚀 Workflow started
  - ⚙️ Node executing
  - 🤖 Agent processing
  - 🔍 Web search
  - 🌐 Scraping
  - 📚 RAG query
  - ✅ Success
  - ❌ Error
  - ⏸️ Paused

### Execution Logs

**Location**: Right panel, Logs tab

**Features**:
- Timestamped entries
- Node-specific actions
- Color-coded messages
- Real-time updates
- Scrollable history

**Example Log**:
```
[14:32:15] 🚀 Workflow execution started
[14:32:16] ⚙️ Executing trigger: "Git Push"
[14:32:16] ✅ Completed trigger: "Git Push"
[14:32:17] ⚙️ Executing agent: "Code Quality Check"
[14:32:17] 🤖 Agent processing with qwen2.5-coder:14b...
[14:32:18] ✅ Completed agent: "Code Quality Check"
[14:32:19] 🎉 Workflow completed successfully
```

---

## Scraping Visualization

### Progress Tracking

**Location**: Right panel, Scraping tab

**Features**:
- **Per-URL Progress**: Individual scraping operations
- **Progress Bars**: Visual completion percentage
- **Item Counter**: Items extracted / Total items
- **Content Preview**: First 3 extracted items
- **Status Indicators**:
  - Pending (gray)
  - Scraping (blue, animated)
  - Success (green)
  - Error (red)

### Content Types

**Visual Indicators**:
- 📄 Text content
- 🖼️ Images
- 💻 Code blocks
- 🔗 Links

**Metadata**:
- CSS selector used
- Timestamp
- Content preview

**Example Display**:
```
┌─────────────────────────────────────────┐
│ 🌐 Scraping: example.com/article        │
│ Status: scraping                        │
│ Progress: ████████░░ 65%                │
│ Items: 6 / 10                           │
│                                         │
│ Extracted Content:                      │
│ 📄 article > h1                         │
│    "Introduction to React Flow..."     │
│                                         │
│ 📄 article > p:nth-child(2)             │
│    "React Flow is a library for..."    │
│                                         │
│ 💻 pre > code                           │
│    'import ReactFlow from "reactflow"' │
└─────────────────────────────────────────┘
```

---

## Backend Integration

### Implemented Endpoints

#### Tool Management
```http
PUT /api/sessions/:sessionId/tools
Content-Type: application/json

Request Body:
{
  "toolId": "websearch",
  "enabled": true
}

Response: 200 OK
{
  "success": true,
  "sessionId": "session-123",
  "tools": {
    "websearch": true,
    "rag": true,
    "scrape": false,
    "filesystem": true
  }
}

Error Responses:
- 404 Not Found: Session not found
- 400 Bad Request: toolId is required
```

**Status**: ✅ Implemented

---

#### Workflow Execution
```http
POST /api/workflows/:workflowId/run
Content-Type: application/json

Request Body (optional):
{
  "parameters": {}
}

Response: 200 OK
{
  "success": true,
  "runId": "run-wf-123-1733385000",
  "status": "running",
  "startedAt": "2025-12-05T14:32:15Z"
}

Error Responses:
- 404 Not Found: Workflow not found
```

**Features**:
- Creates a new workflow run
- Stores run in memory for WebSocket access
- Executes workflow asynchronously
- Broadcasts real-time updates via WebSocket

**Status**: ✅ Implemented

---

#### WebSocket: Workflow Status Stream
```javascript
// Connect to workflow execution stream
const ws = new WebSocket('ws://localhost:8420/ws/workflows/{runId}');

// Connection established
ws.onopen = () => {
  console.log('Connected to workflow stream');
};

// Receive updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  // Initial connection message
  if (data.type === 'connected') {
    console.log('Connected to run:', data.runId);
  }
  
  // Workflow status updates
  if (data.type === 'workflow_status') {
    console.log('Workflow status:', data.status);
    // status: "running" | "success" | "error"
  }
  
  // Node status updates
  if (data.type === 'node_status') {
    console.log('Node', data.nodeId, 'status:', data.status);
    // status: "running" | "success" | "error"
  }
};

// Keep connection alive
setInterval(() => {
  ws.send(JSON.stringify({ action: 'ping' }));
}, 30000);
```

**Event Types**:
1. `connected` - Initial connection confirmation
2. `workflow_status` - Overall workflow status changes
3. `node_status` - Individual node status updates
4. `pong` - Response to ping (keepalive)

**Status**: ✅ Implemented

---

#### WebSocket: Node Execution Logs
```javascript
// Connect to node execution logs
const ws = new WebSocket('ws://localhost:8420/ws/workflows/{runId}/logs');

// Receive logs
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'log') {
    console.log(`[${data.timestamp}] ${data.level}: ${data.message}`);
  }
};

/*
Log Event Structure:
{
  "type": "log",
  "level": "info" | "success" | "warning" | "error",
  "message": "Processing with qwen2.5-coder:14b...",
  "nodeId": "agent-1",  // Optional, present for node-specific logs
  "timestamp": "2025-12-05T14:32:16.123Z"
}
*/
```

**Log Levels**:
- `info` - General information
- `success` - Successful operations
- `warning` - Non-critical issues
- `error` - Errors and failures

**Status**: ✅ Implemented

---

#### WebSocket: Scraping Progress Stream
```javascript
// Connect to scraping updates
const ws = new WebSocket('ws://localhost:8420/ws/scraping/{toolId}');

// Receive progress
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'scraping_progress') {
    console.log(`Scraping ${data.url}: ${data.progress}%`);
    console.log(`Items: ${data.items.length}/${data.totalItems}`);
  }
};

/*
Progress Event Structure:
{
  "type": "scraping_progress",
  "url": "https://example.com",
  "status": "pending" | "scraping" | "success" | "error",
  "progress": 65,
  "items": [
    {
      "type": "text" | "image" | "code" | "link",
      "content": "Sample content",
      "selector": "article > p",
      "timestamp": "2025-12-05T14:32:17Z"
    }
  ],
  "totalItems": 10,
  "timestamp": "2025-12-05T14:32:17.456Z"
}
*/
```

**Scraping Statuses**:
- `pending` - Scraping queued
- `scraping` - Currently scraping
- `success` - Scraping completed
- `error` - Scraping failed

**Status**: ✅ Implemented

---

### Workflow Persistence

All workflow persistence endpoints are implemented and store data in `data/workflows/` directory.

#### List Workflows
```http
GET /api/workflows

Response: 200 OK
{
  "workflows": [
    {
      "id": "wf-1733385000",
      "name": "Code Review",
      "status": "idle" | "running" | "paused",
      "lastRun": "2m ago",
      "nodeCount": 5,
      "connectionCount": 4
    }
  ]
}
```

**Status**: ✅ Implemented

---

#### Create Workflow
```http
POST /api/workflows
Content-Type: application/json

Request Body:
{
  "name": "My Workflow",
  "nodes": [
    {
      "id": "node-1",
      "type": "trigger",
      "name": "Manual Trigger",
      "x": 100,
      "y": 100,
      "config": {}
    }
  ],
  "connections": [
    {
      "id": "conn-1",
      "from": "node-1",
      "to": "node-2"
    }
  ],
  "status": "idle"
}

Response: 200 OK
{
  "success": true,
  "workflow": {
    "id": "wf-1733385000",
    "name": "My Workflow",
    "nodes": [...],
    "connections": [...],
    "status": "idle",
    "created": "2025-12-05T14:00:00Z",
    "updated": "2025-12-05T14:00:00Z",
    "runs": []
  }
}
```

**Status**: ✅ Implemented

---

#### Get Workflow
```http
GET /api/workflows/:workflowId

Response: 200 OK
{
  "id": "wf-1733385000",
  "name": "Code Review",
  "nodes": [...],
  "connections": [...],
  "status": "idle",
  "created": "2025-12-05T14:00:00Z",
  "updated": "2025-12-05T14:32:00Z",
  "runs": [...]
}

Error Responses:
- 404 Not Found: Workflow not found
```

**Status**: ✅ Implemented

---

#### Update Workflow
```http
PUT /api/workflows/:workflowId
Content-Type: application/json

Request Body:
{
  "name": "Updated Workflow",
  "nodes": [...],
  "connections": [...],
  "status": "idle"
}

Response: 200 OK
{
  "success": true,
  "workflow": {
    "id": "wf-1733385000",
    "name": "Updated Workflow",
    ...
  }
}

Error Responses:
- 404 Not Found: Workflow not found
```

**Status**: ✅ Implemented

---

#### Delete Workflow
```http
DELETE /api/workflows/:workflowId

Response: 200 OK
{
  "success": true
}

Error Responses:
- 404 Not Found: Workflow not found
```

**Status**: ✅ Implemented

---

#### Pause Workflow
```http
POST /api/workflows/:workflowId/pause

Response: 200 OK
{
  "status": "paused"
}

Error Responses:
- 404 Not Found: Workflow not found
```

**Status**: ✅ Implemented

---

## Usage Examples

### Creating a Workflow

1. Click "Templates" button
2. Select a template or click "Add Node"
3. Drag nodes to desired positions
4. Click and drag from output to input to connect
5. Double-click nodes to configure
6. Click "Run Workflow" to execute

### Configuring Tools in Chat

1. Open a chat session
2. Look at the right sidebar
3. Toggle tools on/off as needed
4. Tools are active immediately for the session

### Monitoring Execution

1. Run a workflow
2. Watch nodes change color (idle→running→success)
3. Check the Logs tab for detailed execution
4. Switch to Scraping tab to see scraping progress

---

## Keyboard Shortcuts

### Workflow Canvas
- **Drag**: Pan canvas
- **Scroll**: Zoom in/out
- **Click**: Select node
- **Double-Click**: Configure node
- **Delete**: Remove selected node

### General
- **Ctrl+Enter**: Run workflow
- **Escape**: Close dialogs
- **Tab**: Next field in forms

---

## Troubleshooting

### Nodes Won't Connect
- Ensure connection is from output to input
- Check node types are compatible
- Verify both nodes are enabled

### Execution Stuck
- Check logs tab for errors
- Verify node configurations
- Check backend connectivity

### Scraping Not Working
- Ensure scraper tool is enabled
- Check URL accessibility
- Verify selector syntax

---

## Future Enhancements

### Planned Features
- [ ] Workflow import/export (JSON)
- [ ] Conditional branching nodes
- [ ] Loop/iteration nodes
- [ ] Workflow versioning
- [ ] Collaborative editing
- [ ] Workflow marketplace
- [ ] Custom node types
- [ ] Visual debugging

### Backend Requirements
- WebSocket implementation for real-time updates
- Workflow execution engine
- Node execution logging service
- Scraping service with progress tracking
- Workflow persistence layer

---

## Contributing

To contribute to workflow mode:

1. Create new node types in `types/ryxhub.ts`
2. Add node components to `WorkflowCanvasEnhanced.tsx`
3. Add configuration UI in `NodeConfigDialog.tsx`
4. Create templates in `WorkflowTemplates.tsx`
5. Update this documentation

---

## License

Part of the RYX AI project. See main LICENSE file.
