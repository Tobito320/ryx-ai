"""
Ryx AI - Tool Registry
Unified interface for all tools available to the agent
"""

import os
import re
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

# Optional imports with fallback
try:
    import requests
    from bs4 import BeautifulSoup
    WEB_TOOLS_AVAILABLE = True
except ImportError:
    WEB_TOOLS_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class ToolCategory(Enum):
    """Categories of tools"""
    FILESYSTEM = "filesystem"
    WEB = "web"
    SHELL = "shell"
    RAG = "rag"
    GIT = "git"
    SYSTEM = "system"


class SafetyLevel(Enum):
    """Safety levels for tool execution"""
    SAFE = "safe"          # Auto-execute
    RISKY = "risky"        # Warn user
    DANGEROUS = "dangerous" # Require confirmation


@dataclass
class ToolResult:
    """Result from tool execution"""
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolDefinition:
    """Definition of a tool for LLM exposure"""
    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, Any]  # JSON Schema format
    safety_level: SafetyLevel = SafetyLevel.SAFE
    examples: List[str] = field(default_factory=list)


class BaseTool(ABC):
    """Base class for all tools"""
    
    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return tool definition"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        pass


# ============================================
# Filesystem Tools
# ============================================

class FileSearchTool(BaseTool):
    """Search for files by name or pattern"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_search",
            description="Search for files by name or pattern",
            category=ToolCategory.FILESYSTEM,
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern (supports wildcards)"},
                    "path": {"type": "string", "description": "Starting path (default: current dir)"},
                    "max_depth": {"type": "integer", "description": "Max depth to search"}
                },
                "required": ["pattern"]
            },
            examples=["file_search(pattern='*.py')", "file_search(pattern='config', path='~/.config')"]
        )
    
    def execute(self, pattern: str, path: str = ".", max_depth: int = 5) -> ToolResult:
        try:
            path = os.path.expanduser(path)
            results = []
            
            for root, dirs, files in os.walk(path):
                # Check depth
                depth = root[len(path):].count(os.sep)
                if depth >= max_depth:
                    dirs.clear()
                    continue
                
                for name in files + dirs:
                    if self._matches_pattern(name, pattern):
                        results.append(os.path.join(root, name))
            
            return ToolResult(success=True, output=results[:100])  # Limit results
        except Exception as e:
            return ToolResult(success=False, output=[], error=str(e))
    
    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if name matches pattern (simple wildcard support)"""
        import fnmatch
        return fnmatch.fnmatch(name.lower(), pattern.lower())


class FileReadTool(BaseTool):
    """Read contents of a file"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_read",
            description="Read the contents of a file",
            category=ToolCategory.FILESYSTEM,
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to file"},
                    "lines": {"type": "integer", "description": "Number of lines to read (default: all)"}
                },
                "required": ["path"]
            }
        )
    
    def execute(self, path: str, lines: Optional[int] = None) -> ToolResult:
        try:
            path = os.path.expanduser(path)
            with open(path, 'r') as f:
                if lines:
                    content = ''.join(f.readlines()[:lines])
                else:
                    content = f.read()
            
            return ToolResult(success=True, output=content, metadata={"path": path, "size": len(content)})
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class FileWriteTool(BaseTool):
    """Write content to a file (create or overwrite)"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_write",
            description="Write content to a file",
            category=ToolCategory.FILESYSTEM,
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to file"},
                    "content": {"type": "string", "description": "Content to write"},
                    "append": {"type": "boolean", "description": "Append instead of overwrite"}
                },
                "required": ["path", "content"]
            },
            safety_level=SafetyLevel.RISKY
        )
    
    def execute(self, path: str, content: str, append: bool = False) -> ToolResult:
        try:
            path = os.path.expanduser(path)
            mode = 'a' if append else 'w'
            
            # Create directory if needed (only if dirname is not empty)
            dirname = os.path.dirname(path)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            
            with open(path, mode) as f:
                f.write(content)
            
            return ToolResult(success=True, output=f"Written to {path}", metadata={"path": path})
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class FilePatchTool(BaseTool):
    """Apply a patch/diff to a file (minimal edits)"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_patch",
            description="Apply minimal edits to a file (search and replace)",
            category=ToolCategory.FILESYSTEM,
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to file"},
                    "search": {"type": "string", "description": "Text to find"},
                    "replace": {"type": "string", "description": "Text to replace with"}
                },
                "required": ["path", "search", "replace"]
            },
            safety_level=SafetyLevel.RISKY
        )
    
    def execute(self, path: str, search: str, replace: str) -> ToolResult:
        try:
            path = os.path.expanduser(path)
            
            with open(path, 'r') as f:
                content = f.read()
            
            if search not in content:
                return ToolResult(success=False, output="", error="Search text not found in file")
            
            new_content = content.replace(search, replace, 1)
            
            with open(path, 'w') as f:
                f.write(new_content)
            
            return ToolResult(success=True, output=f"Patched {path}", metadata={"path": path})
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class ListDirectoryTool(BaseTool):
    """List contents of a directory"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="list_directory",
            description="List files and directories in a path",
            category=ToolCategory.FILESYSTEM,
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path"},
                    "show_hidden": {"type": "boolean", "description": "Show hidden files"}
                },
                "required": ["path"]
            }
        )
    
    def execute(self, path: str, show_hidden: bool = False) -> ToolResult:
        try:
            path = os.path.expanduser(path)
            entries = os.listdir(path)
            
            if not show_hidden:
                entries = [e for e in entries if not e.startswith('.')]
            
            # Categorize
            files = []
            dirs = []
            for entry in sorted(entries):
                full_path = os.path.join(path, entry)
                if os.path.isdir(full_path):
                    dirs.append(entry + '/')
                else:
                    files.append(entry)
            
            return ToolResult(success=True, output={"directories": dirs, "files": files})
        except Exception as e:
            return ToolResult(success=False, output={}, error=str(e))


# ============================================
# Shell Tools
# ============================================

class ShellCommandTool(BaseTool):
    """Execute shell commands with safety controls"""
    
    # Commands that are always blocked - never execute these
    BLOCKED_COMMANDS = [
        'rm -rf /', 'rm -rf /*', 'dd if=/dev', 'mkfs', ':(){ :|:& };:',
        'chmod -R 777 /', '> /dev/sda', 'mv /* ', 'wget | sh', 'curl | sh',
        'pacman -Syu', 'pacman -S', 'yay -S', 'systemctl enable', 'systemctl disable',
        'grub-install', 'mkinitcpio', 'bootctl', 'fdisk', 'parted', 'gparted'
    ]
    
    # Commands that require confirmation - use regex patterns
    DANGEROUS_PATTERNS = [
        r'rm\s+-rf', r'rm\s+-r', r'chmod\s+-R', r'chown\s+-R',
        r'git\s+reset\s+--hard', r'git\s+push\s+.*--force',
        r'pip\s+uninstall', r'npm\s+uninstall',
        r'pacman\s', r'yay\s', r'sudo\s', r'systemctl\s',
        r'/etc/\w+',  # Matches any /etc/ file paths
        r'>\s*/etc/', r'>>\s*/etc/',  # Redirects to /etc
        r'nano\s+/etc/', r'vim\s+/etc/', r'vi\s+/etc/',  # Editing /etc files
    ]
    
    # Safe directories (default operation areas)
    SAFE_DIRECTORIES = [
        os.path.expanduser('~'),
        '/tmp'
    ]
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="shell_command",
            description="Execute a shell command",
            category=ToolCategory.SHELL,
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default: 30)"},
                    "cwd": {"type": "string", "description": "Working directory"}
                },
                "required": ["command"]
            },
            safety_level=SafetyLevel.RISKY
        )
    
    def execute(self, command: str, timeout: int = 30, cwd: str = None) -> ToolResult:
        # Check if blocked
        command_lower = command.lower()
        for blocked in self.BLOCKED_COMMANDS:
            if blocked in command_lower:
                return ToolResult(
                    success=False, 
                    output="", 
                    error=f"Command blocked for safety: contains '{blocked}'"
                )
        
        # Check if dangerous
        safety = SafetyLevel.SAFE
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                safety = SafetyLevel.DANGEROUS
                break
        
        try:
            if cwd:
                cwd = os.path.expanduser(cwd)
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )
            
            return ToolResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                metadata={
                    "exit_code": result.returncode,
                    "safety_level": safety.value
                }
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error=f"Command timed out after {timeout}s")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


# ============================================
# Web Tools
# ============================================

class WebFetchTool(BaseTool):
    """Fetch content from a URL"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_fetch",
            description="Fetch content from a URL",
            category=ToolCategory.WEB,
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds"}
                },
                "required": ["url"]
            }
        )
    
    def execute(self, url: str, timeout: int = 30) -> ToolResult:
        if not WEB_TOOLS_AVAILABLE:
            return ToolResult(success=False, output="", error="requests library not installed")
        
        try:
            headers = {'User-Agent': 'Ryx-AI/2.0'}
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            return ToolResult(
                success=True,
                output=response.text[:50000],  # Limit size
                metadata={"url": url, "status": response.status_code, "size": len(response.text)}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class WebSearchTool(BaseTool):
    """Search the web using DuckDuckGo"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_search",
            description="Search the web for information",
            category=ToolCategory.WEB,
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {"type": "integer", "description": "Number of results (max 10)"}
                },
                "required": ["query"]
            }
        )
    
    def execute(self, query: str, num_results: int = 5) -> ToolResult:
        if not WEB_TOOLS_AVAILABLE:
            return ToolResult(success=False, output=[], error="requests/beautifulsoup4 libraries not installed")
        
        try:
            search_url = f"https://html.duckduckgo.com/html/?q={query}"
            headers = {'User-Agent': 'Ryx-AI/2.0'}
            
            response = requests.get(search_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'lxml')
            
            results = []
            for result in soup.find_all('div', class_='result')[:num_results]:
                title_elem = result.find('a', class_='result__a')
                snippet_elem = result.find('a', class_='result__snippet')
                
                if title_elem:
                    url = title_elem.get('href', '')
                    if url.startswith('//'):
                        url = 'https:' + url
                    
                    results.append({
                        'title': title_elem.get_text(strip=True),
                        'url': url,
                        'snippet': snippet_elem.get_text(strip=True) if snippet_elem else ""
                    })
            
            return ToolResult(success=True, output=results, metadata={"query": query})
        except Exception as e:
            return ToolResult(success=False, output=[], error=str(e))


class SearxNGSearchTool(BaseTool):
    """Search using SearxNG (local instance preferred)"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="searxng_search",
            description="Search using SearxNG - Tobi's preferred search backend",
            category=ToolCategory.WEB,
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {"type": "integer", "description": "Number of results (max 10)"},
                    "categories": {"type": "string", "description": "Search categories (e.g., 'general', 'images', 'it')"}
                },
                "required": ["query"]
            }
        )
    
    def execute(self, query: str, num_results: int = 5, categories: str = "general") -> ToolResult:
        if not WEB_TOOLS_AVAILABLE:
            return ToolResult(success=False, output=[], error="requests library not installed")
        
        # Try SearxNG first, fall back to DuckDuckGo
        searxng_url = os.environ.get('SEARXNG_URL', 'http://localhost:8080')
        
        try:
            # Try SearxNG JSON API
            search_url = f"{searxng_url}/search"
            params = {
                'q': query,
                'format': 'json',
                'categories': categories
            }
            
            response = requests.get(search_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get('results', [])[:num_results]:
                    results.append({
                        'title': item.get('title', ''),
                        'url': item.get('url', ''),
                        'snippet': item.get('content', '')[:200] if item.get('content') else ''
                    })
                
                return ToolResult(
                    success=True, 
                    output=results, 
                    metadata={"query": query, "source": "searxng"}
                )
        except Exception:
            pass  # Fall back to DuckDuckGo
        
        # Fallback: DuckDuckGo
        try:
            search_url = f"https://html.duckduckgo.com/html/?q={query}"
            headers = {'User-Agent': 'Ryx-AI/2.0 (Technical Partner)'}
            
            response = requests.get(search_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'lxml')
            
            results = []
            for result in soup.find_all('div', class_='result')[:num_results]:
                title_elem = result.find('a', class_='result__a')
                snippet_elem = result.find('a', class_='result__snippet')
                
                if title_elem:
                    url = title_elem.get('href', '')
                    if url.startswith('//'):
                        url = 'https:' + url
                    
                    results.append({
                        'title': title_elem.get_text(strip=True),
                        'url': url,
                        'snippet': snippet_elem.get_text(strip=True) if snippet_elem else ""
                    })
            
            return ToolResult(
                success=True, 
                output=results, 
                metadata={"query": query, "source": "duckduckgo_fallback"}
            )
        except Exception as e:
            return ToolResult(success=False, output=[], error=str(e))


# ============================================
# Git Tools
# ============================================

class GitStatusTool(BaseTool):
    """Get git status of current directory"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="git_status",
            description="Get git status of repository",
            category=ToolCategory.GIT,
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Repository path"}
                }
            }
        )
    
    def execute(self, path: str = ".") -> ToolResult:
        try:
            path = os.path.expanduser(path)
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True, text=True, cwd=path
            )
            
            return ToolResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class GitDiffTool(BaseTool):
    """Get git diff"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="git_diff",
            description="Get git diff of changes",
            category=ToolCategory.GIT,
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Repository path"},
                    "file": {"type": "string", "description": "Specific file to diff"}
                }
            }
        )
    
    def execute(self, path: str = ".", file: str = None) -> ToolResult:
        try:
            path = os.path.expanduser(path)
            cmd = ['git', 'diff']
            if file:
                cmd.append(file)
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=path)
            
            return ToolResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


# ============================================
# System Tools
# ============================================

class SystemInfoTool(BaseTool):
    """Get system information"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="system_info",
            description="Get system information (CPU, memory, disk)",
            category=ToolCategory.SYSTEM,
            parameters={"type": "object", "properties": {}}
        )
    
    def execute(self) -> ToolResult:
        if not PSUTIL_AVAILABLE:
            return ToolResult(success=False, output={}, error="psutil library not installed")
        
        try:
            info = {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory": {
                    "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                    "used_percent": psutil.virtual_memory().percent
                },
                "disk": {
                    "total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
                    "used_percent": psutil.disk_usage('/').percent
                }
            }
            
            return ToolResult(success=True, output=info)
        except Exception as e:
            return ToolResult(success=False, output={}, error=str(e))


# ============================================
# Tool Registry
# ============================================

class ToolRegistry:
    """
    Central registry for all tools
    
    Provides:
    - Tool registration and lookup
    - Uniform execute_tool interface
    - Tool descriptions for LLM exposure
    - Safety checking
    """
    
    def __init__(self):
        """Initialize registry with default tools"""
        self.tools: Dict[str, BaseTool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register all default tools"""
        default_tools = [
            FileSearchTool(),
            FileReadTool(),
            FileWriteTool(),
            FilePatchTool(),
            ListDirectoryTool(),
            ShellCommandTool(),
            WebFetchTool(),
            WebSearchTool(),
            SearxNGSearchTool(),  # SearxNG - Tobi's preferred search backend
            GitStatusTool(),
            GitDiffTool(),
            SystemInfoTool(),
        ]
        
        for tool in default_tools:
            self.register(tool)
    
    def register(self, tool: BaseTool):
        """Register a tool"""
        self.tools[tool.definition.name] = tool
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get tool by name"""
        return self.tools.get(name)
    
    def execute_tool(self, name: str, params: Dict[str, Any]) -> ToolResult:
        """
        Execute a tool by name with parameters
        
        This is the uniform interface for all tool execution
        """
        tool = self.get(name)
        if not tool:
            return ToolResult(success=False, output="", error=f"Unknown tool: {name}")
        
        try:
            return tool.execute(**params)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
    
    def get_tool_descriptions(self) -> List[Dict]:
        """Get descriptions of all tools for LLM exposure"""
        descriptions = []
        for name, tool in self.tools.items():
            defn = tool.definition
            descriptions.append({
                "name": defn.name,
                "description": defn.description,
                "category": defn.category.value,
                "parameters": defn.parameters,
                "safety_level": defn.safety_level.value,
                "examples": defn.examples
            })
        return descriptions
    
    def get_tools_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """Get all tools in a category"""
        return [t for t in self.tools.values() if t.definition.category == category]
    
    def list_tools(self) -> List[str]:
        """List all tool names"""
        return list(self.tools.keys())


# Global registry instance
_registry = None

def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
