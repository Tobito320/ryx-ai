"""
Ryx AI - UI Module
Purple-themed CLI interface with emoji status indicators
"""

import re
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any


class Colors:
    """ANSI color codes for terminal output"""
    # Reset
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Regular colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Purple theme
    PURPLE = '\033[35m'
    BRIGHT_PURPLE = '\033[95m'
    
    # Background
    BG_PURPLE = '\033[45m'


class Icons:
    """Emoji status indicators"""
    # Status
    SUCCESS = '🟣'
    ERROR = '❌'
    WARNING = '⚠️'
    INFO = 'ℹ️'
    QUESTION = '❓'
    
    # Actions
    PLAN = '📋'
    SEARCH = '🔍'
    BROWSE = '🌐'
    FILES = '📂'
    EDIT = '🛠️'
    TEST = '🧪'
    COMMIT = '💾'
    DONE = '✅'
    
    # Progress
    THINKING = '💭'
    LOADING = '⏳'
    RUNNING = '▸'
    
    # Decorative
    STAR = '⭐'
    ROCKET = '🚀'
    SPARKLE = '✨'
    
    @classmethod
    def get(cls, name: str, default: str = '•') -> str:
        """Get icon by name"""
        return getattr(cls, name.upper(), default)


class RyxUI:
    """
    Main UI class for Ryx CLI
    
    Provides:
    - Purple-themed output
    - Emoji status indicators
    - Formatted prompts and responses
    - Progress indicators
    """
    
    def __init__(self):
        """Initialize UI"""
        self.colors = Colors
        self.icons = Icons
        
    def print_header(self, model: str = "balanced", tier: str = "balanced", 
                    repo: str = "~/ryx-ai", safety: str = "normal"):
        """Print session header"""
        header = f"""
{Colors.BRIGHT_PURPLE}╭──────────────────────────────────────────────────────────╮
│  {Colors.BOLD}🟣 ryx{Colors.RESET}{Colors.BRIGHT_PURPLE} – Tobi's Technical Partner                          │
╰──────────────────────────────────────────────────────────╯{Colors.RESET}

{Colors.DIM}Tier: {Colors.RESET}{Colors.PURPLE}{tier}{Colors.RESET} ({Colors.DIM}{model}{Colors.RESET})
{Colors.DIM}Repo: {Colors.RESET}{repo}
{Colors.DIM}Safety: {Colors.RESET}{safety}

{Colors.DIM}Commands: /help /status /tier /experience /clear /quit{Colors.RESET}
"""
        print(header)
    
    def print_prompt(self):
        """Print the user input prompt"""
        print(f"\n{Colors.BRIGHT_PURPLE}Tobi:{Colors.RESET} ", end="")
        sys.stdout.flush()
    
    def print_response_header(self):
        """Print response header"""
        print(f"{Colors.PURPLE}Ryx:{Colors.RESET} ", end="")
        sys.stdout.flush()
    
    def print_thinking(self):
        """Print thinking indicator"""
        print(f"{Colors.DIM}[{Icons.THINKING} thinking...]{Colors.RESET}", end="\r")
        sys.stdout.flush()
    
    def clear_thinking(self):
        """Clear thinking indicator"""
        print(" " * 30, end="\r")
    
    def print_status(self, message: str, icon: str = None, color: str = None):
        """Print a status message with icon"""
        icon = icon or Icons.INFO
        color = color or Colors.PURPLE
        print(f"{icon} {color}{message}{Colors.RESET}")
    
    def print_success(self, message: str):
        """Print success message"""
        print(f"{Icons.DONE} {Colors.GREEN}{message}{Colors.RESET}")
    
    def print_error(self, message: str):
        """Print error message"""
        print(f"{Icons.ERROR} {Colors.RED}{message}{Colors.RESET}")
    
    def print_warning(self, message: str):
        """Print warning message"""
        print(f"{Icons.WARNING} {Colors.YELLOW}{message}{Colors.RESET}")
    
    def print_plan(self, plan: str):
        """Print a workflow plan"""
        print(f"\n{Icons.PLAN} {Colors.BOLD}Plan:{Colors.RESET}")
        for line in plan.split('\n'):
            if line.strip():
                print(f"  {Colors.DIM}{line}{Colors.RESET}")
        print()
    
    def print_step(self, step_num: int, description: str, icon: str = None):
        """Print a workflow step"""
        icon = icon or Icons.RUNNING
        print(f"  {icon} Step {step_num}: {description}")
    
    def print_step_result(self, success: bool, output: str = ""):
        """Print step result"""
        if success:
            print(f"    {Icons.DONE} Done")
        else:
            print(f"    {Icons.ERROR} Failed")
        
        if output:
            # Truncate long output
            if len(output) > 200:
                output = output[:200] + "..."
            print(f"    {Colors.DIM}{output}{Colors.RESET}")
    
    def print_summary(self, completed: int, total: int, changes: list = None):
        """Print workflow summary"""
        print(f"\n{Icons.DONE} {Colors.GREEN}Completed{Colors.RESET}")
        print(f"  {completed}/{total} steps successful")
        
        if changes:
            print(f"\n{Colors.BOLD}Changes:{Colors.RESET}")
            for change in changes:
                print(f"  • {change}")
    
    def print_divider(self, char: str = "─", width: int = 60):
        """Print a divider line"""
        print(f"{Colors.DIM}{char * width}{Colors.RESET}")
    
    def print_help(self):
        """Print help message"""
        help_text = f"""
{Colors.BRIGHT_PURPLE}╭─────────────────────────────────────────────────────────╮
│  {Colors.BOLD}Ryx - Tobi's Technical Partner{Colors.RESET}{Colors.BRIGHT_PURPLE}                         │
╰─────────────────────────────────────────────────────────╯{Colors.RESET}

{Colors.BOLD}What I Can Do (as your partner):{Colors.RESET}
  • Design & implement Hyprland menus, keybindings, workflows
  • Tune Waybar, kitty, wofi, and other configs
  • Manage themes and wallpapers across your setup
  • Refactor code, fix bugs, add features in your repos
  • Search via SearxNG and scrape pages as needed
  • Run diagnostics and automate maintenance tasks

{Colors.BOLD}Session Commands:{Colors.RESET}
  {Colors.CYAN}/help{Colors.RESET}           Show this help
  {Colors.CYAN}/status{Colors.RESET}         Show current status
  {Colors.CYAN}/tier <name>{Colors.RESET}    Switch model tier
  {Colors.CYAN}/experience{Colors.RESET}     Show learning stats
  {Colors.CYAN}/clear{Colors.RESET}          Clear conversation history
  {Colors.CYAN}/save{Colors.RESET}           Save conversation
  {Colors.CYAN}/quit{Colors.RESET}           Exit session

{Colors.BOLD}Model Tiers:{Colors.RESET}
  {Colors.GREEN}fast{Colors.RESET}            Chat & simple tasks (mistral:7b)
  {Colors.CYAN}balanced{Colors.RESET}        Default for coding (qwen2.5-coder:14b)
  {Colors.YELLOW}powerful{Colors.RESET}        Heavy reasoning (deepseek-coder-v2:16b)
  {Colors.MAGENTA}ultra{Colors.RESET}           Big refactors (Qwen3-Coder:30B)
  {Colors.RED}uncensored{Colors.RESET}      Personal chat (gpt-oss:20b)

{Colors.BOLD}Example Tasks:{Colors.RESET}
  {Colors.DIM}"Design a new power menu with options X, Y, Z"{Colors.RESET}
  {Colors.DIM}"Create a theme switcher for my wallpapers"{Colors.RESET}
  {Colors.DIM}"Refactor this module to use async"{Colors.RESET}
  {Colors.DIM}"Research best Hyprland plugins and summarize"{Colors.RESET}
  {Colors.DIM}"Set up recurring maintenance for my configs"{Colors.RESET}

{Colors.DIM}Just tell me what you need - I'll plan and execute autonomously.{Colors.RESET}
"""
        print(help_text)
    
    def print_model_status(self, status: Dict):
        """Print model/router status"""
        print(f"\n{Colors.BRIGHT_PURPLE}Model Status:{Colors.RESET}")
        print(f"  Current tier: {Colors.CYAN}{status.get('current_tier', 'balanced')}{Colors.RESET}")
        
        if status.get('user_override'):
            print(f"  Override: {Colors.YELLOW}{status['user_override']}{Colors.RESET}")
        
        print(f"\n{Colors.BOLD}Available Models:{Colors.RESET}")
        for model in status.get('available_models', [])[:10]:
            print(f"  • {model}")
        
        print(f"\n{Colors.BOLD}Tier Status:{Colors.RESET}")
        for tier_name, tier_info in status.get('tiers', {}).items():
            available = tier_info.get('available', False)
            icon = Icons.DONE if available else Icons.ERROR
            model = tier_info.get('model', 'unknown')
            print(f"  {icon} {tier_name}: {model}")
    
    def print_cached(self):
        """Print cached response indicator"""
        print(f"{Colors.DIM}[cached]{Colors.RESET} ", end="")
        sys.stdout.flush()
    
    def format_code_block(self, code: str, language: str = "bash") -> str:
        """Format code for display"""
        lines = code.strip().split('\n')
        formatted = []
        formatted.append(f"{Colors.DIM}```{language}{Colors.RESET}")
        for line in lines:
            formatted.append(f"  {Colors.CYAN}{line}{Colors.RESET}")
        formatted.append(f"{Colors.DIM}```{Colors.RESET}")
        return '\n'.join(formatted)
    
    def format_response(self, response: str) -> str:
        """Format AI response for display"""
        # Handle code blocks
        def replace_code_block(match):
            lang = match.group(1) or 'bash'
            code = match.group(2)
            return self.format_code_block(code, lang)
        
        # Replace markdown code blocks
        formatted = re.sub(
            r'```(\w*)\n(.*?)```',
            replace_code_block,
            response,
            flags=re.DOTALL
        )
        
        # Handle bold text
        formatted = re.sub(
            r'\*\*(.*?)\*\*',
            f'{Colors.BOLD}\\1{Colors.RESET}',
            formatted
        )
        
        return formatted
    
    def confirm(self, message: str) -> bool:
        """Ask for user confirmation"""
        print(f"{Icons.QUESTION} {Colors.YELLOW}{message}{Colors.RESET} [y/N]: ", end="")
        response = input().strip().lower()
        return response in ['y', 'yes']
    
    def print_uncensored_warning(self):
        """Print uncensored mode warning"""
        print(f"\n{Colors.YELLOW}⚠️  Using uncensored model. Responses may not be filtered.{Colors.RESET}\n")


# Global UI instance
_ui = None

def get_ui() -> RyxUI:
    """Get the global UI instance"""
    global _ui
    if _ui is None:
        _ui = RyxUI()
    return _ui
