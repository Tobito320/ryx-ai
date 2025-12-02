"""
Ryx AI - Agent Tools

Structured tools for controlled code editing.
LLM can only use these tools - no free-form file writing.

Inspired by Claude Code & Aider's tool-based approach.
"""

import os
import re
import subprocess
import shutil
import difflib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from core.paths import get_data_dir


@dataclass
class ToolResult:
    """Result from a tool execution"""
    success: bool
    output: str
    data: Optional[Any] = None
    error: Optional[str] = None


class AgentTool(ABC):
    """Base class for all agent tools"""
    
    name: str
    description: str
    
    @abstractmethod
    def execute(self, **params) -> ToolResult:
        """Execute the tool with given parameters"""
        pass
    
    def get_schema(self) -> Dict:
        """Get JSON schema for this tool"""
        return {
            "name": self.name,
            "description": self.description,
        }


# ─────────────────────────────────────────────────────────────
# File Reading Tools
# ─────────────────────────────────────────────────────────────

class ReadFileTool(AgentTool):
    """Read file contents - provides ground truth"""
    
    name = "read_file"
    description = "Read the contents of a file. Use this to understand code before making changes."
    
    def execute(self, path: str, start_line: int = None, end_line: int = None) -> ToolResult:
        path = os.path.expanduser(path)
        
        if not os.path.exists(path):
            return ToolResult(False, "", error=f"File not found: {path}")
        
        if os.path.isdir(path):
            return ToolResult(False, "", error=f"Path is a directory: {path}")
        
        try:
            with open(path, 'r') as f:
                lines = f.readlines()
            
            # Apply line range if specified
            if start_line is not None:
                start_idx = max(0, start_line - 1)
                end_idx = end_line if end_line else len(lines)
                lines = lines[start_idx:end_idx]
            
            # Add line numbers
            output_lines = []
            base_num = start_line or 1
            for i, line in enumerate(lines):
                output_lines.append(f"{base_num + i:4}| {line.rstrip()}")
            
            return ToolResult(
                True,
                "\n".join(output_lines),
                data={"path": path, "lines": len(lines)}
            )
            
        except Exception as e:
            return ToolResult(False, "", error=str(e))


class ListDirectoryTool(AgentTool):
    """List directory contents"""
    
    name = "list_directory"
    description = "List files and directories in a path. Use to explore project structure."
    
    def execute(self, path: str = ".", max_depth: int = 2) -> ToolResult:
        path = os.path.expanduser(path)
        
        if not os.path.exists(path):
            return ToolResult(False, "", error=f"Path not found: {path}")
        
        try:
            output = []
            for root, dirs, files in os.walk(path):
                level = root.replace(path, '').count(os.sep)
                if level >= max_depth:
                    dirs[:] = []
                    continue
                
                # Skip hidden and common ignore dirs
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'node_modules', '__pycache__', 'venv'}]
                
                indent = "  " * level
                output.append(f"{indent}{os.path.basename(root)}/")
                
                subindent = "  " * (level + 1)
                for f in sorted(files)[:20]:
                    if not f.startswith('.'):
                        output.append(f"{subindent}{f}")
                
                if len(files) > 20:
                    output.append(f"{subindent}... and {len(files) - 20} more")
            
            return ToolResult(True, "\n".join(output))
            
        except Exception as e:
            return ToolResult(False, "", error=str(e))


class SearchCodeTool(AgentTool):
    """Search for patterns in code"""
    
    name = "search_code"
    description = "Search for a pattern in code files. Returns matching lines with context."
    
    def execute(self, pattern: str, path: str = ".", file_pattern: str = None, context_lines: int = 2) -> ToolResult:
        path = os.path.expanduser(path)
        
        # Try ripgrep first, fall back to grep
        cmd = ["rg", "--no-heading", "-n", f"-C{context_lines}"]
        
        if file_pattern:
            cmd.extend(["-g", file_pattern])
        
        cmd.extend([pattern, path])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return ToolResult(True, result.stdout.strip())
            elif result.returncode == 1:
                return ToolResult(True, "No matches found")
            else:
                # Try grep fallback
                return self._grep_fallback(pattern, path, context_lines)
                
        except FileNotFoundError:
            return self._grep_fallback(pattern, path, context_lines)
        except Exception as e:
            return ToolResult(False, "", error=str(e))
    
    def _grep_fallback(self, pattern: str, path: str, context: int) -> ToolResult:
        cmd = ["grep", "-rn", f"-C{context}", pattern, path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return ToolResult(result.returncode == 0, result.stdout.strip())
        except Exception as e:
            return ToolResult(False, "", error=str(e))


# ─────────────────────────────────────────────────────────────
# File Writing Tools
# ─────────────────────────────────────────────────────────────

class WriteFileTool(AgentTool):
    """Write entire file (with backup)"""
    
    name = "write_file"
    description = "Write content to a file. Creates backup of existing files. Use sparingly - prefer apply_diff for small changes."
    
    def __init__(self):
        self.backup_dir = get_data_dir() / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def execute(self, path: str, content: str, create_backup: bool = True) -> ToolResult:
        path = os.path.expanduser(path)
        backup_path = None
        
        try:
            # Create backup if file exists
            if os.path.exists(path) and create_backup:
                backup_path = self._create_backup(path)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            
            # Write file
            with open(path, 'w') as f:
                f.write(content)
            
            return ToolResult(
                True,
                f"✓ Written: {path}" + (f" (backup: {backup_path})" if backup_path else ""),
                data={"path": path, "backup": backup_path}
            )
            
        except Exception as e:
            return ToolResult(False, "", error=str(e))
    
    def _create_backup(self, path: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(path)
        backup_path = self.backup_dir / f"{filename}.{timestamp}.bak"
        shutil.copy2(path, backup_path)
        return str(backup_path)


class ApplyDiffTool(AgentTool):
    """Apply unified diff patch to a file"""
    
    name = "apply_diff"
    description = "Apply a unified diff patch to a file. This is the preferred way to make small changes."
    
    def __init__(self):
        self.backup_dir = get_data_dir() / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def execute(self, path: str, diff: str) -> ToolResult:
        path = os.path.expanduser(path)
        
        if not os.path.exists(path):
            return ToolResult(False, "", error=f"File not found: {path}")
        
        try:
            # Read current content
            with open(path, 'r') as f:
                original_lines = f.readlines()
            
            # Parse and apply diff
            new_lines = self._apply_unified_diff(original_lines, diff)
            
            if new_lines is None:
                return ToolResult(False, "", error="Failed to apply diff - patch doesn't match")
            
            # Backup
            backup_path = self._create_backup(path, original_lines)
            
            # Write new content
            with open(path, 'w') as f:
                f.writelines(new_lines)
            
            return ToolResult(
                True,
                f"✓ Patched: {path}",
                data={"path": path, "backup": backup_path}
            )
            
        except Exception as e:
            return ToolResult(False, "", error=str(e))
    
    def _apply_unified_diff(self, original: List[str], diff: str) -> Optional[List[str]]:
        """Apply unified diff to lines"""
        # Parse diff hunks
        result = original.copy()
        offset = 0
        
        hunk_pattern = r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@'
        
        for match in re.finditer(hunk_pattern, diff):
            start_line = int(match.group(1)) - 1 + offset
            
            # Get hunk content
            hunk_start = match.end()
            next_hunk = re.search(hunk_pattern, diff[hunk_start:])
            hunk_end = next_hunk.start() + hunk_start if next_hunk else len(diff)
            hunk_content = diff[hunk_start:hunk_end].strip().split('\n')
            
            # Apply changes
            new_lines = []
            removed = 0
            added = 0
            
            for line in hunk_content:
                if line.startswith('-') and not line.startswith('---'):
                    removed += 1
                elif line.startswith('+') and not line.startswith('+++'):
                    new_lines.append(line[1:] + '\n')
                    added += 1
                elif line.startswith(' ') or not line.startswith(('-', '+')):
                    new_lines.append(line[1:] + '\n' if line.startswith(' ') else line + '\n')
            
            # Replace in result
            result[start_line:start_line + removed] = new_lines
            offset += added - removed
        
        return result
    
    def _create_backup(self, path: str, content: List[str]) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(path)
        backup_path = self.backup_dir / f"{filename}.{timestamp}.bak"
        with open(backup_path, 'w') as f:
            f.writelines(content)
        return str(backup_path)


class CreateFileTool(AgentTool):
    """Create a new file"""
    
    name = "create_file"
    description = "Create a new file with given content. Fails if file already exists."
    
    def execute(self, path: str, content: str) -> ToolResult:
        path = os.path.expanduser(path)
        
        if os.path.exists(path):
            return ToolResult(False, "", error=f"File already exists: {path}")
        
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            
            with open(path, 'w') as f:
                f.write(content)
            
            return ToolResult(True, f"✓ Created: {path}", data={"path": path})
            
        except Exception as e:
            return ToolResult(False, "", error=str(e))


class DeleteFileTool(AgentTool):
    """Delete a file (with backup)"""
    
    name = "delete_file"
    description = "Delete a file. Creates backup before deletion."
    
    def __init__(self):
        self.backup_dir = get_data_dir() / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def execute(self, path: str) -> ToolResult:
        path = os.path.expanduser(path)
        
        if not os.path.exists(path):
            return ToolResult(False, "", error=f"File not found: {path}")
        
        try:
            # Backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(path)
            backup_path = self.backup_dir / f"{filename}.{timestamp}.deleted"
            shutil.copy2(path, backup_path)
            
            # Delete
            os.remove(path)
            
            return ToolResult(
                True,
                f"✓ Deleted: {path} (backup: {backup_path})",
                data={"path": path, "backup": str(backup_path)}
            )
            
        except Exception as e:
            return ToolResult(False, "", error=str(e))


# ─────────────────────────────────────────────────────────────
# Command Execution Tools
# ─────────────────────────────────────────────────────────────

class RunCommandTool(AgentTool):
    """Run a shell command safely"""
    
    name = "run_command"
    description = "Run a shell command and return output. Use for tests, builds, etc."
    
    # Commands that are always blocked
    BLOCKED_PATTERNS = [
        r'rm\s+-rf\s+[/~]',
        r'rm\s+-rf\s+\*',
        r'>\s*/dev/sd',
        r'mkfs\.',
        r'dd\s+if=',
        r':\(\)\s*\{',  # Fork bomb
    ]
    
    def execute(self, command: str, timeout: int = 60, cwd: str = None) -> ToolResult:
        # Safety check
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, command):
                return ToolResult(False, "", error=f"Blocked dangerous command: {command}")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            
            return ToolResult(
                result.returncode == 0,
                output.strip(),
                data={"exit_code": result.returncode}
            )
            
        except subprocess.TimeoutExpired:
            return ToolResult(False, "", error=f"Command timed out after {timeout}s")
        except Exception as e:
            return ToolResult(False, "", error=str(e))


# ─────────────────────────────────────────────────────────────
# Git Tools
# ─────────────────────────────────────────────────────────────

class GitCommitTool(AgentTool):
    """Commit current changes"""
    
    name = "git_commit"
    description = "Create a git commit with the current changes."
    
    def execute(self, message: str, add_all: bool = True) -> ToolResult:
        try:
            if add_all:
                subprocess.run(["git", "add", "-A"], capture_output=True)
            
            result = subprocess.run(
                ["git", "commit", "-m", message],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return ToolResult(True, f"✓ Committed: {message}")
            else:
                return ToolResult(False, "", error=result.stderr)
                
        except Exception as e:
            return ToolResult(False, "", error=str(e))


class GitRevertTool(AgentTool):
    """Revert changes"""
    
    name = "git_revert"
    description = "Revert the last commit or unstaged changes."
    
    def execute(self, mode: str = "last_commit") -> ToolResult:
        try:
            if mode == "last_commit":
                result = subprocess.run(
                    ["git", "revert", "HEAD", "--no-edit"],
                    capture_output=True,
                    text=True
                )
            elif mode == "unstaged":
                result = subprocess.run(
                    ["git", "checkout", "--", "."],
                    capture_output=True,
                    text=True
                )
            else:
                return ToolResult(False, "", error=f"Unknown mode: {mode}")
            
            if result.returncode == 0:
                return ToolResult(True, f"✓ Reverted ({mode})")
            else:
                return ToolResult(False, "", error=result.stderr)
                
        except Exception as e:
            return ToolResult(False, "", error=str(e))


class GitDiffTool(AgentTool):
    """Show git diff"""
    
    name = "git_diff"
    description = "Show uncommitted changes in git."
    
    def execute(self, path: str = None) -> ToolResult:
        try:
            cmd = ["git", "--no-pager", "diff"]
            if path:
                cmd.append(path)
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            return ToolResult(
                True,
                result.stdout.strip() or "No changes",
                data={"has_changes": bool(result.stdout.strip())}
            )
            
        except Exception as e:
            return ToolResult(False, "", error=str(e))


# ─────────────────────────────────────────────────────────────
# Tool Registry
# ─────────────────────────────────────────────────────────────

class AgentToolRegistry:
    """Registry of all available agent tools"""
    
    def __init__(self):
        self.tools: Dict[str, AgentTool] = {}
        self._register_defaults()
    
    def _register_defaults(self):
        """Register all default tools"""
        default_tools = [
            ReadFileTool(),
            ListDirectoryTool(),
            SearchCodeTool(),
            WriteFileTool(),
            ApplyDiffTool(),
            CreateFileTool(),
            DeleteFileTool(),
            RunCommandTool(),
            GitCommitTool(),
            GitRevertTool(),
            GitDiffTool(),
        ]
        
        for tool in default_tools:
            self.register(tool)
    
    def register(self, tool: AgentTool):
        """Register a tool"""
        self.tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[AgentTool]:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def execute(self, name: str, **params) -> ToolResult:
        """Execute a tool by name"""
        tool = self.get(name)
        if not tool:
            return ToolResult(False, "", error=f"Unknown tool: {name}")
        
        return tool.execute(**params)
    
    def list_tools(self) -> List[Dict]:
        """List all available tools"""
        return [tool.get_schema() for tool in self.tools.values()]
    
    def get_tools_prompt(self) -> str:
        """Get prompt describing available tools"""
        lines = ["Available tools:"]
        for name, tool in self.tools.items():
            lines.append(f"  - {name}: {tool.description}")
        return "\n".join(lines)


# Singleton instance
_registry: Optional[AgentToolRegistry] = None

def get_agent_tools() -> AgentToolRegistry:
    """Get or create agent tools registry"""
    global _registry
    if _registry is None:
        _registry = AgentToolRegistry()
    return _registry
