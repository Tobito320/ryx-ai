"""
Ryx AI - Codebase Explorer

When Ryx gets a vague prompt like "resume work on ryxsurf", it needs to:
1. Understand the project structure
2. Find recent changes (git log)
3. Identify incomplete features
4. Look for TODOs, FIXMEs in code
5. Check for failing tests

This allows Ryx to be autonomous and work with minimal prompts.
"""

import subprocess
import re
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class ProjectInsight:
    """Insights about a project"""
    name: str
    root_path: Path
    main_files: List[str]
    recent_changes: List[str]
    todos_in_code: List[Dict[str, Any]]
    incomplete_features: List[str]
    test_status: Optional[str]
    summary: str


class CodebaseExplorer:
    """
    Explores a codebase to understand its current state.
    
    Inspired by Claude Code's approach:
    - Scan for structure
    - Check git history
    - Find TODOs/FIXMEs
    - Identify work in progress
    """
    
    def __init__(self, repo_root: str = "."):
        self.repo_root = Path(repo_root).resolve()
    
    def explore_project(self, project_name: str) -> ProjectInsight:
        """
        Deep exploration of a project to understand what needs work.
        """
        # Find project directory
        project_dir = self._find_project_dir(project_name)
        if not project_dir:
            return ProjectInsight(
                name=project_name,
                root_path=self.repo_root,
                main_files=[],
                recent_changes=[],
                todos_in_code=[],
                incomplete_features=[],
                test_status=None,
                summary=f"Project '{project_name}' not found"
            )
        
        # Gather insights
        main_files = self._find_main_files(project_dir)
        recent_changes = self._get_recent_changes(project_dir)
        todos = self._find_todos(project_dir)
        incomplete = self._find_incomplete_features(project_dir, recent_changes, todos)
        test_status = self._check_tests(project_dir)
        
        summary = self._generate_summary(
            project_name, main_files, recent_changes, todos, incomplete, test_status
        )
        
        return ProjectInsight(
            name=project_name,
            root_path=project_dir,
            main_files=main_files,
            recent_changes=recent_changes,
            todos_in_code=todos,
            incomplete_features=incomplete,
            test_status=test_status,
            summary=summary
        )
    
    def _find_project_dir(self, name: str) -> Optional[Path]:
        """Find a project directory by name"""
        # Check common locations
        candidates = [
            self.repo_root / name,
            self.repo_root / name.lower(),
            self.repo_root / name.replace("-", "_"),
        ]
        
        for path in candidates:
            if path.exists() and path.is_dir():
                return path
        
        # Search in subdirectories
        for path in self.repo_root.iterdir():
            if path.is_dir() and name.lower() in path.name.lower():
                return path
        
        return None
    
    def _find_main_files(self, project_dir: Path) -> List[str]:
        """Find the main/important files in a project"""
        main_files = []
        
        # Common important file patterns
        important_patterns = [
            "main.py", "__main__.py", "app.py", "index.py",
            "browser.py", "agent.py", "actions.py",
            "README.md", "pyproject.toml", "package.json"
        ]
        
        for pattern in important_patterns:
            files = list(project_dir.rglob(pattern))
            for f in files[:3]:  # Max 3 per pattern
                rel = str(f.relative_to(self.repo_root))
                if rel not in main_files:
                    main_files.append(rel)
        
        return main_files[:15]  # Limit to 15
    
    def _get_recent_changes(self, project_dir: Path) -> List[str]:
        """Get recent git changes for the project"""
        try:
            rel_path = project_dir.relative_to(self.repo_root)
            result = subprocess.run(
                ["git", "--no-pager", "log", "--oneline", "-10", "--", str(rel_path)],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")[:10]
        except:
            pass
        return []
    
    def _find_todos(self, project_dir: Path) -> List[Dict[str, Any]]:
        """Find TODO, FIXME, HACK comments in code"""
        todos = []
        
        try:
            result = subprocess.run(
                ["grep", "-rn", "-E", "TODO|FIXME|HACK|XXX", str(project_dir)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            for line in result.stdout.split("\n")[:20]:  # Limit to 20
                if line.strip():
                    match = re.match(r"([^:]+):(\d+):(.*)", line)
                    if match:
                        file_path, line_num, content = match.groups()
                        todos.append({
                            "file": str(Path(file_path).relative_to(self.repo_root)),
                            "line": int(line_num),
                            "content": content.strip()[:100]
                        })
        except:
            pass
        
        return todos
    
    def _find_incomplete_features(
        self, 
        project_dir: Path, 
        recent_changes: List[str],
        todos: List[Dict[str, Any]]
    ) -> List[str]:
        """Identify features that might be incomplete"""
        incomplete = []
        
        # Check for "WIP", "incomplete", "stub" in recent commits
        for change in recent_changes:
            lower = change.lower()
            if any(kw in lower for kw in ["wip", "incomplete", "stub", "todo", "partial"]):
                incomplete.append(f"Recent: {change}")
        
        # Check for stub/pass statements in Python files
        try:
            result = subprocess.run(
                ["grep", "-rn", "-E", r"pass\s*#|raise NotImplementedError|\.\.\.  #", str(project_dir)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            for line in result.stdout.split("\n")[:5]:
                if line.strip():
                    match = re.match(r"([^:]+):(\d+):", line)
                    if match:
                        file_path = match.group(1)
                        incomplete.append(f"Stub in: {Path(file_path).name}")
        except:
            pass
        
        # High-priority TODOs
        for todo in todos[:5]:
            if "TODO" in todo["content"].upper():
                incomplete.append(f"TODO: {todo['content'][:50]}")
        
        return incomplete[:10]
    
    def _check_tests(self, project_dir: Path) -> Optional[str]:
        """Check if tests exist and their status"""
        test_dirs = ["tests", "test", "spec"]
        
        for test_dir in test_dirs:
            test_path = project_dir / test_dir
            if test_path.exists():
                test_files = list(test_path.glob("test_*.py"))
                if test_files:
                    return f"Found {len(test_files)} test files in {test_dir}/"
        
        return None
    
    def _generate_summary(
        self,
        name: str,
        main_files: List[str],
        recent_changes: List[str],
        todos: List[Dict[str, Any]],
        incomplete: List[str],
        test_status: Optional[str]
    ) -> str:
        """Generate a human-readable summary"""
        lines = [f"## Project: {name}", ""]
        
        if main_files:
            lines.append(f"**Main files:** {len(main_files)} key files found")
            for f in main_files[:5]:
                lines.append(f"  - {f}")
        
        if recent_changes:
            lines.append(f"\n**Recent changes:** {len(recent_changes)} commits")
            for c in recent_changes[:3]:
                lines.append(f"  - {c}")
        
        if incomplete:
            lines.append(f"\n**Needs work:** {len(incomplete)} items")
            for item in incomplete[:5]:
                lines.append(f"  - {item}")
        
        if todos:
            lines.append(f"\n**TODOs in code:** {len(todos)} found")
        
        if test_status:
            lines.append(f"\n**Tests:** {test_status}")
        
        return "\n".join(lines)
    
    def suggest_next_actions(self, insight: ProjectInsight) -> List[str]:
        """Suggest what to work on next based on exploration"""
        suggestions = []
        
        # Priority 1: Incomplete features from recent work
        for item in insight.incomplete_features[:3]:
            if item.startswith("Recent:"):
                suggestions.append(f"Continue: {item[8:]}")
            elif item.startswith("Stub"):
                suggestions.append(f"Implement: {item}")
        
        # Priority 2: High-impact TODOs
        for todo in insight.todos_in_code[:3]:
            content = todo["content"]
            if "important" in content.lower() or "critical" in content.lower():
                suggestions.append(f"Fix: {content[:50]}")
        
        # Priority 3: Add tests if missing
        if not insight.test_status:
            suggestions.append("Add tests for the project")
        
        # Default: Look at main files for improvements
        if not suggestions and insight.main_files:
            suggestions.append(f"Review and improve: {insight.main_files[0]}")
        
        return suggestions[:5]


# Tool schema for LLM
EXPLORE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "explore_project",
        "description": """Explore a project to understand what needs work.
Use this when you get vague prompts like:
- "resume work on X"
- "continue developing X"
- "what's the status of X"

Returns: main files, recent changes, TODOs, incomplete features""",
        "parameters": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Name of the project to explore (e.g., 'ryxsurf', 'core')"
                }
            },
            "required": ["project_name"]
        }
    }
}
