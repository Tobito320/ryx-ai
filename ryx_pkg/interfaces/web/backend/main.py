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
# Memory Functions - MEMORY-FIRST ARCHITECTURE
# =============================================================================

def simple_similarity(s1: str, s2: str) -> float:
    """Simple word-based similarity (0-1). Fast alternative to cosine similarity."""
    words1 = set(s1.lower().split())
    words2 = set(s2.lower().split())
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)

# =============================================================================
# Memory Type Classification (Persona vs General)
# =============================================================================

class MemoryType:
    """Two-tier memory system: Persona facts vs General knowledge."""
    PERSONA = "persona"      # About Tobi (name, location, preferences, skills)
    GENERAL = "general"      # Useful facts learned from conversations
    TRANSIENT = "transient"  # Ignore (questions, greetings, noise)

def classify_memory_type(message: str, fact: str) -> str:
    """Classify a memory as PERSONA, GENERAL, or TRANSIENT."""
    message_lower = message.lower()
    fact_lower = fact.lower()
    
    # PERSONA: Facts specifically about the user
    persona_indicators = [
        r'\b(i live|i\'m from|based in|wohn)\b',  # Location
        r'\b(my name|i\'m called|ich hei[sß]e)\b',  # Name
        r'\b(i prefer|i like|i use|i work|ich bevorzug|ich benutze)\b',  # Preferences
        r'\b(i\'m a|i am a|ich bin ein)\b.*?(developer|engineer|student)',  # Role
        r'\b(my setup|my pc|my gpu|my cpu|my os)\b',  # Tech stack
        r'\b(tobi|tobias)\b',  # Name reference
    ]
    
    for pattern in persona_indicators:
        if re.search(pattern, message_lower) or re.search(pattern, fact_lower):
            return MemoryType.PERSONA
    
    # TRANSIENT: Questions, requests, noise
    transient_patterns = [
        r'^(what is|how do|tell me about|explain|can you)',  # Questions
        r'^(ok|thanks|thx|bye|hi|hello|hey|lol|haha|yes|no|sure|cool|nice)$',  # Greetings
        r'(searched|memory|retrieved|response)',  # Meta-words
        r'^.{0,15}$',  # Too short
        r'\?$',  # Ends with question mark
    ]
    
    for pattern in transient_patterns:
        if re.search(pattern, message_lower) or re.search(pattern, fact_lower):
            return MemoryType.TRANSIENT
    
    # GENERAL: High-value learned facts (solutions, tips)
    if len(fact) > 30:  # Substantial content
        return MemoryType.GENERAL
    
    return MemoryType.TRANSIENT  # Default to not storing

def is_noise_memory(fact: str) -> bool:
    """Check if a memory is noise (transient, trivial, or duplicate)."""
    noise_patterns = [
        r'^(ok|thanks|thx|bye|hi|hello|hey|lol|haha|yes|no|sure|cool|nice)$',
        r'^(what time|tell me a joke|how are you)',
        r'(searched|learned|memory|retrieved)',  # Meta-words
        r'^.{0,10}$',  # Too short
    ]
    fact_lower = fact.lower().strip()
    for pattern in noise_patterns:
        if re.search(pattern, fact_lower):
            return True
    return False

def memory_store(category: str, fact: str, relevance_score: float = 0.5) -> bool:
    """Store a memory fact with deduplication. Returns True if stored."""
    # Filter noise
    if is_noise_memory(fact):
        print(f"Memory rejected (noise): {fact[:50]}")
        return False
    
    # Require minimum confidence
    if relevance_score < 0.5:
        print(f"Memory rejected (low confidence {relevance_score}): {fact[:50]}")
        return False
    
    try:
        conn = sqlite3.connect(str(MEMORY_DB))
        cursor = conn.cursor()
        
        # Check for duplicates (similarity > 0.7)
        cursor.execute("SELECT id, fact, relevance_score FROM memories")
        for row in cursor.fetchall():
            existing_id, existing_fact, existing_score = row
            similarity = simple_similarity(fact, existing_fact)
            if similarity > 0.7:
                # Update existing if new has higher relevance
                if relevance_score > existing_score:
                    cursor.execute(
                        "UPDATE memories SET fact = ?, relevance_score = ?, last_accessed = ? WHERE id = ?",
                        (fact, relevance_score, datetime.now().isoformat(), existing_id)
                    )
                    conn.commit()
                    print(f"Memory updated (similarity {similarity:.2f}): {fact[:50]}")
                else:
                    print(f"Memory skipped (duplicate, similarity {similarity:.2f}): {fact[:50]}")
                conn.close()
                return False
        
        # Store new memory
        cursor.execute(
            "INSERT INTO memories (category, fact, relevance_score) VALUES (?, ?, ?)",
            (category, fact, relevance_score)
        )
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        if success:
            print(f"Memory stored [{category}]: {fact[:50]}")
        return success
    except Exception as e:
        print(f"Memory store error: {e}")
        return False

def memory_retrieve_smart(message: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    SMART memory retrieval - extracts keywords from message and finds relevant memories.
    Returns memories sorted by relevance to the query.
    """
    try:
        conn = sqlite3.connect(str(MEMORY_DB))
        cursor = conn.cursor()
        
        # Extract keywords from message
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'do', 'does', 'did', 
                      'i', 'you', 'he', 'she', 'it', 'we', 'they', 'my', 'your', 'his', 'her',
                      'what', 'where', 'when', 'who', 'how', 'why', 'which', 'can', 'could',
                      'ich', 'du', 'er', 'sie', 'wir', 'ihr', 'mein', 'dein', 'was', 'wo', 'wer', 'wie'}
        keywords = [w.lower() for w in re.findall(r'\b\w+\b', message) if w.lower() not in stop_words and len(w) > 2]
        
        # Get all memories
        cursor.execute("""
            SELECT id, category, fact, relevance_score, last_accessed, access_count
            FROM memories
            ORDER BY relevance_score DESC, access_count DESC
        """)
        
        all_memories = []
        for row in cursor.fetchall():
            mem = {
                "id": row[0],
                "category": row[1],
                "fact": row[2],
                "relevance_score": row[3],
                "last_accessed": row[4],
                "access_count": row[5],
                "match_score": 0.0
            }
            
            # Calculate match score based on keyword overlap
            fact_lower = mem["fact"].lower()
            category_lower = mem["category"].lower()
            
            for keyword in keywords:
                if keyword in fact_lower:
                    mem["match_score"] += 0.3
                if keyword in category_lower:
                    mem["match_score"] += 0.2
            
            # Boost by stored relevance
            mem["match_score"] += mem["relevance_score"] * 0.3
            
            if mem["match_score"] > 0:
                all_memories.append(mem)
        
        # Sort by match score and limit
        all_memories.sort(key=lambda x: x["match_score"], reverse=True)
        results = all_memories[:limit]
        
        # Update access count for retrieved memories
        for mem in results:
            cursor.execute(
                "UPDATE memories SET access_count = access_count + 1, last_accessed = ? WHERE id = ?",
                (datetime.now().isoformat(), mem["id"])
            )
        
        conn.commit()
        conn.close()
        return results
    except Exception as e:
        print(f"Memory retrieve error: {e}")
        return []

def memory_retrieve(topic: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieve relevant memories by topic/category (legacy function)."""
    return memory_retrieve_smart(topic, limit)

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

@app.get("/api/models/{model_name}/status")
async def get_model_status(model_name: str):
    """Get detailed status of a specific model including VRAM usage."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            # Get running models info
            async with session.get(f"{OLLAMA_BASE_URL}/api/ps") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for model in data.get("models", []):
                        if model.get("name") == model_name:
                            # Extract size info
                            size_vram = model.get("size_vram", 0)
                            size_total = model.get("size", 0)
                            
                            return {
                                "name": model_name,
                                "loaded": True,
                                "vram_used_gb": round(size_vram / (1024**3), 2) if size_vram else 0,
                                "size_gb": round(size_total / (1024**3), 2) if size_total else 0,
                                "digest": model.get("digest", ""),
                                "expires_at": model.get("expires_at", "")
                            }
                    
                    # Model not loaded
                    return {
                        "name": model_name,
                        "loaded": False,
                        "vram_used_gb": 0,
                        "size_gb": 0
                    }
        return {"name": model_name, "loaded": False, "vram_used_gb": 0, "size_gb": 0}
    except Exception as e:
        return {"name": model_name, "loaded": False, "error": str(e)}

@app.get("/api/models/vram")
async def get_vram_usage():
    """Get total VRAM usage across all loaded models."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(f"{OLLAMA_BASE_URL}/api/ps") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    total_vram = 0
                    loaded_models = []
                    
                    for model in data.get("models", []):
                        size_vram = model.get("size_vram", 0)
                        total_vram += size_vram
                        loaded_models.append({
                            "name": model.get("name"),
                            "vram_gb": round(size_vram / (1024**3), 2) if size_vram else 0
                        })
                    
                    return {
                        "total_vram_gb": round(total_vram / (1024**3), 2),
                        "max_vram_gb": 16,  # RX 7800 XT has 16GB
                        "usage_percent": round((total_vram / (16 * 1024**3)) * 100, 1),
                        "loaded_models": loaded_models
                    }
        return {"total_vram_gb": 0, "max_vram_gb": 16, "usage_percent": 0, "loaded_models": []}
    except Exception as e:
        return {"error": str(e), "total_vram_gb": 0, "max_vram_gb": 16, "usage_percent": 0}

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
    extraction_prompt = """Analyze this user message and extract ONLY factual information about THE USER that should be remembered.

EXTRACT (high-value personal facts):
- "I live in X" → location: User lives in X
- "My name is X" → personal: User's name is X
- "I prefer X" → preference: User prefers X
- "I use X" (tool/OS/software) → technical: User uses X
- "I work as X" → personal: User works as X
- "My project is X" → project: User's project is X

DO NOT EXTRACT (these are NOT about the user):
- Questions ("What is X?", "How does X work?")
- General facts ("Python is a language")
- Requests ("Help me with X")
- Search queries ("Tell me about X")
- Transient info ("What time is it?")
- Meta-questions about the AI

Return ONLY a JSON array. Format: ["category: fact about the user"]
If NO personal facts, return: []

Examples:
"My name is Tobi, I live in Hagen" → ["personal: User's name is Tobi", "location: User lives in Hagen"]
"What is the weather?" → []
"I prefer concise answers" → ["preference: User prefers concise answers"]
"Explain Kubernetes" → []
"I use Arch Linux with Hyprland" → ["technical: User uses Arch Linux", "technical: User uses Hyprland"]
"Who is the president?" → []

Message to analyze:"""

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
                # Filter: must be about the user, not general facts
                valid = []
                for m in memories:
                    if isinstance(m, str) and len(m) > 10:
                        # Must contain user-related keywords
                        m_lower = m.lower()
                        if any(kw in m_lower for kw in ['user', 'tobi', 'live', 'prefer', 'use', 'work', 'name', 'project']):
                            valid.append(m)
                return valid
        return []
    except Exception as e:
        print(f"Memory extraction failed: {e}")
        return []


def should_use_tools(message: str) -> tuple[bool, str]:
    """
    CRITICAL GATE: Decide if we should invoke ANY tools (memory, search).
    Prevents wasteful API calls for trivial messages like "hi", "ok", "thanks".
    Returns (should_use: bool, reason: str)
    """
    message_lower = message.lower().strip()
    
    # Trivial messages: NO TOOLS
    trivial_exact = {
        'hi', 'hello', 'hey', 'yo', 'sup',
        'thanks', 'thank you', 'thx', 'ty',
        'ok', 'okay', 'k', 'yes', 'no', 'sure', 'yep', 'nope',
        'bye', 'goodbye', 'cya', 'later',
        'lol', 'haha', 'nice', 'cool', 'great', 'awesome',
        'hallo', 'danke', 'ja', 'nein', 'tschüss',  # German
    }
    
    if message_lower in trivial_exact:
        return (False, "Trivial greeting/response")
    
    # Very short queries: NO TOOLS (unless a question)
    if len(message) < 12 and '?' not in message:
        return (False, "Too short for tool usage")
    
    # Generic greetings with variations
    greeting_patterns = [
        r'^(hey|hi|hello|yo)\s*(there|ryx|buddy)?[!.]*$',
        r'^how are you',
        r'^what\'?s up',
        r'^good (morning|afternoon|evening|night)',
        r'^guten (morgen|tag|abend)',
    ]
    
    for pattern in greeting_patterns:
        if re.search(pattern, message_lower):
            return (False, "Greeting detected")
    
    # Questions or substantial messages: USE TOOLS
    return (True, "Substantial query")

def should_search_autonomously(message: str, retrieved_memories: List[Dict] = None) -> tuple[bool, str]:
    """
    AUTONOMOUS tool decision - decides if web search is needed BEFORE generation.
    Returns (needs_search: bool, reason: str)
    
    Decision tree:
    1. If memory answers confidently (relevance > 0.8) → NO SEARCH
    2. If query is time-sensitive (weather, news, prices) → SEARCH
    3. If query is personal (location, preferences) and memory exists → NO SEARCH
    4. If query asks "who is", "what is" about public info → SEARCH
    5. Otherwise → NO SEARCH (use reasoning)
    """
    message_lower = message.lower()
    
    # Check if memory already answers the question with high confidence
    if retrieved_memories:
        # Personal queries that memory should answer
        personal_keywords = ['live', 'wohn', 'location', 'name', 'prefer', 'use', 'work', 'job', 'project']
        is_personal_query = any(kw in message_lower for kw in personal_keywords)
        
        if is_personal_query:
            # Check if we have relevant memory with high confidence
            for mem in retrieved_memories:
                if mem.get('match_score', 0) > 0.3 or mem.get('relevance_score', 0) > 0.7:
                    return (False, f"Memory answers: {mem['fact'][:50]}")
    
    # Time-sensitive queries ALWAYS need search
    time_sensitive = [
        'weather', 'wetter', 'temperature', 'temperatur',
        'news', 'nachrichten', 'today', 'heute', 'current', 'aktuell',
        'price', 'preis', 'cost', 'kosten', 'stock', 'aktie',
        'rate', 'kurs', 'bitcoin', 'crypto', 'dollar', 'euro',
        'latest', 'neueste', 'recent', 'new version', 'neue version',
        'released', 'announced', 'happened', 'update'
    ]
    
    for trigger in time_sensitive:
        if trigger in message_lower:
            return (True, f"Time-sensitive query: {trigger}")
    
    # Factual public knowledge queries need search
    factual_patterns = [
        (r'^(who is|wer ist)', "Public person lookup"),
        (r'^(what is|was ist)\s+(the|der|die|das)?\s*\w+\s*(version|price|cost)', "Version/price lookup"),
        (r'(president|ceo|founder|minister|chancellor|kanzler)', "Public figure lookup"),
        (r'(2024|2025)', "Current year reference"),
    ]
    
    for pattern, reason in factual_patterns:
        if re.search(pattern, message_lower):
            return (True, reason)
    
    # Questions about self/personal context - use memory, not search
    personal_patterns = [
        r'(where do i|wo wohn|my name|mein name|i prefer|ich bevorzug)',
        r'(my project|mein projekt|i use|ich benutze|i work|ich arbeit)',
        r'(about me|über mich|tell me about my|erzähl mir über mein)'
    ]
    
    for pattern in personal_patterns:
        if re.search(pattern, message_lower):
            return (False, "Personal query - use memory")
    
    # Generic questions might need search if no memory context
    question_words = ['what', 'who', 'when', 'where', 'how', 'why', 'which', 'was', 'wer', 'wann', 'wo', 'wie', 'warum']
    starts_with_question = any(message_lower.startswith(qw + ' ') for qw in question_words)
    
    if starts_with_question and not retrieved_memories:
        return (True, "Question without memory context")
    
    return (False, "No search trigger found")


@app.post("/api/chat/smart")
async def smart_chat(data: Dict[str, Any]):
    """
    MEMORY-FIRST Smart Chat - ChatGPT-level autonomy
    
    Architecture:
    1. RETRIEVE memories FIRST (before any decision)
    2. DECIDE tool usage based on memories + query
    3. INJECT context into system prompt
    4. GENERATE response
    5. LEARN from conversation (deduped)
    6. LOG everything for debugging
    """
    start_time = time.time()
    
    message = data.get("message", "")
    model = data.get("model", DEFAULT_MODEL)
    explicit_search = data.get("use_search", False)
    images = data.get("images", [])
    style = data.get("style", "normal")
    system_prompt_override = data.get("system_prompt", None)
    history = data.get("history", [])
    client_memories = data.get("memories", [])
    session_id = data.get("session_id", None)
    
    if not message:
        raise HTTPException(status_code=400, detail="Message required")
    
    # =========================================================================
    # STEP 0: TOOL GATE - Should we even use tools?
    # =========================================================================
    tools_used = []
    tool_decisions = []
    warnings = []
    retrieved_memories = []
    
    use_tools, tool_gate_reason = should_use_tools(message)
    tool_decisions.append(f"Tool gate: {use_tools} ({tool_gate_reason})")
    
    # =========================================================================
    # STEP 1: MEMORY RETRIEVAL (Only if tool gate passes)
    # =========================================================================
    if use_tools:
        # Retrieve memories BEFORE any other decision
        retrieved_memories = memory_retrieve_smart(message, limit=10)
        
        if retrieved_memories:
            tools_used.append("memory_retrieve")
            tool_decisions.append(f"Retrieved {len(retrieved_memories)} memories")
    
    # =========================================================================
    # STEP 2: AUTONOMOUS TOOL DECISION (Based on memories!)
    # =========================================================================
    language = detect_language(message)
    language_prompt = get_language_prompt(language)
    
    # Decide search AFTER checking memories (only if tool gate passed)
    needs_search = False
    search_reason = "Tool gate blocked"
    
    if use_tools:
        needs_search, search_reason = should_search_autonomously(message, retrieved_memories)
        needs_search = needs_search or explicit_search
    
    tool_decisions.append(f"Search decision: {needs_search} ({search_reason})")
    
    # =========================================================================
    # STEP 3: BUILD CONTEXT (Memories injected BEFORE generation)
    # =========================================================================
    
    # System prompt with style
    style_prompts = {
        "normal": """You are Ryx, Tobi's personal AI assistant running locally on his 7800 XT + Ryzen 9.
You have access to his memories and can search the web autonomously.

CRITICAL RULES:
1. Memory is GROUND TRUTH - never contradict stored memories
2. If you remember something about Tobi, use it naturally: "Based on what I know..."
3. Be direct and technical - Tobi is an advanced developer
4. Prefer concise answers unless asked to elaborate""",
        
        "concise": """You are Ryx in STRICT CONCISE MODE.
RULES:
- Maximum 1-2 sentences per response
- No greetings, no filler words
- Answer directly, nothing more
- Memory is ground truth - use it, don't contradict it""",
        
        "explanatory": """You are Ryx. Explain thoroughly with examples and context.
Use the user's stored memories to personalize explanations.
Help the user understand deeply with relevant analogies.""",
        
        "learning": """You are Ryx in teaching mode.
Explain step-by-step, reference user's known technical setup from memory.
Use their context to make examples relevant.""",
        
        "formal": """You are Ryx. Use professional, formal language.
Be precise and structured. Reference stored facts accurately."""
    }
    
    system_prompt = system_prompt_override or style_prompts.get(style, style_prompts["normal"])
    
    # INJECT MEMORIES INTO CONTEXT (Critical - this is what was broken!)
    memory_context = ""
    if retrieved_memories:
        memory_context = "\n\n📌 WHAT YOU KNOW ABOUT TOBI (from memory - treat as ground truth):\n"
        for mem in retrieved_memories[:7]:  # Top 7 most relevant
            category = mem.get('category', 'general')
            fact = mem.get('fact', '')
            score = mem.get('match_score', mem.get('relevance_score', 0))
            memory_context += f"• [{category}] {fact} (confidence: {score:.2f})\n"
        memory_context += "\n⚠️ Use these memories to answer. Do NOT contradict them with web search results.\n"
    
    # Add client-side memories (user-added in settings)
    if client_memories:
        if not memory_context:
            memory_context = "\n\n📌 WHAT YOU KNOW ABOUT TOBI:\n"
        for m in client_memories:
            if m not in [mem.get('fact', '') for mem in retrieved_memories]:
                memory_context += f"• {m}\n"
    
    system_prompt += memory_context
    
    # =========================================================================
    # STEP 4: WEB SEARCH (Only if decided necessary)
    # =========================================================================
    search_context = ""
    if needs_search:
        # Enrich search query with location if relevant
        search_query = message
        location_keywords = ['weather', 'wetter', 'temperature', 'local', 'nearby', 'here']
        if any(kw in message.lower() for kw in location_keywords):
            # Find location from memories
            for mem in retrieved_memories:
                if mem.get('category') == 'location' and 'live' in mem.get('fact', '').lower():
                    # Extract city name
                    fact = mem.get('fact', '')
                    if 'Hagen' in fact:
                        search_query = f"{message} Hagen Germany"
                    elif 'Germany' in fact or 'Deutschland' in fact:
                        search_query = f"{message} Germany"
                    break
        
        search_result = await searxng_search(search_query)
        if search_result.get("results"):
            today = datetime.now().strftime("%Y-%m-%d")
            search_context = f"\n\n🔍 WEB SEARCH RESULTS (today is {today}):\n"
            if search_query != message:
                search_context += f"(Searched: \"{search_query}\" - enriched with your location)\n"
            for r in search_result["results"][:5]:
                title = r.get('title', '')
                content = r.get('content', '')[:150]
                search_context += f"• {title}: {content}\n"
            
            # Add warning about memory vs search
            if retrieved_memories:
                search_context += "\n⚠️ If search results conflict with stored memories about Tobi, TRUST THE MEMORIES (they're from him directly).\n"
            else:
                search_context += "\n✓ Use this information to answer.\n"
            
            tools_used.append("web_search")
            tool_decisions.append(f"Searched: {search_query[:50]}")
        else:
            warnings.append("Web search returned no results")
            tool_decisions.append("Search failed: no results")
    
    system_prompt += search_context
    system_prompt += language_prompt
    
    # =========================================================================
    # STEP 5: GENERATE RESPONSE
    # =========================================================================
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history
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
    latency_ms = (time.time() - start_time) * 1000
    
    # =========================================================================
    # STEP 6: CONFIDENCE CALCULATION (Honest scoring)
    # =========================================================================
    confidence = 0.70  # Base confidence
    
    # Memory boosts confidence
    if retrieved_memories:
        high_match_memories = [m for m in retrieved_memories if m.get('match_score', 0) > 0.3]
        if high_match_memories:
            confidence += 0.15  # Memory directly relevant
        else:
            confidence += 0.05  # Some memory context
    
    # Search boosts confidence for factual queries
    if "web_search" in tools_used:
        confidence += 0.10
    
    # Warnings reduce confidence
    confidence -= 0.05 * len(warnings)
    
    # Cap confidence
    confidence = max(0.3, min(0.98, confidence))
    
    # =========================================================================
    # STEP 7: LEARN FROM CONVERSATION (Only PERSONA facts)
    # =========================================================================
    extracted_memories = []
    stored_memories = []
    
    # Only extract memories if tool gate passed and message is substantial
    if use_tools and message and len(message) > 25:
        extracted_memories = await extract_memories_from_message(message, model)
        for mem in extracted_memories:
            # Parse category from memory string "category: fact"
            if ": " in mem:
                cat, fact = mem.split(": ", 1)
            else:
                cat, fact = "general", mem
            
            # Classify memory type - only store PERSONA or high-value GENERAL
            mem_type = classify_memory_type(message, fact)
            
            if mem_type == MemoryType.PERSONA:
                # Always store persona facts with high confidence
                if memory_store("persona", fact, 0.85):
                    stored_memories.append(f"[persona] {fact}")
            elif mem_type == MemoryType.GENERAL and len(fact) > 50:
                # Only store substantial general facts
                if memory_store("general", fact, 0.65):
                    stored_memories.append(f"[general] {fact}")
            else:
                tool_decisions.append(f"Memory rejected (transient): {fact[:30]}...")
    
    if stored_memories:
        tools_used.append("memory_store")
    
    # =========================================================================
    # STEP 8: LOGGING
    # =========================================================================
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
    
    # Print debug info
    print(f"\n{'='*50}")
    print(f"Query: {message[:80]}")
    print(f"Memories retrieved: {len(retrieved_memories)}")
    print(f"Tool decisions: {tool_decisions}")
    print(f"Tools used: {tools_used}")
    print(f"Confidence: {confidence:.2f}")
    print(f"{'='*50}\n")
    
    return {
        "response": response_content,
        "model": response.get("model", model),
        "latency_ms": latency_ms,
        "extracted_memories": extracted_memories,
        "tools_used": tools_used,
        "confidence": confidence,
        "language": language,
        "warnings": warnings,
        "memories_used": [{"category": m.get("category"), "fact": m.get("fact"), "score": m.get("match_score", m.get("relevance_score", 0))} for m in retrieved_memories[:5]],
        "tool_decisions": tool_decisions
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
async def get_memories(topic: Optional[str] = None, limit: int = 50, category: Optional[str] = None):
    """Get all memories or search by topic/category."""
    if topic:
        memories = memory_retrieve(topic, limit)
    else:
        memories = memory_get_all(limit)
    
    # Filter by category if specified
    if category:
        memories = [m for m in memories if m.get('category', '').lower() == category.lower()]
    
    return {"memories": memories, "count": len(memories)}

@app.get("/api/memory/persona")
async def get_persona_memories(limit: int = 20):
    """Get only persona facts (about the user)."""
    all_memories = memory_get_all(100)
    persona = [m for m in all_memories if m.get('category', '').lower() == 'persona']
    return {"memories": persona[:limit], "count": len(persona)}

@app.get("/api/memory/general")
async def get_general_memories(limit: int = 20):
    """Get only general learned facts."""
    all_memories = memory_get_all(100)
    general = [m for m in all_memories if m.get('category', '').lower() == 'general']
    return {"memories": general[:limit], "count": len(general)}

@app.get("/api/memory/stats")
async def get_memory_stats():
    """Get memory statistics."""
    try:
        conn = sqlite3.connect(str(MEMORY_DB))
        cursor = conn.cursor()
        
        # Total memories
        cursor.execute("SELECT COUNT(*) FROM memories")
        total = cursor.fetchone()[0]
        
        # By category
        cursor.execute("SELECT category, COUNT(*) FROM memories GROUP BY category")
        by_category = dict(cursor.fetchall())
        
        # Average relevance
        cursor.execute("SELECT AVG(relevance_score) FROM memories")
        avg_relevance = cursor.fetchone()[0] or 0
        
        # Most accessed
        cursor.execute("SELECT fact, access_count FROM memories ORDER BY access_count DESC LIMIT 5")
        most_accessed = [{"fact": r[0][:50], "access_count": r[1]} for r in cursor.fetchall()]
        
        conn.close()
        
        return {
            "total_memories": total,
            "by_category": by_category,
            "average_relevance": round(avg_relevance, 3),
            "most_accessed": most_accessed,
            "persona_count": by_category.get("persona", 0),
            "general_count": by_category.get("general", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
