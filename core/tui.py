"""
Ryx AI - Copilot CLI Style TUI with Fixed Bottom Prompt

Layout:
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         ↑ SCROLLABLE CHAT HISTORY ↑                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│ ~/ryx-ai[⎇ main]                                     qwen2.5-7b │ 45% context   │
│ ╭─────────────────────────────────────────────────────────────────────────────╮ │
│ │ > type here_                                                                │ │
│ ╰─────────────────────────────────────────────────────────────────────────────╯ │
│ Ctrl+c Exit · Ctrl+l Clear · Tab Complete                 Session: 12 requests  │
└─────────────────────────────────────────────────────────────────────────────────┘

Features:
- Fixed bottom prompt with rounded corners
- Scrollable chat history
- Status bar with model, branch, context
- Context indicator colors (Green/Yellow/Bold Yellow/Bold Red)
- Tab completion for /commands
- Streaming support
"""

import os
import sys
import time
import shutil
import asyncio
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from contextlib import contextmanager
from pathlib import Path

from prompt_toolkit import Application, PromptSession
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window, FormattedTextControl
from prompt_toolkit.layout.containers import ConditionalContainer, Float, FloatContainer
from prompt_toolkit.layout.dimension import Dimension, D
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.widgets import TextArea, Frame
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import WordCompleter, Completer, Completion
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.formatted_text import FormattedText, HTML, ANSI
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

# Rich for history display
from rich.console import Console
from rich.text import Text


# ═══════════════════════════════════════════════════════════════════════════════
# Theme - Catppuccin Mocha (matches cli_ui.py)
# ═══════════════════════════════════════════════════════════════════════════════

# prompt_toolkit style
TUI_STYLE = PTStyle.from_dict({
    # Core colors
    'prompt': '#ca9ee6',           # Purple - user prompts
    'input': '#c6d0f5',            # Main text
    'reply': '#a6d189',            # Green - AI replies
    'success': '#a6d189',          # Softer green
    'error': '#e78284',            # Softer red
    'warning': '#e5c890',          # Warm yellow
    'info': '#8caaee',             # Blue
    'muted': '#6c6f85',            # Muted text
    'dim': '#51576d',              # Very dim
    'step': '#81c8be',             # Teal - steps/progress

    # Status bar
    'status-bar': 'bg:#303446 #c6d0f5',
    'status-path': '#ef9f76',      # Peach - file paths
    'status-branch': '#99d1db',    # Teal - git branch
    'status-model': '#f4b8e4',     # Pink - model names

    # Context colors
    'context-green': '#a6d189',
    'context-yellow': '#e5c890',
    'context-yellow-bold': '#e5c890 bold',
    'context-red-bold': '#e78284 bold',

    # Border
    'border': '#626880',
    'border.rounded': '#626880',

    # Input area
    'input-area': '#c6d0f5',
    'prompt-char': '#ca9ee6 bold',

    # Hints
    'hint': '#6c6f85',
    'hint-key': '#8caaee bold',
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
# Slash Command Completer
# ═══════════════════════════════════════════════════════════════════════════════

class SlashCommandCompleter(Completer):
    """Tab completion for /commands and @files"""

    COMMANDS = [
        '/help', '/quit', '/exit', '/clear',
        '/status', '/models', '/model',
        '/precision', '/browsing',
        '/search', '/scrape',
        '/tools', '/undo', '/checkpoints',
        '/fix', '/memory', '/benchmark',
        '/style', '/sources', '/metrics', '/cleanup',
    ]

    STYLES = ['normal', 'concise', 'explanatory', 'learning', 'formal']

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor

        # Slash commands
        if text.startswith('/'):
            cmd = text.lower()
            for c in self.COMMANDS:
                if c.startswith(cmd):
                    yield Completion(c, start_position=-len(cmd))

            # Style subcommand
            if cmd.startswith('/style '):
                style_prefix = cmd[7:]
                for s in self.STYLES:
                    if s.startswith(style_prefix):
                        yield Completion(s, start_position=-len(style_prefix))

        # File completion for @
        elif text.startswith('@'):
            path = text[1:]
            if not path:
                path = '.'

            try:
                dir_path = os.path.dirname(path) or '.'
                prefix = os.path.basename(path)

                if os.path.isdir(dir_path):
                    for name in os.listdir(dir_path):
                        if name.startswith(prefix) and not name.startswith('.'):
                            full_path = os.path.join(dir_path, name)
                            display = name + ('/' if os.path.isdir(full_path) else '')
                            yield Completion(
                                os.path.join(dir_path, name) if dir_path != '.' else name,
                                start_position=-len(path)
                            )
            except OSError:
                pass


# ═══════════════════════════════════════════════════════════════════════════════
# Chat History Buffer
# ═══════════════════════════════════════════════════════════════════════════════

class ChatHistoryBuffer:
    """Manages scrollable chat history"""

    def __init__(self):
        self.messages: List[Dict[str, str]] = []
        self._formatted_cache: Optional[FormattedText] = None
        self._cache_valid = False

    def add_user(self, content: str):
        """Add user message"""
        self.messages.append({'role': 'user', 'content': content})
        self._cache_valid = False

    def add_assistant(self, content: str):
        """Add assistant message"""
        self.messages.append({'role': 'assistant', 'content': content})
        self._cache_valid = False

    def add_system(self, content: str, style: str = 'muted'):
        """Add system message (status, errors, etc)"""
        self.messages.append({'role': 'system', 'content': content, 'style': style})
        self._cache_valid = False

    def clear(self):
        """Clear all messages"""
        self.messages = []
        self._cache_valid = False

    def get_formatted(self) -> FormattedText:
        """Get formatted text for display"""
        if self._cache_valid and self._formatted_cache:
            return self._formatted_cache

        parts = []

        for msg in self.messages:
            role = msg.get('role', 'system')
            content = msg.get('content', '')

            if role == 'user':
                parts.append(('class:prompt', '> '))
                parts.append(('class:prompt', content))
                parts.append(('', '\n'))
            elif role == 'assistant':
                parts.append(('class:reply', content))
                parts.append(('', '\n\n'))
            else:
                style = msg.get('style', 'muted')
                parts.append((f'class:{style}', content))
                parts.append(('', '\n'))

        self._formatted_cache = FormattedText(parts)
        self._cache_valid = True
        return self._formatted_cache


# ═══════════════════════════════════════════════════════════════════════════════
# TUI - Main Class
# ═══════════════════════════════════════════════════════════════════════════════

class TUI:
    """
    Copilot CLI Style TUI with fixed bottom prompt.

    Layout:
    ┌─────────────────────────────────────────────────────────────────┐
    │                    Scrollable Chat History                      │
    ├─────────────────────────────────────────────────────────────────┤
    │ ~/path[⎇ branch]                          model │ 45% context   │
    │ ╭───────────────────────────────────────────────────────────────╮
    │ │ > _                                                           │
    │ ╰───────────────────────────────────────────────────────────────╯
    │ Ctrl+c Exit · Tab Complete                     Session: N reqs  │
    └─────────────────────────────────────────────────────────────────┘
    """

    def __init__(self):
        # Terminal size
        self.width = shutil.get_terminal_size().columns
        self.height = shutil.get_terminal_size().lines

        # State
        self.msg_count = 0
        self.current_model = ""
        self.current_branch = ""
        self.current_path = ""
        self.context_percent = 0  # 0-100
        self._welcome_shown = False

        # Rich console for fallback and some output
        self.console = Console(highlight=False)

        # Chat history
        self.history = ChatHistoryBuffer()

        # Streaming state
        self._stream_state: Optional[Dict] = None
        self._last_stats: Optional[ResponseStats] = None
        self.last_tok_s = 0.0

        # History file for prompt
        history_file = self._get_history_file()
        self._prompt_history = FileHistory(str(history_file))

        # Prompt session
        self._session = PromptSession(
            completer=SlashCommandCompleter(),
            history=self._prompt_history,
            auto_suggest=AutoSuggestFromHistory(),
            style=TUI_STYLE,
            enable_history_search=True,
        )

        # For spinner
        self._spinner_active = False
        self._spinner_text = ""

    def _get_history_file(self) -> Path:
        """Get history file path"""
        try:
            from core.paths import get_data_dir
            history_dir = get_data_dir() / "history"
        except ImportError:
            history_dir = Path.home() / ".local" / "share" / "ryx" / "history"

        history_dir.mkdir(parents=True, exist_ok=True)
        return history_dir / "tui_history"

    def _get_context_style(self) -> str:
        """Get context indicator style based on percentage"""
        pct = self.context_percent
        if pct < 60:
            return 'context-green'
        elif pct < 80:
            return 'context-yellow'
        elif pct < 95:
            return 'context-yellow-bold'
        else:
            return 'context-red-bold'

    def _build_status_bar(self) -> FormattedText:
        """Build status bar content"""
        parts = []

        # Left side: path and branch
        path = self.current_path or os.getcwd()
        path = path.replace(os.path.expanduser("~"), "~")
        if len(path) > 30:
            path = "~/" + os.path.basename(path)

        parts.append(('class:status-path', f' {path}'))

        if self.current_branch:
            parts.append(('class:muted', '['))
            parts.append(('class:status-branch', f'⎇ {self.current_branch}'))
            parts.append(('class:muted', ']'))

        # Calculate spacing
        left_len = len(path) + (len(self.current_branch) + 4 if self.current_branch else 0)

        # Right side: model and context
        model_name = self.current_model or "unknown"
        if '/' in model_name:
            model_name = model_name.split('/')[-1]
        if len(model_name) > 20:
            model_name = model_name[:17] + "..."

        context_str = f'{self.context_percent}%'
        right_side = f'{model_name} │ {context_str} context'
        right_len = len(right_side) + 2

        # Padding
        padding = max(1, self.width - left_len - right_len - 2)
        parts.append(('class:status-bar', ' ' * padding))

        # Model
        parts.append(('class:status-model', model_name))
        parts.append(('class:muted', ' │ '))

        # Context with color
        context_style = self._get_context_style()
        parts.append((f'class:{context_style}', context_str))
        parts.append(('class:muted', ' context '))

        return FormattedText(parts)

    def _build_hint_bar(self) -> FormattedText:
        """Build bottom hint bar"""
        parts = []

        # Left: shortcuts
        parts.append(('class:hint-key', ' Ctrl+c'))
        parts.append(('class:hint', ' Exit · '))
        parts.append(('class:hint-key', 'Ctrl+l'))
        parts.append(('class:hint', ' Clear · '))
        parts.append(('class:hint-key', 'Tab'))
        parts.append(('class:hint', ' Complete'))

        # Right: session info
        session_info = f'Session: {self.msg_count} requests '
        padding = max(1, self.width - 45 - len(session_info))
        parts.append(('class:hint', ' ' * padding))
        parts.append(('class:muted', session_info))

        return FormattedText(parts)

    def _build_prompt_box(self) -> str:
        """Build the rounded prompt box characters"""
        inner_width = self.width - 6  # Account for ╭╮ and padding
        top = f'╭{"─" * inner_width}╮'
        bottom = f'╰{"─" * inner_width}╯'
        return top, bottom

    # ═══════════════════════════════════════════════════════════════════════════
    # Public Interface (matches CLI class in cli_ui.py)
    # ═══════════════════════════════════════════════════════════════════════════

    def prompt(self) -> str:
        """Get user input with fixed bottom prompt"""
        try:
            # Print status bar
            status = self._build_status_bar()
            print()  # Spacing

            # Print prompt box top
            box_top, box_bottom = self._build_prompt_box()
            self.console.print(f'[dim]{box_top}[/]')

            # Get input
            user_input = self._session.prompt(
                [('class:border.rounded', '│ '), ('class:prompt-char', '> ')],
            ).strip()

            # Print prompt box bottom
            self.console.print(f'[dim]{box_bottom}[/]')

            # Print hints
            # hints = self._build_hint_bar()
            # print()  # Will format hints separately

            if user_input:
                self.msg_count += 1
                self.history.add_user(user_input)

            return user_input

        except EOFError:
            return "/quit"
        except KeyboardInterrupt:
            print()
            return ""

    def welcome(self, model: str = "", branch: str = "", cwd: str = ""):
        """Show welcome message"""
        if model:
            self.current_model = model
        if branch:
            self.current_branch = branch
        if cwd:
            self.current_path = cwd

        if not self._welcome_shown:
            path = (cwd or os.getcwd()).replace(os.path.expanduser("~"), "~")

            # Status line
            self.console.print()
            line = Text()
            line.append(path, style="#ef9f76")  # Peach
            if branch:
                line.append(" ", style="dim")
                line.append(f"[⎇ {branch}]", style="#99d1db")  # Teal
            if model:
                # Right-align model
                model_short = model.split('/')[-1] if '/' in model else model
                padding = self.width - len(path) - len(branch or "") - len(model_short) - 10
                if padding > 0:
                    line.append(" " * padding, style="dim")
                line.append(model_short, style="#f4b8e4")  # Pink

            self.console.print(line)
            self.console.print()
            self._welcome_shown = True

    def header(self, model: str = "", branch: str = "", cwd: str = ""):
        """Alias for welcome"""
        self.welcome(model, branch, cwd)

    def footer(self, model: str = "", msgs: int = 0, precision: bool = False,
               tok_s: float = 0.0, extra: str = ""):
        """Update footer state"""
        if msgs > 0:
            self.msg_count = msgs
        if tok_s > 0:
            self.last_tok_s = tok_s

    def set_context(self, percent: int):
        """Set context usage percentage (0-100)"""
        self.context_percent = max(0, min(100, percent))

    # ═══════════════════════════════════════════════════════════════════════════
    # Spinner
    # ═══════════════════════════════════════════════════════════════════════════

    @contextmanager
    def spinner(self, text: str = ""):
        """Spinner context manager"""
        self._spinner_active = True
        self._spinner_text = text

        # Simple spinner using rich
        from rich.live import Live
        from rich.spinner import Spinner

        display_text = f" {text}" if text else ""
        spinner = Spinner("dots", text=display_text, style="#81c8be")  # Teal

        live = Live(spinner, console=self.console, refresh_per_second=12, transient=True)
        live.start()

        try:
            yield
        finally:
            live.stop()
            self._spinner_active = False
            self._spinner_text = ""

    def spinner_update(self, text: str):
        """Update spinner text"""
        self._spinner_text = text

    # ═══════════════════════════════════════════════════════════════════════════
    # Streaming
    # ═══════════════════════════════════════════════════════════════════════════

    def stream_start(self, model: str = ""):
        """Start streaming response"""
        self._stream_state = {
            "tokens": 0,
            "start": time.time(),
            "model": model,
            "buffer": "",
        }
        # Start with newline, content in green
        print()
        sys.stdout.write("\033[38;2;166;227;161m")  # Green for reply

    def stream_token(self, token: str):
        """Print streaming token"""
        if self._stream_state:
            self._stream_state["tokens"] += 1
            self._stream_state["buffer"] += token
            sys.stdout.write(token)
            sys.stdout.flush()

    def stream_end(self) -> ResponseStats:
        """End streaming, return stats"""
        sys.stdout.write("\033[0m")  # Reset color

        if not self._stream_state:
            return ResponseStats()

        duration = time.time() - self._stream_state["start"]
        tokens = self._stream_state["tokens"]
        model = self._stream_state["model"]
        buffer = self._stream_state["buffer"]

        stats = ResponseStats(tokens=tokens, duration=duration, model=model)
        self._last_stats = stats
        self.last_tok_s = stats.tok_per_sec

        # Add to history
        self.history.add_assistant(buffer)

        # Stats line
        tok_s = stats.tok_per_sec
        self.console.print(f"\n[dim]{tokens} tokens · {tok_s:.0f} tok/s · {duration:.1f}s[/]")

        self._stream_state = None
        return stats

    # ═══════════════════════════════════════════════════════════════════════════
    # Messages
    # ═══════════════════════════════════════════════════════════════════════════

    def success(self, msg: str):
        """Success message"""
        self.console.print(f"[#a6d189]✓ {msg}[/]")
        self.history.add_system(f"✓ {msg}", 'success')

    def error(self, msg: str):
        """Error message"""
        self.console.print(f"[#e78284]✗ {msg}[/]")
        self.history.add_system(f"✗ {msg}", 'error')

    def warn(self, msg: str):
        """Warning message"""
        self.console.print(f"[#e5c890]⚠ {msg}[/]")
        self.history.add_system(f"⚠ {msg}", 'warning')

    def info(self, msg: str):
        """Info message"""
        self.console.print(f"[#8caaee]ℹ {msg}[/]")
        self.history.add_system(f"ℹ {msg}", 'info')

    def muted(self, msg: str):
        """Muted message"""
        self.console.print(f"[#6c6f85]{msg}[/]")

    def step(self, msg: str):
        """Step/progress message"""
        self.console.print(f"[#81c8be]● {msg}[/]")
        self.history.add_system(f"● {msg}", 'step')

    def confirm(self, msg: str) -> bool:
        """Confirmation prompt"""
        self.console.print(f"[#e5c890]? {msg}[/] ", end="")
        try:
            response = input("[y/N] ").strip().lower()
            return response in ['y', 'yes', 'ja', 'j']
        except:
            return False

    def reply(self, msg: str):
        """AI reply"""
        self.console.print(f"[#a6d189]{msg}[/]")
        self.history.add_assistant(msg)

    def nl(self):
        """Newline"""
        print()

    def assistant(self, msg: str, model: str = ""):
        """Print assistant response"""
        self.console.print(f"\n[#a6d189]{msg}[/]")
        self.history.add_assistant(msg)

    # ═══════════════════════════════════════════════════════════════════════════
    # Steps
    # ═══════════════════════════════════════════════════════════════════════════

    def step_start(self, text: str):
        """Step starting"""
        self.console.print(f"[#81c8be]● {text}...[/]")

    def step_done(self, text: str, detail: str = ""):
        """Step done"""
        line = f"[#a6d189]✓ {text}[/]"
        if detail:
            line += f" [dim]({detail})[/]"
        self.console.print(line)

    def step_fail(self, text: str, error: str = ""):
        """Step failed"""
        line = f"[#e78284]✗ {text}[/]"
        if error:
            line += f" [dim]- {error}[/]"
        self.console.print(line)

    # ═══════════════════════════════════════════════════════════════════════════
    # Help
    # ═══════════════════════════════════════════════════════════════════════════

    def help_box(self, sections: Dict[str, List[tuple]] = None):
        """Show help"""
        from rich.panel import Panel

        help_text = """[#ca9ee6 bold]Shortcuts:[/]
  @          Include file contents
  !          Run shell command
  Ctrl+c     Cancel/Exit
  Tab        Complete command

[#ca9ee6 bold]Commands:[/]
  /help      Show this help
  /clear     Clear conversation
  /model     Show/change model
  /style     Change response style
  /search    Web search
  /quit      Exit

[#ca9ee6 bold]Examples:[/]
  hyprland config     Open config file
  search recursion    Web search
  create login.py     Generate code"""

        panel = Panel(help_text, title="[#ca9ee6]Ryx[/]", border_style="#626880", padding=(0, 1))
        self.console.print(panel)

    # ═══════════════════════════════════════════════════════════════════════════
    # Code & Diff (delegating to Rich)
    # ═══════════════════════════════════════════════════════════════════════════

    def code(self, content: str, language: str = "python", title: str = ""):
        """Show code block"""
        from rich.syntax import Syntax
        from rich.panel import Panel

        syntax = Syntax(content, language, line_numbers=True, theme="monokai")
        if title:
            panel = Panel(syntax, title=title, border_style="#626880")
            self.console.print(panel)
        else:
            self.console.print(syntax)

    def diff(self, filename: str, old_lines: List[str], new_lines: List[str]):
        """Show diff"""
        import difflib

        diff_lines = list(difflib.unified_diff(
            old_lines, new_lines, fromfile=filename, tofile=filename, lineterm=""
        ))

        if not diff_lines:
            return

        self.console.print(f"\n[dim]─ {filename}[/]")
        for line in diff_lines[2:20]:  # Skip header, limit lines
            if line.startswith("+") and not line.startswith("+++"):
                self.console.print(f"[#a6d189]{line}[/]")
            elif line.startswith("-") and not line.startswith("---"):
                self.console.print(f"[#e78284]{line}[/]")
            elif line.startswith("@@"):
                self.console.print(f"[#8caaee]{line}[/]")
            else:
                self.console.print(f"[dim]{line}[/]")

    def diff_summary(self, files: List[Dict[str, Any]]):
        """Show diff summary"""
        for f in files:
            name = f.get("name", "unknown")
            added = f.get("added", 0)
            removed = f.get("removed", 0)
            self.console.print(f"[#a6d189]✓[/] [#ef9f76]{name}[/] [dim]+{added} -{removed}[/]")

    def search_results(self, results: List[Dict], query: str = "", limit: int = 5):
        """Show search results"""
        if not results:
            self.muted("No results")
            return

        if query:
            self.console.print(f"\n[dim]{len(results)} results for \"{query}\":[/]")

        for i, r in enumerate(results[:limit]):
            title = r.get("title", "No title")[:55]
            url = r.get("url", "")

            domain = ""
            if url:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(url).netloc.replace("www.", "")
                except:
                    pass

            self.console.print(f"[#ca9ee6]{i+1}.[/] {title}" + (f" [dim]- {domain}[/]" if domain else ""))

    def error_detail(self, file: str, error: str, line: int = None, suggestion: str = None):
        """Error with detail"""
        msg = f"✗ {file}"
        if line:
            msg += f":{line}"
        self.console.print(f"[#e78284]{msg}[/]")
        self.console.print(f"[dim]  {error}[/]")
        if suggestion:
            self.console.print(f"[#e5c890]  → {suggestion}[/]")

    # ═══════════════════════════════════════════════════════════════════════════
    # Plan UI (P1.6 compatibility)
    # ═══════════════════════════════════════════════════════════════════════════

    def show_plan(self, plan_steps: List[Dict[str, Any]], task: str = "") -> None:
        """Show execution plan"""
        from rich.panel import Panel
        from rich.table import Table

        table = Table(show_header=False, box=None, padding=(0, 1))

        for i, step in enumerate(plan_steps, 1):
            action = step.get("action", "modify")
            file_path = step.get("file_path", step.get("file", ""))
            description = step.get("description", "")

            action_colors = {
                "modify": "#e5c890",
                "create": "#a6d189",
                "delete": "#e78284",
                "run": "#8caaee",
            }
            color = action_colors.get(action, "#c6d0f5")

            table.add_row(
                f"[dim]{i}.[/]",
                f"[{color}][{action}][/]",
                f"[#ef9f76]{file_path}[/]"
            )
            if description:
                table.add_row("", "", f"[dim]{description}[/]")

        title = f"Execution Plan: {task}" if task else "Execution Plan"
        panel = Panel(table, title=f"[#ca9ee6]{title}[/]", border_style="#626880")
        self.console.print(panel)

    def plan_approval_prompt(self, plan_steps: List[Dict[str, Any]], task: str = "") -> str:
        """Show plan and get approval"""
        self.show_plan(plan_steps, task)

        self.console.print()
        self.console.print("[#a6d189 bold][y][/] Approve  [#e78284 bold][n][/] Cancel  [#e5c890 bold][e][/] Edit")

        try:
            choice = input("Choice: ").strip().lower()
            return choice if choice else 'y'
        except:
            return 'n'

    def show_plan_progress(self, plan_steps: List[Dict[str, Any]], current_step: int = 0):
        """Show plan with progress"""
        for i, step in enumerate(plan_steps):
            if step.get("completed", False):
                icon, color = "✓", "#a6d189"
            elif step.get("failed", False):
                icon, color = "✗", "#e78284"
            elif i == current_step:
                icon, color = "▸", "#81c8be"
            else:
                icon, color = "○", "#6c6f85"

            action = step.get("action", "modify")
            file_path = step.get("file_path", "")[:30]
            self.console.print(f"[{color}]{icon}[/] {i+1}. [{action}] {file_path}")

    # ═══════════════════════════════════════════════════════════════════════════
    # Phase support (for complex tasks)
    # ═══════════════════════════════════════════════════════════════════════════

    def phase(self, name: str, status: str = "run", detail: str = ""):
        """Show phase status"""
        icons = {"idle": "○", "run": "●", "ok": "✓", "done": "✓", "err": "✗", "skip": "○"}
        colors = {
            "idle": "#6c6f85", "run": "#81c8be",
            "ok": "#a6d189", "done": "#a6d189",
            "err": "#e78284", "skip": "#6c6f85"
        }

        icon = icons.get(status, "●")
        color = colors.get(status, "#6c6f85")

        line = f"[{color}]{icon}[/] [{color} bold]{name:8}[/]"
        if detail:
            line += f" [dim]{detail}[/]"
        self.console.print(line)

    def phase_steps(self, steps: List[str], current: int = -1):
        """Show steps within a phase"""
        for i, step in enumerate(steps):
            if i < current:
                icon, color = "✓", "#a6d189"
            elif i == current:
                icon, color = "▸", "#81c8be"
            else:
                icon, color = "○", "#6c6f85"

            self.console.print(f"  [{color}]{icon} {i+1}. {step}[/]")


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton and Factory
# ═══════════════════════════════════════════════════════════════════════════════

_tui: Optional[TUI] = None


def get_tui() -> TUI:
    """Get or create TUI singleton"""
    global _tui
    if _tui is None:
        _tui = TUI()
    return _tui


# For backwards compatibility with cli_ui.py
def get_cli():
    """Get CLI instance - returns TUI"""
    return get_tui()


def get_ui():
    """Legacy compatibility"""
    return get_tui()
