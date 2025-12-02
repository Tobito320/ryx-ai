"""
Ryx AI - Tools Module

Powerful tools like Copilot CLI / Claude CLI:
- Shell execution with safety
- File operations (view, edit, create)
- Search (grep, glob, find)
- Web search for grounding (reduce hallucination)
- Browser control
"""

import os
import re
import subprocess
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

from core.paths import get_data_dir


@dataclass
class ToolResult:
    """Result from tool execution"""
    success: bool
    output: str
    data: Optional[Any] = None
    error: Optional[str] = None


class ShellTool:
    """
    Execute shell commands safely.
    Like Copilot CLI bash tool.
    """
    
    DANGEROUS_PATTERNS = [
        r'\brm\s+-rf\s+[/~]',  # rm -rf / or ~
        r'\brm\s+-rf\s+\*',    # rm -rf *
        r':\(\)\s*\{',         # fork bomb
        r'>\s*/dev/sd',        # write to disk
        r'mkfs\.',             # format disk
        r'dd\s+if=',           # dd command
        r'\|\s*sh\b',          # piping to shell
        r'curl.*\|\s*bash',    # curl | bash
    ]
    
    def __init__(self, safety_mode: str = "normal"):
        self.safety_mode = safety_mode
        self.history: List[Dict] = []
    
    def execute(self, command: str, timeout: int = 30, confirm: bool = None) -> ToolResult:
        """Execute a shell command"""
        
        # Safety check
        if self._is_dangerous(command):
            if self.safety_mode == "strict":
                return ToolResult(False, "", error=f"Blocked dangerous command: {command}")
            elif confirm is None:
                return ToolResult(False, "", error=f"DANGEROUS: {command}\nConfirm with confirm=True")
        
        # Normal safety check for modifying commands
        if confirm is None and self.safety_mode != "loose":
            if self._is_modifying(command):
                return ToolResult(
                    False, "",
                    error=f"This command modifies files: {command}\nConfirm with confirm=True"
                )
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd()
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr] {result.stderr}"
            
            self.history.append({
                "command": command,
                "exit_code": result.returncode,
                "timestamp": datetime.now().isoformat()
            })
            
            return ToolResult(
                success=result.returncode == 0,
                output=output.strip(),
                data={"exit_code": result.returncode}
            )
            
        except subprocess.TimeoutExpired:
            return ToolResult(False, "", error=f"Command timed out after {timeout}s")
        except Exception as e:
            return ToolResult(False, "", error=str(e))
    
    def _is_dangerous(self, cmd: str) -> bool:
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, cmd):
                return True
        return False
    
    def _is_modifying(self, cmd: str) -> bool:
        modify_commands = ['rm', 'mv', 'cp', 'chmod', 'chown', 'dd', 'mkfs', 
                          'pacman -R', 'yay -R', 'systemctl', 'kill', 'pkill']
        cmd_lower = cmd.lower()
        return any(m in cmd_lower for m in modify_commands)


class FileTool:
    """
    File operations - view, edit, create.
    Like Copilot CLI view/edit tools.
    """
    
    def view(self, path: str, lines: Optional[Tuple[int, int]] = None) -> ToolResult:
        """View file contents"""
        path = os.path.expanduser(path)
        
        if not os.path.exists(path):
            return ToolResult(False, "", error=f"File not found: {path}")
        
        if os.path.isdir(path):
            return self._view_directory(path)
        
        try:
            with open(path, 'r') as f:
                content = f.readlines()
            
            if lines:
                start, end = lines
                if end == -1:
                    end = len(content)
                content = content[start-1:end]
            
            # Add line numbers
            numbered = []
            start_line = lines[0] if lines else 1
            for i, line in enumerate(content):
                numbered.append(f"{start_line + i:4}. {line.rstrip()}")
            
            return ToolResult(True, "\n".join(numbered), data={"path": path, "lines": len(content)})
            
        except Exception as e:
            return ToolResult(False, "", error=str(e))
    
    def _view_directory(self, path: str, max_depth: int = 2) -> ToolResult:
        """View directory structure"""
        try:
            output = []
            for root, dirs, files in os.walk(path):
                level = root.replace(path, '').count(os.sep)
                if level >= max_depth:
                    dirs[:] = []  # Don't recurse further
                    continue
                
                indent = '  ' * level
                output.append(f"{indent}{os.path.basename(root)}/")
                
                subindent = '  ' * (level + 1)
                for file in sorted(files)[:20]:  # Limit files shown
                    output.append(f"{subindent}{file}")
                
                if len(files) > 20:
                    output.append(f"{subindent}... and {len(files) - 20} more files")
            
            return ToolResult(True, "\n".join(output), data={"path": path})
            
        except Exception as e:
            return ToolResult(False, "", error=str(e))
    
    def edit(self, path: str, old_str: str, new_str: str = "") -> ToolResult:
        """
        Edit file by replacing text.
        Like Copilot CLI edit tool.
        """
        path = os.path.expanduser(path)
        
        if not os.path.exists(path):
            return ToolResult(False, "", error=f"File not found: {path}")
        
        try:
            with open(path, 'r') as f:
                content = f.read()
            
            # Check if old_str exists exactly once
            count = content.count(old_str)
            if count == 0:
                return ToolResult(False, "", error=f"String not found in file")
            if count > 1:
                return ToolResult(False, "", error=f"String found {count} times - be more specific")
            
            # Replace
            new_content = content.replace(old_str, new_str, 1)
            
            # Backup
            backup_path = f"{path}.bak"
            shutil.copy(path, backup_path)
            
            # Write
            with open(path, 'w') as f:
                f.write(new_content)
            
            return ToolResult(True, f"✅ Edited: {path}", data={"backup": backup_path})
            
        except Exception as e:
            return ToolResult(False, "", error=str(e))
    
    def create(self, path: str, content: str) -> ToolResult:
        """Create a new file"""
        path = os.path.expanduser(path)
        
        if os.path.exists(path):
            return ToolResult(False, "", error=f"File already exists: {path}")
        
        try:
            # Create parent directories
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            with open(path, 'w') as f:
                f.write(content)
            
            return ToolResult(True, f"✅ Created: {path}", data={"path": path})
            
        except Exception as e:
            return ToolResult(False, "", error=str(e))


class SearchTool:
    """
    Search tools - grep, glob, find.
    Like Copilot CLI grep/glob tools.
    """
    
    def grep(self, pattern: str, path: str = ".", 
             glob_pattern: str = None, 
             case_insensitive: bool = False,
             context_lines: int = 0) -> ToolResult:
        """
        Search file contents using ripgrep.
        """
        path = os.path.expanduser(path)
        
        cmd = ["rg", "--no-heading", "--line-number"]
        
        if case_insensitive:
            cmd.append("-i")
        
        if context_lines > 0:
            cmd.extend(["-C", str(context_lines)])
        
        if glob_pattern:
            cmd.extend(["-g", glob_pattern])
        
        cmd.extend([pattern, path])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return ToolResult(True, result.stdout.strip())
            elif result.returncode == 1:
                return ToolResult(True, "No matches found")
            else:
                return ToolResult(False, "", error=result.stderr)
                
        except FileNotFoundError:
            # Fallback to grep if rg not installed
            return self._grep_fallback(pattern, path, case_insensitive)
        except Exception as e:
            return ToolResult(False, "", error=str(e))
    
    def _grep_fallback(self, pattern: str, path: str, case_insensitive: bool) -> ToolResult:
        """Fallback using grep"""
        cmd = ["grep", "-rn"]
        if case_insensitive:
            cmd.append("-i")
        cmd.extend([pattern, path])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return ToolResult(result.returncode == 0, result.stdout.strip())
        except Exception as e:
            return ToolResult(False, "", error=str(e))
    
    def glob(self, pattern: str, path: str = ".") -> ToolResult:
        """
        Find files by glob pattern.
        """
        path = os.path.expanduser(path)
        
        try:
            from pathlib import Path
            p = Path(path)
            matches = list(p.glob(pattern))
            
            if matches:
                output = "\n".join(str(m) for m in sorted(matches)[:100])
                return ToolResult(True, output, data={"count": len(matches)})
            else:
                return ToolResult(True, "No files matched")
                
        except Exception as e:
            return ToolResult(False, "", error=str(e))
    
    def find(self, name: str, path: str = "~", 
             file_type: str = None,
             max_depth: int = 5) -> ToolResult:
        """
        Find files by name.
        """
        path = os.path.expanduser(path)
        
        cmd = ["find", path, "-maxdepth", str(max_depth)]
        
        if file_type == "file":
            cmd.extend(["-type", "f"])
        elif file_type == "dir":
            cmd.extend(["-type", "d"])
        
        cmd.extend(["-iname", f"*{name}*"])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            files = [f for f in result.stdout.strip().split('\n') if f]
            if files:
                return ToolResult(True, "\n".join(files[:50]), data={"count": len(files)})
            else:
                return ToolResult(True, "No files found")
                
        except Exception as e:
            return ToolResult(False, "", error=str(e))


class WebSearchTool:
    """
    Web search for grounding - reduces hallucination.
    Uses DuckDuckGo or SearXNG.
    """
    
    def __init__(self):
        self.searxng_url = "http://localhost:8888"
        self.cache_dir = get_data_dir() / "cache" / "search"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def search(self, query: str, num_results: int = 5) -> ToolResult:
        """
        Search the web and return results.
        First tries SearXNG (local), then DuckDuckGo.
        """
        # Try SearXNG first
        result = self._search_searxng(query, num_results)
        if result.success:
            return result
        
        # Fallback to DuckDuckGo
        return self._search_duckduckgo(query, num_results)
    
    def _search_searxng(self, query: str, num_results: int) -> ToolResult:
        """Search using local SearXNG"""
        try:
            import requests
            
            resp = requests.get(
                f"{self.searxng_url}/search",
                params={"q": query, "format": "json"},
                timeout=10
            )
            
            if resp.status_code != 200:
                return ToolResult(False, "", error="SearXNG not available")
            
            data = resp.json()
            results = data.get("results", [])[:num_results]
            
            if not results:
                return ToolResult(True, "No results found")
            
            output_lines = []
            result_data = []
            
            for i, r in enumerate(results, 1):
                title = r.get("title", "No title")
                url = r.get("url", "")
                content = r.get("content", "")[:200]
                
                output_lines.append(f"[{i}] {title}")
                output_lines.append(f"    {url}")
                if content:
                    output_lines.append(f"    {content}...")
                output_lines.append("")
                
                result_data.append({"title": title, "url": url, "content": content})
            
            # Cache results
            self._cache_search(query, result_data)
            
            return ToolResult(True, "\n".join(output_lines), data=result_data)
            
        except Exception as e:
            return ToolResult(False, "", error=str(e))
    
    def _search_duckduckgo(self, query: str, num_results: int) -> ToolResult:
        """Search using DuckDuckGo HTML"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            url = f"https://html.duckduckgo.com/html/?q={query}"
            headers = {'User-Agent': 'Ryx-AI/1.0 (Educational)'}
            
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            results = []
            for result in soup.find_all('div', class_='result')[:num_results]:
                title_elem = result.find('a', class_='result__a')
                snippet_elem = result.find('a', class_='result__snippet')
                
                if title_elem:
                    result_url = title_elem['href']
                    if result_url.startswith('//'):
                        result_url = 'https:' + result_url
                    
                    results.append({
                        'title': title_elem.get_text(strip=True),
                        'url': result_url,
                        'content': snippet_elem.get_text(strip=True) if snippet_elem else ""
                    })
            
            if not results:
                return ToolResult(True, "No results found")
            
            output_lines = []
            for i, r in enumerate(results, 1):
                output_lines.append(f"[{i}] {r['title']}")
                output_lines.append(f"    {r['url']}")
                if r['content']:
                    output_lines.append(f"    {r['content'][:150]}...")
                output_lines.append("")
            
            # Cache results
            self._cache_search(query, results)
            
            return ToolResult(True, "\n".join(output_lines), data=results)
            
        except Exception as e:
            return ToolResult(False, "", error=str(e))
    
    def _cache_search(self, query: str, results: List[Dict]):
        """Cache search results"""
        import hashlib
        query_hash = hashlib.md5(query.lower().encode()).hexdigest()[:12]
        cache_file = self.cache_dir / f"{query_hash}.json"
        
        with open(cache_file, 'w') as f:
            json.dump({
                "query": query,
                "results": results,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)
    
    def get_cached(self, query: str) -> Optional[List[Dict]]:
        """Get cached search results if recent"""
        import hashlib
        query_hash = hashlib.md5(query.lower().encode()).hexdigest()[:12]
        cache_file = self.cache_dir / f"{query_hash}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                
                # Check if cache is recent (< 1 hour)
                cached_time = datetime.fromisoformat(data["timestamp"])
                if (datetime.now() - cached_time).total_seconds() < 3600:
                    return data["results"]
            except:
                pass
        
        return None


class BrowserTool:
    """
    Browser control - open URLs.
    """
    
    def __init__(self):
        self.default_browser = os.environ.get("BROWSER", "xdg-open")
    
    def open(self, url: str, browser: str = None) -> ToolResult:
        """Open URL in browser"""
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        browser = browser or self.default_browser
        
        try:
            if browser == "xdg-open":
                subprocess.Popen(["xdg-open", url])
            else:
                subprocess.Popen([browser, url])
            
            return ToolResult(True, f"✅ Opened: {url}")
            
        except Exception as e:
            return ToolResult(False, "", error=str(e))


class ScrapeTool:
    """
    Web scraping for learning content.
    """
    
    def __init__(self):
        self.scrape_dir = get_data_dir() / "scrape"
        self.scrape_dir.mkdir(parents=True, exist_ok=True)
    
    def scrape(self, url: str) -> ToolResult:
        """Scrape webpage content"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            headers = {'User-Agent': 'Ryx-AI/1.0 (Educational)'}
            resp = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Remove scripts and styles
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            
            # Extract content
            title = soup.title.string if soup.title else "No title"
            text = soup.get_text(separator='\n', strip=True)
            
            # Save
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            safe_name = re.sub(r'[^\w\-_.]', '_', domain)[:50]
            
            data = {
                "url": url,
                "title": title,
                "domain": domain,
                "text": text[:50000],
                "scraped_at": datetime.now().isoformat()
            }
            
            scrape_file = self.scrape_dir / f"{safe_name}.json"
            with open(scrape_file, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return ToolResult(
                True,
                f"✅ Scraped: {title}\n   {len(text)} characters\n   Saved: {scrape_file}",
                data=data
            )
            
        except Exception as e:
            return ToolResult(False, "", error=str(e))


class ToolRegistry:
    """
    Central registry for all tools.
    Like Copilot CLI tool system.
    """
    
    def __init__(self, safety_mode: str = "normal"):
        self.shell = ShellTool(safety_mode)
        self.file = FileTool()
        self.search = SearchTool()
        self.web_search = WebSearchTool()
        self.browser = BrowserTool()
        self.scrape = ScrapeTool()
        
        self.enabled = {
            "shell": True,
            "file": True,
            "search": True,
            "web_search": True,
            "browser": True,
            "scrape": True,
        }
    
    def set_enabled(self, tool_name: str, enabled: bool) -> bool:
        """Enable/disable a tool"""
        if tool_name in self.enabled:
            self.enabled[tool_name] = enabled
            return True
        return False
    
    def get_tool(self, name: str):
        """Get a tool by name"""
        tools = {
            "shell": self.shell,
            "bash": self.shell,
            "file": self.file,
            "view": self.file,
            "edit": self.file,
            "search": self.search,
            "grep": self.search,
            "glob": self.search,
            "find": self.search,
            "web_search": self.web_search,
            "websearch": self.web_search,
            "browser": self.browser,
            "scrape": self.scrape,
        }
        return tools.get(name.lower())
    
    def list_tools(self) -> List[Dict]:
        """List all available tools with status"""
        return [
            {"name": "shell", "desc": "Execute shell commands", "enabled": self.enabled["shell"]},
            {"name": "file", "desc": "View, edit, create files", "enabled": self.enabled["file"]},
            {"name": "search", "desc": "Grep, glob, find files", "enabled": self.enabled["search"]},
            {"name": "web_search", "desc": "Search the web", "enabled": self.enabled["web_search"]},
            {"name": "browser", "desc": "Open URLs in browser", "enabled": self.enabled["browser"]},
            {"name": "scrape", "desc": "Scrape web content", "enabled": self.enabled["scrape"]},
        ]


# Singleton instance
_tools: Optional[ToolRegistry] = None

def get_tools(safety_mode: str = "normal") -> ToolRegistry:
    global _tools
    if _tools is None:
        _tools = ToolRegistry(safety_mode)
    return _tools
