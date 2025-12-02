"""
Ryx AI - Claude CLI Style Rich UI

Production-ready CLI module using Rich that mimics Claude Code / Copilot CLI:
- Step-by-step task visualization
- Git-style diff boxes
- Live status bar
- Workflow phase indicators
- Token streaming with stats

Public API:
- ui.task_start(name) / ui.task_done(name, details)
- ui.show_diff(file, old, new)
- ui.phase(name, status)
- ui.stream_token(token)
- ui.status_bar(model, msgs, tok_s, branch, changes)
"""

import sys
import os
import time
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner
from rich.syntax import Syntax
from rich.rule import Rule
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.columns import Columns
from rich.style import Style
from rich.theme import Theme as RichTheme
from rich.markup import escape


# ═══════════════════════════════════════════════════════════════════════════════
# Theme Configuration (Catppuccin Mocha inspired)
# ═══════════════════════════════════════════════════════════════════════════════

RYX_THEME = RichTheme({
    "ryx.success": "green",
    "ryx.error": "red",
    "ryx.warning": "yellow",
    "ryx.info": "cyan",
    "ryx.dim": "dim",
    "ryx.primary": "magenta",
    "ryx.secondary": "blue",
    "ryx.muted": "#6c7086",
    "ryx.border": "#45475a",
    "ryx.diff.add": "green",
    "ryx.diff.remove": "red",
    "ryx.diff.context": "dim",
    "ryx.model": "cyan",
    "ryx.phase": "magenta bold",
    "ryx.step": "cyan",
})


class PhaseStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class TaskState:
    """State of a running task"""
    name: str
    status: PhaseStatus = PhaseStatus.PENDING
    details: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None


@dataclass
class StreamState:
    """State for token streaming"""
    tokens: int = 0
    start_time: float = field(default_factory=time.time)
    model: str = ""
    buffer: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# RyxUI - Main UI Class
# ═══════════════════════════════════════════════════════════════════════════════

class RyxUI:
    """
    Claude CLI-style Rich UI for Ryx.
    
    Features:
    - Live task updates with spinners
    - Git-style diff display
    - Token streaming with stats
    - Workflow phase indicators
    - Bottom status bar
    """
    
    def __init__(self):
        self.console = Console(theme=RYX_THEME, highlight=False)
        self.tasks: Dict[str, TaskState] = {}
        self.stream: Optional[StreamState] = None
        self.current_phase: str = ""
        self._live: Optional[Live] = None
        
    # ─────────────────────────────────────────────────────────────────────────
    # Status Bar (Top)
    # ─────────────────────────────────────────────────────────────────────────
    
    def print_status_bar(
        self,
        cwd: Optional[str] = None,
        branch: str = "",
        model: str = "",
        context_tokens: int = 0,
        msg_count: int = 0
    ):
        """
        Print top status bar like Claude CLI.
        
        Example:
        ~/ryx-ai[⎇ main]                                    qwen2.5-coder:14b
        ─────────────────────────────────────────────────────────────────────
        """
        cwd = cwd or os.getcwd()
        cwd_short = cwd.replace(os.path.expanduser("~"), "~")
        
        # Build left side
        if branch:
            left = Text()
            left.append(cwd_short)
            left.append("[", style="dim")
            left.append("⎇ ", style="ryx.info")
            left.append(branch, style="ryx.info")
            left.append("]", style="dim")
        else:
            left = Text(cwd_short)
        
        # Build right side
        right_parts = []
        if model:
            right_parts.append(model)
        if context_tokens > 0:
            right_parts.append(f"{context_tokens} ctx")
        if msg_count > 0:
            right_parts.append(f"{msg_count} msgs")
        
        right = Text(" · ".join(right_parts), style="dim")
        
        # Calculate spacing for alignment
        width = self.console.width
        padding = width - len(left.plain) - len(right.plain) - 2
        
        # Print
        self.console.print()
        self.console.print(left + Text(" " * max(1, padding)) + right)
        self.console.print(Rule(style="ryx.border"))
    
    # ─────────────────────────────────────────────────────────────────────────
    # Bottom Hints
    # ─────────────────────────────────────────────────────────────────────────
    
    def print_bottom_hints(
        self,
        left: str = "Ctrl+c Exit · /help",
        right: str = ""
    ):
        """Print bottom hints bar"""
        width = self.console.width
        padding = width - len(left) - len(right) - 2
        
        hint_text = Text()
        hint_text.append(left, style="dim")
        hint_text.append(" " * max(1, padding))
        hint_text.append(right, style="dim")
        
        self.console.print(hint_text)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Task Visualization (Step by Step)
    # ─────────────────────────────────────────────────────────────────────────
    
    def task_start(self, name: str, details: str = "") -> str:
        """
        Start a task with spinner.
        
        Example: ⏳ Read core/session_loop.py...
        
        Returns task_id for later reference.
        """
        task_id = f"task_{len(self.tasks)}"
        self.tasks[task_id] = TaskState(name=name, status=PhaseStatus.RUNNING, details=details)
        
        # Print with spinner
        spinner = "⏳"
        text = Text()
        text.append(f"{spinner} ", style="ryx.info")
        text.append(name, style="ryx.step")
        if details:
            text.append(f" {details}", style="dim")
        text.append("…")
        
        self.console.print(text)
        return task_id
    
    def task_done(
        self,
        task_id_or_name: str,
        details: str = "",
        success: bool = True
    ):
        """
        Mark task as done.
        
        Example: 
        ✅ Read core/session_loop.py
        └─ 40 lines read successfully
        """
        icon = "✅" if success else "❌"
        style = "ryx.success" if success else "ryx.error"
        
        # Find task
        task = None
        for tid, t in self.tasks.items():
            if tid == task_id_or_name or t.name == task_id_or_name:
                task = t
                break
        
        name = task.name if task else task_id_or_name
        
        # Print completion
        text = Text()
        text.append(f"{icon} ", style=style)
        text.append(name, style="ryx.step")
        self.console.print(text)
        
        # Print details if provided
        if details:
            detail_text = Text()
            detail_text.append("└─ ", style="dim")
            detail_text.append(details, style="dim")
            self.console.print(detail_text)
        
        # Update task state
        if task:
            task.status = PhaseStatus.SUCCESS if success else PhaseStatus.ERROR
            task.details = details
            task.end_time = time.time()
    
    def task_update(self, name: str, details: str):
        """Update a running task's details"""
        text = Text()
        text.append("   └─ ", style="dim")
        text.append(details, style="dim")
        self.console.print(text)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Diff Display (Git/GitHub style)
    # ─────────────────────────────────────────────────────────────────────────
    
    def show_diff(
        self,
        filename: str,
        old_lines: List[str],
        new_lines: List[str],
        context_lines: int = 3
    ):
        """
        Show a git-style diff box.
        
        Example:
        ┌─ agents/supervisor.py (modified) ────────────────────────
        │ 42  -   def old(): 
        │ 42  +   def new():  
        └──────────────────────────────────────────────────────────
        """
        import difflib
        
        diff = list(difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=""
        ))
        
        if not diff:
            return  # No changes
        
        # Build diff text
        diff_text = Text()
        
        line_num = 0
        for line in diff[2:]:  # Skip header lines
            if line.startswith("@@"):
                # Parse line numbers
                try:
                    parts = line.split(" ")
                    line_num = int(parts[2].split(",")[0].replace("+", ""))
                except:
                    pass
                diff_text.append(f"│ {line}\n", style="ryx.info")
            elif line.startswith("-"):
                diff_text.append(f"│ {line_num:4d}  ", style="dim")
                diff_text.append(f"{line}\n", style="ryx.diff.remove")
            elif line.startswith("+"):
                diff_text.append(f"│ {line_num:4d}  ", style="dim")
                diff_text.append(f"{line}\n", style="ryx.diff.add")
                line_num += 1
            else:
                diff_text.append(f"│ {line_num:4d}  ", style="dim")
                diff_text.append(f" {line}\n", style="ryx.diff.context")
                line_num += 1
        
        # Print as panel
        header = f"┌─ {filename} (modified) " + "─" * max(1, 50 - len(filename))
        footer = "└" + "─" * 58
        
        self.console.print(Text(header, style="ryx.border"))
        self.console.print(diff_text)
        self.console.print(Text(footer, style="ryx.border"))
    
    def show_file_preview(self, filename: str, content: str, language: str = "python"):
        """Show a file content preview with syntax highlighting"""
        syntax = Syntax(
            content,
            language,
            theme="monokai",
            line_numbers=True,
            word_wrap=True
        )
        
        panel = Panel(
            syntax,
            title=f"[ryx.step]{filename}[/]",
            border_style="ryx.border",
            padding=(0, 1)
        )
        self.console.print(panel)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Workflow Phases
    # ─────────────────────────────────────────────────────────────────────────
    
    def phase_start(self, name: str, description: str = ""):
        """
        Start a workflow phase.
        
        Example: ⏳ EXPLORE: Scanning repository...
        """
        self.current_phase = name
        
        text = Text()
        text.append("⏳ ", style="ryx.info")
        text.append(name.upper(), style="ryx.phase")
        if description:
            text.append(f" {description}", style="dim")
        text.append("…")
        
        self.console.print(text)
    
    def phase_done(self, name: str, result: str = "", success: bool = True):
        """
        Complete a workflow phase.
        
        Example: ✅ EXPLORE: Found 42 files
        """
        icon = "✅" if success else "❌"
        style = "ryx.success" if success else "ryx.error"
        
        text = Text()
        text.append(f"{icon} ", style=style)
        text.append(name.upper(), style="ryx.phase")
        if result:
            text.append(f" {result}", style="dim")
        
        self.console.print(text)
    
    def phase_step(self, step_num: int, description: str, status: str = "pending"):
        """
        Show a step within a phase.
        
        Example:
            1. Identify authentication method
        """
        if status == "done":
            icon = "✓"
            style = "ryx.success"
        elif status == "running":
            icon = "▸"
            style = "ryx.info"
        elif status == "error":
            icon = "✗"
            style = "ryx.error"
        else:
            icon = "○"
            style = "dim"
        
        text = Text()
        text.append(f"    {icon} ", style=style)
        text.append(f"{step_num}. {description}", style="dim" if status == "pending" else "")
        
        self.console.print(text)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Token Streaming with Stats
    # ─────────────────────────────────────────────────────────────────────────
    
    def stream_start(self, model: str = ""):
        """Start streaming output"""
        self.stream = StreamState(model=model)
        
        # Print model header
        text = Text()
        text.append("\nRyx", style="ryx.primary bold")
        if model:
            text.append(f" [{model}]", style="dim")
        text.append(": ")
        
        self.console.print(text, end="")
    
    def stream_token(self, token: str):
        """Print a single token"""
        if self.stream:
            self.stream.tokens += 1
            self.stream.buffer += token
        
        # Print without newline
        sys.stdout.write(token)
        sys.stdout.flush()
    
    def stream_end(self):
        """End streaming and show stats"""
        if not self.stream:
            print()
            return
        
        elapsed = time.time() - self.stream.start_time
        tokens = self.stream.tokens
        
        print()  # End line
        
        if elapsed > 0.1 and tokens > 0:
            tps = tokens / elapsed
            
            stats = Text()
            stats.append(f"  {tokens} tokens", style="dim")
            stats.append(" · ", style="dim")
            stats.append(f"{tps:.1f} tok/s", style="ryx.info")
            stats.append(" · ", style="dim")
            stats.append(f"{elapsed:.1f}s", style="dim")
            
            self.console.print(stats)
        
        self.stream = None
    
    # ─────────────────────────────────────────────────────────────────────────
    # Error Display
    # ─────────────────────────────────────────────────────────────────────────
    
    def show_error(
        self,
        file: str,
        error: str,
        line: Optional[int] = None,
        suggestion: Optional[str] = None
    ):
        """
        Show an error with optional suggestion.
        
        Example:
        ❌ tests/test.py
        └─ ERROR: AssertionError line 45
        Suggestion: Bedingung anpassen? [y/n/show-code]
        """
        # Error line
        error_text = Text()
        error_text.append("❌ ", style="ryx.error")
        error_text.append(file, style="ryx.step")
        self.console.print(error_text)
        
        # Details
        detail = Text()
        detail.append("└─ ", style="dim")
        detail.append("ERROR: ", style="ryx.error")
        detail.append(error)
        if line:
            detail.append(f" line {line}", style="dim")
        self.console.print(detail)
        
        # Suggestion
        if suggestion:
            sugg_text = Text()
            sugg_text.append("Suggestion: ", style="ryx.warning")
            sugg_text.append(suggestion)
            sugg_text.append(" [y/n/show-code]", style="dim")
            self.console.print(sugg_text)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Status Messages
    # ─────────────────────────────────────────────────────────────────────────
    
    def success(self, message: str):
        """Print success message"""
        self.console.print(Text(f"✅ {message}", style="ryx.success"))
    
    def error(self, message: str):
        """Print error message"""
        self.console.print(Text(f"❌ {message}", style="ryx.error"))
    
    def warning(self, message: str):
        """Print warning message"""
        self.console.print(Text(f"⚠️  {message}", style="ryx.warning"))
    
    def info(self, message: str):
        """Print info message"""
        self.console.print(Text(f"ℹ️  {message}", style="ryx.info"))
    
    def dim(self, message: str):
        """Print dimmed message"""
        self.console.print(Text(message, style="dim"))
    
    # ─────────────────────────────────────────────────────────────────────────
    # Search Results
    # ─────────────────────────────────────────────────────────────────────────
    
    def show_search_results(self, results: List[Dict[str, str]], limit: int = 5):
        """
        Show search results in a clean format.
        
        Example:
        📎 Found 5 results:
            • Title here
              snippet preview...
        """
        if not results:
            self.dim("No results found")
            return
        
        self.console.print(Text(f"📎 Found {len(results)} results:", style="ryx.info"))
        
        for i, r in enumerate(results[:limit]):
            title = r.get('title', 'Untitled')[:60]
            snippet = r.get('content', r.get('snippet', ''))[:100]
            
            result_text = Text()
            result_text.append(f"    • ", style="ryx.primary")
            result_text.append(title)
            self.console.print(result_text)
            
            if snippet:
                self.console.print(Text(f"      {snippet}...", style="dim"))
    
    # ─────────────────────────────────────────────────────────────────────────
    # Live Progress Context
    # ─────────────────────────────────────────────────────────────────────────
    
    @contextmanager
    def live_progress(self, description: str = "Processing"):
        """
        Context manager for live progress display.
        
        Usage:
            with ui.live_progress("Analyzing") as progress:
                progress.update("Step 1")
                # do work
                progress.update("Step 2")
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[ryx.step]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            task = progress.add_task(description, total=None)
            
            class ProgressUpdater:
                def update(self, desc: str):
                    progress.update(task, description=desc)
            
            yield ProgressUpdater()
    
    # ─────────────────────────────────────────────────────────────────────────
    # Thinking/Chain of Thought Display
    # ─────────────────────────────────────────────────────────────────────────
    
    def thinking_start(self, step: str):
        """Show a thinking step starting (with animation)"""
        text = Text()
        text.append("  → ", style="ryx.info")
        text.append(step, style="dim")
        text.append("…")
        self.console.print(text)
    
    def thinking_done(self, step: str, result: str = ""):
        """Complete a thinking step"""
        text = Text()
        text.append("  ● ", style="ryx.success")
        text.append(step)
        if result:
            text.append(f" {result}", style="dim")
        self.console.print(text)
    
    def substep(self, detail: str):
        """Show a substep/detail"""
        text = Text()
        text.append("    · ", style="dim")
        text.append(detail, style="dim")
        self.console.print(text)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Animated Status Updates
    # ─────────────────────────────────────────────────────────────────────────
    
    def animate_action(self, action: str, callback, *args, **kwargs):
        """
        Run an action with animated spinner.
        
        Usage:
            result = ui.animate_action("Searching", search_func, query)
        """
        with Progress(
            SpinnerColumn(),
            TextColumn(f"[ryx.step]{action}…"),
            console=self.console,
            transient=True
        ) as progress:
            task = progress.add_task("", total=None)
            result = callback(*args, **kwargs)
        
        return result
    
    # ─────────────────────────────────────────────────────────────────────────
    # Final Status Bar (Bottom)
    # ─────────────────────────────────────────────────────────────────────────
    
    def print_final_status(
        self,
        model: str = "",
        msg_count: int = 0,
        tok_s: float = 0,
        branch: str = "",
        changes: int = 0
    ):
        """
        Print final status bar at bottom.
        
        Example:
        Model: qwen2.5 · 5 msgs · 1.2k tok/s | Git: main · 3 changes
        """
        parts = []
        
        if model:
            parts.append(f"Model: {model}")
        if msg_count > 0:
            parts.append(f"{msg_count} msgs")
        if tok_s > 0:
            if tok_s > 1000:
                parts.append(f"{tok_s/1000:.1f}k tok/s")
            else:
                parts.append(f"{tok_s:.1f} tok/s")
        
        left = " · ".join(parts)
        
        right_parts = []
        if branch:
            right_parts.append(f"Git: {branch}")
        if changes > 0:
            right_parts.append(f"{changes} changes")
        
        right = " · ".join(right_parts)
        
        # Combine
        if right:
            status = f"{left} | {right}"
        else:
            status = left
        
        self.console.print(Rule(style="ryx.border"))
        self.console.print(Text(status, style="dim"))


# ═══════════════════════════════════════════════════════════════════════════════
# Global Instance
# ═══════════════════════════════════════════════════════════════════════════════

_ui: Optional[RyxUI] = None


def get_ui() -> RyxUI:
    """Get or create global UI instance"""
    global _ui
    if _ui is None:
        _ui = RyxUI()
    return _ui
