"""
Ryx AI - Claude CLI Style UI

Ultra-clean interface like Claude Code / Copilot CLI.
ZERO noise - only what matters.

Design Philosophy:
- Spinner while thinking (no verbose steps)
- Clean streamed answer
- Stats AFTER answer (tokens, speed)
- Fixed footer at bottom with hints
- NO "Intent: X" noise
"""

import sys
import os
import time
import shutil
from typing import Optional, List, Dict, Any
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
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.style import Style
from rich.theme import Theme as RichTheme


# ═══════════════════════════════════════════════════════════════════════════════
# Theme - Catppuccin Mocha (darker, cleaner)
# ═══════════════════════════════════════════════════════════════════════════════

RYX_THEME = RichTheme({
    # Core colors
    "ok": "#a6e3a1",       # Green - success
    "err": "#f38ba8",      # Red - errors  
    "warn": "#f9e2af",     # Yellow - warnings
    "info": "#89b4fa",     # Blue - info
    "dim": "#585b70",      # Darker muted
    "muted": "#6c7086",    # Muted text
    "accent": "#cba6f7",   # Purple - brand
    "text": "#cdd6f4",     # Main text
    
    # Semantic
    "step": "#89dceb",     # Cyan - current step
    "model": "#f5c2e7",    # Pink - model name
    "path": "#fab387",     # Peach - file paths
    "branch": "#94e2d5",   # Teal - git branch
    "speed": "#a6e3a1",    # Green - tok/s
    
    # Diff colors
    "diff.add": "#a6e3a1",
    "diff.del": "#f38ba8",
    "diff.hdr": "#89b4fa",
    "diff.line": "#6c7086",
    
    # Structure  
    "border": "#313244",   # Darker border
    "header": "#cdd6f4 bold",
    "footer": "#45475a",
})


@dataclass
class StreamState:
    """State for token streaming"""
    tokens: int = 0
    start_time: float = field(default_factory=time.time)
    model: str = ""
    buffer: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# RyxUI - Clean Claude-style Interface
# ═══════════════════════════════════════════════════════════════════════════════

class RyxUI:
    """
    Ultra-clean Claude CLI-style UI.
    
    Design: ZERO noise, only what matters.
    - Spinner while thinking (no verbose steps)
    - Clean streamed answer
    - Stats after answer
    """
    
    def __init__(self):
        self.console = Console(theme=RYX_THEME, highlight=False)
        self.stream: Optional[StreamState] = None
        self._spinner = None
        self._live = None
        
    # ═══════════════════════════════════════════════════════════════════════════
    # Header - One line at startup
    # ═══════════════════════════════════════════════════════════════════════════
    
    def header(self, model: str = "", branch: str = "", cwd: str = ""):
        """
        ~/project [⎇ main]                                      qwen2.5-coder:14b
        ──────────────────────────────────────────────────────────────────────────
        """
        cwd = cwd or os.getcwd()
        path = cwd.replace(os.path.expanduser("~"), "~")
        
        left = Text()
        left.append(path, style="header")
        if branch:
            left.append(" [", style="dim")
            left.append("⎇ ", style="branch")
            left.append(branch, style="branch")
            left.append("]", style="dim")
        
        right = Text(model, style="model") if model else Text()
        
        w = self.console.width
        pad = w - len(left.plain) - len(right.plain) - 1
        
        self.console.print()
        self.console.print(left + Text(" " * max(1, pad)) + right)
        self.console.print(Rule(style="border"))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Thinking Spinner - Clean single indicator
    # ═══════════════════════════════════════════════════════════════════════════
    
    def thinking(self, text: str = "Thinking"):
        """Start thinking spinner: ⠋ Thinking..."""
        self._stop_spinner()
        spinner = Spinner("dots", text=f" {text}...", style="dim")
        self._live = Live(spinner, console=self.console, refresh_per_second=10, transient=True)
        self._live.start()
    
    def thinking_update(self, text: str):
        """Update spinner text"""
        if self._live:
            spinner = Spinner("dots", text=f" {text}...", style="dim")
            self._live.update(spinner)
    
    def thinking_done(self, result: str = ""):
        """Stop spinner, optionally show brief result"""
        self._stop_spinner()
        if result:
            self.console.print(Text(f"  ✓ {result}", style="dim"))
    
    def _stop_spinner(self):
        if self._live:
            self._live.stop()
            self._live = None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Actions - Brief one-liners
    # ═══════════════════════════════════════════════════════════════════════════
    
    def action(self, text: str):
        """Show action being taken: ▸ Searching web..."""
        self._stop_spinner()
        self.console.print(Text(f"  ▸ {text}", style="step"))
    
    def action_done(self, text: str, detail: str = ""):
        """Action completed: ✓ Found 5 results"""
        line = Text()
        line.append("  ✓ ", style="ok")
        line.append(text, style="text")
        if detail:
            line.append(f" ({detail})", style="dim")
        self.console.print(line)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Footer - Before prompt input
    # ═══════════════════════════════════════════════════════════════════════════
    
    def footer(self, model: str = "", msgs: int = 0, precision: bool = False):
        """
        ───────────────────────────────────────────────────────────────────────
        Ctrl+c Exit · /help                                 🎯 qwen2.5 · 12 msgs
        """
        self.console.print(Rule(style="border"))
        
        left = "Ctrl+c · /help"
        parts = []
        if precision:
            parts.append("🎯")
        if model:
            parts.append(model.split(':')[0])
        if msgs > 0:
            parts.append(f"{msgs}")
        right = " · ".join(parts)
        
        w = self.console.width
        pad = w - len(left) - len(right) - 1
        
        out = Text()
        out.append(left, style="dim")
        out.append(" " * max(1, pad))
        out.append(right, style="dim")
        self.console.print(out)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Steps - Compact One-Line Display
    # ═══════════════════════════════════════════════════════════════════════════
    
    def step(self, text: str, icon: str = "→", style: str = "step"):
        """Single step indicator: → Understanding..."""
        self.console.print(Text(f"  {icon} {text}", style=style))
    
    def step_done(self, text: str, result: str = ""):
        """Completed step: ✓ Analyzed intent"""
        line = Text()
        line.append("  ✓ ", style="ok")
        line.append(text)
        if result:
            line.append(f" → {result}", style="dim")
        self.console.print(line)
    
    def step_fail(self, text: str, error: str = ""):
        """Failed step: ✗ Failed to parse"""
        line = Text()
        line.append("  ✗ ", style="err")
        line.append(text)
        if error:
            line.append(f" ({error})", style="dim")
        self.console.print(line)
    
    def substep(self, text: str):
        """Indented substep:   · fetched 5 results"""
        self.console.print(Text(f"    · {text}", style="dim"))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Phases - Workflow Steps
    # ═══════════════════════════════════════════════════════════════════════════
    
    def phase(self, name: str, status: str = "run", detail: str = ""):
        """
        Workflow phase indicator.
        
        status: "run" | "ok" | "err" | "skip"
        
        ⏳ EXPLORE scanning...
        ✓ EXPLORE found 42 files
        """
        icons = {"run": "⏳", "ok": "✓", "err": "✗", "skip": "○"}
        styles = {"run": "step", "ok": "ok", "err": "err", "skip": "dim"}
        
        line = Text()
        line.append(f"{icons.get(status, '○')} ", style=styles.get(status, "dim"))
        line.append(name.upper(), style="accent bold")
        if detail:
            line.append(f" {detail}", style="dim")
        
        self.console.print(line)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Token Streaming - Clean Output
    # ═══════════════════════════════════════════════════════════════════════════
    
    def stream_start(self, model: str = ""):
        """Start response stream"""
        self.stream = StreamState(model=model)
        
        # Minimal header
        header = Text()
        header.append("\n")
        self.console.print(header, end="")
    
    def stream_token(self, token: str):
        """Stream a single token"""
        if self.stream:
            self.stream.tokens += 1
            self.stream.buffer += token
        sys.stdout.write(token)
        sys.stdout.flush()
    
    def stream_end(self) -> tuple:
        """End stream, return (tokens, tok/s, seconds)"""
        if not self.stream:
            print()
            return (0, 0, 0)
        
        elapsed = max(0.01, time.time() - self.stream.start_time)
        tokens = self.stream.tokens
        tps = tokens / elapsed
        
        print()  # End line
        
        # Compact stats line
        stats = Text()
        stats.append(f"  {tokens} tok", style="dim")
        stats.append(" · ", style="dim")
        stats.append(f"{tps:.0f} tok/s", style="info")
        stats.append(" · ", style="dim")
        stats.append(f"{elapsed:.1f}s", style="dim")
        self.console.print(stats)
        
        result = (tokens, tps, elapsed)
        self.stream = None
        return result
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Diff Display - Git Style
    # ═══════════════════════════════════════════════════════════════════════════
    
    def diff(self, filename: str, old: List[str], new: List[str]):
        """
        Show git-style diff.
        
        ┌─ file.py ──────────────
        │ 10  - old line
        │ 10  + new line
        └────────────────────────
        """
        import difflib
        
        d = list(difflib.unified_diff(old, new, lineterm=""))
        if len(d) < 3:
            return
        
        # Header
        title = f"┌─ {filename} " + "─" * max(1, 40 - len(filename))
        self.console.print(Text(title, style="border"))
        
        # Diff lines
        ln = 0
        for line in d[2:]:
            if line.startswith("@@"):
                try:
                    ln = int(line.split(" ")[2].split(",")[0].replace("+", ""))
                except:
                    pass
                continue
            
            row = Text()
            row.append("│ ", style="border")
            row.append(f"{ln:3d}  ", style="dim")
            
            if line.startswith("-"):
                row.append(line, style="diff.del")
            elif line.startswith("+"):
                row.append(line, style="diff.add")
                ln += 1
            else:
                row.append(line, style="diff.ctx")
                ln += 1
            
            self.console.print(row)
        
        # Footer
        self.console.print(Text("└" + "─" * 45, style="border"))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Messages - Simple Status
    # ═══════════════════════════════════════════════════════════════════════════
    
    def ok(self, msg: str):
        """✓ Success message"""
        self.console.print(Text(f"✓ {msg}", style="ok"))
    
    def err(self, msg: str):
        """✗ Error message"""
        self.console.print(Text(f"✗ {msg}", style="err"))
    
    def warn(self, msg: str):
        """⚠ Warning message"""
        self.console.print(Text(f"⚠ {msg}", style="warn"))
    
    def info(self, msg: str):
        """ℹ Info message"""
        self.console.print(Text(f"ℹ {msg}", style="info"))
    
    def muted(self, msg: str):
        """Dimmed text"""
        self.console.print(Text(msg, style="dim"))
    
    # Legacy compatibility
    def success(self, msg: str): self.ok(msg)
    def error(self, msg: str): self.err(msg)
    def warning(self, msg: str): self.warn(msg)
    def dim(self, msg: str): self.muted(msg)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Search Results - Compact
    # ═══════════════════════════════════════════════════════════════════════════
    
    def search_results(self, results: List[Dict], limit: int = 3):
        """
        Show search results compactly.
        
        Found 5 results:
          • Result title here
        """
        if not results:
            self.muted("No results")
            return
        
        self.console.print(Text(f"  Found {len(results)} results:", style="dim"))
        
        for r in results[:limit]:
            title = r.get('title', 'Untitled')[:55]
            line = Text()
            line.append("    • ", style="accent")
            line.append(title)
            self.console.print(line)
    
    # Legacy
    def show_search_results(self, results: List[Dict], limit: int = 5):
        self.search_results(results, limit)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Thinking Steps - Chain of Thought
    # ═══════════════════════════════════════════════════════════════════════════
    
    def thinking(self, step: str):
        """Show thinking step: → Analyzing..."""
        self.step(step, "→", "step")
    
    def thought(self, step: str, result: str = ""):
        """Completed thought: ● Intent: chat"""
        line = Text()
        line.append("  ● ", style="ok")
        line.append(step)
        if result:
            line.append(f" → {result}", style="dim")
        self.console.print(line)
    
    # Legacy compatibility
    def thinking_start(self, step: str): self.thinking(step)
    def thinking_done(self, step: str, result: str = ""): self.thought(step, result)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Task/Action Visualization
    # ═══════════════════════════════════════════════════════════════════════════
    
    def action_start(self, name: str):
        """Start an action with spinner effect: ⏳ Reading file..."""
        self.console.print(Text(f"⏳ {name}…", style="step"))
    
    def action_done(self, name: str, detail: str = ""):
        """Complete an action: ✓ Read file (42 lines)"""
        line = Text()
        line.append("✓ ", style="ok")
        line.append(name)
        if detail:
            line.append(f" ({detail})", style="dim")
        self.console.print(line)
    
    def action_fail(self, name: str, error: str = ""):
        """Failed action: ✗ Read file (not found)"""
        line = Text()
        line.append("✗ ", style="err")
        line.append(name)
        if error:
            line.append(f" ({error})", style="dim")
        self.console.print(line)
    
    # Legacy
    def task_start(self, name: str, details: str = "") -> str:
        self.action_start(name)
        return name
    
    def task_done(self, name: str, details: str = "", success: bool = True):
        if success:
            self.action_done(name, details)
        else:
            self.action_fail(name, details)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Code Display
    # ═══════════════════════════════════════════════════════════════════════════
    
    def code(self, content: str, language: str = "python", title: str = ""):
        """Show code with syntax highlighting"""
        syntax = Syntax(content, language, theme="monokai", line_numbers=True)
        if title:
            panel = Panel(syntax, title=f"[path]{title}[/]", border_style="border", padding=(0, 1))
            self.console.print(panel)
        else:
            self.console.print(syntax)
    
    # Legacy
    def show_file_preview(self, filename: str, content: str, language: str = "python"):
        self.code(content, language, filename)
    
    def show_diff(self, filename: str, old: List[str], new: List[str], context_lines: int = 3):
        self.diff(filename, old, new)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Error with Context
    # ═══════════════════════════════════════════════════════════════════════════
    
    def error_detail(self, file: str, error: str, line: int = None, suggestion: str = None):
        """
        Show error with details.
        
        ✗ tests/test.py
          ERROR: AssertionError (line 45)
          Fix: Check condition
        """
        self.console.print(Text(f"✗ {file}", style="err"))
        
        detail = f"  ERROR: {error}"
        if line:
            detail += f" (line {line})"
        self.console.print(Text(detail, style="dim"))
        
        if suggestion:
            self.console.print(Text(f"  Fix: {suggestion}", style="warn"))
    
    # Legacy
    def show_error(self, file: str, error: str, line: int = None, suggestion: str = None):
        self.error_detail(file, error, line, suggestion)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Legacy Compatibility Layer
    # ═══════════════════════════════════════════════════════════════════════════
    
    def print_status_bar(self, **kwargs):
        """Legacy: print header"""
        self.header(
            model=kwargs.get('model', ''),
            branch=kwargs.get('branch', ''),
            cwd=kwargs.get('cwd', '')
        )
    
    def print_bottom_hints(self, left: str = "", right: str = ""):
        """Legacy: print footer"""
        # Extract model info from right
        model = ""
        msgs = 0
        if right:
            parts = right.split(" · ")
            for p in parts:
                if "msgs" in p:
                    try:
                        msgs = int(p.split()[0])
                    except:
                        pass
                elif not any(x in p for x in ["msgs", "Exit", "help"]):
                    model = p
        self.footer(model=model, msgs=msgs)
    
    def phase_start(self, name: str, description: str = ""):
        self.phase(name, "run", description)
    
    def phase_done(self, name: str, result: str = "", success: bool = True):
        self.phase(name, "ok" if success else "err", result)
    
    def phase_step(self, step_num: int, description: str, status: str = "pending"):
        icons = {"done": "✓", "running": "▸", "error": "✗", "pending": "○"}
        styles = {"done": "ok", "running": "step", "error": "err", "pending": "dim"}
        line = Text()
        line.append(f"    {icons.get(status, '○')} ", style=styles.get(status, "dim"))
        line.append(f"{step_num}. {description}")
        self.console.print(line)
    
    def print_final_status(self, **kwargs):
        """Legacy: final status"""
        pass  # Now handled inline
    
    def task_update(self, name: str, details: str):
        self.substep(details)
    
    @contextmanager
    def live_progress(self, description: str = "Processing"):
        """Context manager for live progress"""
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
        """Run action with spinner"""
        with Progress(
            SpinnerColumn(),
            TextColumn(f"[step]{action}…"),
            console=self.console,
            transient=True
        ):
            return callback(*args, **kwargs)


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
