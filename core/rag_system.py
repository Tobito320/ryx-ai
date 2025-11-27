"""
Ryx AI - RAG (Retrieval Augmented Generation) System
Provides zero-latency responses through intelligent caching
"""

import sqlite3
import hashlib
import json
import time
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta

class RAGSystem:
    def __init__(self):
        self.db_path = Path.home() / "ryx-ai" / "data" / "rag_knowledge.db"
        self.hot_cache = {}  # In-memory cache for ultra-fast access
        self.max_hot_cache = 100
        
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        self._load_hot_cache()
    
    def _load_hot_cache(self):
        """Load frequently accessed items into memory"""
        self.cursor.execute("""
            SELECT prompt_hash, response, model_used
            FROM quick_responses
            ORDER BY use_count DESC
            LIMIT ?
        """, (self.max_hot_cache,))
        
        for row in self.cursor.fetchall():
            self.hot_cache[row["prompt_hash"]] = {
                "response": row["response"],
                "model": row["model_used"]
            }
    
    def hash_prompt(self, prompt: str) -> str:
        """Create consistent hash for prompt"""
        return hashlib.sha256(prompt.lower().strip().encode()).hexdigest()[:16]
    
    def query_cache(self, prompt: str) -> Optional[str]:
        """
        Check cache for instant response
        
        Layers:
        1. Hot cache (in-memory) - 0ms
        2. SQLite cache - <10ms
        3. None (needs AI query) - 500-2000ms
        """
        prompt_hash = self.hash_prompt(prompt)
        
        # Layer 1: Hot cache
        if prompt_hash in self.hot_cache:
            self._update_cache_stats(prompt_hash)
            return self.hot_cache[prompt_hash]["response"]
        
        # Layer 2: SQLite
        self.cursor.execute("""
            SELECT response, ttl_seconds, created_at, last_used
            FROM quick_responses
            WHERE prompt_hash = ?
        """, (prompt_hash,))
        
        row = self.cursor.fetchone()
        if row:
            # Check if still valid
            created = datetime.fromisoformat(row["created_at"])
            ttl = timedelta(seconds=row["ttl_seconds"])
            
            if datetime.now() - created < ttl:
                response = row["response"]
                self._update_cache_stats(prompt_hash)
                
                # Promote to hot cache
                self.hot_cache[prompt_hash] = {"response": response}
                return response
        
        return None
    
    def cache_response(self, 
                       prompt: str, 
                       response: str,
                       model: str,
                       ttl_seconds: int = 86400):
        """Cache a response for future instant retrieval"""
        prompt_hash = self.hash_prompt(prompt)
        
        self.cursor.execute("""
            INSERT OR REPLACE INTO quick_responses
            (prompt_hash, response, model_used, ttl_seconds, created_at, last_used, use_count)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (prompt_hash, response, model, ttl_seconds, 
              datetime.now().isoformat(), datetime.now().isoformat()))
        
        self.conn.commit()
        
        # Add to hot cache
        if len(self.hot_cache) >= self.max_hot_cache:
            # Remove least recently used
            self.hot_cache.pop(list(self.hot_cache.keys())[0])
        
        self.hot_cache[prompt_hash] = {"response": response, "model": model}
    
    def _update_cache_stats(self, prompt_hash: str):
        """Update cache hit statistics"""
        self.cursor.execute("""
            UPDATE quick_responses
            SET use_count = use_count + 1,
                last_used = ?
            WHERE prompt_hash = ?
        """, (datetime.now().isoformat(), prompt_hash))
        self.conn.commit()
    
    def learn_file_location(self,
                           query: str,
                           file_type: str,
                           file_path: str,
                           confidence: float = 1.0):
        """
        Learn file location for instant future retrieval
        
        Example:
            query: "hyprland config"
            file_type: "config"
            file_path: "~/.config/hyprland/hyprland.conf"
        """
        query_hash = self.hash_prompt(query)
        
        # Read first few lines as preview
        try:
            full_path = Path(file_path).expanduser()
            if full_path.exists():
                with open(full_path, 'r') as f:
                    preview = ''.join(f.readlines()[:5])
            else:
                preview = ""
        except:
            preview = ""
        
        self.cursor.execute("""
            INSERT OR REPLACE INTO knowledge
            (query_hash, file_type, file_path, content_preview, 
             last_accessed, access_count, confidence)
            VALUES (?, ?, ?, ?, ?, 
                    COALESCE((SELECT access_count FROM knowledge WHERE query_hash = ?), 0) + 1,
                    ?)
        """, (query_hash, file_type, str(file_path), preview,
              datetime.now().isoformat(), query_hash, confidence))
        
        self.conn.commit()
    
    def recall_file_location(self, query: str) -> Optional[Dict]:
        """
        Instantly recall file location from previous learning
        
        Returns:
            {
                "file_path": str,
                "file_type": str,
                "confidence": float,
                "preview": str
            }
        """
        query_hash = self.hash_prompt(query)
        
        self.cursor.execute("""
            SELECT file_path, file_type, content_preview, confidence, access_count
            FROM knowledge
            WHERE query_hash = ?
            ORDER BY confidence DESC, access_count DESC
            LIMIT 1
        """, (query_hash,))
        
        row = self.cursor.fetchone()
        if row:
            # Update access stats
            self.cursor.execute("""
                UPDATE knowledge
                SET access_count = access_count + 1,
                    last_accessed = ?
                WHERE query_hash = ?
            """, (datetime.now().isoformat(), query_hash))
            self.conn.commit()
            
            return {
                "file_path": row["file_path"],
                "file_type": row["file_type"],
                "confidence": row["confidence"],
                "preview": row["content_preview"]
            }
        
        return None
    
    def fuzzy_recall(self, query: str) -> List[Dict]:
        """
        Fuzzy search for similar queries
        
        Useful when exact match isn't found
        """
        # Extract keywords
        keywords = query.lower().split()
        
        results = []
        
        # Search in cached responses
        self.cursor.execute("""
            SELECT prompt_hash, response, model_used
            FROM quick_responses
            ORDER BY use_count DESC
            LIMIT 50
        """)
        
        for row in self.cursor.fetchall():
            # Simple similarity check
            # In production: use proper fuzzy matching (e.g., fuzzywuzzy)
            pass
        
        # Search in knowledge base
        for keyword in keywords:
            self.cursor.execute("""
                SELECT file_path, file_type, confidence
                FROM knowledge
                WHERE file_type LIKE ? OR file_path LIKE ?
                ORDER BY confidence DESC, access_count DESC
                LIMIT 5
            """, (f"%{keyword}%", f"%{keyword}%"))
            
            results.extend([
                {
                    "file_path": row["file_path"],
                    "file_type": row["file_type"],
                    "confidence": row["confidence"]
                }
                for row in self.cursor.fetchall()
            ])
        
        return results
    
    def get_context(self, query: str) -> str:
        """
        Build context string for AI query
        
        Includes:
        - Known file locations
        - Related cached responses
        - System information
        """
        context_parts = []
        
        # Check for known file locations
        file_info = self.recall_file_location(query)
        if file_info:
            context_parts.append(
                f"Known location: {file_info['file_type']} at {file_info['file_path']}"
            )
        
        # Add system info if relevant
        if any(kw in query.lower() for kw in ["config", "hyprland", "waybar", "kitty"]):
            context_parts.append("Common config locations: ~/.config/")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def cleanup_old_cache(self, days: int = 30):
        """Remove old cache entries"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        self.cursor.execute("""
            DELETE FROM quick_responses
            WHERE created_at < ? AND use_count < 5
        """, (cutoff,))
        
        deleted = self.cursor.rowcount
        self.conn.commit()
        
        return deleted
    
<<<<<<< HEAD
    def semantic_similarity(self, query1: str, query2: str) -> float:
        """
        Calculate semantic similarity between two queries
        Uses simple word overlap for now (can be enhanced with embeddings)

        Returns: 0.0-1.0 similarity score
        """
        words1 = set(query1.lower().split())
        words2 = set(query2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        # Jaccard similarity
        return len(intersection) / len(union) if union else 0.0

    def query_cache_semantic(self, prompt: str, threshold: float = 0.7) -> Optional[str]:
        """
        Check cache using semantic similarity

        Args:
            prompt: Query to search for
            threshold: Minimum similarity score (0.0-1.0)

        Returns: Cached response if similar query found
        """
        # First try exact match
        exact_match = self.query_cache(prompt)
        if exact_match:
            return exact_match

        # Try semantic match
        prompt_hash = self.hash_prompt(prompt)

        # Get recent queries
        self.cursor.execute("""
            SELECT prompt_hash, response, model_used
            FROM quick_responses
            WHERE last_used > datetime('now', '-7 days')
            ORDER BY use_count DESC
            LIMIT 100
        """)

        best_match = None
        best_similarity = 0.0

        # Note: In production, store original prompts for better matching
        # For now, this is a simplified version

        return None  # Semantic matching needs original prompts stored

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        stats = {}

        self.cursor.execute("SELECT COUNT(*) as count FROM quick_responses")
        row = self.cursor.fetchone()
        stats["cached_responses"] = row["count"] if row else 0

        self.cursor.execute("SELECT COUNT(*) as count FROM knowledge")
        row = self.cursor.fetchone()
        stats["known_files"] = row["count"] if row else 0

        self.cursor.execute("""
            SELECT SUM(use_count) as total FROM quick_responses
        """)
        row = self.cursor.fetchone()
        stats["total_cache_hits"] = row["total"] if row and row["total"] else 0

        stats["hot_cache_size"] = len(self.hot_cache)

=======
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        stats = {}
        
        self.cursor.execute("SELECT COUNT(*) as count FROM quick_responses")
        stats["cached_responses"] = self.cursor.fetchone()["count"]
        
        self.cursor.execute("SELECT COUNT(*) as count FROM knowledge")
        stats["known_files"] = self.cursor.fetchone()["count"]
        
        self.cursor.execute("""
            SELECT SUM(use_count) as total FROM quick_responses
        """)
        stats["total_cache_hits"] = self.cursor.fetchone()["total"] or 0
        
        stats["hot_cache_size"] = len(self.hot_cache)
        
>>>>>>> 9776c4f33e86c9cd995868ae5ae5bf0c8cd7a6b8
        return stats
    
    def close(self):
        """Close database connection"""
        self.conn.close()


# ===================================
# File Finder - Smart file location
# ===================================

class FileFinder:
    """Find files intelligently with learning"""
    
    def __init__(self, rag: RAGSystem):
        self.rag = rag
        self.common_locations = {
            "hyprland": ["~/.config/hyprland", "~/.config/hypr"],
            "waybar": ["~/.config/waybar"],
            "kitty": ["~/.config/kitty"],
            "nvim": ["~/.config/nvim"],
            "bash": ["~/.bashrc", "~/.bash_profile"],
            "zsh": ["~/.zshrc", "~/.zprofile"],
        }
    
    def find(self, query: str) -> Optional[Tuple[str, float]]:
        """
        Find file matching query
        
        Returns: (file_path, confidence)
        """
        # First check RAG
        learned = self.rag.recall_file_location(query)
        if learned and learned["confidence"] > 0.8:
            path = Path(learned["file_path"]).expanduser()
            if path.exists():
                return (str(path), learned["confidence"])
        
        # Extract file type from query
        query_lower = query.lower()
        
        for file_type, locations in self.common_locations.items():
            if file_type in query_lower:
                # Search in known locations
                for loc in locations:
                    path = Path(loc).expanduser()
                    if path.exists():
                        if path.is_dir():
                            # Find config file in directory
                            for ext in [".conf", ".yaml", ".yml", ".json", ".toml"]:
                                for file in path.glob(f"*{ext}"):
                                    # Learn for next time
                                    self.rag.learn_file_location(
                                        query, file_type, str(file), confidence=0.9
                                    )
                                    return (str(file), 0.9)
                        else:
                            # Direct file
                            self.rag.learn_file_location(
                                query, file_type, str(path), confidence=1.0
                            )
                            return (str(path), 1.0)
        
        return None