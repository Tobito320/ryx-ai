"""
Ryx AI - Advanced Memory System

Implements modern AI memory patterns:
1. Episodic Memory - Short-term session context
2. Persistent Memory - Long-term user knowledge
3. Semantic Memory - Vector embeddings for RAG
4. User Profile - Preferences, style, environment
5. Dynamic Context - Evolving understanding

Inspired by:
- Microsoft 365 Copilot Memory
- OpenAI ChatGPT Memory
- Mem0 AI Agents
"""

import sqlite3
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import threading


@dataclass
class Memory:
    """A single memory unit"""
    id: str
    content: str
    memory_type: str  # 'fact', 'preference', 'interaction', 'task', 'environment'
    importance: float  # 0.0 - 1.0
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    decay_rate: float = 0.01  # How fast memory fades


@dataclass 
class UserProfile:
    """Comprehensive user profile built from interactions"""
    # Identity
    preferred_name: Optional[str] = None
    
    # Environment
    os: str = "linux"
    distro: str = "arch"
    wm: str = "hyprland"
    shell: str = "zsh"
    editor: str = "nvim"
    terminal: str = "kitty"
    
    # Coding preferences
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    coding_style: str = "concise"  # 'verbose', 'concise', 'minimal'
    
    # Communication style
    response_length: str = "short"  # 'short', 'medium', 'detailed'
    tone: str = "direct"  # 'friendly', 'professional', 'direct'
    prefers_examples: bool = True
    prefers_explanations: bool = False  # User said: ryx should DO, not explain
    
    # Paths and locations
    project_paths: Dict[str, str] = field(default_factory=dict)
    config_paths: Dict[str, str] = field(default_factory=dict)
    
    # Behavioral patterns
    active_hours: List[int] = field(default_factory=list)  # Hours when user is active
    common_tasks: List[str] = field(default_factory=list)
    
    # Learning
    expertise_areas: Dict[str, float] = field(default_factory=dict)  # topic -> skill level


class EpisodicMemory:
    """
    Short-term memory for current session.
    Stores recent interactions, maintains conversation flow.
    """
    
    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self.turns: List[Dict[str, Any]] = []
        self.session_start = datetime.now()
        self.session_context: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def add_turn(self, role: str, content: str, metadata: Dict = None):
        """Add a conversation turn"""
        with self._lock:
            turn = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            self.turns.append(turn)
            
            # Trim to max size
            if len(self.turns) > self.max_turns:
                self.turns = self.turns[-self.max_turns:]
    
    def get_context(self, last_n: int = 5) -> List[Dict]:
        """Get recent context for AI"""
        with self._lock:
            return self.turns[-last_n:]
    
    def get_summary(self) -> str:
        """Get compressed summary of session"""
        if not self.turns:
            return ""
        
        topics = set()
        for turn in self.turns:
            # Extract key topics (simple word extraction)
            words = turn["content"].lower().split()
            for word in words:
                if len(word) > 5 and word.isalpha():
                    topics.add(word)
        
        return f"Session topics: {', '.join(list(topics)[:10])}"
    
    def set_context(self, key: str, value: Any):
        """Set session context variable"""
        self.session_context[key] = value
    
    def get_context_var(self, key: str, default: Any = None) -> Any:
        """Get session context variable"""
        return self.session_context.get(key, default)
    
    def clear(self):
        """Clear episodic memory (new session)"""
        with self._lock:
            self.turns = []
            self.session_context = {}
            self.session_start = datetime.now()


class PersistentMemory:
    """
    Long-term memory with semantic search.
    Stores facts, preferences, and learned information.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            from core.paths import get_data_dir
            db_path = get_data_dir() / "ryx_memory.db"
        
        self.db_path = db_path
        self._init_db()
        self.ollama = None
    
    def _init_db(self):
        """Initialize memory database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Core memories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                importance REAL DEFAULT 0.5,
                embedding BLOB,
                metadata TEXT,
                created_at TEXT,
                last_accessed TEXT,
                access_count INTEGER DEFAULT 0,
                decay_rate REAL DEFAULT 0.01
            )
        """)
        
        # User profile table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                source TEXT,
                updated_at TEXT
            )
        """)
        
        # Session summaries (compressed old sessions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                summary TEXT NOT NULL,
                key_topics TEXT,
                start_time TEXT,
                end_time TEXT,
                turn_count INTEGER
            )
        """)
        
        # Semantic index for fast similarity search
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_type 
            ON memories(memory_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_importance 
            ON memories(importance DESC)
        """)
        
        conn.commit()
        conn.close()
    
    def _get_ollama(self):
        """Lazy load Ollama client"""
        if self.ollama is None:
            from core.ollama_client import OllamaClient
            self.ollama = OllamaClient()
        return self.ollama
    
    def _compute_embedding(self, text: str) -> Optional[List[float]]:
        """Compute embedding using Ollama"""
        try:
            ollama = self._get_ollama()
            # Use nomic-embed-text or similar if available
            # For now, use a simple hash-based pseudo-embedding
            # In production, use: ollama.embeddings(model="nomic-embed-text", prompt=text)
            
            # Simple word-based embedding (fallback)
            words = text.lower().split()
            embedding = [0.0] * 64
            for i, word in enumerate(words[:64]):
                h = int(hashlib.md5(word.encode()).hexdigest()[:8], 16)
                embedding[i % 64] += (h % 1000) / 1000.0
            
            # Normalize
            magnitude = sum(x*x for x in embedding) ** 0.5
            if magnitude > 0:
                embedding = [x / magnitude for x in embedding]
            
            return embedding
        except:
            return None
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two embeddings"""
        if not a or not b or len(a) != len(b):
            return 0.0
        
        dot = sum(x*y for x, y in zip(a, b))
        mag_a = sum(x*x for x in a) ** 0.5
        mag_b = sum(x*x for x in b) ** 0.5
        
        if mag_a == 0 or mag_b == 0:
            return 0.0
        
        return dot / (mag_a * mag_b)
    
    def store(self, content: str, memory_type: str, importance: float = 0.5, 
              metadata: Dict = None) -> str:
        """Store a new memory"""
        memory_id = hashlib.sha256(f"{content}{time.time()}".encode()).hexdigest()[:16]
        embedding = self._compute_embedding(content)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO memories 
            (id, content, memory_type, importance, embedding, metadata, created_at, last_accessed, access_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory_id,
            content,
            memory_type,
            importance,
            json.dumps(embedding) if embedding else None,
            json.dumps(metadata or {}),
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            0
        ))
        
        conn.commit()
        conn.close()
        
        return memory_id
    
    def recall(self, query: str, memory_type: Optional[str] = None, 
               limit: int = 5, min_similarity: float = 0.3) -> List[Memory]:
        """
        Recall relevant memories using semantic search.
        This is the RAG retrieval step.
        """
        query_embedding = self._compute_embedding(query)
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get candidate memories
        if memory_type:
            cursor.execute("""
                SELECT * FROM memories 
                WHERE memory_type = ?
                ORDER BY importance DESC, access_count DESC
                LIMIT 100
            """, (memory_type,))
        else:
            cursor.execute("""
                SELECT * FROM memories 
                ORDER BY importance DESC, access_count DESC
                LIMIT 100
            """)
        
        rows = cursor.fetchall()
        
        # Compute similarities and rank
        scored_memories = []
        for row in rows:
            memory_embedding = json.loads(row["embedding"]) if row["embedding"] else None
            
            if query_embedding and memory_embedding:
                similarity = self._cosine_similarity(query_embedding, memory_embedding)
            else:
                # Fallback to keyword matching
                query_words = set(query.lower().split())
                content_words = set(row["content"].lower().split())
                overlap = len(query_words & content_words)
                similarity = overlap / max(len(query_words), 1)
            
            if similarity >= min_similarity:
                # Apply importance and recency boost
                recency_days = (datetime.now() - datetime.fromisoformat(row["last_accessed"])).days
                recency_boost = 1.0 / (1.0 + recency_days * 0.1)
                
                final_score = similarity * 0.6 + row["importance"] * 0.3 + recency_boost * 0.1
                
                memory = Memory(
                    id=row["id"],
                    content=row["content"],
                    memory_type=row["memory_type"],
                    importance=row["importance"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    created_at=datetime.fromisoformat(row["created_at"]),
                    last_accessed=datetime.fromisoformat(row["last_accessed"]),
                    access_count=row["access_count"]
                )
                scored_memories.append((final_score, memory))
        
        # Sort by score and return top results
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        
        # Update access counts for returned memories
        result_memories = []
        for score, memory in scored_memories[:limit]:
            cursor.execute("""
                UPDATE memories 
                SET access_count = access_count + 1,
                    last_accessed = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), memory.id))
            result_memories.append(memory)
        
        conn.commit()
        conn.close()
        
        return result_memories
    
    def update_profile(self, key: str, value: str, confidence: float = 1.0, source: str = ""):
        """Update user profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO user_profile (key, value, confidence, source, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (key, value, confidence, source, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_profile(self) -> UserProfile:
        """Load user profile from database"""
        profile = UserProfile()
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT key, value FROM user_profile")
        
        for row in cursor.fetchall():
            key, value = row["key"], row["value"]
            if hasattr(profile, key):
                attr_type = type(getattr(profile, key))
                if attr_type == list:
                    setattr(profile, key, json.loads(value))
                elif attr_type == dict:
                    setattr(profile, key, json.loads(value))
                elif attr_type == bool:
                    setattr(profile, key, value.lower() == "true")
                else:
                    setattr(profile, key, value)
        
        conn.close()
        return profile
    
    def save_session_summary(self, episodic: EpisodicMemory):
        """Compress and save session to long-term memory"""
        if not episodic.turns:
            return
        
        summary = episodic.get_summary()
        topics = [t["content"][:50] for t in episodic.turns[-3:]]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO session_summaries 
            (summary, key_topics, start_time, end_time, turn_count)
            VALUES (?, ?, ?, ?, ?)
        """, (
            summary,
            json.dumps(topics),
            episodic.session_start.isoformat(),
            datetime.now().isoformat(),
            len(episodic.turns)
        ))
        
        conn.commit()
        conn.close()
    
    def forget_old_memories(self, days_threshold: int = 30, min_importance: float = 0.3):
        """Apply memory decay - forget unimportant old memories"""
        cutoff = datetime.now() - timedelta(days=days_threshold)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM memories 
            WHERE last_accessed < ? 
            AND importance < ?
            AND access_count < 3
        """, (cutoff.isoformat(), min_importance))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted


class RyxMemory:
    """
    Unified memory system for Ryx AI.
    Combines episodic, persistent, and profile memory.
    """
    
    def __init__(self):
        self.episodic = EpisodicMemory()
        self.persistent = PersistentMemory()
        self._profile_cache: Optional[UserProfile] = None
    
    @property
    def profile(self) -> UserProfile:
        """Get user profile (cached)"""
        if self._profile_cache is None:
            self._profile_cache = self.persistent.get_profile()
        return self._profile_cache
    
    def remember(self, content: str, memory_type: str = "fact", 
                 importance: float = 0.5, metadata: Dict = None):
        """Store something in long-term memory"""
        return self.persistent.store(content, memory_type, importance, metadata)
    
    def recall(self, query: str, memory_type: str = None, limit: int = 5) -> List[Memory]:
        """Recall relevant memories"""
        return self.persistent.recall(query, memory_type, limit)
    
    def get_context_for_query(self, query: str) -> Dict[str, Any]:
        """
        Build rich context for AI query.
        Combines episodic context, relevant memories, and user profile.
        """
        context = {
            "recent_conversation": self.episodic.get_context(last_n=5),
            "session_context": self.episodic.session_context,
            "relevant_memories": [],
            "user_preferences": {}
        }
        
        # Get relevant memories
        memories = self.recall(query, limit=3)
        context["relevant_memories"] = [
            {"content": m.content, "type": m.memory_type}
            for m in memories
        ]
        
        # Add user preferences
        profile = self.profile
        context["user_preferences"] = {
            "editor": profile.editor,
            "shell": profile.shell,
            "response_style": profile.response_length,
            "prefers_action": not profile.prefers_explanations,
        }
        
        return context
    
    def learn_from_interaction(self, query: str, response: str, success: bool = True):
        """Learn from an interaction"""
        # Add to episodic
        self.episodic.add_turn("user", query)
        self.episodic.add_turn("assistant", response)
        
        # Extract and store important facts
        importance = 0.6 if success else 0.3
        
        # Store successful interactions as learnable patterns
        if success and len(query) > 20:
            self.persistent.store(
                f"User asked: {query[:100]}",
                memory_type="interaction",
                importance=importance,
                metadata={"response_snippet": response[:100], "success": success}
            )
    
    def learn_preference(self, key: str, value: str, source: str = "explicit"):
        """Learn a user preference"""
        self.persistent.update_profile(key, value, confidence=1.0, source=source)
        self._profile_cache = None  # Invalidate cache
    
    def end_session(self):
        """End current session, save to long-term memory"""
        self.persistent.save_session_summary(self.episodic)
        self.episodic.clear()
    
    def maintain(self) -> Dict[str, int]:
        """Run memory maintenance (forget old, unimportant memories)"""
        deleted = self.persistent.forget_old_memories()
        return {"memories_forgotten": deleted}


# Global memory instance
_memory: Optional[RyxMemory] = None


def get_memory() -> RyxMemory:
    """Get or create global memory instance"""
    global _memory
    if _memory is None:
        _memory = RyxMemory()
    return _memory
