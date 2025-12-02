"""
Ryx AI - Modern Fixed Input Box (Claude Code Style++)

Ultra-modern split-layout with:
- Scrollable content area (chat history)
- Fixed input box at bottom (never scrolls)
- Multi-line input with Ctrl+Enter to send
- Auto-complete for @files and /commands
- Catppuccin Mocha theme
"""

import os
import sys
import shutil
from typing import Optional, List, Callable, Any
from dataclasses import dataclass

try:
    from prompt_toolkit import Application
    from prompt_toolkit.layout import (
        HSplit, VSplit, Window, Layout,
        FormattedTextControl, Dimension, ScrollablePane
    )
    from prompt_toolkit.widgets import TextArea, Frame
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.formatted_text import HTML, FormattedText, ANSI
    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.styles import Style as PTStyle
    from prompt_toolkit.document import Document
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════
# Auto-Complete for @files and /commands
# ═══════════════════════════════════════════════════════════════════════════════

class RyxCompleter(Completer):
    """Auto-complete for @files and /commands"""

    def __init__(self, cwd: str = "."):
        self.cwd = cwd
        self.commands = [
            "/help", "/clear", "/model", "/quit", "/precision",
            "/web", "/search", "/undo", "/checkpoints", "/status",
            "/tools", "/themes", "/browsing"
        ]

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor

        # Complete /commands
        if text.lstrip().startswith("/"):
            word = text.split()[-1] if text.split() else "/"
            for cmd in self.commands:
                if cmd.startswith(word):
                    yield Completion(
                        cmd,
                        start_position=-len(word),
                        display=cmd,
                        display_meta="command"
                    )

        # Complete @files
        elif "@" in text:
            parts = text.split("@")
            if len(parts) > 1:
                prefix = parts[-1]
                try:
                    for item in os.listdir(self.cwd):
                        if item.startswith(prefix) or prefix == "":
                            path = os.path.join(self.cwd, item)
                            meta = "dir" if os.path.isdir(path) else "file"
                            yield Completion(
                                item,
                                start_position=-len(prefix),
                                display=f"@{item}",
                                display_meta=meta
                            )
                except:
                    pass


# ═══════════════════════════════════════════════════════════════════════════════
# Content Line
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ContentLine:
    """A line in the content area with style info"""
    text: str
    style: str = "text"


# ═══════════════════════════════════════════════════════════════════════════════
# Modern CLI with Fixed Input Box
# ═══════════════════════════════════════════════════════════════════════════════

class ModernCLI:
    """
    Modern CLI with fixed input box - Claude Code style.

    Layout:
    ┌─────────────────────────────────────────────────────────────┐
    │                                                             │
    │         Scrollable Content Area                             │
    │         (Chat history, AI responses, steps)                 │
    │                                                             │
    ├─────────────────────────────────────────────────────────────┤
    │ ~/ryx-ai [main]                           qwen2.5-coder:14b │
    ├─────────────────────────────────────────────────────────────┤
    │ ❯ Your prompt here...                                       │
    ├─────────────────────────────────────────────────────────────┤
    │ Ctrl+Enter: Send · Shift+Enter: New line · Ctrl+C: Exit    │
    └─────────────────────────────────────────────────────────────┘
    """

    def __init__(self, cwd: str = None):
        if not PROMPT_TOOLKIT_AVAILABLE:
            raise ImportError("prompt_toolkit required: pip install prompt_toolkit>=3.0")

        # Session state
        self.cwd = cwd or os.getcwd()
        self.current_model = "ryx"
        self.current_branch = ""
        self.msg_count = 0
        self.tok_s = 0.0

        # Content buffer
        self.content_lines: List[ContentLine] = []

        # Input result
        self._input_result: Optional[str] = None

        # Create UI
        self._create_buffers()
        self._create_layout()
        self._create_keybindings()

        # Create application
        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            style=self._create_style(),
            full_screen=True,
            mouse_support=True,
        )

    def _create_buffers(self):
        """Create input buffer with auto-complete"""
        self.input_buffer = Buffer(
            multiline=True,
            completer=RyxCompleter(self.cwd),
            auto_suggest=AutoSuggestFromHistory(),
            enable_history_search=True,
        )

    def _create_layout(self):
        """Create the split layout"""

        # Content area (scrollable, takes all remaining space)
        self.content_control = FormattedTextControl(
            text=self._get_formatted_content,
            focusable=False,
        )

        self.content_window = Window(
            content=self.content_control,
            wrap_lines=True,
            allow_scroll_beyond_bottom=False,
        )

        # Status line (1 line exactly)
        self.status_window = Window(
            content=FormattedTextControl(
                text=self._get_status_line,
                focusable=False,
            ),
            height=Dimension.exact(1),
            style="class:status-line",
        )

        # Input area - minimal height, just 1 line
        from prompt_toolkit.layout.controls import BufferControl
        
        self.input_control = BufferControl(
            buffer=self.input_buffer,
            focusable=True,
        )
        
        self.input_window = Window(
            content=self.input_control,
            height=Dimension.exact(1),  # Exactly 1 line
            wrap_lines=False,
            style="class:input",
        )

        # Prompt indicator (fixed width)
        self.prompt_window = Window(
            content=FormattedTextControl(
                text=lambda: FormattedText([("class:prompt", "❯ ")]),
                focusable=False,
            ),
            width=Dimension.exact(2),
            height=Dimension.exact(1),
        )

        # Hints line (1 line exactly)
        self.hints_window = Window(
            content=FormattedTextControl(
                text=self._get_hints_line,
                focusable=False,
            ),
            height=Dimension.exact(1),
            style="class:hints-line",
        )

        # Separator windows
        sep1 = Window(height=Dimension.exact(1), char="─", style="class:separator")
        sep2 = Window(height=Dimension.exact(1), char="─", style="class:separator")

        # Input row: prompt + input field
        input_row = VSplit([
            self.prompt_window,
            self.input_window,
        ])

        # Build layout - content expands, bottom is fixed
        self.layout = Layout(
            HSplit([
                self.content_window,      # Expands to fill space
                sep1,                      # ─────────────
                self.status_window,        # ~/path [branch] ... model
                sep2,                      # ─────────────
                input_row,                 # ❯ [input]
                self.hints_window,         # Enter Send · Ctrl+C Exit
            ]),
            focused_element=self.input_window,
        )

    def _create_keybindings(self):
        """Setup keyboard shortcuts"""
        self.kb = KeyBindings()

        # Enter: Send (if single line, no trailing newline)
        @self.kb.add("enter")
        def send_on_enter(event):
            text = self.input_buffer.text.strip()
            if text:
                self._input_result = text
                self.input_buffer.text = ""
                event.app.exit(result=text)

        # Ctrl+C: Exit
        @self.kb.add("c-c")
        def exit_app(event):
            self._input_result = None
            event.app.exit(result="__EXIT__")

        # Ctrl+L: Clear content
        @self.kb.add("c-l")
        def clear_content(event):
            self.content_lines.clear()
            self.app.invalidate()

    def _create_style(self):
        """Catppuccin Mocha theme - optimized for visibility"""
        return PTStyle.from_dict({
            # Content area
            "text": "#c6d0f5",
            "success": "#a6d189",
            "error": "#e78284",
            "warning": "#e5c890",
            "info": "#8caaee",
            "muted": "#737994",
            "dim": "#626880",
            "step": "#81c8be",
            "reply": "#a6d189",
            "user": "#ca9ee6",

            # Status line - subtle dark background
            "status-line": "bg:#232634 #c6d0f5",
            "path": "#ef9f76 bold",
            "branch": "#99d1db",
            "model": "#f4b8e4 bold",

            # Input area
            "prompt": "#ca9ee6 bold",
            "input": "#c6d0f5",

            # Hints line - very subtle
            "hints-line": "#626880",

            # Separators - visible but not too bright
            "separator": "#414559",

            # Completion menu
            "completion-menu": "bg:#303446 #c6d0f5",
            "completion-menu.completion.current": "bg:#51576d #ca9ee6 bold",
        })

    # ═══════════════════════════════════════════════════════════════════════════
    # Content Rendering
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_formatted_content(self):
        """Return formatted content"""
        if not self.content_lines:
            return FormattedText([
                ("class:dim", "  ~\n"),
                ("class:dim", "  Start chatting...\n"),
            ])

        result = []
        for line in self.content_lines:
            style_class = f"class:{line.style}"
            result.append((style_class, line.text + "\n"))

        return FormattedText(result)

    def _get_status_line(self):
        """Status line: path [branch] ... model"""
        path = self.cwd.replace(os.path.expanduser("~"), "~")
        left = f"{path}"
        if self.current_branch:
            left += f" [{self.current_branch}]"

        right = self.current_model

        width = shutil.get_terminal_size().columns
        pad_len = width - len(left) - len(right) - 2
        padding = " " * max(1, pad_len)

        return FormattedText([
            ("class:path", left),
            ("", padding),
            ("class:model", right),
        ])

    def _get_hints_line(self):
        """Hints: shortcuts ... message count"""
        hints = [
            ("class:muted bold", "Enter"),
            ("class:dim", " Send · "),
            ("class:muted bold", "Ctrl+C"),
            ("class:dim", " Exit"),
        ]

        if self.msg_count > 0:
            width = shutil.get_terminal_size().columns
            left_len = sum(len(t[1]) for t in hints)
            right_text = f"{self.msg_count} messages"
            if self.tok_s > 0:
                right_text += f" · {self.tok_s:.0f} tok/s"
            pad_len = width - left_len - len(right_text) - 2

            hints.append(("", " " * max(1, pad_len)))
            hints.append(("class:dim", right_text))

        return FormattedText(hints)

    # ═══════════════════════════════════════════════════════════════════════════
    # Public API - Content
    # ═══════════════════════════════════════════════════════════════════════════

    def add_content(self, text: str, style: str = "text"):
        """Add line to content area"""
        self.content_lines.append(ContentLine(text=text, style=style))

    def success(self, msg: str):
        self.add_content(f"✓ {msg}", "success")

    def error(self, msg: str):
        self.add_content(f"✗ {msg}", "error")

    def warn(self, msg: str):
        self.add_content(f"⚠ {msg}", "warning")

    def info(self, msg: str):
        self.add_content(f"ℹ {msg}", "info")

    def muted(self, msg: str):
        self.add_content(msg, "muted")

    def step(self, msg: str):
        self.add_content(f"● {msg}", "step")

    def reply(self, msg: str):
        self.add_content(msg, "reply")

    def assistant(self, msg: str, model: str = ""):
        self.add_content(msg, "reply")

    def nl(self):
        self.add_content("", "text")

    # ═══════════════════════════════════════════════════════════════════════════
    # Public API - Session
    # ═══════════════════════════════════════════════════════════════════════════

    def welcome(self, model: str = "", branch: str = "", cwd: str = ""):
        if model:
            self.current_model = model
        if branch:
            self.current_branch = branch
        if cwd:
            self.cwd = cwd

    def header(self, **kwargs):
        self.welcome(**kwargs)

    def footer(self, msgs: int = 0, tok_s: float = 0.0, **kwargs):
        if msgs > 0:
            self.msg_count = msgs
        if tok_s > 0:
            self.tok_s = tok_s

    # ═══════════════════════════════════════════════════════════════════════════
    # Main Prompt
    # ═══════════════════════════════════════════════════════════════════════════

    def prompt(self) -> str:
        """Run UI and get input"""
        try:
            result = self.app.run()

            if result == "__EXIT__" or result is None:
                return "/quit"

            self.msg_count += 1
            # Add user message to content
            self.add_content(f"❯ {result}", "user")
            return result.strip()

        except KeyboardInterrupt:
            return "/quit"
        except EOFError:
            return "/quit"

    # ═══════════════════════════════════════════════════════════════════════════
    # Legacy Compatibility
    # ═══════════════════════════════════════════════════════════════════════════

    def step_start(self, text: str):
        self.add_content(f"● {text}...", "step")

    def step_done(self, text: str, detail: str = ""):
        msg = f"✓ {text}"
        if detail:
            msg += f" ({detail})"
        self.add_content(msg, "success")

    def step_fail(self, text: str, error: str = ""):
        msg = f"✗ {text}"
        if error:
            msg += f" - {error}"
        self.add_content(msg, "error")

    def substep(self, text: str):
        self.add_content(f"  {text}", "muted")

    def phase(self, name: str, status: str = "run", detail: str = ""):
        icons = {"idle": "○", "run": "●", "ok": "✓", "done": "✓", "err": "✗"}
        icon = icons.get(status, "●")
        style = "success" if status in ["ok", "done"] else "error" if status == "err" else "step"
        msg = f"{icon} {name}"
        if detail:
            msg += f"  {detail}"
        self.add_content(msg, style)

    def phase_start(self, name: str, description: str = ""):
        self.phase(name, "run", description)

    def phase_done(self, name: str, result: str = "", success: bool = True):
        self.phase(name, "ok" if success else "err", result)

    def thinking(self, text: str = ""):
        self.add_content(f"● {text}...", "step")

    def thinking_done(self, result: str = ""):
        pass

    def confirm(self, msg: str) -> bool:
        self.add_content(f"? {msg} [y/N]", "warning")
        # For now, auto-decline in full-screen mode
        return False

    def search_results(self, results: list, query: str = "", limit: int = 5):
        if query:
            self.muted(f"{len(results)} results for \"{query}\":")
        for i, r in enumerate(results[:limit]):
            title = r.get("title", "")[:55]
            self.add_content(f"  {i+1}. {title}", "muted")

    def help_box(self, sections: dict = None):
        help_lines = [
            "Shortcuts:",
            "  @          Include file",
            "  /help      Show help",
            "  /quit      Exit",
            "  Ctrl+C     Cancel",
        ]
        for line in help_lines:
            self.muted(line)

    def stream_start(self, model: str = ""):
        if model:
            self.current_model = model

    def stream_token(self, token: str):
        # In full-screen mode, we buffer tokens
        if self.content_lines and self.content_lines[-1].style == "reply":
            self.content_lines[-1].text += token
        else:
            self.add_content(token, "reply")

    def stream_end(self):
        pass

    # Context manager
    from contextlib import contextmanager

    @contextmanager
    def spinner(self, text: str = ""):
        self.add_content(f"● {text}...", "step")
        try:
            yield
        finally:
            pass

    @property
    def console(self):
        return self


# ═══════════════════════════════════════════════════════════════════════════════
# Factory
# ═══════════════════════════════════════════════════════════════════════════════

_modern_cli: Optional[ModernCLI] = None


def get_modern_cli(cwd: str = None) -> Optional[ModernCLI]:
    """Get or create ModernCLI instance"""
    global _modern_cli
    if _modern_cli is None:
        if PROMPT_TOOLKIT_AVAILABLE:
            try:
                _modern_cli = ModernCLI(cwd=cwd)
            except Exception as e:
                print(f"Warning: ModernCLI failed: {e}", file=sys.stderr)
                return None
        else:
            return None
    return _modern_cli


def create_modern_cli(cwd: str = None) -> Optional[ModernCLI]:
    """Create new ModernCLI instance"""
    if not PROMPT_TOOLKIT_AVAILABLE:
        return None
    try:
        return ModernCLI(cwd=cwd)
    except Exception as e:
        print(f"Warning: ModernCLI failed: {e}", file=sys.stderr)
        return None
