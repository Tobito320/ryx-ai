"""
Ryx Repository Explorer

High-level repository exploration for Ryx agents.
Combines RepoMap and FileSelector for intelligent file discovery.
Now integrated with Manifest system for project-specific configuration.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging

from .repo_map import RepoMap
from .file_selector import FileSelector

logger = logging.getLogger(__name__)

# Try to import Manifest system
try:
    from core.manifest import ManifestLoader, ManifestConfig
    MANIFEST_AVAILABLE = True
except ImportError:
    MANIFEST_AVAILABLE = False
    ManifestLoader = None
    ManifestConfig = None


@dataclass
class RepoStats:
    """Statistics about a repository"""
    total_files: int = 0
    total_size: int = 0
    languages: Dict[str, int] = field(default_factory=dict)
    directories: int = 0
    last_scan: str = ""


@dataclass 
class RepoContext:
    """Context about the repository for LLM consumption"""
    root: str
    name: str
    stats: RepoStats
    relevant_files: List[str] = field(default_factory=list)
    file_tree: str = ""
    definitions: str = ""


class RepoExplorer:
    """
    High-level repository explorer for Ryx.
    
    Provides:
    - Repository scanning and indexing
    - Automatic file discovery for tasks
    - Context generation for LLMs
    - Caching for performance
    - Manifest integration for project-specific config (P1.7)
    
    Usage:
        explorer = RepoExplorer("/path/to/project")
        files = explorer.find_for_task("fix the login button")
        context = explorer.get_context_for_llm(files)
    """
    
    CACHE_FILE = ".ryx.repo.json"
    
    def __init__(
        self,
        root: str = None,
        verbose: bool = False,
        use_cache: bool = True,
        ignore_patterns: List[str] = None
    ):
        """
        Initialize RepoExplorer.
        
        Args:
            root: Repository root directory (defaults to cwd)
            verbose: Enable verbose logging
            use_cache: Use cached repository data
            ignore_patterns: Additional patterns to ignore
        """
        self.root = Path(root or os.getcwd()).resolve()
        self.verbose = verbose
        self.use_cache = use_cache
        
        # Load manifest if available (P1.7)
        self.manifest: Optional[Any] = None
        if MANIFEST_AVAILABLE:
            try:
                loader = ManifestLoader(str(self.root))
                self.manifest = loader.load()
                if self.manifest and self.manifest.ignore_patterns:
                    # Merge manifest ignore patterns with provided ones
                    ignore_patterns = list(set(
                        (ignore_patterns or []) + self.manifest.ignore_patterns
                    ))
            except Exception as e:
                logger.debug(f"Could not load manifest: {e}")
        
        self.repo_map = RepoMap(
            root=str(self.root),
            verbose=verbose,
            ignore_patterns=ignore_patterns
        )
        self.file_selector = FileSelector(
            root=str(self.root),
            repo_map=self.repo_map
        )
        
        self._stats: Optional[RepoStats] = None
        self._scanned = False
    
    def get_manifest(self) -> Optional[Any]:
        """Get the loaded manifest config"""
        return self.manifest
    
    def get_priority_files(self) -> List[str]:
        """Get priority files from manifest (P1.7)"""
        if self.manifest and hasattr(self.manifest, 'priority_files'):
            return self.manifest.priority_files
        return []
    
    def get_context_limit(self) -> int:
        """Get context limit from manifest (P1.7)"""
        if self.manifest and hasattr(self.manifest, 'context_limit'):
            return self.manifest.context_limit
        return 50
    
    def scan(self, force: bool = False, progress_callback=None) -> RepoStats:
        """
        Scan the repository.
        
        Args:
            force: Force rescan even if cached
            progress_callback: Optional callback for progress updates
            
        Returns:
            Repository statistics
        """
        if self._scanned and not force:
            return self._stats
        
        # Try to load from cache
        if self.use_cache and not force:
            cached = self._load_cache()
            if cached:
                self._stats = cached
                self._scanned = True
                return self._stats
        
        # Scan the repository
        if progress_callback:
            progress_callback("Scanning repository...")
        
        files = self.repo_map.scan(progress_callback)
        
        # Calculate stats
        stats = RepoStats(
            total_files=len(files),
            last_scan=datetime.now().isoformat()
        )
        
        languages = {}
        total_size = 0
        directories = set()
        
        for rel_path, file_info in files.items():
            total_size += file_info.size
            
            ext = file_info.extension.lstrip('.')
            if ext:
                languages[ext] = languages.get(ext, 0) + 1
            
            dir_path = str(Path(rel_path).parent)
            if dir_path != '.':
                directories.add(dir_path)
        
        stats.total_size = total_size
        stats.languages = languages
        stats.directories = len(directories)
        
        self._stats = stats
        self._scanned = True
        
        # Save to cache
        if self.use_cache:
            self._save_cache(stats)
        
        return stats
    
    def _load_cache(self) -> Optional[RepoStats]:
        """Load cached repository data"""
        cache_path = self.root / self.CACHE_FILE
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            
            # Check if cache is still valid (max 1 hour)
            last_scan = datetime.fromisoformat(data.get('last_scan', ''))
            age = (datetime.now() - last_scan).total_seconds()
            if age > 3600:  # 1 hour
                return None
            
            return RepoStats(**data)
        except Exception as e:
            logger.debug(f"Cache load error: {e}")
            return None
    
    def _save_cache(self, stats: RepoStats):
        """Save repository data to cache"""
        cache_path = self.root / self.CACHE_FILE
        try:
            with open(cache_path, 'w') as f:
                json.dump(asdict(stats), f, indent=2)
        except Exception as e:
            logger.debug(f"Cache save error: {e}")
    
    def find_for_task(
        self,
        task: str,
        max_files: int = 10,
        file_types: List[str] = None
    ) -> List[str]:
        """
        Find relevant files for a task.
        
        This is the main entry point for Ryx agents to find files.
        Respects manifest priority_files if available (P1.7).
        
        Args:
            task: Natural language task description
            max_files: Maximum number of files to return
            file_types: Optional file type filters (e.g., ['code', 'config'])
            
        Returns:
            List of relevant file paths
        """
        if not self._scanned:
            self.scan()
        
        # Use manifest context limit if available
        if self.manifest and hasattr(self.manifest, 'context_limit'):
            max_files = min(max_files, self.manifest.context_limit)
        
        # Convert file types to extensions
        extensions = None
        if file_types:
            extensions = []
            from .file_selector import FileSelector
            for ft in file_types:
                if ft in FileSelector.EXTENSIONS:
                    extensions.extend(FileSelector.EXTENSIONS[ft])
        
        # Get priority files from manifest first (P1.7)
        priority_files = []
        if self.manifest and hasattr(self.manifest, 'priority_files'):
            for pf in self.manifest.priority_files:
                # Check if file exists
                full_path = self.root / pf
                if full_path.exists():
                    priority_files.append(pf)
        
        # Find task-relevant files
        task_files = self.file_selector.find_files(
            task,
            max_files=max_files,
            extensions=extensions
        )
        
        # Combine: priority files first, then task-relevant (no duplicates)
        result = list(priority_files)
        for f in task_files:
            if f not in result and len(result) < max_files:
                result.append(f)
        
        return result
    
    def get_context_for_llm(
        self,
        files: List[str] = None,
        task: str = None,
        max_tokens: int = 4096,
        include_content: bool = False
    ) -> str:
        """
        Generate context string for LLM consumption.
        
        Args:
            files: Specific files to include (or auto-select if None)
            task: Task description (used if files is None)
            max_tokens: Maximum context tokens
            include_content: Include file contents (not just structure)
            
        Returns:
            Formatted context string
        """
        if not self._scanned:
            self.scan()
        
        if files is None and task:
            files = self.find_for_task(task, max_files=15)
        elif files is None:
            files = list(self.repo_map.files.keys())[:20]
        
        lines = []
        lines.append(f"# Repository: {self.root.name}")
        lines.append(f"# Path: {self.root}")
        
        if self._stats:
            lines.append(f"# Files: {self._stats.total_files}")
            if self._stats.languages:
                top_langs = sorted(
                    self._stats.languages.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
                lang_str = ", ".join(f"{k}:{v}" for k, v in top_langs)
                lines.append(f"# Languages: {lang_str}")
        
        lines.append("")
        lines.append("## Relevant Files")
        lines.append("")
        
        for f in files:
            file_info = self.repo_map.files.get(f)
            if file_info:
                tags = self.repo_map.get_tags(file_info)
                defs = [t.name for t in tags if t.kind == 'def'][:5]
                if defs:
                    lines.append(f"- {f}")
                    lines.append(f"  Defines: {', '.join(defs)}")
                else:
                    lines.append(f"- {f}")
            else:
                lines.append(f"- {f}")
        
        if include_content:
            lines.append("")
            lines.append("## File Contents")
            
            for f in files[:5]:  # Limit to 5 files with content
                fpath = self.root / f
                if fpath.exists() and fpath.is_file():
                    try:
                        content = fpath.read_text(errors='replace')
                        # Truncate large files
                        if len(content) > 2000:
                            content = content[:2000] + "\n... (truncated)"
                        
                        lines.append(f"\n### {f}")
                        lines.append("```")
                        lines.append(content)
                        lines.append("```")
                    except Exception:
                        pass
        
        result = '\n'.join(lines)
        
        # Truncate if too long
        char_limit = max_tokens * 4
        if len(result) > char_limit:
            result = result[:char_limit] + "\n... (truncated)"
        
        return result
    
    def get_file_tree(self, max_depth: int = 3) -> str:
        """
        Get a tree representation of the repository.
        
        Args:
            max_depth: Maximum depth to display
            
        Returns:
            ASCII tree representation
        """
        if not self._scanned:
            self.scan()
        
        lines = [str(self.root.name)]
        
        # Build directory tree
        dirs = {}
        for rel_path in sorted(self.repo_map.files.keys()):
            parts = Path(rel_path).parts
            if len(parts) > max_depth:
                parts = parts[:max_depth]
            
            for i, part in enumerate(parts):
                key = '/'.join(parts[:i+1])
                if key not in dirs:
                    prefix = "  " * i + "├─ "
                    if i < len(parts) - 1:
                        lines.append(f"{prefix}{part}/")
                    else:
                        lines.append(f"{prefix}{part}")
                    dirs[key] = True
        
        return '\n'.join(lines[:100])  # Limit output
