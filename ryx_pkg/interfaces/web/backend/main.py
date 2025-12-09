"""
Ryx AI - FastAPI Backend with Ollama
REST API for RyxHub web interface using Ollama inference.
"""

import os
import sys
import time
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import aiohttp

# =============================================================================
# Configuration
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT))

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8888")
API_PORT = int(os.environ.get("RYX_API_PORT", "8420"))

# Default model for RyxHub (fast, small model)
DEFAULT_MODEL = "qwen2.5:1.5b"

# =============================================================================
# Pydantic Models
# =============================================================================

class HealthResponse(BaseModel):
    status: str
    ollama_status: str
    searxng_status: str
    models_available: int

class ModelInfo(BaseModel):
    name: str
    size: int
    modified: str

# =============================================================================
# Ollama Client
# =============================================================================

async def ollama_health_check() -> bool:
    """Check if Ollama is running."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(f"{OLLAMA_BASE_URL}/api/tags") as resp:
                return resp.status == 200
    except:
        return False

async def ollama_list_models() -> List[Dict[str, Any]]:
    """List all available Ollama models."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(f"{OLLAMA_BASE_URL}/api/tags") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("models", [])
                return []
    except Exception as e:
        print(f"Failed to list models: {e}")
        return []

async def ollama_load_model(model_name: str) -> Dict[str, Any]:
    """Preload a model into memory and keep it loaded."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            async with session.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": model_name, 
                    "prompt": "", 
                    "stream": False,
                    "keep_alive": "24h"  # Keep loaded 24 hours
                }
            ) as resp:
                if resp.status == 200:
                    return {"success": True, "model": model_name}
                return {"success": False, "error": f"HTTP {resp.status}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def ollama_unload_model(model_name: str) -> Dict[str, Any]:
    """Unload a model from memory."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={"model": model_name, "prompt": "", "keep_alive": 0}
            ) as resp:
                if resp.status == 200:
                    return {"success": True, "model": model_name}
                return {"success": False, "error": f"HTTP {resp.status}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def ollama_chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    stream: bool = False
) -> Dict[str, Any]:
    """Send chat request to Ollama."""
    if not model:
        model = DEFAULT_MODEL
    
    start_time = time.time()
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
            async with session.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": stream,
                    "options": {"temperature": temperature},
                    "keep_alive": "24h"  # Keep model loaded 24 hours
                }
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    return {"error": f"Ollama error: {error_text}"}
                
                data = await resp.json()
                latency_ms = (time.time() - start_time) * 1000
                
                return {
                    "content": data.get("message", {}).get("content", ""),
                    "model": model,
                    "latency_ms": latency_ms
                }
    except Exception as e:
        return {"error": str(e)}

async def ollama_chat_stream(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7
):
    """Stream chat response from Ollama."""
    if not model:
        model = DEFAULT_MODEL
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
            async with session.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "options": {"temperature": temperature}
                }
            ) as resp:
                if resp.status != 200:
                    yield f"data: {json.dumps({'error': 'Ollama error'})}\n\n"
                    return
                
                async for line in resp.content:
                    line_text = line.decode('utf-8').strip()
                    if line_text:
                        try:
                            chunk = json.loads(line_text)
                            if chunk.get("done"):
                                yield "data: [DONE]\n\n"
                                break
                            content = chunk.get("message", {}).get("content", "")
                            if content:
                                yield f"data: {json.dumps({'content': content})}\n\n"
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

# =============================================================================
# SearXNG Client
# =============================================================================

async def searxng_search(query: str) -> Dict[str, Any]:
    """Search using SearXNG."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            async with session.get(
                f"{SEARXNG_URL}/search",
                params={"q": query, "format": "json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "results": data.get("results", [])[:5],
                        "query": query
                    }
                return {"results": [], "error": f"HTTP {resp.status}"}
    except Exception as e:
        return {"results": [], "error": str(e)}

async def searxng_health_check() -> bool:
    """Check if SearXNG is running."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(f"{SEARXNG_URL}") as resp:
                return resp.status == 200
    except:
        return False

# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(title="Ryx AI API", version="1.0.0")

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

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    ollama_ok = await ollama_health_check()
    searxng_ok = await searxng_health_check()
    models = await ollama_list_models()
    
    return {
        "status": "healthy" if ollama_ok else "degraded",
        "ollama_status": "online" if ollama_ok else "offline",
        "searxng_status": "online" if searxng_ok else "offline",
        "models_available": len(models)
    }

@app.get("/api/status")
async def get_status():
    """Get system status."""
    models = await ollama_list_models()
    return {
        "models_loaded": len(models),
        "ollama_url": OLLAMA_BASE_URL,
        "searxng_url": SEARXNG_URL
    }

# =============================================================================
# Model Management Endpoints
# =============================================================================

@app.get("/api/models")
async def list_models():
    """List all available models with loaded status."""
    all_models = await ollama_list_models()
    
    # Get currently loaded models
    loaded = set()
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
            async with session.get(f"{OLLAMA_BASE_URL}/api/ps") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    loaded = {m.get("name") for m in data.get("models", [])}
    except:
        pass
    
    return {
        "models": [
            {
                "id": m.get("name"),
                "name": m.get("name"),
                "size": m.get("size", 0),
                "modified": m.get("modified_at", ""),
                "status": "loaded" if m.get("name") in loaded else "available"
            }
            for m in all_models
        ]
    }

@app.post("/api/models/{model_name}/load")
async def load_model(model_name: str):
    """Load a model into memory."""
    result = await ollama_load_model(model_name)
    if result.get("success"):
        return {"message": f"Model {model_name} loaded successfully"}
    raise HTTPException(status_code=500, detail=result.get("error", "Failed to load model"))

@app.post("/api/models/{model_name}/unload")
async def unload_model(model_name: str):
    """Unload a model from memory."""
    result = await ollama_unload_model(model_name)
    if result.get("success"):
        return {"message": f"Model {model_name} unloaded successfully"}
    raise HTTPException(status_code=500, detail=result.get("error", "Failed to unload model"))

@app.post("/api/models/save-last")
async def save_last_model(data: Dict[str, Any]):
    """Save the last used model for next startup."""
    model_name = data.get("model")
    if not model_name:
        raise HTTPException(status_code=400, detail="Model name required")
    
    last_model_file = Path("/home/tobi/ryx-ai/data/last_model")
    last_model_file.parent.mkdir(parents=True, exist_ok=True)
    last_model_file.write_text(model_name)
    return {"message": f"Saved {model_name} as default model"}

@app.get("/api/models/last")
async def get_last_model():
    """Get the last used model."""
    last_model_file = Path("/home/tobi/ryx-ai/data/last_model")
    if last_model_file.exists():
        return {"model": last_model_file.read_text().strip()}
    return {"model": "qwen2.5:1.5b"}

# =============================================================================
# Chat Endpoints
# =============================================================================

@app.post("/api/chat")
async def chat(data: Dict[str, Any]):
    """Simple chat endpoint with image support."""
    message = data.get("message", "")
    model = data.get("model")
    stream = data.get("stream", False)
    images = data.get("images", [])  # Base64 encoded images
    
    if not message:
        raise HTTPException(status_code=400, detail="Message required")
    
    messages = [{"role": "user", "content": message}]
    
    # Add images to the user message if provided
    if images:
        messages[0]["images"] = images
    
    if stream:
        return StreamingResponse(
            ollama_chat_stream(messages, model),
            media_type="text/event-stream"
        )
    
    response = await ollama_chat(messages, model)
    
    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])
    
    return {
        "response": response.get("content", ""),
        "model": response.get("model", ""),
        "latency_ms": response.get("latency_ms", 0)
    }


async def extract_memories_from_message(message: str, model: str) -> list:
    """Extract factual memories about the user from their message using a fast LLM call."""
    extraction_prompt = """Analyze this user message and extract ONLY factual information about the user that should be remembered for future conversations.

Extract facts like:
- Name, age, location
- Job, profession, skills
- Preferences (likes, dislikes, how they want responses)
- Important personal details (family, pets, hobbies)
- Technical setup (OS, tools they use)

Return ONLY a JSON array of strings. Each string should be a single fact.
If no personal facts are found, return an empty array: []

Examples:
User: "My name is Tobi and I'm a software developer in Germany"
Output: ["User's name is Tobi", "User is a software developer", "User lives in Germany"]

User: "Can you help me fix this code?"
Output: []

User: "I prefer concise answers, I use Arch Linux with Hyprland"
Output: ["User prefers concise answers", "User uses Arch Linux", "User uses Hyprland window manager"]

Now analyze this message:"""

    try:
        messages = [
            {"role": "system", "content": extraction_prompt},
            {"role": "user", "content": message}
        ]
        
        # Use a fast model for extraction
        response = await ollama_chat(messages, "qwen2.5:1.5b")
        content = response.get("content", "").strip()
        
        # Parse JSON response
        import json
        import re
        
        # Try to find JSON array in response
        match = re.search(r'\[.*?\]', content, re.DOTALL)
        if match:
            memories = json.loads(match.group())
            if isinstance(memories, list):
                return [m for m in memories if isinstance(m, str) and len(m) > 5]
        return []
    except Exception as e:
        print(f"Memory extraction failed: {e}")
        return []


@app.post("/api/chat/smart")
async def smart_chat(data: Dict[str, Any]):
    """Smart chat with context, image support, response styles, memory, and conversation history."""
    message = data.get("message", "")
    model = data.get("model", DEFAULT_MODEL)
    use_search = data.get("use_search", False)
    images = data.get("images", [])
    style = data.get("style", "normal")
    system_prompt_override = data.get("system_prompt", None)
    history = data.get("history", [])  # Conversation history for follow-up questions
    user_memories = data.get("memories", [])  # Things to remember about user
    
    if not message:
        raise HTTPException(status_code=400, detail="Message required")
    
    # Style prompts - stronger enforcement
    style_prompts = {
        "normal": "You are Ryx, a helpful AI assistant. Be balanced, clear and helpful.",
        "concise": """You are Ryx in STRICT CONCISE MODE.
RULES:
- Maximum 1-2 sentences per response
- No greetings, no filler words, no explanations unless asked
- Answer the question directly, nothing more
- If asked for a name/fact, just state it""",
        "explanatory": "You are Ryx. Explain thoroughly with examples and context. Help the user understand deeply. Use analogies when helpful.",
        "learning": "You are Ryx in teaching mode. Explain step-by-step. Assume the user wants to learn. Use analogies and examples. Check understanding.",
        "formal": "You are Ryx. Use professional, formal language. Be precise, structured and thorough."
    }
    
    # Build context
    context_parts = []
    
    # Add user memories if available
    if user_memories:
        memory_context = "What you know about the user:\n"
        for mem in user_memories:
            memory_context += f"- {mem}\n"
        context_parts.append(memory_context)
    
    # Add web search if requested
    if use_search:
        search_result = await searxng_search(message)
        if search_result.get("results"):
            today = __import__('datetime').datetime.now().strftime("%Y-%m-%d")
            search_context = f"TODAY IS {today}. Current web search results for this query:\n"
            for r in search_result["results"][:5]:
                title = r.get('title', '')
                content = r.get('content', '')[:250]
                search_context += f"• {title}: {content}\n"
            search_context += "\nYOU MUST use these search results to answer. The information above is current and accurate."
            context_parts.append(search_context)
    
    # Build system prompt - use override if provided, otherwise use style
    if system_prompt_override:
        system_prompt = system_prompt_override
    else:
        system_prompt = style_prompts.get(style, style_prompts["normal"])
    
    if context_parts:
        system_prompt += "\n\n" + "\n".join(context_parts)
    
    # Build messages with conversation history
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history for context
    for h in history:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    
    # Add current message
    user_msg = {"role": "user", "content": message}
    if images:
        user_msg["images"] = images
    messages.append(user_msg)
    
    response = await ollama_chat(messages, model)
    
    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])
    
    response_content = response.get("content", "")
    
    # Extract memories from conversation (async, non-blocking)
    extracted_memories = []
    if message and len(message) > 20:  # Only analyze substantial messages
        extracted_memories = await extract_memories_from_message(message, model)
    
    return {
        "response": response_content,
        "model": response.get("model", ""),
        "latency_ms": response.get("latency_ms", 0),
        "extracted_memories": extracted_memories
    }

# =============================================================================
# Search Endpoints
# =============================================================================

@app.get("/api/search")
async def search(q: str):
    """Web search endpoint."""
    if not q:
        raise HTTPException(status_code=400, detail="Query required")
    
    result = await searxng_search(q)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result

# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Starting Ryx API on port {API_PORT}")
    print(f"📡 Ollama: {OLLAMA_BASE_URL}")
    print(f"🔍 SearXNG: {SEARXNG_URL}")
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)
