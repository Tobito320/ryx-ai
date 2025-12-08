"""
Ryx AI - Repository Map (Extracted from Aider patterns)

Creates a semantic map of the repository for intelligent file selection.

Why this matters:
- LLMs have limited context windows
- Loading ALL files is impossible and wastes tokens
- We need to select the MOST RELEVANT files for each query
- A good repo map understands code structure, not just file names

Key features:
1. Tree-sitter parsing for code structure (functions, classes, imports)
2. Symbol indexing for quick lookup
3. Dependency graph (what imports what)
4. Relevance scoring based on query terms
5. Caching for performance

Inspired by Aider's RepoMap but simplified for local performance.
"""

import os
import re
import subprocess
import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, NamedTuple
from dataclasses import dataclass, field
from collections import defaultdict

from core.paths import get_data_dir

logger = logging.getLogger(__name__)


class Symbol(NamedTuple):
    """A code symbol (function, class, variable)"""
    name: str
    kind: str  # function, class, method, variable, import
    file: str
    line: int
    signature: Optional[str] = None


@dataclass
class FileInfo:
    """Information about a source file"""
    path: str
    language: str
    size: int
    modified: float
    symbols: List[Symbol] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    exported: List[str] = field(default_factory=list)  # Public symbols
    
    def get_summary(self, max_symbols: int = 20) -> str:
        """Get a compact summary of the file"""
        lines = [f"## {self.path}"]
        
        # Group by kind
        by_kind = defaultdict(list)
        for sym in self.symbols[:max_symbols]:
            by_kind[sym.kind].append(sym)
        
        for kind in ['class', 'function', 'method']:
            if kind in by_kind:
                names = [s.name for s in by_kind[kind]]
                lines.append(f"  {kind}s: {', '.join(names[:10])}")
        
        return '\n'.join(lines)


class RepoMap:
    """
    Semantic map of a code repository.
    
    Usage:
        repo_map = RepoMap("/path/to/repo")
        relevant = repo_map.get_relevant_files("fix the vllm client")
        for file_info in relevant:
            print(file_info.path, file_info.symbols)
    """
    
    # File extensions we care about
    CODE_EXTENSIONS = {
        '.py': 'python',
        '.js': 'javascript', 
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.jsx': 'javascript',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.java': 'java',
        '.c': 'c',
        '.cpp': 'cpp',
        '.h': 'c',
        '.hpp': 'cpp',
    }
    
    # Directories to ignore
    IGNORE_DIRS = {
        'node_modules', '__pycache__', '.git', 'venv', '.venv',
        'dist', 'build', '.egg-info', 'eggs', '.tox', '.nox',
        '.pytest_cache', '.mypy_cache', 'htmlcov', '.coverage',
        'target', 'vendor', 'pkg', 'bin', 'obj',
        '@types', 'typings',  # TypeScript type definitions (noise)
    }
    
    def __init__(self, root: str, cache_dir: Optional[str] = None):
        self.root = Path(root).resolve()
        self.cache_dir = Path(cache_dir) if cache_dir else get_data_dir() / "repo_map_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.files: Dict[str, FileInfo] = {}
        self.symbols: Dict[str, List[Symbol]] = defaultdict(list)  # name -> symbols
        self.imports_graph: Dict[str, Set[str]] = defaultdict(set)  # file -> imported files
        
        self._cache_file = self.cache_dir / f"{self._hash_root()}.json"
        self._load_cache()
    
    def _hash_root(self) -> str:
        """Hash the root path for cache key"""
        return hashlib.md5(str(self.root).encode()).hexdigest()[:12]
    
    def _load_cache(self):
        """Load cached repo map if valid"""
        if not self._cache_file.exists():
            return
        
        try:
            cache = json.loads(self._cache_file.read_text())
            # Check cache version and staleness
            if cache.get('version') != 2:
                return
            if cache.get('root') != str(self.root):
                return
            
            # Load file info
            for path, info in cache.get('files', {}).items():
                symbols = [Symbol(**s) for s in info.get('symbols', [])]
                self.files[path] = FileInfo(
                    path=path,
                    language=info['language'],
                    size=info['size'],
                    modified=info['modified'],
                    symbols=symbols,
                    imports=info.get('imports', []),
                    exported=info.get('exported', [])
                )
                for sym in symbols:
                    self.symbols[sym.name].append(sym)
            
            logger.debug(f"Loaded repo map cache: {len(self.files)} files")
        except Exception as e:
            logger.debug(f"Failed to load cache: {e}")
    
    def _save_cache(self):
        """Save repo map to cache"""
        try:
            cache = {
                'version': 2,
                'root': str(self.root),
                'files': {}
            }
            
            for path, info in self.files.items():
                cache['files'][path] = {
                    'language': info.language,
                    'size': info.size,
                    'modified': info.modified,
                    'symbols': [s._asdict() for s in info.symbols],
                    'imports': info.imports,
                    'exported': info.exported
                }
            
            self._cache_file.write_text(json.dumps(cache))
            logger.debug(f"Saved repo map cache: {len(self.files)} files")
        except Exception as e:
            logger.debug(f"Failed to save cache: {e}")
    
    def scan(self, force: bool = False):
        """
        Scan the repository and build the map.
        
        Args:
            force: Force rescan even if cached
        """
        if not force and self.files:
            # Check if any files changed
            needs_update = False
            for path, info in list(self.files.items()):
                full_path = self.root / path
                if not full_path.exists():
                    del self.files[path]
                    needs_update = True
                elif full_path.stat().st_mtime > info.modified:
                    needs_update = True
                    break
            
            if not needs_update:
                return
        
        logger.info(f"Scanning repository: {self.root}")
        
        # Find all code files
        for root, dirs, files in os.walk(self.root):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS]
            
            for filename in files:
                ext = Path(filename).suffix.lower()
                if ext not in self.CODE_EXTENSIONS:
                    continue
                
                full_path = Path(root) / filename
                rel_path = str(full_path.relative_to(self.root))
                
                # Check if already scanned and unchanged
                if rel_path in self.files:
                    cached = self.files[rel_path]
                    if full_path.stat().st_mtime <= cached.modified:
                        continue
                
                # Scan the file
                file_info = self._scan_file(full_path, rel_path, self.CODE_EXTENSIONS[ext])
                if file_info:
                    self.files[rel_path] = file_info
                    for sym in file_info.symbols:
                        self.symbols[sym.name].append(sym)
        
        self._save_cache()
        logger.info(f"Scanned {len(self.files)} files, found {len(self.symbols)} unique symbols")
    
    def _scan_file(self, path: Path, rel_path: str, language: str) -> Optional[FileInfo]:
        """Scan a single file for symbols"""
        try:
            content = path.read_text(encoding='utf-8', errors='replace')
            stat = path.stat()
            
            symbols = []
            imports = []
            
            if language == 'python':
                symbols, imports = self._parse_python(content, rel_path)
            elif language in ('javascript', 'typescript'):
                symbols, imports = self._parse_js_ts(content, rel_path)
            else:
                # Basic fallback - find function/class declarations
                symbols = self._parse_basic(content, rel_path, language)
            
            # Determine exported symbols (Python: no leading underscore)
            exported = [s.name for s in symbols if not s.name.startswith('_')]
            
            return FileInfo(
                path=rel_path,
                language=language,
                size=stat.st_size,
                modified=stat.st_mtime,
                symbols=symbols,
                imports=imports,
                exported=exported
            )
        except Exception as e:
            logger.debug(f"Failed to scan {rel_path}: {e}")
            return None
    
    def _parse_python(self, content: str, file_path: str) -> Tuple[List[Symbol], List[str]]:
        """Parse Python file for symbols and imports"""
        symbols = []
        imports = []
        
        lines = content.splitlines()
        current_class = None
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Imports
            if stripped.startswith('import ') or stripped.startswith('from '):
                # Extract module name
                match = re.match(r'(?:from\s+(\S+)|import\s+(\S+))', stripped)
                if match:
                    module = match.group(1) or match.group(2)
                    imports.append(module.split('.')[0])
            
            # Class definitions
            match = re.match(r'^class\s+(\w+)', stripped)
            if match:
                class_name = match.group(1)
                current_class = class_name
                # Get the full signature
                sig_match = re.match(r'^(class\s+\w+[^:]*)', stripped)
                sig = sig_match.group(1) if sig_match else f"class {class_name}"
                symbols.append(Symbol(class_name, 'class', file_path, i, sig))
                continue
            
            # Function/method definitions  
            match = re.match(r'^(\s*)def\s+(\w+)\s*\((.*?)\)', stripped)
            if match:
                indent = len(match.group(1)) if match.group(1) else len(line) - len(line.lstrip())
                func_name = match.group(2)
                params = match.group(3)
                
                kind = 'method' if current_class and indent > 0 else 'function'
                full_name = f"{current_class}.{func_name}" if kind == 'method' and current_class else func_name
                sig = f"def {func_name}({params})"
                
                symbols.append(Symbol(full_name, kind, file_path, i, sig))
                
                # Reset class context if we're back to top-level
                if indent == 0:
                    current_class = None
            
            # Top-level assignments (module constants)
            if not line.startswith(' ') and not line.startswith('\t'):
                match = re.match(r'^([A-Z][A-Z_0-9]*)\s*=', line)
                if match:
                    symbols.append(Symbol(match.group(1), 'constant', file_path, i))
        
        return symbols, list(set(imports))
    
    def _parse_js_ts(self, content: str, file_path: str) -> Tuple[List[Symbol], List[str]]:
        """Parse JavaScript/TypeScript for symbols"""
        symbols = []
        imports = []
        
        lines = content.splitlines()
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Imports
            if stripped.startswith('import '):
                match = re.search(r'from\s+[\'"]([^\'"]+)[\'"]', stripped)
                if match:
                    imports.append(match.group(1).split('/')[0])
            
            # Function declarations
            match = re.match(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)', stripped)
            if match:
                symbols.append(Symbol(match.group(1), 'function', file_path, i))
            
            # Arrow functions / const functions
            match = re.match(r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(', stripped)
            if match:
                symbols.append(Symbol(match.group(1), 'function', file_path, i))
            
            # Class declarations
            match = re.match(r'(?:export\s+)?class\s+(\w+)', stripped)
            if match:
                symbols.append(Symbol(match.group(1), 'class', file_path, i))
            
            # Interface/type declarations
            match = re.match(r'(?:export\s+)?(?:interface|type)\s+(\w+)', stripped)
            if match:
                symbols.append(Symbol(match.group(1), 'type', file_path, i))
        
        return symbols, list(set(imports))
    
    def _parse_basic(self, content: str, file_path: str, language: str) -> List[Symbol]:
        """Basic parsing for other languages"""
        symbols = []
        lines = content.splitlines()
        
        for i, line in enumerate(lines, 1):
            # Function patterns
            for pattern in [
                r'(?:def|fn|func|function)\s+(\w+)',  # Python, Ruby, Go, JS
                r'(?:public|private|protected)?\s*(?:static\s+)?(?:\w+\s+)+(\w+)\s*\(',  # Java/C#
            ]:
                match = re.search(pattern, line)
                if match:
                    symbols.append(Symbol(match.group(1), 'function', file_path, i))
                    break
            
            # Class patterns
            if re.search(r'\bclass\s+(\w+)', line):
                match = re.search(r'\bclass\s+(\w+)', line)
                if match:
                    symbols.append(Symbol(match.group(1), 'class', file_path, i))
        
        return symbols
    
    def get_relevant_files(
        self,
        query: str,
        max_files: int = 10,
        include_imports: bool = True
    ) -> List[FileInfo]:
        """
        Get files most relevant to a query.
        
        Uses multiple signals:
        1. File path contains query terms
        2. Symbol names match query terms
        3. Imported by other relevant files
        
        Args:
            query: Natural language query
            max_files: Maximum files to return
            include_imports: Include files imported by matches
            
        Returns:
            List of FileInfo ordered by relevance
        """
        # Ensure we have a map
        self.scan()
        
        # Extract search terms
        terms = self._extract_terms(query)
        
        if not terms:
            return []
        
        # Score each file
        scored: Dict[str, float] = {}
        
        for path, info in self.files.items():
            score = 0.0
            
            # Path matching
            path_lower = path.lower()
            for term in terms:
                if term in path_lower:
                    score += 0.5
                    if term in Path(path).stem.lower():
                        score += 0.3  # Filename match is stronger
            
            # Symbol matching
            for sym in info.symbols:
                name_lower = sym.name.lower()
                for term in terms:
                    if term in name_lower:
                        score += 0.3
                        if name_lower == term:
                            score += 0.2  # Exact match bonus
            
            if score > 0:
                scored[path] = score
        
        # Add imported files if requested
        if include_imports:
            additions = {}
            for path in list(scored.keys()):
                info = self.files.get(path)
                if info:
                    for imp in info.imports:
                        # Find files that might provide this import
                        for other_path, other_info in self.files.items():
                            if other_path in scored:
                                continue
                            if imp in other_path or any(imp in sym.name.lower() for sym in other_info.symbols):
                                additions[other_path] = 0.2  # Lower score for imported
            scored.update(additions)
        
        # Sort by score and return
        sorted_files = sorted(scored.items(), key=lambda x: x[1], reverse=True)
        
        return [self.files[path] for path, _ in sorted_files[:max_files]]
    
    def _extract_terms(self, query: str) -> List[str]:
        """Extract meaningful terms from a query"""
        # Lowercase and split
        words = re.findall(r'\b\w+\b', query.lower())
        
        # Filter common words
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'can', 'this',
            'that', 'it', 'to', 'of', 'in', 'for', 'on', 'with', 'at',
            'by', 'from', 'as', 'or', 'and', 'but', 'not', 'what', 'how',
            'why', 'where', 'when', 'which', 'who', 'file', 'code', 'fix',
            'add', 'change', 'update', 'modify', 'create', 'edit'
        }
        
        terms = [w for w in words if w not in stop_words and len(w) >= 2]
        
        # Also try to identify specific patterns
        # CamelCase: vLLMClient -> vllm, client
        for word in query.split():
            camel = re.findall(r'[A-Z][a-z]+', word)
            terms.extend([c.lower() for c in camel])
        
        # snake_case: some_function -> some, function
        for word in query.split():
            if '_' in word:
                terms.extend(word.lower().split('_'))
        
        return list(set(terms))
    
    def find_symbol(self, name: str) -> List[Symbol]:
        """Find all symbols with a given name"""
        self.scan()
        
        results = []
        name_lower = name.lower()
        
        for sym_name, syms in self.symbols.items():
            if name_lower in sym_name.lower():
                results.extend(syms)
        
        return results
    
    def get_file_info(self, path: str) -> Optional[FileInfo]:
        """Get info about a specific file"""
        self.scan()
        return self.files.get(path)
    
    def get_summary(self, max_files: int = 50, max_symbols_per_file: int = 10) -> str:
        """Get a compact text summary of the repository"""
        self.scan()
        
        lines = [f"# Repository: {self.root.name}"]
        lines.append(f"Total files: {len(self.files)}, Total symbols: {sum(len(s) for s in self.symbols.values())}")
        lines.append("")
        
        # Sort files by symbol count (most important first)
        sorted_files = sorted(
            self.files.values(),
            key=lambda f: len(f.symbols),
            reverse=True
        )
        
        for info in sorted_files[:max_files]:
            lines.append(info.get_summary(max_symbols_per_file))
        
        return '\n'.join(lines)


# Global instance
_repo_map: Optional[RepoMap] = None


def get_repo_map(root: str = ".") -> RepoMap:
    """Get or create the global repo map"""
    global _repo_map
    if _repo_map is None or str(_repo_map.root) != str(Path(root).resolve()):
        _repo_map = RepoMap(root)
    return _repo_map
