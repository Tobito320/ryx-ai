"""
Ryx AI - Copilot CLI Style UI

Layout:
┌─────────────────────────────────────────────────────────────────────┐
│ ~/ryx-ai [main]                                    qwen2.5-coder:14b│
├─────────────────────────────────────────────────────────────────────┤
│ > your prompt here                                                  │
├─────────────────────────────────────────────────────────────────────┤
│ Ctrl+c Exit · Ctrl+r Recent                              3 messages │
└─────────────────────────────────────────────────────────────────────┘

Colors:
- Purple: User prompt
- Green: Success/Ryx reply  
- Cyan: Steps/progress
- Yellow: Confirmation requests
- Red: Errors
- Dim: Status/info
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
    "success": "#a6e3a1",      # Green - success, replies
    "error": "#f38ba8",        # Red - errors
    "warning": "#f9e2af",      # Yellow - warnings, confirmations
    "info": "#89b4fa",         # Blue - info
    "muted": "#6c7086",        # Muted text
    "dim": "#45475a",          # Very dim
    "accent": "#cba6f7",       # Purple - user prompts, brand
    "text": "#cdd6f4",         # Main text
    
    # Semantic
    "step": "#89dceb",         # Cyan - steps/progress
    "confirm": "#f9e2af",      # Yellow - confirmation requests
    "reply": "#a6e3a1",        # Green - AI replies
    "user": "#cba6f7",         # Purple - user input
    "model": "#f5c2e7",        # Pink - model names
    "path": "#fab387",         # Peach - file paths
    "branch": "#94e2d5",       # Teal - git branch
    
    # Diff colors
    "diff.add": "#a6e3a1",
    "diff.del": "#f38ba8",
    "diff.hdr": "#89b4fa",
    "diff.line": "#6c7086",
    
    # Phase colors
    "phase.explore": "#89b4fa",
    "phase.plan": "#f9e2af",
    "phase.apply": "#cba6f7",
    "phase.verify": "#a6e3a1",
    
    # Structure  
    "border": "#585b70",
    "bar": "#313244",
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
# CLI - Main Interface with Bottom Bar Layout
# ═══════════════════════════════════════════════════════════════════════════════

class CLI:
    """
    Copilot CLI style with bottom status bar.
    
    Layout:
    ┌─────────────────────────────────────────────────────────────────────┐
    │ ~/path [branch]                                              model │
    ├─────────────────────────────────────────────────────────────────────┤
    │ > prompt                                                           │
    ├─────────────────────────────────────────────────────────────────────┤
    │ Ctrl+c Exit · Ctrl+r Recent                            N messages  │
    └─────────────────────────────────────────────────────────────────────┘
    """
    
    def __init__(self):
        self.console = Console(theme=THEME, highlight=False)
        self._live: Optional[Live] = None
        self._stream_state: Optional[Dict] = None
        self._last_stats: Optional[ResponseStats] = None
        
        # Terminal size
        self.width = shutil.get_terminal_size().columns
        self.height = shutil.get_terminal_size().lines
        
        # Session state
        self.msg_count = 0
        self.last_tok_s = 0.0
        self.current_model = ""
        self.current_branch = ""
        self.current_path = ""
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Status Bar - Top line (path + branch | model)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _top_bar(self, model: str = "", branch: str = "", cwd: str = "") -> Text:
        """Build top status bar content"""
        cwd = cwd or self.current_path or os.getcwd()
        path = cwd.replace(os.path.expanduser("~"), "~")
        branch = branch or self.current_branch
        model = model or self.current_model
        
        # Left: path + branch
        left = Text()
        left.append(path, style="path")
        if branch:
            left.append(" [", style="dim")
            left.append(branch, style="branch")
            left.append("]", style="dim")
        
        # Right: model
        right = Text()
        if model:
            short = model.split(":")[0].split("/")[-1]
            right.append(short, style="model")
        
        # Pad between left and right
        pad = self.width - len(left.plain) - len(right.plain) - 4
        return left + Text(" " * max(1, pad)) + right
    
    def _bottom_bar(self) -> Text:
        """Build bottom status bar content"""
        # Left: shortcuts
        left = Text()
        left.append("Ctrl+c", style="muted")
        left.append(" Exit · ", style="dim")
        left.append("Ctrl+r", style="muted")
        left.append(" Recent", style="dim")
        
        # Right: message count + tok/s
        right = Text()
        if self.msg_count > 0:
            right.append(f"{self.msg_count} messages", style="muted")
        if self.last_tok_s > 0:
            if self.msg_count > 0:
                right.append(" · ", style="dim")
            right.append(f"{self.last_tok_s:.0f} tok/s", style="muted")
        
        pad = self.width - len(left.plain) - len(right.plain) - 4
        return left + Text(" " * max(1, pad)) + right
    
    def draw_frame(self, model: str = "", branch: str = "", cwd: str = ""):
        """
        Draw the complete frame with status bars.
        Called once at start and when refreshing.
        """
        # Store for later use
        if model:
            self.current_model = model
        if branch:
            self.current_branch = branch
        if cwd:
            self.current_path = cwd
        
        # Top border + content
        self.console.print("┌" + "─" * (self.width - 2) + "┐", style="border")
        
        top_content = self._top_bar(model, branch, cwd)
        self.console.print(Text("│ ", style="border") + top_content + Text(" │", style="border"))
        
        # Middle separator
        self.console.print("├" + "─" * (self.width - 2) + "┤", style="border")
    
    def draw_bottom(self):
        """Draw bottom bar after content"""
        # Bottom separator
        self.console.print("├" + "─" * (self.width - 2) + "┤", style="border")
        
        bottom_content = self._bottom_bar()
        self.console.print(Text("│ ", style="border") + bottom_content + Text(" │", style="border"))
        
        # Bottom border
        self.console.print("└" + "─" * (self.width - 2) + "┘", style="border")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Prompt - Inside the frame
    # ═══════════════════════════════════════════════════════════════════════════
    
    def prompt(self) -> str:
        """
        Get user input with purple prompt indicator.
        """
        try:
            # Purple > prompt
            user_input = input("\033[38;2;203;166;247m❯\033[0m ").strip()
            self.msg_count += 1
            return user_input
        except EOFError:
            return "/quit"
        except KeyboardInterrupt:
            print()
            return ""
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Welcome - Initial frame draw
    # ═══════════════════════════════════════════════════════════════════════════
    
    def welcome(self, model: str = "", branch: str = "", cwd: str = ""):
        """Draw initial frame once"""
        self.draw_frame(model, branch, cwd)
        self.console.print()  # Blank line after frame
    
    def header(self, model: str = "", branch: str = "", cwd: str = ""):
        """Alias for welcome"""
        self.welcome(model, branch, cwd)
    
    def footer(self, model: str = "", msgs: int = 0, precision: bool = False,
               tok_s: float = 0.0, extra: str = ""):
        """Update state and draw bottom bar"""
        if msgs > 0:
            self.msg_count = msgs
        if tok_s > 0:
            self.last_tok_s = tok_s
        self.draw_bottom()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Spinner - Minimal thinking indicator (cyan)
    # ═══════════════════════════════════════════════════════════════════════════
    
    @contextmanager
    def spinner(self, text: str = ""):
        """Spinner in step color (cyan)"""
        display_text = f" {text}" if text else ""
        spinner = Spinner("dots", text=display_text, style="step")
        self._live = Live(spinner, console=self.console, refresh_per_second=12, transient=True)
        self._live.start()
        try:
            yield
        finally:
            if self._live:
                self._live.stop()
                self._live = None
    
    def spinner_update(self, text: str):
        """Update spinner text"""
        if self._live:
            spinner = Spinner("dots", text=f" {text}", style="step")
            self._live.update(spinner)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Streaming - Token output (green = reply)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def stream_start(self, model: str = ""):
        """Start streaming - replies are green"""
        self._stream_state = {
            "tokens": 0,
            "start": time.time(),
            "model": model,
            "buffer": "",
        }
        # Start with newline, content will be green
        print()  
        sys.stdout.write("\033[38;2;166;227;161m")  # Green for reply
    
    def stream_token(self, token: str):
        """Print a single token (in green)"""
        if self._stream_state:
            self._stream_state["tokens"] += 1
            self._stream_state["buffer"] += token
            sys.stdout.write(token)
            sys.stdout.flush()
    
    def stream_end(self) -> ResponseStats:
        """End streaming, show stats"""
        sys.stdout.write("\033[0m")  # Reset color
        
        if not self._stream_state:
            return ResponseStats()
        
        duration = time.time() - self._stream_state["start"]
        tokens = self._stream_state["tokens"]
        model = self._stream_state["model"]
        
        stats = ResponseStats(tokens=tokens, duration=duration, model=model)
        self._last_stats = stats
        self.last_tok_s = stats.tok_per_sec
        
        # Stats on new line (muted)
        tok_s = stats.tok_per_sec
        self.console.print(f"\n[dim]{tokens} tokens · {tok_s:.0f} tok/s · {duration:.1f}s[/]")
        
        self._stream_state = None
        return stats
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Messages - Color-coded output
    # ═══════════════════════════════════════════════════════════════════════════
    
    def success(self, msg: str):
        """✓ Success (green)"""
        self.console.print(Text(f"✓ {msg}", style="success"))
    
    def error(self, msg: str):
        """✗ Error (red)"""
        self.console.print(Text(f"✗ {msg}", style="error"))
    
    def warn(self, msg: str):
        """⚠ Warning (yellow)"""
        self.console.print(Text(f"⚠ {msg}", style="warning"))
    
    def info(self, msg: str):
        """ℹ Info (blue)"""
        self.console.print(Text(f"ℹ {msg}", style="info"))
    
    def muted(self, msg: str):
        """Muted helper text"""
        self.console.print(Text(msg, style="muted"))
    
    def step(self, msg: str):
        """● Step/progress (cyan)"""
        self.console.print(Text(f"● {msg}", style="step"))
    
    def confirm(self, msg: str) -> bool:
        """? Confirmation request (yellow) - returns True/False"""
        self.console.print(Text(f"? {msg} ", style="confirm"), end="")
        try:
            response = input("[y/N] ").strip().lower()
            return response in ['y', 'yes', 'ja', 'j']
        except:
            return False
    
    def reply(self, msg: str):
        """AI Reply (green)"""
        self.console.print(Text(msg, style="reply"))
    
    def nl(self):
        """Newline"""
        self.console.print()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Steps - Progress indicators (cyan)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def step_start(self, text: str):
        """● Running step (cyan)"""
        self.console.print(Text(f"● {text}...", style="step"))
    
    def step_done(self, text: str, detail: str = ""):
        """✓ Step complete (green)"""
        line = Text(f"✓ {text}", style="success")
        if detail:
            line.append(f" ({detail})", style="dim")
        self.console.print(line)
    
    def step_fail(self, text: str, error: str = ""):
        """✗ Step failed (red)"""
        line = Text(f"✗ {text}", style="error")
        if error:
            line.append(f" - {error}", style="dim")
        self.console.print(line)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Phases - For complex tasks (EXPLORE → PLAN → APPLY → VERIFY)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def phase(self, name: str, status: str = "run", detail: str = ""):
        """
        Show phase status:
        
        ● EXPLORE  Scanning...
        ✓ EXPLORE  Found 42 files
        """
        icons = {"idle": "○", "run": "●", "ok": "✓", "done": "✓", "err": "✗", "skip": "○"}
        colors = {
            "idle": "dim", "run": f"phase.{name.lower()}", 
            "ok": "success", "done": "success", "err": "error", "skip": "dim"
        }
        
        icon = icons.get(status, "●")
        color = colors.get(status, "dim")
        
        line = Text()
        line.append(f"{icon} ", style=color)
        line.append(f"{name:8}", style=f"{color} bold")
        if detail:
            line.append(f" {detail}", style="dim")
        
        self.console.print(line)
    
    def phase_steps(self, steps: List[str], current: int = -1):
        """Show numbered steps within a phase"""
        for i, step in enumerate(steps):
            if i < current:
                icon, style = "✓", "success"
            elif i == current:
                icon, style = "▸", "step"
            else:
                icon, style = "○", "dim"
            
            self.console.print(Text(f"  {icon} {i+1}. {step}", style=style))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Diff Display - Git-style with line numbers in a box
    # ═══════════════════════════════════════════════════════════════════════════
    
    def diff(self, filename: str, old_lines: List[str], new_lines: List[str]):
        """
        Show git-style diff in a box:
        
        ┌─ filename.py ──────────────────────────────────────────┐
        │  42 │ + new line                                       │
        │  43 │ - old line                                       │
        └────────────────────────────────────────────────────────┘
        """
        import difflib
        
        diff_lines = list(difflib.unified_diff(
            old_lines, new_lines, fromfile=filename, tofile=filename, lineterm=""
        ))
        
        if not diff_lines:
            return
        
        # Build diff content
        content_lines = []
        line_num = 0
        
        for line in diff_lines[2:]:  # Skip header
            if line.startswith("@@"):
                # Extract line number from @@ -start,count +start,count @@
                try:
                    parts = line.split(" ")
                    line_num = int(parts[2].split(",")[0].replace("+", ""))
                except:
                    pass
                continue
            
            if line.startswith("+") and not line.startswith("+++"):
                # Added line (green)
                content_lines.append((line_num, "+", line[1:], "diff.add"))
                line_num += 1
            elif line.startswith("-") and not line.startswith("---"):
                # Removed line (red)
                content_lines.append((line_num, "-", line[1:], "diff.del"))
            else:
                # Context line
                content_lines.append((line_num, " ", line, "dim"))
                line_num += 1
        
        # Draw box
        box_width = self.width - 4
        title = f" {filename} "
        title_padding = box_width - len(title) - 2
        
        self.console.print("┌─" + title + "─" * title_padding + "┐", style="border")
        
        for num, sign, content, style in content_lines[:15]:  # Limit lines
            # Format: │ 42 │ + content │
            line_str = f"{num:4} │ {sign} {content[:box_width - 12]}"
            padding = box_width - len(line_str) - 1
            self.console.print(Text("│ ", style="border") + 
                              Text(f"{num:4}", style="diff.line") +
                              Text(" │ ", style="border") +
                              Text(sign, style=style) +
                              Text(f" {content[:box_width - 12]}", style=style if sign != " " else "dim") +
                              Text(" " * max(0, padding) + "│", style="border"))
        
        if len(content_lines) > 15:
            more = f"... {len(content_lines) - 15} more lines"
            self.console.print(Text(f"│ {more:^{box_width - 2}} │", style="dim"))
        
        self.console.print("└" + "─" * box_width + "┘", style="border")
    
    def diff_summary(self, files: List[Dict[str, Any]]):
        """Show summary of changes"""
        if not files:
            return
        
        for f in files:
            name = f.get("name", "unknown")
            added = f.get("added", 0)
            removed = f.get("removed", 0)
            
            line = Text("✓ ", style="success")
            line.append(name, style="path")
            line.append(f" +{added} -{removed}", style="dim")
            self.console.print(line)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Code Display - In a box with line numbers
    # ═══════════════════════════════════════════════════════════════════════════
    
    def code(self, content: str, language: str = "python", title: str = ""):
        """
        Show code in a box with line numbers:
        
        ┌─ filename.py ───────────────────────────────────────────┐
        │  1 │ def hello():                                       │
        │  2 │     print("Hello!")                                │
        └─────────────────────────────────────────────────────────┘
        """
        lines = content.split('\n')
        box_width = self.width - 4
        
        # Header
        if title:
            title_str = f" {title} "
            title_padding = box_width - len(title_str) - 2
            self.console.print("┌─" + title_str + "─" * title_padding + "┐", style="border")
        else:
            self.console.print("┌" + "─" * box_width + "┐", style="border")
        
        # Content
        for i, line in enumerate(lines[:20], 1):  # Limit lines
            display = line[:box_width - 10]
            padding = box_width - len(display) - 8
            self.console.print(
                Text("│ ", style="border") +
                Text(f"{i:3}", style="diff.line") +
                Text(" │ ", style="border") +
                Text(display) +
                Text(" " * max(0, padding) + "│", style="border")
            )
        
        if len(lines) > 20:
            more = f"... {len(lines) - 20} more lines"
            self.console.print(Text(f"│ {more:^{box_width - 2}} │", style="dim"))
        
        # Footer
        self.console.print("└" + "─" * box_width + "┘", style="border")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Search Results - Compact
    # ═══════════════════════════════════════════════════════════════════════════
    
    def search_results(self, results: List[Dict], query: str = "", limit: int = 5):
        """Show search results compactly"""
        if not results:
            self.muted("No results")
            return
        
        if query:
            self.console.print(Text(f"\n{len(results)} results for \"{query}\":", style="dim"))
        
        for i, r in enumerate(results[:limit]):
            title = r.get("title", "No title")[:55]
            url = r.get("url", "")
            
            # Extract domain
            domain = ""
            if url:
                try:
                    from urllib.parse import urlparse, parse_qs, unquote
                    parsed = urlparse(url)
                    if "duckduckgo.com" in parsed.netloc and "uddg" in url:
                        query_params = parse_qs(parsed.query)
                        if "uddg" in query_params:
                            real_url = unquote(query_params["uddg"][0])
                            domain = urlparse(real_url).netloc.replace("www.", "")
                    else:
                        domain = parsed.netloc.replace("www.", "")
                except:
                    domain = ""
            
            # Compact format: "1. Title - domain.com"
            line = Text(f"{i+1}. ", style="accent")
            line.append(title, style="text")
            if domain:
                line.append(f" - {domain}", style="dim")
            self.console.print(line)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Error with detail
    # ═══════════════════════════════════════════════════════════════════════════
    
    def error_detail(self, file: str, error: str, line: int = None, suggestion: str = None):
        """Error with file context"""
        msg = f"✗ {file}"
        if line:
            msg += f":{line}"
        self.console.print(Text(msg, style="error"))
        self.console.print(Text(f"  {error}", style="dim"))
        if suggestion:
            self.console.print(Text(f"  → {suggestion}", style="warning"))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Assistant response (green = reply)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def assistant(self, msg: str, model: str = ""):
        """Print assistant response in green (reply color)"""
        self.console.print(f"\n[reply]{msg}[/]")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Help (Copilot CLI style)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def help_box(self, sections: Dict[str, List[tuple]] = None):
        """Show help - Copilot CLI style"""
        help_text = """[accent bold]Shortcuts:[/]
  @          Include file contents
  !          Run shell command
  Ctrl+c     Cancel/Exit
  Ctrl+l     Clear screen

[accent bold]Commands:[/]
  /help      Show this help
  /clear     Clear conversation
  /model     Show/change model
  /quit      Exit

[accent bold]Examples:[/]
  hyprland config     Open config file
  search recursion    Web search
  create login.py     Generate code"""
        
        panel = Panel(help_text, title="[accent]Ryx[/]", border_style="border", padding=(0, 1))
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
    def step(self, text: str, icon: str = "●", style: str = "step"):
        """Legacy step - now uses step color (cyan)"""
        self.console.print(Text(f"  {icon} {text}", style=style))
    
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
