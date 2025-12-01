"""
Ryx AI - FastAPI Backend
REST and WebSocket API for the Ryx AI web interface
"""

import sys
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import asyncio

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Setup project root for imports
def _setup_project_root() -> Path:
    """Find and setup project root for core module imports."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "pyproject.toml").exists() or (current / "core").is_dir():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return current

PROJECT_ROOT = _setup_project_root()
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault('RYX_PROJECT_ROOT', str(PROJECT_ROOT))


# =============================================================================
# Pydantic Models
# =============================================================================

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    model: Optional[str] = None
    stream: bool = False


class SettingsRequest(BaseModel):
    """Request model for settings endpoint."""
    theme: Optional[str] = None
    default_model: Optional[str] = None
    auto_scroll: Optional[bool] = None


class ModelInfo(BaseModel):
    """Information about an available model."""
    id: str
    name: str
    size: str
    available: bool


class ModelsResponse(BaseModel):
    """Response model for models list endpoint."""
    models: List[ModelInfo]


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str
    model_used: str
    latency_ms: float


class HistoryItem(BaseModel):
    """Single item in conversation history."""
    id: str
    timestamp: datetime
    user_message: str
    assistant_response: str
    model_used: str


class HistoryResponse(BaseModel):
    """Response model for history endpoint."""
    items: List[HistoryItem]
    total: int


class StatusResponse(BaseModel):
    """Generic status response."""
    status: str
    message: Optional[str] = None


class WorkflowInfo(BaseModel):
    """Information about a workflow."""
    name: str
    icon: str
    description: str
    category: str


class WorkflowListResponse(BaseModel):
    """Response model for workflow list endpoint."""
    workflows: List[WorkflowInfo]


class ExecuteRequest(BaseModel):
    """Request model for execute endpoint."""
    command: str
    model: Optional[str] = None


class ServiceRequest(BaseModel):
    """Request model for service management."""
    service: str


class ServiceStatusResponse(BaseModel):
    """Response model for service status."""
    service: str
    running: bool
    ports: List[str]
    pids: Optional[Dict[str, int]] = None


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Ryx AI API",
    version="2.0.0",
    description="REST and WebSocket API for Ryx AI - N8N-style workflow interface"
)

# CORS middleware for development
# NOTE: Allowing all origins for development only.
# In production, restrict to specific frontend origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Workflow Templates
# =============================================================================

WORKFLOW_TEMPLATES = [
    WorkflowInfo(
        name="Search",
        icon="🔍",
        description="Web search with SearxNG",
        category="Research"
    ),
    WorkflowInfo(
        name="Code Help",
        icon="💻",
        description="Get coding assistance",
        category="Development"
    ),
    WorkflowInfo(
        name="File Mgmt",
        icon="📁",
        description="Find and open files",
        category="System"
    ),
    WorkflowInfo(
        name="Browse",
        icon="🌐",
        description="Browse and scrape web pages",
        category="Research"
    ),
    WorkflowInfo(
        name="Chat",
        icon="💬",
        description="General conversation",
        category="Chat"
    ),
]


# =============================================================================
# REST Endpoints
# =============================================================================

@app.get("/api/models", response_model=ModelsResponse)
async def get_models() -> ModelsResponse:
    """
    Get list of available LLM models.

    Returns:
        ModelsResponse with list of available models
    """
    try:
        from core.ollama_client import OllamaClient
        client = OllamaClient()
        model_names = client.list_models()
        
        models = [
            ModelInfo(
                id=name,
                name=name.split(':')[0] if ':' in name else name,
                size=name.split(':')[1] if ':' in name else "latest",
                available=True
            )
            for name in model_names
        ]
        return ModelsResponse(models=models)
    except Exception:
        # Return empty list if Ollama is not available
        return ModelsResponse(models=[])


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Send a chat message and receive a response.

    Args:
        request: ChatRequest with message and optional model

    Returns:
        ChatResponse with AI response
    """
    start_time = time.time()
    model_name = request.model or "mistral:7b"
    
    try:
        from core.ollama_client import OllamaClient
        client = OllamaClient()
        
        result = client.generate(
            prompt=request.message,
            model=model_name,
            system="You are Ryx, a helpful AI assistant.",
            max_tokens=2048
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        if result.error:
            return ChatResponse(
                response=f"Error: {result.error}",
                model_used=model_name,
                latency_ms=latency_ms
            )
        
        return ChatResponse(
            response=result.response,
            model_used=result.model,
            latency_ms=latency_ms
        )
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return ChatResponse(
            response=f"Error connecting to Ollama: {str(e)}",
            model_used=model_name,
            latency_ms=latency_ms
        )


@app.get("/api/history", response_model=HistoryResponse)
async def get_history(
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0)
) -> HistoryResponse:
    """
    Get conversation history.

    Args:
        limit: Maximum number of items to return
        offset: Number of items to skip

    Returns:
        HistoryResponse with conversation history
    """
    try:
        from core.paths import get_data_dir
        import json
        
        history_file = get_data_dir() / "session_state.json"
        
        if not history_file.exists():
            return HistoryResponse(items=[], total=0)
        
        with open(history_file, 'r') as f:
            data = json.load(f)
        
        conversation_history = data.get('conversation_history', [])
        total = len(conversation_history)
        
        # Apply pagination
        paginated = conversation_history[offset:offset + limit]
        
        items = []
        for i, entry in enumerate(paginated):
            # Create HistoryItem from conversation history
            if entry.get('role') == 'user':
                # Find corresponding assistant response
                assistant_response = ""
                if i + 1 < len(paginated) and paginated[i + 1].get('role') == 'assistant':
                    assistant_response = paginated[i + 1].get('content', '')
                
                items.append(HistoryItem(
                    id=f"msg-{offset + i}",
                    timestamp=datetime.fromisoformat(data.get('saved_at', datetime.now().isoformat())),
                    user_message=entry.get('content', ''),
                    assistant_response=assistant_response,
                    model_used=data.get('current_tier', 'balanced')
                ))
        
        return HistoryResponse(items=items, total=total)
    except Exception:
        return HistoryResponse(items=[], total=0)


@app.post("/api/settings", response_model=StatusResponse)
async def update_settings(request: SettingsRequest) -> StatusResponse:
    """
    Update user settings.

    Args:
        request: SettingsRequest with settings to update

    Returns:
        StatusResponse indicating success/failure
    """
    try:
        from core.paths import get_config_dir
        import json
        
        config_file = get_config_dir() / "ryx_config.json"
        
        # Load existing config or create new
        config = {}
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
        
        # Update settings
        if request.theme:
            config.setdefault('ui', {})['theme'] = request.theme
        if request.default_model:
            config['default_model'] = request.default_model
        if request.auto_scroll is not None:
            config.setdefault('ui', {})['auto_scroll'] = request.auto_scroll
        
        # Save config
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        return StatusResponse(status="ok", message="Settings updated successfully")
    except Exception as e:
        return StatusResponse(status="error", message=f"Failed to update settings: {str(e)}")


@app.post("/api/workflows/list", response_model=WorkflowListResponse)
async def list_workflows() -> WorkflowListResponse:
    """
    Get list of available workflow templates.

    Returns:
        WorkflowListResponse with list of workflow templates
    """
    return WorkflowListResponse(workflows=WORKFLOW_TEMPLATES)


@app.post("/api/execute")
async def execute_command(request: ExecuteRequest) -> Dict[str, Any]:
    """
    Execute a command and return results.
    For streaming updates, use the WebSocket endpoint.

    Args:
        request: ExecuteRequest with command to execute

    Returns:
        Dict with execution results
    """
    start_time = time.time()
    steps = []
    
    try:
        # Step 1: Parse intent
        step_start = time.time()
        from core.intent_classifier import IntentClassifier
        classifier = IntentClassifier()
        intent = classifier.classify(request.command, {})
        step_latency = (time.time() - step_start) * 1000
        steps.append({
            "step": 1,
            "action": "Parse Intent",
            "status": "complete",
            "latency_ms": round(step_latency, 2),
            "data": {"intent": intent.intent_type.value if intent else "unknown"}
        })
        
        # Step 2: Route to model
        step_start = time.time()
        from core.model_router import ModelRouter
        router = ModelRouter()
        model = router.get_model()
        step_latency = (time.time() - step_start) * 1000
        steps.append({
            "step": 2,
            "action": "Select Model",
            "status": "complete",
            "latency_ms": round(step_latency, 2),
            "data": {"model": model.name}
        })
        
        # Step 3: Generate response
        step_start = time.time()
        from core.ollama_client import OllamaClient
        client = OllamaClient()
        result = client.generate(
            prompt=request.command,
            model=request.model or model.name,
            system="You are Ryx, a helpful AI assistant.",
            max_tokens=2048
        )
        step_latency = (time.time() - step_start) * 1000
        steps.append({
            "step": 3,
            "action": "Generate Response",
            "status": "complete" if not result.error else "error",
            "latency_ms": round(step_latency, 2),
            "data": {"error": result.error} if result.error else {}
        })
        
        total_latency = (time.time() - start_time) * 1000
        
        return {
            "status": "completed" if not result.error else "error",
            "command": request.command,
            "steps": steps,
            "result": result.response if not result.error else result.error,
            "total_latency_ms": round(total_latency, 2)
        }
        
    except Exception as e:
        total_latency = (time.time() - start_time) * 1000
        return {
            "status": "error",
            "command": request.command,
            "steps": steps,
            "result": f"Error: {str(e)}",
            "total_latency_ms": round(total_latency, 2)
        }


@app.post("/api/results/cache")
async def get_cached_results(
    limit: int = Query(default=10, ge=1, le=100)
) -> Dict[str, Any]:
    """
    Get recently cached results for fast repeat queries.

    Args:
        limit: Maximum number of cached results to return

    Returns:
        Dict with cached results
    """
    try:
        from core.rag_system import RAGSystem
        rag = RAGSystem()
        
        # Get cached responses from RAG system
        cached = rag.get_recent_responses(limit=limit)
        rag.close()
        
        return {
            "cached_results": cached,
            "total": len(cached)
        }
    except Exception:
        # Return empty if RAG system not available
        return {
            "cached_results": [],
            "total": 0
        }


@app.post("/api/service/start")
async def start_service(request: ServiceRequest) -> ServiceStatusResponse:
    """
    Start a service.

    Args:
        request: ServiceRequest with service name

    Returns:
        ServiceStatusResponse with service status
    """
    # Import here to avoid circular imports
    import sys
    import os
    from pathlib import Path

    # Find project root by looking for marker files
    def find_project_root(start_path: Path) -> Path:
        """Find project root by looking for pyproject.toml or core/ directory"""
        current = start_path
        for _ in range(10):  # Limit search depth
            if (current / "pyproject.toml").exists() or (current / "core").is_dir():
                return current
            parent = current.parent
            if parent == current:  # Reached filesystem root
                break
            current = parent
        # Fallback to calculated path
        return start_path.parent.parent.parent.parent.parent

    project_root = find_project_root(Path(__file__).resolve().parent)
    sys.path.insert(0, str(project_root))
    os.environ.setdefault('RYX_PROJECT_ROOT', str(project_root))

    try:
        from core.service_manager import ServiceManager
        manager = ServiceManager()

        if request.service.lower() in ['ryxhub', 'hub']:
            result = manager.start_ryxhub()
            if result['success']:
                return ServiceStatusResponse(
                    service="RyxHub",
                    running=True,
                    ports=result.get('info', []),
                    pids=result.get('pids')
                )
            else:
                raise HTTPException(status_code=500, detail=result.get('error', 'Failed to start'))
        else:
            raise HTTPException(status_code=400, detail=f"Unknown service: {request.service}")
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Service manager not available: {e}")


@app.post("/api/service/stop")
async def stop_service(request: ServiceRequest) -> ServiceStatusResponse:
    """
    Stop a service.

    Args:
        request: ServiceRequest with service name

    Returns:
        ServiceStatusResponse with service status
    """
    import sys
    import os
    from pathlib import Path

    # Reuse project root finder
    def find_project_root(start_path: Path) -> Path:
        current = start_path
        for _ in range(10):
            if (current / "pyproject.toml").exists() or (current / "core").is_dir():
                return current
            parent = current.parent
            if parent == current:
                break
            current = parent
        return start_path.parent.parent.parent.parent.parent

    project_root = find_project_root(Path(__file__).resolve().parent)
    sys.path.insert(0, str(project_root))
    os.environ.setdefault('RYX_PROJECT_ROOT', str(project_root))

    try:
        from core.service_manager import ServiceManager
        manager = ServiceManager()

        if request.service.lower() in ['ryxhub', 'hub']:
            result = manager.stop_ryxhub()
            if result['success']:
                return ServiceStatusResponse(
                    service="RyxHub",
                    running=False,
                    ports=[],
                    pids=None
                )
            else:
                raise HTTPException(status_code=500, detail=result.get('error', 'Failed to stop'))
        else:
            raise HTTPException(status_code=400, detail=f"Unknown service: {request.service}")
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Service manager not available: {e}")


@app.get("/api/service/status")
async def get_service_status() -> Dict[str, ServiceStatusResponse]:
    """
    Get status of all services.

    Returns:
        Dict with service status for each service
    """
    import sys
    import os
    from pathlib import Path

    # Reuse project root finder
    def find_project_root(start_path: Path) -> Path:
        current = start_path
        for _ in range(10):
            if (current / "pyproject.toml").exists() or (current / "core").is_dir():
                return current
            parent = current.parent
            if parent == current:
                break
            current = parent
        return start_path.parent.parent.parent.parent.parent

    project_root = find_project_root(Path(__file__).resolve().parent)
    sys.path.insert(0, str(project_root))
    os.environ.setdefault('RYX_PROJECT_ROOT', str(project_root))

    try:
        from core.service_manager import ServiceManager
        manager = ServiceManager()
        status = manager.get_status()

        result = {}
        for service_name, info in status.items():
            result[service_name] = ServiceStatusResponse(
                service=service_name,
                running=info.get('running', False),
                ports=info.get('ports', []),
                pids=info.get('pids')
            )
        return result
    except ImportError:
        return {
            "RyxHub": ServiceStatusResponse(
                service="RyxHub",
                running=False,
                ports=[],
                pids=None
            )
        }


# =============================================================================
# WebSocket Endpoint
# =============================================================================

@app.websocket("/api/workflow/stream")
async def workflow_stream(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for streaming workflow events.

    Protocol:
        Client sends: {"action": "execute_workflow", "input": "...", "model": "..."}
        Server sends: WorkflowEvent objects as JSON
    """
    await websocket.accept()
    try:
        while True:
            try:
                data = await websocket.receive_json()
            except Exception:
                # Handle invalid JSON
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON data"
                })
                continue

            # Handle workflow execution
            if data.get("action") == "execute_workflow":
                command = data.get("input", "")

                # Send step_start events
                await websocket.send_json({
                    "type": "step_start",
                    "step": 1,
                    "action": "Parsing command",
                    "timestamp": datetime.now().isoformat()
                })
                await asyncio.sleep(0.1)

                await websocket.send_json({
                    "type": "step_complete",
                    "step": 1,
                    "latency_ms": 50,
                    "result": "Command parsed"
                })

                await websocket.send_json({
                    "type": "step_start",
                    "step": 2,
                    "action": "Executing",
                    "timestamp": datetime.now().isoformat()
                })
                await asyncio.sleep(0.2)

                await websocket.send_json({
                    "type": "step_complete",
                    "step": 2,
                    "latency_ms": 200,
                    "result": f"Executed: {command}"
                })

                await websocket.send_json({
                    "type": "task_complete",
                    "total_latency_ms": 250,
                    "results": [f"Result for: {command}"]
                })
            else:
                await websocket.send_json({
                    "type": "acknowledged",
                    "data": data
                })
    except WebSocketDisconnect:
        pass


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    General WebSocket endpoint for real-time updates.
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        pass


# =============================================================================
# Health Check
# =============================================================================

@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
