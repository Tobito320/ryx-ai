"""
Ryx AI - True Fullscreen TUI with Fixed Bottom Prompt

Layout (fullscreen mode like vim/htop):
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  You: hi                                                                        │
│                                                                                 │
│  Ryx: Hi! How can I assist you today?                                           │
│                                                                                 │
│  You: how are you                                                               │
│                                                                                 │
│  Ryx: I'm well, thanks. How about you?                                          │
│                                                                                 │
│                         [SCROLLABLE - mouse/arrows work]                        │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│ ~/ryx-ai[⎇ main]                                     qwen2.5-7b │ 12% context   │
│ ╭─────────────────────────────────────────────────────────────────────────────╮ │
│ │ > _                                                                         │ │
│ ╰─────────────────────────────────────────────────────────────────────────────╯ │
│ Ctrl+c Exit · Ctrl+l Clear · Tab Complete                 Session: 3 requests   │
└─────────────────────────────────────────────────────────────────────────────────┘

Features:
- True fullscreen mode (like vim, htop, Copilot CLI)
- Fixed bottom section that never moves
- Scrollable chat history
- Single Ctrl+C interrupts, double Ctrl+C exits
- Streaming responses update in-place
"""

import os
import sys
import time
import shutil
import threading
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from contextlib import contextmanager
from pathlib import Path

from prompt_toolkit import Application
from prompt_toolkit.application import get_app
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window, FormattedTextControl, ScrollablePane
from prompt_toolkit.layout.containers import ConditionalContainer, WindowAlign
from prompt_toolkit.layout.dimension import Dimension, D
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.history import FileHistory, InMemoryHistory
from prompt_toolkit.filters import Condition


# ═══════════════════════════════════════════════════════════════════════════════
# Theme - Catppuccin Mocha
# ═══════════════════════════════════════════════════════════════════════════════

TUI_STYLE = PTStyle.from_dict({
    # Core colors
    'user': '#ca9ee6 bold',        # Purple - user messages
    'user-label': '#ca9ee6',       # Purple label
    'assistant': '#a6d189',        # Green - AI replies
    'assistant-label': '#a6d189 bold',
    'system': '#6c6f85',           # Muted - system messages
    'success': '#a6d189',          # Green dot - completed
    'error': '#e78284',            # Red dot - failed
    'warning': '#e5c890',          # Yellow dot - warning
    'info': '#8caaee',             # Blue dot - info
    'thinking': '#e5c890 italic',  # Yellow dot - thinking/planning
    'step': '#81c8be',             # Cyan dot - in progress
    'muted': '#6c6f85',
    'dim': '#51576d',

    # Status bar
    'status-bar': 'bg:#303446 #c6d0f5',
    'status-path': '#ef9f76',
    'status-branch': '#99d1db',
    'status-model': '#f4b8e4',

    # Context colors
    'context-green': '#a6d189',
    'context-yellow': '#e5c890',
    'context-yellow-bold': '#e5c890 bold',
    'context-red-bold': '#e78284 bold',

    # Input box
    'input-border': '#626880',
    'input-text': '#c6d0f5',
    'prompt-char': '#ca9ee6 bold',

    # Hints bar
    'hint': '#6c6f85',
    'hint-key': '#8caaee bold',

    # Spinner
    'spinner': '#81c8be',

    # Scrollbar
    'scrollbar.background': '#303446',
    'scrollbar.button': '#626880',
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

        if text.startswith('/'):
            cmd = text.lower()
            for c in self.COMMANDS:
                if c.startswith(cmd):
                    yield Completion(c, start_position=-len(cmd))

            if cmd.startswith('/style '):
                style_prefix = cmd[7:]
                for s in self.STYLES:
                    if s.startswith(style_prefix):
                        yield Completion(s, start_position=-len(style_prefix))

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
                            yield Completion(
                                os.path.join(dir_path, name) if dir_path != '.' else name,
                                start_position=-len(path)
                            )
            except OSError:
                pass


# ═══════════════════════════════════════════════════════════════════════════════
# Message Types
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ChatMessage:
    """A single chat message"""
    role: str  # 'user', 'assistant', 'system'
    content: str
    style: str = ''  # For system messages: 'success', 'error', 'warning', etc.
    is_streaming: bool = False


class TUIConsole:
    """
    Mock console that redirects print() calls to the TUI chat.
    Prevents direct stdout writes that break the fullscreen layout.
    """
    
    def __init__(self, tui: 'FullscreenTUI'):
        self._tui = tui
    
    def print(self, *args, **kwargs):
        """Redirect print to TUI system message"""
        # Convert args to string, strip rich markup
        text = ' '.join(str(a) for a in args)
        # Remove rich markup like [accent bold], [/], etc.
        import re
        text = re.sub(r'\[/?[^\]]+\]', '', text)
        text = text.strip()
        if text:
            self._tui.add_system(text, 'info')
    
    def log(self, *args, **kwargs):
        """Redirect log to TUI"""
        self.print(*args, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# Fullscreen TUI
# ═══════════════════════════════════════════════════════════════════════════════

class FullscreenTUI:
    """
    True fullscreen TUI with fixed bottom prompt.

    Uses prompt_toolkit Application with full_screen=True.
    """

    def __init__(self):
        # Terminal size
        self.width = shutil.get_terminal_size().columns
        self.height = shutil.get_terminal_size().lines

        # State
        self.msg_count = 0
        self.current_model = ""
        self.current_branch = ""
        self.current_path = os.getcwd()
        self.context_percent = 0
        self._last_ctrl_c = 0.0
        self._is_streaming = False
        self._stream_interrupted = False
        self._pending_input: Optional[str] = None
        self._should_exit = False
        self._hint_message = ""
        self._is_processing = False

        # Callback for processing input (set by session loop)
        self._on_submit: Optional[Callable[[str], None]] = None

        # Chat messages
        self.messages: List[ChatMessage] = []

        # Streaming state
        self._stream_state: Optional[Dict] = None
        self._last_stats: Optional[ResponseStats] = None
        self.last_tok_s = 0.0

        # Input history
        self._history = self._get_history()
        
        # Mock console that redirects to TUI (prevents stdout breaks)
        self.console = TUIConsole(self)

        # Build the UI
        self._build_ui()
    
    def set_submit_handler(self, callback: Callable[[str], None]):
        """Set callback for when user submits input"""
        self._on_submit = callback

    def _get_history(self):
        """Get command history"""
        try:
            from core.paths import get_data_dir
            history_dir = get_data_dir() / "history"
        except ImportError:
            history_dir = Path.home() / ".local" / "share" / "ryx" / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        return FileHistory(str(history_dir / "tui_history"))

    def _build_ui(self):
        """Build the fullscreen UI layout"""
        # Key bindings
        self.kb = KeyBindings()

        @self.kb.add('c-c')
        def handle_ctrl_c(event):
            """Single Ctrl+C interrupts, double Ctrl+C exits"""
            now = time.time()

            # Double Ctrl+C within 1 second = exit
            if now - self._last_ctrl_c < 1.0:
                self._should_exit = True
                event.app.exit(result=None)
                return

            self._last_ctrl_c = now

            # Single Ctrl+C = interrupt current operation
            if self._is_streaming:
                self._stream_interrupted = True
                self._is_streaming = False
                self.add_system("[Interrupted]", "warning")
            else:
                self._hint_message = "[Press Ctrl+C again to exit]"
                self._invalidate()

        @self.kb.add('c-l')
        def handle_ctrl_l(event):
            """Clear chat history"""
            self.messages = []
            self._hint_message = "Chat cleared"
            self._invalidate()

        @self.kb.add('enter')
        def handle_enter(event):
            """Submit input - process via callback without exiting fullscreen"""
            text = self.input_buffer.text.strip()
            if text and not self._is_processing:
                self.input_buffer.reset()
                self._hint_message = ""
                
                # Add user message immediately
                self.add_user(text)
                
                # If we have a callback, process in background
                if self._on_submit:
                    self._is_processing = True
                    self._hint_message = "Processing..."
                    self._invalidate()
                    
                    # Run in background thread with stderr capture
                    import threading
                    import io
                    import sys
                    import logging
                    
                    def process():
                        # Suppress logging output that would break TUI
                        old_stderr = sys.stderr
                        sys.stderr = io.StringIO()
                        
                        # Also suppress specific loggers
                        searxng_logger = logging.getLogger('core.council.searxng')
                        old_level = searxng_logger.level
                        searxng_logger.setLevel(logging.CRITICAL)
                        
                        try:
                            self._on_submit(text)
                        except Exception as e:
                            # Show error in TUI
                            self.add_system(f"Error: {e}", "error")
                        finally:
                            # Restore stderr and logger
                            sys.stderr = old_stderr
                            searxng_logger.setLevel(old_level)
                            
                            self._is_processing = False
                            self._hint_message = ""
                            self._invalidate()
                    
                    thread = threading.Thread(target=process, daemon=True)
                    thread.start()
                else:
                    # No callback - store for legacy prompt() mode
                    self._pending_input = text
                    event.app.exit(result=text)

        @self.kb.add('c-d')
        def handle_ctrl_d(event):
            """Exit on Ctrl+D"""
            self._pending_input = '/quit'
            event.app.exit(result='/quit')

        # Input buffer
        self.input_buffer = Buffer(
            completer=SlashCommandCompleter(),
            history=self._history,
            multiline=False,
        )

        # Chat history window (scrollable)
        self.chat_window = ScrollablePane(
            Window(
                FormattedTextControl(self._get_chat_text),
                wrap_lines=True,
            ),
            show_scrollbar=True,
        )

        # Status bar
        self.status_window = Window(
            FormattedTextControl(self._get_status_text),
            height=1,
            style='class:status-bar',
        )

        # Input box top border
        self.input_top = Window(
            FormattedTextControl(self._get_input_top),
            height=1,
        )

        # Input area with prompt
        self.input_window = VSplit([
            Window(
                FormattedTextControl(lambda: [('class:input-border', '│ '), ('class:prompt-char', '> ')]),
                width=4,
            ),
            Window(
                BufferControl(buffer=self.input_buffer),
                wrap_lines=False,
            ),
            Window(
                FormattedTextControl(lambda: [('class:input-border', ' │')]),
                width=2,
            ),
        ], height=1)

        # Input box bottom border
        self.input_bottom = Window(
            FormattedTextControl(self._get_input_bottom),
            height=1,
        )

        # Hints bar
        self.hints_window = Window(
            FormattedTextControl(self._get_hints_text),
            height=1,
        )

        # Bottom section (fixed height)
        self.bottom_section = HSplit([
            self.status_window,
            self.input_top,
            self.input_window,
            self.input_bottom,
            self.hints_window,
        ])

        # Main layout
        self.layout = Layout(
            HSplit([
                self.chat_window,  # Takes remaining space
                self.bottom_section,  # Fixed at bottom
            ])
        )

        # Application
        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            style=TUI_STYLE,
            full_screen=True,
            mouse_support=True,
        )

    def _invalidate(self):
        """Refresh the display"""
        if self.app.is_running:
            self.app.invalidate()

    def _get_chat_text(self) -> FormattedText:
        """Get formatted chat history"""
        parts = []

        if not self.messages:
            # Welcome message
            parts.append(('class:muted', '\n  Welcome to Ryx AI\n'))
            parts.append(('class:dim', '  Type a message to get started. Use /help for commands.\n'))
            return FormattedText(parts)

        parts.append(('', '\n'))

        for msg in self.messages:
            if msg.role == 'user':
                parts.append(('class:user-label', '  You: '))
                parts.append(('class:user', msg.content))
                parts.append(('', '\n\n'))
            elif msg.role == 'assistant':
                parts.append(('class:assistant-label', '  Ryx: '))
                if msg.is_streaming:
                    parts.append(('class:assistant', msg.content))
                    parts.append(('class:spinner', ' ●'))  # Streaming indicator
                else:
                    parts.append(('class:assistant', msg.content))
                parts.append(('', '\n\n'))
            else:  # system
                style = f'class:{msg.style}' if msg.style else 'class:system'
                parts.append(('', '  '))
                parts.append((style, msg.content))
                parts.append(('', '\n\n'))

        return FormattedText(parts)

    def _get_status_text(self) -> FormattedText:
        """Get status bar text"""
        parts = []

        # Left: path and branch
        path = self.current_path.replace(os.path.expanduser("~"), "~")
        if len(path) > 40:
            path = "~/" + os.path.basename(self.current_path)

        parts.append(('class:status-path', f' {path}'))

        if self.current_branch:
            parts.append(('class:dim', '['))
            parts.append(('class:status-branch', f'⎇ {self.current_branch}'))
            parts.append(('class:dim', ']'))

        # Calculate left length
        left_len = len(path) + 1
        if self.current_branch:
            left_len += len(self.current_branch) + 4

        # Right: model and context
        model_name = self.current_model or "no model"
        if '/' in model_name:
            model_name = model_name.split('/')[-1]
        if len(model_name) > 20:
            model_name = model_name[:17] + "..."

        context_str = f'{self.context_percent}%'

        # Context color
        if self.context_percent < 60:
            ctx_style = 'class:context-green'
        elif self.context_percent < 80:
            ctx_style = 'class:context-yellow'
        elif self.context_percent < 95:
            ctx_style = 'class:context-yellow-bold'
        else:
            ctx_style = 'class:context-red-bold'

        right_text = f'{model_name} │ {context_str} context '
        right_len = len(right_text)

        # Get terminal width
        try:
            width = shutil.get_terminal_size().columns
        except:
            width = 80

        # Padding
        padding = max(1, width - left_len - right_len)
        parts.append(('class:status-bar', ' ' * padding))

        parts.append(('class:status-model', model_name))
        parts.append(('class:dim', ' │ '))
        parts.append((ctx_style, context_str))
        parts.append(('class:dim', ' context '))

        return FormattedText(parts)

    def _get_input_top(self) -> FormattedText:
        """Get input box top border"""
        try:
            width = shutil.get_terminal_size().columns - 4
        except:
            width = 76
        return FormattedText([('class:input-border', '╭' + '─' * width + '╮')])

    def _get_input_bottom(self) -> FormattedText:
        """Get input box bottom border"""
        try:
            width = shutil.get_terminal_size().columns - 4
        except:
            width = 76
        return FormattedText([('class:input-border', '╰' + '─' * width + '╯')])

    def _get_hints_text(self) -> FormattedText:
        """Get hints bar text"""
        parts = []

        # Left: shortcuts
        parts.append(('class:hint-key', ' Ctrl+c'))
        parts.append(('class:hint', ' Exit · '))
        parts.append(('class:hint-key', 'Ctrl+l'))
        parts.append(('class:hint', ' Clear · '))
        parts.append(('class:hint-key', 'Tab'))
        parts.append(('class:hint', ' Complete'))

        # Show hint message if any
        if self._hint_message:
            parts.append(('class:warning', f'  {self._hint_message}'))
            self._hint_message = ""  # Clear after showing

        # Right: session info
        session_info = f'Session: {self.msg_count} requests '
        try:
            width = shutil.get_terminal_size().columns
        except:
            width = 80

        left_len = 45  # Approximate
        padding = max(1, width - left_len - len(session_info))
        parts.append(('class:hint', ' ' * padding))
        parts.append(('class:muted', session_info))

        return FormattedText(parts)

    # ═══════════════════════════════════════════════════════════════════════════
    # Public Interface (matches CLI class)
    # ═══════════════════════════════════════════════════════════════════════════

    def run(self):
        """Run the fullscreen TUI - stays in fullscreen until exit"""
        try:
            self.app.run()
        except (EOFError, KeyboardInterrupt):
            pass

    def run_with_callback(self, on_submit: Callable[[str], None]):
        """Run TUI with a callback for processing input - PREFERRED method"""
        self._on_submit = on_submit
        try:
            self.app.run()
        except (EOFError, KeyboardInterrupt):
            pass

    def prompt(self) -> str:
        """Get user input - legacy mode, exits fullscreen temporarily"""
        self._pending_input = None
        self._hint_message = ""
        self._on_submit = None  # Disable callback mode

        try:
            result = self.app.run()
            if result is None:
                if self._should_exit:
                    return "/quit"
                return ""
            return result
        except (EOFError, KeyboardInterrupt):
            return "/quit"

    def add_user(self, content: str):
        """Add user message to chat"""
        self.messages.append(ChatMessage(role='user', content=content))
        self.msg_count += 1
        self._invalidate()

    def add_assistant(self, content: str):
        """Add assistant message to chat"""
        self.messages.append(ChatMessage(role='assistant', content=content))
        self._invalidate()

    def add_system(self, content: str, style: str = ''):
        """Add system message"""
        self.messages.append(ChatMessage(role='system', content=content, style=style))
        self._invalidate()

    def welcome(self, model: str = "", branch: str = "", cwd: str = ""):
        """Set welcome/status info"""
        if model:
            self.current_model = model
        if branch:
            self.current_branch = branch
        if cwd:
            self.current_path = cwd

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
        """Set context usage percentage"""
        self.context_percent = max(0, min(100, percent))
        self._invalidate()

    # ═══════════════════════════════════════════════════════════════════════════
    # Streaming
    # ═══════════════════════════════════════════════════════════════════════════

    def stream_start(self, model: str = ""):
        """Start streaming a response"""
        self._stream_state = {
            "tokens": 0,
            "start": time.time(),
            "model": model,
            "buffer": "",
        }
        self._is_streaming = True
        self._stream_interrupted = False
        # Add empty streaming message
        self.messages.append(ChatMessage(role='assistant', content='', is_streaming=True))
        self._invalidate()

    def stream_token(self, token: str):
        """Add a token to the streaming response"""
        if self._stream_state and not self._stream_interrupted:
            self._stream_state["tokens"] += 1
            self._stream_state["buffer"] += token
            # Update the last message
            if self.messages and self.messages[-1].is_streaming:
                self.messages[-1].content = self._stream_state["buffer"]
                self._invalidate()

    def stream_end(self) -> ResponseStats:
        """End streaming"""
        self._is_streaming = False

        if not self._stream_state:
            return ResponseStats()

        duration = time.time() - self._stream_state["start"]
        tokens = self._stream_state["tokens"]
        model = self._stream_state["model"]
        buffer = self._stream_state["buffer"]

        stats = ResponseStats(tokens=tokens, duration=duration, model=model)
        self._last_stats = stats
        self.last_tok_s = stats.tok_per_sec

        # Mark message as no longer streaming
        if self.messages and self.messages[-1].is_streaming:
            self.messages[-1].is_streaming = False
            self.messages[-1].content = buffer

        # Add stats as system message
        tok_s = stats.tok_per_sec
        self.add_system(f"{tokens} tokens · {tok_s:.0f} tok/s · {duration:.1f}s", "dim")

        self._stream_state = None
        return stats

    # ═══════════════════════════════════════════════════════════════════════════
    # Spinner (for non-streaming operations)
    # ═══════════════════════════════════════════════════════════════════════════

    @contextmanager
    def spinner(self, text: str = ""):
        """Show a spinner during an operation"""
        spinner_msg = ChatMessage(role='system', content=f"● {text or 'Thinking'}...", style='step')
        self.messages.append(spinner_msg)
        self._invalidate()

        try:
            yield
        finally:
            # Remove spinner message
            if spinner_msg in self.messages:
                self.messages.remove(spinner_msg)
            self._invalidate()

    def spinner_update(self, text: str):
        """Update spinner text"""
        # Find and update spinner message
        for msg in reversed(self.messages):
            if msg.style == 'step' and msg.content.startswith('●'):
                msg.content = f"● {text}..."
                self._invalidate()
                break

    # ═══════════════════════════════════════════════════════════════════════════
    # Messages
    # ═══════════════════════════════════════════════════════════════════════════

    def success(self, msg: str):
        """Success message"""
        self.add_system(f"✓ {msg}", "success")

    def error(self, msg: str):
        """Error message"""
        self.add_system(f"✗ {msg}", "error")

    def warn(self, msg: str):
        """Warning message"""
        self.add_system(f"⚠ {msg}", "warning")

    def info(self, msg: str):
        """Info message"""
        self.add_system(f"ℹ {msg}", "info")

    def muted(self, msg: str):
        """Muted message"""
        self.add_system(msg, "muted")

    def step(self, msg: str):
        """Step/progress message"""
        self.add_system(f"● {msg}", "step")

    def confirm(self, msg: str) -> bool:
        """Confirmation prompt - adds to chat and waits for y/n"""
        self.add_system(f"? {msg} [y/N]", "warning")
        # For now, use simple input since we're in fullscreen
        # This will be handled by the main loop
        return False

    def reply(self, msg: str):
        """AI reply"""
        self.add_assistant(msg)

    def nl(self):
        """Add spacing"""
        pass  # In fullscreen, messages have built-in spacing

    def assistant(self, msg: str, model: str = ""):
        """Print assistant response"""
        self.add_assistant(msg)

    # ═══════════════════════════════════════════════════════════════════════════
    # Thinking Steps (colored status dots)
    # ═══════════════════════════════════════════════════════════════════════════

    def thinking(self, text: str):
        """Show thinking/planning step (yellow dot)"""
        self.add_system(f"● {text}", "thinking")
        self._invalidate()

    def step_start(self, text: str):
        """Step starting (cyan dot, animated feel)"""
        self.add_system(f"◐ {text}...", "step")
        self._invalidate()

    def step_done(self, text: str, detail: str = ""):
        """Step completed successfully (green dot)"""
        msg = f"● {text}"
        if detail:
            msg += f"\n   └ {detail}"
        self.add_system(msg, "success")
        self._invalidate()

    def step_fail(self, text: str, error: str = ""):
        """Step failed (red dot)"""
        msg = f"● {text}"
        if error:
            msg += f"\n   └ {error}"
        self.add_system(msg, "error")
        self._invalidate()
    
    def step_info(self, text: str, detail: str = ""):
        """Info step (blue dot)"""
        msg = f"● {text}"
        if detail:
            msg += f"\n   └ {detail}"
        self.add_system(msg, "info")
        self._invalidate()
    
    def step_warn(self, text: str, detail: str = ""):
        """Warning step (yellow dot)"""
        msg = f"● {text}"
        if detail:
            msg += f"\n   └ {detail}"
        self.add_system(msg, "warning")
        self._invalidate()

    # ═══════════════════════════════════════════════════════════════════════════
    # Help
    # ═══════════════════════════════════════════════════════════════════════════

    def help_box(self, sections: Dict[str, List[tuple]] = None):
        """Show help in chat"""
        help_text = """Shortcuts:
  @          Include file contents
  !          Run shell command
  Ctrl+c     Interrupt / Exit (double-press)
  Ctrl+l     Clear chat
  Tab        Complete command

Commands:
  /help      Show this help
  /clear     Clear conversation
  /model     Show/change model
  /style     Change response style
  /search    Web search
  /quit      Exit

Examples:
  hyprland config     Open config file
  search recursion    Web search
  create login.py     Generate code"""
        self.add_system(help_text, "info")

    # ═══════════════════════════════════════════════════════════════════════════
    # Code & Diff
    # ═══════════════════════════════════════════════════════════════════════════

    def code(self, content: str, language: str = "python", title: str = ""):
        """Show code block"""
        header = f"─── {title} ───" if title else "───"
        self.add_system(f"{header}\n{content}\n───", "muted")

    def diff(self, filename: str, old_lines: List[str], new_lines: List[str]):
        """Show diff"""
        import difflib
        diff_lines = list(difflib.unified_diff(
            old_lines, new_lines, fromfile=filename, tofile=filename, lineterm=""
        ))
        if diff_lines:
            diff_text = '\n'.join(diff_lines[:30])
            self.add_system(f"─── {filename} ───\n{diff_text}", "muted")

    def diff_summary(self, files: List[Dict[str, Any]]):
        """Show diff summary"""
        for f in files:
            name = f.get("name", "unknown")
            added = f.get("added", 0)
            removed = f.get("removed", 0)
            self.add_system(f"✓ {name} +{added} -{removed}", "success")

    def search_results(self, results: List[Dict], query: str = "", limit: int = 5):
        """Show search results"""
        if not results:
            self.add_system("No results", "muted")
            return

        lines = []
        if query:
            lines.append(f'{len(results)} results for "{query}":')

        for i, r in enumerate(results[:limit]):
            title = r.get("title", "No title")[:55]
            lines.append(f"  {i+1}. {title}")

        self.add_system('\n'.join(lines), "info")

    def error_detail(self, file: str, error: str, line: int = None, suggestion: str = None):
        """Error with detail"""
        msg = f"✗ {file}"
        if line:
            msg += f":{line}"
        msg += f"\n  {error}"
        if suggestion:
            msg += f"\n  → {suggestion}"
        self.add_system(msg, "error")

    # ═══════════════════════════════════════════════════════════════════════════
    # Plan UI
    # ═══════════════════════════════════════════════════════════════════════════

    def show_plan(self, plan_steps: List[Dict[str, Any]], task: str = "") -> None:
        """Show execution plan"""
        lines = []
        if task:
            lines.append(f"Execution Plan: {task}")
        else:
            lines.append("Execution Plan:")

        for i, step in enumerate(plan_steps, 1):
            action = step.get("action", "modify")
            file_path = step.get("file_path", step.get("file", ""))
            description = step.get("description", "")
            lines.append(f"  {i}. [{action}] {file_path}")
            if description:
                lines.append(f"      {description}")

        self.add_system('\n'.join(lines), "info")

    def plan_approval_prompt(self, plan_steps: List[Dict[str, Any]], task: str = "") -> str:
        """Show plan and get approval"""
        self.show_plan(plan_steps, task)
        self.add_system("[y] Approve  [n] Cancel  [e] Edit", "muted")
        return 'y'  # Default approve for now

    def show_plan_progress(self, plan_steps: List[Dict[str, Any]], current_step: int = 0):
        """Show plan with progress"""
        lines = []
        for i, step in enumerate(plan_steps):
            if step.get("completed", False):
                icon = "✓"
            elif step.get("failed", False):
                icon = "✗"
            elif i == current_step:
                icon = "▸"
            else:
                icon = "○"

            action = step.get("action", "modify")
            file_path = step.get("file_path", "")[:30]
            lines.append(f"  {icon} {i+1}. [{action}] {file_path}")

        self.add_system('\n'.join(lines), "step")

    # ═══════════════════════════════════════════════════════════════════════════
    # Phase support
    # ═══════════════════════════════════════════════════════════════════════════

    def phase(self, name: str, status: str = "run", detail: str = ""):
        """Show phase status"""
        icons = {"idle": "○", "run": "●", "ok": "✓", "done": "✓", "err": "✗", "skip": "○"}
        icon = icons.get(status, "●")
        msg = f"{icon} {name}"
        if detail:
            msg += f" {detail}"

        style = "step" if status == "run" else ("success" if status in ("ok", "done") else "muted")
        self.add_system(msg, style)

    def phase_steps(self, steps: List[str], current: int = -1):
        """Show steps within a phase"""
        lines = []
        for i, step in enumerate(steps):
            if i < current:
                icon = "✓"
            elif i == current:
                icon = "▸"
            else:
                icon = "○"
            lines.append(f"    {icon} {i+1}. {step}")
        self.add_system('\n'.join(lines), "muted")

    def clear(self):
        """Clear all messages"""
        self.messages = []
        self._invalidate()


# ═══════════════════════════════════════════════════════════════════════════════
# Legacy TUI wrapper (non-fullscreen fallback)
# ═══════════════════════════════════════════════════════════════════════════════

class TUI(FullscreenTUI):
    """
    TUI class - now uses fullscreen mode by default.
    This is a thin wrapper for backward compatibility.
    """

    def __init__(self):
        super().__init__()
        self._welcome_shown = False
        # console is already set by FullscreenTUI to TUIConsole
        # Don't override it with rich.Console!

    @property
    def history(self):
        """Legacy access to history buffer"""
        return self


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


def get_cli():
    """Get CLI instance - returns TUI"""
    return get_tui()


def get_ui():
    """Legacy compatibility"""
    return get_tui()
