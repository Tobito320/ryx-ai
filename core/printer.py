"""
Ryx AI - Modern Terminal Printing Layer

Provides styled output matching modern CLI aesthetics:
- Rounded step blocks with borders
- Status badges (green dot for success, red for error)
- Grouped command + output blocks
- Confirmation prompts with numbered options
- Minimal status line at bottom

Uses ANSI escape codes compatible with modern terminals (kitty, alacritty, etc.)
"""

import sys
import os
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from core.theme import get_theme, Theme, ANSI


class StepStatus(Enum):
    """Status of a step/block"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ToolState:
    """State of a tool (on/off)"""
    name: str
    enabled: bool
    description: str = ""


class RyxPrinter:
    """
    Modern styled printer for Ryx CLI output.
    
    Design principles:
    - Each command+output is grouped in a visual block
    - Success = green dot, Error = red dot
    - Clean horizontal rules between sections
    - Minimal, single-column layout
    """
    
    def __init__(self, theme: Optional[Theme] = None):
        self.theme = theme or get_theme()
        self._tools: Dict[str, ToolState] = {}
        self._init_default_tools()
    
    def _init_default_tools(self):
        """Initialize default tool states"""
        self._tools = {
            "search": ToolState("search", True, "Web search capability"),
            "rag": ToolState("rag", True, "Retrieval-augmented generation"),
            "scrape": ToolState("scrape", True, "Web page scraping"),
            "files": ToolState("files", True, "File operations"),
            "shell": ToolState("shell", True, "Shell command execution"),
            "browse": ToolState("browse", True, "URL opening"),
        }
    
    def _get_terminal_width(self) -> int:
        """Get terminal width, default to 80"""
        try:
            return os.get_terminal_size().columns
        except OSError:
            return 80
    
    def _make_line(self, char: str = "─", width: Optional[int] = None) -> str:
        """Create a horizontal line"""
        width = width or min(60, self._get_terminal_width() - 4)
        return char * width
    
    # ─────────────────────────────────────────────────────────────
    # Step Block Printing
    # ─────────────────────────────────────────────────────────────
    
    def print_step_header(
        self,
        label: str,
        status: StepStatus = StepStatus.RUNNING,
        context: str = ""
    ):
        """
        Print a step header with colored status badge.
        
        Example:
          ● Bash(~/ryx-ai): ryx --health
        """
        t = self.theme
        
        # Status badge
        if status == StepStatus.SUCCESS:
            badge = t.success(t.icons["success"])
        elif status == StepStatus.ERROR:
            badge = t.error(t.icons["error"])
        elif status == StepStatus.WARNING:
            badge = t.warning(t.icons["warning"])
        elif status == StepStatus.RUNNING:
            badge = t.info(t.icons["running"])
        else:
            badge = t.dim(t.icons["pending"])
        
        # Context (like path)
        ctx_str = f"({t.dim(context)})" if context else ""
        
        # Print header
        print(f"\n{badge} {t.primary(label)}{ctx_str}")
    
    def print_step_output(self, output: str, preserve_ansi: bool = True):
        """
        Print step output as a code block.
        
        Args:
            output: The output text
            preserve_ansi: Keep existing ANSI codes in output
        """
        t = self.theme
        
        if not output.strip():
            return
        
        # Indent and print each line
        for line in output.split('\n'):
            print(f"  {line}")
    
    def print_step_block(
        self,
        label: str,
        command: Optional[str] = None,
        output: Optional[str] = None,
        status: StepStatus = StepStatus.SUCCESS,
        context: str = ""
    ):
        """
        Print a complete step block with header, command, and output.
        
        Example:
          ● Bash(~/ryx-ai)
            $ ryx --health
            Ollama: healthy (5 models)
            RAG: enabled
        """
        t = self.theme
        
        # Header
        self.print_step_header(label, status, context)
        
        # Command (if provided)
        if command:
            print(f"  {t.dim('$')} {t.info(command)}")
        
        # Output (if provided)
        if output:
            self.print_step_output(output)
    
    # ─────────────────────────────────────────────────────────────
    # Status Messages
    # ─────────────────────────────────────────────────────────────
    
    def success(self, message: str):
        """Print success message with green badge"""
        t = self.theme
        print(f"{t.success(t.icons['success'])} {message}")
    
    def error(self, message: str):
        """Print error message with red badge"""
        t = self.theme
        print(f"{t.error(t.icons['error'])} {message}")
    
    def warning(self, message: str):
        """Print warning message with yellow badge"""
        t = self.theme
        print(f"{t.warning(t.icons['warning'])} {message}")
    
    def info(self, message: str):
        """Print info message"""
        t = self.theme
        print(f"{t.info(t.icons['info'])} {message}")
    
    def dim(self, message: str):
        """Print dimmed message"""
        t = self.theme
        print(t.dim(message))
    
    # ─────────────────────────────────────────────────────────────
    # Confirmation Prompts
    # ─────────────────────────────────────────────────────────────
    
    def print_confirmation_block(
        self,
        description: str,
        command: str,
        options: Optional[List[Tuple[str, str]]] = None
    ) -> str:
        """
        Print a confirmation prompt block.
        
        Args:
            description: What will be done
            command: The command to execute
            options: List of (key, description) tuples
        
        Returns:
            User input
        
        Example:
            ─────────────────────────────────────
            Bash command
              $ sudo pacman -Syu
            
            1) Yes
            2) Yes, and don't ask again for this session
            3) No
            
            >
        """
        t = self.theme
        
        # Divider
        print(f"\n{t.border(self._make_line())}")
        
        # Description
        print(f"{t.bold(description)}")
        
        # Command preview
        print(f"  {t.dim('$')} {t.info(command)}")
        print()
        
        # Options
        if options is None:
            options = [
                ("1", "Yes"),
                ("2", "Yes, and don't ask again for this session"),
                ("3", "No"),
            ]
        
        for key, desc in options:
            print(f"  {t.primary(key)}) {desc}")
        
        print()
        
        # Prompt
        try:
            return input(f"{t.primary('>')} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return "3"  # Default to No
    
    def confirm_simple(self, message: str, default: bool = False) -> bool:
        """Simple y/n confirmation"""
        t = self.theme
        default_str = "[Y/n]" if default else "[y/N]"
        
        try:
            response = input(f"{t.primary('?')} {message} {t.dim(default_str)} ").strip().lower()
            if not response:
                return default
            return response in ['y', 'yes', 'ja', 'j']
        except (EOFError, KeyboardInterrupt):
            print()
            return False
    
    # ─────────────────────────────────────────────────────────────
    # Tool Management
    # ─────────────────────────────────────────────────────────────
    
    def print_tools(self):
        """Print list of available tools with their status"""
        t = self.theme
        
        print(f"\n{t.bold('Available Tools:')}")
        print()
        
        for name, tool in self._tools.items():
            status = t.success("ON") if tool.enabled else t.dim("OFF")
            desc = f" - {t.dim(tool.description)}" if tool.description else ""
            print(f"  {t.primary(name):<12} {status}{desc}")
        
        print()
        print(t.dim("Toggle: /tool <name> on|off"))
    
    def set_tool_state(self, name: str, enabled: bool) -> bool:
        """Set tool enabled state"""
        if name in self._tools:
            self._tools[name].enabled = enabled
            return True
        return False
    
    def get_tool_state(self, name: str) -> bool:
        """Get tool enabled state"""
        return self._tools.get(name, ToolState(name, True)).enabled
    
    def is_tool_enabled(self, name: str) -> bool:
        """Check if tool is enabled"""
        return self.get_tool_state(name)
    
    # ─────────────────────────────────────────────────────────────
    # Dividers and Decorations
    # ─────────────────────────────────────────────────────────────
    
    def divider(self, style: str = "thin"):
        """Print a divider line"""
        t = self.theme
        
        if style == "thin":
            print(t.border(self._make_line("─")))
        elif style == "double":
            print(t.border(self._make_line("═")))
        elif style == "dotted":
            print(t.border(self._make_line("·")))
        else:
            print()
    
    def spacer(self, lines: int = 1):
        """Print empty lines"""
        for _ in range(lines):
            print()
    
    # ─────────────────────────────────────────────────────────────
    # Status Line
    # ─────────────────────────────────────────────────────────────
    
    def print_status_line(
        self,
        cwd: Optional[str] = None,
        model: Optional[str] = None,
        extra: Optional[str] = None
    ):
        """
        Print a minimal status line at the bottom.
        
        Example:
          ~/ryx-ai · qwen2.5-coder:7b
        """
        t = self.theme
        parts = []
        
        if cwd:
            # Shorten home directory
            cwd = cwd.replace(os.path.expanduser("~"), "~")
            parts.append(t.dim(cwd))
        
        if model:
            parts.append(t.primary(model))
        
        if extra:
            parts.append(t.dim(extra))
        
        if parts:
            print(f"\n{t.dim(t.icons['dot']).join(parts)}")
    
    # ─────────────────────────────────────────────────────────────
    # Panels and Boxes
    # ─────────────────────────────────────────────────────────────
    
    def print_box(
        self,
        content: str,
        title: Optional[str] = None,
        width: Optional[int] = None
    ):
        """
        Print content in a rounded box.
        
        Example:
          ╭────────────────────────╮
          │ Title                  │
          ├────────────────────────┤
          │ Content here           │
          ╰────────────────────────╯
        """
        t = self.theme
        width = width or min(60, self._get_terminal_width() - 4)
        inner_width = width - 2
        
        # Top border
        print(t.border(f"{t.icons['corner_tl']}{self._make_line(width=inner_width)}{t.icons['corner_tr']}"))
        
        # Title
        if title:
            title_padded = f" {title}".ljust(inner_width)
            print(f"{t.border(t.icons['line_v'])}{t.bold(title_padded)}{t.border(t.icons['line_v'])}")
            print(t.border(f"{t.icons['tee_l']}{self._make_line(width=inner_width)}{t.icons['tee_r']}"))
        
        # Content lines
        for line in content.split('\n'):
            # Truncate if too long
            if len(line) > inner_width - 1:
                line = line[:inner_width - 4] + "..."
            line_padded = f" {line}".ljust(inner_width)
            print(f"{t.border(t.icons['line_v'])}{line_padded}{t.border(t.icons['line_v'])}")
        
        # Bottom border
        print(t.border(f"{t.icons['corner_bl']}{self._make_line(width=inner_width)}{t.icons['corner_br']}"))
    
    # ─────────────────────────────────────────────────────────────
    # Session Header/Banner
    # ─────────────────────────────────────────────────────────────
    
    def print_banner(
        self,
        mode: str = "normal",
        model: str = "default",
        browsing: bool = True
    ):
        """Print session start banner"""
        t = self.theme
        browsing_str = "ON" if browsing else "OFF"
        
        content = f"""Mode: {mode}
Model: {model}
Browsing: {browsing_str}"""
        
        self.print_box(content, title=f"{t.icons['ryx']} Ryx - Local AI Agent")
        print()
        self.dim("Type naturally. /help for commands.")
        print()
    
    # ─────────────────────────────────────────────────────────────
    # Theme Commands
    # ─────────────────────────────────────────────────────────────
    
    def print_themes(self):
        """Print available themes"""
        from core.theme import get_theme_manager
        
        t = self.theme
        tm = get_theme_manager()
        
        print(f"\n{t.bold('Available Themes:')}")
        print()
        
        for name in tm.list_themes():
            current = " (current)" if name == tm.current_theme_name else ""
            print(f"  {t.primary(name)}{t.dim(current)}")
        
        print()
        print(t.dim("Switch: /theme <name>"))
    
    def set_theme(self, name: str) -> bool:
        """Set current theme"""
        from core.theme import get_theme_manager
        
        tm = get_theme_manager()
        if tm.set_theme(name):
            self.theme = tm.theme
            return True
        return False
    
    # ─────────────────────────────────────────────────────────────
    # Input Prompt
    # ─────────────────────────────────────────────────────────────
    
    def prompt(self, prefix: str = ">") -> str:
        """Get user input with styled prompt"""
        t = self.theme
        try:
            return input(f"\n{t.primary(prefix)} ").strip()
        except EOFError:
            return "/quit"
        except KeyboardInterrupt:
            print()
            return ""
    
    # ─────────────────────────────────────────────────────────────
    # Assistant Response
    # ─────────────────────────────────────────────────────────────
    
    def assistant(self, message: str, model: Optional[str] = None):
        """Print assistant response"""
        t = self.theme
        
        model_tag = f" {t.dim(f'[{model}]')}" if model else ""
        print(f"\n{t.primary('Ryx')}{model_tag}: {message}")


# Global printer instance
_printer: Optional[RyxPrinter] = None


def get_printer() -> RyxPrinter:
    """Get or create global printer instance"""
    global _printer
    if _printer is None:
        _printer = RyxPrinter()
    return _printer
