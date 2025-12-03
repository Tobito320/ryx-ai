"""
Ryx AI - Code Embeddings

Generate embeddings for code chunks using local models (Ollama).
Supports incremental updates and caching.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import hashlib
import json
import sqlite3
import numpy as np
import logging
import requests

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingConfig:
    """Configuration for the embedding system"""
    # Model settings
    model: str = "nomic-embed-text"  # or "mxbai-embed-large"
    ollama_url: str = "http://localhost:11434"
    
    # Chunking settings
    chunk_size: int = 512  # tokens/chars per chunk
    chunk_overlap: int = 50
    
    # Cache settings
    cache_dir: Optional[Path] = None
    max_cache_size_mb: int = 500
    
    # Dimensions
    embedding_dim: int = 768  # Depends on model


@dataclass
class CodeChunk:
    """A chunk of code with metadata"""
    id: str
    content: str
    file_path: str
    start_line: int
    end_line: int
    language: str
    chunk_type: str  # function, class, module, block
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class EmbeddedChunk:
    """A code chunk with its embedding"""
    chunk: CodeChunk
    embedding: np.ndarray
    hash: str  # Content hash for cache invalidation


class CodeEmbeddings:
    """
    Generate and manage embeddings for code.
    
    Features:
    - Chunking strategies for different code structures
    - Local embedding via Ollama
    - SQLite caching for fast retrieval
    - Incremental updates (only re-embed changed files)
    
    Usage:
    ```python
    embeddings = CodeEmbeddings()
    
    # Embed a file
    chunks = embeddings.embed_file("path/to/file.py")
    
    # Search for similar code
    results = embeddings.search("user authentication", top_k=5)
    ```
    """
    
    def __init__(
        self,
        config: Optional[EmbeddingConfig] = None,
        db_path: Optional[Path] = None
    ):
        self.config = config or EmbeddingConfig()
        
        # Setup cache database
        if db_path:
            self.db_path = db_path
        elif self.config.cache_dir:
            self.db_path = self.config.cache_dir / "embeddings.db"
        else:
            from core.paths import get_data_dir
            self.db_path = get_data_dir() / "code_embeddings.db"
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
        # Check if embedding model is available
        self._model_available = self._check_model()
    
    def _init_db(self):
        """Initialize SQLite database for caching"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                chunk_id TEXT PRIMARY KEY,
                content_hash TEXT,
                file_path TEXT,
                start_line INTEGER,
                end_line INTEGER,
                language TEXT,
                chunk_type TEXT,
                embedding BLOB,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_path 
            ON embeddings(file_path)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_content_hash 
            ON embeddings(content_hash)
        """)
        conn.commit()
        conn.close()
    
    def _check_model(self) -> bool:
        """Check if embedding model is available"""
        try:
            response = requests.get(
                f"{self.config.ollama_url}/api/tags",
                timeout=2
            )
            if response.status_code == 200:
                models = [m["name"] for m in response.json().get("models", [])]
                return self.config.model in models
        except Exception:
            pass
        return False
    
    def embed_text(self, text: str) -> Optional[np.ndarray]:
        """
        Generate embedding for text using Ollama.
        
        Returns:
            numpy array of embedding or None if failed
        """
        if not self._model_available:
            logger.warning(f"Embedding model {self.config.model} not available")
            return None
        
        try:
            response = requests.post(
                f"{self.config.ollama_url}/api/embeddings",
                json={
                    "model": self.config.model,
                    "prompt": text
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                embedding = data.get("embedding")
                if embedding:
                    return np.array(embedding, dtype=np.float32)
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
        
        return None
    
    def embed_chunks(
        self, 
        chunks: List[CodeChunk],
        use_cache: bool = True
    ) -> List[EmbeddedChunk]:
        """
        Generate embeddings for multiple code chunks.
        
        Uses caching to avoid re-embedding unchanged content.
        """
        results = []
        
        for chunk in chunks:
            content_hash = self._hash_content(chunk.content)
            
            # Check cache
            if use_cache:
                cached = self._get_cached(chunk.id, content_hash)
                if cached:
                    results.append(cached)
                    continue
            
            # Generate embedding
            embedding = self.embed_text(chunk.content)
            
            if embedding is not None:
                embedded = EmbeddedChunk(
                    chunk=chunk,
                    embedding=embedding,
                    hash=content_hash
                )
                results.append(embedded)
                
                # Cache it
                if use_cache:
                    self._cache_embedding(embedded)
        
        return results
    
    def embed_file(
        self, 
        file_path: Path,
        force: bool = False
    ) -> List[EmbeddedChunk]:
        """
        Embed all chunks from a file.
        
        Args:
            file_path: Path to the file
            force: Re-embed even if cached
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return []
        
        # Check if file needs re-embedding
        if not force and not self._file_changed(file_path):
            return self._get_file_embeddings(file_path)
        
        # Read and chunk the file
        content = file_path.read_text(errors='replace')
        language = self._detect_language(file_path)
        chunks = self._chunk_code(content, str(file_path), language)
        
        # Embed chunks
        return self.embed_chunks(chunks)
    
    def _chunk_code(
        self,
        content: str,
        file_path: str,
        language: str
    ) -> List[CodeChunk]:
        """
        Split code into chunks for embedding.
        
        Strategy:
        1. Try to split on logical boundaries (functions, classes)
        2. Fall back to line-based chunking
        """
        chunks = []
        lines = content.split('\n')
        
        # Simple line-based chunking for now
        # TODO: Use tree-sitter for semantic chunking
        chunk_lines = self.config.chunk_size // 80  # ~80 chars per line
        overlap_lines = self.config.chunk_overlap // 80
        
        i = 0
        chunk_idx = 0
        
        while i < len(lines):
            end_idx = min(i + chunk_lines, len(lines))
            chunk_content = '\n'.join(lines[i:end_idx])
            
            if chunk_content.strip():  # Skip empty chunks
                chunk_id = f"{file_path}:{i}:{end_idx}"
                chunks.append(CodeChunk(
                    id=chunk_id,
                    content=chunk_content,
                    file_path=file_path,
                    start_line=i + 1,
                    end_line=end_idx,
                    language=language,
                    chunk_type="block"
                ))
                chunk_idx += 1
            
            i = end_idx - overlap_lines
            if i <= chunks[-1].start_line - 1 if chunks else 0:
                i = end_idx  # Avoid infinite loop
        
        return chunks
    
    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension"""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.rb': 'ruby',
            '.php': 'php',
            '.sh': 'bash',
            '.md': 'markdown',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
        }
        return ext_map.get(file_path.suffix.lower(), 'unknown')
    
    def _hash_content(self, content: str) -> str:
        """Create hash of content for cache invalidation"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _get_cached(
        self, 
        chunk_id: str, 
        content_hash: str
    ) -> Optional[EmbeddedChunk]:
        """Get cached embedding if still valid"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("""
            SELECT * FROM embeddings 
            WHERE chunk_id = ? AND content_hash = ?
        """, (chunk_id, content_hash))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            embedding = np.frombuffer(row["embedding"], dtype=np.float32)
            chunk = CodeChunk(
                id=row["chunk_id"],
                content="",  # Not stored to save space
                file_path=row["file_path"],
                start_line=row["start_line"],
                end_line=row["end_line"],
                language=row["language"],
                chunk_type=row["chunk_type"],
                metadata=json.loads(row["metadata"] or "{}")
            )
            return EmbeddedChunk(
                chunk=chunk,
                embedding=embedding,
                hash=row["content_hash"]
            )
        
        return None
    
    def _cache_embedding(self, embedded: EmbeddedChunk):
        """Cache an embedding"""
        conn = sqlite3.connect(self.db_path)
        
        conn.execute("""
            INSERT OR REPLACE INTO embeddings 
            (chunk_id, content_hash, file_path, start_line, end_line, 
             language, chunk_type, embedding, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            embedded.chunk.id,
            embedded.hash,
            embedded.chunk.file_path,
            embedded.chunk.start_line,
            embedded.chunk.end_line,
            embedded.chunk.language,
            embedded.chunk.chunk_type,
            embedded.embedding.tobytes(),
            json.dumps(embedded.chunk.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def _file_changed(self, file_path: Path) -> bool:
        """Check if file has changed since last embedding"""
        conn = sqlite3.connect(self.db_path)
        
        cursor = conn.execute("""
            SELECT updated_at FROM embeddings 
            WHERE file_path = ? 
            ORDER BY updated_at DESC LIMIT 1
        """, (str(file_path),))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return True
        
        # Compare file mtime with last update
        try:
            file_mtime = file_path.stat().st_mtime
            from datetime import datetime
            db_time = datetime.fromisoformat(row[0]).timestamp()
            return file_mtime > db_time
        except:
            return True
    
    def _get_file_embeddings(self, file_path: Path) -> List[EmbeddedChunk]:
        """Get all embeddings for a file from cache"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("""
            SELECT * FROM embeddings WHERE file_path = ?
        """, (str(file_path),))
        
        results = []
        for row in cursor.fetchall():
            embedding = np.frombuffer(row["embedding"], dtype=np.float32)
            chunk = CodeChunk(
                id=row["chunk_id"],
                content="",
                file_path=row["file_path"],
                start_line=row["start_line"],
                end_line=row["end_line"],
                language=row["language"],
                chunk_type=row["chunk_type"],
                metadata=json.loads(row["metadata"] or "{}")
            )
            results.append(EmbeddedChunk(
                chunk=chunk,
                embedding=embedding,
                hash=row["content_hash"]
            ))
        
        conn.close()
        return results
    
    def clear_file(self, file_path: Path):
        """Remove embeddings for a file"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "DELETE FROM embeddings WHERE file_path = ?",
            (str(file_path),)
        )
        conn.commit()
        conn.close()
    
    def clear_all(self):
        """Clear all cached embeddings"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM embeddings")
        conn.commit()
        conn.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get embedding cache statistics"""
        conn = sqlite3.connect(self.db_path)
        
        cursor = conn.execute("SELECT COUNT(*) FROM embeddings")
        total_chunks = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(DISTINCT file_path) FROM embeddings")
        total_files = cursor.fetchone()[0]
        
        cursor = conn.execute("""
            SELECT language, COUNT(*) 
            FROM embeddings 
            GROUP BY language
        """)
        by_language = dict(cursor.fetchall())
        
        conn.close()
        
        # Get cache size
        cache_size_mb = self.db_path.stat().st_size / (1024 * 1024)
        
        return {
            "total_chunks": total_chunks,
            "total_files": total_files,
            "by_language": by_language,
            "cache_size_mb": round(cache_size_mb, 2),
            "model": self.config.model,
            "model_available": self._model_available
        }
