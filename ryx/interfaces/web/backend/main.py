"""
Ryx AI - FastAPI Backend
REST and WebSocket API for the Ryx AI web interface
"""

from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
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


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Ryx AI API",
    version="0.1.0",
    description="REST and WebSocket API for Ryx AI"
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
                    "event": "error",
                    "message": "Invalid JSON data"
                })
                continue
            # TODO: Implement actual workflow execution
            # Echo back for now
            await websocket.send_json({
                "event": "acknowledged",
                "data": data
            })
    except WebSocketDisconnect:
        pass


# =============================================================================
# Health Check
# =============================================================================

@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
