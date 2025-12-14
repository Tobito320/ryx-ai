"""
Ryx AI - FastAPI Backend with Ollama
REST API for RyxHub web interface using Ollama inference.

Features:
- Autonomous tool use (web search, memory, RAG)
- Memory management with SQLite persistence
- Session logging for debugging
- Multilingual support (German, Arabic, English)
"""

import os
import sys
import time
import json
import sqlite3
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import asyncio

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

# Paths
DATA_DIR = Path("/home/tobi/ryx-ai/data")
MEMORY_DB = DATA_DIR / "ryxhub_memory.db"
LOGS_DIR = DATA_DIR / "ryxhub_logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# Memory Database
# =============================================================================

def init_memory_db():
    """Initialize SQLite memory database."""
    conn = sqlite3.connect(str(MEMORY_DB))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            fact TEXT NOT NULL UNIQUE,
            relevance_score REAL DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            access_count INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS session_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            session_id TEXT,
            user_input TEXT,
            model TEXT,
            response_time_ms INTEGER,
            tools_used TEXT,
            confidence REAL,
            memory_stored TEXT,
            response_length INTEGER,
            warnings TEXT,
            language TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_relevance ON memories(relevance_score DESC)")
    conn.commit()
    conn.close()

# Initialize DB on startup
init_memory_db()

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

class MemoryItem(BaseModel):
    id: Optional[int] = None
    category: str
    fact: str
    relevance_score: float = 0.5

class SessionLogEntry(BaseModel):
    timestamp: str
    session_id: Optional[str]
    user_input: str
    model: str
    response_time_ms: int
    tools_used: List[str]
    confidence: float
    memory_stored: List[str]
    response_length: int
    warnings: List[str]
    language: str

# =============================================================================
# Memory Functions
# =============================================================================

def memory_store(category: str, fact: str, relevance_score: float = 0.5) -> bool:
    """Store a memory fact in the database."""
    try:
        conn = sqlite3.connect(str(MEMORY_DB))
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO memories (category, fact, relevance_score) VALUES (?, ?, ?)",
            (category, fact, relevance_score)
        )
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Memory store error: {e}")
        return False

def memory_retrieve(topic: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieve relevant memories by topic/category."""
    try:
        conn = sqlite3.connect(str(MEMORY_DB))
        cursor = conn.cursor()
        # Search by category or fact content
        cursor.execute("""
            SELECT id, category, fact, relevance_score, last_accessed, access_count
            FROM memories
            WHERE category LIKE ? OR fact LIKE ?
            ORDER BY relevance_score DESC, access_count DESC
            LIMIT ?
        """, (f"%{topic}%", f"%{topic}%", limit))
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "category": row[1],
                "fact": row[2],
                "relevance_score": row[3],
                "last_accessed": row[4],
                "access_count": row[5]
            })
            # Update access count and timestamp
            cursor.execute(
                "UPDATE memories SET access_count = access_count + 1, last_accessed = ? WHERE id = ?",
                (datetime.now().isoformat(), row[0])
            )
        conn.commit()
        conn.close()
        return results
    except Exception as e:
        print(f"Memory retrieve error: {e}")
        return []

def memory_get_all(limit: int = 50) -> List[Dict[str, Any]]:
    """Get all memories ordered by relevance."""
    try:
        conn = sqlite3.connect(str(MEMORY_DB))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, category, fact, relevance_score, last_accessed, access_count
            FROM memories
            ORDER BY relevance_score DESC, access_count DESC
            LIMIT ?
        """, (limit,))
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "category": row[1],
                "fact": row[2],
                "relevance_score": row[3],
                "last_accessed": row[4],
                "access_count": row[5]
            })
        conn.close()
        return results
    except Exception as e:
        print(f"Memory get all error: {e}")
        return []

def memory_delete(memory_id: int) -> bool:
    """Delete a specific memory."""
    try:
        conn = sqlite3.connect(str(MEMORY_DB))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Memory delete error: {e}")
        return False

# =============================================================================
# Session Logging
# =============================================================================

def log_session(entry: Dict[str, Any]):
    """Log a session interaction to the database."""
    try:
        conn = sqlite3.connect(str(MEMORY_DB))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO session_logs 
            (session_id, user_input, model, response_time_ms, tools_used, confidence, memory_stored, response_length, warnings, language)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.get("session_id"),
            entry.get("user_input", "")[:500],  # Truncate
            entry.get("model", ""),
            entry.get("response_time_ms", 0),
            json.dumps(entry.get("tools_used", [])),
            entry.get("confidence", 0.5),
            json.dumps(entry.get("memory_stored", [])),
            entry.get("response_length", 0),
            json.dumps(entry.get("warnings", [])),
            entry.get("language", "en")
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Session log error: {e}")

# =============================================================================
# Language Detection
# =============================================================================

def detect_language(text: str) -> str:
    """Detect language from text (simple heuristic)."""
    # Arabic characters
    if re.search(r'[\u0600-\u06FF]', text):
        return "ar"
    # German-specific characters and patterns
    german_patterns = [
        r'\b(ich|du|er|sie|es|wir|ihr|Sie)\b',
        r'\b(der|die|das|den|dem|des)\b',
        r'\b(und|oder|aber|wenn|dass|weil)\b',
        r'\b(ist|sind|war|waren|sein|haben|werden)\b',
        r'[äöüÄÖÜß]'
    ]
    for pattern in german_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return "de"
    return "en"

def get_language_prompt(language: str) -> str:
    """Get language-specific system prompt additions."""
    prompts = {
        "de": "\n\nRespond in German. Use formal 'Sie' unless the user uses 'du'.",
        "ar": "\n\nRespond in Arabic (Modern Standard Arabic). Use appropriate formal register.",
        "en": ""
    }
    return prompts.get(language, "")

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

Return ONLY a JSON array of strings with category prefix. Each string format: "category: fact"
Categories: personal, technical, preference, project, location

If no personal facts are found, return an empty array: []

Examples:
User: "My name is Tobi and I'm a software developer in Germany"
Output: ["personal: User's name is Tobi", "personal: User is a software developer", "location: User lives in Germany"]

User: "Can you help me fix this code?"
Output: []

User: "I prefer concise answers, I use Arch Linux with Hyprland"
Output: ["preference: User prefers concise answers", "technical: User uses Arch Linux", "technical: User uses Hyprland window manager"]

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
        match = re.search(r'\[.*?\]', content, re.DOTALL)
        if match:
            memories = json.loads(match.group())
            if isinstance(memories, list):
                return [m for m in memories if isinstance(m, str) and len(m) > 5]
        return []
    except Exception as e:
        print(f"Memory extraction failed: {e}")
        return []


def should_search_autonomously(message: str) -> bool:
    """Determine if a query needs web search based on content analysis."""
    message_lower = message.lower()
    
    # Keywords that strongly suggest need for search
    search_triggers = [
        # Current information
        'today', 'current', 'latest', 'recent', 'now', 'right now',
        'this week', 'this month', 'this year', '2024', '2025',
        # Factual queries
        'who is', 'what is', 'when did', 'where is', 'why did', 'how to',
        'what are', 'who are', 'when was', 'where was',
        # News/Events
        'news', 'update', 'released', 'announced', 'happened',
        # Prices/Data
        'price', 'cost', 'stock', 'weather', 'temperature',
        # Specific lookups
        'president', 'ceo', 'founder', 'version',
        # German equivalents
        'wetter', 'heute', 'aktuell', 'neueste', 'preis',
        'wer ist', 'was ist', 'wann', 'wo ist',
        # Arabic triggers (transliterated and Arabic script)
        'الآن', 'اليوم', 'من هو', 'ما هو', 'أين'
    ]
    
    for trigger in search_triggers:
        if trigger in message_lower:
            return True
    
    # Question patterns
    question_patterns = [
        r'^(who|what|when|where|why|how|which)\s',
        r'^(wer|was|wann|wo|warum|wie|welche)\s',
        r'^(من|ما|متى|أين|لماذا|كيف)\s',
        r'\?$'
    ]
    
    for pattern in question_patterns:
        if re.search(pattern, message_lower):
            return True
    
    return False


@app.post("/api/chat/smart")
async def smart_chat(data: Dict[str, Any]):
    """
    Smart chat with AUTONOMOUS tool use:
    - Auto web search when needed (no explicit request required)
    - Memory retrieval and storage
    - Language detection and response matching
    - Response styles
    - Conversation history
    - Detailed logging
    """
    start_time = time.time()
    
    message = data.get("message", "")
    model = data.get("model", DEFAULT_MODEL)
    use_search = data.get("use_search", False)  # Explicit search request
    images = data.get("images", [])
    style = data.get("style", "normal")
    system_prompt_override = data.get("system_prompt", None)
    history = data.get("history", [])
    user_memories = data.get("memories", [])  # Client-side memories
    session_id = data.get("session_id", None)
    
    if not message:
        raise HTTPException(status_code=400, detail="Message required")
    
    # Track what tools we use
    tools_used = []
    warnings = []
    confidence = 0.85  # Base confidence
    
    # Language detection
    language = detect_language(message)
    language_prompt = get_language_prompt(language)
    
    # AUTONOMOUS: Decide if we need web search
    needs_search = use_search or should_search_autonomously(message)
    
    # Style prompts
    style_prompts = {
        "normal": "You are Ryx, Tobi's local AI assistant. Be balanced, clear and helpful. Be direct and technical - Tobi is an advanced developer.",
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
    
    # 1. Retrieve relevant memories from database
    db_memories = memory_retrieve(message, limit=5)
    if db_memories:
        memory_context = "What you remember about the user:\n"
        for mem in db_memories:
            memory_context += f"- {mem['fact']}\n"
        context_parts.append(memory_context)
        tools_used.append("memory_retrieve")
    
    # 2. Add client-provided memories
    if user_memories:
        if not db_memories:  # Don't duplicate header
            context_parts.append("What you know about the user:\n" + "\n".join(f"- {m}" for m in user_memories))
        else:
            for m in user_memories:
                if m not in [mem['fact'] for mem in db_memories]:
                    context_parts[-1] += f"\n- {m}"
    
    # 3. AUTONOMOUS web search
    search_context = ""
    if needs_search:
        search_result = await searxng_search(message)
        if search_result.get("results"):
            today = datetime.now().strftime("%Y-%m-%d")
            search_context = f"\n\n📡 TODAY IS {today}. Live web search results:\n"
            for r in search_result["results"][:5]:
                title = r.get('title', '')
                content = r.get('content', '')[:200]
                url = r.get('url', '')
                search_context += f"• {title}: {content}\n"
            search_context += "\n⚠️ USE these search results to answer. This information is current."
            context_parts.append(search_context)
            tools_used.append("web_search")
            confidence = 0.92  # Higher confidence with search
        else:
            warnings.append("Web search returned no results")
            confidence = 0.7
    
    # Build system prompt
    if system_prompt_override:
        system_prompt = system_prompt_override
    else:
        system_prompt = style_prompts.get(style, style_prompts["normal"])
    
    # Add language instruction
    system_prompt += language_prompt
    
    # Add context
    if context_parts:
        system_prompt += "\n\n" + "\n".join(context_parts)
    
    # Add tool usage indicator instruction
    if tools_used:
        system_prompt += f"\n\n[Tools used: {', '.join(tools_used)}. You may mention this if relevant.]"
    
    # Build messages
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history
    for h in history:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    
    # Add current message
    user_msg = {"role": "user", "content": message}
    if images:
        user_msg["images"] = images
    messages.append(user_msg)
    
    # Call LLM
    response = await ollama_chat(messages, model)
    
    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])
    
    response_content = response.get("content", "")
    latency_ms = (time.time() - start_time) * 1000
    
    # AUTONOMOUS: Extract and store memories
    extracted_memories = []
    stored_memories = []
    if message and len(message) > 20:
        extracted_memories = await extract_memories_from_message(message, model)
        for mem in extracted_memories:
            # Parse category from memory string "category: fact"
            if ": " in mem:
                cat, fact = mem.split(": ", 1)
            else:
                cat, fact = "general", mem
            if memory_store(cat, fact, 0.6):
                stored_memories.append(fact)
                tools_used.append("memory_store")
    
    # Calculate confidence based on factors
    if not tools_used:
        confidence = 0.75  # Lower without tools
    if warnings:
        confidence -= 0.1 * len(warnings)
    confidence = max(0.3, min(1.0, confidence))
    
    # Log the session
    log_entry = {
        "session_id": session_id,
        "user_input": message,
        "model": model,
        "response_time_ms": int(latency_ms),
        "tools_used": tools_used,
        "confidence": confidence,
        "memory_stored": stored_memories,
        "response_length": len(response_content),
        "warnings": warnings,
        "language": language
    }
    log_session(log_entry)
    
    # Add confidence warning if low
    if confidence < 0.8 and warnings:
        response_content += "\n\n⚠️ Uncertain—verify independently"
    
    return {
        "response": response_content,
        "model": response.get("model", model),
        "latency_ms": latency_ms,
        "extracted_memories": extracted_memories,
        "tools_used": tools_used,
        "confidence": confidence,
        "language": language,
        "warnings": warnings
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
# Memory Endpoints
# =============================================================================

@app.get("/api/memory")
async def get_memories(topic: Optional[str] = None, limit: int = 50):
    """Get all memories or search by topic."""
    if topic:
        memories = memory_retrieve(topic, limit)
    else:
        memories = memory_get_all(limit)
    return {"memories": memories, "count": len(memories)}

@app.post("/api/memory")
async def store_memory(data: Dict[str, Any]):
    """Store a new memory."""
    category = data.get("category", "general")
    fact = data.get("fact", "")
    relevance = data.get("relevance_score", 0.5)
    
    if not fact:
        raise HTTPException(status_code=400, detail="Fact is required")
    
    success = memory_store(category, fact, relevance)
    return {"success": success, "category": category, "fact": fact}

@app.delete("/api/memory/{memory_id}")
async def delete_memory(memory_id: int):
    """Delete a specific memory."""
    success = memory_delete(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"success": True, "deleted_id": memory_id}

@app.post("/api/memory/bulk")
async def store_memories_bulk(data: Dict[str, Any]):
    """Store multiple memories at once."""
    memories = data.get("memories", [])
    stored = 0
    for mem in memories:
        if isinstance(mem, str):
            if memory_store("general", mem):
                stored += 1
        elif isinstance(mem, dict):
            if memory_store(mem.get("category", "general"), mem.get("fact", ""), mem.get("relevance_score", 0.5)):
                stored += 1
    return {"success": True, "stored_count": stored, "total_submitted": len(memories)}

# =============================================================================
# Session Logs Endpoints
# =============================================================================

@app.get("/api/logs")
async def get_session_logs(limit: int = 100, session_id: Optional[str] = None):
    """Get session logs for debugging."""
    try:
        conn = sqlite3.connect(str(MEMORY_DB))
        cursor = conn.cursor()
        
        if session_id:
            cursor.execute("""
                SELECT timestamp, session_id, user_input, model, response_time_ms, 
                       tools_used, confidence, memory_stored, response_length, warnings, language
                FROM session_logs
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session_id, limit))
        else:
            cursor.execute("""
                SELECT timestamp, session_id, user_input, model, response_time_ms, 
                       tools_used, confidence, memory_stored, response_length, warnings, language
                FROM session_logs
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
        
        logs = []
        for row in cursor.fetchall():
            logs.append({
                "timestamp": row[0],
                "session_id": row[1],
                "user_input": row[2],
                "model": row[3],
                "response_time_ms": row[4],
                "tools_used": json.loads(row[5]) if row[5] else [],
                "confidence": row[6],
                "memory_stored": json.loads(row[7]) if row[7] else [],
                "response_length": row[8],
                "warnings": json.loads(row[9]) if row[9] else [],
                "language": row[10]
            })
        conn.close()
        return {"logs": logs, "count": len(logs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs/stats")
async def get_log_stats():
    """Get statistics from session logs."""
    try:
        conn = sqlite3.connect(str(MEMORY_DB))
        cursor = conn.cursor()
        
        # Total interactions
        cursor.execute("SELECT COUNT(*) FROM session_logs")
        total = cursor.fetchone()[0]
        
        # Average response time
        cursor.execute("SELECT AVG(response_time_ms) FROM session_logs")
        avg_latency = cursor.fetchone()[0] or 0
        
        # Average confidence
        cursor.execute("SELECT AVG(confidence) FROM session_logs")
        avg_confidence = cursor.fetchone()[0] or 0
        
        # Tools usage
        cursor.execute("SELECT tools_used FROM session_logs WHERE tools_used IS NOT NULL")
        all_tools = []
        for row in cursor.fetchall():
            tools = json.loads(row[0]) if row[0] else []
            all_tools.extend(tools)
        
        from collections import Counter
        tool_counts = dict(Counter(all_tools))
        
        # Language distribution
        cursor.execute("SELECT language, COUNT(*) FROM session_logs GROUP BY language")
        language_dist = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "total_interactions": total,
            "average_latency_ms": round(avg_latency, 2),
            "average_confidence": round(avg_confidence, 3),
            "tool_usage": tool_counts,
            "language_distribution": language_dist
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Starting Ryx API on port {API_PORT}")
    print(f"📡 Ollama: {OLLAMA_BASE_URL}")
    print(f"🔍 SearXNG: {SEARXNG_URL}")
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)
