"""
RYX AI API - FastAPI Backend with WebSocket Streaming

Provides:
- REST API for model management and queries
- WebSocket streaming for real-time workflow updates
- N8N-style workflow execution tracking
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio
import json
import uuid
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from .workflow import WorkflowEngine, ExecutionEvent, EventType, SimpleWorkflow, WorkflowState
from .interfaces import WorkflowNode, ExecutionContext, NodeStatus
from .router import IntelligentRouter, RouteDecision

# Global state
active_workflows: Dict[str, Dict[str, Any]] = {}
connected_clients: Dict[str, WebSocket] = {}
router_instance = IntelligentRouter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    print("🟣 Ryx AI API starting up...")
    yield
    # Shutdown
    print("🟣 Ryx AI API shutting down...")
    # Close all WebSocket connections
    for client_id, websocket in connected_clients.items():
        try:
            await websocket.close()
        except Exception:
            pass


app = FastAPI(
    title="Ryx AI API",
    description="🟣 Intelligent Local AI Agent API with N8N-style Workflow Visualization",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class ChatRequest(BaseModel):
    """Chat request model"""
    prompt: str = Field(..., description="User prompt")
    tier: Optional[str] = Field("balanced", description="Model tier")
    session_id: Optional[str] = Field(None, description="Session ID for context")
    stream: bool = Field(True, description="Whether to stream response")


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    model: str
    latency_ms: float
    workflow_id: Optional[str] = None


class WorkflowRequest(BaseModel):
    """Workflow execution request"""
    prompt: str
    workflow_type: str = "chat"  # 'chat', 'code', 'research', 'task'
    visualize: bool = True


class WorkflowNodeResponse(BaseModel):
    """Workflow node response for UI"""
    id: str
    name: str
    type: str
    status: str
    position: Dict[str, int]
    result: Optional[str] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class WorkflowVisualization(BaseModel):
    """Complete workflow visualization data"""
    workflow_id: str
    status: str
    nodes: List[WorkflowNodeResponse]
    edges: List[Dict[str, Any]]
    entry_node: Optional[str] = None


class ModelInfo(BaseModel):
    """Model information"""
    name: str
    tier: str
    available: bool
    vram_mb: int
    latency_ms: float


class RouteInfo(BaseModel):
    """Routing decision info"""
    selected_model: str
    tier: str
    reason: str
    confidence: float


# API Endpoints

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "Ryx AI API",
        "version": "0.2.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_workflows": len(active_workflows),
        "connected_clients": len(connected_clients),
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a chat message and get a response.
    
    For streaming responses, use the WebSocket endpoint instead.
    """
    import time
    start_time = time.time()
    
    # Route the request
    decision = router_instance.route(request.prompt, tier_override=None)
    
    # Here you would call the actual AI engine
    # For now, return a placeholder
    response_text = f"[Ryx AI] Processing: {request.prompt[:50]}..."
    
    latency = (time.time() - start_time) * 1000
    
    return ChatResponse(
        response=response_text,
        model=decision.selected_model,
        latency_ms=latency,
    )


@app.post("/api/route", response_model=RouteInfo)
async def route_prompt(request: ChatRequest):
    """
    Get routing decision for a prompt without executing it.
    
    Useful for UI to show which model will be used.
    """
    decision = router_instance.route(request.prompt)
    
    return RouteInfo(
        selected_model=decision.selected_model,
        tier=decision.tier.value,
        reason=decision.reason,
        confidence=decision.confidence,
    )


@app.get("/api/models", response_model=List[ModelInfo])
async def list_models():
    """List available models with their status"""
    models = []
    
    for name, profile in router_instance.profiles.items():
        models.append(ModelInfo(
            name=profile.name,
            tier=profile.tier.value,
            available=profile.is_available,
            vram_mb=profile.vram_mb,
            latency_ms=profile.avg_latency_ms,
        ))
    
    return models


@app.post("/api/workflow/create")
async def create_workflow(request: WorkflowRequest):
    """
    Create a new workflow for the given prompt.
    
    Returns workflow structure for visualization without executing.
    """
    workflow_id = str(uuid.uuid4())[:8]
    
    # Create workflow based on type
    workflow = _create_workflow_for_prompt(request.prompt, request.workflow_type)
    
    # Store workflow
    active_workflows[workflow_id] = {
        "workflow": workflow,
        "status": "created",
        "created_at": datetime.now().isoformat(),
        "prompt": request.prompt,
    }
    
    # Return visualization
    viz = workflow.to_visualization()
    
    return {
        "workflow_id": workflow_id,
        "visualization": viz,
    }


@app.post("/api/workflow/{workflow_id}/execute")
async def execute_workflow(workflow_id: str):
    """
    Execute a previously created workflow.
    
    For real-time updates, connect via WebSocket and listen for events.
    """
    if workflow_id not in active_workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow_data = active_workflows[workflow_id]
    workflow = workflow_data["workflow"]
    
    # Update status
    workflow_data["status"] = "running"
    workflow_data["started_at"] = datetime.now().isoformat()
    
    # Execute and collect results
    context = ExecutionContext(workflow_id=workflow_id)
    
    engine = WorkflowEngine()
    events = []
    
    for event in engine.execute(workflow, context, stream_events=True):
        events.append(event.to_dict())
        # Broadcast to connected WebSocket clients
        await _broadcast_event(workflow_id, event)
    
    workflow_data["status"] = "completed"
    workflow_data["completed_at"] = datetime.now().isoformat()
    
    return {
        "workflow_id": workflow_id,
        "status": "completed",
        "events_count": len(events),
    }


@app.get("/api/workflow/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get workflow status and visualization"""
    if workflow_id not in active_workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow_data = active_workflows[workflow_id]
    workflow = workflow_data["workflow"]
    
    return {
        "workflow_id": workflow_id,
        "status": workflow_data["status"],
        "visualization": workflow.to_visualization(),
        "created_at": workflow_data.get("created_at"),
        "started_at": workflow_data.get("started_at"),
        "completed_at": workflow_data.get("completed_at"),
    }


@app.delete("/api/workflow/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Delete a workflow"""
    if workflow_id not in active_workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    del active_workflows[workflow_id]
    return {"deleted": workflow_id}


# WebSocket Endpoint for Real-time Updates

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time workflow updates.
    
    Clients connect here to receive:
    - Workflow execution events (node start, complete, failed)
    - Live streaming of AI responses
    - Status updates
    """
    await websocket.accept()
    connected_clients[client_id] = websocket
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id,
            "message": "Connected to Ryx AI WebSocket",
        })
        
        # Handle incoming messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "subscribe":
                # Subscribe to workflow events
                workflow_id = message.get("workflow_id")
                await websocket.send_json({
                    "type": "subscribed",
                    "workflow_id": workflow_id,
                })
            
            elif message.get("type") == "chat":
                # Handle chat message with streaming
                prompt = message.get("prompt", "")
                tier = message.get("tier", "balanced")
                
                # Create and execute a workflow
                workflow_id = str(uuid.uuid4())[:8]
                workflow = _create_workflow_for_prompt(prompt, "chat")
                
                active_workflows[workflow_id] = {
                    "workflow": workflow,
                    "status": "running",
                    "created_at": datetime.now().isoformat(),
                    "prompt": prompt,
                    "client_id": client_id,
                }
                
                # Send workflow started
                await websocket.send_json({
                    "type": "workflow_started",
                    "workflow_id": workflow_id,
                    "visualization": workflow.to_visualization(),
                })
                
                # Execute workflow and stream events
                context = ExecutionContext(workflow_id=workflow_id)
                context.set_variable("user_input", prompt)
                
                engine = WorkflowEngine()
                
                for event in engine.execute(workflow, context, stream_events=True):
                    await websocket.send_json({
                        "type": "workflow_event",
                        "event": event.to_dict(),
                    })
                
                # Send workflow complete
                await websocket.send_json({
                    "type": "workflow_complete",
                    "workflow_id": workflow_id,
                })
            
            elif message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        if client_id in connected_clients:
            del connected_clients[client_id]
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e),
        })
        if client_id in connected_clients:
            del connected_clients[client_id]


# Helper Functions

def _create_workflow_for_prompt(prompt: str, workflow_type: str) -> SimpleWorkflow:
    """Create a workflow for a given prompt"""
    workflow = SimpleWorkflow()
    
    # Input node
    input_node = WorkflowNode(
        name="User Input",
        node_type="input",
        description=f"Input: {prompt[:50]}...",
        config={"input": prompt},
        position_x=100,
        position_y=200,
    )
    input_id = workflow.add_node(input_node)
    workflow.set_entry_node(input_id)
    
    # Router node (model selection)
    router_node = WorkflowNode(
        name="LLM Router",
        node_type="router",
        description="Intelligent model selection",
        config={"default_model": "balanced"},
        position_x=300,
        position_y=200,
    )
    router_id = workflow.add_node(router_node)
    workflow.add_edge(input_id, router_id)
    
    # Model execution node
    model_node = WorkflowNode(
        name="Model Execution",
        node_type="model",
        description="Execute with selected model",
        config={
            "prompt": "${user_input}",
            "system_prompt": "You are Ryx AI, an intelligent assistant.",
        },
        position_x=500,
        position_y=200,
    )
    model_id = workflow.add_node(model_node)
    workflow.add_edge(router_id, model_id)
    
    # Add tool nodes for specific workflow types
    if workflow_type == "code":
        tool_node = WorkflowNode(
            name="Code Analysis",
            node_type="tool",
            description="Analyze and execute code",
            config={"tool_name": "code_analyzer"},
            position_x=700,
            position_y=150,
        )
        tool_id = workflow.add_node(tool_node)
        workflow.add_edge(model_id, tool_id)
        final_source = tool_id
    elif workflow_type == "research":
        search_node = WorkflowNode(
            name="Web Search",
            node_type="tool",
            description="Search the web for information",
            config={"tool_name": "web_search"},
            position_x=700,
            position_y=150,
        )
        search_id = workflow.add_node(search_node)
        workflow.add_edge(model_id, search_id)
        final_source = search_id
    else:
        final_source = model_id
    
    # Output node
    output_node = WorkflowNode(
        name="Output",
        node_type="output",
        description="Format and return response",
        config={"format": "markdown"},
        position_x=900,
        position_y=200,
    )
    output_id = workflow.add_node(output_node)
    workflow.add_edge(final_source, output_id)
    
    return workflow


async def _broadcast_event(workflow_id: str, event: ExecutionEvent):
    """Broadcast event to all connected clients subscribed to this workflow"""
    workflow_data = active_workflows.get(workflow_id, {})
    client_id = workflow_data.get("client_id")
    
    if client_id and client_id in connected_clients:
        websocket = connected_clients[client_id]
        try:
            await websocket.send_json({
                "type": "workflow_event",
                "event": event.to_dict(),
            })
        except Exception:
            pass  # Client disconnected


# ============================================================================
# Document Scanner API - For Board Mode
# ============================================================================

# Document path configuration
DOCUMENTS_PATH = Path("/home/tobi/documents")

# Category mapping based on folder names
CATEGORY_MAP = {
    "azubi": "azubi",
    "schule": "azubi",
    "berufsschule": "azubi",
    "arbeit": "arbeit",
    "job": "arbeit",
    "aok": "aok",
    "krankenkasse": "aok",
    "sparkasse": "sparkasse",
    "bank": "sparkasse",
    "auto": "auto",
    "kfz": "auto",
    "fahrzeug": "auto",
}


class DocumentInfo(BaseModel):
    name: str
    path: str
    type: str
    category: Optional[str] = None
    modifiedAt: Optional[str] = None
    size: Optional[int] = None


class ScanDocumentsResponse(BaseModel):
    documents: List[DocumentInfo]
    total: int
    scanned_path: str


def detect_category(file_path: Path) -> Optional[str]:
    """Detect document category from path"""
    path_lower = str(file_path).lower()
    for keyword, category in CATEGORY_MAP.items():
        if keyword in path_lower:
            return category
    return "other"


@app.get("/api/documents/scan", response_model=ScanDocumentsResponse)
async def scan_documents(
    path: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
):
    """Scan documents directory and return file information"""
    scan_path = Path(path) if path else DOCUMENTS_PATH
    
    if not scan_path.exists():
        # Create the directory if it doesn't exist
        scan_path.mkdir(parents=True, exist_ok=True)
        return ScanDocumentsResponse(
            documents=[],
            total=0,
            scanned_path=str(scan_path),
        )
    
    documents = []
    
    # Recursively scan for documents
    for ext in ["*.pdf", "*.PDF", "*.png", "*.jpg", "*.jpeg", "*.doc", "*.docx", "*.txt"]:
        for file_path in scan_path.rglob(ext):
            if file_path.is_file():
                doc_category = detect_category(file_path)
                
                # Filter by category if specified
                if category and category != "all" and doc_category != category:
                    continue
                
                # Filter by search query
                if search and search.lower() not in file_path.name.lower():
                    continue
                
                file_type = file_path.suffix[1:].lower()
                stat = file_path.stat()
                
                documents.append(DocumentInfo(
                    name=file_path.name,
                    path=str(file_path.parent) + "/",
                    type=file_type,
                    category=doc_category,
                    modifiedAt=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    size=stat.st_size,
                ))
    
    # Sort by modification date (newest first)
    documents.sort(key=lambda x: x.modifiedAt or "", reverse=True)
    
    return ScanDocumentsResponse(
        documents=documents,
        total=len(documents),
        scanned_path=str(scan_path),
    )


# ============================================================================
# Memory API - Personal Knowledge Store
# ============================================================================

# Memory storage path
MEMORY_FILE = PROJECT_ROOT / "data" / "user_memory.json"


class MemoryEntry(BaseModel):
    id: str
    type: str  # fact, preference, contact, template, routine
    key: str
    value: str
    confidence: float = 1.0
    source: Optional[str] = None
    createdAt: str
    updatedAt: str
    usageCount: int = 0


class MemoryListResponse(BaseModel):
    memories: List[MemoryEntry]
    total: int


def load_memories() -> List[Dict[str, Any]]:
    """Load memories from file"""
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_memories(memories: List[Dict[str, Any]]):
    """Save memories to file"""
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_FILE, "w") as f:
        json.dump(memories, f, indent=2)


@app.get("/api/memory", response_model=MemoryListResponse)
async def list_memories(type: Optional[str] = None):
    """List all user memories"""
    memories = load_memories()
    
    if type:
        memories = [m for m in memories if m.get("type") == type]
    
    return MemoryListResponse(
        memories=[MemoryEntry(**m) for m in memories],
        total=len(memories),
    )


class CreateMemoryRequest(BaseModel):
    type: str
    key: str
    value: str
    confidence: float = 1.0
    source: Optional[str] = None


@app.post("/api/memory", response_model=MemoryEntry)
async def create_memory(request: CreateMemoryRequest):
    """Create a new memory entry"""
    memories = load_memories()
    
    now = datetime.now().isoformat()
    new_memory = {
        "id": str(uuid.uuid4()),
        "type": request.type,
        "key": request.key,
        "value": request.value,
        "confidence": request.confidence,
        "source": request.source,
        "createdAt": now,
        "updatedAt": now,
        "usageCount": 0,
    }
    
    memories.append(new_memory)
    save_memories(memories)
    
    return MemoryEntry(**new_memory)


@app.delete("/api/memory/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a memory entry"""
    memories = load_memories()
    memories = [m for m in memories if m.get("id") != memory_id]
    save_memories(memories)
    return {"success": True}


# ============================================================================
# Gmail API - Multi-Account Email Integration
# ============================================================================

# Gmail accounts storage
GMAIL_FILE = PROJECT_ROOT / "data" / "gmail_accounts.json"


class GmailAccount(BaseModel):
    id: str
    email: str
    name: str
    isDefault: bool = False
    lastSync: Optional[str] = None


class GmailAccountsResponse(BaseModel):
    accounts: List[GmailAccount]
    default_account: Optional[str] = None


def load_gmail_accounts() -> List[Dict[str, Any]]:
    """Load Gmail accounts from file"""
    if GMAIL_FILE.exists():
        try:
            with open(GMAIL_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_gmail_accounts(accounts: List[Dict[str, Any]]):
    """Save Gmail accounts to file"""
    GMAIL_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(GMAIL_FILE, "w") as f:
        json.dump(accounts, f, indent=2)


@app.get("/api/gmail/accounts", response_model=GmailAccountsResponse)
async def list_gmail_accounts():
    """List all connected Gmail accounts"""
    accounts = load_gmail_accounts()
    default_id = None
    
    for acc in accounts:
        if acc.get("isDefault"):
            default_id = acc.get("id")
            break
    
    return GmailAccountsResponse(
        accounts=[GmailAccount(**a) for a in accounts],
        default_account=default_id,
    )


class AddGmailAccountRequest(BaseModel):
    email: str
    name: str
    isDefault: bool = False


@app.post("/api/gmail/accounts", response_model=GmailAccount)
async def add_gmail_account(request: AddGmailAccountRequest):
    """Add a new Gmail account (placeholder for OAuth flow)"""
    accounts = load_gmail_accounts()
    
    # Check if email already exists
    for acc in accounts:
        if acc.get("email") == request.email:
            raise HTTPException(status_code=400, detail="Email already connected")
    
    # If this is the first account or marked as default, make it default
    if request.isDefault or len(accounts) == 0:
        # Remove default from others
        for acc in accounts:
            acc["isDefault"] = False
    
    new_account = {
        "id": str(uuid.uuid4()),
        "email": request.email,
        "name": request.name,
        "isDefault": request.isDefault or len(accounts) == 0,
        "lastSync": None,
    }
    
    accounts.append(new_account)
    save_gmail_accounts(accounts)
    
    return GmailAccount(**new_account)


@app.delete("/api/gmail/accounts/{account_id}")
async def remove_gmail_account(account_id: str):
    """Remove a Gmail account"""
    accounts = load_gmail_accounts()
    accounts = [a for a in accounts if a.get("id") != account_id]
    save_gmail_accounts(accounts)
    return {"success": True}


@app.put("/api/gmail/accounts/{account_id}/default")
async def set_default_gmail_account(account_id: str):
    """Set an account as the default"""
    accounts = load_gmail_accounts()
    
    for acc in accounts:
        acc["isDefault"] = acc.get("id") == account_id
    
    save_gmail_accounts(accounts)
    return {"success": True}


# ============================================================================
# Board API - Infinite Canvas Storage
# ============================================================================

BOARDS_FILE = PROJECT_ROOT / "data" / "boards.json"


class Board(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    createdAt: str
    updatedAt: str
    isDefault: bool = False
    category: Optional[str] = None


class BoardsResponse(BaseModel):
    boards: List[Board]
    total: int


def load_boards() -> List[Dict[str, Any]]:
    """Load boards from file"""
    if BOARDS_FILE.exists():
        try:
            with open(BOARDS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    # Return default board if none exist
    now = datetime.now().isoformat()
    return [{
        "id": "default-board",
        "name": "Mein Board",
        "description": "Hauptboard für Dokumente und Notizen",
        "createdAt": now,
        "updatedAt": now,
        "isDefault": True,
        "category": "personal",
    }]


def save_boards(boards: List[Dict[str, Any]]):
    """Save boards to file"""
    BOARDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BOARDS_FILE, "w") as f:
        json.dump(boards, f, indent=2)


@app.get("/api/boards", response_model=BoardsResponse)
async def list_boards():
    """List all boards"""
    boards = load_boards()
    return BoardsResponse(
        boards=[Board(**b) for b in boards],
        total=len(boards),
    )


class CreateBoardRequest(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None


@app.post("/api/boards", response_model=Board)
async def create_board(request: CreateBoardRequest):
    """Create a new board"""
    boards = load_boards()
    
    now = datetime.now().isoformat()
    new_board = {
        "id": str(uuid.uuid4()),
        "name": request.name,
        "description": request.description,
        "createdAt": now,
        "updatedAt": now,
        "isDefault": False,
        "category": request.category,
    }
    
    boards.append(new_board)
    save_boards(boards)
    
    return Board(**new_board)


@app.delete("/api/boards/{board_id}")
async def delete_board(board_id: str):
    """Delete a board (cannot delete default board)"""
    boards = load_boards()
    
    # Check if trying to delete default board
    for b in boards:
        if b.get("id") == board_id and b.get("isDefault"):
            raise HTTPException(status_code=400, detail="Cannot delete default board")
    
    boards = [b for b in boards if b.get("id") != board_id]
    save_boards(boards)
    return {"success": True}
