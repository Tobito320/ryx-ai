"""
Ryx AI - Terminal UI with Fixed Input Box (Claude Code Style)

Uses prompt_toolkit for a real split-terminal layout:
- Scrollable content area (top) - chat history, responses
- Fixed input box (bottom) - always visible at screen bottom

This is how Claude Code CLI does it.
"""

import os
import sys
from typing import Optional, List, Callable, Any
from dataclasses import dataclass, field
from contextlib import contextmanager

from prompt_toolkit import PromptSession, HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import FormattedText, HTML
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window, FormattedTextControl
from prompt_toolkit.layout.containers import ConditionalContainer, Float, FloatContainer
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.widgets import TextArea, Frame, Box
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.output import ColorDepth


# ═══════════════════════════════════════════════════════════════════════════════
# Catppuccin Frappe Theme for prompt_toolkit
# ═══════════════════════════════════════════════════════════════════════════════

STYLE = Style.from_dict({
    # Prompt
    'prompt': '#ca9ee6 bold',           # Purple - prompt symbol
    'input': '#c6d0f5',                  # Main text
    
    # Status bar
    'status': '#626880',                 # Border color
    'status.key': '#737994',             # Shortcut keys
    'status.text': '#51576d',            # Hint text
    'status.model': '#f4b8e4',           # Model name (pink)
    'status.path': '#ef9f76',            # Path (peach)
    'status.branch': '#99d1db',          # Git branch (teal)
    'status.count': '#737994',           # Message count
    
    # Content
    'success': '#a6d189',                # Green
    'error': '#e78284',                  # Red
    'warning': '#e5c890',                # Yellow
    'info': '#8caaee',                   # Blue
    'muted': '#6c6f85',                  # Muted
    'step': '#81c8be',                   # Teal - steps
    
    # Separator line
    'separator': '#626880',
})


@dataclass
class TerminalState:
    """Tracks terminal state"""
    model: str = "ryx"
    branch: str = ""
    path: str = ""
    msg_count: int = 0
    tok_s: float = 0.0
    precision: bool = False


class TerminalUI:
    """
    Claude Code style terminal UI with fixed input box.
    
    Layout:
    ┌─────────────────────────────────────────────────────────────────────┐
    │ [scrollable content - chat history, responses, etc.]               │
    │                                                                     │
    │                                                                     │
    ├─────────────────────────────────────────────────────────────────────┤
    │ ~                                                      model-name  │
    │ ─────────────────────────────────────────────────────────────────  │
    │ > [input here]                                                     │
    │ Ctrl+c Exit · Ctrl+r Recent                           N messages   │
    └─────────────────────────────────────────────────────────────────────┘
    """
    
    def __init__(self):
        self.state = TerminalState()
        self.history = InMemoryHistory()
        self.content_lines: List[str] = []
        
        # Simple session for prompts
        self.session = PromptSession(
            history=self.history,
            auto_suggest=AutoSuggestFromHistory(),
            style=STYLE,
        )
        
        # Terminal width
        self.width = os.get_terminal_size().columns
    
    def _get_toolbar(self) -> str:
        """Build bottom toolbar with hints and stats"""
        left = "Ctrl+c Exit · Ctrl+r Recent"
        right = f"{self.state.msg_count} messages"
        if self.state.tok_s > 0:
            right += f" · {self.state.tok_s:.0f} tok/s"
        
        pad = self.width - len(left) - len(right) - 2
        return f"{left}{' ' * max(1, pad)}{right}"
    
    def _draw_separator(self):
        """Draw the separator line above input"""
        # Model line
        model = self.state.model.split(":")[0] if ":" in self.state.model else self.state.model
        left = "~"
        right = model
        pad = self.width - len(left) - len(right) - 2
        
        print(f"\033[38;2;81;87;109m{left}\033[0m{' ' * max(1, pad)}\033[38;2;244;184;228m{right}\033[0m")
        print(f"\033[38;2;98;104;128m{'─' * self.width}\033[0m")
    
    def welcome(self, model: str = "", branch: str = "", cwd: str = ""):
        """Show welcome - path and branch"""
        if model:
            self.state.model = model
        if branch:
            self.state.branch = branch
        if cwd:
            self.state.path = cwd
        
        path = (cwd or os.getcwd()).replace(os.path.expanduser("~"), "~")
        
        # Print welcome line
        welcome = f"\033[38;2;239;159;118m{path}\033[0m"
        if branch:
            welcome += f" \033[38;2;81;87;109m(\033[38;2;153;209;219m{branch}\033[38;2;81;87;109m)\033[0m"
        print(welcome)
        print()
    
    def prompt(self) -> str:
        """Get user input with fixed input area"""
        self._draw_separator()
        
        try:
            # Purple > prompt
            result = self.session.prompt(
                HTML('<prompt>> </prompt>'),
                bottom_toolbar=HTML(f'<status.key>Ctrl+c</status.key> <status.text>Exit · </status.text>'
                                   f'<status.key>Ctrl+r</status.key> <status.text>Recent</status.text>'
                                   f'<status.text>{"" * 20}</status.text>'
                                   f'<status.count>{self.state.msg_count} messages</status.count>'),
            )
            self.state.msg_count += 1
            return result.strip()
        except KeyboardInterrupt:
            print()
            return ""
        except EOFError:
            return "/quit"
    
    def print(self, text: str, style: str = ""):
        """Print content to scrollable area"""
        # Map style to ANSI colors
        colors = {
            'success': '\033[38;2;166;209;137m',  # Green
            'error': '\033[38;2;231;130;132m',    # Red
            'warning': '\033[38;2;229;200;144m',  # Yellow
            'info': '\033[38;2;140;170;238m',     # Blue
            'muted': '\033[38;2;108;111;133m',    # Muted
            'step': '\033[38;2;129;200;190m',     # Teal
            'reply': '\033[38;2;166;209;137m',    # Green (AI reply)
        }
        
        reset = '\033[0m'
        color = colors.get(style, '')
        
        print(f"{color}{text}{reset}")
        self.content_lines.append(text)
    
    def success(self, msg: str):
        self.print(f"✓ {msg}", 'success')
    
    def error(self, msg: str):
        self.print(f"✗ {msg}", 'error')
    
    def warn(self, msg: str):
        self.print(f"⚠ {msg}", 'warning')
    
    def info(self, msg: str):
        self.print(f"ℹ {msg}", 'info')
    
    def muted(self, msg: str):
        self.print(msg, 'muted')
    
    def step(self, msg: str):
        self.print(f"● {msg}", 'step')
    
    def reply(self, msg: str):
        """AI reply in green"""
        self.print(msg, 'reply')
    
    def assistant(self, msg: str, model: str = ""):
        """Print assistant response"""
        print()
        self.print(msg, 'reply')
    
    def nl(self):
        print()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Streaming Support
    # ═══════════════════════════════════════════════════════════════════════════
    
    def stream_start(self, model: str = ""):
        """Start streaming"""
        if model:
            self.state.model = model
        print()
        sys.stdout.write('\033[38;2;166;209;137m')  # Green
    
    def stream_token(self, token: str):
        """Print a single token"""
        sys.stdout.write(token)
        sys.stdout.flush()
    
    def stream_end(self):
        """End streaming"""
        sys.stdout.write('\033[0m')  # Reset
        print()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Spinner
    # ═══════════════════════════════════════════════════════════════════════════
    
    def spinner_start(self, text: str = ""):
        """Start spinner (simple dots animation)"""
        sys.stdout.write(f'\033[38;2;129;200;190m● {text}...\033[0m')
        sys.stdout.flush()
    
    def spinner_stop(self):
        """Stop spinner"""
        sys.stdout.write('\r\033[K')  # Clear line
        sys.stdout.flush()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Stats
    # ═══════════════════════════════════════════════════════════════════════════
    
    def show_stats(self, tokens: int, duration: float):
        """Show token stats after response"""
        tok_s = tokens / duration if duration > 0 else 0
        self.state.tok_s = tok_s
        self.print(f"{tokens} tokens · {tok_s:.0f} tok/s · {duration:.1f}s", 'muted')
    
    def footer(self, msgs: int = 0, tok_s: float = 0.0, **kwargs):
        """Update state (toolbar updates automatically on next prompt)"""
        if msgs > 0:
            self.state.msg_count = msgs
        if tok_s > 0:
            self.state.tok_s = tok_s
        # No extra output - toolbar shows on next prompt
    
    def header(self, **kwargs):
        """Alias for welcome"""
        self.welcome(**kwargs)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Legacy Compatibility Methods
    # ═══════════════════════════════════════════════════════════════════════════
    
    def thinking(self, text: str = "Thinking"):
        self.spinner_start(text)
    
    def thinking_done(self, result: str = ""):
        self.spinner_stop()
    
    def step_start(self, text: str):
        self.print(f"● {text}...", 'step')
    
    def step_done(self, text: str, detail: str = ""):
        msg = f"✓ {text}"
        if detail:
            msg += f" ({detail})"
        self.print(msg, 'success')
    
    def step_fail(self, text: str, error: str = ""):
        msg = f"✗ {text}"
        if error:
            msg += f" - {error}"
        self.print(msg, 'error')
    
    def substep(self, text: str):
        self.print(f"  {text}", 'muted')
    
    def phase(self, name: str, status: str = "run", detail: str = ""):
        icons = {"idle": "○", "run": "●", "ok": "✓", "done": "✓", "err": "✗"}
        icon = icons.get(status, "●")
        style = 'success' if status in ['ok', 'done'] else 'error' if status == 'err' else 'step'
        msg = f"{icon} {name}"
        if detail:
            msg += f"  {detail}"
        self.print(msg, style)
    
    def phase_start(self, name: str, description: str = ""):
        self.phase(name, "run", description)
    
    def phase_done(self, name: str, result: str = "", success: bool = True):
        self.phase(name, "ok" if success else "err", result)
    
    def confirm(self, msg: str) -> bool:
        """Confirmation prompt"""
        self.print(f"? {msg} ", 'warning')
        try:
            response = input("[y/N] ").strip().lower()
            return response in ['y', 'yes', 'ja', 'j']
        except:
            return False
    
    def search_results(self, results: List[dict], query: str = "", limit: int = 5):
        """Show search results"""
        if query:
            self.muted(f"{len(results)} results for \"{query}\":")
        for i, r in enumerate(results[:limit]):
            title = r.get("title", "")[:55]
            self.print(f"  {i+1}. {title}", 'muted')
    
    def help_box(self, sections: dict = None):
        """Show help"""
        help_text = """Shortcuts:
  @          Include file contents
  !          Run shell command
  Ctrl+c     Cancel/Exit

Commands:
  /help      Show this help
  /clear     Clear conversation
  /quit      Exit"""
        self.muted(help_text)
    
    def console(self):
        """For compatibility - returns self"""
        return self
    
    @contextmanager
    def spinner(self, text: str = ""):
        """Spinner context manager"""
        self.spinner_start(text)
        try:
            yield
        finally:
            self.spinner_stop()


# ═══════════════════════════════════════════════════════════════════════════════
# Global Instance
# ═══════════════════════════════════════════════════════════════════════════════

_terminal_ui: Optional[TerminalUI] = None


def get_terminal_ui() -> TerminalUI:
    """Get or create global TerminalUI instance"""
    global _terminal_ui
    if _terminal_ui is None:
        _terminal_ui = TerminalUI()
    return _terminal_ui
