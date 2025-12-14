"""
Comprehensive Settings Manager for RyxSurf

Aggregates features from:
- Zen Browser (split view, workspace management, compact mode)
- Chrome (sync, extensions, developer tools)
- Firefox (privacy, container tabs, custom CSS)
- Opera GX (RAM/CPU limiters, built-in VPN, force dark pages)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import logging

log = logging.getLogger("ryxsurf.settings")

SETTINGS_DIR = Path.home() / ".config" / "ryxsurf"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"


@dataclass
class AppearanceSettings:
    """Visual appearance settings"""
    # Theme
    theme: str = "dark"  # dark, light, auto
    color_scheme: str = "violet"  # violet, blue, green, orange, red, custom
    custom_accent_color: str = "#7c3aed"
    
    # Layout
    compact_mode: bool = False  # Zen Browser style
    sidebar_position: str = "left"  # left, right, floating
    sidebar_width_percent: int = 12  # 10-25%
    url_bar_position: str = "top"  # top, bottom, floating
    
    # Typography
    font_family: str = "system-ui"
    font_size: int = 14
    monospace_font: str = "monospace"
    
    # Visual effects
    glassmorphism: bool = True
    animations: bool = True
    blur_background: bool = True
    smooth_scrolling: bool = True
    
    # UI density
    tab_height: int = 36  # pixels
    url_bar_height: int = 36
    show_tab_icons: bool = True
    show_tab_close_button: str = "hover"  # always, hover, never
    
    # Status indicators
    show_loading_bar: bool = True
    show_https_indicator: bool = True
    show_tab_count: bool = True


@dataclass
class PrivacySettings:
    """Privacy & security settings"""
    # Tracking
    block_trackers: bool = True
    block_ads: bool = False  # Use uBlock Origin instead
    block_fingerprinting: bool = True
    block_cryptominers: bool = True
    
    # Cookies
    cookie_policy: str = "block_third_party"  # allow_all, block_third_party, block_all
    clear_cookies_on_exit: bool = False
    
    # History
    remember_history: bool = True
    remember_downloads: bool = True
    remember_search_form_history: bool = True
    clear_history_on_exit: bool = False
    history_expiration_days: int = 90
    
    # HTTPS
    https_only_mode: bool = True
    enable_dns_over_https: bool = True
    dns_provider: str = "cloudflare"  # cloudflare, quad9, custom
    
    # Permissions
    ask_for_location: bool = True
    ask_for_camera: bool = True
    ask_for_microphone: bool = True
    ask_for_notifications: bool = True
    ask_for_autoplay: bool = True
    
    # Firefox Container Tabs
    enable_containers: bool = False
    containers: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class PerformanceSettings:
    """Performance & resource management"""
    # Opera GX style limiters
    enable_ram_limiter: bool = False
    ram_limit_mb: int = 4096
    enable_cpu_limiter: bool = False
    cpu_limit_percent: int = 50
    
    # Tab management
    auto_unload_tabs: bool = True
    unload_after_minutes: int = 5
    max_loaded_tabs: int = 10
    suspend_background_tabs: bool = True
    
    # Hardware acceleration
    gpu_acceleration: bool = True
    enable_webgl: bool = True
    enable_webgl2: bool = True
    
    # Network
    enable_prefetch: bool = True
    enable_preconnect: bool = True
    enable_http3: bool = True
    
    # Cache
    cache_size_mb: int = 512
    clear_cache_on_exit: bool = False


@dataclass
class ContentSettings:
    """Content & media settings"""
    # Media
    autoplay_policy: str = "user_gesture"  # allow, user_gesture, block
    enable_drm: bool = True
    prefer_reduced_motion: bool = False
    
    # Images
    load_images: bool = True
    enable_webp: bool = True
    enable_avif: bool = True
    
    # JavaScript
    enable_javascript: bool = True
    enable_wasm: bool = True
    
    # Fonts
    allow_custom_fonts: bool = True
    minimum_font_size: int = 9
    
    # Language
    preferred_languages: List[str] = field(default_factory=lambda: ["en-US"])
    enable_translation: bool = False
    
    # Force dark mode (Opera GX)
    force_dark_mode: bool = False
    force_dark_exclude: List[str] = field(default_factory=list)


@dataclass
class SearchSettings:
    """Search & navigation settings"""
    # Default search
    default_engine: str = "searxng"
    searxng_url: str = "http://localhost:8888"
    
    # Search engines
    engines: Dict[str, str] = field(default_factory=lambda: {
        "g": "https://www.google.com/search?q={}",
        "d": "https://duckduckgo.com/?q={}",
        "b": "https://search.brave.com/search?q={}",
        "gh": "https://github.com/search?q={}",
        "yt": "https://www.youtube.com/results?search_query={}",
        "w": "https://en.wikipedia.org/wiki/{}",
    })
    
    # Suggestions
    show_search_suggestions: bool = True
    show_history_suggestions: bool = True
    show_bookmark_suggestions: bool = True
    max_suggestions: int = 8
    
    # Behavior
    search_on_type: bool = False
    open_links_in_new_tab: bool = False
    focus_search_on_new_tab: bool = True


@dataclass
class WorkspaceSettings:
    """Zen Browser style workspaces"""
    enable_workspaces: bool = True
    workspaces: List[Dict[str, Any]] = field(default_factory=lambda: [
        {"id": "default", "name": "Default", "icon": "○", "color": "#7c3aed"},
        {"id": "work", "name": "Work", "icon": "◆", "color": "#3b82f6"},
        {"id": "personal", "name": "Personal", "icon": "◇", "color": "#22c55e"},
    ])
    auto_switch_workspace: bool = False
    isolate_cookies_per_workspace: bool = False


@dataclass
class TabSettings:
    """Tab behavior settings"""
    # New tab
    new_tab_page: str = "homepage"  # homepage, blank, custom
    new_tab_custom_url: str = ""
    
    # Tab behavior
    open_new_tab_next_to_current: bool = True
    switch_to_new_tab: bool = True
    close_tab_selects: str = "next"  # next, previous, last_active
    confirm_close_multiple: bool = True
    confirm_close_multiple_threshold: int = 3
    
    # Tab groups (Chrome style)
    enable_tab_groups: bool = False
    auto_group_by_domain: bool = False
    
    # Tab pinning
    pinned_tabs_show_title: bool = False
    
    # Recently closed
    remember_closed_tabs: int = 25


@dataclass
class SessionSettings:
    """Session & startup settings"""
    # Startup
    restore_on_startup: str = "last_session"  # blank, homepage, last_session, urls
    startup_urls: List[str] = field(default_factory=list)
    
    # Session management
    auto_save_session: bool = True
    save_interval_seconds: int = 30
    enable_session_restore: bool = True
    
    # Crash recovery
    show_restore_prompt: bool = True


@dataclass
class DeveloperSettings:
    """Developer tools settings"""
    # DevTools
    enable_devtools: bool = True
    devtools_theme: str = "dark"
    devtools_position: str = "bottom"  # bottom, right, window
    
    # Debugging
    enable_remote_debugging: bool = False
    remote_debugging_port: int = 9222
    
    # Extensions
    enable_extensions: bool = True
    enable_userscripts: bool = True
    
    # Experimental
    enable_experimental_features: bool = False
    user_agent: str = "default"


@dataclass
class DownloadSettings:
    """Download management settings"""
    # Location
    download_dir: str = str(Path.home() / "Downloads")
    ask_download_location: bool = False
    
    # Behavior
    auto_open_downloads: bool = False
    show_download_notification: bool = True
    
    # Safety
    warn_dangerous_downloads: bool = True
    block_dangerous_downloads: bool = True


@dataclass
class SyncSettings:
    """Chrome-style sync settings (via RyxHub)"""
    enable_sync: bool = False
    sync_url: str = "http://localhost:8420"
    
    # What to sync
    sync_bookmarks: bool = True
    sync_history: bool = True
    sync_passwords: bool = False
    sync_tabs: bool = True
    sync_extensions: bool = False
    sync_settings: bool = True


@dataclass
class AccessibilitySettings:
    """Accessibility settings"""
    # Visual
    high_contrast: bool = False
    force_colors: bool = False
    
    # Text
    use_system_font_size: bool = False
    page_zoom: float = 1.0
    
    # Navigation
    caret_browsing: bool = False
    spatial_navigation: bool = False
    
    # Screen reader
    screen_reader_mode: bool = False


class SettingsManager:
    """Manages all browser settings"""
    
    def __init__(self):
        self.appearance = AppearanceSettings()
        self.privacy = PrivacySettings()
        self.performance = PerformanceSettings()
        self.content = ContentSettings()
        self.search = SearchSettings()
        self.workspace = WorkspaceSettings()
        self.tabs = TabSettings()
        self.session = SessionSettings()
        self.developer = DeveloperSettings()
        self.downloads = DownloadSettings()
        self.sync = SyncSettings()
        self.accessibility = AccessibilitySettings()
        
        self.load()
    
    def load(self):
        """Load settings from file"""
        if not SETTINGS_FILE.exists():
            log.info("No settings file found, using defaults")
            return
        
        try:
            data = json.loads(SETTINGS_FILE.read_text())
            
            # Load each category
            if "appearance" in data:
                self._load_category(self.appearance, data["appearance"])
            if "privacy" in data:
                self._load_category(self.privacy, data["privacy"])
            if "performance" in data:
                self._load_category(self.performance, data["performance"])
            if "content" in data:
                self._load_category(self.content, data["content"])
            if "search" in data:
                self._load_category(self.search, data["search"])
            if "workspace" in data:
                self._load_category(self.workspace, data["workspace"])
            if "tabs" in data:
                self._load_category(self.tabs, data["tabs"])
            if "session" in data:
                self._load_category(self.session, data["session"])
            if "developer" in data:
                self._load_category(self.developer, data["developer"])
            if "downloads" in data:
                self._load_category(self.downloads, data["downloads"])
            if "sync" in data:
                self._load_category(self.sync, data["sync"])
            if "accessibility" in data:
                self._load_category(self.accessibility, data["accessibility"])
                
            log.info("Settings loaded successfully")
        except Exception as e:
            log.error(f"Failed to load settings: {e}")
    
    def _load_category(self, category: Any, data: Dict[str, Any]):
        """Load settings for a category"""
        for key, value in data.items():
            if hasattr(category, key):
                setattr(category, key, value)
    
    def save(self):
        """Save settings to file"""
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        
        data = {
            "appearance": self._to_dict(self.appearance),
            "privacy": self._to_dict(self.privacy),
            "performance": self._to_dict(self.performance),
            "content": self._to_dict(self.content),
            "search": self._to_dict(self.search),
            "workspace": self._to_dict(self.workspace),
            "tabs": self._to_dict(self.tabs),
            "session": self._to_dict(self.session),
            "developer": self._to_dict(self.developer),
            "downloads": self._to_dict(self.downloads),
            "sync": self._to_dict(self.sync),
            "accessibility": self._to_dict(self.accessibility),
        }
        
        SETTINGS_FILE.write_text(json.dumps(data, indent=2))
        log.info("Settings saved")
    
    def _to_dict(self, obj: Any) -> Dict[str, Any]:
        """Convert dataclass to dict"""
        if hasattr(obj, "__dataclass_fields__"):
            return {
                k: getattr(obj, k)
                for k in obj.__dataclass_fields__.keys()
            }
        return {}
    
    def get(self, category: str, key: str = None, default: Any = None) -> Any:
        """Get a setting value - supports legacy single-arg calls"""
        # Legacy support: get("homepage") -> search.searxng_url
        if key is None:
            # Old format: self.settings.get("homepage")
            legacy_map = {
                "homepage": ("search", "searxng_url"),
                "search_engine": ("search", "default_engine"),
                "searxng_url": ("search", "searxng_url"),
                "dark_mode": ("appearance", "theme"),
                "gpu_acceleration": ("performance", "gpu_acceleration"),
                "tab_unload_timeout_seconds": ("performance", "unload_after_minutes"),
                "max_loaded_tabs": ("performance", "max_loaded_tabs"),
                "restore_session_on_startup": ("session", "restore_on_startup"),
            }
            
            if category in legacy_map:
                cat, key = legacy_map[category]
                cat_obj = getattr(self, cat, None)
                if cat_obj is None:
                    return default
                val = getattr(cat_obj, key, default)
                # Convert boolean values for legacy compatibility
                if category == "dark_mode" and val == "dark":
                    return True
                elif category == "dark_mode" and val != "dark":
                    return False
                return val
            return default
        
        # New format: self.settings.get("search", "default_engine")
        cat = getattr(self, category, None)
        if cat is None:
            return default
        return getattr(cat, key, default)
    
    def set(self, category: str, key: str, value: Any):
        """Set a setting value"""
        cat = getattr(self, category, None)
        if cat is not None:
            setattr(cat, key, value)
            self.save()
    
    def reset_category(self, category: str):
        """Reset a category to defaults"""
        if category == "appearance":
            self.appearance = AppearanceSettings()
        elif category == "privacy":
            self.privacy = PrivacySettings()
        elif category == "performance":
            self.performance = PerformanceSettings()
        elif category == "content":
            self.content = ContentSettings()
        elif category == "search":
            self.search = SearchSettings()
        elif category == "workspace":
            self.workspace = WorkspaceSettings()
        elif category == "tabs":
            self.tabs = TabSettings()
        elif category == "session":
            self.session = SessionSettings()
        elif category == "developer":
            self.developer = DeveloperSettings()
        elif category == "downloads":
            self.downloads = DownloadSettings()
        elif category == "sync":
            self.sync = SyncSettings()
        elif category == "accessibility":
            self.accessibility = AccessibilitySettings()
        
        self.save()
    
    def reset_all(self):
        """Reset all settings to defaults"""
        self.__init__()
        self.save()
    
    def export_settings(self, path: Path):
        """Export settings to a file"""
        data = {
            "appearance": self._to_dict(self.appearance),
            "privacy": self._to_dict(self.privacy),
            "performance": self._to_dict(self.performance),
            "content": self._to_dict(self.content),
            "search": self._to_dict(self.search),
            "workspace": self._to_dict(self.workspace),
            "tabs": self._to_dict(self.tabs),
            "session": self._to_dict(self.session),
            "developer": self._to_dict(self.developer),
            "downloads": self._to_dict(self.downloads),
            "sync": self._to_dict(self.sync),
            "accessibility": self._to_dict(self.accessibility),
        }
        path.write_text(json.dumps(data, indent=2))
    
    def import_settings(self, path: Path):
        """Import settings from a file"""
        data = json.loads(path.read_text())
        
        for category in ["appearance", "privacy", "performance", "content", 
                        "search", "workspace", "tabs", "session", "developer",
                        "downloads", "sync", "accessibility"]:
            if category in data:
                cat_obj = getattr(self, category)
                self._load_category(cat_obj, data[category])
        
        self.save()
