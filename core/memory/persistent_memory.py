"""
Ryx AI - Persistent Memory System

A comprehensive, user-scoped memory system with:
- Encrypted SQLite storage for facts, preferences, session context
- Embedding-based recall with recency/importance scoring
- Periodic compaction and garbage collection
- Session stitching for seamless memory across reboots

Based on best practices from MemGPT and other agentic repos.
"""

import os
import re
import json
import sqlite3
import hashlib
import base64
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types of memories that can be stored"""
    FACT = "fact"              # Learned facts about user/system
    PREFERENCE = "preference"  # User preferences
    SESSION = "session"        # Session context and history
    SKILL = "skill"            # Learned skills and patterns
    ERROR = "error"            # Error patterns and fixes


@dataclass
class MemoryEntry:
    """A single memory entry with metadata"""
    id: str
    memory_type: MemoryType
    key: str
    value: Any
    importance: float = 1.0      # 0.0 - 1.0 importance score
    access_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_accessed: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['memory_type'] = self.memory_type.value
        return d
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'MemoryEntry':
        d = d.copy()
        d['memory_type'] = MemoryType(d['memory_type'])
        return cls(**d)


@dataclass
class UserPreferences:
    """User preferences that persist across sessions"""
    language: str = "de"                    # Preferred language
    device: str = "arch-linux"              # Device type
    vram_mb: int = 16000                    # Available VRAM (16GB for RX 7800 XT)
    max_vram_percent: float = 90.0          # Max VRAM usage percentage
    ai_sidebar_auto_load: bool = False      # Don't auto-load AI in Surf
    preferred_models: Dict[str, str] = field(default_factory=dict)
    concise_responses: bool = True          # Prefer concise responses
    theme: str = "dark"                     # UI theme preference
    keyboard_first: bool = True             # Keyboard-driven UX
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'UserPreferences':
        return cls(**d)


class SimpleEncryption:
    """
    Simple XOR-based encryption for local data protection.
    Not cryptographically strong, but provides basic obfuscation.
    For production, consider using cryptography.fernet.
    """
    
    def __init__(self, key: Optional[str] = None):
        # Use machine-specific key if not provided
        if key is None:
            key = self._get_machine_key()
        self.key = key.encode('utf-8') if isinstance(key, str) else key
    
    def _get_machine_key(self) -> str:
        """Generate a machine-specific key"""
        # Combine multiple machine identifiers
        identifiers = [
            os.environ.get('USER', 'ryx'),
            os.environ.get('HOME', '/home'),
            str(Path.home()),
        ]
        combined = '|'.join(identifiers)
        return hashlib.sha256(combined.encode()).hexdigest()[:32]
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data (handles Unicode properly)"""
        # Encode to bytes first (UTF-8)
        data_bytes = data.encode('utf-8')
        # Extend key to match data length
        key_extended = (self.key * (len(data_bytes) // len(self.key) + 1))[:len(data_bytes)]
        # XOR encrypt
        encrypted = bytes(a ^ b for a, b in zip(data_bytes, key_extended))
        return base64.b64encode(encrypted).decode('ascii')
    
    def decrypt(self, data: str) -> str:
        """Decrypt string data (handles Unicode properly)"""
        # Decode from base64
        decoded = base64.b64decode(data.encode('ascii'))
        # Extend key to match decoded length
        key_extended = (self.key * (len(decoded) // len(self.key) + 1))[:len(decoded)]
        # XOR decrypt
        decrypted = bytes(a ^ b for a, b in zip(decoded, key_extended))
        return decrypted.decode('utf-8')


class PersistentMemory:
    """
    Persistent, encrypted memory system for Ryx AI.
    
    Features:
    - SQLite-backed storage with encryption
    - User preferences persistence
    - Session stitching across restarts
    - Importance-based recall with recency weighting
    - Automatic compaction and cleanup
    
    Usage:
        memory = PersistentMemory()
        
        # Store a fact
        memory.store_fact("user_name", "Tobi")
        
        # Get user preferences
        prefs = memory.get_preferences()
        prefs.language = "de"
        memory.save_preferences(prefs)
        
        # Find related memories
        memories = memory.recall("hyprland config")
    """
    
    def __init__(self, db_path: Optional[Path] = None, encrypt: bool = True):
        from core.paths import get_data_dir
        
        if db_path is None:
            db_path = get_data_dir() / "persistent_memory.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.encrypt = encrypt
        self.crypto = SimpleEncryption() if encrypt else None
        
        self._init_db()
        self._preferences: Optional[UserPreferences] = None
    
    def _init_db(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            conn.executescript("""
                -- Main memory table
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    memory_type TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    importance REAL DEFAULT 1.0,
                    access_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_accessed TEXT NOT NULL,
                    tags TEXT DEFAULT '[]',
                    embedding BLOB
                );
                
                CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(memory_type);
                CREATE INDEX IF NOT EXISTS idx_memory_key ON memories(key);
                CREATE INDEX IF NOT EXISTS idx_memory_importance ON memories(importance DESC);
                CREATE INDEX IF NOT EXISTS idx_memory_accessed ON memories(last_accessed DESC);
                
                -- User preferences table
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    preferences TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                
                -- Session history table
                CREATE TABLE IF NOT EXISTS session_history (
                    session_id TEXT PRIMARY KEY,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    summary TEXT,
                    tasks_completed INTEGER DEFAULT 0,
                    tasks_failed INTEGER DEFAULT 0,
                    context TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_session_time ON session_history(start_time DESC);
                
                -- Error patterns table (for self-healing)
                CREATE TABLE IF NOT EXISTS error_patterns (
                    id TEXT PRIMARY KEY,
                    error_signature TEXT NOT NULL,
                    fix_pattern TEXT,
                    success_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0,
                    last_seen TEXT NOT NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_error_signature ON error_patterns(error_signature);
            """)
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _generate_id(self, content: str) -> str:
        """Generate unique ID for memory entry (24 chars for lower collision risk)"""
        timestamp = datetime.now().isoformat()
        combined = f"{content}{timestamp}"
        return hashlib.sha256(combined.encode()).hexdigest()[:24]
    
    def _encrypt_value(self, value: Any) -> str:
        """Encrypt and serialize a value"""
        json_str = json.dumps(value)
        if self.crypto:
            return self.crypto.encrypt(json_str)
        return json_str
    
    def _decrypt_value(self, encrypted: str) -> Any:
        """Decrypt and deserialize a value"""
        if self.crypto:
            json_str = self.crypto.decrypt(encrypted)
        else:
            json_str = encrypted
        return json.loads(json_str)
    
    # ─────────────────────────────────────────────────────────────
    # Memory Operations
    # ─────────────────────────────────────────────────────────────
    
    def store(
        self,
        key: str,
        value: Any,
        memory_type: MemoryType = MemoryType.FACT,
        importance: float = 1.0,
        tags: Optional[List[str]] = None
    ) -> str:
        """Store a memory entry"""
        memory_id = self._generate_id(f"{key}:{str(value)}")
        now = datetime.now().isoformat()
        
        encrypted_value = self._encrypt_value(value)
        tags_json = json.dumps(tags or [])
        
        with self._get_connection() as conn:
            # Check if key exists and update instead
            existing = conn.execute(
                "SELECT id FROM memories WHERE key = ? AND memory_type = ?",
                (key, memory_type.value)
            ).fetchone()
            
            if existing:
                conn.execute("""
                    UPDATE memories
                    SET value = ?, importance = ?, tags = ?, updated_at = ?
                    WHERE id = ?
                """, (encrypted_value, importance, tags_json, now, existing['id']))
                return existing['id']
            else:
                conn.execute("""
                    INSERT INTO memories 
                    (id, memory_type, key, value, importance, access_count, 
                     created_at, updated_at, last_accessed, tags)
                    VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
                """, (memory_id, memory_type.value, key, encrypted_value, 
                      importance, now, now, now, tags_json))
                return memory_id
    
    def store_fact(self, key: str, value: Any, importance: float = 1.0) -> str:
        """Convenience: store a fact"""
        return self.store(key, value, MemoryType.FACT, importance)
    
    def store_preference(self, key: str, value: Any) -> str:
        """Convenience: store a user preference"""
        return self.store(key, value, MemoryType.PREFERENCE, importance=2.0)
    
    def get(self, key: str, memory_type: Optional[MemoryType] = None) -> Optional[Any]:
        """Retrieve a memory by key"""
        with self._get_connection() as conn:
            if memory_type:
                row = conn.execute(
                    "SELECT value FROM memories WHERE key = ? AND memory_type = ?",
                    (key, memory_type.value)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT value FROM memories WHERE key = ?",
                    (key,)
                ).fetchone()
            
            if row:
                # Update access stats
                conn.execute("""
                    UPDATE memories
                    SET access_count = access_count + 1, last_accessed = ?
                    WHERE key = ?
                """, (datetime.now().isoformat(), key))
                
                return self._decrypt_value(row['value'])
        
        return None
    
    def recall(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10,
        min_importance: float = 0.0
    ) -> List[MemoryEntry]:
        """
        Recall memories relevant to a query.
        Uses keyword matching with recency and importance weighting.
        
        TODO: Add embedding-based semantic search
        """
        import re
        # Split on whitespace, underscores, and hyphens for better matching
        query_words = set(re.split(r'[\s_\-]+', query.lower()))
        results = []
        
        with self._get_connection() as conn:
            type_filter = f"AND memory_type = '{memory_type.value}'" if memory_type else ""
            
            rows = conn.execute(f"""
                SELECT * FROM memories
                WHERE importance >= ?
                {type_filter}
                ORDER BY importance DESC, last_accessed DESC
                LIMIT 100
            """, (min_importance,)).fetchall()
            
            for row in rows:
                # Calculate relevance score - split key on underscores/hyphens too
                key_words = set(re.split(r'[\s_\-]+', row['key'].lower()))
                try:
                    value = self._decrypt_value(row['value'])
                    value_words = set(re.split(r'[\s_\-/\\]+', str(value).lower()))
                except Exception:
                    value_words = set()
                
                all_words = key_words | value_words
                overlap = len(query_words & all_words)
                
                if overlap > 0:
                    # Score based on overlap, importance, and recency
                    base_score = overlap / max(len(query_words), 1)
                    importance_boost = row['importance'] * 0.3
                    
                    # Recency boost (higher for recent memories)
                    try:
                        last_accessed = datetime.fromisoformat(row['last_accessed'])
                        days_ago = (datetime.now() - last_accessed).days
                        recency_boost = max(0, 1 - (days_ago / 30)) * 0.2
                    except Exception:
                        recency_boost = 0
                    
                    final_score = base_score + importance_boost + recency_boost
                    
                    entry = MemoryEntry(
                        id=row['id'],
                        memory_type=MemoryType(row['memory_type']),
                        key=row['key'],
                        value=self._decrypt_value(row['value']),
                        importance=row['importance'],
                        access_count=row['access_count'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        last_accessed=row['last_accessed'],
                        tags=json.loads(row['tags'])
                    )
                    results.append((final_score, entry))
        
        # Sort by score and return top results
        results.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in results[:limit]]
    
    def delete(self, key: str, memory_type: Optional[MemoryType] = None) -> bool:
        """Delete a memory by key"""
        with self._get_connection() as conn:
            if memory_type:
                result = conn.execute(
                    "DELETE FROM memories WHERE key = ? AND memory_type = ?",
                    (key, memory_type.value)
                )
            else:
                result = conn.execute(
                    "DELETE FROM memories WHERE key = ?",
                    (key,)
                )
            return result.rowcount > 0
    
    # ─────────────────────────────────────────────────────────────
    # User Preferences
    # ─────────────────────────────────────────────────────────────
    
    def get_preferences(self) -> UserPreferences:
        """Get user preferences (cached)"""
        if self._preferences is not None:
            return self._preferences
        
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT preferences FROM user_preferences WHERE id = 1"
            ).fetchone()
            
            if row:
                try:
                    prefs_dict = self._decrypt_value(row['preferences'])
                    self._preferences = UserPreferences.from_dict(prefs_dict)
                except Exception as e:
                    logger.warning(f"Failed to load preferences: {e}")
                    self._preferences = UserPreferences()
            else:
                self._preferences = UserPreferences()
        
        return self._preferences
    
    def save_preferences(self, prefs: UserPreferences):
        """Save user preferences"""
        now = datetime.now().isoformat()
        encrypted = self._encrypt_value(prefs.to_dict())
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_preferences (id, preferences, updated_at)
                VALUES (1, ?, ?)
            """, (encrypted, now))
        
        self._preferences = prefs
    
    def update_preference(self, key: str, value: Any):
        """Update a single preference"""
        prefs = self.get_preferences()
        if hasattr(prefs, key):
            setattr(prefs, key, value)
            self.save_preferences(prefs)
    
    # ─────────────────────────────────────────────────────────────
    # Session Management
    # ─────────────────────────────────────────────────────────────
    
    def start_session(self, session_id: Optional[str] = None) -> str:
        """Start a new session and return session ID"""
        if session_id is None:
            session_id = self._generate_id("session")
        
        now = datetime.now().isoformat()
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO session_history (session_id, start_time, tasks_completed, tasks_failed)
                VALUES (?, ?, 0, 0)
            """, (session_id, now))
        
        return session_id
    
    def end_session(self, session_id: str, summary: str = ""):
        """End a session and store summary"""
        now = datetime.now().isoformat()
        
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE session_history
                SET end_time = ?, summary = ?
                WHERE session_id = ?
            """, (now, summary, session_id))
    
    def get_last_session(self) -> Optional[Dict]:
        """Get the most recent session for continuity"""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM session_history
                ORDER BY start_time DESC
                LIMIT 1
            """).fetchone()
            
            if row:
                return dict(row)
        return None
    
    def update_session_stats(
        self,
        session_id: str,
        tasks_completed: int = 0,
        tasks_failed: int = 0
    ):
        """Update session task statistics"""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE session_history
                SET tasks_completed = tasks_completed + ?,
                    tasks_failed = tasks_failed + ?
                WHERE session_id = ?
            """, (tasks_completed, tasks_failed, session_id))
    
    # ─────────────────────────────────────────────────────────────
    # Error Pattern Learning
    # ─────────────────────────────────────────────────────────────
    
    def learn_error_fix(
        self,
        error_signature: str,
        fix_pattern: str,
        success: bool = True
    ):
        """Learn from error fixes for self-healing"""
        error_id = self._generate_id(error_signature)
        now = datetime.now().isoformat()
        
        with self._get_connection() as conn:
            existing = conn.execute(
                "SELECT * FROM error_patterns WHERE error_signature = ?",
                (error_signature,)
            ).fetchone()
            
            if existing:
                if success:
                    conn.execute("""
                        UPDATE error_patterns
                        SET fix_pattern = ?, success_count = success_count + 1, last_seen = ?
                        WHERE error_signature = ?
                    """, (fix_pattern, now, error_signature))
                else:
                    conn.execute("""
                        UPDATE error_patterns
                        SET fail_count = fail_count + 1, last_seen = ?
                        WHERE error_signature = ?
                    """, (now, error_signature))
            else:
                conn.execute("""
                    INSERT INTO error_patterns
                    (id, error_signature, fix_pattern, success_count, fail_count, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (error_id, error_signature, fix_pattern,
                      1 if success else 0, 0 if success else 1, now))
    
    def find_error_fix(self, error_signature: str) -> Optional[str]:
        """Find a known fix for an error pattern"""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT fix_pattern FROM error_patterns
                WHERE error_signature = ? AND success_count > fail_count
                ORDER BY success_count DESC
                LIMIT 1
            """, (error_signature,)).fetchone()
            
            if row:
                return row['fix_pattern']
        return None
    
    # ─────────────────────────────────────────────────────────────
    # Maintenance
    # ─────────────────────────────────────────────────────────────
    
    def compact(self, days_threshold: int = 30, min_importance: float = 0.3):
        """
        Compact memory by removing old, low-importance entries.
        Keeps high-importance memories and frequently accessed ones.
        """
        cutoff = (datetime.now() - timedelta(days=days_threshold)).isoformat()
        
        with self._get_connection() as conn:
            # Delete old, low-importance, rarely accessed memories
            result = conn.execute("""
                DELETE FROM memories
                WHERE last_accessed < ?
                AND importance < ?
                AND access_count < 3
            """, (cutoff, min_importance))
            
            deleted = result.rowcount
            
            # Also clean old sessions
            session_cutoff = (datetime.now() - timedelta(days=90)).isoformat()
            conn.execute("""
                DELETE FROM session_history
                WHERE end_time < ?
            """, (session_cutoff,))
        
        logger.info(f"Compacted memory: removed {deleted} entries")
        return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        with self._get_connection() as conn:
            stats = {}
            
            # Count by type
            rows = conn.execute("""
                SELECT memory_type, COUNT(*) as count
                FROM memories
                GROUP BY memory_type
            """).fetchall()
            stats['by_type'] = {row['memory_type']: row['count'] for row in rows}
            
            # Total count
            result = conn.execute("SELECT COUNT(*) as count FROM memories").fetchone()
            stats['total_memories'] = result['count'] if result else 0
            
            # Sessions
            result = conn.execute("SELECT COUNT(*) as count FROM session_history").fetchone()
            stats['total_sessions'] = result['count'] if result else 0
            
            # Error patterns
            result = conn.execute("SELECT COUNT(*) as count FROM error_patterns").fetchone()
            stats['error_patterns'] = result['count'] if result else 0
            
            # Database size
            if self.db_path.exists():
                stats['db_size_mb'] = self.db_path.stat().st_size / (1024 * 1024)
        
        return stats


# ═══════════════════════════════════════════════════════════════
# Singleton & Helper Functions
# ═══════════════════════════════════════════════════════════════

_persistent_memory: Optional[PersistentMemory] = None


def get_persistent_memory() -> PersistentMemory:
    """Get or create the global persistent memory instance"""
    global _persistent_memory
    if _persistent_memory is None:
        _persistent_memory = PersistentMemory()
    return _persistent_memory
