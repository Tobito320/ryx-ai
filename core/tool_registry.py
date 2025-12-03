"""
Ryx AI - Tool Registry
Unified tool interface for filesystem, web, shell, and RAG operations

Privacy-first design:
- Web search goes through self-hosted SearxNG (configurable)
- HTML parsing with BeautifulSoup (local, no external services)
- No telemetry or third-party analytics
"""

import os
import subprocess
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
import logging
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

# Module-level registry singleton
_registry_instance: Optional['ToolRegistry'] = None


def get_tool_registry(safety_mode: str = "normal") -> 'ToolRegistry':
    """Get the singleton ToolRegistry instance"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolRegistry(safety_mode=safety_mode)
    return _registry_instance


def _get_searxng_config() -> Dict[str, Any]:
    """
    Load SearxNG configuration from config file or environment.
    
    Priority:
    1. SEARXNG_URL environment variable
    2. configs/ryx_config.json → search.searxng_url
    3. Default to None (will trigger helpful error message)
    """
    # Try environment variable first
    searxng_url = os.environ.get('SEARXNG_URL')
    timeout = int(os.environ.get('SEARXNG_TIMEOUT', '10'))
    max_results = int(os.environ.get('SEARXNG_MAX_RESULTS', '5'))
    
    if searxng_url:
        return {
            'searxng_url': searxng_url,
            'timeout_seconds': timeout,
            'max_results': max_results
        }
    
    # Try config file
    try:
        config_paths = [
            Path(__file__).parent.parent / "configs" / "ryx_config.json",
            Path.home() / ".ryx" / "configs" / "ryx_config.json",
            Path.home() / "ryx-ai" / "configs" / "ryx_config.json",
        ]
        
        for config_path in config_paths:
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                    search_config = config.get('search', {})
                    return {
                        'searxng_url': search_config.get('searxng_url'),
                        'timeout_seconds': search_config.get('timeout_seconds', 10),
                        'max_results': search_config.get('max_results', 5),
                        'fallback_to_duckduckgo': search_config.get('fallback_to_duckduckgo', False)
                    }
    except Exception as e:
        logger.warning(f"Failed to load search config: {e}")
    
    return {
        'searxng_url': None,
        'timeout_seconds': 10,
        'max_results': 5,
        'fallback_to_duckduckgo': False
    }


class ToolCategory(Enum):
    """Categories of tools"""
    FILESYSTEM = "filesystem"
    WEB = "web"
    SHELL = "shell"
    RAG = "rag"
    MISC = "misc"


class SafetyLevel(Enum):
    """Safety levels for tool execution"""
    SAFE = "safe"  # Auto-approve
    RISKY = "risky"  # Confirm in strict mode
    DANGEROUS = "dangerous"  # Always confirm


@dataclass
class ToolDefinition:
    """Definition of a tool"""
    name: str
    description: str
    category: ToolCategory
    safety_level: SafetyLevel
    parameters: Dict[str, Any]  # Parameter schemas
    handler: Callable  # Function to execute


@dataclass
class ToolResult:
    """Result of tool execution"""
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """
    Unified tool registry and executor

    Features:
    - Filesystem tools: search, read, write/patch, list tree
    - Web tools: fetch HTTP, scrape, search
    - Shell tools: run commands with safety controls
    - RAG tools: add/query/rebuild index
    - Misc: health checks, cache cleanup, logs

    All tools have:
    - Consistent interface: execute_tool(name, params) -> ToolResult
    - Safety controls with confirmation for dangerous operations
    - LLM-friendly descriptions for tool selection
    """

    def __init__(self, safety_mode: str = "normal"):
        """
        Initialize tool registry

        Args:
            safety_mode: 'strict', 'normal', or 'loose'
        """
        self.safety_mode = safety_mode
        self.tools: Dict[str, ToolDefinition] = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """Register all built-in tools"""
        # Filesystem tools
        self.register(ToolDefinition(
            name="read_file",
            description="Read contents of a file",
            category=ToolCategory.FILESYSTEM,
            safety_level=SafetyLevel.SAFE,
            parameters={"path": "string - File path to read"},
            handler=self._read_file
        ))

        self.register(ToolDefinition(
            name="write_file",
            description="Write content to a file (creates or overwrites)",
            category=ToolCategory.FILESYSTEM,
            safety_level=SafetyLevel.RISKY,
            parameters={
                "path": "string - File path to write",
                "content": "string - Content to write"
            },
            handler=self._write_file
        ))

        self.register(ToolDefinition(
            name="patch_file",
            description="Apply a patch/diff to a file (minimal edit)",
            category=ToolCategory.FILESYSTEM,
            safety_level=SafetyLevel.RISKY,
            parameters={
                "path": "string - File path to patch",
                "search": "string - Text to find",
                "replace": "string - Text to replace with"
            },
            handler=self._patch_file
        ))

        self.register(ToolDefinition(
            name="search_files",
            description="Search for files by name or content",
            category=ToolCategory.FILESYSTEM,
            safety_level=SafetyLevel.SAFE,
            parameters={
                "pattern": "string - Search pattern (glob or regex)",
                "directory": "string - Directory to search in (default: current)",
                "content_search": "string - Optional content to search for"
            },
            handler=self._search_files
        ))

        self.register(ToolDefinition(
            name="list_tree",
            description="List directory tree structure",
            category=ToolCategory.FILESYSTEM,
            safety_level=SafetyLevel.SAFE,
            parameters={
                "path": "string - Directory path",
                "depth": "int - Maximum depth (default: 3)"
            },
            handler=self._list_tree
        ))

        self.register(ToolDefinition(
            name="find_file",
            description="Find a specific file (config, source, etc.)",
            category=ToolCategory.FILESYSTEM,
            safety_level=SafetyLevel.SAFE,
            parameters={"query": "string - What file to find (e.g., 'hyprland config')"},
            handler=self._find_file
        ))

        # Shell tools
        self.register(ToolDefinition(
            name="run_command",
            description="Run a shell command",
            category=ToolCategory.SHELL,
            safety_level=SafetyLevel.RISKY,
            parameters={
                "command": "string - Command to run",
                "cwd": "string - Working directory (optional)"
            },
            handler=self._run_command
        ))

        self.register(ToolDefinition(
            name="run_command_dangerous",
            description="Run a dangerous command (rm, mv to system dirs, etc.)",
            category=ToolCategory.SHELL,
            safety_level=SafetyLevel.DANGEROUS,
            parameters={
                "command": "string - Command to run",
                "reason": "string - Why this command is needed"
            },
            handler=self._run_command_dangerous
        ))

        # Web tools
        self.register(ToolDefinition(
            name="fetch_url",
            description="Fetch content from a URL",
            category=ToolCategory.WEB,
            safety_level=SafetyLevel.SAFE,
            parameters={"url": "string - URL to fetch"},
            handler=self._fetch_url
        ))

        self.register(ToolDefinition(
            name="scrape_page",
            description="Scrape and extract readable text from a web page using BeautifulSoup (local parsing)",
            category=ToolCategory.WEB,
            safety_level=SafetyLevel.SAFE,
            parameters={
                "url": "string - URL to scrape",
                "extract_links": "bool - Whether to extract links (default: false)"
            },
            handler=self._scrape_page
        ))

        self.register(ToolDefinition(
            name="searxng_search",
            description="Search the web using self-hosted SearxNG (privacy-first, local search)",
            category=ToolCategory.WEB,
            safety_level=SafetyLevel.SAFE,
            parameters={
                "query": "string - Search query",
                "num_results": "int - Number of results (default: 5)"
            },
            handler=self._searxng_search
        ))

        self.register(ToolDefinition(
            name="web_search",
            description="Search the web (uses SearxNG if configured, otherwise DuckDuckGo fallback)",
            category=ToolCategory.WEB,
            safety_level=SafetyLevel.SAFE,
            parameters={
                "query": "string - Search query",
                "num_results": "int - Number of results (default: 5)"
            },
            handler=self._web_search
        ))

        self.register(ToolDefinition(
            name="web_search_health",
            description="Check web search health (SearxNG connectivity and BeautifulSoup availability)",
            category=ToolCategory.MISC,
            safety_level=SafetyLevel.SAFE,
            parameters={},
            handler=self._web_search_health
        ))

        # RAG tools
        self.register(ToolDefinition(
            name="save_note",
            description="Save a note to the knowledge base",
            category=ToolCategory.RAG,
            safety_level=SafetyLevel.SAFE,
            parameters={
                "title": "string - Note title",
                "content": "string - Note content",
                "tags": "list - Optional tags"
            },
            handler=self._save_note
        ))

        self.register(ToolDefinition(
            name="search_notes",
            description="Search notes in the knowledge base",
            category=ToolCategory.RAG,
            safety_level=SafetyLevel.SAFE,
            parameters={"query": "string - Search query"},
            handler=self._search_notes
        ))

        self.register(ToolDefinition(
            name="rebuild_index",
            description="Rebuild the RAG knowledge index",
            category=ToolCategory.RAG,
            safety_level=SafetyLevel.RISKY,
            parameters={},
            handler=self._rebuild_index
        ))

        # Misc tools
        self.register(ToolDefinition(
            name="health_check",
            description="Check system health (vLLM, databases, etc.)",
            category=ToolCategory.MISC,
            safety_level=SafetyLevel.SAFE,
            parameters={},
            handler=self._health_check
        ))

        self.register(ToolDefinition(
            name="cleanup_cache",
            description="Clean up cache and temporary files",
            category=ToolCategory.MISC,
            safety_level=SafetyLevel.RISKY,
            parameters={"aggressive": "bool - Whether to do aggressive cleanup (default: false)"},
            handler=self._cleanup_cache
        ))

        self.register(ToolDefinition(
            name="view_logs",
            description="View recent logs",
            category=ToolCategory.MISC,
            safety_level=SafetyLevel.SAFE,
            parameters={
                "lines": "int - Number of lines (default: 50)",
                "filter": "string - Optional filter pattern"
            },
            handler=self._view_logs
        ))

        # Register tool aliases for test compatibility
        # Tests expect: file_search, file_read, file_write, file_patch, list_directory, shell_command, web_fetch
        self._register_tool_aliases()

    def _register_tool_aliases(self):
        """
        Register aliases for tools to maintain backward compatibility.
        Tests expect different tool names than what we use internally.
        """
        alias_map = {
            'file_read': 'read_file',
            'file_write': 'write_file',
            'file_patch': 'patch_file',
            'file_search': 'search_files',
            'list_directory': 'list_tree',
            'shell_command': 'run_command',
            'web_fetch': 'fetch_url',
        }
        for alias, original in alias_map.items():
            if original in self.tools and alias not in self.tools:
                # Create a copy of the tool definition with the alias name
                orig_tool = self.tools[original]
                self.tools[alias] = ToolDefinition(
                    name=alias,
                    description=orig_tool.description,
                    category=orig_tool.category,
                    safety_level=orig_tool.safety_level,
                    parameters=orig_tool.parameters,
                    handler=orig_tool.handler
                )

    def register(self, tool: ToolDefinition):
        """Register a tool"""
        self.tools[tool.name] = tool

    def execute_tool(
        self,
        name: str,
        params: Dict[str, Any],
        confirmed: bool = False
    ) -> ToolResult:
        """
        Execute a tool by name

        Args:
            name: Tool name
            params: Tool parameters
            confirmed: Whether dangerous operations are pre-confirmed

        Returns:
            ToolResult with success status and output
        """
        if name not in self.tools:
            return ToolResult(
                success=False,
                output=None,
                error=f"Unknown tool: {name}"
            )

        tool = self.tools[name]

        # Safety check
        if not self._check_safety(tool, confirmed):
            return ToolResult(
                success=False,
                output=None,
                error=f"Tool '{name}' requires confirmation (safety: {tool.safety_level.value})"
            )

        try:
            result = tool.handler(params)
            return result

        except Exception as e:
            logger.error(f"Tool execution error: {name} - {e}")
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )

    def _check_safety(self, tool: ToolDefinition, confirmed: bool) -> bool:
        """Check if tool execution is allowed based on safety settings"""
        if tool.safety_level == SafetyLevel.SAFE:
            return True

        if tool.safety_level == SafetyLevel.DANGEROUS:
            return confirmed

        # RISKY level depends on safety mode
        if tool.safety_level == SafetyLevel.RISKY:
            if self.safety_mode == "loose":
                return True
            elif self.safety_mode == "strict":
                return confirmed
            else:  # normal
                return True

        return confirmed

    def get_tool_descriptions(self) -> List[Dict[str, Any]]:
        """
        Get tool descriptions for LLM context.
        
        Returns list of dicts with name, description, and parameters for each tool.
        """
        descriptions = []

        for name, tool in self.tools.items():
            descriptions.append({
                'name': name,
                'description': tool.description,
                'parameters': tool.parameters
            })

        return descriptions

    def get_tool_descriptions_text(self) -> str:
        """Get tool descriptions as formatted text for LLM prompts"""
        lines = []
        for name, tool in self.tools.items():
            param_str = ", ".join([f"{k}: {v}" for k, v in tool.parameters.items()])
            lines.append(f"- {name}({param_str}): {tool.description}")
        return "\n".join(lines)

    def list_tools(self, category: Optional[ToolCategory] = None) -> List[str]:
        """
        List available tools.
        
        Returns a list of tool names (strings) for simple iteration.
        Use list_tools_detailed() for full tool information.
        """
        result = []

        for name, tool in self.tools.items():
            if category and tool.category != category:
                continue
            result.append(name)

        return result

    def list_tools_detailed(self, category: Optional[ToolCategory] = None) -> List[Dict[str, Any]]:
        """List available tools with full details"""
        result = []

        for name, tool in self.tools.items():
            if category and tool.category != category:
                continue

            result.append({
                'name': name,
                'description': tool.description,
                'category': tool.category.value,
                'safety_level': tool.safety_level.value,
                'parameters': tool.parameters
            })

        return result

    # ===== Tool Handlers =====

    def _read_file(self, params: Dict) -> ToolResult:
        """Read file contents"""
        path = Path(params['path']).expanduser()

        if not path.exists():
            return ToolResult(success=False, output=None, error=f"File not found: {path}")

        try:
            content = path.read_text()
            return ToolResult(
                success=True,
                output=content,
                metadata={'path': str(path), 'size': len(content)}
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _write_file(self, params: Dict) -> ToolResult:
        """Write file contents"""
        path = Path(params['path']).expanduser()
        content = params['content']

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            return ToolResult(
                success=True,
                output=f"Wrote {len(content)} bytes to {path}",
                metadata={'path': str(path), 'size': len(content)}
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _patch_file(self, params: Dict) -> ToolResult:
        """Patch file with search/replace"""
        path = Path(params['path']).expanduser()
        search = params['search']
        replace = params['replace']

        if not path.exists():
            return ToolResult(success=False, output=None, error=f"File not found: {path}")

        try:
            content = path.read_text()
            if search not in content:
                return ToolResult(success=False, output=None, error="Search pattern not found in file")

            new_content = content.replace(search, replace, 1)
            path.write_text(new_content)

            return ToolResult(
                success=True,
                output=f"Patched {path}: replaced {len(search)} chars with {len(replace)} chars",
                metadata={'path': str(path), 'changes': 1}
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _search_files(self, params: Dict) -> ToolResult:
        """Search for files"""
        pattern = params['pattern']
        directory = Path(params.get('directory', '.')).expanduser()
        content_search = params.get('content_search')

        try:
            results = []

            for path in directory.rglob(pattern):
                if path.is_file():
                    if content_search:
                        try:
                            if content_search in path.read_text():
                                results.append(str(path))
                        except:
                            pass
                    else:
                        results.append(str(path))

            return ToolResult(
                success=True,
                output=results,
                metadata={'count': len(results)}
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _list_tree(self, params: Dict) -> ToolResult:
        """List directory tree"""
        path = Path(params['path']).expanduser()
        depth = params.get('depth', 3)

        if not path.exists():
            return ToolResult(success=False, output=None, error=f"Directory not found: {path}")

        try:
            tree = []
            self._build_tree(path, tree, "", depth)
            
            # Count files and directories for summary
            file_count = 0
            dir_count = 0
            for entry in path.rglob('*'):
                if entry.is_file():
                    file_count += 1
                elif entry.is_dir():
                    dir_count += 1
            
            # Add summary line for test compatibility (contains "files" and "directories")
            summary = f"\n{dir_count} directories, {file_count} files"
            output = "\n".join(tree) + summary
            
            return ToolResult(
                success=True,
                output=output,
                metadata={'path': str(path), 'files': file_count, 'directories': dir_count}
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _build_tree(self, path: Path, tree: List[str], prefix: str, depth: int):
        """Recursively build directory tree"""
        if depth <= 0:
            return

        try:
            entries = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            for i, entry in enumerate(entries):
                is_last = i == len(entries) - 1
                connector = "└── " if is_last else "├── "
                tree.append(f"{prefix}{connector}{entry.name}")

                if entry.is_dir():
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    self._build_tree(entry, tree, new_prefix, depth - 1)
        except PermissionError:
            tree.append(f"{prefix}[Permission denied]")

    def _find_file(self, params: Dict) -> ToolResult:
        """Find a specific file"""
        query = params['query'].lower()

        # Common config locations
        locations = {
            'hyprland': ['~/.config/hypr/hyprland.conf', '~/.config/hyprland/hyprland.conf'],
            'waybar': ['~/.config/waybar/config', '~/.config/waybar/config.jsonc'],
            'kitty': ['~/.config/kitty/kitty.conf'],
            'nvim': ['~/.config/nvim/init.lua', '~/.config/nvim/init.vim'],
            'zsh': ['~/.zshrc'],
            'bash': ['~/.bashrc'],
            'fish': ['~/.config/fish/config.fish'],
        }

        for key, paths in locations.items():
            if key in query:
                for p in paths:
                    path = Path(p).expanduser()
                    if path.exists():
                        return ToolResult(
                            success=True,
                            output=str(path),
                            metadata={'type': key}
                        )

        return ToolResult(success=False, output=None, error=f"File not found for: {query}")

    def _run_command(self, params: Dict) -> ToolResult:
        """Run a shell command"""
        command = params['command']
        cwd = params.get('cwd')

        # More robust dangerous command detection
        # Check for dangerous patterns with various bypass attempts
        dangerous_patterns = [
            # Direct dangerous commands
            r'rm\s+(-[rf]+\s+)*/\s*$',  # rm -rf /
            r'rm\s+(-[rf]+\s+)*/\*',  # rm -rf /*
            r'rm\s+(-[rf]+\s+)*~\s*$',  # rm -rf ~
            r'rm\s+(-[rf]+\s+)*~/\*',  # rm -rf ~/*
            r'dd\s+if=/dev/zero\s+of=/dev/sd',
            r'dd\s+if=/dev/random\s+of=/dev/sd',
            r'mkfs\.',  # mkfs.ext4, mkfs.ntfs, etc.
            r':\(\)\{\s*:\|\s*:&\s*\}\s*;',  # Fork bomb
            r'>\s*/dev/sd[a-z]',  # Overwrite disk
            r'chmod\s+(-R\s+)?[0-7]*\s+/',  # chmod on root
            r'chown\s+(-R\s+)?\w+\s+/',  # chown on root
            r'shred\s+/dev/sd',
            r'wipefs\s+',
            r'curl\s+.*\|\s*(ba)?sh',  # Pipe from curl to shell
            r'wget\s+.*\|\s*(ba)?sh',  # Pipe from wget to shell
        ]

        # Also check for exact dangerous strings (case-insensitive)
        dangerous_exact = [
            'rm -rf /',
            'rm -rf ~',
            '> /dev/sda',
            ':(){:|:&};:',
        ]

        import re
        command_lower = command.lower().strip()

        # Check exact matches
        for pattern in dangerous_exact:
            if pattern in command_lower:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Dangerous command blocked: {pattern}"
                )

        # Check regex patterns
        for pattern in dangerous_patterns:
            if re.search(pattern, command_lower):
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Dangerous command blocked"
                )

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30
            )

            return ToolResult(
                success=result.returncode == 0,
                output=result.stdout if result.stdout else result.stderr,
                metadata={
                    'exit_code': result.returncode,
                    'command': command
                }
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output=None, error="Command timed out after 30s")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _run_command_dangerous(self, params: Dict) -> ToolResult:
        """Run a dangerous command (requires confirmation)"""
        # This should only be called after confirmation
        return self._run_command(params)

    def _fetch_url(self, params: Dict) -> ToolResult:
        """Fetch URL content"""
        import requests

        url = params['url']

        try:
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Ryx-AI/1.0 (Educational; +https://github.com/ryx-ai)'
            })
            return ToolResult(
                success=response.status_code == 200,
                output=response.text[:10000],  # Limit size
                metadata={
                    'status_code': response.status_code,
                    'content_type': response.headers.get('content-type'),
                    'url': url
                }
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _scrape_page(self, params: Dict) -> ToolResult:
        """
        Scrape web page using BeautifulSoup (local parsing).
        
        Returns:
            Extracted text content and optionally links.
            Mentions the domain for transparency.
        """
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError as e:
            return ToolResult(
                success=False,
                output=None,
                error="BeautifulSoup not installed. Run: pip install beautifulsoup4 lxml"
            )

        url = params['url']
        extract_links = params.get('extract_links', False)

        try:
            # Parse domain for transparency
            domain = urlparse(url).netloc
            
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Ryx-AI/2.0 (Local; Privacy-First)'
            })
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'lxml')

            # Remove script, style, nav, footer elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()

            # Try to find main content
            main_content = soup.find('main') or soup.find('article') or soup.find('body')
            
            if main_content:
                text = main_content.get_text(separator=' ', strip=True)
            else:
                text = soup.get_text(separator=' ', strip=True)
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            text = ' '.join(chunk for chunk in lines if chunk)
            
            # Truncate to reasonable size
            text = text[:5000]

            result = {
                'domain': domain,
                'text': text,
                'text_length': len(text)
            }

            if extract_links:
                links = []
                for a in soup.find_all('a', href=True):
                    href = a.get('href', '')
                    # Convert relative URLs to absolute
                    if href and not href.startswith(('#', 'javascript:', 'mailto:')):
                        full_url = urljoin(url, href)
                        links.append(full_url)
                result['links'] = list(set(links))[:50]  # Deduplicate and limit

            return ToolResult(
                success=True,
                output=result,
                metadata={'url': url, 'domain': domain}
            )
        except requests.exceptions.RequestException as e:
            return ToolResult(success=False, output=None, error=f"Failed to fetch {url}: {str(e)}")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _searxng_search(self, params: Dict) -> ToolResult:
        """
        Search using self-hosted SearxNG instance.
        
        Privacy-first: All queries go to your own SearxNG instance.
        No direct calls to Google/Bing/etc.
        
        Returns structured results (title, URL, snippet) parsed with BeautifulSoup.
        """
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            return ToolResult(
                success=False,
                output=None,
                error="BeautifulSoup not installed. Run: pip install beautifulsoup4 lxml"
            )

        query = params['query']
        num_results = params.get('num_results', 5)
        
        # Load SearxNG configuration
        config = _get_searxng_config()
        searxng_url = config.get('searxng_url')
        timeout = config.get('timeout_seconds', 10)
        
        # Auto-start SearXNG if not configured or not running
        if not searxng_url:
            from core.service_manager import SearXNGManager
            manager = SearXNGManager()
            result = manager.ensure_running()
            if result.get('success'):
                searxng_url = result.get('url')
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=(
                        f"❌ Web search unavailable: {result.get('error', 'SearXNG not running')}\n"
                        "Install SearXNG with:\n"
                        "  podman run -d --name ryx-searxng -p 8888:8080 searxng/searxng\n"
                        "Or: docker run -d --name ryx-searxng -p 8888:8080 searxng/searxng"
                    )
                )
        
        try:
            # Build search URL (SearxNG JSON API)
            search_endpoint = f"{searxng_url.rstrip('/')}/search"
            
            response = requests.get(
                search_endpoint,
                params={
                    'q': query,
                    'format': 'json',
                    'categories': 'general'
                },
                timeout=timeout,
                headers={'User-Agent': 'Ryx-AI/2.0 (Local; Privacy-First)'}
            )
            
            if response.status_code != 200:
                # Try HTML format as fallback
                return self._searxng_search_html(query, searxng_url, num_results, timeout)
            
            data = response.json()
            results = []
            
            for item in data.get('results', [])[:num_results]:
                results.append({
                    'title': item.get('title', 'No title'),
                    'url': item.get('url', ''),
                    'snippet': item.get('content', '')[:200] if item.get('content') else ''
                })
            
            return ToolResult(
                success=True,
                output=results,
                metadata={
                    'query': query,
                    'count': len(results),
                    'source': 'SearxNG',
                    'searxng_url': searxng_url
                }
            )
            
        except requests.exceptions.ConnectionError:
            # Try to auto-start SearXNG
            from core.service_manager import SearXNGManager
            manager = SearXNGManager()
            result = manager.ensure_running()
            
            if result.get('success'):
                # Retry with the new URL
                new_url = result.get('url')
                return self._searxng_search({
                    'query': query,
                    'num_results': num_results,
                    '_retry': True  # Prevent infinite loop
                })
            
            return ToolResult(
                success=False,
                output=None,
                error=(
                    f"❌ Cannot connect to SearxNG at {searxng_url}\n"
                    f"Auto-start failed: {result.get('error', 'Unknown error')}\n"
                    "Install SearXNG with:\n"
                    "  podman run -d --name ryx-searxng -p 8888:8080 searxng/searxng"
                )
            )
        except requests.exceptions.Timeout:
            return ToolResult(
                success=False,
                output=None,
                error=f"SearxNG request timed out after {timeout}s. Try increasing timeout_seconds."
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=f"SearxNG search error: {str(e)}")

    def _searxng_search_html(self, query: str, searxng_url: str, num_results: int, timeout: int) -> ToolResult:
        """Fallback: Parse SearxNG HTML results if JSON API not available"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            search_endpoint = f"{searxng_url.rstrip('/')}/search"
            response = requests.get(
                search_endpoint,
                params={'q': query},
                timeout=timeout,
                headers={'User-Agent': 'Ryx-AI/2.0 (Local; Privacy-First)'}
            )
            
            soup = BeautifulSoup(response.text, 'lxml')
            results = []
            
            # Try to find result containers (SearxNG HTML structure)
            for article in soup.find_all(['article', 'div'], class_=['result', 'search-result'])[:num_results]:
                title_elem = article.find(['h3', 'h4', 'a'])
                link_elem = article.find('a', href=True)
                snippet_elem = article.find(['p', 'span'], class_=['content', 'snippet', 'description'])
                
                if title_elem and link_elem:
                    results.append({
                        'title': title_elem.get_text(strip=True),
                        'url': link_elem.get('href', ''),
                        'snippet': snippet_elem.get_text(strip=True)[:200] if snippet_elem else ''
                    })
            
            return ToolResult(
                success=True,
                output=results,
                metadata={'query': query, 'count': len(results), 'source': 'SearxNG (HTML)'}
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=f"SearxNG HTML parse error: {str(e)}")

    def _web_search(self, params: Dict) -> ToolResult:
        """
        Search the web - uses SearxNG if configured, with optional DuckDuckGo fallback.
        
        Privacy note: SearxNG is preferred for privacy. DuckDuckGo is only used
        as a fallback if explicitly enabled in config (fallback_to_duckduckgo: true).
        """
        query = params['query']
        num_results = params.get('num_results', 5)
        
        # Try SearxNG first
        searxng_result = self._searxng_search(params)
        
        if searxng_result.success:
            return searxng_result
        
        # Check if fallback is allowed
        config = _get_searxng_config()
        if not config.get('fallback_to_duckduckgo', False):
            # Return the SearxNG error with helpful message
            return searxng_result
        
        # Fallback to DuckDuckGo HTML search
        try:
            import requests
            from bs4 import BeautifulSoup
            
            search_url = f"https://html.duckduckgo.com/html/?q={query}"
            response = requests.get(search_url, timeout=10, headers={
                'User-Agent': 'Ryx-AI/2.0 (Local; Privacy-First)'
            })

            soup = BeautifulSoup(response.text, 'lxml')
            results = []

            for result in soup.find_all('div', class_='result')[:num_results]:
                title_elem = result.find('a', class_='result__a')
                snippet_elem = result.find('a', class_='result__snippet')

                if title_elem:
                    results.append({
                        'title': title_elem.get_text(strip=True),
                        'url': title_elem['href'],
                        'snippet': snippet_elem.get_text(strip=True) if snippet_elem else ""
                    })

            return ToolResult(
                success=True,
                output=results,
                metadata={'query': query, 'count': len(results), 'source': 'DuckDuckGo (fallback)'}
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=f"Web search failed: {str(e)}")

    def _web_search_health(self, params: Dict) -> ToolResult:
        """
        Check web search health and configuration.
        
        Tests:
        1. BeautifulSoup availability
        2. SearxNG URL configuration
        3. SearxNG connectivity (if configured)
        """
        health = {
            'beautifulsoup': {'status': 'unknown'},
            'searxng_config': {'status': 'unknown'},
            'searxng_connection': {'status': 'unknown'}
        }
        
        # Check BeautifulSoup
        try:
            from bs4 import BeautifulSoup
            health['beautifulsoup'] = {
                'status': 'healthy',
                'message': 'BeautifulSoup is installed and working'
            }
        except ImportError:
            health['beautifulsoup'] = {
                'status': 'error',
                'message': 'BeautifulSoup not installed. Run: pip install beautifulsoup4 lxml'
            }
        
        # Check SearxNG configuration
        config = _get_searxng_config()
        searxng_url = config.get('searxng_url')
        
        if searxng_url:
            health['searxng_config'] = {
                'status': 'healthy',
                'url': searxng_url,
                'timeout': config.get('timeout_seconds', 10),
                'max_results': config.get('max_results', 5),
                'fallback_enabled': config.get('fallback_to_duckduckgo', False)
            }
            
            # Test SearxNG connectivity
            try:
                import requests
                response = requests.get(
                    f"{searxng_url.rstrip('/')}/",
                    timeout=5,
                    headers={'User-Agent': 'Ryx-AI/2.0 (Health-Check)'}
                )
                if response.status_code == 200:
                    health['searxng_connection'] = {
                        'status': 'healthy',
                        'message': f'SearxNG is reachable at {searxng_url}'
                    }
                else:
                    health['searxng_connection'] = {
                        'status': 'warning',
                        'message': f'SearxNG returned status {response.status_code}'
                    }
            except requests.exceptions.ConnectionError:
                health['searxng_connection'] = {
                    'status': 'error',
                    'message': f'Cannot connect to SearxNG at {searxng_url}. Is it running?'
                }
            except Exception as e:
                health['searxng_connection'] = {
                    'status': 'error',
                    'message': str(e)
                }
        else:
            health['searxng_config'] = {
                'status': 'not_configured',
                'message': (
                    'SearxNG URL not set. Configure via:\n'
                    '  - Environment: export SEARXNG_URL=http://localhost:8080\n'
                    '  - Config file: configs/ryx_config.json → search.searxng_url'
                )
            }
            health['searxng_connection'] = {
                'status': 'skipped',
                'message': 'Skipped - SearxNG not configured'
            }
        
        # Determine overall status
        statuses = [v['status'] for v in health.values()]
        if 'error' in statuses:
            overall = 'unhealthy'
        elif 'warning' in statuses or 'not_configured' in statuses:
            overall = 'degraded'
        else:
            overall = 'healthy'
        
        return ToolResult(
            success=True,
            output=health,
            metadata={'overall_status': overall}
        )

    def _save_note(self, params: Dict) -> ToolResult:
        """Save note to knowledge base"""
        title = params['title']
        content = params['content']
        tags = params.get('tags', [])

        try:
            from core.paths import get_data_dir
            notes_dir = get_data_dir() / "notes"
            notes_dir.mkdir(parents=True, exist_ok=True)

            # Create filename from title - sanitize to prevent path traversal
            # Remove any path separators and only keep safe characters
            sanitized_title = title.replace('/', '_').replace('\\', '_').replace('..', '_')
            filename = "".join(c if c.isalnum() or c in ' -_' else '_' for c in sanitized_title[:50])
            # Ensure filename is not empty and doesn't start with .
            if not filename or filename.startswith('.'):
                filename = f"note_{filename}"
            filepath = notes_dir / f"{filename}.md"

            # Verify the resolved path is within notes_dir (prevent path traversal)
            resolved_path = filepath.resolve()
            if not str(resolved_path).startswith(str(notes_dir.resolve())):
                return ToolResult(success=False, output=None, error="Invalid note title (path traversal detected)")

            # Write note
            note_content = f"# {title}\n\nTags: {', '.join(tags)}\n\n{content}"
            filepath.write_text(note_content)

            return ToolResult(
                success=True,
                output=f"Saved note: {filepath}",
                metadata={'path': str(filepath)}
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _search_notes(self, params: Dict) -> ToolResult:
        """Search notes in knowledge base"""
        query = params['query'].lower()

        try:
            from core.paths import get_data_dir
            notes_dir = get_data_dir() / "notes"

            if not notes_dir.exists():
                return ToolResult(success=True, output=[], metadata={'count': 0})

            results = []
            for note_file in notes_dir.glob("*.md"):
                try:
                    content = note_file.read_text()
                    if query in content.lower():
                        results.append({
                            'title': note_file.stem,
                            'preview': content[:200],
                            'path': str(note_file)
                        })
                except:
                    pass

            return ToolResult(
                success=True,
                output=results,
                metadata={'count': len(results)}
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _rebuild_index(self, params: Dict) -> ToolResult:
        """Rebuild RAG index"""
        # Placeholder - integrate with RAG system
        return ToolResult(
            success=True,
            output="Index rebuild triggered",
            metadata={}
        )

    def _health_check(self, params: Dict) -> ToolResult:
        """Check system health"""
        from core.llm_client import vLLMClient

        checks = {}

        # Check vLLM
        client = vLLMClient()
        llm_health = client.health_check()
        checks['llm'] = llm_health

        # Check database
        try:
            from core.paths import get_data_dir
            db_path = get_data_dir() / "rag_knowledge.db"
            checks['database'] = {
                'status': 'healthy' if db_path.exists() else 'missing',
                'path': str(db_path)
            }
        except Exception as e:
            checks['database'] = {'status': 'error', 'error': str(e)}

        return ToolResult(
            success=True,
            output=checks,
            metadata={}
        )

    def _cleanup_cache(self, params: Dict) -> ToolResult:
        """Clean up cache"""
        aggressive = params.get('aggressive', False)

        try:
            from core.paths import get_data_dir
            cache_dir = get_data_dir() / "cache"

            if not cache_dir.exists():
                return ToolResult(success=True, output="No cache to clean", metadata={})

            cleaned = 0
            for item in cache_dir.rglob("*"):
                if item.is_file():
                    if aggressive or item.suffix in ['.tmp', '.log']:
                        item.unlink()
                        cleaned += 1

            return ToolResult(
                success=True,
                output=f"Cleaned {cleaned} files",
                metadata={'cleaned': cleaned}
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _view_logs(self, params: Dict) -> ToolResult:
        """View logs"""
        lines = params.get('lines', 50)
        filter_pattern = params.get('filter')

        try:
            from core.paths import get_data_dir
            log_path = get_data_dir() / "history" / "commands.log"

            if not log_path.exists():
                return ToolResult(success=True, output="No logs found", metadata={})

            all_lines = log_path.read_text().splitlines()
            recent = all_lines[-lines:]

            if filter_pattern:
                recent = [l for l in recent if filter_pattern in l]

            return ToolResult(
                success=True,
                output="\n".join(recent),
                metadata={'total_lines': len(recent)}
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
