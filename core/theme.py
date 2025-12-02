"""
Ryx AI - Theme System
Modern, minimal terminal UI with Dracula-inspired colors

Themes:
- dracula: Dark purple/pink aesthetic (default)
- nord: Cool blue-gray tones  
- catppuccin: Soft pastel colors
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
import json
from pathlib import Path


@dataclass
class ThemeColors:
    """Color palette for a theme"""
    # Background tones (used conceptually - actual bg is terminal)
    bg_dark: str = "#1e1e2e"
    bg_light: str = "#313244"
    
    # Foreground
    fg: str = "#cdd6f4"
    fg_dim: str = "#6c7086"
    
    # Accents
    primary: str = "#bd93f9"     # Main accent (purple)
    secondary: str = "#ff79c6"   # Secondary (pink)
    
    # Status colors
    success: str = "#50fa7b"
    error: str = "#ff5555"
    warning: str = "#f1fa8c"
    info: str = "#8be9fd"
    
    # Special
    highlight: str = "#44475a"
    border: str = "#6272a4"


# ANSI escape codes for terminal colors
class ANSI:
    """ANSI escape codes"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    
    # Basic colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # 256 color (for more precise colors)
    @staticmethod
    def fg_256(n: int) -> str:
        return f"\033[38;5;{n}m"
    
    @staticmethod
    def bg_256(n: int) -> str:
        return f"\033[48;5;{n}m"
    
    # True color (24-bit)
    @staticmethod
    def fg_rgb(r: int, g: int, b: int) -> str:
        return f"\033[38;2;{r};{g};{b}m"
    
    @staticmethod
    def bg_rgb(r: int, g: int, b: int) -> str:
        return f"\033[48;2;{r};{g};{b}m"
    
    @staticmethod
    def hex_to_rgb(hex_color: str) -> tuple:
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def fg_hex(hex_color: str) -> str:
        """Get ANSI escape for hex color"""
        r, g, b = ANSI.hex_to_rgb(hex_color)
        return ANSI.fg_rgb(r, g, b)
    
    @staticmethod
    def bg_hex(hex_color: str) -> str:
        """Get ANSI escape for hex background"""
        r, g, b = ANSI.hex_to_rgb(hex_color)
        return ANSI.bg_rgb(r, g, b)


# Pre-defined themes
THEMES = {
    "dracula": ThemeColors(
        bg_dark="#1e1e2e",
        bg_light="#313244",
        fg="#f8f8f2",
        fg_dim="#6272a4",
        primary="#bd93f9",
        secondary="#ff79c6",
        success="#50fa7b",
        error="#ff5555",
        warning="#f1fa8c",
        info="#8be9fd",
        highlight="#44475a",
        border="#6272a4",
    ),
    "nord": ThemeColors(
        bg_dark="#2e3440",
        bg_light="#3b4252",
        fg="#eceff4",
        fg_dim="#4c566a",
        primary="#88c0d0",
        secondary="#81a1c1",
        success="#a3be8c",
        error="#bf616a",
        warning="#ebcb8b",
        info="#5e81ac",
        highlight="#434c5e",
        border="#4c566a",
    ),
    "catppuccin": ThemeColors(
        bg_dark="#1e1e2e",
        bg_light="#313244",
        fg="#cdd6f4",
        fg_dim="#6c7086",
        primary="#cba6f7",
        secondary="#f5c2e7",
        success="#a6e3a1",
        error="#f38ba8",
        warning="#f9e2af",
        info="#89dceb",
        highlight="#45475a",
        border="#585b70",
    ),
}


@dataclass
class Theme:
    """Complete theme with colors and icons"""
    name: str
    colors: ThemeColors
    
    # Unicode icons
    icons: Dict[str, str] = field(default_factory=lambda: {
        "success": "●",
        "error": "●",
        "warning": "●",
        "info": "●",
        "running": "◐",
        "pending": "○",
        "ryx": "🟣",
        "user": "›",
        "arrow": "▸",
        "check": "✓",
        "cross": "✗",
        "dot": "·",
        "line_h": "─",
        "line_v": "│",
        "corner_tl": "╭",
        "corner_tr": "╮",
        "corner_bl": "╰",
        "corner_br": "╯",
        "tee_l": "├",
        "tee_r": "┤",
    })
    
    def primary(self, text: str) -> str:
        """Wrap text in primary color"""
        return f"{ANSI.fg_hex(self.colors.primary)}{text}{ANSI.RESET}"
    
    def secondary(self, text: str) -> str:
        """Wrap text in secondary color"""
        return f"{ANSI.fg_hex(self.colors.secondary)}{text}{ANSI.RESET}"
    
    def success(self, text: str) -> str:
        """Wrap text in success color"""
        return f"{ANSI.fg_hex(self.colors.success)}{text}{ANSI.RESET}"
    
    def error(self, text: str) -> str:
        """Wrap text in error color"""
        return f"{ANSI.fg_hex(self.colors.error)}{text}{ANSI.RESET}"
    
    def warning(self, text: str) -> str:
        """Wrap text in warning color"""
        return f"{ANSI.fg_hex(self.colors.warning)}{text}{ANSI.RESET}"
    
    def info(self, text: str) -> str:
        """Wrap text in info color"""
        return f"{ANSI.fg_hex(self.colors.info)}{text}{ANSI.RESET}"
    
    def dim(self, text: str) -> str:
        """Wrap text in dim color"""
        return f"{ANSI.fg_hex(self.colors.fg_dim)}{text}{ANSI.RESET}"
    
    def bold(self, text: str) -> str:
        """Wrap text in bold"""
        return f"{ANSI.BOLD}{text}{ANSI.RESET}"
    
    def border(self, text: str) -> str:
        """Wrap text in border color"""
        return f"{ANSI.fg_hex(self.colors.border)}{text}{ANSI.RESET}"


class ThemeManager:
    """Manages theme selection and persistence"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path
        self._current_theme_name = "dracula"
        self._current_theme: Optional[Theme] = None
        self._load_preference()
    
    def _load_preference(self):
        """Load saved theme preference"""
        if self.config_path and self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    data = json.load(f)
                    self._current_theme_name = data.get("theme", "dracula")
            except Exception:
                pass
    
    def _save_preference(self):
        """Save theme preference"""
        if self.config_path:
            try:
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                data = {}
                if self.config_path.exists():
                    with open(self.config_path) as f:
                        data = json.load(f)
                data["theme"] = self._current_theme_name
                with open(self.config_path, 'w') as f:
                    json.dump(data, f, indent=2)
            except Exception:
                pass
    
    @property
    def theme(self) -> Theme:
        """Get current theme"""
        if self._current_theme is None or self._current_theme.name != self._current_theme_name:
            colors = THEMES.get(self._current_theme_name, THEMES["dracula"])
            self._current_theme = Theme(name=self._current_theme_name, colors=colors)
        return self._current_theme
    
    def set_theme(self, name: str) -> bool:
        """Set current theme"""
        if name in THEMES:
            self._current_theme_name = name
            self._current_theme = None
            self._save_preference()
            return True
        return False
    
    def list_themes(self) -> list:
        """List available themes"""
        return list(THEMES.keys())
    
    @property
    def current_theme_name(self) -> str:
        return self._current_theme_name


# Global theme manager instance
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager(config_path: Optional[Path] = None) -> ThemeManager:
    """Get or create theme manager singleton"""
    global _theme_manager
    if _theme_manager is None:
        if config_path is None:
            from core.paths import get_data_dir
            config_path = get_data_dir() / "theme_prefs.json"
        _theme_manager = ThemeManager(config_path)
    return _theme_manager


def get_theme() -> Theme:
    """Get current theme"""
    return get_theme_manager().theme
