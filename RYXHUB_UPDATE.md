# RyxHub Update - New Features

## Summary

This update adds comprehensive functionality to RyxHub, the web interface for RYX AI, including:

1. **Dynamic Model Discovery** - Automatically scan and manage vLLM models
2. **New Session Management** - Create and manage chat sessions via UI
3. **SearXNG Integration** - Web search status monitoring and testing
4. **Workflow Canvas Enhancements** - N8N-like node management

## Changes Made

### Backend (`ryx_pkg/interfaces/web/backend/main.py`)

#### New Functionality

1. **Dynamic Model Discovery**
   ```python
   def scan_local_models() -> List[Dict[str, Any]]
   ```
   - Scans `/models/{size}/{category}/{model_name}` directory structure
   - Identifies valid models by checking for config files
   - Returns comprehensive model metadata

2. **Enhanced Model Endpoints**
   - `GET /api/models` - Now returns both loaded and available models
   - `POST /api/models/load` - Improved with proper status checking
   - `POST /api/models/unload` - Better error messaging
   - `GET /api/models/{model_id}/status` - **NEW** - Check specific model status

3. **SearXNG Integration**
   - `GET /api/searxng/status` - **NEW** - Check SearXNG health
   - `POST /api/searxng/search` - **NEW** - Perform web searches
   - Health checking with timeout handling

4. **Configuration**
   ```python
   VLLM_MODELS_DIR = os.environ.get("VLLM_MODELS_DIR", "/home/tobi/vllm-models")
   ```

### Frontend (ryxhub/)

#### New Components

1. **ModelDialog** (`src/components/ryxhub/ModelDialog.tsx`)
   - Interactive model management
   - Status checking and connection attempts
   - Real-time feedback with toast notifications
   - Displays comprehensive model information

2. **NewSessionDialog** (`src/components/ryxhub/NewSessionDialog.tsx`)
   - Session creation with model selection
   - Dynamic model loading from API
   - Input validation
   - Auto-switches to chat view on creation

3. **AddNodeDialog** (`src/components/ryxhub/AddNodeDialog.tsx`)
   - Add workflow nodes interactively
   - Support for 4 node types (Trigger, Agent, Tool, Output)
   - Live preview of node configuration

4. **SearxngStatus** (`src/components/ryxhub/SearxngStatus.tsx`)
   - Real-time SearXNG health monitoring
   - Test search functionality
   - Visual status indicators

#### Enhanced Components

1. **LeftSidebar** - Models now clickable with event dispatching
2. **WorkflowCanvas** - Add node functionality integrated
3. **DashboardView** - SearXNG status widget added
4. **Index** - Event listeners for cross-component communication

#### API Layer Updates

1. **API Client** (`src/lib/api/client.ts`)
   - Added `getModelStatus(modelId)`
   - Added `getSearxngStatus()`
   - Added `searxngSearch(query)`

2. **Mock API** (`src/lib/api/mock.ts`)
   - Full mock implementations for all new endpoints
   - Realistic data simulation

3. **Service Layer** (`src/services/ryxService.ts`)
   - Updated interface with new methods
   - Automatic fallback between mock and live API

## Usage

### Model Management

```typescript
// Check model status
const status = await ryxService.getModelStatus(modelId);

// Attempt to load model
const result = await ryxService.loadModel(modelId);
if (result.success) {
  console.log("Model loaded!");
}
```

### Session Management

```typescript
// Create new session
const session = await ryxService.createSession({
  name: "My Session",
  model: "model-id"
});
```

### SearXNG

```typescript
// Check SearXNG status
const status = await ryxService.getSearxngStatus();

// Perform search
const results = await ryxService.searxngSearch("query");
```

## Testing

### Backend Testing

Run the test script:
```bash
python test_backend_api.py
```

This tests:
- Health endpoint
- Models listing and status
- SearXNG status and search
- Session creation and listing

### Frontend Testing

```bash
cd ryxhub
npm run build  # Ensure it builds
npm run dev    # Test in development
```

### Manual Testing Checklist

- [ ] Click on models in sidebar to open ModelDialog
- [ ] Check model status via ModelDialog
- [ ] Click "New Session" to create a session
- [ ] Select model and create session
- [ ] View SearXNG status on dashboard
- [ ] Test SearXNG search functionality
- [ ] Add nodes to workflow canvas
- [ ] Play/Pause workflow execution

## Configuration

### Environment Variables

#### Backend
```bash
# Required for dynamic model discovery
VLLM_MODELS_DIR=/path/to/vllm-models

# Existing configs
VLLM_BASE_URL=http://localhost:8001
SEARXNG_URL=http://localhost:8888
RYX_API_PORT=8420
```

#### Frontend
```bash
# Development with mock API
VITE_USE_MOCK_API=true

# Production with live backend
VITE_USE_MOCK_API=false
VITE_RYX_API_URL=http://localhost:8420
```

## File Structure

```
ryx-ai/
├── ryx_pkg/interfaces/web/backend/
│   └── main.py                          # Enhanced with new endpoints
│
├── ryxhub/
│   ├── src/
│   │   ├── components/ryxhub/
│   │   │   ├── ModelDialog.tsx          # NEW
│   │   │   ├── NewSessionDialog.tsx     # NEW
│   │   │   ├── AddNodeDialog.tsx        # NEW
│   │   │   ├── SearxngStatus.tsx        # NEW
│   │   │   ├── LeftSidebar.tsx          # UPDATED
│   │   │   ├── WorkflowCanvas.tsx       # UPDATED
│   │   │   └── DashboardView.tsx        # UPDATED
│   │   ├── lib/api/
│   │   │   ├── client.ts                # UPDATED
│   │   │   └── mock.ts                  # UPDATED
│   │   ├── services/
│   │   │   └── ryxService.ts            # UPDATED
│   │   └── pages/
│   │       └── Index.tsx                # UPDATED
│   └── FEATURES.md                      # NEW - Feature documentation
│
└── test_backend_api.py                  # NEW - Backend test script
```

## Known Limitations

1. **vLLM Model Loading**: vLLM typically loads one model at a time. Dynamic switching requires container restart.
2. **Model Directory**: Models must be organized in the expected structure: `/models/{size}/{category}/{model_name}`
3. **SearXNG**: Must be running on configured URL for search functionality to work

## Future Enhancements

- [ ] Workflow node drag-and-drop connections
- [ ] Workflow persistence
- [ ] Real-time workflow execution monitoring
- [ ] Advanced model configuration UI
- [ ] Multi-model parallel execution
- [ ] Workflow templates

## Migration Notes

### Existing Users

No breaking changes - all existing functionality is preserved. New features are additive.

### New Deployments

1. Ensure `VLLM_MODELS_DIR` is set correctly
2. Verify model directory structure matches expected format
3. Ensure SearXNG is running if search functionality is needed
4. Update docker-compose.yml if needed for new environment variables

## Support

For issues or questions:
1. Check FEATURES.md in ryxhub/ directory
2. Run test_backend_api.py to diagnose backend issues
3. Check browser console for frontend errors
4. Verify environment variables are set correctly

## Credits

- UI components: [Shadcn/ui](https://ui.shadcn.com/)
- State management: [TanStack Query](https://tanstack.com/query)
- Notifications: [Sonner](https://sonner.emilkowal.ski/)

---

**Version**: 2.1.0  
**Date**: 2025-12-04  
**Status**: ✅ Tested and Ready
