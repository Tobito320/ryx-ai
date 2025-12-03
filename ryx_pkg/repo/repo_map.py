"""
Ryx Repository Map

Builds a map of code definitions and references using tree-sitter.
Provides ranked file selection based on PageRank algorithm.

Inspired by Aider's repomap.py, adapted for Ryx architecture.
Original: https://github.com/paul-gauthier/aider (Apache 2.0 License)
"""

import os
import math
import sqlite3
import hashlib
from collections import Counter, defaultdict, namedtuple
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Tag represents a code symbol (definition or reference)
Tag = namedtuple("Tag", "rel_fname fname line name kind".split())


# Extensions we can parse with tree-sitter
PARSEABLE_EXTENSIONS = {
    '.py', '.js', '.ts', '.tsx', '.jsx', '.rs', '.go', '.c', '.cpp', '.h',
    '.java', '.kt', '.rb', '.php', '.swift', '.cs', '.scala', '.lua',
    '.sh', '.bash', '.zsh'
}

# Extensions to include in repo map (text files)
TEXT_EXTENSIONS = PARSEABLE_EXTENSIONS | {
    '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
    '.md', '.txt', '.rst', '.html', '.css', '.scss', '.less',
    '.xml', '.sql', '.graphql'
}


@dataclass
class FileInfo:
    """Information about a file in the repository"""
    path: str
    rel_path: str
    size: int
    extension: str
    is_parseable: bool
    tags: List[Tag] = None
    mtime: float = 0


class RepoMap:
    """
    Builds and maintains a map of the repository structure.
    
    Uses tree-sitter for code parsing and PageRank for relevance ranking.
    Provides automatic file selection based on task description.
    """
    
    CACHE_DIR = ".ryx.cache"
    
    def __init__(
        self,
        root: str = None,
        max_tokens: int = 4096,
        verbose: bool = False,
        ignore_patterns: List[str] = None
    ):
        """
        Initialize RepoMap.
        
        Args:
            root: Repository root directory (defaults to cwd)
            max_tokens: Maximum tokens for repo map context
            verbose: Enable verbose logging
            ignore_patterns: Additional patterns to ignore
        """
        self.root = Path(root or os.getcwd()).resolve()
        self.max_tokens = max_tokens
        self.verbose = verbose
        
        # Default ignore patterns
        self.ignore_patterns = {
            '.git', '__pycache__', 'node_modules', '.venv', 'venv',
            '.pytest_cache', '.mypy_cache', 'dist', 'build', '.egg-info',
            '.ryx.cache', '.aider*', '*.pyc', '*.pyo', '.DS_Store'
        }
        if ignore_patterns:
            self.ignore_patterns.update(ignore_patterns)
        
        # File index
        self.files: Dict[str, FileInfo] = {}
        self.tags_by_file: Dict[str, List[Tag]] = {}
        self.definitions: Dict[str, Set[str]] = defaultdict(set)  # name -> files
        self.references: Dict[str, List[str]] = defaultdict(list)  # name -> files
        
        # Cache
        self._cache: Dict[str, Any] = {}
        self._tree_sitter_available = self._check_tree_sitter()
    
    def _check_tree_sitter(self) -> bool:
        """Check if tree-sitter is available"""
        try:
            from grep_ast import filename_to_lang
            from grep_ast.tsl import get_parser
            return True
        except ImportError:
            logger.warning("tree-sitter not available, using fallback parsing")
            return False
    
    def should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored"""
        path_str = str(path)
        for pattern in self.ignore_patterns:
            if pattern in path_str:
                return True
            if path.match(pattern):
                return True
        return False
    
    def scan(self, progress_callback=None) -> Dict[str, FileInfo]:
        """
        Scan the repository and build file index.
        
        Args:
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict of relative path -> FileInfo
        """
        self.files = {}
        
        for root, dirs, files in os.walk(self.root):
            # Filter directories in-place
            dirs[:] = [d for d in dirs if not self.should_ignore(Path(root) / d)]
            
            for fname in files:
                fpath = Path(root) / fname
                
                if self.should_ignore(fpath):
                    continue
                
                try:
                    rel_path = str(fpath.relative_to(self.root))
                    ext = fpath.suffix.lower()
                    
                    if ext not in TEXT_EXTENSIONS:
                        continue
                    
                    stat = fpath.stat()
                    
                    self.files[rel_path] = FileInfo(
                        path=str(fpath),
                        rel_path=rel_path,
                        size=stat.st_size,
                        extension=ext,
                        is_parseable=ext in PARSEABLE_EXTENSIONS,
                        mtime=stat.st_mtime
                    )
                    
                    if progress_callback:
                        progress_callback(f"Scanning: {rel_path}")
                        
                except (OSError, ValueError) as e:
                    logger.debug(f"Skip {fpath}: {e}")
        
        if self.verbose:
            logger.info(f"Scanned {len(self.files)} files in {self.root}")
        
        return self.files
    
    def get_tags(self, file_info: FileInfo) -> List[Tag]:
        """
        Get tags (definitions and references) from a file.
        
        Uses tree-sitter if available, falls back to regex-based parsing.
        """
        if file_info.tags is not None:
            return file_info.tags
        
        if not file_info.is_parseable:
            return []
        
        try:
            if self._tree_sitter_available:
                tags = self._get_tags_treesitter(file_info)
            else:
                tags = self._get_tags_fallback(file_info)
            
            file_info.tags = tags
            return tags
            
        except Exception as e:
            logger.debug(f"Error parsing {file_info.rel_path}: {e}")
            return []
    
    def _get_tags_treesitter(self, file_info: FileInfo) -> List[Tag]:
        """Get tags using tree-sitter"""
        from grep_ast import filename_to_lang
        from grep_ast.tsl import get_parser, get_language
        
        lang = filename_to_lang(file_info.path)
        if not lang:
            return []
        
        try:
            parser = get_parser(lang)
            language = get_language(lang)
        except Exception:
            return []
        
        try:
            with open(file_info.path, 'r', encoding='utf-8', errors='replace') as f:
                code = f.read()
        except Exception:
            return []
        
        tree = parser.parse(bytes(code, 'utf-8'))
        
        # Get query for this language
        query_scm = self._get_query_scm(lang)
        if not query_scm:
            return self._get_tags_fallback(file_info)
        
        query = language.query(query_scm)
        captures = query.captures(tree.root_node)
        
        tags = []
        for node, tag_name in captures.items() if isinstance(captures, dict) else captures:
            if isinstance(captures, dict):
                nodes = captures[node]
                tag = node
            else:
                nodes = [node]
                tag = tag_name
            
            for n in (nodes if isinstance(nodes, list) else [nodes]):
                if tag.startswith("name.definition."):
                    kind = "def"
                elif tag.startswith("name.reference."):
                    kind = "ref"
                else:
                    continue
                
                tags.append(Tag(
                    rel_fname=file_info.rel_path,
                    fname=file_info.path,
                    name=n.text.decode('utf-8') if hasattr(n, 'text') else str(n),
                    kind=kind,
                    line=n.start_point[0] if hasattr(n, 'start_point') else 0
                ))
        
        return tags
    
    def _get_query_scm(self, lang: str) -> Optional[str]:
        """Get tree-sitter query for language"""
        try:
            from importlib import resources
            scm_path = resources.files('grep_ast') / 'queries' / f'{lang}-tags.scm'
            if scm_path.is_file():
                return scm_path.read_text()
        except Exception:
            pass
        return None
    
    def _get_tags_fallback(self, file_info: FileInfo) -> List[Tag]:
        """Fallback tag extraction using regex patterns"""
        import re
        
        patterns = {
            '.py': [
                (r'^(?:async\s+)?def\s+(\w+)', 'def'),
                (r'^class\s+(\w+)', 'def'),
                (r'(\w+)\s*\(', 'ref'),
            ],
            '.js': [
                (r'(?:function|const|let|var)\s+(\w+)', 'def'),
                (r'class\s+(\w+)', 'def'),
                (r'(\w+)\s*\(', 'ref'),
            ],
            '.ts': [
                (r'(?:function|const|let|var)\s+(\w+)', 'def'),
                (r'(?:class|interface|type)\s+(\w+)', 'def'),
                (r'(\w+)\s*\(', 'ref'),
            ],
        }
        
        ext = file_info.extension
        if ext not in patterns:
            return []
        
        tags = []
        try:
            with open(file_info.path, 'r', encoding='utf-8', errors='replace') as f:
                for line_num, line in enumerate(f):
                    for pattern, kind in patterns[ext]:
                        for match in re.finditer(pattern, line):
                            name = match.group(1)
                            if name and len(name) > 1:
                                tags.append(Tag(
                                    rel_fname=file_info.rel_path,
                                    fname=file_info.path,
                                    name=name,
                                    kind=kind,
                                    line=line_num
                                ))
        except Exception:
            pass
        
        return tags
    
    def build_index(self, progress_callback=None):
        """Build the definitions and references index"""
        if not self.files:
            self.scan(progress_callback)
        
        self.definitions.clear()
        self.references.clear()
        
        for rel_path, file_info in self.files.items():
            if progress_callback:
                progress_callback(f"Indexing: {rel_path}")
            
            tags = self.get_tags(file_info)
            self.tags_by_file[rel_path] = tags
            
            for tag in tags:
                if tag.kind == 'def':
                    self.definitions[tag.name].add(rel_path)
                else:
                    self.references[tag.name].append(rel_path)
        
        if self.verbose:
            logger.info(f"Indexed {len(self.definitions)} definitions, "
                       f"{len(self.references)} references")
    
    def get_ranked_files(
        self,
        mentioned_files: Set[str] = None,
        mentioned_idents: Set[str] = None,
        max_files: int = 20
    ) -> List[Tuple[str, float]]:
        """
        Get files ranked by relevance using PageRank.
        
        Args:
            mentioned_files: Files mentioned in the query
            mentioned_idents: Identifiers mentioned in the query
            max_files: Maximum number of files to return
            
        Returns:
            List of (rel_path, rank) tuples, sorted by rank descending
        """
        try:
            import networkx as nx
        except ImportError:
            logger.warning("networkx not available, using simple ranking")
            return self._simple_ranking(mentioned_files, mentioned_idents, max_files)
        
        if not self.definitions:
            self.build_index()
        
        G = nx.MultiDiGraph()
        
        # Build personalization for mentioned items
        personalization = {}
        base_weight = 100 / max(len(self.files), 1)
        
        for fname in (mentioned_files or set()):
            if fname in self.files:
                personalization[fname] = base_weight * 10
        
        # Add edges based on references
        for name, definers in self.definitions.items():
            refs = self.references.get(name, [])
            
            weight = 1.0
            if mentioned_idents and name in mentioned_idents:
                weight *= 10
            
            # Prefer longer, more specific names
            if len(name) >= 8 and ('_' in name or any(c.isupper() for c in name)):
                weight *= 2
            
            for ref_file in refs:
                for def_file in definers:
                    G.add_edge(ref_file, def_file, weight=weight, ident=name)
        
        if not G.nodes():
            return list(self.files.keys())[:max_files]
        
        try:
            if personalization:
                ranked = nx.pagerank(G, weight='weight', 
                                    personalization=personalization,
                                    dangling=personalization)
            else:
                ranked = nx.pagerank(G, weight='weight')
        except Exception:
            ranked = {n: 1.0 for n in G.nodes()}
        
        sorted_files = sorted(ranked.items(), key=lambda x: x[1], reverse=True)
        return sorted_files[:max_files]
    
    def _simple_ranking(
        self,
        mentioned_files: Set[str],
        mentioned_idents: Set[str],
        max_files: int
    ) -> List[Tuple[str, float]]:
        """Simple fallback ranking without networkx"""
        scores = {}
        
        for rel_path, file_info in self.files.items():
            score = 1.0
            
            if mentioned_files and rel_path in mentioned_files:
                score += 10
            
            if mentioned_idents:
                tags = self.get_tags(file_info)
                for tag in tags:
                    if tag.name in mentioned_idents:
                        score += 5 if tag.kind == 'def' else 1
            
            scores[rel_path] = score
        
        sorted_files = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_files[:max_files]
    
    def find_relevant_files(
        self,
        query: str,
        max_files: int = 10,
        file_patterns: List[str] = None
    ) -> List[str]:
        """
        Find files relevant to a query/task description.
        
        Args:
            query: Task description or search query
            max_files: Maximum number of files to return
            file_patterns: Optional file patterns to filter (e.g., ["*.py"])
            
        Returns:
            List of relevant file paths (relative to repo root)
        """
        if not self.files:
            self.scan()
        
        # Extract identifiers from query
        import re
        words = set(re.findall(r'\b\w+\b', query))
        
        # Filter for likely code identifiers
        mentioned_idents = {
            w for w in words 
            if len(w) >= 3 and (
                '_' in w or  # snake_case
                any(c.isupper() for c in w[1:]) or  # camelCase or PascalCase
                w.lower() in {'def', 'class', 'function', 'method', 'test'}
            )
        }
        
        # Also include regular words for file name matching
        keywords = {w.lower() for w in words if len(w) >= 3}
        
        # Find files matching patterns
        mentioned_files = set()
        for rel_path in self.files:
            path_lower = rel_path.lower()
            for kw in keywords:
                if kw in path_lower:
                    mentioned_files.add(rel_path)
                    break
        
        # Apply file pattern filter if specified
        if file_patterns:
            import fnmatch
            filtered = set()
            for rel_path in self.files:
                for pattern in file_patterns:
                    if fnmatch.fnmatch(rel_path, pattern):
                        filtered.add(rel_path)
                        break
            mentioned_files = mentioned_files.intersection(filtered) if mentioned_files else filtered
        
        # Get ranked files
        ranked = self.get_ranked_files(mentioned_files, mentioned_idents, max_files * 2)
        
        # Combine with keyword-matched files
        result = []
        seen = set()
        
        # First add files that matched keywords
        for f in mentioned_files:
            if f not in seen and len(result) < max_files:
                result.append(f)
                seen.add(f)
        
        # Then add PageRank-ranked files
        for f, _ in ranked:
            if f not in seen and len(result) < max_files:
                result.append(f)
                seen.add(f)
        
        return result
    
    def get_context_string(
        self,
        files: List[str] = None,
        max_tokens: int = None
    ) -> str:
        """
        Generate a context string for the LLM.
        
        Args:
            files: Files to include (uses all if not specified)
            max_tokens: Maximum tokens (uses self.max_tokens if not specified)
            
        Returns:
            Formatted context string with file structure and definitions
        """
        max_tokens = max_tokens or self.max_tokens
        files = files or list(self.files.keys())
        
        lines = ["# Repository Structure\n"]
        
        # Group files by directory
        by_dir = defaultdict(list)
        for f in sorted(files):
            parts = Path(f).parts
            if len(parts) > 1:
                by_dir[parts[0]].append(f)
            else:
                by_dir['.'].append(f)
        
        for dir_name, dir_files in sorted(by_dir.items()):
            lines.append(f"\n## {dir_name}/")
            for f in dir_files[:10]:  # Limit files per directory
                file_info = self.files.get(f)
                if file_info:
                    tags = self.get_tags(file_info)
                    defs = [t.name for t in tags if t.kind == 'def'][:5]
                    if defs:
                        lines.append(f"- {f}: {', '.join(defs)}")
                    else:
                        lines.append(f"- {f}")
        
        result = '\n'.join(lines)
        
        # Simple token estimation (4 chars per token)
        est_tokens = len(result) / 4
        if est_tokens > max_tokens:
            # Truncate if too long
            char_limit = int(max_tokens * 4)
            result = result[:char_limit] + "\n... (truncated)"
        
        return result


def find_relevant_files(query: str, root: str = None, max_files: int = 10) -> List[str]:
    """
    Convenience function to find relevant files for a query.
    
    Args:
        query: Task description or search query
        root: Repository root (defaults to cwd)
        max_files: Maximum number of files to return
        
    Returns:
        List of relevant file paths
    """
    repo_map = RepoMap(root=root)
    return repo_map.find_relevant_files(query, max_files)
