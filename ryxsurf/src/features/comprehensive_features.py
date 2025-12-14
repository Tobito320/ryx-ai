"""
Comprehensive Browser Features
Includes all features from Zen Browser, Chrome, Firefox, and Opera GX.

Design philosophy: Symbols over emojis, subtle over colorful, minimal over cluttered
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from enum import Enum
import json
import logging

log = logging.getLogger("ryxsurf.features")


# ============================================================================
# PRIVACY & SECURITY FEATURES
# ============================================================================

class TrackingProtectionLevel(Enum):
    """Tracking protection levels"""
    OFF = "off"
    STANDARD = "standard"  # Blocks known trackers
    STRICT = "strict"      # Blocks all third-party trackers
    CUSTOM = "custom"      # User-defined rules


@dataclass
class PrivacySettings:
    """Privacy and security settings"""
    # Tracking Protection
    tracking_protection: TrackingProtectionLevel = TrackingProtectionLevel.STANDARD
    block_cookies: str = "third-party"  # all, third-party, none
    block_fingerprinting: bool = True
    block_cryptominers: bool = True
    
    # HTTPS
    https_only_mode: bool = True
    upgrade_mixed_content: bool = True
    
    # DNS
    enable_dns_over_https: bool = True
    dns_provider: str = "cloudflare"  # cloudflare, google, custom
    
    # Privacy
    send_do_not_track: bool = True
    send_referrer: str = "same-origin"  # always, same-origin, never
    clear_on_exit: List[str] = field(default_factory=lambda: [])  # cookies, cache, history, etc
    
    # Permissions
    location_permission: str = "ask"  # allow, ask, deny
    camera_permission: str = "ask"
    microphone_permission: str = "ask"
    notification_permission: str = "deny"
    autoplay_permission: str = "block"  # allow, block-audio, block
    
    # Container Tabs
    enable_containers: bool = True
    container_isolation: bool = True  # Isolate cookies/storage per container


# ============================================================================
# APPEARANCE & THEMING
# ============================================================================

class Theme(Enum):
    """UI themes"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"  # Follow system
    CUSTOM = "custom"


@dataclass
class AppearanceSettings:
    """Appearance and UI settings"""
    # Theme
    theme: Theme = Theme.DARK
    accent_color: str = "#5294E2"  # Subtle blue
    
    # Toolbar
    toolbar_style: str = "minimal"  # minimal, compact, normal, spacious
    show_bookmarks_bar: bool = False
    show_sidebar: bool = True
    sidebar_position: str = "left"  # left, right
    sidebar_width: int = 15  # Percentage (10-20%)
    
    # Tabs
    tab_style: str = "compact"  # compact, normal, vertical
    tab_position: str = "top"  # top, bottom, side
    show_tab_icons: bool = True
    tab_width: str = "adaptive"  # fixed, adaptive, shrink
    
    # URL Bar
    url_bar_style: str = "minimal"  # minimal, normal, centered
    url_bar_suggestions: bool = True
    url_bar_autohide: bool = False
    
    # Fonts
    font_family: str = "system"  # system, serif, sans-serif, mono
    font_size: int = 14
    min_font_size: int = 9
    
    # Spacing
    compact_mode: bool = True  # Reduce padding/margins
    animations: bool = True
    smooth_scrolling: bool = True
    
    # Page Display
    reader_mode_auto: bool = False
    force_dark_mode: bool = False  # Force dark on all sites
    zoom_level: float = 1.0  # Default zoom (0.5 - 3.0)


# ============================================================================
# PERFORMANCE & OPTIMIZATION
# ============================================================================

@dataclass
class PerformanceSettings:
    """Performance optimization settings"""
    # Hardware Acceleration
    enable_gpu: bool = True
    enable_webgl: bool = True
    enable_webgpu: bool = True
    
    # Memory Management
    tab_hibernation: bool = True
    tab_hibernation_timeout: int = 300  # seconds (5 min)
    max_active_tabs: int = 10
    tab_discarding: bool = True  # Discard tabs under memory pressure
    
    # Cache
    disk_cache_size: int = 1024  # MB
    memory_cache_size: int = 256  # MB
    enable_cache_compression: bool = True
    
    # Network
    enable_http2: bool = True
    enable_http3: bool = True
    max_connections: int = 256
    enable_prefetch: bool = True
    enable_prerender: bool = False  # Resource intensive
    
    # Resources
    lazy_load_images: bool = True
    lazy_load_iframes: bool = True
    limit_background_tabs: bool = True  # Throttle background tab CPU/network
    
    # Startup
    restore_session: bool = True
    restore_tabs_on_demand: bool = True  # Don't load all tabs immediately
    preload_homepage: bool = False


# ============================================================================
# BROWSING BEHAVIOR
# ============================================================================

@dataclass
class BrowsingSettings:
    """Browsing behavior settings"""
    # Homepage & New Tab
    homepage: str = "http://localhost:8888"  # SearXNG
    new_tab_page: str = "search"  # blank, search, homepage, custom
    
    # Search
    default_search: str = "searxng"
    search_suggestions: bool = True
    search_in_urlbar: bool = True
    
    # Navigation
    enable_gestures: bool = True  # Swipe back/forward
    middle_click_action: str = "new-tab"  # new-tab, close-tab, paste-go
    ctrl_tab_behavior: str = "recent"  # recent, order
    
    # Downloads
    download_location: str = "~/Downloads"
    ask_download_location: bool = False
    auto_open_downloads: bool = False
    
    # Links
    open_links_in: str = "tab"  # tab, window, background-tab
    single_click_open: bool = False
    
    # History
    remember_history: bool = True
    remember_downloads: bool = True
    remember_search: bool = True
    history_retention_days: int = 90
    
    # Forms
    enable_autofill: bool = True
    autofill_addresses: bool = True
    autofill_passwords: bool = True
    autofill_credit_cards: bool = False


# ============================================================================
# ADVANCED FEATURES
# ============================================================================

@dataclass
class AdvancedFeatures:
    """Advanced browser features"""
    # Split View
    enable_split_view: bool = True
    split_orientation: str = "horizontal"  # horizontal, vertical, grid
    
    # Tab Groups
    enable_tab_groups: bool = True
    auto_group_by_domain: bool = False
    
    # Sessions
    enable_sessions: bool = True
    auto_save_sessions: bool = True
    session_names: List[str] = field(default_factory=lambda: ["work", "personal", "dev"])
    
    # Picture-in-Picture
    enable_pip: bool = True
    pip_position: str = "bottom-right"
    
    # Reader Mode
    enable_reader_mode: bool = True
    reader_font: str = "serif"
    reader_width: str = "normal"  # narrow, normal, wide
    reader_color_scheme: str = "auto"  # light, dark, sepia, auto
    
    # PDF Viewer
    enable_pdf_viewer: bool = True
    pdf_default_zoom: str = "fit-width"
    
    # Media
    enable_media_controls: bool = True
    enable_autoplay: bool = False
    enable_captions: bool = True
    
    # Developer Tools
    enable_devtools: bool = True
    devtools_theme: str = "dark"
    enable_remote_debugging: bool = False
    
    # AI Integration
    enable_ai: bool = True
    ai_provider: str = "local"  # local (ollama), openai, custom
    ai_model: str = "qwen2.5:1.5b"
    ai_features: List[str] = field(default_factory=lambda: [
        "summarize", "translate", "explain", "click", "fill-forms"
    ])


# ============================================================================
# EXPERIMENTAL FEATURES (Opera GX-style)
# ============================================================================

@dataclass
class ExperimentalFeatures:
    """Experimental and gaming-focused features"""
    # Resource Limiter (Opera GX)
    enable_resource_limiter: bool = False
    cpu_limit_percent: int = 100  # Max CPU usage
    ram_limit_mb: int = 4096  # Max RAM usage
    network_limit_mbps: int = 0  # 0 = unlimited
    
    # Gaming Features
    game_mode: bool = False  # Reduce resource usage when gaming
    force_gpu_rendering: bool = False
    
    # Music Player
    enable_music_player: bool = False  # Sidebar music player
    
    # Ad Blocker
    enable_ad_blocker: bool = False
    ad_blocker_lists: List[str] = field(default_factory=list)
    
    # VPN Integration
    enable_vpn: bool = False
    vpn_provider: str = "custom"
    
    # Web3
    enable_web3: bool = False
    web3_provider: str = "metamask"
    
    # Sidebar Apps
    sidebar_apps: List[str] = field(default_factory=lambda: [
        "bookmarks", "history", "downloads"
    ])


# ============================================================================
# KEYBOARD SHORTCUTS
# ============================================================================

@dataclass
class KeyboardShortcuts:
    """Keyboard shortcut configuration"""
    # Navigation
    back: str = "Alt+Left"
    forward: str = "Alt+Right"
    reload: str = "Ctrl+R"
    hard_reload: str = "Ctrl+Shift+R"
    home: str = "Alt+Home"
    
    # Tabs
    new_tab: str = "Ctrl+T"
    close_tab: str = "Ctrl+W"
    reopen_tab: str = "Ctrl+Shift+T"
    next_tab: str = "Ctrl+Tab"
    prev_tab: str = "Ctrl+Shift+Tab"
    tab_1: str = "Ctrl+1"
    tab_2: str = "Ctrl+2"
    tab_3: str = "Ctrl+3"
    tab_4: str = "Ctrl+4"
    tab_5: str = "Ctrl+5"
    tab_6: str = "Ctrl+6"
    tab_7: str = "Ctrl+7"
    tab_8: str = "Ctrl+8"
    last_tab: str = "Ctrl+9"
    
    # Windows
    new_window: str = "Ctrl+N"
    new_private_window: str = "Ctrl+Shift+P"
    close_window: str = "Ctrl+Shift+W"
    
    # Page
    find: str = "Ctrl+F"
    print: str = "Ctrl+P"
    save_page: str = "Ctrl+S"
    zoom_in: str = "Ctrl+Plus"
    zoom_out: str = "Ctrl+Minus"
    zoom_reset: str = "Ctrl+0"
    fullscreen: str = "F11"
    
    # Tools
    downloads: str = "Ctrl+J"
    history: str = "Ctrl+H"
    bookmarks: str = "Ctrl+Shift+O"
    settings: str = "Ctrl+Comma"
    devtools: str = "F12"
    
    # Bookmarks
    bookmark_page: str = "Ctrl+D"
    bookmark_all_tabs: str = "Ctrl+Shift+D"
    
    # URL Bar
    focus_url: str = "Ctrl+L"
    search: str = "Ctrl+K"
    
    # AI (Custom)
    ai_command: str = "Ctrl+Space"
    ai_summarize: str = "Ctrl+Shift+S"
    ai_explain: str = "Ctrl+Shift+E"
    
    # View
    toggle_sidebar: str = "Ctrl+B"
    toggle_bookmarks_bar: str = "Ctrl+Shift+B"
    reader_mode: str = "Ctrl+Alt+R"
    
    # Advanced
    split_view_horizontal: str = "Ctrl+Shift+H"
    split_view_vertical: str = "Ctrl+Shift+V"
    pip_toggle: str = "Ctrl+Shift+P"


# ============================================================================
# MASTER SETTINGS MANAGER
# ============================================================================

class ComprehensiveSettingsManager:
    """Manages all browser settings"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "comprehensive_settings.json"
        
        # Settings categories
        self.privacy = PrivacySettings()
        self.appearance = AppearanceSettings()
        self.performance = PerformanceSettings()
        self.browsing = BrowsingSettings()
        self.advanced = AdvancedFeatures()
        self.experimental = ExperimentalFeatures()
        self.shortcuts = KeyboardShortcuts()
        
        # Load saved settings
        self.load()
    
    def save(self):
        """Save all settings to file"""
        data = {
            "privacy": self._dataclass_to_dict(self.privacy),
            "appearance": self._dataclass_to_dict(self.appearance),
            "performance": self._dataclass_to_dict(self.performance),
            "browsing": self._dataclass_to_dict(self.browsing),
            "advanced": self._dataclass_to_dict(self.advanced),
            "experimental": self._dataclass_to_dict(self.experimental),
            "shortcuts": self._dataclass_to_dict(self.shortcuts),
        }
        
        try:
            self.config_file.write_text(json.dumps(data, indent=2))
            log.info(f"Settings saved to {self.config_file}")
        except Exception as e:
            log.error(f"Failed to save settings: {e}")
    
    def load(self):
        """Load settings from file"""
        if not self.config_file.exists():
            log.info("No settings file found, using defaults")
            return
        
        try:
            data = json.loads(self.config_file.read_text())
            
            # Load each category
            if "privacy" in data:
                self.privacy = self._dict_to_dataclass(PrivacySettings, data["privacy"])
            if "appearance" in data:
                self.appearance = self._dict_to_dataclass(AppearanceSettings, data["appearance"])
            if "performance" in data:
                self.performance = self._dict_to_dataclass(PerformanceSettings, data["performance"])
            if "browsing" in data:
                self.browsing = self._dict_to_dataclass(BrowsingSettings, data["browsing"])
            if "advanced" in data:
                self.advanced = self._dict_to_dataclass(AdvancedFeatures, data["advanced"])
            if "experimental" in data:
                self.experimental = self._dict_to_dataclass(ExperimentalFeatures, data["experimental"])
            if "shortcuts" in data:
                self.shortcuts = self._dict_to_dataclass(KeyboardShortcuts, data["shortcuts"])
            
            log.info(f"Settings loaded from {self.config_file}")
            
        except Exception as e:
            log.error(f"Failed to load settings: {e}")
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self.privacy = PrivacySettings()
        self.appearance = AppearanceSettings()
        self.performance = PerformanceSettings()
        self.browsing = BrowsingSettings()
        self.advanced = AdvancedFeatures()
        self.experimental = ExperimentalFeatures()
        self.shortcuts = KeyboardShortcuts()
        self.save()
        log.info("Settings reset to defaults")
    
    def _dataclass_to_dict(self, obj) -> dict:
        """Convert dataclass to dict"""
        result = {}
        for key, value in obj.__dict__.items():
            if isinstance(value, Enum):
                result[key] = value.value
            elif isinstance(value, (list, dict, str, int, float, bool, type(None))):
                result[key] = value
            else:
                result[key] = str(value)
        return result
    
    def _dict_to_dataclass(self, cls, data: dict):
        """Convert dict to dataclass"""
        # Get field types
        field_types = {f.name: f.type for f in cls.__dataclass_fields__.values()}
        
        # Convert values
        kwargs = {}
        for key, value in data.items():
            if key in field_types:
                field_type = field_types[key]
                
                # Handle Enum types
                if hasattr(field_type, '__bases__') and Enum in field_type.__bases__:
                    kwargs[key] = field_type(value)
                else:
                    kwargs[key] = value
        
        return cls(**kwargs)
    
    def export_settings(self, file_path: Path):
        """Export settings to file"""
        import shutil
        shutil.copy(self.config_file, file_path)
        log.info(f"Settings exported to {file_path}")
    
    def import_settings(self, file_path: Path):
        """Import settings from file"""
        import shutil
        shutil.copy(file_path, self.config_file)
        self.load()
        log.info(f"Settings imported from {file_path}")


# ============================================================================
# FEATURE FLAGS
# ============================================================================

class FeatureFlags:
    """Feature flags for A/B testing and gradual rollout"""
    
    def __init__(self):
        self.flags = {
            # Experimental features
            "experimental_gpu_renderer": False,
            "experimental_tab_groups_2": False,
            "experimental_ai_autofill": False,
            "experimental_web3": False,
            
            # Beta features
            "beta_resource_limiter": True,
            "beta_tab_hibernation": True,
            "beta_force_dark_mode": True,
            
            # Stable features (always on)
            "stable_split_view": True,
            "stable_reader_mode": True,
            "stable_sessions": True,
        }
    
    def is_enabled(self, flag: str) -> bool:
        """Check if feature flag is enabled"""
        return self.flags.get(flag, False)
    
    def enable(self, flag: str):
        """Enable a feature flag"""
        self.flags[flag] = True
        log.info(f"Feature flag enabled: {flag}")
    
    def disable(self, flag: str):
        """Disable a feature flag"""
        self.flags[flag] = False
        log.info(f"Feature flag disabled: {flag}")
