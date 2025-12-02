"""
Ryx AI - Embedding System

Uses nomic-embed-text for semantic search across codebase.
This enables intelligent file discovery without keyword matching.

Features:
- Embed code files for semantic search
- Find relevant files by natural language query
- Cache embeddings for speed
- Incremental updates (only changed files)
"""

import os
import json
import hashlib
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import numpy as np

from core.paths import get_data_dir


@dataclass
class FileEmbedding:
    """Embedding for a single file"""
    path: str
    content_hash: str
    embedding: List[float]
    summary: str = ""


class EmbeddingStore:
    """
    Stores and retrieves file embeddings for semantic search.
    Uses nomic-embed-text via Ollama.
    """
    
    MODEL = "nomic-embed-text"
    CACHE_VERSION = 1
    
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path).resolve()
        self.cache_dir = get_data_dir() / "embeddings"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_file = self.cache_dir / f"{self._project_hash()}.json"
        self.embeddings: Dict[str, FileEmbedding] = {}
        
        self._load_cache()
    
    def _project_hash(self) -> str:
        """Get unique hash for this project"""
        return hashlib.md5(str(self.project_path).encode()).hexdigest()[:12]
    
    def _load_cache(self):
        """Load embeddings from cache"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                
                if data.get('version') == self.CACHE_VERSION:
                    for path, emb_data in data.get('embeddings', {}).items():
                        self.embeddings[path] = FileEmbedding(
                            path=path,
                            content_hash=emb_data['hash'],
                            embedding=emb_data['embedding'],
                            summary=emb_data.get('summary', '')
                        )
            except Exception:
                pass
    
    def _save_cache(self):
        """Save embeddings to cache"""
        data = {
            'version': self.CACHE_VERSION,
            'project': str(self.project_path),
            'embeddings': {}
        }
        
        for path, emb in self.embeddings.items():
            data['embeddings'][path] = {
                'hash': emb.content_hash,
                'embedding': emb.embedding,
                'summary': emb.summary
            }
        
        with open(self.cache_file, 'w') as f:
            json.dump(data, f)
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding vector from Ollama"""
        try:
            import requests
            
            response = requests.post(
                "http://localhost:11434/api/embeddings",
                json={
                    "model": self.MODEL,
                    "prompt": text[:8000]  # Limit size
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get('embedding')
        except Exception:
            pass
        
        return None
    
    def _file_hash(self, path: Path) -> str:
        """Get hash of file contents"""
        try:
            content = path.read_text()
            return hashlib.md5(content.encode()).hexdigest()
        except Exception:
            return ""
    
    def _should_embed(self, path: Path) -> bool:
        """Check if file should be embedded"""
        # Skip hidden, binary, large files
        if path.name.startswith('.'):
            return False
        
        # Only code/text files
        extensions = {
            '.py', '.js', '.ts', '.tsx', '.jsx',
            '.rs', '.go', '.java', '.c', '.cpp', '.h',
            '.sh', '.bash', '.zsh',
            '.json', '.yaml', '.yml', '.toml',
            '.md', '.txt', '.conf', '.cfg'
        }
        
        if path.suffix.lower() not in extensions:
            return False
        
        # Skip large files (>100KB)
        try:
            if path.stat().st_size > 100_000:
                return False
        except Exception:
            return False
        
        return True
    
    def embed_file(self, path: Path) -> Optional[FileEmbedding]:
        """Embed a single file"""
        if not path.exists() or not self._should_embed(path):
            return None
        
        rel_path = str(path.relative_to(self.project_path))
        content_hash = self._file_hash(path)
        
        # Check if already cached and unchanged
        if rel_path in self.embeddings:
            cached = self.embeddings[rel_path]
            if cached.content_hash == content_hash:
                return cached
        
        # Read and embed
        try:
            content = path.read_text()
            
            # Create summary for embedding (filename + first part of content)
            summary = f"File: {path.name}\n\n{content[:2000]}"
            
            embedding = self._get_embedding(summary)
            if embedding:
                file_emb = FileEmbedding(
                    path=rel_path,
                    content_hash=content_hash,
                    embedding=embedding,
                    summary=summary[:500]
                )
                self.embeddings[rel_path] = file_emb
                return file_emb
        except Exception:
            pass
        
        return None
    
    def embed_project(self, show_progress: bool = True) -> int:
        """Embed all files in project"""
        count = 0
        
        # Skip common directories
        skip_dirs = {'.git', 'node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build'}
        
        for root, dirs, files in os.walk(self.project_path):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
            
            for filename in files:
                path = Path(root) / filename
                
                if self.embed_file(path):
                    count += 1
                    if show_progress and count % 10 == 0:
                        print(f"  Embedded {count} files...")
        
        self._save_cache()
        return count
    
    def search(self, query: str, limit: int = 10) -> List[Tuple[str, float]]:
        """
        Search for files relevant to query.
        Returns list of (path, similarity_score) tuples.
        """
        if not self.embeddings:
            return []
        
        # Get query embedding
        query_emb = self._get_embedding(query)
        if not query_emb:
            return []
        
        # Calculate similarities
        results = []
        query_vec = np.array(query_emb)
        
        for path, file_emb in self.embeddings.items():
            file_vec = np.array(file_emb.embedding)
            
            # Cosine similarity
            similarity = np.dot(query_vec, file_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(file_vec)
            )
            
            results.append((path, float(similarity)))
        
        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:limit]
    
    def find_related(self, file_path: str, limit: int = 5) -> List[Tuple[str, float]]:
        """Find files related to a given file"""
        if file_path not in self.embeddings:
            return []
        
        target_emb = self.embeddings[file_path]
        target_vec = np.array(target_emb.embedding)
        
        results = []
        for path, file_emb in self.embeddings.items():
            if path == file_path:
                continue
            
            file_vec = np.array(file_emb.embedding)
            similarity = np.dot(target_vec, file_vec) / (
                np.linalg.norm(target_vec) * np.linalg.norm(file_vec)
            )
            results.append((path, float(similarity)))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]


# ═══════════════════════════════════════════════════════════════
# Integration with RepoExplorer
# ═══════════════════════════════════════════════════════════════

class SemanticFileSearch:
    """
    Combines RepoExplorer (fast keyword) with EmbeddingStore (semantic).
    Uses embeddings only when keyword search fails.
    """
    
    def __init__(self, project_path: str = "."):
        self.project_path = project_path
        self._embedding_store: Optional[EmbeddingStore] = None
        self._repo_explorer = None
    
    @property
    def embedding_store(self) -> EmbeddingStore:
        """Lazy load embedding store"""
        if self._embedding_store is None:
            self._embedding_store = EmbeddingStore(self.project_path)
        return self._embedding_store
    
    @property
    def repo_explorer(self):
        """Lazy load repo explorer"""
        if self._repo_explorer is None:
            from core.repo_explorer import get_explorer
            self._repo_explorer = get_explorer(self.project_path)
        return self._repo_explorer
    
    def ensure_indexed(self):
        """Make sure project is indexed (both keyword and semantic)"""
        # Keyword index (fast)
        self.repo_explorer.scan()
        
        # Semantic index (slower, only if model available)
        if self._is_embed_model_available():
            if not self.embedding_store.embeddings:
                print("  Building semantic index...")
                self.embedding_store.embed_project(show_progress=True)
    
    def _is_embed_model_available(self) -> bool:
        """Check if embedding model is installed"""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "nomic-embed-text" in result.stdout
        except Exception:
            return False
    
    def search(self, query: str, limit: int = 10) -> List[Tuple[str, float]]:
        """
        Search for relevant files.
        
        Strategy:
        1. Try keyword search first (fast)
        2. If few results, enhance with semantic search
        """
        # Keyword search
        keyword_results = self.repo_explorer.find_relevant(query, limit=limit)
        keyword_paths = [(f.path, 0.8) for f in keyword_results]
        
        # If we have enough keyword results, use them
        if len(keyword_paths) >= limit // 2:
            return keyword_paths[:limit]
        
        # Enhance with semantic search
        if self._is_embed_model_available():
            semantic_results = self.embedding_store.search(query, limit=limit)
            
            # Merge results (deduplicate, prefer keyword matches)
            seen = set(p for p, _ in keyword_paths)
            combined = list(keyword_paths)
            
            for path, score in semantic_results:
                if path not in seen:
                    combined.append((path, score * 0.9))  # Slightly lower weight for semantic
                    seen.add(path)
            
            # Sort by score
            combined.sort(key=lambda x: x[1], reverse=True)
            return combined[:limit]
        
        return keyword_paths[:limit]


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

_search: Optional[SemanticFileSearch] = None

def get_semantic_search(project_path: str = ".") -> SemanticFileSearch:
    """Get or create semantic search instance"""
    global _search
    if _search is None or _search.project_path != project_path:
        _search = SemanticFileSearch(project_path)
    return _search
