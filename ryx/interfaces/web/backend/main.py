"""
Ryx AI - FastAPI Backend
REST and WebSocket API for the Ryx AI web interface
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
import asyncio

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


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
    # TODO: Implement actual model listing from Ollama
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
    # TODO: Implement actual chat with LLM
    return ChatResponse(
        response="This is a stub response",
        model_used=request.model or "default",
        latency_ms=0.0
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
    # TODO: Implement actual history retrieval
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
    # TODO: Implement actual settings update
    return StatusResponse(status="ok", message="Settings updated")


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
    # TODO: Implement actual command execution
    return {
        "status": "completed",
        "command": request.command,
        "steps": [
            {"step": 1, "action": "Parse", "status": "complete", "latency_ms": 50},
            {"step": 2, "action": "Execute", "status": "complete", "latency_ms": 200},
            {"step": 3, "action": "Format", "status": "complete", "latency_ms": 30},
        ],
        "result": f"Executed: {request.command}",
        "total_latency_ms": 280
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
    # TODO: Implement actual cache retrieval
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

    # Add project root to path
    project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
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

    project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
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

    project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
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
