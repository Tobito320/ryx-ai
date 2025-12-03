"""
Ryx File Selector

Intelligent file selection based on task description.
Combines keyword matching, path analysis, and repository structure.
"""

import os
import re
import fnmatch
from pathlib import Path
from typing import List, Set, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class FileMatch:
    """A file match with relevance score"""
    path: str
    score: float
    reasons: List[str]


class FileSelector:
    """
    Intelligent file selector for Ryx.
    
    Finds relevant files based on:
    - Keyword matching in file names and paths
    - File type detection
    - Directory structure analysis
    - Code symbol matching (when RepoMap is available)
    """
    
    # Common file type keywords
    FILE_TYPE_KEYWORDS = {
        'config': ['config', 'settings', 'conf', 'cfg', 'env', 'yaml', 'yml', 'json', 'toml'],
        'test': ['test', 'spec', 'tests', '__tests__', 'pytest', 'jest', 'mocha'],
        'style': ['style', 'css', 'scss', 'less', 'theme', 'color'],
        'doc': ['doc', 'docs', 'readme', 'changelog', 'contributing', 'md', 'rst'],
        'ui': ['component', 'view', 'page', 'layout', 'template', 'ui', 'widget'],
        'api': ['api', 'route', 'endpoint', 'controller', 'handler', 'service'],
        'model': ['model', 'schema', 'entity', 'type', 'interface', 'dto'],
        'util': ['util', 'utils', 'helper', 'helpers', 'lib', 'common'],
    }
    
    # File extensions by category
    EXTENSIONS = {
        'code': {'.py', '.js', '.ts', '.tsx', '.jsx', '.rs', '.go', '.java', '.kt', '.rb'},
        'config': {'.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.env'},
        'style': {'.css', '.scss', '.less', '.sass'},
        'doc': {'.md', '.rst', '.txt'},
        'web': {'.html', '.htm', '.xml'},
    }
    
    def __init__(self, root: str = None, repo_map=None):
        """
        Initialize FileSelector.
        
        Args:
            root: Repository root directory
            repo_map: Optional RepoMap instance for code analysis
        """
        self.root = Path(root or os.getcwd()).resolve()
        self.repo_map = repo_map
        self._file_cache = None
        
        # Ignore patterns
        self.ignore = {
            '.git', '__pycache__', 'node_modules', '.venv', 'venv',
            'dist', 'build', '.egg-info', '.pytest_cache', '.mypy_cache',
            '.ryx.cache', '*.pyc', '*.pyo'
        }
    
    def _get_files(self) -> List[str]:
        """Get all files in the repository"""
        if self._file_cache is not None:
            return self._file_cache
        
        files = []
        for root, dirs, filenames in os.walk(self.root):
            # Filter ignored directories
            dirs[:] = [d for d in dirs if not any(
                fnmatch.fnmatch(d, p) for p in self.ignore
            )]
            
            for fname in filenames:
                fpath = Path(root) / fname
                if any(fnmatch.fnmatch(str(fpath), p) for p in self.ignore):
                    continue
                
                try:
                    rel_path = str(fpath.relative_to(self.root))
                    files.append(rel_path)
                except ValueError:
                    pass
        
        self._file_cache = files
        return files
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful keywords from text"""
        # Split on word boundaries and common separators
        words = re.findall(r'[a-zA-Z][a-zA-Z0-9]*', text.lower())
        
        # Filter very short words
        keywords = {w for w in words if len(w) >= 2}
        
        # Also handle camelCase and snake_case
        for word in list(keywords):
            # camelCase -> individual words
            parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', word)
            keywords.update(p.lower() for p in parts if len(p) >= 2)
        
        return keywords
    
    def _match_file(self, path: str, keywords: Set[str]) -> FileMatch:
        """Score a file against keywords"""
        path_lower = path.lower()
        path_parts = Path(path).parts
        filename = Path(path).name.lower()
        stem = Path(path).stem.lower()
        ext = Path(path).suffix.lower()
        
        score = 0.0
        reasons = []
        
        # Exact filename match
        for kw in keywords:
            if kw == stem:
                score += 10
                reasons.append(f"exact_name:{kw}")
            elif kw in stem:
                score += 5
                reasons.append(f"name_contains:{kw}")
            elif kw in path_lower:
                score += 2
                reasons.append(f"path_contains:{kw}")
        
        # File type keywords
        for category, type_keywords in self.FILE_TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw in type_keywords:
                    # Check if file matches this category
                    if any(tk in path_lower for tk in type_keywords):
                        score += 3
                        reasons.append(f"category:{category}")
                        break
        
        # Directory relevance
        dir_names = set(p.lower() for p in path_parts[:-1])
        for kw in keywords:
            if kw in dir_names:
                score += 3
                reasons.append(f"directory:{kw}")
        
        return FileMatch(path=path, score=score, reasons=reasons)
    
    def find_files(
        self,
        query: str,
        max_files: int = 10,
        extensions: List[str] = None,
        include_patterns: List[str] = None,
        exclude_patterns: List[str] = None
    ) -> List[str]:
        """
        Find files relevant to a query.
        
        Args:
            query: Natural language description of the task
            max_files: Maximum number of files to return
            extensions: Filter by extensions (e.g., ['.py', '.js'])
            include_patterns: Glob patterns to include
            exclude_patterns: Glob patterns to exclude
            
        Returns:
            List of relevant file paths (relative to root)
        """
        keywords = self._extract_keywords(query)
        
        if not keywords:
            return []
        
        files = self._get_files()
        
        # Apply filters
        if extensions:
            ext_set = set(e if e.startswith('.') else f'.{e}' for e in extensions)
            files = [f for f in files if Path(f).suffix.lower() in ext_set]
        
        if include_patterns:
            filtered = []
            for f in files:
                if any(fnmatch.fnmatch(f, p) for p in include_patterns):
                    filtered.append(f)
            files = filtered
        
        if exclude_patterns:
            files = [f for f in files if not any(
                fnmatch.fnmatch(f, p) for p in exclude_patterns
            )]
        
        # Score files
        matches = []
        for f in files:
            match = self._match_file(f, keywords)
            if match.score > 0:
                matches.append(match)
        
        # Sort by score
        matches.sort(key=lambda m: m.score, reverse=True)
        
        # Use RepoMap for additional ranking if available
        if self.repo_map and len(matches) > max_files:
            repo_ranked = self.repo_map.find_relevant_files(query, max_files * 2)
            
            # Combine rankings
            repo_scores = {f: max_files * 2 - i for i, f in enumerate(repo_ranked)}
            for match in matches:
                if match.path in repo_scores:
                    match.score += repo_scores[match.path]
            
            matches.sort(key=lambda m: m.score, reverse=True)
        
        return [m.path for m in matches[:max_files]]
    
    def find_by_type(self, file_type: str, max_files: int = 20) -> List[str]:
        """
        Find files by type category.
        
        Args:
            file_type: One of 'config', 'test', 'style', 'doc', 'ui', 'api', 'model', 'util'
            max_files: Maximum number of files to return
            
        Returns:
            List of matching file paths
        """
        keywords = self.FILE_TYPE_KEYWORDS.get(file_type.lower(), [file_type])
        query = ' '.join(keywords)
        return self.find_files(query, max_files)
    
    def find_related(self, file_path: str, max_files: int = 5) -> List[str]:
        """
        Find files related to a given file.
        
        Args:
            file_path: Path to the reference file
            max_files: Maximum number of related files to return
            
        Returns:
            List of related file paths
        """
        path = Path(file_path)
        keywords = self._extract_keywords(path.stem)
        
        # Add directory names as keywords
        for part in path.parts[:-1]:
            keywords.update(self._extract_keywords(part))
        
        # Find files with similar names/paths
        matches = []
        for f in self._get_files():
            if f == file_path:
                continue
            match = self._match_file(f, keywords)
            if match.score > 0:
                matches.append(match)
        
        matches.sort(key=lambda m: m.score, reverse=True)
        return [m.path for m in matches[:max_files]]


def find_relevant_files(
    query: str,
    root: str = None,
    max_files: int = 10,
    extensions: List[str] = None
) -> List[str]:
    """
    Convenience function to find relevant files.
    
    Args:
        query: Task description or search query
        root: Repository root (defaults to cwd)
        max_files: Maximum files to return
        extensions: Filter by extensions
        
    Returns:
        List of relevant file paths
    """
    selector = FileSelector(root=root)
    return selector.find_files(query, max_files, extensions)
