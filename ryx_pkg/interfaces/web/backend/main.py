"""
Ryx AI - FastAPI Backend
REST and WebSocket API for RyxHub web interface.

Connects directly to vLLM for inference.
All Ollama references removed - this is a vLLM-only system.
"""

import sys
import os
import time
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import aiohttp

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
# Configuration
# =============================================================================

VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://localhost:8001")
SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8888")
API_PORT = int(os.environ.get("RYX_API_PORT", "8420"))
VLLM_MODELS_DIR = os.environ.get("VLLM_MODELS_DIR", "/home/tobi/vllm-models")


# =============================================================================
# Pydantic Models
# =============================================================================

class MessageRequest(BaseModel):
    """Request model for sending a message."""
    content: str
    model: Optional[str] = None
    stream: bool = False


class MessageResponse(BaseModel):
    """Response from chat."""
    id: str
    role: str
    content: str
    timestamp: str
    model: Optional[str] = None
    latency_ms: Optional[float] = None
    tokens_per_second: Optional[float] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


class ModelInfo(BaseModel):
    """Information about an available model."""
    id: str
    name: str
    status: str = "online"
    provider: str = "vLLM"


class SessionInfo(BaseModel):
    """Session information."""
    id: str
    name: str
    lastMessage: str
    timestamp: str
    isActive: bool = False
    model: str
    agentId: str
    messages: List[Dict[str, Any]] = []


class RAGStatus(BaseModel):
    """RAG index status."""
    indexed: int
    pending: int
    lastSync: str
    status: str = "idle"


class WorkflowInfo(BaseModel):
    """Workflow information."""
    id: str
    name: str
    status: str = "idle"
    lastRun: str


class AgentInfo(BaseModel):
    """Agent information."""
    id: str
    name: str
    status: str = "idle"
    model: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    uptime: int
    vllm_status: str


class StatusResponse(BaseModel):
    """System status response."""
    models_loaded: int
    active_sessions: int
    gpu_memory_used: float
    gpu_memory_total: float
    vllm_workers: int


# =============================================================================
# Session Persistence
# =============================================================================

SESSIONS_DIR = Path(os.environ.get("SESSIONS_DIR", PROJECT_ROOT / "data" / "sessions"))
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

sessions: Dict[str, SessionInfo] = {}
message_counter = 0


def get_next_message_id() -> str:
    global message_counter
    message_counter += 1
    return f"msg-{message_counter}"


def save_session(session: SessionInfo) -> None:
    """Persist session to disk."""
    try:
        session_file = SESSIONS_DIR / f"{session.id}.json"
        with open(session_file, 'w') as f:
            json.dump(session.dict(), f, indent=2, default=str)
    except Exception as e:
        print(f"Failed to save session {session.id}: {e}")


def load_sessions() -> None:
    """Load all sessions from disk on startup."""
    global sessions, message_counter
    try:
        for session_file in SESSIONS_DIR.glob("*.json"):
            try:
                with open(session_file) as f:
                    data = json.load(f)
                    session = SessionInfo(**data)
                    sessions[session.id] = session
                    # Update message counter
                    for msg in session.messages:
                        if msg.get("id", "").startswith("msg-"):
                            try:
                                num = int(msg["id"].split("-")[1])
                                message_counter = max(message_counter, num)
                            except:
                                pass
            except Exception as e:
                print(f"Failed to load session {session_file}: {e}")
    except Exception as e:
        print(f"Failed to scan sessions: {e}")


def delete_session_file(session_id: str) -> None:
    """Delete session file from disk."""
    try:
        session_file = SESSIONS_DIR / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()
    except Exception as e:
        print(f"Failed to delete session file {session_id}: {e}")


# =============================================================================
# vLLM Client Helper
# =============================================================================

async def vllm_health_check() -> Dict[str, Any]:
    """Check vLLM server health."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(f"{VLLM_BASE_URL}/health") as resp:
                if resp.status == 200:
                    return {"healthy": True, "status": "online"}
                return {"healthy": False, "status": f"HTTP {resp.status}"}
    except Exception as e:
        return {"healthy": False, "status": str(e)}


async def vllm_list_models() -> List[str]:
    """List models available in vLLM."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(f"{VLLM_BASE_URL}/v1/models") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [m["id"] for m in data.get("data", [])]
                return []
    except Exception:
        return []


def scan_local_models() -> List[Dict[str, Any]]:
    """Scan local models directory for available models."""
    models = []
    
    if not os.path.exists(VLLM_MODELS_DIR):
        return models
    
    try:
        # Scan directory structure: /models/{size}/{category}/{model_name}
        for size_dir in ["small", "medium", "large"]:
            size_path = os.path.join(VLLM_MODELS_DIR, size_dir)
            if not os.path.exists(size_path):
                continue
            
            # Use os.scandir for better performance
            with os.scandir(size_path) as size_entries:
                for category_entry in size_entries:
                    if not category_entry.is_dir():
                        continue
                    
                    category_dir = category_entry.name
                    category_path = category_entry.path
                    
                    with os.scandir(category_path) as model_entries:
                        for model_entry in model_entries:
                            if not model_entry.is_dir():
                                continue
                            
                            model_name = model_entry.name
                            model_path = model_entry.path
                            
                            # Check if it's a valid model directory (contains config.json or similar)
                            config_exists = (
                                os.path.exists(os.path.join(model_path, "config.json")) or
                                os.path.exists(os.path.join(model_path, "pytorch_model.bin")) or
                                os.path.exists(os.path.join(model_path, "model.safetensors"))
                            )
                            
                            # Only check for .safetensors files if config not found
                            if not config_exists:
                                try:
                                    with os.scandir(model_path) as files:
                                        config_exists = any(
                                            f.name.endswith('.safetensors') and f.is_file()
                                            for f in files
                                        )
                                except (OSError, PermissionError):
                                    continue
                            
                            if config_exists:
                                full_path = f"/models/{size_dir}/{category_dir}/{model_name}"
                                models.append({
                                    "id": full_path,
                                    "name": model_name,
                                    "path": full_path,
                                    "size": size_dir,
                                    "category": category_dir,
                                    "status": "offline"  # Default, will be checked against loaded models
                                })
    except Exception as e:
        print(f"Error scanning models directory: {e}")
    
    return models


async def vllm_chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    stream: bool = False
) -> Dict[str, Any]:
    """Send chat completion request to vLLM."""
    # If no model specified, try to get the first available
    if not model:
        models = await vllm_list_models()
        model = models[0] if models else "/models/medium/general/qwen2.5-7b-gptq"

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream
    }

    start_time = time.time()

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
            async with session.post(
                f"{VLLM_BASE_URL}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    return {"error": f"vLLM error: {error_text}", "model": model}

                data = await resp.json()
                choice = data.get("choices", [{}])[0]
                message = choice.get("message", {})
                usage = data.get("usage", {})

                latency_ms = (time.time() - start_time) * 1000
                completion_tokens = usage.get("completion_tokens", 0)
                prompt_tokens = usage.get("prompt_tokens", 0)
                
                # Calculate tokens per second
                tokens_per_second = 0.0
                if latency_ms > 0 and completion_tokens > 0:
                    tokens_per_second = (completion_tokens / latency_ms) * 1000

                return {
                    "content": message.get("content", ""),
                    "model": model,
                    "latency_ms": latency_ms,
                    "finish_reason": choice.get("finish_reason", ""),
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "tokens_per_second": tokens_per_second
                }
    except asyncio.TimeoutError:
        return {"error": "Request timeout", "model": model}
    except Exception as e:
        return {"error": str(e), "model": model}


async def vllm_chat_stream(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048
):
    """Stream chat completion from vLLM."""
    if not model:
        models = await vllm_list_models()
        model = models[0] if models else "/models/medium/general/qwen2.5-7b-gptq"

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True
    }

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
            async with session.post(
                f"{VLLM_BASE_URL}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status != 200:
                    yield f"data: {json.dumps({'error': 'vLLM error'})}\n\n"
                    return

                async for line in resp.content:
                    line_text = line.decode('utf-8').strip()
                    if line_text.startswith("data: "):
                        data = line_text[6:]
                        if data == "[DONE]":
                            yield "data: [DONE]\n\n"
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield f"data: {json.dumps({'content': content, 'model': model})}\n\n"
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


# =============================================================================
# Application Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print(f"🚀 Ryx API starting on port {API_PORT}")
    print(f"📡 vLLM backend: {VLLM_BASE_URL}")
    print(f"🔍 SearXNG: {SEARXNG_URL}")
    print(f"💾 Sessions dir: {SESSIONS_DIR}")

    # Load persisted sessions
    load_sessions()
    print(f"📂 Loaded {len(sessions)} sessions")

    # Check vLLM connection
    health = await vllm_health_check()
    if health["healthy"]:
        print("✅ vLLM connection: OK")
    else:
        print(f"⚠️  vLLM connection: {health['status']}")

    yield

    # Shutdown - save all sessions
    for session in sessions.values():
        save_session(session)
    print(f"💾 Saved {len(sessions)} sessions")
    print("👋 Ryx API shutting down")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Ryx AI API",
    version="2.1.0",
    description="REST and WebSocket API for RyxHub - vLLM backend",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health & Status Endpoints
# =============================================================================

@app.get("/api/health")
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    vllm_health = await vllm_health_check()
    return HealthResponse(
        status="healthy" if vllm_health["healthy"] else "degraded",
        version="2.1.0",
        uptime=int(time.time()),
        vllm_status=vllm_health["status"]
    )


@app.get("/api/status")
async def get_status() -> StatusResponse:
    """Get system status."""
    models = await vllm_list_models()
    
    # Try to get real GPU stats from vLLM metrics
    gpu_used = 8.5
    gpu_total = 16.0
    try:
        metrics = await get_vllm_metrics()
        if metrics:
            # Convert bytes to GB
            gpu_used = metrics.get("process_resident_memory_bytes", 0) / (1024**3)
    except:
        pass
    
    return StatusResponse(
        models_loaded=len(models),
        active_sessions=len([s for s in sessions.values() if s.isActive]),
        gpu_memory_used=gpu_used,
        gpu_memory_total=gpu_total,
        vllm_workers=1
    )


async def get_vllm_metrics() -> Dict[str, Any]:
    """Fetch and parse vLLM Prometheus metrics."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(f"{VLLM_BASE_URL}/metrics") as resp:
                if resp.status != 200:
                    return {}
                
                text = await resp.text()
                metrics = {}
                
                for line in text.split('\n'):
                    if line.startswith('#') or not line.strip():
                        continue
                    
                    # Parse metric line: name{labels} value
                    if ' ' in line:
                        parts = line.rsplit(' ', 1)
                        if len(parts) == 2:
                            metric_name = parts[0].split('{')[0]
                            try:
                                value = float(parts[1])
                                metrics[metric_name] = value
                            except ValueError:
                                pass
                
                return metrics
    except Exception:
        return {}


@app.get("/api/metrics/vllm")
async def get_vllm_metrics_endpoint() -> Dict[str, Any]:
    """Get detailed vLLM metrics for the metrics page."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(f"{VLLM_BASE_URL}/metrics") as resp:
                if resp.status != 200:
                    return {"error": "Failed to fetch metrics", "available": False}
                
                text = await resp.text()
                
                # Parse key metrics
                metrics = {
                    "available": True,
                    "memory": {},
                    "requests": {},
                    "tokens": {},
                    "cache": {},
                    "model": {}
                }
                
                for line in text.split('\n'):
                    if line.startswith('#') or not line.strip():
                        continue
                    
                    try:
                        # Parse metric
                        if ' ' not in line:
                            continue
                        parts = line.rsplit(' ', 1)
                        value = float(parts[1])
                        metric_key = parts[0]
                        
                        # Memory metrics
                        if 'process_resident_memory_bytes' in metric_key:
                            metrics["memory"]["resident_gb"] = round(value / (1024**3), 2)
                        elif 'process_virtual_memory_bytes' in metric_key:
                            metrics["memory"]["virtual_gb"] = round(value / (1024**3), 2)
                        
                        # Request metrics
                        elif 'vllm:num_requests_running' in metric_key:
                            metrics["requests"]["running"] = int(value)
                        elif 'vllm:num_requests_waiting' in metric_key:
                            metrics["requests"]["waiting"] = int(value)
                        elif 'vllm:request_success_total' in metric_key and 'stop' in metric_key:
                            metrics["requests"]["successful"] = int(value)
                        
                        # Token metrics
                        elif 'vllm:prompt_tokens_total' in metric_key:
                            metrics["tokens"]["prompt_total"] = int(value)
                        elif 'vllm:generation_tokens_total' in metric_key:
                            metrics["tokens"]["generation_total"] = int(value)
                        
                        # Cache metrics
                        elif 'vllm:kv_cache_usage_perc' in metric_key:
                            metrics["cache"]["kv_usage_percent"] = round(value * 100, 2)
                        elif 'vllm:prefix_cache_hits_total' in metric_key:
                            metrics["cache"]["prefix_hits"] = int(value)
                        elif 'vllm:prefix_cache_queries_total' in metric_key:
                            metrics["cache"]["prefix_queries"] = int(value)
                        
                        # Extract model name
                        if 'model_name="' in metric_key:
                            model_match = metric_key.split('model_name="')[1].split('"')[0]
                            metrics["model"]["name"] = model_match
                            metrics["model"]["short_name"] = model_match.split('/')[-1]
                            
                    except (ValueError, IndexError):
                        continue
                
                # Calculate derived metrics
                if metrics["cache"].get("prefix_queries", 0) > 0:
                    hit_rate = metrics["cache"].get("prefix_hits", 0) / metrics["cache"]["prefix_queries"] * 100
                    metrics["cache"]["hit_rate_percent"] = round(hit_rate, 1)
                
                metrics["tokens"]["total"] = (
                    metrics["tokens"].get("prompt_total", 0) + 
                    metrics["tokens"].get("generation_total", 0)
                )
                
                return metrics
                
    except Exception as e:
        return {"error": str(e), "available": False}


# =============================================================================
# Model Endpoints
# =============================================================================

@app.get("/api/models")
async def list_models() -> Dict[str, Any]:
    """List available models from vLLM and local directory."""
    # Get currently loaded models from vLLM
    loaded_model_ids = await vllm_list_models()
    loaded_models_set = set(loaded_model_ids)
    
    # Scan local models directory
    local_models = scan_local_models()
    
    # Combine and deduplicate
    models = []
    seen_ids = set()
    
    # First add loaded models
    for model_id in loaded_model_ids:
        if model_id not in seen_ids:
            name = model_id.split("/")[-1] if "/" in model_id else model_id
            models.append(ModelInfo(
                id=model_id,
                name=name,
                status="online",
                provider="vLLM"
            ))
            seen_ids.add(model_id)
    
    # Then add local models not yet loaded
    for local_model in local_models:
        model_id = local_model["id"]
        if model_id not in seen_ids:
            status = "online" if model_id in loaded_models_set else "offline"
            models.append(ModelInfo(
                id=model_id,
                name=local_model["name"],
                status=status,
                provider="vLLM"
            ))
            seen_ids.add(model_id)
    
    # If no models found, return a default message
    if not models:
        models.append(ModelInfo(
            id="no-models", 
            name="No Models Found", 
            status="offline", 
            provider="vLLM"
        ))
    
    return {
        "models": models,
        "loaded_count": len(loaded_model_ids),
        "available_count": len(local_models)
    }


@app.post("/api/models/load")
async def load_model(data: Dict[str, str]) -> Dict[str, Any]:
    """
    Load a model in vLLM.
    
    Note: vLLM typically loads one model at startup via docker-compose.
    To switch models, you need to restart the vLLM container with a different model.
    This endpoint checks if the requested model is already loaded.
    """
    model_id = data.get("model_id")
    
    if not model_id:
        return {"success": False, "message": "model_id is required"}
    
    # Check if model is already loaded
    loaded_models = await vllm_list_models()
    
    if model_id in loaded_models:
        return {
            "success": True, 
            "message": f"Model {model_id} is already loaded",
            "status": "connected"
        }
    
    # Check if model exists locally
    local_models = scan_local_models()
    model_exists = any(m["id"] == model_id for m in local_models)
    
    if not model_exists:
        return {
            "success": False,
            "message": f"Model {model_id} not found in local directory",
            "status": "not_found"
        }
    
    return {
        "success": False,
        "message": f"To load {model_id}, restart vLLM container with this model. vLLM supports one model at a time.",
        "status": "requires_restart",
        "instructions": f"Update docker-compose.yml to use: --model {model_id}"
    }


@app.post("/api/models/unload")
async def unload_model(data: Dict[str, str]) -> Dict[str, Any]:
    """
    Unload a model from vLLM.
    
    Note: vLLM doesn't support dynamic unloading. 
    The model stays loaded until the container is stopped.
    """
    model_id = data.get("model_id")
    
    if not model_id:
        return {"success": False, "message": "model_id is required"}
    
    return {
        "success": False,
        "message": f"vLLM doesn't support dynamic unloading. Stop the vLLM container to unload {model_id}",
        "status": "not_supported"
    }


@app.get("/api/models/{model_id:path}/status")
async def get_model_status(model_id: str) -> Dict[str, Any]:
    """Get the status of a specific model."""
    # URL decode the model_id
    from urllib.parse import unquote
    model_id = unquote(model_id)
    
    loaded_models = await vllm_list_models()
    
    is_loaded = model_id in loaded_models
    
    if is_loaded:
        return {
            "id": model_id,
            "status": "online",
            "loaded": True,
            "message": "Model is loaded and ready"
        }
    
    # Check if it exists locally
    local_models = scan_local_models()
    exists_locally = any(m["id"] == model_id for m in local_models)
    
    if exists_locally:
        return {
            "id": model_id,
            "status": "offline",
            "loaded": False,
            "message": "Model is available but not loaded"
        }
    
    return {
        "id": model_id,
        "status": "not_found",
        "loaded": False,
        "message": "Model not found"
    }


# =============================================================================
# Session Endpoints
# =============================================================================

@app.get("/api/sessions")
async def list_sessions() -> Dict[str, List[Dict[str, Any]]]:
    """List all sessions."""
    return {"sessions": [s.dict() for s in sessions.values()]}


@app.post("/api/sessions")
async def create_session(data: Dict[str, str]) -> SessionInfo:
    """Create a new session."""
    session_id = f"session-{int(time.time())}"
    models = await vllm_list_models()
    model = data.get("model") or (models[0] if models else "default")

    session = SessionInfo(
        id=session_id,
        name=data.get("name", "New Session"),
        lastMessage="",
        timestamp="just now",
        isActive=True,
        model=model,
        agentId=f"agent-{session_id}",
        messages=[]
    )
    sessions[session_id] = session
    save_session(session)
    return session


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> SessionInfo:
    """Get session by ID."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]


@app.patch("/api/sessions/{session_id}")
async def update_session(session_id: str, data: Dict[str, Any]) -> SessionInfo:
    """Update session properties (name, model, etc)."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    # Update allowed fields
    if "name" in data:
        session.name = data["name"]
    if "model" in data:
        session.model = data["model"]
    
    save_session(session)
    return session


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str) -> Dict[str, str]:
    """Delete a session."""
    if session_id in sessions:
        del sessions[session_id]
        delete_session_file(session_id)
    return {"status": "deleted"}


# =============================================================================
# Chat/Message Endpoints
# =============================================================================

@app.post("/api/sessions/{session_id}/messages")
async def send_message(session_id: str, request: MessageRequest) -> MessageResponse:
    """Send a message and get AI response."""
    # Get or create session
    if session_id not in sessions:
        # Auto-create session
        models = await vllm_list_models()
        model = request.model or (models[0] if models else "default")
        sessions[session_id] = SessionInfo(
            id=session_id,
            name="Chat Session",
            lastMessage="",
            timestamp="just now",
            isActive=True,
            model=model,
            agentId=f"agent-{session_id}",
            messages=[]
        )

    session = sessions[session_id]

    # Add user message to history
    user_msg = {
        "id": get_next_message_id(),
        "role": "user",
        "content": request.content,
        "timestamp": datetime.now().strftime("%H:%M")
    }
    session.messages.append(user_msg)

    # Build messages for vLLM
    messages = [{"role": "system", "content": "You are Ryx, a helpful AI assistant running on vLLM. Be concise and helpful."}]
    for msg in session.messages[-10:]:  # Last 10 messages for context
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Get response from vLLM
    result = await vllm_chat(
        messages=messages,
        model=request.model or session.model,
        max_tokens=2048
    )

    if "error" in result:
        content = f"⚠️ Error: {result['error']}\n\nPlease check if vLLM is running on {VLLM_BASE_URL}"
        model_used = "System"
    else:
        content = result["content"]
        model_used = result["model"]

    # Add assistant response to history
    assistant_msg = {
        "id": get_next_message_id(),
        "role": "assistant",
        "content": content,
        "timestamp": datetime.now().strftime("%H:%M"),
        "model": model_used,
        "latency_ms": result.get("latency_ms"),
        "tokens_per_second": result.get("tokens_per_second"),
    }
    session.messages.append(assistant_msg)
    session.lastMessage = content[:50] + "..." if len(content) > 50 else content
    session.timestamp = "just now"
    
    # Update model if switched mid-chat
    if request.model and request.model != session.model:
        session.model = request.model
    
    # Persist session
    save_session(session)

    return MessageResponse(
        id=assistant_msg["id"],
        role="assistant",
        content=content,
        timestamp=assistant_msg["timestamp"],
        model=model_used,
        latency_ms=result.get("latency_ms"),
        tokens_per_second=result.get("tokens_per_second"),
        prompt_tokens=result.get("prompt_tokens"),
        completion_tokens=result.get("completion_tokens")
    )


@app.get("/api/sessions/{session_id}/stream")
async def stream_chat(session_id: str, message: str, model: Optional[str] = None):
    """Stream chat response using SSE."""
    if session_id not in sessions:
        models = await vllm_list_models()
        m = model or (models[0] if models else "default")
        sessions[session_id] = SessionInfo(
            id=session_id,
            name="Stream Session",
            lastMessage="",
            timestamp="just now",
            isActive=True,
            model=m,
            agentId=f"agent-{session_id}",
            messages=[]
        )

    session = sessions[session_id]

    # Build messages
    messages = [{"role": "system", "content": "You are Ryx, a helpful AI assistant."}]
    for msg in session.messages[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": message})

    return StreamingResponse(
        vllm_chat_stream(messages, model or session.model),
        media_type="text/event-stream"
    )


@app.post("/api/sessions/import")
async def import_cli_session(data: Dict[str, Any]) -> SessionInfo:
    """
    Import a CLI session (from ryx terminal) into RyxHub.
    This enables syncing ryx CLI conversations to the web UI.
    
    Expected payload:
    {
        "name": "Session Name",
        "messages": [{"role": "user/assistant", "content": "..."}, ...],
        "model": "model-name"
    }
    """
    session_id = f"cli-session-{int(time.time())}"
    
    # Convert messages to proper format
    imported_messages = []
    for msg in data.get("messages", []):
        imported_messages.append({
            "id": get_next_message_id(),
            "role": msg.get("role", "user"),
            "content": msg.get("content", ""),
            "timestamp": msg.get("timestamp", datetime.now().strftime("%H:%M")),
            "model": msg.get("model")
        })
    
    session = SessionInfo(
        id=session_id,
        name=data.get("name", f"Imported from CLI - {datetime.now().strftime('%Y-%m-%d %H:%M')}"),
        lastMessage=imported_messages[-1]["content"][:50] + "..." if imported_messages else "",
        timestamp="just now",
        isActive=False,
        model=data.get("model", "default"),
        agentId=f"cli-agent-{session_id}",
        messages=imported_messages
    )
    
    sessions[session_id] = session
    save_session(session)
    
    return session


# =============================================================================
# RAG Endpoints
# =============================================================================

@app.get("/api/rag/status")
async def get_rag_status() -> RAGStatus:
    """Get RAG index status."""
    try:
        from core.rag_system import RAGSystem
        rag = RAGSystem()
        stats = rag.get_stats() if hasattr(rag, 'get_stats') else {}
        rag.close()
        return RAGStatus(
            indexed=stats.get("indexed", 0),
            pending=stats.get("pending", 0),
            lastSync=stats.get("last_sync", "never"),
            status=stats.get("status", "idle")
        )
    except Exception:
        return RAGStatus(indexed=0, pending=0, lastSync="never", status="unavailable")


@app.post("/api/rag/sync")
async def trigger_rag_sync() -> Dict[str, Any]:
    """Trigger RAG sync."""
    try:
        from core.rag_system import RAGSystem
        rag = RAGSystem()
        result = rag.sync() if hasattr(rag, 'sync') else {"queued": 0}
        rag.close()
        return {"success": True, "queued_files": result.get("queued", 0)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/rag/search")
async def search_rag(data: Dict[str, Any]) -> Dict[str, Any]:
    """Search RAG index."""
    query = data.get("query", "")
    top_k = data.get("top_k", 5)

    try:
        from core.rag_system import RAGSystem
        rag = RAGSystem()
        results = rag.search(query, top_k=top_k) if hasattr(rag, 'search') else []
        rag.close()
        return {"results": results, "total": len(results)}
    except Exception:
        return {"results": [], "total": 0}


# =============================================================================
# SearXNG Endpoints
# =============================================================================

async def searxng_health_check() -> Dict[str, Any]:
    """Check SearXNG server health."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(f"{SEARXNG_URL}") as resp:
                if resp.status == 200:
                    return {"healthy": True, "status": "online"}
                return {"healthy": False, "status": f"HTTP {resp.status}"}
    except Exception as e:
        return {"healthy": False, "status": str(e)}


@app.get("/api/searxng/status")
async def get_searxng_status() -> Dict[str, Any]:
    """Get SearXNG service status."""
    health = await searxng_health_check()
    return {
        "url": SEARXNG_URL,
        "healthy": health["healthy"],
        "status": health["status"],
        "message": "SearXNG is online" if health["healthy"] else f"SearXNG is offline: {health['status']}"
    }


@app.post("/api/searxng/search")
async def searxng_search(data: Dict[str, Any]) -> Dict[str, Any]:
    """Search via SearXNG."""
    query = data.get("query", "")
    
    if not query:
        return {"results": [], "error": "Query is required"}
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            params = {
                "q": query,
                "format": "json",
                "language": "en"
            }
            
            async with session.get(f"{SEARXNG_URL}/search", params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("results", [])
                    return {
                        "results": results[:10],  # Top 10 results
                        "total": len(results),
                        "query": query
                    }
                else:
                    error_text = await resp.text()
                    return {
                        "results": [],
                        "error": f"SearXNG returned status {resp.status}: {error_text}"
                    }
    except Exception as e:
        return {
            "results": [],
            "error": f"Failed to search: {str(e)}"
        }


# =============================================================================
# Workflow Endpoints
# =============================================================================

@app.get("/api/workflows")
async def list_workflows() -> Dict[str, List[WorkflowInfo]]:
    """List available workflows."""
    # TODO: Load from workflow storage
    return {"workflows": [
        WorkflowInfo(id="wf-1", name="PR Review", status="idle", lastRun="2h ago"),
        WorkflowInfo(id="wf-2", name="Code Analysis", status="idle", lastRun="4h ago"),
    ]}


@app.get("/api/workflows/{workflow_id}")
async def get_workflow(workflow_id: str) -> Dict[str, Any]:
    """Get workflow details."""
    # TODO: Load workflow from storage
    return {
        "id": workflow_id,
        "name": "Sample Workflow",
        "status": "idle",
        "lastRun": "never",
        "nodes": [],
        "connections": []
    }


@app.post("/api/workflows/{workflow_id}/run")
async def run_workflow(workflow_id: str) -> Dict[str, Any]:
    """Run a workflow."""
    return {"success": True, "run_id": f"run-{int(time.time())}"}


@app.post("/api/workflows/{workflow_id}/pause")
async def pause_workflow(workflow_id: str) -> Dict[str, str]:
    """Pause a running workflow."""
    return {"status": "paused"}


# =============================================================================
# Agent Endpoints
# =============================================================================

@app.get("/api/agents")
async def list_agents() -> Dict[str, List[AgentInfo]]:
    """List available agents."""
    models = await vllm_list_models()
    default_model = models[0] if models else "default"

    return {"agents": [
        AgentInfo(id="agent-1", name="Code Analyzer", status="active", model=default_model),
        AgentInfo(id="agent-2", name="Research Agent", status="idle", model=default_model),
    ]}


@app.get("/api/agents/{agent_id}/logs")
async def get_agent_logs(agent_id: str, lines: int = 50) -> Dict[str, List[Dict[str, str]]]:
    """Get agent logs."""
    return {"logs": [
        {"time": "10:00:00", "level": "info", "message": f"Agent {agent_id} initialized"},
        {"time": "10:00:01", "level": "info", "message": "Ready to process requests"},
    ]}


# =============================================================================
# Tool Endpoints
# =============================================================================

@app.get("/api/tools")
async def list_tools() -> Dict[str, List[Dict[str, Any]]]:
    """List available tools."""
    return {"tools": [
        {"id": "rag-search", "name": "RAG Search", "description": "Search knowledge base", "parameters": {}},
        {"id": "web-search", "name": "Web Search", "description": "Search the web via SearXNG", "parameters": {}},
        {"id": "code-exec", "name": "Code Executor", "description": "Execute code safely", "parameters": {}},
    ]}


@app.post("/api/tools/{tool_name}/dry-run")
async def tool_dry_run(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Dry run a tool."""
    return {"result": {"tool": tool_name, "params": params, "dry_run": True}}


# =============================================================================
# WebSocket Endpoints
# =============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates and streaming chat."""
    await websocket.accept()

    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to Ryx API",
            "vllm_status": (await vllm_health_check())["status"]
        })

        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "chat":
                # Stream chat response
                session_id = data.get("session_id", "ws-session")
                message = data.get("message", "")
                model = data.get("model")

                messages = [
                    {"role": "system", "content": "You are Ryx, a helpful AI assistant."},
                    {"role": "user", "content": message}
                ]

                full_response = ""
                async for chunk in vllm_chat_stream(messages, model):
                    if chunk.startswith("data: "):
                        chunk_data = chunk[6:].strip()
                        if chunk_data and chunk_data != "[DONE]":
                            try:
                                parsed = json.loads(chunk_data)
                                if "content" in parsed:
                                    full_response += parsed["content"]
                                    await websocket.send_json({
                                        "type": "token",
                                        "content": parsed["content"],
                                        "model": parsed.get("model")
                                    })
                            except json.JSONDecodeError:
                                pass

                await websocket.send_json({
                    "type": "complete",
                    "content": full_response,
                    "model": model
                })

            elif action == "ping":
                await websocket.send_json({"type": "pong"})

            elif action == "status":
                health = await vllm_health_check()
                models = await vllm_list_models()
                await websocket.send_json({
                    "type": "status",
                    "vllm_healthy": health["healthy"],
                    "models": models
                })

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown action: {action}"
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass


@app.websocket("/api/workflow/stream")
async def workflow_stream(websocket: WebSocket):
    """WebSocket for workflow execution streaming."""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("action") == "execute_workflow":
                workflow_id = data.get("workflow_id")

                # Simulate workflow steps
                steps = ["Parsing input", "Loading context", "Processing", "Generating output"]

                for i, step in enumerate(steps, 1):
                    await websocket.send_json({
                        "type": "step_start",
                        "step": i,
                        "action": step,
                        "timestamp": datetime.now().isoformat()
                    })
                    await asyncio.sleep(0.5)
                    await websocket.send_json({
                        "type": "step_complete",
                        "step": i,
                        "latency_ms": 100 + i * 50
                    })

                await websocket.send_json({
                    "type": "workflow_complete",
                    "workflow_id": workflow_id,
                    "total_latency_ms": 500
                })
            else:
                await websocket.send_json({"type": "acknowledged", "data": data})

    except WebSocketDisconnect:
        pass


# =============================================================================
# Service Management Endpoints
# =============================================================================

@app.post("/api/services/start")
async def start_service(data: Dict[str, str]) -> Dict[str, Any]:
    """Start a service."""
    service = data.get("service", "").lower()

    try:
        from core.docker_services import start_service as docker_start
        result = docker_start(service)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/services/stop")
async def stop_service(data: Dict[str, str]) -> Dict[str, Any]:
    """Stop a service."""
    service = data.get("service", "").lower()

    try:
        from core.docker_services import stop_service as docker_stop
        result = docker_stop(service)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/services/status")
async def get_services_status() -> Dict[str, Any]:
    """Get status of all services."""
    try:
        from core.docker_services import service_status
        return service_status()
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)
