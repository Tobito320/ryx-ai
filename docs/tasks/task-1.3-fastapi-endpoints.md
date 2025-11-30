# Task 1.3: FastAPI Endpoints Skeleton

**Time:** 30 min | **Priority:** HIGH | **Agent:** Copilot

## Objective

Create a FastAPI application skeleton with 5 endpoints for the Ryx AI web interface, including CORS middleware and Pydantic request/response models.

## Output File(s)

`ryx/interfaces/web/backend/main.py`

## Requirements

1. Create FastAPI application with:
   - App title: "Ryx AI API"
   - App version: "0.1.0"
   - CORS middleware allowing all origins (development)

2. Create these endpoints with stub responses:

   | Method | Path | Description |
   |--------|------|-------------|
   | GET | `/api/models` | List available LLM models |
   | POST | `/api/chat` | Send a chat message |
   | WebSocket | `/api/workflow/stream` | Stream workflow events |
   | GET | `/api/history` | Get conversation history |
   | POST | `/api/settings` | Update user settings |

3. Create Pydantic models for request/response:

   ```python
   # Request Models
   class ChatRequest(BaseModel):
       message: str
       model: Optional[str] = None
       stream: bool = False
   
   class SettingsRequest(BaseModel):
       theme: Optional[str] = None
       default_model: Optional[str] = None
       auto_scroll: Optional[bool] = None
   
   # Response Models
   class ModelInfo(BaseModel):
       id: str
       name: str
       size: str
       available: bool
   
   class ModelsResponse(BaseModel):
       models: List[ModelInfo]
   
   class ChatResponse(BaseModel):
       response: str
       model_used: str
       latency_ms: float
   
   class HistoryItem(BaseModel):
       id: str
       timestamp: datetime
       user_message: str
       assistant_response: str
       model_used: str
   
   class HistoryResponse(BaseModel):
       items: List[HistoryItem]
       total: int
   
   class StatusResponse(BaseModel):
       status: str
       message: Optional[str] = None
   ```

4. All endpoints should return `{"status": "ok"}` or appropriate stub data

5. WebSocket endpoint should accept connections and echo messages

## Code Template

```python
"""
Ryx AI - FastAPI Backend
REST and WebSocket API for the Ryx AI web interface
"""

from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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
async def get_history(limit: int = 50, offset: int = 0) -> HistoryResponse:
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
async def workflow_stream(websocket: WebSocket):
    """
    WebSocket endpoint for streaming workflow events.
    
    Protocol:
        Client sends: {"action": "execute_workflow", "input": "...", "model": "..."}
        Server sends: WorkflowEvent objects as JSON
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
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
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Acceptance Criteria

- [ ] FastAPI app created with title "Ryx AI API" and version "0.1.0"
- [ ] CORS middleware configured (allow all origins)
- [ ] All 5 Pydantic request models created
- [ ] All 6 Pydantic response models created
- [ ] GET `/api/models` endpoint implemented (stub)
- [ ] POST `/api/chat` endpoint implemented (stub)
- [ ] WebSocket `/api/workflow/stream` endpoint implemented (echo)
- [ ] GET `/api/history` endpoint implemented (stub)
- [ ] POST `/api/settings` endpoint implemented (stub)
- [ ] Health check endpoint at `/health`
- [ ] All endpoints have docstrings
- [ ] File can run: `python -m ryx.interfaces.web.backend.main`

## Notes

- Create the directory structure if it doesn't exist
- Add `__init__.py` files as needed for the package structure
- Use async functions for all endpoints
- The WebSocket endpoint should handle disconnections gracefully
- All response models should use Pydantic BaseModel
- Include type hints on all function parameters and returns
