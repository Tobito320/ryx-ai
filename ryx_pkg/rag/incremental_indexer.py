"""
Ryx AI - Incremental Indexer

Efficiently index repositories by only processing changed files.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
from datetime import datetime
import hashlib
import json
import sqlite3
import logging
import os

from .code_embeddings import CodeEmbeddings, EmbeddingConfig

logger = logging.getLogger(__name__)


@dataclass
class IndexStatus:
    """Status of the index"""
    total_files: int = 0
    indexed_files: int = 0
    pending_files: int = 0
    failed_files: int = 0
    last_update: Optional[datetime] = None
    is_stale: bool = False


@dataclass
class FileStatus:
    """Status of a single file in the index"""
    path: str
    content_hash: str
    last_modified: float  # mtime
    indexed_at: datetime
    chunk_count: int
    is_current: bool = True


class IncrementalIndexer:
    """
    Incremental repository indexer.
    
    Features:
    - Only re-index changed files
    - Track file modifications
    - Detect deleted files
    - Parallel indexing
    - Progress reporting
    
    Usage:
    ```python
    indexer = IncrementalIndexer("/path/to/repo")
    
    # Initial index
    status = indexer.index()
    
    # Subsequent updates (only changed files)
    status = indexer.update()
    ```
    """
    
    def __init__(
        self,
        repo_path: Path,
        embeddings: Optional[CodeEmbeddings] = None,
        config: Optional[EmbeddingConfig] = None,
        ignore_patterns: Optional[List[str]] = None,
        extensions: Optional[List[str]] = None
    ):
        self.repo_path = Path(repo_path).resolve()
        self.embeddings = embeddings or CodeEmbeddings(config)
        
        self.ignore_patterns = ignore_patterns or [
            '__pycache__', 'node_modules', '.git',
            'venv', '.venv', 'dist', 'build',
            '.next', '.nuxt', 'target', '.tox',
            '*.pyc', '*.pyo', '*.so', '*.dll'
        ]
        
        self.extensions = extensions or [
            '.py', '.js', '.ts', '.tsx', '.jsx',
            '.go', '.rs', '.java', '.cpp', '.c',
            '.rb', '.php', '.sh', '.md'
        ]
        
        # Setup index database
        from core.paths import get_data_dir
        self.index_db = get_data_dir() / "file_index.db"
        self._init_db()
    
    def _init_db(self):
        """Initialize the index database"""
        conn = sqlite3.connect(self.index_db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_index (
                path TEXT PRIMARY KEY,
                repo_path TEXT,
                content_hash TEXT,
                last_modified REAL,
                indexed_at TIMESTAMP,
                chunk_count INTEGER,
                status TEXT DEFAULT 'indexed'
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_repo_path 
            ON file_index(repo_path)
        """)
        conn.commit()
        conn.close()
    
    def index(
        self,
        force: bool = False,
        on_progress: Optional[callable] = None
    ) -> IndexStatus:
        """
        Index the repository.
        
        Args:
            force: Re-index all files even if unchanged
            on_progress: Callback for progress updates (current, total, file)
        """
        files = self._scan_files()
        
        total = len(files)
        indexed = 0
        failed = 0
        
        for i, file_path in enumerate(files):
            if on_progress:
                on_progress(i + 1, total, str(file_path))
            
            try:
                if force or self._needs_indexing(file_path):
                    self._index_file(file_path)
                    indexed += 1
            except Exception as e:
                logger.warning(f"Failed to index {file_path}: {e}")
                failed += 1
        
        # Clean up deleted files
        self._cleanup_deleted()
        
        return self._get_status()
    
    def update(
        self,
        on_progress: Optional[callable] = None
    ) -> IndexStatus:
        """
        Update the index with changed files only.
        """
        return self.index(force=False, on_progress=on_progress)
    
    def _scan_files(self) -> List[Path]:
        """Scan repository for indexable files"""
        files = []
        
        for ext in self.extensions:
            pattern = f"**/*{ext}"
            for file_path in self.repo_path.glob(pattern):
                if self._should_ignore(file_path):
                    continue
                files.append(file_path)
        
        return files
    
    def _should_ignore(self, path: Path) -> bool:
        """Check if file should be ignored"""
        path_str = str(path)
        
        for pattern in self.ignore_patterns:
            if pattern.startswith('*'):
                # Wildcard pattern
                if path_str.endswith(pattern[1:]):
                    return True
            else:
                # Directory pattern
                if pattern in path_str:
                    return True
        
        return False
    
    def _needs_indexing(self, file_path: Path) -> bool:
        """Check if file needs to be (re)indexed"""
        conn = sqlite3.connect(self.index_db)
        cursor = conn.execute("""
            SELECT content_hash, last_modified 
            FROM file_index 
            WHERE path = ?
        """, (str(file_path),))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return True
        
        # Check if file has changed
        current_mtime = file_path.stat().st_mtime
        if current_mtime > row[1]:
            # File modified, check hash
            current_hash = self._hash_file(file_path)
            return current_hash != row[0]
        
        return False
    
    def _index_file(self, file_path: Path):
        """Index a single file"""
        # Get file info
        content_hash = self._hash_file(file_path)
        mtime = file_path.stat().st_mtime
        
        # Embed the file
        chunks = self.embeddings.embed_file(file_path, force=True)
        
        # Update index
        conn = sqlite3.connect(self.index_db)
        conn.execute("""
            INSERT OR REPLACE INTO file_index 
            (path, repo_path, content_hash, last_modified, indexed_at, chunk_count, status)
            VALUES (?, ?, ?, ?, ?, ?, 'indexed')
        """, (
            str(file_path),
            str(self.repo_path),
            content_hash,
            mtime,
            datetime.now().isoformat(),
            len(chunks)
        ))
        conn.commit()
        conn.close()
        
        logger.debug(f"Indexed {file_path}: {len(chunks)} chunks")
    
    def _cleanup_deleted(self):
        """Remove index entries for deleted files"""
        conn = sqlite3.connect(self.index_db)
        
        cursor = conn.execute("""
            SELECT path FROM file_index WHERE repo_path = ?
        """, (str(self.repo_path),))
        
        for row in cursor.fetchall():
            path = Path(row[0])
            if not path.exists():
                # File deleted
                conn.execute("DELETE FROM file_index WHERE path = ?", (row[0],))
                self.embeddings.clear_file(path)
                logger.debug(f"Removed deleted file from index: {path}")
        
        conn.commit()
        conn.close()
    
    def _hash_file(self, file_path: Path) -> str:
        """Calculate hash of file content"""
        hasher = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()[:16]
        except Exception:
            return ""
    
    def _get_status(self) -> IndexStatus:
        """Get current index status"""
        conn = sqlite3.connect(self.index_db)
        
        cursor = conn.execute("""
            SELECT COUNT(*), MAX(indexed_at)
            FROM file_index 
            WHERE repo_path = ?
        """, (str(self.repo_path),))
        
        row = cursor.fetchone()
        conn.close()
        
        indexed = row[0] if row else 0
        last_update = (
            datetime.fromisoformat(row[1]) 
            if row and row[1] else None
        )
        
        # Count pending
        all_files = self._scan_files()
        pending = sum(1 for f in all_files if self._needs_indexing(f))
        
        return IndexStatus(
            total_files=len(all_files),
            indexed_files=indexed,
            pending_files=pending,
            last_update=last_update,
            is_stale=pending > 0
        )
    
    def get_file_status(self, file_path: Path) -> Optional[FileStatus]:
        """Get status of a specific file"""
        conn = sqlite3.connect(self.index_db)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("""
            SELECT * FROM file_index WHERE path = ?
        """, (str(file_path),))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        is_current = not self._needs_indexing(file_path)
        
        return FileStatus(
            path=row["path"],
            content_hash=row["content_hash"],
            last_modified=row["last_modified"],
            indexed_at=datetime.fromisoformat(row["indexed_at"]),
            chunk_count=row["chunk_count"],
            is_current=is_current
        )
    
    def get_changed_files(self) -> List[Path]:
        """Get list of files that need re-indexing"""
        return [f for f in self._scan_files() if self._needs_indexing(f)]
    
    def clear_index(self):
        """Clear all index data for this repo"""
        conn = sqlite3.connect(self.index_db)
        conn.execute(
            "DELETE FROM file_index WHERE repo_path = ?",
            (str(self.repo_path),)
        )
        conn.commit()
        conn.close()
        
        # Also clear embeddings
        self.embeddings.clear_all()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get indexer statistics"""
        status = self._get_status()
        
        conn = sqlite3.connect(self.index_db)
        
        cursor = conn.execute("""
            SELECT 
                SUM(chunk_count) as total_chunks,
                COUNT(DISTINCT path) as files
            FROM file_index 
            WHERE repo_path = ?
        """, (str(self.repo_path),))
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            "repo_path": str(self.repo_path),
            "status": {
                "total_files": status.total_files,
                "indexed_files": status.indexed_files,
                "pending_files": status.pending_files,
                "is_stale": status.is_stale
            },
            "total_chunks": row[0] if row else 0,
            "last_update": (
                status.last_update.isoformat() 
                if status.last_update else None
            ),
            "embedding_stats": self.embeddings.get_stats()
        }
