"""
Ryx AI - UI Module
Purple-themed terminal UI with emoji status indicators
"""

import sys
from typing import Optional, List, Dict, Any
from enum import Enum


class Color:
    """ANSI color codes for terminal output"""
    # Purple theme
    PURPLE = "\033[35m"
    PURPLE_BOLD = "\033[1;35m"
    PURPLE_DIM = "\033[2;35m"

    # Standard colors
    WHITE = "\033[37m"
    WHITE_BOLD = "\033[1;37m"
    GRAY = "\033[2;37m"
    GREEN = "\033[32m"
    GREEN_BOLD = "\033[1;32m"
    YELLOW = "\033[33m"
    YELLOW_BOLD = "\033[1;33m"
    RED = "\033[31m"
    RED_BOLD = "\033[1;31m"
    CYAN = "\033[36m"
    CYAN_BOLD = "\033[1;36m"
    BLUE = "\033[34m"
    BLUE_BOLD = "\033[1;34m"

    # Reset
    RESET = "\033[0m"


class Emoji:
    """Status emoji indicators"""
    # Status
    DONE = "✅"
    SUCCESS = "✅"  # Alias for DONE (test compatibility)
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    QUESTION = "❓"

    # Actions
    PLAN = "📋"
    SEARCH = "🔍"
    BROWSE = "🌐"
    FILES = "📂"
    EDIT = "🛠️"
    TEST = "🧪"
    COMMIT = "💾"
    THINKING = "🤔"
    RUNNING = "🔄"

    # Session
    RYX = "🟣"
    USER = "👤"
    ASSISTANT = "🤖"

    # Misc
    ROCKET = "🚀"
    SPARKLE = "✨"
    BULB = "💡"
    LOCK = "🔒"


class RyxUI:
    """
    Purple-themed terminal UI for Ryx AI

    Features:
    - Consistent purple color scheme
    - Emoji status indicators
    - Formatted output for plans, results, errors
    - Progress indicators
    """

    def __init__(self, show_emoji: bool = True):
        """
        Initialize UI

        Args:
            show_emoji: Whether to show emoji (disable for non-emoji terminals)
        """
        self.show_emoji = show_emoji

    def _emoji(self, emoji: str) -> str:
        """Get emoji if enabled"""
        return emoji if self.show_emoji else ""

    def header(self, tier: str = "balanced", model: str = "qwen2.5-coder:14b", repo: str = "~/ryx-ai", safety: str = "normal"):
        """Print session header"""
        print()
        print(f"{Color.PURPLE_BOLD}╭{'─' * 60}╮{Color.RESET}")
        print(f"{Color.PURPLE_BOLD}│{Color.RESET} {self._emoji(Emoji.RYX)} {Color.PURPLE_BOLD}ryx{Color.RESET} – Local AI Agent")
        print(f"{Color.PURPLE_BOLD}│{Color.RESET}")
        print(f"{Color.PURPLE_BOLD}│{Color.RESET} {Color.GRAY}Tier:{Color.RESET} {tier} ({Color.CYAN}{model}{Color.RESET})")
        print(f"{Color.PURPLE_BOLD}│{Color.RESET} {Color.GRAY}Repo:{Color.RESET} {repo}")
        print(f"{Color.PURPLE_BOLD}│{Color.RESET} {Color.GRAY}Safety:{Color.RESET} {safety}")
        print(f"{Color.PURPLE_BOLD}╰{'─' * 60}╯{Color.RESET}")
        print()

    def prompt(self) -> str:
        """Show input prompt and get user input"""
        try:
            return input(f"{Color.PURPLE_BOLD}>{Color.RESET} ").strip()
        except EOFError:
            return "/quit"
        except KeyboardInterrupt:
            print()
            return ""

    def user_message(self, text: str):
        """Display user message"""
        print(f"\n{Color.PURPLE_BOLD}You:{Color.RESET} {text}")

    def assistant_message(self, text: str, model: Optional[str] = None):
        """Display assistant message"""
        model_tag = f" {Color.GRAY}[{model}]{Color.RESET}" if model else ""
        print(f"\n{Color.PURPLE}Ryx:{Color.RESET}{model_tag} {text}")

    def status(self, emoji: str, message: str, color: str = Color.WHITE):
        """Print status message with emoji"""
        print(f"{self._emoji(emoji)}  {color}{message}{Color.RESET}")

    def step(self, emoji: str, message: str):
        """Print step in a workflow"""
        print(f"  {self._emoji(emoji)} {message}")

    def plan(self, steps: List[str]):
        """Display a numbered plan"""
        print(f"\n{self._emoji(Emoji.PLAN)} {Color.PURPLE_BOLD}Plan:{Color.RESET}")
        for i, step in enumerate(steps, 1):
            print(f"  {Color.PURPLE}{i}.{Color.RESET} {step}")
        print()

    def thinking(self, message: str = "Thinking..."):
        """Show thinking indicator"""
        print(f"{self._emoji(Emoji.THINKING)} {Color.GRAY}{message}{Color.RESET}", end="\r")
        sys.stdout.flush()

    def clear_thinking(self):
        """Clear thinking indicator"""
        print(" " * 50, end="\r")
        sys.stdout.flush()

    def success(self, message: str):
        """Print success message"""
        print(f"{self._emoji(Emoji.DONE)} {Color.GREEN}{message}{Color.RESET}")

    def error(self, message: str):
        """Print error message"""
        print(f"{self._emoji(Emoji.ERROR)} {Color.RED}{message}{Color.RESET}")

    def warning(self, message: str):
        """Print warning message"""
        print(f"{self._emoji(Emoji.WARNING)} {Color.YELLOW}{message}{Color.RESET}")

    def info(self, message: str):
        """Print info message"""
        print(f"{self._emoji(Emoji.INFO)} {Color.CYAN}{message}{Color.RESET}")

    def code_block(self, code: str, language: str = ""):
        """Display code block"""
        print(f"\n{Color.GRAY}```{language}{Color.RESET}")
        print(f"{Color.CYAN}{code}{Color.RESET}")
        print(f"{Color.GRAY}```{Color.RESET}")

    def file_path(self, path: str, exists: bool = True):
        """Display file path"""
        status = f"{Color.GREEN}✓{Color.RESET}" if exists else f"{Color.RED}✗{Color.RESET}"
        print(f"  {status} {Color.CYAN}{path}{Color.RESET}")

    def confirm(self, message: str, default: bool = False) -> bool:
        """Ask for confirmation"""
        default_str = "[Y/n]" if default else "[y/N]"
        try:
            response = input(f"{self._emoji(Emoji.QUESTION)} {message} {default_str}: ").strip().lower()
            if not response:
                return default
            return response in ['y', 'yes']
        except (EOFError, KeyboardInterrupt):
            return False

    def select(self, message: str, options: List[str]) -> Optional[int]:
        """Show selection menu"""
        print(f"\n{self._emoji(Emoji.QUESTION)} {message}")
        for i, option in enumerate(options, 1):
            print(f"  {Color.PURPLE}[{i}]{Color.RESET} {option}")

        try:
            response = input(f"\n{Color.PURPLE}>{Color.RESET} ").strip()
            if response.isdigit():
                idx = int(response) - 1
                if 0 <= idx < len(options):
                    return idx
        except (EOFError, KeyboardInterrupt):
            pass

        return None

    def tool_call(self, tool_name: str, params: Dict[str, Any]):
        """Display tool call"""
        param_str = ", ".join([f"{k}={repr(v)[:30]}" for k, v in params.items()])
        print(f"  {self._emoji(Emoji.RUNNING)} {Color.CYAN}{tool_name}{Color.RESET}({Color.GRAY}{param_str}{Color.RESET})")

    def tool_result(self, success: bool, output: str):
        """Display tool result"""
        emoji = Emoji.DONE if success else Emoji.ERROR
        color = Color.GREEN if success else Color.RED
        output_preview = output[:100] + "..." if len(output) > 100 else output
        print(f"    {self._emoji(emoji)} {color}{output_preview}{Color.RESET}")

    def summary(self, changes: List[str], todos: Optional[List[str]] = None):
        """Display summary of changes"""
        print(f"\n{self._emoji(Emoji.DONE)} {Color.PURPLE_BOLD}Summary:{Color.RESET}")

        if changes:
            print(f"\n  {Color.GREEN_BOLD}Changes:{Color.RESET}")
            for change in changes:
                print(f"    • {change}")

        if todos:
            print(f"\n  {Color.YELLOW_BOLD}TODOs:{Color.RESET}")
            for todo in todos:
                print(f"    • {todo}")

        print()

    def divider(self, char: str = "─"):
        """Print divider line"""
        print(f"{Color.PURPLE_DIM}{char * 60}{Color.RESET}")

    def help_section(self, title: str, commands: List[tuple]):
        """Display help section"""
        print(f"\n{Color.PURPLE_BOLD}{title}{Color.RESET}")
        for cmd, desc in commands:
            print(f"  {Color.CYAN}{cmd:<25}{Color.RESET} {desc}")

    def help(self):
        """Show full help"""
        print()
        print(f"{Color.PURPLE_BOLD}╭{'─' * 60}╮{Color.RESET}")
        print(f"{Color.PURPLE_BOLD}│{Color.RESET} {self._emoji(Emoji.RYX)} Ryx AI Help")
        print(f"{Color.PURPLE_BOLD}╰{'─' * 60}╯{Color.RESET}")

        self.help_section("Commands", [
            ("/help", "Show this help"),
            ("/status", "Show current status"),
            ("/tier <name>", "Switch model tier (fast/balanced/powerful/ultra)"),
            ("/models", "List available models"),
            ("/clear", "Clear conversation context"),
            ("/save <title>", "Save conversation as note"),
            ("/quit, /exit, /q", "Exit Ryx"),
        ])

        self.help_section("Examples", [
            ("open hyprland config", "Opens config file in editor"),
            ("refactor the intent parser", "AI helps refactor code"),
            ("search for AI coding tools", "Searches web"),
            ("fix the bug in utils.py", "AI analyzes and fixes bug"),
        ])

        self.help_section("Tips", [
            ("Just type naturally", "Ryx understands context"),
            ("Use /tier fast", "For quick simple tasks"),
            ("Use /tier powerful", "For complex coding tasks"),
        ])

        print()

    def models_list(self, models: Dict[str, Dict]):
        """Display models list"""
        print(f"\n{Color.PURPLE_BOLD}Available Models:{Color.RESET}\n")

        for tier, info in models.items():
            available = info.get('available', False)
            config = info.get('config', {})

            status_icon = f"{Color.GREEN}●{Color.RESET}" if available else f"{Color.RED}○{Color.RESET}"
            tier_display = f"{Color.PURPLE_BOLD}{tier}{Color.RESET}"

            name = config.name if hasattr(config, 'name') else str(config.get('name', 'unknown'))
            desc = config.description if hasattr(config, 'description') else str(config.get('description', ''))

            print(f"  {status_icon} {tier_display}: {name}")
            print(f"      {Color.GRAY}{desc}{Color.RESET}")

        print()

    def format_response(self, response: str) -> str:
        """Format AI response with syntax highlighting"""
        lines = response.split('\n')
        formatted = []
        in_code_block = False
        code_lang = ""

        for line in lines:
            if line.strip().startswith('```'):
                if not in_code_block:
                    in_code_block = True
                    code_lang = line.strip()[3:]
                    formatted.append(f"\n{Color.GRAY}```{code_lang}{Color.RESET}")
                else:
                    in_code_block = False
                    formatted.append(f"{Color.GRAY}```{Color.RESET}")
                continue

            if in_code_block:
                formatted.append(f"{Color.CYAN}{line}{Color.RESET}")
            else:
                formatted.append(line)

        return '\n'.join(formatted)


# Global UI instance
ui = RyxUI()

# Aliases for backward compatibility with tests
# The tests expect 'Colors' and 'Icons' class names
Colors = Color
Icons = Emoji

# Singleton getter function for compatibility with tests expecting get_ui()
def get_ui() -> RyxUI:
    """Get the global UI instance (singleton pattern)."""
    return ui
