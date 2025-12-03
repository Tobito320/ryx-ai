"""
Ryx AI - Semantic Search

Search code using embeddings for semantic similarity.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import numpy as np
import sqlite3
import logging

from .code_embeddings import CodeEmbeddings, EmbeddingConfig, EmbeddedChunk, CodeChunk

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A search result with relevance score"""
    chunk: CodeChunk
    score: float  # 0.0 - 1.0 similarity
    content: str  # Actual content (loaded on demand)
    highlights: List[Tuple[int, int]] = field(default_factory=list)  # (start, end) positions


class SemanticSearch:
    """
    Semantic code search using embeddings.
    
    Features:
    - Vector similarity search
    - Hybrid search (semantic + keyword)
    - File filtering
    - Language filtering
    
    Usage:
    ```python
    search = SemanticSearch()
    
    # Index a directory
    search.index_directory("./src")
    
    # Search
    results = search.search("handle user login", top_k=10)
    ```
    """
    
    def __init__(
        self,
        embeddings: Optional[CodeEmbeddings] = None,
        config: Optional[EmbeddingConfig] = None
    ):
        self.embeddings = embeddings or CodeEmbeddings(config)
        self._index: List[EmbeddedChunk] = []
    
    def index_directory(
        self,
        path: Path,
        extensions: Optional[List[str]] = None,
        ignore_patterns: Optional[List[str]] = None
    ) -> int:
        """
        Index all files in a directory.
        
        Returns number of chunks indexed.
        """
        path = Path(path)
        if not path.exists():
            return 0
        
        # Default extensions
        if extensions is None:
            extensions = [
                '.py', '.js', '.ts', '.tsx', '.jsx',
                '.go', '.rs', '.java', '.cpp', '.c',
                '.rb', '.php', '.sh'
            ]
        
        # Default ignore patterns
        if ignore_patterns is None:
            ignore_patterns = [
                '__pycache__', 'node_modules', '.git',
                'venv', '.venv', 'dist', 'build',
                '.next', '.nuxt', 'target'
            ]
        
        total_chunks = 0
        
        for file_path in path.rglob('*'):
            if not file_path.is_file():
                continue
            
            # Check extension
            if file_path.suffix.lower() not in extensions:
                continue
            
            # Check ignore patterns
            if any(pattern in str(file_path) for pattern in ignore_patterns):
                continue
            
            # Embed file
            chunks = self.embeddings.embed_file(file_path)
            self._index.extend(chunks)
            total_chunks += len(chunks)
        
        logger.info(f"Indexed {total_chunks} chunks from {path}")
        return total_chunks
    
    def index_files(self, files: List[Path]) -> int:
        """Index specific files"""
        total_chunks = 0
        
        for file_path in files:
            chunks = self.embeddings.embed_file(Path(file_path))
            self._index.extend(chunks)
            total_chunks += len(chunks)
        
        return total_chunks
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.3,
        file_filter: Optional[str] = None,
        language_filter: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Search for code chunks matching the query.
        
        Args:
            query: Natural language query
            top_k: Maximum results to return
            min_score: Minimum similarity score
            file_filter: Only search in files matching this pattern
            language_filter: Only search in this language
        """
        # Get query embedding
        query_embedding = self.embeddings.embed_text(query)
        
        if query_embedding is None:
            # Fall back to keyword search
            return self._keyword_search(query, top_k, file_filter, language_filter)
        
        # Get candidates from index
        candidates = self._get_candidates(file_filter, language_filter)
        
        if not candidates:
            # Load from database
            candidates = self._load_from_db(file_filter, language_filter)
        
        # Calculate similarities
        results = []
        
        for embedded in candidates:
            score = self._cosine_similarity(query_embedding, embedded.embedding)
            
            if score >= min_score:
                # Load content
                content = self._load_content(embedded.chunk)
                
                results.append(SearchResult(
                    chunk=embedded.chunk,
                    score=score,
                    content=content,
                    highlights=self._find_highlights(content, query)
                ))
        
        # Sort by score and return top_k
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]
    
    def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        semantic_weight: float = 0.7
    ) -> List[SearchResult]:
        """
        Hybrid search combining semantic and keyword matching.
        
        Args:
            semantic_weight: Weight for semantic search (0-1)
                            keyword weight = 1 - semantic_weight
        """
        # Get semantic results
        semantic_results = self.search(query, top_k=top_k * 2)
        
        # Get keyword results
        keyword_results = self._keyword_search(query, top_k=top_k * 2)
        
        # Combine and re-rank
        combined = {}
        
        for result in semantic_results:
            key = result.chunk.id
            combined[key] = {
                'result': result,
                'semantic_score': result.score,
                'keyword_score': 0.0
            }
        
        for result in keyword_results:
            key = result.chunk.id
            if key in combined:
                combined[key]['keyword_score'] = result.score
            else:
                combined[key] = {
                    'result': result,
                    'semantic_score': 0.0,
                    'keyword_score': result.score
                }
        
        # Calculate combined scores
        final_results = []
        for item in combined.values():
            combined_score = (
                semantic_weight * item['semantic_score'] +
                (1 - semantic_weight) * item['keyword_score']
            )
            item['result'].score = combined_score
            final_results.append(item['result'])
        
        final_results.sort(key=lambda r: r.score, reverse=True)
        return final_results[:top_k]
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(np.dot(a, b) / (norm_a * norm_b))
    
    def _get_candidates(
        self,
        file_filter: Optional[str],
        language_filter: Optional[str]
    ) -> List[EmbeddedChunk]:
        """Get candidate chunks from in-memory index"""
        candidates = self._index
        
        if file_filter:
            candidates = [
                c for c in candidates 
                if file_filter in c.chunk.file_path
            ]
        
        if language_filter:
            candidates = [
                c for c in candidates
                if c.chunk.language == language_filter
            ]
        
        return candidates
    
    def _load_from_db(
        self,
        file_filter: Optional[str],
        language_filter: Optional[str]
    ) -> List[EmbeddedChunk]:
        """Load embeddings from database"""
        conn = sqlite3.connect(self.embeddings.db_path)
        conn.row_factory = sqlite3.Row
        
        query = "SELECT * FROM embeddings WHERE 1=1"
        params = []
        
        if file_filter:
            query += " AND file_path LIKE ?"
            params.append(f"%{file_filter}%")
        
        if language_filter:
            query += " AND language = ?"
            params.append(language_filter)
        
        cursor = conn.execute(query, params)
        
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
                chunk_type=row["chunk_type"]
            )
            results.append(EmbeddedChunk(
                chunk=chunk,
                embedding=embedding,
                hash=row["content_hash"]
            ))
        
        conn.close()
        return results
    
    def _keyword_search(
        self,
        query: str,
        top_k: int = 10,
        file_filter: Optional[str] = None,
        language_filter: Optional[str] = None
    ) -> List[SearchResult]:
        """Fallback keyword-based search"""
        keywords = set(query.lower().split())
        results = []
        
        candidates = self._get_candidates(file_filter, language_filter)
        
        for embedded in candidates:
            content = self._load_content(embedded.chunk)
            content_lower = content.lower()
            
            # Score based on keyword matches
            matches = sum(1 for k in keywords if k in content_lower)
            score = matches / len(keywords) if keywords else 0
            
            if score > 0:
                results.append(SearchResult(
                    chunk=embedded.chunk,
                    score=score,
                    content=content,
                    highlights=self._find_highlights(content, query)
                ))
        
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]
    
    def _load_content(self, chunk: CodeChunk) -> str:
        """Load actual content for a chunk"""
        try:
            path = Path(chunk.file_path)
            if path.exists():
                lines = path.read_text(errors='replace').split('\n')
                return '\n'.join(lines[chunk.start_line - 1:chunk.end_line])
        except Exception as e:
            logger.warning(f"Failed to load content: {e}")
        return ""
    
    def _find_highlights(
        self,
        content: str,
        query: str
    ) -> List[Tuple[int, int]]:
        """Find positions of query terms in content"""
        highlights = []
        content_lower = content.lower()
        
        for word in query.lower().split():
            if len(word) < 3:
                continue
            
            pos = 0
            while True:
                pos = content_lower.find(word, pos)
                if pos == -1:
                    break
                highlights.append((pos, pos + len(word)))
                pos += 1
        
        return highlights
    
    def clear_index(self):
        """Clear the in-memory index"""
        self._index.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get search statistics"""
        return {
            "index_size": len(self._index),
            "embedding_stats": self.embeddings.get_stats()
        }
