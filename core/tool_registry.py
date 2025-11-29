"""
Ryx AI - Tool Registry
Unified tool interface for filesystem, web, shell, and RAG operations
"""

import os
import subprocess
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


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
            description="Scrape and extract text from a web page",
            category=ToolCategory.WEB,
            safety_level=SafetyLevel.SAFE,
            parameters={
                "url": "string - URL to scrape",
                "extract_links": "bool - Whether to extract links (default: false)"
            },
            handler=self._scrape_page
        ))

        self.register(ToolDefinition(
            name="web_search",
            description="Search the web using DuckDuckGo",
            category=ToolCategory.WEB,
            safety_level=SafetyLevel.SAFE,
            parameters={
                "query": "string - Search query",
                "num_results": "int - Number of results (default: 5)"
            },
            handler=self._web_search
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
            description="Check system health (Ollama, databases, etc.)",
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

    def get_tool_descriptions(self) -> str:
        """Get tool descriptions for LLM context"""
        descriptions = []

        for name, tool in self.tools.items():
            param_str = ", ".join([f"{k}: {v}" for k, v in tool.parameters.items()])
            descriptions.append(
                f"- {name}({param_str}): {tool.description}"
            )

        return "\n".join(descriptions)

    def list_tools(self, category: Optional[ToolCategory] = None) -> List[Dict[str, Any]]:
        """List available tools"""
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
            return ToolResult(
                success=True,
                output="\n".join(tree),
                metadata={'path': str(path)}
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

        # Check for dangerous patterns
        dangerous = ['rm -rf /', 'dd if=', 'mkfs', ':(){:|:&};:', '> /dev/sd']
        for pattern in dangerous:
            if pattern in command:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Dangerous command blocked: {pattern}"
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
        """Scrape web page"""
        import requests
        from bs4 import BeautifulSoup

        url = params['url']
        extract_links = params.get('extract_links', False)

        try:
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Ryx-AI/1.0 (Educational; +https://github.com/ryx-ai)'
            })

            soup = BeautifulSoup(response.text, 'lxml')

            # Remove script and style
            for script in soup(["script", "style"]):
                script.decompose()

            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            text = ' '.join(chunk for chunk in lines if chunk)

            result = {'text': text[:5000]}

            if extract_links:
                links = [a.get('href') for a in soup.find_all('a', href=True)]
                result['links'] = links[:50]

            return ToolResult(
                success=True,
                output=result,
                metadata={'url': url}
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _web_search(self, params: Dict) -> ToolResult:
        """Search the web"""
        import requests
        from bs4 import BeautifulSoup

        query = params['query']
        num_results = params.get('num_results', 5)

        try:
            search_url = f"https://html.duckduckgo.com/html/?q={query}"
            response = requests.get(search_url, timeout=10, headers={
                'User-Agent': 'Ryx-AI/1.0 (Educational; +https://github.com/ryx-ai)'
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
                metadata={'query': query, 'count': len(results)}
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _save_note(self, params: Dict) -> ToolResult:
        """Save note to knowledge base"""
        title = params['title']
        content = params['content']
        tags = params.get('tags', [])

        try:
            from core.paths import get_data_dir
            notes_dir = get_data_dir() / "notes"
            notes_dir.mkdir(parents=True, exist_ok=True)

            # Create filename from title
            filename = "".join(c if c.isalnum() or c in ' -_' else '_' for c in title[:50])
            filepath = notes_dir / f"{filename}.md"

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
        from core.ollama_client import OllamaClient

        checks = {}

        # Check Ollama
        client = OllamaClient()
        ollama_health = client.health_check()
        checks['ollama'] = ollama_health

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
