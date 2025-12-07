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
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import aiohttp

# Import model router for multi-instance support
try:
    from core.model_router import router as model_router
    MULTI_MODEL_ENABLED = True
except ImportError:
    MULTI_MODEL_ENABLED = False
    print("⚠️  Model router not available - using single instance mode")

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
    path: Optional[str] = None
    size: Optional[str] = None
    category: Optional[str] = None


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
    tools: Dict[str, bool] = {}


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


# =============================================================================
# Workflow Persistence
# =============================================================================

WORKFLOWS_DIR = Path(os.environ.get("WORKFLOWS_DIR", PROJECT_ROOT / "data" / "workflows"))
WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)

workflows: Dict[str, Dict[str, Any]] = {}
workflow_runs: Dict[str, Dict[str, Any]] = {}


def save_workflow(workflow: Dict[str, Any]) -> None:
    """Persist workflow to disk."""
    try:
        workflow_file = WORKFLOWS_DIR / f"{workflow['id']}.json"
        with open(workflow_file, 'w') as f:
            json.dump(workflow, f, indent=2, default=str)
    except Exception as e:
        print(f"Failed to save workflow {workflow['id']}: {e}")


def load_workflows() -> None:
    """Load all workflows from disk on startup."""
    global workflows
    try:
        for workflow_file in WORKFLOWS_DIR.glob("*.json"):
            try:
                with open(workflow_file) as f:
                    data = json.load(f)
                    workflows[data['id']] = data
            except Exception as e:
                print(f"Failed to load workflow {workflow_file}: {e}")
    except Exception as e:
        print(f"Failed to scan workflows: {e}")


def delete_workflow_file(workflow_id: str) -> None:
    """Delete workflow file from disk."""
    try:
        workflow_file = WORKFLOWS_DIR / f"{workflow_id}.json"
        if workflow_file.exists():
            workflow_file.unlink()
    except Exception as e:
        print(f"Failed to delete workflow file {workflow_id}: {e}")


# =============================================================================
# Activity Log
# =============================================================================

activity_log: List[Dict[str, Any]] = []
MAX_ACTIVITY_LOG = 100


def log_activity(activity_type: str, message: str) -> None:
    """Log an activity event."""
    global activity_log
    activity_log.insert(0, {
        "id": len(activity_log) + 1,
        "type": activity_type,
        "message": message,
        "time": datetime.now().strftime("%H:%M:%S"),
        "timestamp": datetime.now().isoformat()
    })
    # Keep only the last MAX_ACTIVITY_LOG items
    if len(activity_log) > MAX_ACTIVITY_LOG:
        activity_log = activity_log[:MAX_ACTIVITY_LOG]


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
    """Send chat completion request to vLLM (routes to correct instance if multi-model)."""
    # If no model specified, try to get the first available
    if not model:
        if MULTI_MODEL_ENABLED:
            model = model_router.default_instance
        else:
            models = await vllm_list_models()
            model = models[0] if models else "/models/medium/general/qwen2.5-7b-gptq"

    # Determine the base URL
    if MULTI_MODEL_ENABLED:
        instance = model_router.get_instance(model)
        base_url = instance.base_url
    else:
        base_url = VLLM_BASE_URL

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
                f"{base_url}/v1/chat/completions",
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

    # Load persisted workflows
    load_workflows()
    print(f"🔄 Loaded {len(workflows)} workflows")

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


@app.get("/api/stats/dashboard")
async def get_dashboard_stats() -> Dict[str, Any]:
    """Get dashboard statistics."""
    models = await vllm_list_models()
    active_agents = len(models)
    
    # Count running workflows
    running_workflows = sum(1 for wf in workflows.values() if wf.get("status") == "running")
    queued_workflows = sum(1 for wf in workflows.values() if wf.get("status") == "queued")
    
    # Get RAG documents count
    rag_status = await get_rag_status_data()
    
    # Count total activity events (as proxy for API calls)
    # In production, this should track actual API request counts
    api_calls = len(activity_log)
    
    return {
        "activeAgents": {
            "value": active_agents,
            "change": "+0 today"  # Would need historical tracking to show real change
        },
        "workflowsRunning": {
            "value": running_workflows,
            "queued": queued_workflows
        },
        "ragDocuments": {
            "value": rag_status["indexed"],
            "pending": rag_status["pending"]
        },
        "apiCalls": {
            "value": f"{api_calls / 1000:.1f}K" if api_calls > 1000 else str(api_calls),
            "period": "Last 24h"
        }
    }


@app.get("/api/activity/recent")
async def get_recent_activity(limit: int = Query(default=10, le=100)) -> Dict[str, List[Dict[str, Any]]]:
    """Get recent activity log."""
    return {"activities": activity_log[:limit]}


@app.get("/api/workflows/top")
async def get_top_workflows(limit: int = Query(default=5, le=20)) -> Dict[str, List[Dict[str, Any]]]:
    """Get top workflows by run count."""
    # Calculate workflow stats
    workflow_stats = []
    for wf_id, wf in workflows.items():
        runs = wf.get("runs", [])
        total_runs = len(runs)
        successful_runs = sum(1 for r in runs if r.get("status") == "success")
        success_rate = int((successful_runs / total_runs * 100)) if total_runs > 0 else 0
        
        workflow_stats.append({
            "name": wf.get("name", wf_id),
            "runs": total_runs,
            "successRate": success_rate
        })
    
    # Sort by runs and take top N
    workflow_stats.sort(key=lambda x: x["runs"], reverse=True)
    return {"workflows": workflow_stats[:limit]}


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
    if MULTI_MODEL_ENABLED:
        # Use model router to check all instances
        health_status = await model_router.check_all_health()
        router_instances = model_router.list_models()

        models = []
        loaded_count = 0

        for instance in router_instances:
            is_online = health_status.get(instance.model_id, False)
            if is_online:
                loaded_count += 1

            models.append(ModelInfo(
                id=instance.model_id,
                name=instance.name,
                status="online" if is_online else "offline",
                provider="vLLM",
                path=instance.model_id,
                size=instance.size,
                category=instance.category
            ))

        # Also scan for other local models not in router config
        local_models = scan_local_models()
        seen_ids = {m.id for m in models}

        for local_model in local_models:
            if local_model["id"] not in seen_ids:
                models.append(ModelInfo(
                    id=local_model["id"],
                    name=local_model["name"],
                    status="offline",
                    provider="vLLM",
                    path=local_model.get("path"),
                    size=local_model.get("size"),
                    category=local_model.get("category")
                ))

        return {
            "models": models,
            "loaded_count": loaded_count,
            "available_count": len(models),
            "multi_model_enabled": True
        }
    else:
        # Fallback to single instance mode
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
                # Extract size and category from path if available
                path_parts = model_id.split("/")
                size = path_parts[2] if len(path_parts) > 2 else None
                category = path_parts[3] if len(path_parts) > 3 else None
                models.append(ModelInfo(
                    id=model_id,
                    name=name,
                    status="online",
                    provider="vLLM",
                    path=model_id,
                    size=size,
                    category=category
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
                    provider="vLLM",
                    path=local_model.get("path"),
                    size=local_model.get("size"),
                    category=local_model.get("category")
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
            "available_count": len(local_models),
            "multi_model_enabled": False
        }


@app.post("/api/models/load")
async def load_model(data: Dict[str, str]) -> Dict[str, Any]:
    """
    Load a model in vLLM.

    With multi-model mode: Starts the corresponding vLLM instance.
    With single-model mode: Requires container restart.
    """
    model_id = data.get("model_id")

    if not model_id:
        return {"success": False, "message": "model_id is required"}

    if MULTI_MODEL_ENABLED:
        # Use model router to start instance
        result = await model_router.start_instance(model_id)
        return result
    else:
        # Single instance mode - check if model is already loaded
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
            "message": f"To load {model_id}, restart vLLM container with this model. Enable multi-model mode for dynamic switching.",
            "status": "requires_restart",
            "instructions": f"docker-compose -f docker/vllm/model-router.yml up -d"
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
    log_activity("success", f"Session '{session.name}' created")
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
        session_name = sessions[session_id].name
        del sessions[session_id]
        delete_session_file(session_id)
        log_activity("warning", f"Session '{session_name}' deleted")
    return {"status": "deleted"}


@app.put("/api/sessions/{session_id}/tools")
async def update_session_tools(session_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update tool state for a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    tool_id = data.get("toolId")
    enabled = data.get("enabled", False)
    
    if not tool_id:
        raise HTTPException(status_code=400, detail="toolId is required")
    
    # Store tool state in session metadata (tools field is initialized in SessionInfo)
    session.tools[tool_id] = enabled
    save_session(session)
    
    log_activity("info", f"Session '{session.name}': tool '{tool_id}' {'enabled' if enabled else 'disabled'}")
    
    return {
        "success": True,
        "sessionId": session_id,
        "tools": session.tools
    }


@app.get("/api/sessions/{session_id}/export")
async def export_session(session_id: str, format: str = Query(default="json")) -> Dict[str, Any]:
    """Export a session in various formats."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    if format == "markdown":
        # Convert session to markdown
        md_content = f"# {session.name}\n\n"
        md_content += f"**Model:** {session.model}\n"
        md_content += f"**Date:** {session.timestamp}\n\n"
        md_content += "---\n\n"
        
        for msg in session.messages:
            role = "**User:**" if msg["role"] == "user" else "**Assistant:**"
            md_content += f"{role}\n{msg['content']}\n\n"
        
        return {
            "format": "markdown",
            "content": md_content,
            "filename": f"{session.name.replace(' ', '_')}.md"
        }
    
    # Default: JSON format
    return {
        "format": "json",
        "content": session.dict(),
        "filename": f"{session.name.replace(' ', '_')}.json"
    }


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

    # Build messages for vLLM with current date
    today = datetime.now()
    date_str = today.strftime("%A, %d. %B %Y")
    time_str = today.strftime("%H:%M")
    system_content = f"You are Ryx, a helpful AI assistant. Today is {date_str}, current time: {time_str}. Be concise and helpful."
    messages = [{"role": "system", "content": system_content}]
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

async def get_rag_status_data() -> Dict[str, Any]:
    """Get RAG status as dictionary (internal helper)."""
    try:
        from core.rag_system import RAGSystem
        rag = RAGSystem()
        stats = rag.get_stats() if hasattr(rag, 'get_stats') else {}
        rag.close()
        return {
            "indexed": stats.get("indexed", 0),
            "pending": stats.get("pending", 0),
            "lastSync": stats.get("last_sync", "never"),
            "status": stats.get("status", "idle")
        }
    except Exception:
        return {"indexed": 0, "pending": 0, "lastSync": "never", "status": "unavailable"}


@app.get("/api/rag/status")
async def get_rag_status() -> RAGStatus:
    """Get RAG index status."""
    data = await get_rag_status_data()
    return RAGStatus(**data)


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


@app.post("/api/rag/upload")
async def upload_rag_documents() -> Dict[str, Any]:
    """Upload documents to RAG index.
    
    Note: This endpoint is a placeholder for future implementation.
    In a real implementation, this would:
    1. Accept multipart/form-data file uploads
    2. Save uploaded files to a staging directory
    3. Queue them for processing and embedding
    4. Add to vector store
    """
    try:
        log_activity("info", "Document upload requested (endpoint not fully implemented)")
        return {"success": True, "message": "Upload endpoint ready for implementation", "count": 0}
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
        log_activity("info", f"RAG search: '{query[:50]}'")
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

class WorkflowRequest(BaseModel):
    """Request model for creating/updating workflow."""
    name: str
    nodes: List[Dict[str, Any]] = []
    connections: List[Dict[str, Any]] = []
    status: str = "idle"


@app.get("/api/workflows")
async def list_workflows() -> Dict[str, List[Dict[str, Any]]]:
    """List available workflows."""
    workflow_list = []
    for wf_id, wf in workflows.items():
        last_run = "never"
        runs = wf.get("runs", [])
        if runs:
            # Get the most recent run
            last_run_time = runs[-1].get("timestamp", "never")
            try:
                run_dt = datetime.fromisoformat(last_run_time)
                diff = datetime.now() - run_dt
                if diff.seconds < 60:
                    last_run = "just now"
                elif diff.seconds < 3600:
                    last_run = f"{diff.seconds // 60}m ago"
                elif diff.total_seconds() < 86400:
                    last_run = f"{int(diff.total_seconds() // 3600)}h ago"
                else:
                    last_run = f"{diff.days}d ago"
            except:
                pass
        
        workflow_list.append({
            "id": wf_id,
            "name": wf.get("name", wf_id),
            "status": wf.get("status", "idle"),
            "lastRun": last_run,
            "nodeCount": len(wf.get("nodes", [])),
            "connectionCount": len(wf.get("connections", []))
        })
    
    return {"workflows": workflow_list}


@app.post("/api/workflows")
async def create_workflow(workflow: WorkflowRequest) -> Dict[str, Any]:
    """Create a new workflow."""
    workflow_id = f"wf-{int(time.time())}"
    workflow_data = {
        "id": workflow_id,
        "name": workflow.name,
        "nodes": workflow.nodes,
        "connections": workflow.connections,
        "status": workflow.status,
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
        "runs": []
    }
    
    workflows[workflow_id] = workflow_data
    save_workflow(workflow_data)
    log_activity("success", f"Workflow '{workflow.name}' created")
    
    return {"success": True, "workflow": workflow_data}


@app.get("/api/workflows/{workflow_id}")
async def get_workflow(workflow_id: str) -> Dict[str, Any]:
    """Get workflow details."""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return workflows[workflow_id]


@app.put("/api/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, workflow: WorkflowRequest) -> Dict[str, Any]:
    """Update an existing workflow."""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    existing = workflows[workflow_id]
    existing.update({
        "name": workflow.name,
        "nodes": workflow.nodes,
        "connections": workflow.connections,
        "status": workflow.status,
        "updated": datetime.now().isoformat()
    })
    
    workflows[workflow_id] = existing
    save_workflow(existing)
    log_activity("info", f"Workflow '{workflow.name}' updated")
    
    return {"success": True, "workflow": existing}


@app.delete("/api/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str) -> Dict[str, bool]:
    """Delete a workflow."""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow_name = workflows[workflow_id].get("name", workflow_id)
    del workflows[workflow_id]
    delete_workflow_file(workflow_id)
    log_activity("warning", f"Workflow '{workflow_name}' deleted")
    
    return {"success": True}


@app.post("/api/workflows/{workflow_id}/run")
async def run_workflow(workflow_id: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Run a workflow."""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = workflows[workflow_id]
    run_id = f"run-{workflow_id}-{int(time.time())}"
    
    # Create run record
    run_record = {
        "id": run_id,
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "startTime": datetime.now().isoformat(),
        "parameters": params or {}
    }
    
    if "runs" not in workflow:
        workflow["runs"] = []
    workflow["runs"].append(run_record)
    workflow["status"] = "running"
    
    # Store run in global runs dict for WebSocket access
    # Only store reference to workflow, not the full data
    workflow_runs[run_id] = {
        "id": run_id,
        "workflow_id": workflow_id,
        "status": "running",
        "logs": [],
        "node_statuses": {},
        "startTime": datetime.now().isoformat()
    }
    
    save_workflow(workflow)
    log_activity("info", f"Workflow '{workflow.get('name')}' started")
    
    # Start workflow execution asynchronously
    asyncio.create_task(execute_workflow(run_id, workflow))
    
    return {
        "success": True,
        "runId": run_id,
        "status": "running",
        "startedAt": datetime.now().isoformat()
    }


@app.post("/api/workflows/{workflow_id}/pause")
async def pause_workflow(workflow_id: str) -> Dict[str, str]:
    """Pause a running workflow."""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = workflows[workflow_id]
    workflow["status"] = "paused"
    save_workflow(workflow)
    log_activity("warning", f"Workflow '{workflow.get('name')}' paused")
    
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
# Workflow Execution Engine
# =============================================================================

# WebSocket connection managers
workflow_ws_connections: Dict[str, set] = {}  # run_id -> set of WebSocket connections
scraping_ws_connections: Dict[str, set] = {}  # tool_id -> set of WebSocket connections


async def execute_workflow(run_id: str, workflow: Dict[str, Any]) -> None:
    """Execute a workflow and broadcast updates via WebSocket."""
    try:
        nodes = workflow.get("nodes", [])
        connections = workflow.get("connections", [])
        
        # Send workflow started event
        await broadcast_workflow_event(run_id, {
            "type": "workflow_status",
            "status": "running",
            "timestamp": datetime.now().isoformat()
        })
        
        await broadcast_workflow_log(run_id, {
            "level": "info",
            "message": "🚀 Workflow execution started",
            "timestamp": datetime.now().isoformat()
        })
        
        # Execute nodes sequentially (in real implementation, follow connections)
        for node in nodes:
            node_id = node.get("id")
            node_type = node.get("type")
            node_name = node.get("name", node_id)
            
            # Update node status to running
            await broadcast_workflow_event(run_id, {
                "type": "node_status",
                "nodeId": node_id,
                "status": "running",
                "timestamp": datetime.now().isoformat()
            })
            
            await broadcast_workflow_log(run_id, {
                "level": "info",
                "message": f"⚙️ Executing {node_type}: '{node_name}'",
                "nodeId": node_id,
                "timestamp": datetime.now().isoformat()
            })
            
            # Simulate node execution
            await asyncio.sleep(1)
            
            # Node-specific actions
            if node_type == "agent":
                model = node.get("config", {}).get("model", "default")
                await broadcast_workflow_log(run_id, {
                    "level": "info",
                    "message": f"🤖 Agent processing with {model}...",
                    "nodeId": node_id,
                    "timestamp": datetime.now().isoformat()
                })
                await asyncio.sleep(1)
                
            elif node_type == "tool":
                tool_type = node.get("config", {}).get("toolType")
                if tool_type == "scrape":
                    await broadcast_workflow_log(run_id, {
                        "level": "info",
                        "message": "🌐 Scraping web content...",
                        "nodeId": node_id,
                        "timestamp": datetime.now().isoformat()
                    })
                    # Simulate scraping progress
                    await broadcast_scraping_progress(node_id, {
                        "url": "https://example.com",
                        "status": "scraping",
                        "progress": 50,
                        "items": [],
                        "totalItems": 10,
                        "timestamp": datetime.now().isoformat()
                    })
                    await asyncio.sleep(1)
                    await broadcast_scraping_progress(node_id, {
                        "url": "https://example.com",
                        "status": "success",
                        "progress": 100,
                        "items": [{"type": "text", "content": "Sample content", "selector": "article > p"}],
                        "totalItems": 10,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                elif tool_type == "websearch":
                    await broadcast_workflow_log(run_id, {
                        "level": "info",
                        "message": "🔍 Searching via SearXNG...",
                        "nodeId": node_id,
                        "timestamp": datetime.now().isoformat()
                    })
                    await asyncio.sleep(1)
                    
                elif tool_type == "rag":
                    await broadcast_workflow_log(run_id, {
                        "level": "info",
                        "message": "📚 Querying RAG database...",
                        "nodeId": node_id,
                        "timestamp": datetime.now().isoformat()
                    })
                    await asyncio.sleep(1)
            
            # Mark node as success
            await broadcast_workflow_event(run_id, {
                "type": "node_status",
                "nodeId": node_id,
                "status": "success",
                "timestamp": datetime.now().isoformat()
            })
            
            await broadcast_workflow_log(run_id, {
                "level": "success",
                "message": f"✅ Completed {node_type}: '{node_name}'",
                "nodeId": node_id,
                "timestamp": datetime.now().isoformat()
            })
        
        # Workflow completed
        await broadcast_workflow_event(run_id, {
            "type": "workflow_status",
            "status": "success",
            "timestamp": datetime.now().isoformat()
        })
        
        await broadcast_workflow_log(run_id, {
            "level": "success",
            "message": "🎉 Workflow completed successfully",
            "timestamp": datetime.now().isoformat()
        })
        
        # Update run status
        if run_id in workflow_runs:
            workflow_runs[run_id]["status"] = "success"
            workflow_runs[run_id]["endTime"] = datetime.now().isoformat()
        
    except Exception as e:
        # Workflow failed
        await broadcast_workflow_event(run_id, {
            "type": "workflow_status",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })
        
        await broadcast_workflow_log(run_id, {
            "level": "error",
            "message": f"❌ Workflow failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })
        
        if run_id in workflow_runs:
            workflow_runs[run_id]["status"] = "error"
            workflow_runs[run_id]["error"] = str(e)


async def broadcast_workflow_event(run_id: str, event: Dict[str, Any]) -> None:
    """Broadcast workflow event to all connected WebSocket clients."""
    if run_id not in workflow_ws_connections:
        return
    
    disconnected = set()
    for ws in workflow_ws_connections[run_id]:
        try:
            await ws.send_json(event)
        except Exception:
            disconnected.add(ws)
    
    # Remove disconnected clients
    for ws in disconnected:
        workflow_ws_connections[run_id].discard(ws)


async def broadcast_workflow_log(run_id: str, log: Dict[str, Any]) -> None:
    """Broadcast workflow log to all connected WebSocket clients."""
    await broadcast_workflow_event(run_id, {
        "type": "log",
        **log
    })


async def broadcast_scraping_progress(tool_id: str, progress: Dict[str, Any]) -> None:
    """Broadcast scraping progress to all connected WebSocket clients."""
    if tool_id not in scraping_ws_connections:
        return
    
    disconnected = set()
    for ws in scraping_ws_connections[tool_id]:
        try:
            await ws.send_json({
                "type": "scraping_progress",
                **progress
            })
        except Exception:
            disconnected.add(ws)
    
    # Remove disconnected clients
    for ws in disconnected:
        scraping_ws_connections[tool_id].discard(ws)


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


@app.websocket("/ws/workflows/{run_id}")
async def workflow_execution_stream(websocket: WebSocket, run_id: str):
    """WebSocket for real-time workflow execution updates."""
    await websocket.accept()
    
    # Register connection
    if run_id not in workflow_ws_connections:
        workflow_ws_connections[run_id] = set()
    workflow_ws_connections[run_id].add(websocket)
    
    try:
        # Send initial status
        if run_id in workflow_runs:
            run_data = workflow_runs[run_id]
            await websocket.send_json({
                "type": "connected",
                "runId": run_id,
                "status": run_data.get("status", "running"),
                "timestamp": datetime.now().isoformat()
            })
        else:
            await websocket.send_json({
                "type": "error",
                "message": "Run not found",
                "runId": run_id
            })
            return
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_json()
                
                # Handle client messages if needed
                if data.get("action") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except Exception:
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        # Unregister connection
        if run_id in workflow_ws_connections:
            workflow_ws_connections[run_id].discard(websocket)
            if not workflow_ws_connections[run_id]:
                del workflow_ws_connections[run_id]


@app.websocket("/ws/workflows/{run_id}/logs")
async def workflow_logs_stream(websocket: WebSocket, run_id: str):
    """WebSocket for workflow execution logs."""
    await websocket.accept()
    
    # Register connection for both workflow events and logs
    if run_id not in workflow_ws_connections:
        workflow_ws_connections[run_id] = set()
    workflow_ws_connections[run_id].add(websocket)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "runId": run_id,
            "message": "Connected to logs stream",
            "timestamp": datetime.now().isoformat()
        })
        
        # Send historical logs if available
        if run_id in workflow_runs:
            for log in workflow_runs[run_id].get("logs", []):
                await websocket.send_json({
                    "type": "log",
                    **log
                })
        
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_json()
                
                if data.get("action") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except Exception:
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        if run_id in workflow_ws_connections:
            workflow_ws_connections[run_id].discard(websocket)


@app.websocket("/ws/scraping/{tool_id}")
async def scraping_progress_stream(websocket: WebSocket, tool_id: str):
    """WebSocket for scraping progress updates."""
    await websocket.accept()
    
    # Register connection
    if tool_id not in scraping_ws_connections:
        scraping_ws_connections[tool_id] = set()
    scraping_ws_connections[tool_id].add(websocket)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "toolId": tool_id,
            "message": "Connected to scraping stream",
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_json()
                
                if data.get("action") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except Exception:
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        if tool_id in scraping_ws_connections:
            scraping_ws_connections[tool_id].discard(websocket)
            if not scraping_ws_connections[tool_id]:
                del scraping_ws_connections[tool_id]


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
# Documents API - Document scanning and management
# =============================================================================

DOCUMENTS_DIR = Path("/home/tobi/documents")
ICS_FILE = Path("/home/tobi/Downloads/alleestrassehagen.ics")

# Document categories based on folder structure
DOC_CATEGORIES = {
    "azubi": ["azubi", "ausbildung", "berufsschule", "ihk"],
    "arbeit": ["arbeit", "work", "firma", "gehalt"],
    "aok": ["aok", "krankenkasse", "gesundheit", "arzt"],
    "sparkasse": ["sparkasse", "bank", "konto", "überweisung"],
    "auto": ["auto", "kfz", "versicherung", "tüv", "werkstatt"],
    "familie": ["familie", "family", "eltern", "personal"],
}

def categorize_document(path: str, name: str) -> str:
    """Categorize a document based on path and name."""
    path_lower = path.lower()
    name_lower = name.lower()
    combined = f"{path_lower} {name_lower}"
    
    for category, keywords in DOC_CATEGORIES.items():
        for keyword in keywords:
            if keyword in combined:
                return category
    return "sonstige"


@app.get("/api/documents/scan")
async def scan_documents() -> Dict[str, Any]:
    """Scan documents directory and return all files."""
    documents = []
    
    if not DOCUMENTS_DIR.exists():
        DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
        return {"documents": [], "total": 0}
    
    try:
        for file_path in DOCUMENTS_DIR.rglob("*"):
            if file_path.is_file():
                # Get file info
                stat = file_path.stat()
                rel_path = str(file_path.relative_to(DOCUMENTS_DIR))
                
                # Determine file type
                suffix = file_path.suffix.lower()
                file_type = "document"
                if suffix == ".pdf":
                    file_type = "pdf"
                elif suffix in [".jpg", ".jpeg", ".png", ".gif"]:
                    file_type = "image"
                elif suffix in [".doc", ".docx"]:
                    file_type = "word"
                elif suffix in [".xls", ".xlsx"]:
                    file_type = "excel"
                elif suffix in [".txt", ".md"]:
                    file_type = "text"
                
                documents.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "relativePath": rel_path,
                    "type": file_type,
                    "category": categorize_document(rel_path, file_path.name),
                    "modifiedAt": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "size": stat.st_size,
                })
        
        # Sort by modified date, newest first
        documents.sort(key=lambda x: x["modifiedAt"], reverse=True)
        
        return {"documents": documents, "total": len(documents)}
    
    except Exception as e:
        return {"documents": [], "total": 0, "error": str(e)}


@app.post("/api/documents/organize")
async def organize_documents(data: Dict[str, Any]) -> Dict[str, Any]:
    """AI-assisted document organization."""
    source = data.get("source")
    target_category = data.get("category")
    
    if not source or not target_category:
        raise HTTPException(status_code=400, detail="Source and category required")
    
    source_path = Path(source)
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="Source file not found")
    
    # Create category folder if needed
    target_dir = DOCUMENTS_DIR / target_category
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Move file
    target_path = target_dir / source_path.name
    import shutil
    shutil.move(str(source_path), str(target_path))
    
    return {"success": True, "new_path": str(target_path)}


@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form("unsorted")
) -> Dict[str, Any]:
    """Upload a document to the documents folder."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Create category folder if needed
    target_dir = DOCUMENTS_DIR / category
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename if exists
    target_path = target_dir / file.filename
    counter = 1
    while target_path.exists():
        stem = Path(file.filename).stem
        suffix = Path(file.filename).suffix
        target_path = target_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    
    # Save file
    try:
        content = await file.read()
        target_path.write_bytes(content)
        
        return {
            "success": True,
            "path": str(target_path),
            "name": target_path.name,
            "size": len(content),
            "category": category,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/api/documents/upload-multiple")
async def upload_multiple_documents(
    files: List[UploadFile] = File(...),
    category: str = Form("unsorted")
) -> Dict[str, Any]:
    """Upload multiple documents."""
    results = []
    errors = []
    
    target_dir = DOCUMENTS_DIR / category
    target_dir.mkdir(parents=True, exist_ok=True)
    
    for file in files:
        if not file.filename:
            continue
            
        target_path = target_dir / file.filename
        counter = 1
        while target_path.exists():
            stem = Path(file.filename).stem
            suffix = Path(file.filename).suffix
            target_path = target_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        
        try:
            content = await file.read()
            target_path.write_bytes(content)
            results.append({
                "name": target_path.name,
                "path": str(target_path),
                "size": len(content),
            })
        except Exception as e:
            errors.append({"name": file.filename, "error": str(e)})
    
    return {
        "success": len(results) > 0,
        "uploaded": results,
        "errors": errors,
        "total": len(results),
    }


# =============================================================================
# PDF Form Detection and Filling
# =============================================================================

@app.get("/api/pdf/fields/{path:path}")
async def get_pdf_form_fields(path: str) -> Dict[str, Any]:
    """Get form fields from a PDF."""
    from urllib.parse import unquote
    
    try:
        import pikepdf
    except ImportError:
        return {"error": "pikepdf not installed", "fields": []}
    
    path = unquote(path)
    file_path = Path(path)
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if file_path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Not a PDF file")
    
    try:
        fields = []
        with pikepdf.open(file_path) as pdf:
            if "/AcroForm" in pdf.Root:
                acroform = pdf.Root.AcroForm
                if "/Fields" in acroform:
                    for field in acroform.Fields:
                        field_info = extract_pdf_field(field)
                        if field_info:
                            fields.append(field_info)
        
        return {
            "path": str(file_path),
            "fields": fields,
            "total": len(fields),
            "has_form": len(fields) > 0,
        }
    except Exception as e:
        return {"error": str(e), "fields": []}


def extract_pdf_field(field) -> Optional[Dict[str, Any]]:
    """Extract info from a PDF form field."""
    try:
        field_type = str(field.get("/FT", ""))
        field_name = str(field.get("/T", ""))
        field_value = str(field.get("/V", "")) if "/V" in field else ""
        
        # Map PDF field types
        type_map = {
            "/Tx": "text",
            "/Btn": "checkbox",
            "/Ch": "dropdown",
            "/Sig": "signature",
        }
        
        return {
            "name": field_name,
            "type": type_map.get(field_type, "unknown"),
            "value": field_value,
            "required": bool(field.get("/Ff", 0) & 2),  # Required flag
        }
    except:
        return None


@app.post("/api/pdf/fill")
async def fill_pdf_form(data: Dict[str, Any]) -> Dict[str, Any]:
    """Fill a PDF form with provided values."""
    try:
        import pikepdf
    except ImportError:
        raise HTTPException(status_code=500, detail="pikepdf not installed")
    
    path = data.get("path")
    values = data.get("values", {})  # {field_name: value}
    
    if not path:
        raise HTTPException(status_code=400, detail="Path required")
    
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Create output path
        output_path = file_path.parent / f"{file_path.stem}_filled{file_path.suffix}"
        
        with pikepdf.open(file_path, allow_overwriting_input=True) as pdf:
            if "/AcroForm" not in pdf.Root:
                raise HTTPException(status_code=400, detail="PDF has no form fields")
            
            acroform = pdf.Root.AcroForm
            if "/Fields" in acroform:
                filled_count = 0
                for field in acroform.Fields:
                    field_name = str(field.get("/T", ""))
                    if field_name in values:
                        field["/V"] = pikepdf.String(str(values[field_name]))
                        filled_count += 1
            
            pdf.save(str(output_path))
        
        return {
            "success": True,
            "output_path": str(output_path),
            "filled_fields": filled_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fill failed: {str(e)}")


@app.post("/api/pdf/ai-fill")
async def ai_fill_pdf_form(data: Dict[str, Any]) -> Dict[str, Any]:
    """Use AI to suggest values for PDF form fields based on user profile."""
    path = data.get("path")
    
    if not path:
        raise HTTPException(status_code=400, detail="Path required")
    
    # Get form fields
    fields_response = await get_pdf_form_fields(path)
    if "error" in fields_response:
        return fields_response
    
    fields = fields_response.get("fields", [])
    if not fields:
        return {"error": "No form fields found", "suggestions": {}}
    
    # Get user profile for filling
    memory = load_memory()
    profile = memory.get("profile", {})
    
    # Build prompt for AI
    field_list = "\n".join([f"- {f['name']} ({f['type']})" for f in fields])
    
    prompt = f"""Du bist ein Assistent der beim Ausfüllen von Formularen hilft.

Bekannte User-Daten:
- Name: {profile.get('name', 'Tobi')}
- Adresse: {profile.get('address', 'Alleestraße 58, 58097 Hagen')}

Das Formular hat folgende Felder:
{field_list}

Antworte NUR mit einem JSON-Objekt das die Feldnamen als Keys und die vorgeschlagenen Werte als Values enthält.
Fülle nur Felder aus die du sicher kennst. Beispiel:
{{"Vorname": "Tobi", "PLZ": "58097"}}"""

    try:
        response = await vllm_chat(
            messages=[
                {"role": "system", "content": "Du bist ein Formular-Assistent. Antworte nur mit validem JSON."},
                {"role": "user", "content": prompt},
            ],
            model=MODEL_LARGE,
            max_tokens=500,
            temperature=0.3,
        )
        
        content = response.get("content", "{}")
        
        # Try to parse JSON from response
        import re
        json_match = re.search(r'\{[^{}]*\}', content)
        if json_match:
            suggestions = json.loads(json_match.group())
        else:
            suggestions = {}
        
        return {
            "fields": fields,
            "suggestions": suggestions,
            "path": path,
        }
    except Exception as e:
        return {"error": str(e), "suggestions": {}}


@app.get("/api/documents/preview/{path:path}")
async def preview_document(path: str) -> Dict[str, Any]:
    """Get document preview information."""
    from urllib.parse import unquote
    path = unquote(path)
    
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Get file info
    stat = file_path.stat()
    suffix = file_path.suffix.lower()
    
    preview_data = {
        "name": file_path.name,
        "path": str(file_path),
        "size": stat.st_size,
        "size_formatted": f"{stat.st_size / 1024:.1f} KB" if stat.st_size < 1024*1024 else f"{stat.st_size / (1024*1024):.1f} MB",
        "modifiedAt": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "type": suffix[1:] if suffix else "unknown",
        "previewable": suffix in [".txt", ".md", ".json", ".py", ".js", ".ts"],
    }
    
    # For text files, include content preview
    if suffix in [".txt", ".md"]:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")[:2000]
            preview_data["content"] = content
        except:
            pass
    
    return preview_data


@app.post("/api/documents/open")
async def open_document(data: Dict[str, str]) -> Dict[str, Any]:
    """Open a document with the system default application."""
    import subprocess
    import shutil
    
    path = data.get("path")
    if not path:
        raise HTTPException(status_code=400, detail="Path required")
    
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Try zen-browser first for PDFs/images, then xdg-open
        suffix = file_path.suffix.lower()
        
        # For web-viewable files, prefer Zen browser if available
        if suffix in ['.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.html', '.htm']:
            zen_path = shutil.which("zen-browser") or shutil.which("zen")
            if zen_path:
                subprocess.Popen([zen_path, str(file_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return {"success": True, "message": f"Opened {file_path.name} in Zen"}
        
        # Fallback to xdg-open
        subprocess.Popen(["xdg-open", str(file_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"success": True, "message": f"Opened {file_path.name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to open: {str(e)}")


@app.get("/api/documents/serve/{path:path}")
async def serve_document(path: str):
    """Serve a document file for in-app viewing."""
    from fastapi.responses import FileResponse
    from urllib.parse import unquote
    import mimetypes
    
    # Decode the path
    decoded_path = unquote(path)
    
    # Handle both absolute and relative paths
    if decoded_path.startswith("/"):
        file_path = Path(decoded_path)
    else:
        # Try to find in documents directory
        file_path = DOCUMENTS_DIR / decoded_path
        if not file_path.exists():
            file_path = Path.home() / "Downloads" / decoded_path
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    
    # Security: only serve from allowed directories
    allowed_dirs = [DOCUMENTS_DIR, Path.home() / "Downloads", Path.home() / "documents"]
    file_path_resolved = file_path.resolve()
    if not any(str(file_path_resolved).startswith(str(d.resolve())) for d in allowed_dirs if d.exists()):
        raise HTTPException(status_code=403, detail=f"Access denied: {file_path}")
    
    # Determine content type
    content_type, _ = mimetypes.guess_type(str(file_path))
    if not content_type:
        content_type = "application/octet-stream"
    
    return FileResponse(
        path=str(file_path),
        media_type=content_type,
        filename=file_path.name
    )


@app.get("/api/documents/thumbnail/{path:path}")
async def get_document_thumbnail(path: str) -> Dict[str, Any]:
    """Generate a thumbnail for a document (images only for now)."""
    from urllib.parse import unquote
    import base64
    
    path = unquote(path)
    file_path = Path(path)
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    suffix = file_path.suffix.lower()
    
    # For images, return base64 encoded thumbnail
    if suffix in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
        try:
            content = file_path.read_bytes()
            mime_type = f"image/{suffix[1:]}"
            if suffix == ".jpg":
                mime_type = "image/jpeg"
            
            return {
                "type": "image",
                "data": f"data:{mime_type};base64,{base64.b64encode(content).decode()}",
                "size": len(content),
            }
        except Exception as e:
            return {"type": "error", "error": str(e)}
    
    # For PDFs, we could use pdf2image but keep it simple for now
    elif suffix == ".pdf":
        return {
            "type": "pdf",
            "url": f"/api/documents/serve/{path}",
            "pages": "unknown",
        }
    
    # For text files
    elif suffix in [".txt", ".md", ".json", ".py", ".js", ".ts"]:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")[:5000]
            return {
                "type": "text",
                "content": content,
                "size": len(content),
            }
        except Exception as e:
            return {"type": "error", "error": str(e)}
    
    return {"type": "unsupported", "message": f"Cannot preview {suffix} files"}


# =============================================================================
# Trash Schedule API - ICS calendar parsing
# =============================================================================

def parse_ics_file() -> List[Dict[str, Any]]:
    """Parse ICS file for trash pickup dates."""
    events = []
    
    if not ICS_FILE.exists():
        return events
    
    try:
        content = ICS_FILE.read_text()
        
        # Simple ICS parsing
        current_event = {}
        for line in content.split("\n"):
            line = line.strip()
            if line == "BEGIN:VEVENT":
                current_event = {}
            elif line == "END:VEVENT":
                if current_event:
                    events.append(current_event)
                current_event = {}
            elif ":" in line:
                key, value = line.split(":", 1)
                key = key.split(";")[0]  # Handle parameters
                if key == "DTSTART":
                    current_event["date"] = value
                elif key == "SUMMARY":
                    current_event["type"] = value
                elif key == "DESCRIPTION":
                    current_event["description"] = value
        
        return events
    except Exception as e:
        print(f"Error parsing ICS: {e}")
        return []


@app.get("/api/trash/schedule")
async def get_trash_schedule() -> Dict[str, Any]:
    """Get upcoming trash pickup schedule."""
    events = parse_ics_file()
    today = datetime.now().strftime("%Y%m%d")
    
    # Filter future events
    upcoming = []
    for event in events:
        event_date = event.get("date", "")
        if event_date >= today:
            # Parse date for display
            try:
                dt = datetime.strptime(event_date, "%Y%m%d")
                event["formatted_date"] = dt.strftime("%d.%m.%Y")
                event["weekday"] = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][dt.weekday()]
                upcoming.append(event)
            except:
                pass
    
    # Sort by date
    upcoming.sort(key=lambda x: x.get("date", ""))
    
    # Get tomorrow's pickups
    tomorrow = (datetime.now() + __import__("datetime").timedelta(days=1)).strftime("%Y%m%d")
    tomorrow_pickups = [e for e in upcoming if e.get("date") == tomorrow]
    
    return {
        "upcoming": upcoming[:10],  # Next 10 pickups
        "tomorrow": tomorrow_pickups,
        "total": len(upcoming),
    }


# =============================================================================
# Dashboard Summary API
# =============================================================================

@app.get("/api/dashboard/summary")
async def get_dashboard_summary() -> Dict[str, Any]:
    """Get complete dashboard summary for holographic desk."""
    
    # Get documents
    doc_result = await scan_documents()
    documents = doc_result.get("documents", [])
    
    # Count by category
    by_category = {}
    for doc in documents:
        cat = doc.get("category", "sonstige")
        by_category[cat] = by_category.get(cat, 0) + 1
    
    # Get trash schedule
    trash_result = await get_trash_schedule()
    
    # Get reminders (from memory)
    reminders = await get_reminders()
    
    return {
        "documents": {
            "total": len(documents),
            "by_category": by_category,
        },
        "reminders": reminders,
        "trash": {
            "tomorrow": trash_result.get("tomorrow", []),
            "upcoming": trash_result.get("upcoming", [])[:5],
        },
        "profile": {
            "name": "Tobi",
            "address": "Alleestraße 58, 58097 Hagen",
        },
    }


# =============================================================================
# Memory System - Persistent AI memory like ChatGPT
# =============================================================================

MEMORY_FILE = PROJECT_ROOT / "data" / "memory.json"

def load_memory() -> Dict[str, Any]:
    """Load persistent memory."""
    if MEMORY_FILE.exists():
        try:
            return json.loads(MEMORY_FILE.read_text())
        except:
            pass
    return {
        "profile": {
            "name": "Tobi",
            "address": "Alleestraße 58, 58097 Hagen",
            "city": "Hagen",
        },
        "facts": [],
        "preferences": {},
        "reminders": [],
        "gmail_accounts": [],
    }


def save_memory(memory: Dict[str, Any]) -> None:
    """Save memory to disk."""
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(json.dumps(memory, indent=2, ensure_ascii=False))


@app.get("/api/memory")
async def get_memory() -> Dict[str, Any]:
    """Get AI memory."""
    return load_memory()


@app.post("/api/memory/fact")
async def add_memory_fact(data: Dict[str, str]) -> Dict[str, Any]:
    """Add a fact to memory."""
    memory = load_memory()
    fact = {
        "content": data.get("fact", ""),
        "added": datetime.now().isoformat(),
        "source": data.get("source", "user"),
    }
    memory["facts"].append(fact)
    save_memory(memory)
    return {"success": True, "fact": fact}


@app.delete("/api/memory/fact/{index}")
async def delete_memory_fact(index: int) -> Dict[str, Any]:
    """Delete a fact from memory."""
    memory = load_memory()
    if 0 <= index < len(memory["facts"]):
        removed = memory["facts"].pop(index)
        save_memory(memory)
        return {"success": True, "removed": removed}
    raise HTTPException(status_code=404, detail="Fact not found")


@app.post("/api/memory/profile")
async def update_profile(data: Dict[str, str]) -> Dict[str, Any]:
    """Update user profile in memory."""
    memory = load_memory()
    memory["profile"].update(data)
    save_memory(memory)
    return {"success": True, "profile": memory["profile"]}


# =============================================================================
# Reminders API
# =============================================================================

@app.get("/api/reminders")
async def get_reminders() -> Dict[str, Any]:
    """Get all reminders."""
    memory = load_memory()
    reminders = memory.get("reminders", [])
    
    today = datetime.now().date()
    
    # Categorize reminders
    today_items = []
    overdue_items = []
    upcoming_items = []
    
    for r in reminders:
        try:
            due_date = datetime.fromisoformat(r.get("due", "")).date()
            if due_date < today and not r.get("completed"):
                overdue_items.append(r)
            elif due_date == today:
                today_items.append(r)
            else:
                upcoming_items.append(r)
        except:
            upcoming_items.append(r)
    
    return {
        "today": len(today_items),
        "overdue": len(overdue_items),
        "items": today_items + overdue_items + upcoming_items[:5],
    }


@app.post("/api/reminders")
async def add_reminder(data: Dict[str, Any]) -> Dict[str, Any]:
    """Add a reminder."""
    memory = load_memory()
    
    reminder = {
        "id": f"rem_{int(time.time()*1000)}",
        "title": data.get("title", ""),
        "due": data.get("due", ""),
        "notes": data.get("notes", ""),
        "completed": False,
        "source": data.get("source", "user"),
        "created": datetime.now().isoformat(),
    }
    
    memory["reminders"].append(reminder)
    save_memory(memory)
    
    return {"success": True, "reminder": reminder}


@app.put("/api/reminders/{reminder_id}")
async def update_reminder(reminder_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a reminder."""
    memory = load_memory()
    
    for r in memory["reminders"]:
        if r.get("id") == reminder_id:
            r.update(data)
            save_memory(memory)
            return {"success": True, "reminder": r}
    
    raise HTTPException(status_code=404, detail="Reminder not found")


@app.delete("/api/reminders/{reminder_id}")
async def delete_reminder(reminder_id: str) -> Dict[str, Any]:
    """Delete a reminder."""
    memory = load_memory()
    
    memory["reminders"] = [r for r in memory["reminders"] if r.get("id") != reminder_id]
    save_memory(memory)
    
    return {"success": True}


# =============================================================================
# Gmail Integration - Simple App Password based
# =============================================================================

@app.get("/api/gmail/accounts")
async def get_gmail_accounts() -> Dict[str, Any]:
    """Get configured Gmail accounts."""
    memory = load_memory()
    accounts = memory.get("gmail_accounts", [])
    
    # Don't expose passwords
    safe_accounts = []
    for i, acc in enumerate(accounts):
        safe_accounts.append({
            "id": acc.get("id", str(i)),
            "email": acc.get("email"),
            "name": acc.get("name", acc.get("email", "").split("@")[0]),
            "isDefault": acc.get("is_default", False),
        })
    
    # Also return the default account email
    default_account = next((a["email"] for a in safe_accounts if a.get("isDefault")), None)
    
    return {"accounts": safe_accounts, "default_account": default_account}


@app.post("/api/gmail/accounts")
async def add_gmail_account(data: Dict[str, str]) -> Dict[str, Any]:
    """Add a Gmail account with app password."""
    email = data.get("email")
    app_password = data.get("app_password")
    name = data.get("name", email.split("@")[0] if email else "")
    
    if not email or not app_password:
        raise HTTPException(status_code=400, detail="Email and app_password required")
    
    memory = load_memory()
    
    # Check if already exists
    for acc in memory.get("gmail_accounts", []):
        if acc.get("email") == email:
            raise HTTPException(status_code=400, detail="Account already exists")
    
    # Set as default if first account
    is_default = len(memory.get("gmail_accounts", [])) == 0
    
    account = {
        "id": f"gmail_{int(time.time()*1000)}",
        "email": email,
        "app_password": app_password,  # In production, encrypt this!
        "name": name,
        "is_default": is_default,
        "added": datetime.now().isoformat(),
    }
    
    if "gmail_accounts" not in memory:
        memory["gmail_accounts"] = []
    memory["gmail_accounts"].append(account)
    save_memory(memory)
    
    return {"success": True, "email": email, "id": account["id"]}


@app.delete("/api/gmail/accounts/{email}")
async def delete_gmail_account(email: str) -> Dict[str, Any]:
    """Remove a Gmail account by ID or email."""
    memory = load_memory()
    
    # Try to match by ID first, then by email
    memory["gmail_accounts"] = [
        a for a in memory.get("gmail_accounts", []) 
        if a.get("id") != email and a.get("email") != email
    ]
    save_memory(memory)
    
    return {"success": True}


@app.put("/api/gmail/accounts/{account_id}/default")
async def set_default_gmail(account_id: str) -> Dict[str, Any]:
    """Set a Gmail account as default by ID or email."""
    memory = load_memory()
    
    for acc in memory.get("gmail_accounts", []):
        acc["is_default"] = (acc.get("id") == account_id or acc.get("email") == account_id)
    
    save_memory(memory)
    return {"success": True}


@app.post("/api/gmail/send")
async def send_gmail(data: Dict[str, Any]) -> Dict[str, Any]:
    """Send an email via Gmail."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    memory = load_memory()
    
    # Get account to use
    account_email = data.get("from")
    account = None
    
    if account_email:
        for acc in memory.get("gmail_accounts", []):
            if acc.get("email") == account_email:
                account = acc
                break
    else:
        # Use default
        for acc in memory.get("gmail_accounts", []):
            if acc.get("is_default"):
                account = acc
                break
    
    if not account:
        raise HTTPException(status_code=400, detail="No Gmail account configured")
    
    try:
        msg = MIMEMultipart()
        msg["From"] = account["email"]
        msg["To"] = data.get("to", "")
        msg["Subject"] = data.get("subject", "")
        msg.attach(MIMEText(data.get("body", ""), "plain"))
        
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(account["email"], account["app_password"])
            server.send_message(msg)
        
        return {"success": True, "message": "Email sent"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


@app.post("/api/gmail/compose")
async def compose_email(data: Dict[str, Any]) -> Dict[str, Any]:
    """AI-assisted email composition."""
    prompt = data.get("prompt", "")
    context = data.get("context", "")
    style = data.get("style", "formal")  # formal, casual, brief
    language = data.get("language", "de")  # de, en
    
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt required")
    
    # Load memory for context
    memory = load_memory()
    profile = memory.get("profile", {})
    user_name = profile.get("name", "")
    user_address = profile.get("address", "")
    
    # Build system prompt for email composition
    today = datetime.now()
    date_str = today.strftime("%d.%m.%Y")
    
    style_instructions = {
        "formal": "Schreibe eine formelle, höfliche Email im Sie-Form.",
        "casual": "Schreibe eine lockere, freundliche Email.",
        "brief": "Schreibe eine sehr kurze, präzise Email."
    }
    
    system_prompt = f"""Du bist ein Email-Assistent. Heute ist {date_str}.
{style_instructions.get(style, style_instructions["formal"])}

User-Info (wenn relevant):
- Name: {user_name}
- Adresse: {user_address}

Generiere NUR den Email-Text, keine Erklärungen.
Formatiere mit Betreff: am Anfang, dann leerzeile, dann Email-Body.
"""
    
    if context:
        system_prompt += f"\n\nKontext (vorheriger Briefverkehr etc.):\n{context}"
    
    try:
        response = await vllm_chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            model=None,
            max_tokens=1000,
            temperature=0.7,
        )
        
        email_text = response.get("content", "")
        
        # Try to extract subject and body
        subject = ""
        body = email_text
        
        if "Betreff:" in email_text:
            lines = email_text.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("Betreff:"):
                    subject = line.replace("Betreff:", "").strip()
                    body = "\n".join(lines[i+1:]).strip()
                    break
        
        return {
            "subject": subject,
            "body": body,
            "full_text": email_text,
            "model": response.get("model", ""),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Composition failed: {str(e)}")


# =============================================================================
# Web Search API - Uses SearXNG
# =============================================================================

@app.post("/api/search/web")
async def web_search(data: Dict[str, str]) -> Dict[str, Any]:
    """Search the web using SearXNG."""
    query = data.get("query", "")
    
    if not query:
        raise HTTPException(status_code=400, detail="Query required")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{SEARXNG_URL}/search",
                params={"q": query, "format": "json"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    results = await resp.json()
                    
                    # Simplify results
                    simplified = []
                    for r in results.get("results", [])[:5]:
                        simplified.append({
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "content": r.get("content", "")[:200],
                        })
                    
                    return {"results": simplified, "query": query}
                else:
                    return {"results": [], "error": "Search failed"}
    except Exception as e:
        return {"results": [], "error": str(e)}


@app.post("/api/scrape")
async def scrape_webpage(data: Dict[str, str]) -> Dict[str, Any]:
    """Scrape a webpage for content (opening hours, contact info, etc.)."""
    url = data.get("url", "")
    
    if not url:
        raise HTTPException(status_code=400, detail="URL required")
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; RyxBot/1.0)"}
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    return {"success": False, "error": f"HTTP {resp.status}"}
                
                html = await resp.text()
                
                # Simple text extraction (no heavy deps)
                import re
                
                # Remove scripts and styles
                html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
                html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
                
                # Extract text
                text = re.sub(r'<[^>]+>', ' ', html)
                text = re.sub(r'\s+', ' ', text).strip()
                
                # Extract common patterns
                # Opening hours patterns
                hours_pattern = r'(?:Öffnungszeiten|Opening Hours|Hours).*?(?:\d{1,2}[:.]\d{2}|\d{1,2}\s*(?:Uhr|AM|PM))'
                hours_matches = re.findall(hours_pattern, text, re.IGNORECASE)
                
                # Phone patterns
                phone_pattern = r'(?:\+49|0)\s*\d{2,5}[\s/-]?\d{3,}[\s/-]?\d{0,}'
                phone_matches = re.findall(phone_pattern, text)
                
                # Email patterns
                email_pattern = r'[\w.+-]+@[\w.-]+\.\w{2,}'
                email_matches = re.findall(email_pattern, text)
                
                return {
                    "success": True,
                    "url": url,
                    "text": text[:3000],  # First 3000 chars
                    "extracted": {
                        "hours": hours_matches[:3] if hours_matches else [],
                        "phones": list(set(phone_matches[:5])),
                        "emails": list(set(email_matches[:5])),
                    }
                }
                
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# WebUntis Integration - School Schedule
# =============================================================================

@app.get("/api/webuntis/config")
async def get_webuntis_config() -> Dict[str, Any]:
    """Get WebUntis configuration (without password)."""
    memory = load_memory()
    config = memory.get("webuntis", {})
    return {
        "configured": bool(config.get("server") and config.get("username")),
        "server": config.get("server", ""),
        "school": config.get("school", ""),
        "username": config.get("username", ""),
    }


@app.post("/api/webuntis/config")
async def save_webuntis_config(data: Dict[str, str]) -> Dict[str, Any]:
    """Save WebUntis configuration."""
    server = data.get("server", "")
    school = data.get("school", "")
    username = data.get("username", "")
    password = data.get("password", "")
    
    if not all([server, school, username, password]):
        raise HTTPException(status_code=400, detail="All fields required")
    
    memory = load_memory()
    memory["webuntis"] = {
        "server": server,
        "school": school,
        "username": username,
        "password": password,  # In production, encrypt this!
    }
    save_memory(memory)
    
    return {"success": True}


@app.get("/api/webuntis/timetable")
async def get_webuntis_timetable(days: int = 7) -> Dict[str, Any]:
    """Get timetable for the next N days."""
    try:
        import webuntis
        
        memory = load_memory()
        config = memory.get("webuntis", {})
        
        if not config.get("server"):
            return {"error": "WebUntis not configured", "lessons": []}
        
        session = webuntis.Session(
            server=config["server"],
            school=config["school"],
            username=config["username"],
            password=config["password"],
            useragent="RyxHub/1.0"
        )
        
        session.login()
        
        today = datetime.now().date()
        end_date = today + timedelta(days=days)
        
        # Get timetable
        timetable = session.my_timetable(start=today, end=end_date)
        
        lessons = []
        for lesson in timetable:
            lessons.append({
                "id": lesson.id,
                "date": lesson.start.strftime("%Y-%m-%d"),
                "weekday": lesson.start.strftime("%A"),
                "start": lesson.start.strftime("%H:%M"),
                "end": lesson.end.strftime("%H:%M"),
                "subject": lesson.subjects[0].name if lesson.subjects else "?",
                "subject_long": lesson.subjects[0].long_name if lesson.subjects else "",
                "room": lesson.rooms[0].name if lesson.rooms else "",
                "teacher": lesson.teachers[0].name if lesson.teachers else "",
                "cancelled": lesson.code == "cancelled",
            })
        
        session.logout()
        
        # Group by date
        by_date = {}
        for lesson in lessons:
            date = lesson["date"]
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(lesson)
        
        return {"lessons": lessons, "by_date": by_date, "total": len(lessons)}
        
    except Exception as e:
        return {"error": str(e), "lessons": []}


@app.get("/api/webuntis/today")
async def get_webuntis_today() -> Dict[str, Any]:
    """Get today's timetable."""
    result = await get_webuntis_timetable(days=1)
    today = datetime.now().strftime("%Y-%m-%d")
    
    today_lessons = result.get("by_date", {}).get(today, [])
    
    return {
        "date": today,
        "weekday": datetime.now().strftime("%A"),
        "lessons": today_lessons,
        "total": len(today_lessons),
    }


# =============================================================================
# NRW Holidays
# =============================================================================

def get_nrw_holidays(year: int = None) -> List[Dict[str, Any]]:
    """Get NRW public holidays for a year."""
    if year is None:
        year = datetime.now().year
    
    # Fixed holidays
    holidays = [
        {"name": "Neujahr", "date": f"{year}-01-01"},
        {"name": "Tag der Arbeit", "date": f"{year}-05-01"},
        {"name": "Tag der Deutschen Einheit", "date": f"{year}-10-03"},
        {"name": "Allerheiligen", "date": f"{year}-11-01"},
        {"name": "1. Weihnachtstag", "date": f"{year}-12-25"},
        {"name": "2. Weihnachtstag", "date": f"{year}-12-26"},
    ]
    
    # Easter-based holidays (simplified calculation)
    # Using Anonymous Gregorian algorithm
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    
    easter = datetime(year, month, day)
    
    # Easter-based holidays
    holidays.extend([
        {"name": "Karfreitag", "date": (easter - timedelta(days=2)).strftime("%Y-%m-%d")},
        {"name": "Ostersonntag", "date": easter.strftime("%Y-%m-%d")},
        {"name": "Ostermontag", "date": (easter + timedelta(days=1)).strftime("%Y-%m-%d")},
        {"name": "Christi Himmelfahrt", "date": (easter + timedelta(days=39)).strftime("%Y-%m-%d")},
        {"name": "Pfingstsonntag", "date": (easter + timedelta(days=49)).strftime("%Y-%m-%d")},
        {"name": "Pfingstmontag", "date": (easter + timedelta(days=50)).strftime("%Y-%m-%d")},
        {"name": "Fronleichnam", "date": (easter + timedelta(days=60)).strftime("%Y-%m-%d")},
    ])
    
    # Sort by date
    holidays.sort(key=lambda x: x["date"])
    
    # Add weekday
    for h in holidays:
        dt = datetime.strptime(h["date"], "%Y-%m-%d")
        h["weekday"] = dt.strftime("%A")
        h["formatted"] = dt.strftime("%d.%m.%Y")
    
    return holidays


@app.get("/api/holidays/nrw")
async def get_holidays_nrw(year: int = None) -> Dict[str, Any]:
    """Get NRW public holidays."""
    if year is None:
        year = datetime.now().year
    
    holidays = get_nrw_holidays(year)
    
    # Also get upcoming holidays
    today = datetime.now().date()
    upcoming = []
    for h in holidays:
        h_date = datetime.strptime(h["date"], "%Y-%m-%d").date()
        if h_date >= today:
            days_until = (h_date - today).days
            h["days_until"] = days_until
            upcoming.append(h)
    
    return {
        "year": year,
        "holidays": holidays,
        "upcoming": upcoming[:5],
        "next": upcoming[0] if upcoming else None,
    }


# =============================================================================
# Smart Intent Detection & Model Selection
# =============================================================================

# Model paths
MODEL_SMALL = "/models/small/general/qwen2.5-3b"
MODEL_LARGE = "/models/powerful/general/qwen2.5-14b-gptq"

def detect_intent_and_model(message: str, has_document: bool = False) -> Dict[str, Any]:
    """
    Detect user intent and select appropriate model.
    Returns enhanced prompt context and model choice.
    """
    message_lower = message.lower().strip()
    
    # Intent patterns
    SIMPLE_PATTERNS = [
        # Greetings
        r'^(hi|hallo|hey|moin|guten\s*(morgen|tag|abend)|servus|na)\b',
        # Simple questions
        r'^(wie geht|was geht|alles klar|wie läuft)',
        # Time/date
        r'^(wie spät|welcher tag|welches datum|wann ist)',
        # Yes/no
        r'^(ja|nein|ok|okay|danke|bitte|gut|cool|nice)\b',
        # Short confirmations
        r'^.{1,15}$',  # Very short messages
    ]
    
    COMPLEX_PATTERNS = [
        # Document analysis
        r'(dokument|pdf|datei|inhalt|zusammenfass|analys|erkl[äa]r|was steht)',
        # Email composition
        r'(email|mail|schreib|brief|antwort|formulier)',
        # Search/research
        r'(such|find|recherch|info über|was ist|wer ist|wie funktioniert)',
        # Planning/scheduling
        r'(termin|plan|erinnerung|deadline|bis wann)',
        # Arabic/complex text
        r'[\u0600-\u06FF]',  # Arabic characters
        # Long detailed questions
        r'.{100,}',  # Long messages
    ]
    
    import re
    
    # Check for simple patterns
    is_simple = any(re.search(p, message_lower) for p in SIMPLE_PATTERNS)
    is_complex = any(re.search(p, message_lower) for p in COMPLEX_PATTERNS)
    
    # Document context always needs big model
    if has_document:
        is_complex = True
    
    # Determine model
    use_large_model = is_complex and not is_simple
    
    # Enhance the prompt based on intent
    enhanced_context = []
    
    # Auto-detect what user wants
    if re.search(r'(zusammenfass|worum geht|was steht|inhalt)', message_lower):
        enhanced_context.append("User wants a summary or explanation of content.")
    
    if re.search(r'(schreib|formulier|email|brief)', message_lower):
        enhanced_context.append("User wants help writing/composing something.")
    
    if re.search(r'(find|such|wo ist|welche)', message_lower):
        enhanced_context.append("User is searching for something specific.")
    
    if has_document and len(message) < 30:
        # Short message with document = probably asking about the document
        enhanced_context.append("User is likely asking about the selected document.")
    
    return {
        "use_large_model": use_large_model,
        "model": MODEL_LARGE if use_large_model else MODEL_SMALL,
        "intent_hints": enhanced_context,
        "is_simple": is_simple,
        "is_complex": is_complex,
    }


# =============================================================================
# AI Chat with Memory Context
# =============================================================================

@app.post("/api/chat/smart")
async def smart_chat(data: Dict[str, Any]) -> Dict[str, Any]:
    """Chat with AI including memory context, web search, and more."""
    message = data.get("message", "")
    include_memory = data.get("include_memory", True)
    use_search = data.get("use_search", False)
    use_scrape = data.get("use_scrape", False)
    document_name = data.get("document")
    
    if not message:
        raise HTTPException(status_code=400, detail="Message required")
    
    # Smart intent detection and model selection
    intent_info = detect_intent_and_model(message, has_document=bool(document_name))
    selected_model = intent_info["model"]
    
    # Build context from memory
    context_parts = []
    
    # Add intent hints
    if intent_info["intent_hints"]:
        context_parts.extend(intent_info["intent_hints"])
    
    if include_memory:
        memory = load_memory()
        
        # Add profile
        profile = memory.get("profile", {})
        if profile:
            context_parts.append(f"User info: Name={profile.get('name')}, Address={profile.get('address')}")
        
        # Add recent facts
        facts = memory.get("facts", [])[-10:]  # Last 10 facts
        if facts:
            context_parts.append("Known facts: " + "; ".join([f.get("content", "") for f in facts]))
        
        # Add upcoming reminders
        reminders = await get_reminders()
        if reminders.get("items"):
            reminder_texts = [r.get("title", "") for r in reminders["items"][:3]]
            context_parts.append("Upcoming reminders: " + ", ".join(reminder_texts))
        
        # Add tomorrow's trash
        trash = await get_trash_schedule()
        if trash.get("tomorrow"):
            trash_types = [t.get("type", "") for t in trash["tomorrow"]]
            context_parts.append(f"Tomorrow's trash: {', '.join(trash_types)}")
    
    # Add document context if provided
    if document_name:
        context_parts.append(f"User is looking at document: {document_name}")
    
    # Web search if enabled
    search_results = []
    if use_search:
        try:
            search_response = await searxng_search({"query": message})
            if search_response.get("results"):
                search_results = search_response["results"][:3]
                search_context = "Web search results:\n"
                for r in search_results:
                    search_context += f"- {r.get('title', '')}: {r.get('content', '')[:150]}\n"
                context_parts.append(search_context)
        except Exception as e:
            print(f"Search failed: {e}")
    
    # Build system prompt with current date
    today = datetime.now()
    date_str = today.strftime("%A, %d. %B %Y")
    time_str = today.strftime("%H:%M")
    
    system_prompt = f"""Du bist Ryx, Tobi's persönlicher AI-Assistent. Heute ist {date_str}, aktuelle Uhrzeit: {time_str}.

WICHTIG:
- Wenn der User ein Dokument ausgewählt hat, beziehe dich darauf und hilf konkret damit
- Antworte auf Deutsch, kurz und präzise
- Bei Fragen zu Dokumenten: erkläre was du siehst/verstehst oder frag nach dem spezifischen Problem
- Du kannst helfen mit: Dokumente verstehen, Emails schreiben, Termine verwalten, Formulare ausfüllen
- Sei proaktiv: schlage Aktionen vor die dem User helfen könnten

User-Profil:
- Name: Tobi
- Wohnort: Hagen
- Situation: Azubi, braucht Hilfe mit Alltagsbürokratie"""
    
    if context_parts:
        system_prompt += "\n\nAktuelle Kontext-Informationen:\n" + "\n".join(context_parts)
    
    # Call vLLM with selected model
    try:
        response = await vllm_chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            model=selected_model,
            max_tokens=1000 if intent_info["use_large_model"] else 300,
            temperature=0.7,
        )
        
        return {
            "response": response.get("content", ""),
            "model": response.get("model", ""),
            "used_large_model": intent_info["use_large_model"],
        }
    
    except Exception as e:
        return {"response": f"Fehler: {str(e)}", "error": True}


@app.get("/api/chat/smart/stream")
async def smart_chat_stream(
    message: str,
    include_memory: bool = True,
    use_search: bool = False,
    document: str = None
):
    """Stream smart chat response with memory context."""
    if not message:
        raise HTTPException(status_code=400, detail="Message required")
    
    # Smart intent detection and model selection
    intent_info = detect_intent_and_model(message, has_document=bool(document))
    selected_model = intent_info["model"]
    
    # Build context from memory
    context_parts = []
    
    # Add intent hints
    if intent_info["intent_hints"]:
        context_parts.extend(intent_info["intent_hints"])
    
    if include_memory:
        memory = load_memory()
        profile = memory.get("profile", {})
        if profile:
            context_parts.append(f"User info: Name={profile.get('name')}, Address={profile.get('address')}")
        
        facts = memory.get("facts", [])[-10:]
        if facts:
            context_parts.append("Known facts: " + "; ".join([f.get("content", "") for f in facts]))
        
        reminders_data = await get_reminders()
        if reminders_data.get("items"):
            reminder_texts = [r.get("title", "") for r in reminders_data["items"][:3]]
            context_parts.append("Upcoming reminders: " + ", ".join(reminder_texts))
        
        trash = await get_trash_schedule()
        if trash.get("tomorrow"):
            trash_types = [t.get("type", "") for t in trash["tomorrow"]]
            context_parts.append(f"Tomorrow's trash: {', '.join(trash_types)}")
    
    if document:
        context_parts.append(f"User is looking at document: {document}")
    
    if use_search:
        try:
            search_response = await searxng_search({"query": message})
            if search_response.get("results"):
                search_results = search_response["results"][:3]
                search_context = "Web search results:\n"
                for r in search_results:
                    search_context += f"- {r.get('title', '')}: {r.get('content', '')[:150]}\n"
                context_parts.append(search_context)
        except:
            pass
    
    # Build system prompt
    today = datetime.now()
    date_str = today.strftime("%A, %d. %B %Y")
    time_str = today.strftime("%H:%M")
    
    system_prompt = f"""Du bist Ryx, Tobi's persönlicher AI-Assistent. Heute ist {date_str}, aktuelle Uhrzeit: {time_str}.

WICHTIG:
- Wenn der User ein Dokument ausgewählt hat, beziehe dich darauf und hilf konkret damit
- Antworte auf Deutsch, kurz und präzise
- Bei Fragen zu Dokumenten: erkläre was du siehst/verstehst oder frag nach dem spezifischen Problem
- Du kannst helfen mit: Dokumente verstehen, Emails schreiben, Termine verwalten, Formulare ausfüllen
- Sei proaktiv: schlage Aktionen vor die dem User helfen könnten

User-Profil:
- Name: Tobi
- Wohnort: Hagen
- Situation: Azubi, braucht Hilfe mit Alltagsbürokratie"""
    
    if context_parts:
        system_prompt += "\n\nAktuelle Kontext-Informationen:\n" + "\n".join(context_parts)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message}
    ]
    
    return StreamingResponse(
        vllm_chat_stream(messages),
        media_type="text/event-stream"
    )


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)
