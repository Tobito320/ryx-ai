"""
Ryx AI - Terminal UI with Fixed Bottom Prompt

Copilot CLI / Claude CLI style interface:
- Scrollable chat history at top
- Fixed input box at bottom with rounded corners
- Git repo/branch info on left
- Model + context truncation indicator on right
- Status bar with shortcuts

Uses prompt_toolkit for the TUI layout.
"""

import os
import sys
import subprocess
from datetime import datetime
from typing import Optional, List, Dict, Callable

from prompt_toolkit import PromptSession
from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window, WindowAlign, FormattedTextControl, BufferControl, ScrollablePane
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML, FormattedText
from prompt_toolkit.widgets import TextArea, Frame, Box
from prompt_toolkit.document import Document


class RyxTUI:
    """
    Terminal UI with fixed bottom prompt box.
    
    Layout:
    ┌─────────────────────────────────────────────────────┐
    │  Scrollable Chat History                            │
    │                                                     │
    │  User: Hello                                        │
    │  Ryx: Hi! How can I help?                           │
    │                                                     │
    ├─────────────────────────────────────────────────────┤
    │  ~/repo[⎇ main]              model-name │ 45% ctx   │
    │ ╭─────────────────────────────────────────────────╮ │
    │ │ > _                                             │ │
    │ ╰─────────────────────────────────────────────────╯ │
    │  Ctrl+c Exit · Ctrl+l Clear    Session: 5 requests  │
    └─────────────────────────────────────────────────────┘
    """
    
    def __init__(self):
        self.messages: List[Dict] = []
        self.model_name = "qwen2.5-7b"
        self.context_percent = 0
        self.session_requests = 0
        self.git_info = self._get_git_info()
        
        # Callbacks
        self.on_submit: Optional[Callable[[str], None]] = None
        self.on_exit: Optional[Callable[[], None]] = None
        
        # Setup components
        self._setup_style()
        self._setup_keybindings()
        self._setup_layout()
    
    def _get_git_info(self) -> str:
        """Get git repo and branch info, or directory path."""
        try:
            # Get repo root name
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                capture_output=True, text=True, timeout=1
            )
            if result.returncode == 0:
                repo_path = result.stdout.strip()
                repo_name = os.path.basename(repo_path)
                
                # Get branch
                result = subprocess.run(
                    ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                    capture_output=True, text=True, timeout=1
                )
                if result.returncode == 0:
                    branch = result.stdout.strip()
                    return f"~/{repo_name}[⎇ {branch}]"
            
        except Exception:
            pass
        
        # Fallback to current directory
        cwd = os.getcwd()
        home = os.path.expanduser("~")
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]
        return cwd
    
    def _get_context_color(self) -> str:
        """Get color based on context percentage."""
        if self.context_percent >= 90:
            return "ansired bold"
        elif self.context_percent >= 70:
            return "ansiyellow"
        elif self.context_percent >= 50:
            return "ansiyellow"
        else:
            return "ansigreen"
    
    def _get_context_label(self) -> str:
        """Get context status label."""
        if self.context_percent >= 95:
            return "Truncated"
        elif self.context_percent >= 80:
            return f"{self.context_percent}% (near limit)"
        else:
            return f"{self.context_percent}%"
    
    def _setup_style(self):
        """Setup prompt_toolkit styles."""
        self.style = Style.from_dict({
            # Chat area
            'chat': 'bg:#1a1a2e',
            'user': '#00ff88 bold',
            'assistant': '#88ccff',
            'system': '#888888 italic',
            
            # Input box
            'input-box': 'bg:#16213e',
            'input-border': '#4a5568',
            'input-text': '#ffffff',
            
            # Header bar
            'header-left': '#88ccff',
            'header-right': '#ffffff',
            'model-name': '#00ff88',
            'context-ok': '#00ff88',
            'context-warn': '#ffaa00',
            'context-danger': '#ff4444 bold',
            
            # Footer
            'footer': '#666666',
            'shortcut': '#888888',
            'shortcut-key': '#00ff88',
        })
    
    def _setup_keybindings(self):
        """Setup key bindings."""
        self.kb = KeyBindings()
        
        @self.kb.add('c-c')
        def exit_(event):
            """Exit on Ctrl+C."""
            if self.on_exit:
                self.on_exit()
            event.app.exit()
        
        @self.kb.add('c-l')
        def clear_(event):
            """Clear screen on Ctrl+L."""
            self.messages = []
            self._update_chat()
        
        @self.kb.add('enter')
        def submit_(event):
            """Submit input on Enter."""
            buf = event.app.current_buffer
            text = buf.text.strip()
            if text:
                if self.on_submit:
                    self.on_submit(text)
                buf.reset()
    
    def _format_chat_history(self) -> FormattedText:
        """Format chat history for display."""
        lines = []
        
        for msg in self.messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'user':
                lines.append(('class:user', f"\n  You: "))
                lines.append(('', content + "\n"))
            elif role == 'assistant':
                lines.append(('class:assistant', f"\n  Ryx: "))
                lines.append(('', content + "\n"))
            else:
                lines.append(('class:system', f"\n  [{role}] {content}\n"))
        
        if not lines:
            lines.append(('class:system', '\n  Start a conversation...\n'))
        
        return FormattedText(lines)
    
    def _get_header_left(self) -> FormattedText:
        """Get left side of header (git info)."""
        return FormattedText([
            ('class:header-left', f" {self.git_info}")
        ])
    
    def _get_header_right(self) -> FormattedText:
        """Get right side of header (model + context)."""
        ctx_class = f"class:context-{'danger' if self.context_percent >= 90 else 'warn' if self.context_percent >= 70 else 'ok'}"
        
        return FormattedText([
            ('class:model-name', f"{self.model_name}"),
            ('', ' │ '),
            (ctx_class, self._get_context_label()),
            ('', ' ')
        ])
    
    def _get_footer_left(self) -> FormattedText:
        """Get left footer (shortcuts)."""
        return FormattedText([
            ('class:shortcut-key', ' Ctrl+c'),
            ('class:shortcut', ' Exit · '),
            ('class:shortcut-key', 'Ctrl+l'),
            ('class:shortcut', ' Clear · '),
            ('class:shortcut-key', 'Tab'),
            ('class:shortcut', ' Complete'),
        ])
    
    def _get_footer_right(self) -> FormattedText:
        """Get right footer (session info)."""
        return FormattedText([
            ('class:footer', f'Session: {self.session_requests} requests '),
        ])
    
    def _setup_layout(self):
        """Setup the TUI layout."""
        # Chat history buffer
        self.chat_buffer = Buffer(read_only=True)
        
        # Input buffer
        self.input_buffer = Buffer(
            multiline=False,
            accept_handler=lambda buff: None,  # Handled by keybinding
        )
        
        # Chat window (scrollable)
        chat_window = Window(
            content=FormattedTextControl(self._format_chat_history),
            wrap_lines=True,
            right_margins=[ScrollbarMargin(display_arrows=True)],
        )
        
        # Header bar (above input box)
        header = VSplit([
            Window(
                content=FormattedTextControl(self._get_header_left),
                height=1,
                align=WindowAlign.LEFT,
            ),
            Window(
                content=FormattedTextControl(self._get_header_right),
                height=1,
                align=WindowAlign.RIGHT,
            ),
        ])
        
        # Input box with border
        input_area = Box(
            body=Window(
                content=BufferControl(buffer=self.input_buffer),
                height=1,
            ),
            padding=0,
            padding_left=1,
            char='│',
            style='class:input-border',
        )
        
        # Rounded box frame (simulated with unicode)
        input_frame = HSplit([
            Window(content=FormattedTextControl(lambda: [('class:input-border', '╭' + '─' * 78 + '╮')]), height=1),
            VSplit([
                Window(content=FormattedTextControl(lambda: [('class:input-border', '│')]), width=1),
                Window(content=FormattedTextControl(lambda: [('', ' > ')]), width=3),
                Window(content=BufferControl(buffer=self.input_buffer), wrap_lines=True),
                Window(content=FormattedTextControl(lambda: [('class:input-border', '│')]), width=1),
            ], height=1),
            Window(content=FormattedTextControl(lambda: [('class:input-border', '╰' + '─' * 78 + '╯')]), height=1),
        ])
        
        # Footer bar
        footer = VSplit([
            Window(
                content=FormattedTextControl(self._get_footer_left),
                height=1,
                align=WindowAlign.LEFT,
            ),
            Window(
                content=FormattedTextControl(self._get_footer_right),
                height=1,
                align=WindowAlign.RIGHT,
            ),
        ])
        
        # Main layout
        self.layout = Layout(
            HSplit([
                # Chat history (takes remaining space)
                Window(
                    content=FormattedTextControl(self._format_chat_history),
                    wrap_lines=True,
                ),
                # Separator
                Window(height=1, char='─', style='class:input-border'),
                # Header above input
                header,
                # Input box
                input_frame,
                # Footer
                footer,
            ])
        )
    
    def _update_chat(self):
        """Refresh chat display."""
        if hasattr(self, 'app') and self.app:
            self.app.invalidate()
    
    def add_message(self, role: str, content: str):
        """Add a message to the chat."""
        self.messages.append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })
        self.session_requests += 1
        self._update_chat()
    
    def set_model(self, model_name: str):
        """Update displayed model name."""
        self.model_name = model_name
        self._update_chat()
    
    def set_context_percent(self, percent: int):
        """Update context usage percentage."""
        self.context_percent = min(100, max(0, percent))
        self._update_chat()
    
    def run(self):
        """Run the TUI application."""
        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            style=self.style,
            full_screen=True,
            mouse_support=True,
        )
        self.app.run()
    
    def get_input(self) -> str:
        """Get current input text."""
        return self.input_buffer.text


# Simpler version for integration with existing session loop
class SimpleRyxPrompt:
    """
    Simplified TUI prompt that integrates with existing session loop.
    Uses prompt_toolkit's bottom_toolbar for the fixed prompt experience.
    """
    
    def __init__(self):
        self.model_name = "qwen2.5-7b"
        self.context_percent = 0
        self.session_requests = 0
        self.git_info = self._get_git_info()
        
        self.session = PromptSession(
            message=self._get_prompt,
            bottom_toolbar=self._get_toolbar,
            style=self._get_style(),
            complete_while_typing=True,
        )
    
    def _get_git_info(self) -> str:
        """Get git repo and branch info."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                capture_output=True, text=True, timeout=1
            )
            if result.returncode == 0:
                repo_name = os.path.basename(result.stdout.strip())
                
                result = subprocess.run(
                    ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                    capture_output=True, text=True, timeout=1
                )
                if result.returncode == 0:
                    branch = result.stdout.strip()
                    return f"~/{repo_name}[⎇ {branch}]"
        except:
            pass
        
        cwd = os.getcwd()
        home = os.path.expanduser("~")
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]
        return cwd
    
    def _get_style(self) -> Style:
        return Style.from_dict({
            'bottom-toolbar': 'bg:#333333 #888888',
            'prompt': '#00ff88 bold',
            'git-info': '#88ccff',
            'model': '#00ff88',
            'context-ok': '#00ff88',
            'context-warn': '#ffaa00 bold',
            'context-danger': '#ff4444 bold',
        })
    
    def _get_prompt(self) -> FormattedText:
        """Build the prompt with git info and model."""
        ctx_style = 'context-ok'
        if self.context_percent >= 90:
            ctx_style = 'context-danger'
        elif self.context_percent >= 70:
            ctx_style = 'context-warn'
        
        ctx_label = "Truncated" if self.context_percent >= 95 else f"{self.context_percent}%"
        
        return FormattedText([
            ('class:git-info', f'{self.git_info}'),
            ('', '  '),
            ('class:model', f'{self.model_name}'),
            ('', ' │ '),
            (f'class:{ctx_style}', ctx_label),
            ('', '\n'),
            ('class:prompt', '╭─────────────────────────────────────────────────────────────────────────────────╮\n'),
            ('class:prompt', '│ > '),
        ])
    
    def _get_toolbar(self) -> FormattedText:
        """Build the bottom toolbar."""
        return FormattedText([
            ('', '╰─────────────────────────────────────────────────────────────────────────────────╯  '),
            ('class:shortcut', 'Ctrl+c'),
            ('', ' Exit · '),
            ('class:shortcut', 'Tab'),
            ('', ' Complete'),
            ('', '  │  '),
            ('', f'Session: {self.session_requests} requests'),
        ])
    
    def prompt(self) -> str:
        """Get user input."""
        try:
            return self.session.prompt()
        except KeyboardInterrupt:
            return '/quit'
        except EOFError:
            return '/quit'
    
    def set_model(self, name: str):
        self.model_name = name
    
    def set_context(self, percent: int):
        self.context_percent = percent
    
    def increment_requests(self):
        self.session_requests += 1


if __name__ == "__main__":
    # Demo
    tui = RyxTUI()
    tui.add_message("user", "Hello!")
    tui.add_message("assistant", "Hi! How can I help you today?")
    tui.set_context_percent(35)
    
    def on_submit(text):
        tui.add_message("user", text)
        tui.add_message("assistant", f"You said: {text}")
    
    tui.on_submit = on_submit
    tui.run()
