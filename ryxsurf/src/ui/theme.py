"""
RyxSurf Theme System - Minimal, Subtle, Calm Design

Provides beautiful glassmorphism UI with subtle symbols and calm colors.
Preferences: symbols over emojis, subtle over colorful, calm over chaotic, minimal over cluttered.
"""

# Color Palette - Calm & Subtle
COLORS = {
    # Base colors (dark theme)
    "bg_primary": "rgba(18, 18, 20, 1.0)",        # Deep dark background
    "bg_secondary": "rgba(25, 25, 28, 1.0)",      # Slightly lighter
    "bg_tertiary": "rgba(32, 32, 36, 1.0)",       # Cards/panels
    
    # Glassmorphism
    "glass_light": "rgba(255, 255, 255, 0.02)",   # Very subtle glass
    "glass_medium": "rgba(255, 255, 255, 0.04)",  # Medium glass
    "glass_heavy": "rgba(255, 255, 255, 0.06)",   # Heavier glass
    
    # Borders
    "border_subtle": "rgba(255, 255, 255, 0.06)", # Barely visible
    "border_normal": "rgba(255, 255, 255, 0.10)", # Normal visibility
    "border_accent": "rgba(255, 255, 255, 0.15)", # Emphasized
    
    # Text
    "text_primary": "rgba(240, 240, 245, 1.0)",   # Main text
    "text_secondary": "rgba(160, 160, 170, 1.0)", # Dimmed text
    "text_tertiary": "rgba(100, 100, 110, 1.0)",  # Very dim
    
    # Accents - Calm blue-gray
    "accent_primary": "rgba(120, 140, 180, 1.0)", # Subtle blue
    "accent_hover": "rgba(140, 160, 200, 1.0)",   # Slightly brighter
    "accent_active": "rgba(160, 180, 220, 1.0)",  # Active state
    
    # Status colors (muted)
    "success": "rgba(120, 180, 140, 0.8)",        # Muted green
    "warning": "rgba(200, 160, 100, 0.8)",        # Muted orange
    "error": "rgba(200, 120, 120, 0.8)",          # Muted red
    "info": "rgba(120, 160, 200, 0.8)",           # Muted blue
}

# Symbols (no emojis)
SYMBOLS = {
    # Navigation
    "back": "‹",
    "forward": "›",
    "reload": "↻",
    "home": "⌂",
    "up": "↑",
    "down": "↓",
    
    # Actions
    "add": "+",
    "remove": "−",
    "close": "×",
    "minimize": "_",
    "maximize": "□",
    "search": "⌕",
    "settings": "⚙",
    "menu": "≡",
    
    # Status
    "check": "✓",
    "error": "⚠",
    "info": "ⓘ",
    "loading": "⋯",
    
    # Media
    "play": "▸",
    "pause": "‖",
    "stop": "■",
    "volume": "♪",
    "mute": "🔇",
    
    # Files
    "file": "📄",
    "folder": "📁",
    "download": "⬇",
    "upload": "⬆",
    
    # Security
    "shield": "⛨",
    "lock": "🔒",
    "unlock": "🔓",
    "key": "🔑",
    
    # Network
    "globe": "🌐",
    "wifi": "📶",
    "offline": "⚠",
    
    # Misc
    "star": "★",
    "star_empty": "☆",
    "bookmark": "🔖",
    "history": "⟲",
    "clock": "🕐",
    "calendar": "📅",
    "tag": "🏷",
    "pin": "📌",
}

# Typography
FONTS = {
    "sans": "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    "mono": "'JetBrains Mono', 'Fira Code', Consolas, monospace",
    "display": "'Inter Display', Inter, sans-serif",
}

FONT_SIZES = {
    "xs": 11,
    "sm": 12,
    "base": 14,
    "lg": 16,
    "xl": 18,
    "2xl": 24,
    "3xl": 32,
    "4xl": 48,
}

# Spacing (8px base unit)
SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 16,
    "lg": 24,
    "xl": 32,
    "2xl": 48,
}

# Border radius
RADIUS = {
    "sm": 4,
    "md": 8,
    "lg": 12,
    "xl": 16,
    "full": 9999,
}

# Shadows (subtle)
SHADOWS = {
    "sm": "0 1px 2px rgba(0, 0, 0, 0.1)",
    "md": "0 2px 4px rgba(0, 0, 0, 0.15)",
    "lg": "0 4px 8px rgba(0, 0, 0, 0.2)",
    "xl": "0 8px 16px rgba(0, 0, 0, 0.25)",
}

# Animation durations (ms)
DURATIONS = {
    "fast": 150,
    "normal": 250,
    "slow": 400,
}

# GTK CSS Theme
GTK_CSS = f"""
/* Global reset */
* {{
    font-family: {FONTS['sans']};
    color: {COLORS['text_primary']};
}}

/* Window background */
window {{
    background-color: {COLORS['bg_primary']};
}}

/* Glassmorphic panels */
.glass-panel {{
    background-color: {COLORS['glass_medium']};
    border: 1px solid {COLORS['border_subtle']};
    border-radius: {RADIUS['lg']}px;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
}}

/* URL bar */
entry {{
    background-color: {COLORS['glass_light']};
    border: 1px solid {COLORS['border_normal']};
    border-radius: {RADIUS['md']}px;
    padding: {SPACING['sm']}px {SPACING['md']}px;
    font-size: {FONT_SIZES['base']}px;
    color: {COLORS['text_primary']};
    min-height: 36px;
}}

entry:focus {{
    border-color: {COLORS['accent_primary']};
    background-color: {COLORS['glass_medium']};
    box-shadow: 0 0 0 2px {COLORS['accent_primary']}33;
}}

/* Buttons - minimal */
button {{
    background-color: transparent;
    border: 1px solid {COLORS['border_subtle']};
    border-radius: {RADIUS['md']}px;
    padding: {SPACING['sm']}px {SPACING['md']}px;
    font-size: {FONT_SIZES['sm']}px;
    min-height: 32px;
    transition: all {DURATIONS['fast']}ms ease;
}}

button:hover {{
    background-color: {COLORS['glass_light']};
    border-color: {COLORS['border_normal']};
}}

button:active {{
    background-color: {COLORS['glass_medium']};
    transform: scale(0.98);
}}

button.flat {{
    border: none;
    background: none;
}}

button.flat:hover {{
    background-color: {COLORS['glass_light']};
}}

/* Tab button */
button.tab {{
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    padding: {SPACING['sm']}px {SPACING['md']}px;
    background: none;
}}

button.tab:hover {{
    background-color: {COLORS['glass_light']};
    border-bottom-color: {COLORS['border_normal']};
}}

button.tab.active {{
    background-color: {COLORS['glass_medium']};
    border-bottom-color: {COLORS['accent_primary']};
}}

/* Scrollbar - minimal */
scrollbar {{
    background: transparent;
}}

scrollbar slider {{
    background-color: {COLORS['border_normal']};
    border-radius: {RADIUS['full']}px;
    min-width: 6px;
    min-height: 6px;
}}

scrollbar slider:hover {{
    background-color: {COLORS['border_accent']};
}}

/* Progress bar */
progressbar {{
    background-color: {COLORS['glass_light']};
    border-radius: {RADIUS['full']}px;
}}

progressbar progress {{
    background-color: {COLORS['accent_primary']};
    border-radius: {RADIUS['full']}px;
}}

/* Tooltips */
tooltip {{
    background-color: {COLORS['bg_tertiary']};
    border: 1px solid {COLORS['border_normal']};
    border-radius: {RADIUS['sm']}px;
    padding: {SPACING['xs']}px {SPACING['sm']}px;
    font-size: {FONT_SIZES['xs']}px;
}}

/* Menu */
menu {{
    background-color: {COLORS['bg_secondary']};
    border: 1px solid {COLORS['border_normal']};
    border-radius: {RADIUS['md']}px;
    padding: {SPACING['xs']}px;
}}

menuitem {{
    border-radius: {RADIUS['sm']}px;
    padding: {SPACING['sm']}px {SPACING['md']}px;
}}

menuitem:hover {{
    background-color: {COLORS['glass_medium']};
}}

/* Sidebar */
.sidebar {{
    background-color: {COLORS['bg_secondary']};
    border-right: 1px solid {COLORS['border_subtle']};
    min-width: 200px;
}}

/* Stats card */
.stat-card {{
    background-color: {COLORS['glass_light']};
    border: 1px solid {COLORS['border_subtle']};
    border-radius: {RADIUS['lg']}px;
    padding: {SPACING['lg']}px;
    transition: all {DURATIONS['normal']}ms ease;
}}

.stat-card:hover {{
    background-color: {COLORS['glass_medium']};
    border-color: {COLORS['border_normal']};
    transform: translateY(-2px);
}}

/* Labels */
.dim-label {{
    color: {COLORS['text_secondary']};
    font-size: {FONT_SIZES['sm']}px;
}}

.title {{
    font-size: {FONT_SIZES['2xl']}px;
    font-weight: 600;
    color: {COLORS['text_primary']};
}}

.subtitle {{
    font-size: {FONT_SIZES['lg']}px;
    font-weight: 500;
    color: {COLORS['text_secondary']};
}}

/* Status indicators */
.status-success {{
    color: {COLORS['success']};
}}

.status-warning {{
    color: {COLORS['warning']};
}}

.status-error {{
    color: {COLORS['error']};
}}

.status-info {{
    color: {COLORS['info']};
}}

/* Spinner - minimal */
spinner {{
    color: {COLORS['accent_primary']};
    opacity: 0.8;
}}

/* Selection */
selection {{
    background-color: {COLORS['accent_primary']}44;
}}

/* Focus ring - subtle */
*:focus {{
    outline: none;
    box-shadow: 0 0 0 2px {COLORS['accent_primary']}33;
}}
"""

def apply_theme(widget):
    """Apply theme to a GTK widget"""
    from gi.repository import Gtk
    
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(GTK_CSS.encode())
    
    style_context = widget.get_style_context()
    style_context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    
    # Also apply to all children
    if hasattr(widget, 'get_children'):
        for child in widget.get_children():
            apply_theme(child)
