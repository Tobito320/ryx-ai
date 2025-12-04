# RyxHub Features

## Overview
RyxHub is the web interface for RYX AI, providing a modern UI for managing AI models, chat sessions, workflows, and search capabilities.

## Key Features

### 1. Dynamic Model Management

#### Features
- **Dynamic Model Discovery**: Automatically scans the vLLM models directory to discover available models
- **Model Status Checking**: Real-time status for each model (online/offline/loading)
- **Interactive Model Dialog**: Click any model in the sidebar to:
  - View model details (provider, status, model ID)
  - Check current connection status
  - Attempt to connect to the model
  - Get informative feedback about model availability

#### API Endpoints
- `GET /api/models` - List all available models (loaded + available)
- `POST /api/models/load` - Attempt to load a model
- `POST /api/models/unload` - Unload a model
- `GET /api/models/{model_id}/status` - Get status of a specific model

#### Usage
1. Open RyxHub dashboard
2. Look at the "Active Models" section in the left sidebar
3. Click on any model to open the Model Dialog
4. Check status or attempt to connect

**Note**: vLLM typically loads one model at a time. To switch models, you may need to restart the vLLM container with the desired model configuration.

---

### 2. Session Management

#### Features
- **New Session Creation**: Create new chat sessions with a clean dialog interface
- **Model Selection**: Choose which AI model to use for each session
- **Session Persistence**: Sessions are stored and can be accessed later

#### Usage
1. Click the "New Session" button in the left sidebar (under Sessions section)
2. Enter a session name
3. Select an AI model from the dropdown
4. Click "Create Session"
5. The new session will open in the Chat view automatically

---

### 3. SearXNG Integration

#### Features
- **Real-time Status Monitoring**: Dashboard widget showing SearXNG service health
- **Test Search Functionality**: Test search directly from the UI
- **Health Checks**: Automatic health monitoring with visual indicators

#### API Endpoints
- `GET /api/searxng/status` - Get SearXNG service status
- `POST /api/searxng/search` - Perform a search query

#### Usage
1. View SearXNG status on the dashboard (right side, Recent Activity section)
2. Click "Refresh" to check current status
3. Click "Test Search" to verify search functionality
4. View results in toast notifications

---

### 4. Workflow Canvas (N8N-like)

#### Features
- **Visual Workflow Editor**: N8N-inspired workflow canvas
- **Node Types**: Support for Trigger, Agent, Tool, and Output nodes
- **Add Nodes**: Interactive dialog for adding new workflow nodes
- **Node Status**: Visual indicators for idle, running, success, and error states
- **Connections**: Visualize data flow between nodes
- **Execution Controls**: Play/Pause workflow execution

#### Node Types
1. **Trigger**: Start workflow on specific events (e.g., GitHub PR, schedule)
2. **Agent**: AI agent processing (code analysis, research, etc.)
3. **Tool**: Execute specific tools (RAG search, web search, code execution)
4. **Output**: Store or display workflow results

#### Usage
1. Navigate to "Workflow" view using the view toggle
2. Click "Add Node" to open the Add Node dialog
3. Select a node type and enter a name
4. Click nodes to inspect their details in the right panel
5. Use Play/Pause buttons to control workflow execution

---

## Development

### Mock Mode
RyxHub supports mock mode for development without backend:
```bash
# Enable mock mode (default in development)
VITE_USE_MOCK_API=true npm run dev

# Use live backend
VITE_USE_MOCK_API=false VITE_RYX_API_URL=http://localhost:8420 npm run dev
```

### Building
```bash
npm install
npm run build
```

### Testing
```bash
npm run test
```

---

## Architecture

### Frontend
- **React 18** with TypeScript
- **Vite** for fast development and building
- **TanStack Query** for API state management
- **Shadcn/ui** for UI components
- **Tailwind CSS** for styling

### Backend
- **FastAPI** for REST API
- **vLLM** for model inference
- **SearXNG** for web search
- **Docker** for service orchestration

### API Service Layer
The `ryxService` provides a unified interface that automatically switches between mock and live API based on configuration.

```typescript
import { ryxService } from '@/services/ryxService';

// Use throughout the app - automatically handles mock/live mode
const models = await ryxService.listModels();
const status = await ryxService.getSearxngStatus();
```

---

## Configuration

### Environment Variables

#### Frontend (`.env`)
```bash
VITE_USE_MOCK_API=false              # Use mock API (true) or live API (false)
VITE_RYX_API_URL=http://localhost:8420  # Backend API URL
```

#### Backend
```bash
VLLM_BASE_URL=http://localhost:8001   # vLLM API URL
SEARXNG_URL=http://localhost:8888     # SearXNG URL
RYX_API_PORT=8420                     # Backend API port
VLLM_MODELS_DIR=/home/tobi/vllm-models  # Models directory path
```

---

## Directory Structure

```
ryxhub/
├── src/
│   ├── components/
│   │   ├── ryxhub/           # RyxHub-specific components
│   │   │   ├── ChatView.tsx
│   │   │   ├── DashboardView.tsx
│   │   │   ├── WorkflowCanvas.tsx
│   │   │   ├── LeftSidebar.tsx
│   │   │   ├── ModelDialog.tsx
│   │   │   ├── NewSessionDialog.tsx
│   │   │   ├── AddNodeDialog.tsx
│   │   │   └── SearxngStatus.tsx
│   │   └── ui/               # Reusable UI components (Shadcn)
│   ├── lib/
│   │   └── api/
│   │       ├── client.ts     # Live API client
│   │       └── mock.ts       # Mock API for development
│   ├── services/
│   │   └── ryxService.ts     # Unified service layer
│   ├── types/
│   │   └── ryxhub.ts         # TypeScript type definitions
│   └── pages/
│       └── Index.tsx         # Main app component
```

---

## Future Enhancements

### Planned Features
- [ ] Workflow node connections editing (drag to connect)
- [ ] Workflow persistence and loading
- [ ] Real-time workflow execution monitoring
- [ ] Advanced model configuration (parameters, temperature, etc.)
- [ ] Multi-model parallel execution
- [ ] Workflow templates library
- [ ] Integration with more search engines
- [ ] Voice input/output for chat
- [ ] Advanced RAG configuration UI

---

## Troubleshooting

### Models Not Showing Up
1. Check that `VLLM_MODELS_DIR` points to the correct directory
2. Ensure models are organized in the expected structure: `/models/{size}/{category}/{model_name}`
3. Verify model directories contain `config.json` or `.safetensors` files

### SearXNG Not Working
1. Check SearXNG is running: `docker ps | grep searxng`
2. Test SearXNG directly: `curl http://localhost:8888`
3. Check SearXNG logs: `docker logs ryx-searxng`

### Backend Connection Errors
1. Verify backend is running on port 8420
2. Check CORS settings if accessing from different origin
3. Ensure vLLM is accessible at configured URL

---

## Contributing

When adding new features:
1. Add proper TypeScript types in `src/types/`
2. Implement both live and mock API versions
3. Add proper error handling with toast notifications
4. Update this documentation
5. Test in both mock and live modes

---

## License

See main repository LICENSE file.
