"""
RyxSurf Advanced Settings - Comprehensive browser settings
Includes all features from Chrome, Firefox, Zen Browser, and Opera GX
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from pathlib import Path
import json
from typing import Dict, Any, List, Callable

# Theme imports (with fallback)
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from ui.theme import COLORS, SYMBOLS, SPACING, RADIUS, FONT_SIZES
except ImportError:
    COLORS = {"accent_primary": "rgba(120,140,180,1.0)", "info": "rgba(120,160,200,0.8)", "success": "rgba(120,180,140,0.8)", "warning": "rgba(200,160,100,0.8)", "text_secondary": "gray", "bg_secondary": "rgba(25,25,28,1.0)", "border_subtle": "rgba(255,255,255,0.06)", "border_normal": "rgba(255,255,255,0.10)"}
    SYMBOLS = {"home": "⌂", "shield": "⛨", "file": "📄", "search": "⌕", "settings": "⚙", "lock": "🔒", "close": "×", "add": "+"}
    SPACING = {"xs": 4, "sm": 8, "md": 16, "lg": 24, "xl": 32}
    RADIUS = {"sm": 4, "md": 8, "lg": 12}
    FONT_SIZES = {"xs": 11, "sm": 12, "base": 14}

SETTINGS_FILE = Path.home() / ".config" / "ryxsurf" / "settings.json"

# Comprehensive settings structure
DEFAULT_SETTINGS = {
    # General
    "general": {
        "startup_page": "dashboard",  # dashboard, homepage, last_session, blank
        "homepage": "http://localhost:8888",
        "search_engine": "searxng",
        "downloads_path": str(Path.home() / "Downloads"),
        "ask_download_location": False,
        "restore_session": True,
        "continue_where_left_off": True,
        "show_home_button": False,
        "show_bookmarks_bar": True,
    },
    
    # Appearance (Zen Browser style)
    "appearance": {
        "theme": "dark",  # dark, light, auto
        "accent_color": COLORS["accent_primary"],
        "sidebar_position": "left",  # left, right
        "sidebar_width": 15,  # percentage
        "sidebar_style": "compact",  # compact, normal, wide
        "tab_style": "rounded",  # rounded, squared, minimal
        "tab_width": "auto",  # auto, fixed, compact
        "show_tab_icons": True,
        "show_tab_close_buttons": True,
        "animate_tabs": True,
        "glassmorphism": True,
        "transparency": 0.95,
        "blur_strength": 10,
        "font_family": "Inter",
        "font_size": 14,
        "ui_density": "comfortable",  # compact, comfortable, spacious
        "toolbar_style": "minimal",
        "show_status_bar": False,
    },
    
    # Privacy & Security (Firefox inspired)
    "privacy": {
        "tracking_protection": "strict",  # off, standard, strict
        "block_ads": True,
        "block_trackers": True,
        "block_cryptominers": True,
        "block_fingerprinting": True,
        "block_cookies": "third_party",  # all, third_party, none
        "do_not_track": True,
        "https_only": True,
        "send_referrer": False,
        "clear_on_exit": {
            "history": False,
            "cookies": False,
            "cache": True,
            "downloads": False,
            "form_data": False,
            "passwords": False,
        },
        "enable_private_browsing_shortcuts": True,
    },
    
    # Performance (Opera GX inspired)
    "performance": {
        "hardware_acceleration": True,
        "use_gpu": True,
        "gpu_max_usage": 90,  # percentage
        "ram_limiter": False,
        "ram_limit_mb": 4096,
        "cpu_limiter": False,
        "cpu_limit_percent": 50,
        "network_limiter": False,
        "network_limit_mbps": 10,
        "lazy_load_tabs": True,
        "tab_unload_timeout": 300,  # seconds
        "max_loaded_tabs": 10,
        "preload_pages": True,
        "smooth_scrolling": True,
        "use_autoscroll": True,
        "enable_animations": True,
    },
    
    # Content Settings (Chrome style)
    "content": {
        "javascript": True,
        "images": True,
        "popups": "block",  # block, allow, ask
        "notifications": "ask",  # block, allow, ask
        "location": "ask",
        "camera": "ask",
        "microphone": "ask",
        "midi_devices": "ask",
        "usb_devices": "ask",
        "clipboard": "ask",
        "payment_handlers": "ask",
        "background_sync": True,
        "auto_downloads": "ask",
        "unsandboxed_plugins": "block",
        "protected_content": True,
        "font_size_standard": 16,
        "font_size_minimum": 10,
        "default_zoom": 100,
        "page_zoom": 100,
    },
    
    # Search Engines
    "search_engines": {
        "default": "searxng",
        "engines": {
            "searxng": {
                "name": "SearXNG",
                "url": "http://localhost:8888/search?q=%s",
                "suggest_url": "http://localhost:8888/autocomplete?q=%s",
                "icon": SYMBOLS["search"],
            },
            "google": {
                "name": "Google",
                "url": "https://www.google.com/search?q=%s",
                "suggest_url": "https://www.google.com/complete/search?q=%s",
                "icon": "G",
            },
            "duckduckgo": {
                "name": "DuckDuckGo",
                "url": "https://duckduckgo.com/?q=%s",
                "suggest_url": "https://ac.duckduckgo.com/ac/?q=%s",
                "icon": "D",
            },
            "brave": {
                "name": "Brave",
                "url": "https://search.brave.com/search?q=%s",
                "suggest_url": "https://search.brave.com/api/suggest?q=%s",
                "icon": "B",
            },
        },
        "keyword_shortcuts": {
            "g": "google",
            "d": "duckduckgo",
            "b": "brave",
            "s": "searxng",
            "yt": "https://youtube.com/results?search_query=%s",
            "gh": "https://github.com/search?q=%s",
            "w": "https://en.wikipedia.org/wiki/%s",
            "r": "https://reddit.com/search?q=%s",
        },
    },
    
    # Downloads
    "downloads": {
        "location": str(Path.home() / "Downloads"),
        "ask_location": False,
        "show_download_prompt": True,
        "open_when_done": False,
        "auto_open_types": [],
        "parallel_downloads": 3,
        "speed_limit": 0,  # 0 = unlimited
    },
    
    # Tabs & Windows
    "tabs": {
        "open_links_in_new_tab": True,
        "open_new_tab_next_to_current": True,
        "show_tab_preview": True,
        "show_tab_preview_delay": 500,  # ms
        "tab_groups_enabled": True,
        "vertical_tabs": False,
        "tab_bar_position": "top",  # top, bottom, left, right
        "tab_animation_speed": 250,  # ms
        "tab_scroll_behavior": "smooth",
        "middle_click_closes_tab": True,
        "ctrl_tab_cycles_recent": False,
        "warn_on_close_multiple": True,
        "reopen_closed_tab_button": True,
    },
    
    # Keybinds (Hyprland-style)
    "keybinds": {
        "navigation": {
            "scroll_down": "Super+j",
            "scroll_up": "Super+k",
            "back": "Super+h",
            "forward": "Super+l",
            "go_to_url": "Super+g",
            "search_in_page": "Super+slash",
            "hint_mode": "Super+f",
        },
        "tabs": {
            "new_tab": "Super+t",
            "close_tab": "Super+w",
            "switch_tab": "Super+1-9",
            "next_tab": "Super+Tab",
            "prev_tab": "Super+Shift+Tab",
            "reopen_closed": "Super+Shift+t",
            "duplicate_tab": "Super+Shift+d",
            "pin_tab": "Super+p",
        },
        "ui": {
            "toggle_sidebar": "Super+b",
            "toggle_bookmarks": "Super+Shift+b",
            "toggle_fullscreen": "Super+Escape",
            "toggle_developer_tools": "F12",
            "focus_url_bar": "Ctrl+l",
        },
        "ai": {
            "ai_command": "Super+a",
            "ai_summarize": "Super+Shift+a",
            "ai_dismiss_popup": "Super+x",
            "ai_reader_mode": "Super+r",
        },
        "quick": {
            "yank_url": "Super+y",
            "paste_and_go": "Super+Shift+v",
            "open_file": "Super+o",
            "downloads": "Super+d",
            "history": "Super+h",
            "bookmarks": "Super+Shift+o",
        },
    },
    
    # Extensions (WebExtensions API)
    "extensions": {
        "enabled": True,
        "allow_unsigned": False,
        "update_automatically": True,
        "installed": [],
    },
    
    # Developer Tools
    "developer": {
        "enable_devtools": True,
        "devtools_position": "bottom",  # bottom, right, window
        "enable_remote_debugging": False,
        "remote_debugging_port": 9222,
        "enable_source_maps": True,
        "console_clear_on_navigate": False,
        "network_throttling": "disabled",  # disabled, slow_3g, fast_3g
        "user_agent_override": "",
    },
    
    # Advanced
    "advanced": {
        "use_system_proxy": True,
        "proxy_type": "system",  # system, manual, auto, none
        "proxy_http": "",
        "proxy_https": "",
        "proxy_socks": "",
        "proxy_bypass": "localhost,127.0.0.1",
        "dns_over_https": True,
        "dns_provider": "cloudflare",  # cloudflare, google, quad9
        "enable_spell_check": True,
        "spell_check_languages": ["en-US"],
        "restore_zoom_levels": True,
        "media_autoplay": "allow",  # allow, block, ask
        "webrtc_ip_handling": "default",  # default, disable_non_proxy
        "referrer_policy": "strict-origin-when-cross-origin",
        "enable_webgl": True,
        "enable_webgl2": True,
        "enable_webaudio": True,
        "enable_webassembly": True,
        "memory_cache_size": 512,  # MB
        "disk_cache_size": 1024,  # MB
        "enable_experimental_features": False,
    },
    
    # Passwords & Autofill
    "passwords": {
        "save_passwords": True,
        "auto_signin": False,
        "suggest_strong_passwords": True,
        "show_passwords_on_sites": False,
        "alert_weak_passwords": True,
        "check_breached_passwords": True,
    },
    
    "autofill": {
        "addresses": True,
        "payment_methods": False,
        "phone_numbers": True,
        "emails": True,
    },
    
    # Sync (future feature)
    "sync": {
        "enabled": False,
        "sync_bookmarks": True,
        "sync_history": True,
        "sync_passwords": False,
        "sync_extensions": True,
        "sync_settings": True,
        "sync_open_tabs": True,
    },
    
    # AI Integration (Ryx-specific)
    "ai": {
        "enabled": True,
        "model": "qwen2.5:7b",
        "backend": "ollama",
        "ollama_url": "http://localhost:11434",
        "auto_summarize": False,
        "auto_dismiss_popups": True,
        "reader_mode_button": True,
        "context_menu_integration": True,
        "sidebar_chat": True,
    },
    
    # Workspace & Sessions (Zen Browser)
    "workspace": {
        "enable_workspaces": True,
        "workspaces": [
            {"name": "Personal", "icon": "⌂", "color": COLORS["accent_primary"]},
            {"name": "Work", "icon": "⚒", "color": COLORS["info"]},
            {"name": "School", "icon": "◆", "color": COLORS["success"]},
            {"name": "Chill", "icon": "♪", "color": COLORS["warning"]},
        ],
        "auto_switch_workspace": True,
        "workspace_tab_isolation": True,
    },
    
    # Gaming Mode (Opera GX)
    "gaming": {
        "gx_control_enabled": False,
        "force_dark_mode": True,
        "network_priority": False,
        "ram_priority": False,
        "sound_effects": False,
        "rgb_theme": False,
        "hot_tabs_killer": True,
    },
}


class AdvancedSettingsDialog(Gtk.Window):
    """Comprehensive settings dialog"""
    
    def __init__(self, parent=None):
        super().__init__(title="RyxSurf Settings")
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(900, 700)
        
        self.settings = self._load_settings()
        self.callbacks = {}  # Setting change callbacks
        
        self._build_ui()
        
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from disk"""
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE) as f:
                    loaded = json.load(f)
                    # Merge with defaults
                    return self._merge_settings(DEFAULT_SETTINGS, loaded)
            except Exception as e:
                print(f"Error loading settings: {e}")
        return DEFAULT_SETTINGS.copy()
    
    def _merge_settings(self, defaults: Dict, loaded: Dict) -> Dict:
        """Recursively merge loaded settings with defaults"""
        result = defaults.copy()
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_settings(result[key], value)
            else:
                result[key] = value
        return result
    
    def _save_settings(self):
        """Save settings to disk"""
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f, indent=2)
            print("Settings saved")
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def _build_ui(self):
        """Build settings UI"""
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add(main_box)
        
        # Sidebar with categories
        sidebar = self._create_sidebar()
        main_box.pack_start(sidebar, False, False, 0)
        
        # Content area
        self.content_stack = Gtk.Stack()
        self.content_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.content_stack.set_transition_duration(200)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.content_stack)
        
        main_box.pack_start(scroll, True, True, 0)
        
        # Add all setting pages
        self._add_setting_pages()
        
    def _create_sidebar(self) -> Gtk.Box:
        """Create sidebar with category list"""
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar.set_size_request(200, -1)
        sidebar.get_style_context().add_class("sidebar")
        
        categories = [
            ("general", SYMBOLS["home"], "General"),
            ("appearance", "◈", "Appearance"),
            ("privacy", SYMBOLS["shield"], "Privacy"),
            ("performance", "⚡", "Performance"),
            ("content", SYMBOLS["file"], "Content"),
            ("search_engines", SYMBOLS["search"], "Search"),
            ("downloads", "⬇", "Downloads"),
            ("tabs", "☰", "Tabs"),
            ("keybinds", "⌘", "Keybinds"),
            ("extensions", "⊞", "Extensions"),
            ("developer", "⚒", "Developer"),
            ("advanced", SYMBOLS["settings"], "Advanced"),
            ("passwords", SYMBOLS["lock"], "Passwords"),
            ("autofill", "✎", "Autofill"),
            ("sync", "⟲", "Sync"),
            ("ai", "◆", "AI"),
            ("workspace", "⚐", "Workspace"),
            ("gaming", "▸", "Gaming"),
        ]
        
        for key, symbol, label in categories:
            btn = self._create_category_button(key, symbol, label)
            sidebar.pack_start(btn, False, False, 0)
        
        return sidebar
    
    def _create_category_button(self, key: str, symbol: str, label: str) -> Gtk.Button:
        """Create a category button"""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_start(SPACING['sm'])
        box.set_margin_end(SPACING['sm'])
        box.set_margin_top(SPACING['xs'])
        box.set_margin_bottom(SPACING['xs'])
        
        # Symbol
        symbol_label = Gtk.Label()
        symbol_label.set_markup(f'<span size="large">{symbol}</span>')
        box.pack_start(symbol_label, False, False, 0)
        
        # Label
        text_label = Gtk.Label(label)
        text_label.set_halign(Gtk.Align.START)
        box.pack_start(text_label, True, True, 0)
        
        btn = Gtk.Button()
        btn.add(box)
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.connect("clicked", lambda w: self.content_stack.set_visible_child_name(key))
        
        return btn
    
    def _add_setting_pages(self):
        """Add all setting pages to stack"""
        # General
        self.content_stack.add_named(self._create_general_page(), "general")
        # Add more pages as needed
        
    def _create_general_page(self) -> Gtk.Box:
        """Create general settings page"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=SPACING['lg'])
        page.set_margin_start(SPACING['xl'])
        page.set_margin_end(SPACING['xl'])
        page.set_margin_top(SPACING['lg'])
        page.set_margin_bottom(SPACING['lg'])
        
        # Title
        title = Gtk.Label()
        title.set_markup('<span size="xx-large" weight="bold">General</span>')
        title.set_halign(Gtk.Align.START)
        page.pack_start(title, False, False, 0)
        
        # Settings
        page.pack_start(self._create_dropdown(
            "Startup page",
            "general.startup_page",
            ["dashboard", "homepage", "last_session", "blank"],
            ["Dashboard", "Homepage", "Last Session", "Blank Page"]
        ), False, False, 0)
        
        page.pack_start(self._create_entry(
            "Homepage",
            "general.homepage"
        ), False, False, 0)
        
        page.pack_start(self._create_dropdown(
            "Search engine",
            "general.search_engine",
            ["searxng", "google", "duckduckgo", "brave"],
            ["SearXNG", "Google", "DuckDuckGo", "Brave"]
        ), False, False, 0)
        
        page.pack_start(self._create_switch(
            "Restore session on startup",
            "general.restore_session"
        ), False, False, 0)
        
        page.pack_start(self._create_switch(
            "Show bookmarks bar",
            "general.show_bookmarks_bar"
        ), False, False, 0)
        
        return page
    
    def _create_switch(self, label: str, setting_path: str) -> Gtk.Box:
        """Create a boolean switch setting"""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=SPACING['md'])
        box.set_margin_top(SPACING['sm'])
        box.set_margin_bottom(SPACING['sm'])
        
        label_widget = Gtk.Label(label)
        label_widget.set_halign(Gtk.Align.START)
        box.pack_start(label_widget, True, True, 0)
        
        switch = Gtk.Switch()
        value = self._get_setting(setting_path)
        switch.set_active(value)
        switch.connect("notify::active", lambda w, p: self._set_setting(setting_path, w.get_active()))
        box.pack_start(switch, False, False, 0)
        
        return box
    
    def _create_entry(self, label: str, setting_path: str) -> Gtk.Box:
        """Create a text entry setting"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=SPACING['xs'])
        box.set_margin_top(SPACING['sm'])
        box.set_margin_bottom(SPACING['sm'])
        
        label_widget = Gtk.Label(label)
        label_widget.set_halign(Gtk.Align.START)
        box.pack_start(label_widget, False, False, 0)
        
        entry = Gtk.Entry()
        entry.set_text(str(self._get_setting(setting_path)))
        entry.connect("changed", lambda w: self._set_setting(setting_path, w.get_text()))
        box.pack_start(entry, False, False, 0)
        
        return box
    
    def _create_dropdown(self, label: str, setting_path: str, values: List[str], labels: List[str]) -> Gtk.Box:
        """Create a dropdown setting"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=SPACING['xs'])
        box.set_margin_top(SPACING['sm'])
        box.set_margin_bottom(SPACING['sm'])
        
        label_widget = Gtk.Label(label)
        label_widget.set_halign(Gtk.Align.START)
        box.pack_start(label_widget, False, False, 0)
        
        combo = Gtk.ComboBoxText()
        for value, label_text in zip(values, labels):
            combo.append(value, label_text)
        
        current = self._get_setting(setting_path)
        combo.set_active_id(current)
        combo.connect("changed", lambda w: self._set_setting(setting_path, w.get_active_id()))
        box.pack_start(combo, False, False, 0)
        
        return box
    
    def _get_setting(self, path: str) -> Any:
        """Get setting value by path (e.g., 'general.homepage')"""
        keys = path.split('.')
        value = self.settings
        for key in keys:
            value = value[key]
        return value
    
    def _set_setting(self, path: str, value: Any):
        """Set setting value by path"""
        keys = path.split('.')
        target = self.settings
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = value
        self._save_settings()
        
        # Call callback if registered
        if path in self.callbacks:
            self.callbacks[path](value)
    
    def register_callback(self, setting_path: str, callback: Callable[[Any], None]):
        """Register a callback for when a setting changes"""
        self.callbacks[setting_path] = callback
