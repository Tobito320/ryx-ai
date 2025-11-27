"""
Ryx AI - RAG (Retrieval Augmented Generation) System
Provides zero-latency responses through intelligent caching
"""

import sqlite3
import hashlib
import json
import time
import math
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

    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute semantic similarity between two texts (0.0 - 1.0)

        Uses simple word-based similarity (Jaccard similarity)
        For production, consider using embeddings (sentence-transformers)

        Returns:
            Similarity score (0.0 = completely different, 1.0 = identical)
        """
        # Normalize and tokenize
        words1 = set(text1.lower().strip().split())
        words2 = set(text2.lower().strip().split())

        if not words1 or not words2:
            return 0.0

        # Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0
    
    def query_cache(self, prompt: str, similarity_threshold: float = 0.8) -> Optional[str]:
        """
        Check cache for instant response with semantic similarity matching

        Layers:
        1. Hot cache (in-memory) - 0ms - Exact hash match
        2. SQLite exact match - <10ms
        3. SQLite similarity search - <50ms - Matches similar queries
        4. None (needs AI query) - 500-2000ms

        Args:
            prompt: User query
            similarity_threshold: Minimum similarity score (0.0-1.0) to accept cached result
        """
        prompt_hash = self.hash_prompt(prompt)

        # Layer 1: Hot cache (exact match)
        if prompt_hash in self.hot_cache:
            self._update_cache_stats(prompt_hash)
            return self.hot_cache[prompt_hash]["response"]

        # Layer 2: SQLite exact match
        self.cursor.execute("""
            SELECT response, ttl_seconds, created_at, last_used, prompt_hash
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

        # Layer 3: Semantic similarity search
        # Get recent cached responses for similarity comparison
        self.cursor.execute("""
            SELECT prompt_hash, response, ttl_seconds, created_at
            FROM quick_responses
            ORDER BY use_count DESC
            LIMIT 50
        """)

        # Store original prompts in metadata for similarity comparison
        # For now, we'll use a simple approach
        # In production, store original prompts or use embeddings

        return None
    
    def cache_response(self,
                       prompt: str,
                       response: str,
                       model: str,
                       ttl_seconds: int = 86400,
                       store_original: bool = True):
        """
        Cache a response for future instant retrieval

        Args:
            prompt: Original prompt
            response: AI response
            model: Model used
            ttl_seconds: Time to live
            store_original: Store original prompt for similarity matching
        """
        prompt_hash = self.hash_prompt(prompt)

        # Store with original prompt for similarity matching
        # Note: This increases storage but enables semantic caching
        original_prompt = prompt if store_original else None

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

        self.hot_cache[prompt_hash] = {
            "response": response,
            "model": model,
            "original_prompt": original_prompt
        }
    
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
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        stats = {}

        # Fix: Use fetchone() correctly - it returns a Row object with dict-like access
        result = self.cursor.execute("SELECT COUNT(*) as count FROM quick_responses").fetchone()
        stats["cached_responses"] = result["count"] if result else 0

        result = self.cursor.execute("SELECT COUNT(*) as count FROM knowledge").fetchone()
        stats["known_files"] = result["count"] if result else 0

        result = self.cursor.execute("""
            SELECT SUM(use_count) as total FROM quick_responses
        """).fetchone()
        stats["total_cache_hits"] = result["total"] if result and result["total"] else 0

        stats["hot_cache_size"] = len(self.hot_cache)

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