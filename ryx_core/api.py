"""
RYX AI API - FastAPI Backend with WebSocket Streaming

Provides:
- REST API for model management and queries
- WebSocket streaming for real-time workflow updates
- N8N-style workflow execution tracking
- Memory system (like ChatGPT)
- Reminders and scheduling
- File organization
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
from .document_ai import DocumentAI
from .memory import memory_system, MemoryEntry
from .reminders import reminder_system, Reminder, ReminderStatus, ReminderType
from .trash_schedule import trash_schedule
from .file_organizer import file_organizer, CATEGORIES

# Global state
document_ai = DocumentAI()
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

# Category mapping based on folder names and file content keywords
CATEGORY_MAP = {
    # Folder-based
    "azubi": "azubi",
    "schule": "azubi",
    "berufsschule": "azubi",
    "ausbildung": "azubi",
    "arbeit": "arbeit",
    "job": "arbeit",
    "aok": "aok",
    "krankenkasse": "aok",
    "gesundheit": "aok",
    "sparkasse": "sparkasse",
    "bank": "sparkasse",
    "konto": "sparkasse",
    "auto": "auto",
    "kfz": "auto",
    "fahrzeug": "auto",
    "tuev": "auto",
    "tüv": "auto",
    # Family/Housing
    "familie": "familie",
    "wohnung": "familie",
    "wohngeld": "familie",
    "miete": "familie",
    "heizung": "familie",
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


# ============================================================================
# Document Intelligence API - Smart Brief/Letter Processing
# ============================================================================

class DocumentAnalysisRequest(BaseModel):
    path: str


class DocumentAnalysisResponse(BaseModel):
    type: str
    sender: Optional[str]
    date: Optional[str]
    subject: Optional[str]
    deadlines: List[Dict[str, Any]]
    requires_response: bool
    priority: str
    summary: str
    text_preview: str


class GenerateResponseRequest(BaseModel):
    document_path: str
    response_type: str = "standard"  # standard, rechnung, widerspruch


class TemplateRequest(BaseModel):
    name: str
    content: Optional[str] = None


@app.post("/api/documents/analyze", response_model=DocumentAnalysisResponse)
async def analyze_document(request: DocumentAnalysisRequest):
    """Analyze a document (PDF) and extract key information"""
    doc_path = Path(request.path)
    
    if not doc_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Extract text
    text = document_ai.extract_text_from_pdf(doc_path)
    
    # Analyze
    analysis = document_ai.analyze_document(text)
    
    return DocumentAnalysisResponse(
        **analysis,
        text_preview=text[:500]
    )


@app.post("/api/documents/generate-response")
async def generate_response(request: GenerateResponseRequest):
    """Generate a response letter template"""
    doc_path = Path(request.document_path)
    
    if not doc_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Analyze document first
    text = document_ai.extract_text_from_pdf(doc_path)
    analysis = document_ai.analyze_document(text)
    
    # Generate response template
    template = document_ai.generate_response_template(analysis, request.response_type)
    
    return {
        "template": template,
        "analysis": analysis
    }


@app.get("/api/templates")
async def list_templates():
    """List available brief templates"""
    templates = document_ai.list_templates()
    return {"templates": templates}


@app.get("/api/templates/{name}")
async def get_template(name: str):
    """Get a specific template"""
    content = document_ai.load_template(name)
    if not content:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"name": name, "content": content}


@app.post("/api/templates")
async def save_template(request: TemplateRequest):
    """Save a custom template"""
    if not request.content:
        raise HTTPException(status_code=400, detail="Content required")
    
    document_ai.save_template(request.name, request.content)
    return {"success": True, "name": request.name}


# ============================================================================
# Frontend Logging API
# ============================================================================

from datetime import datetime as dt
import json as json_lib

LOGS_DIR = Path(__file__).parent.parent / "logs"
FRONTEND_LOGS_DIR = LOGS_DIR / "frontend"
BACKEND_LOGS_DIR = LOGS_DIR / "backend"

# Ensure log directories exist
FRONTEND_LOGS_DIR.mkdir(parents=True, exist_ok=True)
BACKEND_LOGS_DIR.mkdir(parents=True, exist_ok=True)


class FrontendLogEntry(BaseModel):
    level: str
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str
    userAgent: str
    url: str


class FrontendLogsRequest(BaseModel):
    logs: List[FrontendLogEntry]


@app.post("/api/logs/frontend")
async def log_frontend(request: FrontendLogsRequest):
    """Receive frontend logs and save to file"""
    today = dt.now().strftime("%Y-%m-%d")
    log_file = FRONTEND_LOGS_DIR / f"{today}.log"
    
    with open(log_file, "a") as f:
        for log in request.logs:
            log_line = json_lib.dumps({
                "timestamp": log.timestamp,
                "level": log.level,
                "message": log.message,
                "data": log.data,
                "url": log.url,
                "userAgent": log.userAgent,
            })
            f.write(log_line + "\n")
    
    return {"success": True, "count": len(request.logs)}


@app.get("/api/logs/list")
async def list_logs():
    """List available log files"""
    frontend_logs = sorted([f.name for f in FRONTEND_LOGS_DIR.glob("*.log")], reverse=True)
    backend_logs = sorted([f.name for f in BACKEND_LOGS_DIR.glob("*.log")], reverse=True)
    
    return {
        "frontend": frontend_logs,
        "backend": backend_logs,
    }


@app.get("/api/logs/view/{log_type}/{filename}")
async def view_log(log_type: str, filename: str):
    """View a specific log file"""
    if log_type not in ["frontend", "backend"]:
        raise HTTPException(status_code=400, detail="Invalid log type")
    
    log_dir = FRONTEND_LOGS_DIR if log_type == "frontend" else BACKEND_LOGS_DIR
    log_file = log_dir / filename
    
    if not log_file.exists():
        raise HTTPException(status_code=404, detail="Log file not found")
    
    # Read last 100 lines
    with open(log_file, "r") as f:
        lines = f.readlines()
        last_lines = lines[-100:] if len(lines) > 100 else lines
    
    return {
        "filename": filename,
        "lines": [json_lib.loads(line) for line in last_lines if line.strip()],
        "total": len(lines),
    }


# ============================================================================
# Memory System API - Like ChatGPT Memory
# ============================================================================

class MemoryRequest(BaseModel):
    type: str = "fact"
    key: str
    value: str
    source: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    full_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    email_default: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[str] = None
    occupation: Optional[str] = None
    employer: Optional[str] = None


@app.get("/api/memory")
async def get_memories(type: Optional[str] = None, limit: int = 50):
    """Get all memories or filtered by type"""
    memories = memory_system.get_memories(type=type, limit=limit)
    return {"memories": [m.model_dump() for m in memories]}


@app.post("/api/memory")
async def add_memory(request: MemoryRequest):
    """Add a new memory"""
    memory = memory_system.add_memory(
        type=request.type,
        key=request.key,
        value=request.value,
        source=request.source,
    )
    return {"success": True, "memory": memory.model_dump()}


@app.delete("/api/memory/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a memory"""
    success = memory_system.delete_memory(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"success": True}


@app.get("/api/memory/search")
async def search_memories(q: str):
    """Search memories"""
    memories = memory_system.search_memories(q)
    return {"memories": [m.model_dump() for m in memories]}


@app.get("/api/profile")
async def get_profile():
    """Get user profile"""
    return memory_system.profile.model_dump()


@app.patch("/api/profile")
async def update_profile(request: ProfileUpdateRequest):
    """Update user profile"""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    profile = memory_system.update_profile(**updates)
    return {"success": True, "profile": profile.model_dump()}


@app.get("/api/memory/context")
async def get_ai_context():
    """Get context string for AI prompts"""
    return {"context": memory_system.get_context_for_ai()}


# ============================================================================
# Reminders API
# ============================================================================

class ReminderRequest(BaseModel):
    title: str
    date: str  # YYYY-MM-DD
    type: str = "custom"
    time: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    source_id: Optional[str] = None


class ReminderStatusUpdate(BaseModel):
    status: str  # pending, completed, missed, cancelled
    notes: Optional[str] = None


@app.get("/api/reminders")
async def get_reminders(days: int = 7, include_overdue: bool = True):
    """Get upcoming reminders"""
    upcoming = reminder_system.get_upcoming(days=days)
    overdue = reminder_system.get_overdue() if include_overdue else []
    today = reminder_system.get_today()
    
    return {
        "today": [r.model_dump() for r in today],
        "upcoming": [r.model_dump() for r in upcoming],
        "overdue": [r.model_dump() for r in overdue],
    }


@app.post("/api/reminders")
async def add_reminder(request: ReminderRequest):
    """Add a new reminder"""
    reminder = reminder_system.add_reminder(
        title=request.title,
        date=request.date,
        type=ReminderType(request.type),
        time=request.time,
        description=request.description,
        source=request.source,
        source_id=request.source_id,
    )
    return {"success": True, "reminder": reminder.model_dump()}


@app.patch("/api/reminders/{reminder_id}")
async def update_reminder_status(reminder_id: str, request: ReminderStatusUpdate):
    """Update reminder status"""
    reminder = reminder_system.update_status(
        reminder_id=reminder_id,
        status=ReminderStatus(request.status),
        notes=request.notes,
    )
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"success": True, "reminder": reminder.model_dump()}


@app.delete("/api/reminders/{reminder_id}")
async def delete_reminder(reminder_id: str):
    """Delete a reminder"""
    success = reminder_system.delete_reminder(reminder_id)
    if not success:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"success": True}


# ============================================================================
# Trash Schedule API (HEB Hagen)
# ============================================================================

@app.get("/api/trash")
async def get_trash_schedule(days: int = 14):
    """Get upcoming trash collection dates"""
    upcoming = trash_schedule.get_upcoming(days=days)
    next_collection = trash_schedule.get_next()
    today = trash_schedule.get_today()
    tomorrow = trash_schedule.get_tomorrow()
    
    return {
        "today": [{"date": e.date, "type": e.type, "description": e.description} for e in today],
        "tomorrow": [{"date": e.date, "type": e.type, "description": e.description} for e in tomorrow],
        "next": {"date": next_collection.date, "type": next_collection.type} if next_collection else None,
        "upcoming": [{"date": e.date, "type": e.type, "description": e.description} for e in upcoming],
        "needs_update": trash_schedule.needs_update(),
        "last_updated": trash_schedule.config.get("last_updated"),
    }


class TrashICSRequest(BaseModel):
    ics_url: str


@app.post("/api/trash/sync")
async def sync_trash_schedule(request: TrashICSRequest):
    """Sync trash schedule from ICS URL"""
    success = trash_schedule.fetch_from_ics_url(request.ics_url)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to fetch ICS calendar")
    return {
        "success": True,
        "events_count": len(trash_schedule.events),
    }


# ============================================================================
# File Organization API
# ============================================================================

@app.get("/api/files/stats")
async def get_file_stats():
    """Get folder statistics"""
    return file_organizer.get_folder_stats()


@app.get("/api/files/uncategorized")
async def get_uncategorized_files():
    """Get uncategorized files in documents root"""
    return {"files": file_organizer.get_uncategorized()}


@app.get("/api/files/categories")
async def get_categories():
    """Get available categories"""
    return {
        "categories": [
            {"id": cat, "keywords": info["keywords"], "path": str(info["path"])}
            for cat, info in CATEGORIES.items()
        ]
    }


class MoveFileRequest(BaseModel):
    source_path: str
    category: str
    new_name: Optional[str] = None


@app.post("/api/files/move")
async def move_file(request: MoveFileRequest):
    """Move file to category"""
    success, result = file_organizer.move_to_category(
        source_path=request.source_path,
        category=request.category,
        new_name=request.new_name,
    )
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"success": True, "new_path": result}


class RenameFileRequest(BaseModel):
    path: str
    new_name: str


@app.post("/api/files/rename")
async def rename_file(request: RenameFileRequest):
    """Rename a file"""
    success, result = file_organizer.rename_file(request.path, request.new_name)
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"success": True, "new_path": result}


class CreateFolderRequest(BaseModel):
    parent: str
    name: str


@app.post("/api/files/folder")
async def create_folder(request: CreateFolderRequest):
    """Create a new folder"""
    success, result = file_organizer.create_folder(request.parent, request.name)
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"success": True, "path": result}


@app.delete("/api/files")
async def delete_file(path: str):
    """Delete a file (moves to trash)"""
    success, result = file_organizer.delete_file(path)
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"success": True, "message": result}


# ============================================================================
# Dashboard Summary API
# ============================================================================

@app.get("/api/dashboard/summary")
async def get_dashboard_summary():
    """Get summary for dashboard - all in one call"""
    # Documents
    scan_path = Path("/home/tobi/documents")
    documents = []
    for ext in ["*.pdf", "*.PDF"]:
        for file_path in scan_path.rglob(ext):
            if file_path.is_file():
                documents.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "category": detect_category(file_path),
                })
    
    # Reminders
    today_reminders = reminder_system.get_today()
    overdue_reminders = reminder_system.get_overdue()
    
    # Trash
    tomorrow_trash = trash_schedule.get_tomorrow()
    
    # Memory count
    memory_count = len(memory_system.memories)
    
    # File stats
    file_stats = file_organizer.get_folder_stats()
    uncategorized = file_organizer.get_uncategorized()
    
    return {
        "documents": {
            "total": len(documents),
            "by_category": {cat: len([d for d in documents if d["category"] == cat]) for cat in CATEGORIES.keys()},
        },
        "reminders": {
            "today": len(today_reminders),
            "overdue": len(overdue_reminders),
            "items": [r.model_dump() for r in (overdue_reminders + today_reminders)[:5]],
        },
        "trash": {
            "tomorrow": [{"type": t.type, "description": t.description} for t in tomorrow_trash],
        },
        "memory": {
            "facts_count": memory_count,
        },
        "files": {
            "uncategorized_count": len(uncategorized),
            "stats": file_stats,
        },
        "profile": memory_system.profile.model_dump(),
    }


# ============================================================================
# Smart Chat API - Using vLLM with Memory & Search
# ============================================================================

import httpx

VLLM_BASE = "http://localhost:8001/v1"
SEARXNG_BASE = "http://localhost:8888"


class SmartChatRequest(BaseModel):
    message: str
    include_memory: bool = True
    include_search: bool = False
    include_scrape: bool = False
    document: Optional[str] = None
    gmail_account: Optional[str] = None


class SmartChatResponse(BaseModel):
    response: str
    tools_used: List[str]
    model: str
    tokens: int


@app.post("/api/chat/smart", response_model=SmartChatResponse)
async def smart_chat(request: SmartChatRequest):
    """
    Smart chat endpoint that:
    - Integrates with memory system (knows user's personal info)
    - Can search the web via SearXNG
    - Can analyze documents if selected
    - Uses the 14B model for quality German responses
    """
    tools_used = []
    context_parts = []
    
    # 1. Add memory context
    if request.include_memory:
        memory_context = memory_system.get_context_for_ai()
        if memory_context:
            context_parts.append(f"## Benutzer-Kontext:\n{memory_context}")
            tools_used.append("memory")
        
        # Always add trash schedule to context when memory is enabled
        upcoming_trash = trash_schedule.get_upcoming(days=14)
        if upcoming_trash:
            trash_info = "\n".join([
                f"- {e.date}: {e.type}" for e in upcoming_trash[:5]
            ])
            context_parts.append(f"## Müllabfuhr-Termine (Alleestraße 58, Hagen):\n{trash_info}")
        
        # Add today's reminders
        today_reminders = reminder_system.get_today()
        if today_reminders:
            reminder_info = "\n".join([f"- {r.title}" for r in today_reminders])
            context_parts.append(f"## Heutige Termine:\n{reminder_info}")
    
    # 2. Add document context if selected
    if request.document:
        doc_path = DOCUMENTS_PATH / request.document
        if doc_path.exists() and doc_path.suffix.lower() == ".pdf":
            try:
                text = document_ai.extract_text_from_pdf(doc_path)
                if text:
                    context_parts.append(f"## Dokument ({request.document}):\n{text[:2000]}...")
                    tools_used.append("document")
            except Exception as e:
                pass
    
    # 3. Web search if requested
    search_results = ""
    if request.include_search:
        try:
            # Use SearXNG for search
            async with httpx.AsyncClient(timeout=10.0) as client:
                search_url = f"{SEARXNG_BASE}/search"
                params = {
                    "q": request.message,
                    "format": "json",
                    "categories": "general",
                }
                res = await client.get(search_url, params=params)
                if res.status_code == 200:
                    data = res.json()
                    results = data.get("results", [])[:3]
                    if results:
                        search_results = "\n".join([
                            f"- {r.get('title', '')}: {r.get('content', '')[:200]}"
                            for r in results
                        ])
                        context_parts.append(f"## Web-Suchergebnisse:\n{search_results}")
                        tools_used.append("search")
        except Exception as e:
            pass
    
    # 4. Build system prompt with current date
    from datetime import datetime as dt
    current_date = dt.now().strftime("%A, %d. %B %Y")
    current_time = dt.now().strftime("%H:%M")
    
    system_prompt = f"""Du bist ein hilfreicher persönlicher Assistent.
HEUTE ist {current_date}, aktuelle Uhrzeit: {current_time}.
Antworte KURZ und PRÄZISE - maximal 2-3 Sätze wenn möglich.
Du sprichst Deutsch und kennst den Benutzer persönlich.
Nutze den bereitgestellten Kontext um personalisierte Antworten zu geben.
"""
    
    if context_parts:
        system_prompt += "\n\n" + "\n\n".join(context_parts)
    
    # 5. Call vLLM
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            vllm_res = await client.post(
                f"{VLLM_BASE}/chat/completions",
                json={
                    "model": "/models/powerful/general/qwen2.5-14b-gptq",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": request.message},
                    ],
                    "max_tokens": 500,
                    "temperature": 0.7,
                },
            )
            
            if vllm_res.status_code == 200:
                data = vllm_res.json()
                response_text = data["choices"][0]["message"]["content"]
                tokens_used = data.get("usage", {}).get("total_tokens", 0)
                model_used = data.get("model", "unknown")
                
                return SmartChatResponse(
                    response=response_text.strip(),
                    tools_used=tools_used,
                    model=model_used,
                    tokens=tokens_used,
                )
            else:
                # Fallback response if vLLM fails
                return SmartChatResponse(
                    response=f"vLLM nicht erreichbar (Status: {vllm_res.status_code}). Starte mit: ryx restart all",
                    tools_used=tools_used,
                    model="error",
                    tokens=0,
                )
    except httpx.TimeoutException:
        return SmartChatResponse(
            response="vLLM Timeout - Model wird möglicherweise noch geladen. Bitte warten...",
            tools_used=tools_used,
            model="timeout",
            tokens=0,
        )
    except Exception as e:
        return SmartChatResponse(
            response=f"Fehler: {str(e)}",
            tools_used=tools_used,
            model="error",
            tokens=0,
        )
