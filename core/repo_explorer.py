"""
Ryx AI - Repository Explorer

Scans and indexes codebases to provide context for the AI.
Inspired by Aider's repomap system.

Key features:
- Recursive directory scanning
- File type classification
- Semantic tagging (theme, config, test, etc.)
- Relevance scoring for tasks
"""

import os
import re
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

from core.paths import get_data_dir


class FileType(Enum):
    """Classification of file types"""
    CODE = "code"
    CONFIG = "config"
    DOC = "doc"
    ASSET = "asset"
    TEST = "test"
    BUILD = "build"
    DATA = "data"
    OTHER = "other"


@dataclass
class FileInfo:
    """Metadata about a single file"""
    path: str
    name: str
    extension: str
    size: int
    file_type: FileType
    tags: List[str] = field(default_factory=list)
    summary: str = ""
    last_modified: str = ""
    
    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "name": self.name,
            "extension": self.extension,
            "size": self.size,
            "file_type": self.file_type.value,
            "tags": self.tags,
            "summary": self.summary,
            "last_modified": self.last_modified,
        }


@dataclass
class RepoMap:
    """Complete map of a repository"""
    root: str
    files: Dict[str, FileInfo] = field(default_factory=dict)
    tags_index: Dict[str, List[str]] = field(default_factory=dict)  # tag -> [paths]
    created_at: str = ""
    file_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "files": {k: v.to_dict() for k, v in self.files.items()},
            "tags_index": self.tags_index,
            "created_at": self.created_at,
            "file_count": self.file_count,
        }


class RepoExplorer:
    """
    Explores and indexes a repository/directory.
    Builds a map for intelligent file selection.
    """
    
    # File extension classifications
    CODE_EXTENSIONS = {
        '.py', '.js', '.ts', '.tsx', '.jsx', '.rs', '.go', '.c', '.cpp', '.h',
        '.java', '.kt', '.swift', '.rb', '.php', '.lua', '.sh', '.bash', '.zsh',
        '.vim', '.el', '.clj', '.ex', '.exs', '.hs', '.ml', '.scala', '.r'
    }
    
    CONFIG_EXTENSIONS = {
        '.json', '.yaml', '.yml', '.toml', '.ini', '.conf', '.cfg', '.env',
        '.xml', '.properties', '.rc', '.rasi', '.css', '.scss', '.less'
    }
    
    DOC_EXTENSIONS = {
        '.md', '.rst', '.txt', '.adoc', '.org', '.tex', '.html', '.htm'
    }
    
    ASSET_EXTENSIONS = {
        '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp', '.bmp',
        '.mp3', '.wav', '.ogg', '.mp4', '.webm', '.avi', '.mov',
        '.ttf', '.otf', '.woff', '.woff2', '.eot'
    }
    
    DATA_EXTENSIONS = {
        '.csv', '.tsv', '.sqlite', '.db', '.sql', '.parquet', '.pkl', '.npy'
    }
    
    # Directory patterns to skip
    SKIP_DIRS = {
        '.git', '__pycache__', 'node_modules', 'venv', '.venv', 'env',
        '.env', 'dist', 'build', '.cache', '.pytest_cache', '.mypy_cache',
        'target', '.idea', '.vscode', '.eggs', '*.egg-info'
    }
    
    # Tagging patterns (filename/path patterns -> tags)
    TAG_PATTERNS = {
        # Theme-related
        r'theme|color|style|css|scss': ['theme', 'ui'],
        r'palette|dark|light': ['theme'],
        
        # Config-related
        r'config|settings|preferences|options': ['config'],
        r'\.env|\.rc$|\.conf$': ['config'],
        
        # Test-related
        r'test_|_test\.py|\.test\.|spec\.': ['test'],
        r'tests/|__tests__/|spec/': ['test'],
        
        # UI-related
        r'component|widget|view|page|screen': ['ui'],
        r'button|input|form|modal|dialog': ['ui'],
        
        # API/Network
        r'api|endpoint|route|handler|controller': ['api'],
        r'http|request|response|client|server': ['network'],
        r'websocket|socket|ws': ['network', 'realtime'],
        
        # Database
        r'model|schema|migration|database|db': ['database'],
        r'query|repository|dao': ['database'],
        
        # Auth
        r'auth|login|logout|session|token|jwt': ['auth'],
        r'permission|role|access|security': ['auth', 'security'],
        
        # Utils
        r'util|helper|common|shared|lib': ['util'],
        r'tool|service|manager': ['util'],
        
        # Core
        r'main|app|index|entry|init': ['core'],
        r'brain|engine|core': ['core'],
    }
    
    def __init__(self, root_path: str = "."):
        self.root = os.path.abspath(os.path.expanduser(root_path))
        self.map: Optional[RepoMap] = None
        self.cache_dir = get_data_dir() / "repomap"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def scan(self, force: bool = False) -> RepoMap:
        """
        Scan the repository and build a map.
        Uses cache if available and not forced.
        """
        cache_file = self._get_cache_path()
        
        # Try to load from cache
        if not force and cache_file.exists():
            cached = self._load_cache(cache_file)
            if cached:
                self.map = cached
                return cached
        
        # Build fresh map
        self.map = RepoMap(
            root=self.root,
            created_at=datetime.now().isoformat()
        )
        
        # Walk directory tree
        for dirpath, dirnames, filenames in os.walk(self.root):
            # Filter out skip directories
            dirnames[:] = [d for d in dirnames if d not in self.SKIP_DIRS and not d.startswith('.')]
            
            for filename in filenames:
                if filename.startswith('.'):
                    continue
                    
                filepath = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(filepath, self.root)
                
                # Skip large files (> 1MB)
                try:
                    size = os.path.getsize(filepath)
                    if size > 1_000_000:
                        continue
                except:
                    continue
                
                # Create file info
                info = self._analyze_file(rel_path, filepath)
                self.map.files[rel_path] = info
                
                # Update tags index
                for tag in info.tags:
                    if tag not in self.map.tags_index:
                        self.map.tags_index[tag] = []
                    self.map.tags_index[tag].append(rel_path)
        
        self.map.file_count = len(self.map.files)
        
        # Save to cache
        self._save_cache(cache_file)
        
        return self.map
    
    def _analyze_file(self, rel_path: str, abs_path: str) -> FileInfo:
        """Analyze a single file and extract metadata"""
        name = os.path.basename(rel_path)
        ext = os.path.splitext(name)[1].lower()
        
        # Get file stats
        try:
            stat = os.stat(abs_path)
            size = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime).isoformat()
        except:
            size = 0
            mtime = ""
        
        # Classify file type
        file_type = self._classify_file_type(ext, name, rel_path)
        
        # Generate tags
        tags = self._generate_tags(rel_path, name, ext)
        
        # Generate summary (first docstring or key lines)
        summary = self._generate_summary(abs_path, ext) if file_type == FileType.CODE else ""
        
        return FileInfo(
            path=rel_path,
            name=name,
            extension=ext,
            size=size,
            file_type=file_type,
            tags=tags,
            summary=summary,
            last_modified=mtime
        )
    
    def _classify_file_type(self, ext: str, name: str, path: str) -> FileType:
        """Classify file type based on extension and name"""
        name_lower = name.lower()
        
        # Check for test files
        if 'test' in name_lower or 'spec' in name_lower or '/tests/' in path:
            return FileType.TEST
        
        # Check for build/config files
        if name_lower in {'makefile', 'dockerfile', 'jenkinsfile', 'vagrantfile'}:
            return FileType.BUILD
        if name_lower in {'package.json', 'cargo.toml', 'pyproject.toml', 'setup.py'}:
            return FileType.BUILD
        
        # Extension-based classification
        if ext in self.CODE_EXTENSIONS:
            return FileType.CODE
        if ext in self.CONFIG_EXTENSIONS:
            return FileType.CONFIG
        if ext in self.DOC_EXTENSIONS:
            return FileType.DOC
        if ext in self.ASSET_EXTENSIONS:
            return FileType.ASSET
        if ext in self.DATA_EXTENSIONS:
            return FileType.DATA
        
        return FileType.OTHER
    
    def _generate_tags(self, path: str, name: str, ext: str) -> List[str]:
        """Generate semantic tags for a file"""
        tags = set()
        search_text = f"{path} {name}".lower()
        
        # Apply pattern-based tagging
        for pattern, tag_list in self.TAG_PATTERNS.items():
            if re.search(pattern, search_text):
                tags.update(tag_list)
        
        # Add extension-based tags
        if ext == '.py':
            tags.add('python')
        elif ext in {'.js', '.ts', '.jsx', '.tsx'}:
            tags.add('javascript')
        elif ext == '.rs':
            tags.add('rust')
        elif ext == '.go':
            tags.add('go')
        elif ext in {'.sh', '.bash', '.zsh'}:
            tags.add('shell')
        
        return list(tags)
    
    def _generate_summary(self, filepath: str, ext: str) -> str:
        """Generate a brief summary of a code file"""
        try:
            with open(filepath, 'r', errors='ignore') as f:
                content = f.read(2000)  # First 2KB only
            
            # Python: extract module docstring
            if ext == '.py':
                match = re.search(r'^"""(.*?)"""', content, re.DOTALL)
                if match:
                    return match.group(1).strip()[:200]
                # Or first comment
                match = re.search(r'^#\s*(.+)$', content, re.MULTILINE)
                if match:
                    return match.group(1).strip()[:200]
            
            # JS/TS: extract first comment
            if ext in {'.js', '.ts', '.jsx', '.tsx'}:
                match = re.search(r'^/\*\*(.*?)\*/', content, re.DOTALL)
                if match:
                    return match.group(1).strip()[:200]
                match = re.search(r'^//\s*(.+)$', content, re.MULTILINE)
                if match:
                    return match.group(1).strip()[:200]
            
            return ""
        except:
            return ""
    
    def _get_cache_path(self) -> Path:
        """Get cache file path for this repo"""
        repo_hash = hashlib.md5(self.root.encode()).hexdigest()[:12]
        return self.cache_dir / f"repo_{repo_hash}.json"
    
    def _save_cache(self, path: Path):
        """Save map to cache"""
        if self.map:
            with open(path, 'w') as f:
                json.dump(self.map.to_dict(), f, indent=2)
    
    def _load_cache(self, path: Path) -> Optional[RepoMap]:
        """Load map from cache"""
        try:
            with open(path) as f:
                data = json.load(f)
            
            # Check if cache is recent (< 1 hour)
            created = datetime.fromisoformat(data['created_at'])
            if (datetime.now() - created).total_seconds() > 3600:
                return None
            
            # Reconstruct RepoMap
            repo_map = RepoMap(
                root=data['root'],
                created_at=data['created_at'],
                file_count=data['file_count'],
                tags_index=data['tags_index']
            )
            
            for path, info in data['files'].items():
                repo_map.files[path] = FileInfo(
                    path=info['path'],
                    name=info['name'],
                    extension=info['extension'],
                    size=info['size'],
                    file_type=FileType(info['file_type']),
                    tags=info['tags'],
                    summary=info.get('summary', ''),
                    last_modified=info.get('last_modified', '')
                )
            
            return repo_map
        except:
            return None
    
    # ─────────────────────────────────────────────────────────────
    # Query Methods
    # ─────────────────────────────────────────────────────────────
    
    def find_by_tags(self, tags: List[str]) -> List[FileInfo]:
        """Find files matching any of the given tags"""
        if not self.map:
            self.scan()
        
        matching_paths = set()
        for tag in tags:
            if tag in self.map.tags_index:
                matching_paths.update(self.map.tags_index[tag])
        
        return [self.map.files[p] for p in matching_paths if p in self.map.files]
    
    def find_by_keyword(self, keyword: str) -> List[FileInfo]:
        """Find files by keyword in path/name"""
        if not self.map:
            self.scan()
        
        keyword = keyword.lower()
        results = []
        
        for path, info in self.map.files.items():
            if keyword in path.lower() or keyword in info.name.lower():
                results.append(info)
            elif info.summary and keyword in info.summary.lower():
                results.append(info)
        
        return results
    
    def find_relevant(self, task: str, limit: int = 20) -> List[FileInfo]:
        """
        Find files relevant to a task description.
        Uses keyword extraction and tag matching.
        """
        if not self.map:
            self.scan()
        
        # Extract keywords from task
        task_lower = task.lower()
        words = re.findall(r'\b\w+\b', task_lower)
        
        # Score each file
        scores: Dict[str, float] = {}
        
        for path, info in self.map.files.items():
            score = 0.0
            path_lower = path.lower()
            
            # Keyword matches in path (high weight)
            for word in words:
                if len(word) > 2 and word in path_lower:
                    score += 3.0
            
            # Tag matches (medium weight)
            for word in words:
                if word in info.tags:
                    score += 2.0
            
            # Summary matches (lower weight)
            if info.summary:
                for word in words:
                    if len(word) > 3 and word in info.summary.lower():
                        score += 1.0
            
            # Boost for code files
            if info.file_type == FileType.CODE:
                score *= 1.2
            
            if score > 0:
                scores[path] = score
        
        # Sort by score and return top N
        sorted_paths = sorted(scores.keys(), key=lambda p: scores[p], reverse=True)
        return [self.map.files[p] for p in sorted_paths[:limit]]
    
    def get_summary(self) -> str:
        """Get a text summary of the repo map"""
        if not self.map:
            self.scan()
        
        lines = [
            f"Repository: {self.map.root}",
            f"Files: {self.map.file_count}",
            f"Scanned: {self.map.created_at}",
            "",
            "File types:",
        ]
        
        # Count by type
        type_counts: Dict[FileType, int] = {}
        for info in self.map.files.values():
            type_counts[info.file_type] = type_counts.get(info.file_type, 0) + 1
        
        for ft, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {ft.value}: {count}")
        
        lines.append("")
        lines.append("Tags:")
        
        # Top tags
        tag_counts = [(tag, len(paths)) for tag, paths in self.map.tags_index.items()]
        for tag, count in sorted(tag_counts, key=lambda x: x[1], reverse=True)[:10]:
            lines.append(f"  {tag}: {count} files")
        
        return "\n".join(lines)
    
    def get_tree(self, max_depth: int = 3) -> str:
        """Get a tree view of the repository"""
        if not self.map:
            self.scan()
        
        lines = [os.path.basename(self.root) + "/"]
        
        # Group files by directory
        dirs: Dict[str, List[str]] = {}
        for path in sorted(self.map.files.keys()):
            parts = path.split(os.sep)
            if len(parts) <= max_depth:
                dir_path = os.sep.join(parts[:-1]) if len(parts) > 1 else ""
                if dir_path not in dirs:
                    dirs[dir_path] = []
                dirs[dir_path].append(parts[-1])
        
        # Build tree
        for dir_path in sorted(dirs.keys()):
            if dir_path:
                depth = dir_path.count(os.sep) + 1
                indent = "  " * depth
                lines.append(f"{indent}{os.path.basename(dir_path)}/")
            
            for filename in dirs[dir_path][:10]:  # Limit files shown
                depth = (dir_path.count(os.sep) + 2) if dir_path else 1
                indent = "  " * depth
                lines.append(f"{indent}{filename}")
            
            if len(dirs[dir_path]) > 10:
                depth = (dir_path.count(os.sep) + 2) if dir_path else 1
                indent = "  " * depth
                lines.append(f"{indent}... and {len(dirs[dir_path]) - 10} more")
        
        return "\n".join(lines)


# Singleton instance
_explorer: Optional[RepoExplorer] = None

def get_explorer(root: str = ".") -> RepoExplorer:
    """Get or create explorer instance"""
    global _explorer
    if _explorer is None or _explorer.root != os.path.abspath(root):
        _explorer = RepoExplorer(root)
    return _explorer
