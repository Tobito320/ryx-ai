"""
Ryx AI - Claude CLI Style UI v2

Production-ready CLI interface matching Claude Code / Copilot CLI exactly.

Features:
- Fixed bottom status bar (like Claude)
- Clean spinner while thinking
- Token streaming with stats
- Diff display for code changes
- Phase visualization (EXPLORE → PLAN → APPLY → VERIFY)
- NO verbose output - only what matters
"""

import sys
import os
import time
import shutil
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from contextlib import contextmanager

from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner
from rich.syntax import Syntax
from rich.rule import Rule
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.style import Style
from rich.theme import Theme as RichTheme
from rich.layout import Layout
from rich.align import Align


# ═══════════════════════════════════════════════════════════════════════════════
# Theme - Catppuccin Mocha
# ═══════════════════════════════════════════════════════════════════════════════

THEME = RichTheme({
    # Core
    "success": "#a6e3a1",    # Green
    "error": "#f38ba8",      # Red  
    "warning": "#f9e2af",    # Yellow
    "info": "#89b4fa",       # Blue
    "muted": "#585b70",      # Dark muted
    "dim": "#6c7086",        # Muted
    "accent": "#cba6f7",     # Purple - brand
    "text": "#cdd6f4",       # Main text
    
    # Semantic
    "step": "#89dceb",       # Cyan
    "model": "#f5c2e7",      # Pink
    "path": "#fab387",       # Peach
    "branch": "#94e2d5",     # Teal
    "speed": "#a6e3a1",      # Green
    "tokens": "#89b4fa",     # Blue
    
    # Diff
    "diff.add": "#a6e3a1 bold",
    "diff.del": "#f38ba8 bold",
    "diff.hdr": "#89b4fa",
    "diff.ctx": "#6c7086",
    "diff.line": "#45475a",
    
    # Phases
    "phase.idle": "#6c7086",
    "phase.explore": "#89b4fa",
    "phase.plan": "#f9e2af",
    "phase.apply": "#cba6f7",
    "phase.verify": "#a6e3a1",
    
    # Structure  
    "border": "#313244",
    "header": "#cdd6f4 bold",
    "footer.bg": "#1e1e2e",
})


@dataclass 
class ResponseStats:
    """Stats from a response"""
    tokens: int = 0
    duration: float = 0.0
    model: str = ""
    
    @property
    def tok_per_sec(self) -> float:
        if self.duration > 0:
            return self.tokens / self.duration
        return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# CLI UI - Main Interface
# ═══════════════════════════════════════════════════════════════════════════════

class CLI:
    """
    Claude CLI-style interface.
    
    Usage:
        ui = CLI()
        ui.header(model="qwen2.5:7b", branch="main")
        
        with ui.spinner("Thinking"):
            result = do_something()
        
        ui.stream_start("qwen2.5:7b")
        for token in tokens:
            ui.stream_token(token)
        stats = ui.stream_end()
        
        ui.footer()  # Shows at bottom
    """
    
    def __init__(self):
        self.console = Console(theme=THEME, highlight=False)
        self._live: Optional[Live] = None
        self._stream_state: Optional[Dict] = None
        self._last_stats: Optional[ResponseStats] = None
        
        # Terminal size
        self.width = shutil.get_terminal_size().columns
        self.height = shutil.get_terminal_size().lines
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Header - Top bar with path/model
    # ═══════════════════════════════════════════════════════════════════════════
    
    def header(self, model: str = "", branch: str = "", cwd: str = ""):
        """
        Print header like Claude CLI:
        
        ~/ryx-ai [⎇ main]                                    qwen2.5-coder:14b
        ──────────────────────────────────────────────────────────────────────
        """
        cwd = cwd or os.getcwd()
        path = cwd.replace(os.path.expanduser("~"), "~")
        
        # Left side: path + branch
        left = Text()
        left.append(path, style="header")
        if branch:
            left.append("[", style="muted")
            left.append("⎇ ", style="branch")
            left.append(branch, style="branch")
            left.append("]", style="muted")
        
        # Right side: model
        right = Text(model, style="model") if model else Text()
        
        # Calculate padding
        pad = self.width - len(left.plain) - len(right.plain) - 2
        
        self.console.print()
        line = left + Text(" " * max(1, pad)) + right
        self.console.print(line)
        self.console.print(Rule(style="border"))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Footer - Bottom hints (like Claude CLI)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def footer(self, model: str = "", msgs: int = 0, precision: bool = False, 
               tok_s: float = 0.0, extra: str = ""):
        """
        Print footer hints like Claude CLI:
        
        ─────────────────────────────────────────────────────────────────────────
        Ctrl+c Exit · /help                                 qwen2.5 · 12 msgs
        """
        self.console.print(Rule(style="border"))
        
        # Left: hints
        left = Text("Ctrl+c Exit · /help · @ files", style="muted")
        
        # Right: model + stats
        parts = []
        if precision:
            parts.append("🎯")
        if model:
            # Short model name
            short = model.split(":")[0].split("/")[-1]
            parts.append(short)
        if msgs > 0:
            parts.append(f"{msgs} msgs")
        if tok_s > 0:
            parts.append(f"{tok_s:.0f} tok/s")
        
        right = Text(" · ".join(parts), style="dim")
        
        pad = self.width - len(left.plain) - len(right.plain) - 2
        line = left + Text(" " * max(1, pad)) + right
        self.console.print(line)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Spinner - For thinking/loading
    # ═══════════════════════════════════════════════════════════════════════════
    
    @contextmanager
    def spinner(self, text: str = "Thinking"):
        """
        Context manager for spinner:
        
        with ui.spinner("Searching"):
            results = search()
        """
        spinner = Spinner("dots", text=f"  {text}...", style="dim")
        self._live = Live(spinner, console=self.console, refresh_per_second=12, transient=True)
        self._live.start()
        try:
            yield
        finally:
            if self._live:
                self._live.stop()
                self._live = None
    
    def spinner_update(self, text: str):
        """Update spinner text while running"""
        if self._live:
            spinner = Spinner("dots", text=f"  {text}...", style="dim")
            self._live.update(spinner)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Streaming - Token by token output
    # ═══════════════════════════════════════════════════════════════════════════
    
    def stream_start(self, model: str = ""):
        """Start streaming response"""
        self._stream_state = {
            "tokens": 0,
            "start": time.time(),
            "model": model,
            "buffer": "",
            "line_started": False
        }
        # Print model indicator
        short = model.split(":")[0].split("/")[-1] if model else "Ryx"
        self.console.print(f"\n[accent bold]{short}[/]: ", end="")
        self._stream_state["line_started"] = True
    
    def stream_token(self, token: str):
        """Print a single token"""
        if self._stream_state:
            self._stream_state["tokens"] += 1
            self._stream_state["buffer"] += token
            # Print directly
            sys.stdout.write(token)
            sys.stdout.flush()
    
    def stream_end(self) -> ResponseStats:
        """End streaming, return stats"""
        if not self._stream_state:
            return ResponseStats()
        
        duration = time.time() - self._stream_state["start"]
        tokens = self._stream_state["tokens"]
        model = self._stream_state["model"]
        
        stats = ResponseStats(tokens=tokens, duration=duration, model=model)
        self._last_stats = stats
        
        # Print stats on new line
        tok_s = stats.tok_per_sec
        self.console.print(f"\n  [dim]{tokens} tokens · {tok_s:.1f} tok/s · {duration:.1f}s[/]")
        
        self._stream_state = None
        return stats
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Simple Messages
    # ═══════════════════════════════════════════════════════════════════════════
    
    def success(self, msg: str):
        """✓ Success message"""
        self.console.print(Text(f"✓ {msg}", style="success"))
    
    def error(self, msg: str):
        """✗ Error message"""
        self.console.print(Text(f"✗ {msg}", style="error"))
    
    def warn(self, msg: str):
        """⚠ Warning message"""
        self.console.print(Text(f"⚠ {msg}", style="warning"))
    
    def info(self, msg: str):
        """ℹ Info message"""
        self.console.print(Text(f"ℹ {msg}", style="info"))
    
    def muted(self, msg: str):
        """Muted helper text"""
        self.console.print(Text(msg, style="muted"))
    
    def nl(self):
        """Print newline"""
        self.console.print()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Steps - For multi-step operations
    # ═══════════════════════════════════════════════════════════════════════════
    
    def step_start(self, text: str):
        """
        ⏳ Reading file...
        """
        self.console.print(Text(f"⏳ {text}…", style="step"))
    
    def step_done(self, text: str, detail: str = ""):
        """
        ✓ Read file
        └─ 42 lines
        """
        self.console.print(Text(f"✓ {text}", style="success"))
        if detail:
            self.console.print(Text(f"└─ {detail}", style="dim"))
    
    def step_fail(self, text: str, error: str = ""):
        """
        ✗ Read file
        └─ File not found
        """
        self.console.print(Text(f"✗ {text}", style="error"))
        if error:
            self.console.print(Text(f"└─ {error}", style="dim"))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Phases - For complex tasks (EXPLORE → PLAN → APPLY → VERIFY)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def phase(self, name: str, status: str = "run", detail: str = ""):
        """
        Show phase status:
        
        ● EXPLORE  Scanning repository...
        ✓ EXPLORE  Found 42 files
        """
        icons = {
            "idle": "○",
            "run": "●", 
            "ok": "✓",
            "done": "✓",
            "err": "✗",
            "skip": "○"
        }
        styles = {
            "idle": "phase.idle",
            "run": "step",
            "ok": "success",
            "done": "success", 
            "err": "error",
            "skip": "muted"
        }
        
        icon = icons.get(status, "●")
        style = styles.get(status, "dim")
        
        line = Text()
        line.append(f"{icon} ", style=style)
        line.append(f"{name:8}", style=f"{style} bold")
        if detail:
            line.append(f"  {detail}", style="dim")
        
        self.console.print(line)
    
    def phase_steps(self, steps: List[str], current: int = -1):
        """
        Show steps within a phase:
        
        ✓ 1. Identify files
        ▸ 2. Analyze structure  
        ○ 3. Generate code
        """
        for i, step in enumerate(steps):
            if i < current:
                icon, style = "✓", "success"
            elif i == current:
                icon, style = "▸", "step"
            else:
                icon, style = "○", "muted"
            
            self.console.print(Text(f"    {icon} {i+1}. {step}", style=style))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Diff Display - For code changes
    # ═══════════════════════════════════════════════════════════════════════════
    
    def diff(self, filename: str, old_lines: List[str], new_lines: List[str]):
        """
        Show unified diff like git:
        
        ┌─ core/brain.py (modified) ─────────────────────────
        │  42  -   def old_function():
        │  42  +   def new_function():
        └────────────────────────────────────────────────────
        """
        import difflib
        
        diff_lines = list(difflib.unified_diff(
            old_lines, new_lines,
            fromfile=filename,
            tofile=filename,
            lineterm=""
        ))
        
        if not diff_lines:
            return
        
        # Build diff content
        content = []
        for line in diff_lines[2:]:  # Skip header
            if line.startswith("+"):
                content.append(Text(f"│  {line}", style="diff.add"))
            elif line.startswith("-"):
                content.append(Text(f"│  {line}", style="diff.del"))
            elif line.startswith("@@"):
                content.append(Text(f"│  {line}", style="diff.hdr"))
            else:
                content.append(Text(f"│  {line}", style="diff.ctx"))
        
        # Header
        self.console.print(Text(f"┌─ {filename} (modified) ", style="diff.hdr") + 
                          Text("─" * (self.width - len(filename) - 20), style="border"))
        
        # Content
        for line in content[:20]:  # Limit lines
            self.console.print(line)
        
        if len(content) > 20:
            self.console.print(Text(f"│  ... {len(content) - 20} more lines", style="muted"))
        
        # Footer
        self.console.print(Text("└" + "─" * (self.width - 2), style="border"))
    
    def diff_summary(self, files: List[Dict[str, Any]]):
        """
        Show summary of all changes:
        
        Changes:
          ✓ core/brain.py        +15 -3
          ✓ core/tools.py        +42 -0 (new)
        """
        if not files:
            return
        
        self.console.print(Text("\nChanges:", style="header"))
        for f in files:
            name = f.get("name", "unknown")
            added = f.get("added", 0)
            removed = f.get("removed", 0)
            status = f.get("status", "modified")
            
            line = Text("  ✓ ", style="success")
            line.append(f"{name:30}", style="path")
            line.append(f"+{added} -{removed}", style="dim")
            if status == "new":
                line.append(" (new)", style="info")
            
            self.console.print(line)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Code Display
    # ═══════════════════════════════════════════════════════════════════════════
    
    def code(self, content: str, language: str = "python", title: str = "", 
             line_numbers: bool = True):
        """Show code with syntax highlighting"""
        syntax = Syntax(
            content, language, 
            theme="monokai", 
            line_numbers=line_numbers,
            word_wrap=True
        )
        
        if title:
            panel = Panel(
                syntax, 
                title=f"[path]{title}[/]", 
                border_style="border",
                padding=(0, 1)
            )
            self.console.print(panel)
        else:
            self.console.print(syntax)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Search Results
    # ═══════════════════════════════════════════════════════════════════════════
    
    def search_results(self, results: List[Dict], query: str = "", limit: int = 5):
        """
        Show search results cleanly:
        
        Found 5 results for "recursion":
        
        1. Introduction to Recursion - GeeksforGeeks
           geeksforgeeks.org
        
        2. Recursion - Wikipedia  
           en.wikipedia.org
        """
        if not results:
            self.muted("No results found")
            return
        
        # Header
        if query:
            self.console.print(Text(f"\nFound {len(results)} results for \"{query}\":", style="dim"))
        
        # Results
        for i, r in enumerate(results[:limit]):
            title = r.get("title", "No title")[:60]
            url = r.get("url", "")
            snippet = r.get("snippet", r.get("content", ""))[:80]
            
            # Extract domain - handle DuckDuckGo redirect URLs
            domain = ""
            if url:
                try:
                    from urllib.parse import urlparse, parse_qs, unquote
                    parsed = urlparse(url)
                    
                    # DuckDuckGo uses ?uddg=<real_url> redirect
                    if "duckduckgo.com" in parsed.netloc and "uddg" in url:
                        query_params = parse_qs(parsed.query)
                        if "uddg" in query_params:
                            real_url = unquote(query_params["uddg"][0])
                            domain = urlparse(real_url).netloc.replace("www.", "")
                    else:
                        domain = parsed.netloc.replace("www.", "")
                except:
                    domain = url[:40]
            
            self.console.print()
            self.console.print(Text(f"  {i+1}. ", style="accent") + Text(title, style="text bold"))
            if domain:
                self.console.print(Text(f"     {domain}", style="muted"))
            if snippet:
                # Clean snippet
                clean = snippet.replace("\n", " ").strip()[:80]
                self.console.print(Text(f"     {clean}...", style="dim"))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Error Display
    # ═══════════════════════════════════════════════════════════════════════════
    
    def error_detail(self, file: str, error: str, line: int = None, 
                     suggestion: str = None):
        """
        Show error with context:
        
        ✗ tests/test_brain.py
          ERROR: AssertionError (line 45)
          Suggestion: Check the expected value
        """
        self.console.print(Text(f"✗ {file}", style="error"))
        
        msg = f"  ERROR: {error}"
        if line:
            msg += f" (line {line})"
        self.console.print(Text(msg, style="dim"))
        
        if suggestion:
            self.console.print(Text(f"  Suggestion: {suggestion}", style="warning"))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Prompt - Get user input
    # ═══════════════════════════════════════════════════════════════════════════
    
    def prompt(self) -> str:
        """
        Get user input with styled prompt:
        
        > _
        """
        try:
            return input("\n\033[38;2;203;166;247m>\033[0m ").strip()
        except EOFError:
            return "/quit"
        except KeyboardInterrupt:
            print()
            return ""
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Assistant Response (non-streaming)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def assistant(self, msg: str, model: str = ""):
        """Print assistant response"""
        short = model.split(":")[0].split("/")[-1] if model else "Ryx"
        self.console.print(f"\n[accent bold]{short}[/]: {msg}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Help Box
    # ═══════════════════════════════════════════════════════════════════════════
    
    def help_box(self, sections: Dict[str, List[tuple]]):
        """
        Show help in a nice box:
        
        ╭─ 🟣 Ryx Help ─────────────────────────────────────────╮
        │ COMMANDS:                                             │
        │   /help        Show this help                         │
        │   /quit        Exit                                   │
        ╰───────────────────────────────────────────────────────╯
        """
        content = []
        
        for section, items in sections.items():
            content.append(Text(f"{section}:", style="header"))
            for cmd, desc in items:
                line = Text()
                line.append(f"  {cmd:18}", style="accent")
                line.append(desc, style="dim")
                content.append(line)
            content.append(Text())
        
        panel = Panel(
            Group(*content),
            title="[accent]🟣 Ryx Help[/]",
            border_style="border",
            padding=(1, 2)
        )
        self.console.print(panel)


# ═══════════════════════════════════════════════════════════════════════════════
# Legacy Compatibility - Map old RyxUI calls to new CLI
# ═══════════════════════════════════════════════════════════════════════════════

class RyxUI(CLI):
    """Legacy compatibility wrapper"""
    
    def __init__(self):
        super().__init__()
    def err(self, msg: str): self.error(msg)
    def ok(self, msg: str): self.success(msg)
    def warning(self, msg: str): self.warn(msg)
    
    def thinking(self, text: str = "Thinking"):
        """Legacy: start spinner"""
        self._stop_spinner()
        spinner = Spinner("dots", text=f"  {text}...", style="dim")
        self._live = Live(spinner, console=self.console, refresh_per_second=12, transient=True)
        self._live.start()
    
    def thinking_done(self, result: str = ""):
        """Legacy: stop spinner"""
        self._stop_spinner()
    
    def _stop_spinner(self):
        if self._live:
            self._live.stop()
            self._live = None
    
    def print_status_bar(self, **kwargs):
        self.header(**kwargs)
    
    def print_bottom_hints(self, left: str = "", right: str = ""):
        self.footer()
    
    # Legacy step methods
    def step(self, text: str, icon: str = "▸", style: str = "step"):
        line = Text()
        line.append(f"  {icon} ", style=style)
        line.append(text)
        self.console.print(line)
    
    def substep(self, text: str):
        self.console.print(Text(f"    · {text}", style="dim"))
    
    def thought(self, step: str, result: str = ""):
        line = Text()
        line.append("  ● ", style="success")
        line.append(step)
        if result:
            line.append(f" → {result}", style="dim")
        self.console.print(line)
    
    # Action methods
    def action_start(self, name: str):
        self.step_start(name)
    
    def action_done(self, name: str, detail: str = ""):
        self.step_done(name, detail)
    
    def action_fail(self, name: str, error: str = ""):
        self.step_fail(name, error)
    
    def task_start(self, name: str, details: str = "") -> str:
        self.step_start(name)
        return name
    
    def task_done(self, name: str, details: str = "", success: bool = True):
        if success:
            self.step_done(name, details)
        else:
            self.step_fail(name, details)
    
    # Phase methods
    def phase_start(self, name: str, description: str = ""):
        self.phase(name, "run", description)
    
    def phase_done(self, name: str, result: str = "", success: bool = True):
        self.phase(name, "ok" if success else "err", result)
    
    def phase_step(self, step_num: int, description: str, status: str = "pending"):
        icons = {"done": "✓", "running": "▸", "error": "✗", "pending": "○"}
        styles = {"done": "success", "running": "step", "error": "error", "pending": "muted"}
        line = Text()
        line.append(f"    {icons.get(status, '○')} ", style=styles.get(status, "muted"))
        line.append(f"{step_num}. {description}")
        self.console.print(line)
    
    # Search results
    def show_search_results(self, results: List[Dict], limit: int = 5):
        self.search_results(results, limit=limit)
    
    # Code display
    def show_file_preview(self, filename: str, content: str, language: str = "python"):
        self.code(content, language, filename)
    
    def show_diff(self, filename: str, old: List[str], new: List[str], context_lines: int = 3):
        self.diff(filename, old, new)
    
    # Error display  
    def show_error(self, file: str, error: str, line: int = None, suggestion: str = None):
        self.error_detail(file, error, line, suggestion)
    
    # Other legacy
    def print_final_status(self, **kwargs):
        pass
    
    def task_update(self, name: str, details: str):
        self.substep(details)
    
    @contextmanager
    def live_progress(self, description: str = "Processing"):
        with Progress(
            SpinnerColumn(),
            TextColumn("[step]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            task = progress.add_task(description, total=None)
            class Updater:
                def update(self, desc: str):
                    progress.update(task, description=desc)
            yield Updater()
    
    def animate_action(self, action: str, callback, *args, **kwargs):
        with self.spinner(action):
            return callback(*args, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# Global Instances - MUST be after class definitions
# ═══════════════════════════════════════════════════════════════════════════════

_cli: Optional[RyxUI] = None


def get_cli() -> RyxUI:
    """Get or create global CLI instance"""
    global _cli
    if _cli is None:
        _cli = RyxUI()
    return _cli


def get_ui() -> RyxUI:
    """Get or create global UI instance (legacy compat)"""
    return get_cli()
