"""
RyxSurf Core - Browser Engine Integration

Uses WebKitGTK for rendering (same engine as GNOME Web/Epiphany).
Provides a minimal, keyboard-driven interface with modern glassmorphism UI.

Features:
- Tab management with count display, hover titles, middle-click close
- Session persistence with auto-save/restore
- Smart tab unloading for memory efficiency  
- History tracking with URL bar suggestions
- Download manager with progress tracking
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit', '6.0')

from gi.repository import Gtk, WebKit, GLib, Gdk, Pango
from typing import Optional, List, Callable, Dict
from ..ui.hints import HintMode
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote_plus
import json
import time
import logging
import sys

# Setup logging with immediate flush
LOG_FILE = Path.home() / ".config" / "ryxsurf" / "ryxsurf.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# File handler with immediate flush
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setLevel(logging.INFO)

# Stream handler with immediate flush  
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[file_handler, stream_handler],
    force=True
)
log = logging.getLogger("ryxsurf")
log.setLevel(logging.INFO)

from .history import HistoryManager
from .downloads import DownloadManager, DownloadNotification, DownloadInfo
from .bookmarks import BookmarkManager


# Settings file path
SETTINGS_FILE = Path.home() / ".config" / "ryxsurf" / "settings.json"

DEFAULT_SETTINGS = {
    "homepage": "https://www.google.com",
    "search_engine": "https://google.com/search?q=",
    "url_bar_auto_hide": True,
    "url_bar_hide_delay_ms": 1500,
    "gpu_acceleration": True,
    "dark_mode": True,
    "font_size": 14,
    "smooth_scrolling": True,
    "tab_unload_timeout_seconds": 120,  # 2 minutes - aggressive memory saving
    "max_loaded_tabs": 8,
    "restore_session_on_startup": True,
}


@dataclass
class Tab:
    """Represents a browser tab"""
    id: int
    webview: WebKit.WebView
    title: str = "New Tab"
    url: str = "about:blank"
    is_loaded: bool = False
    is_unloaded: bool = False  # For memory optimization
    favicon: Optional[str] = None
    last_active: float = field(default_factory=time.time)  # For tab unloading
    scroll_position: int = 0  # Preserve scroll on unload
    zoom_level: float = 1.0  # Per-tab zoom level


@dataclass
class Session:
    """A named collection of tabs"""
    name: str
    tabs: List[dict] = field(default_factory=list)  # Serialized tab data
    active_tab: int = 0


# Workspace definitions with icons
WORKSPACES = {
    "chill": {"icon": "🎮", "name": "Chill", "color": "#22c55e"},
    "school": {"icon": "📚", "name": "School", "color": "#3b82f6"},
    "work": {"icon": "💼", "name": "Work", "color": "#f59e0b"},
    "research": {"icon": "🔬", "name": "Research", "color": "#8b5cf6"},
    "private": {"icon": "🔒", "name": "Private", "color": "#ef4444"},
}


def load_settings() -> dict:
    """Load settings from file or return defaults"""
    if SETTINGS_FILE.exists():
        try:
            return {**DEFAULT_SETTINGS, **json.loads(SETTINGS_FILE.read_text())}
        except json.JSONDecodeError:
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict):
    """Save settings to file"""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2))


class Browser:
    """
    Main browser class.
    
    Manages tabs, sessions, and UI state.
    Designed for keyboard-first interaction.
    
    Features:
    - Tab count in URL bar
    - Tab title on hover
    - Middle-click to close tabs
    - Session auto-save on close, restore on startup
    - Smart tab unloading (5 min timeout)
    - History tracking
    - Download manager
    """
    
    def __init__(self, config: 'Config'):
        self.config = config
        self.tabs: List[Tab] = []
        self.active_tab_idx: int = 0
        self.sessions: dict[str, Session] = {}
        self.current_session: str = "default"
        
        # Workspace support
        self.current_workspace: str = "chill"
        self.workspace_tabs: dict[str, List[Tab]] = {ws: [] for ws in WORKSPACES}
        
        # Load settings
        self.settings = load_settings()
        
        # UI state
        self.sidebar_visible: bool = False
        self.bookmarks_visible: bool = False
        self.url_bar_visible: bool = True
        self.url_bar_pinned: bool = False  # When user explicitly shows it
        self.fullscreen: bool = False  # Don't start fullscreen by default
        self._last_scroll_y: float = 0
        self._url_bar_hide_timeout: Optional[int] = None
        
        # Tab unloading
        self._tab_unload_timeout: Optional[int] = None
        self._unload_after_seconds: int = self.settings.get("tab_unload_timeout_seconds", 300)
        
        # History manager
        self.history_manager = HistoryManager()
        
        # Bookmark manager
        self.bookmark_manager = BookmarkManager()
        self.hint_mode = HintMode()
        
        # Download manager
        self.download_manager = DownloadManager(
            on_progress=self._on_download_progress,
            on_complete=self._on_download_complete,
            on_failed=self._on_download_failed
        )
        
        # History suggestions popup
        self._suggestions_popup: Optional[Gtk.Popover] = None
        self._suggestions_list: Optional[Gtk.ListBox] = None
        
        # AI integration
        self.ai_client = None
        self._connect_to_ai_backend()
        
        # GTK setup
        self.app = None
        self.window = None
        self.main_box = None
        self.content_box = None
        self.url_entry = None
        self.url_bar_box = None
        self.url_bar_indicator = None  # Thin line indicator
        self.tab_count_label = None  # Tab count in URL bar
        self.security_icon = None  # HTTPS lock icon
        self.bookmark_icon = None  # Bookmark star icon
        self.tab_sidebar = None
        self.ai_sidebar = None
        self.settings_dialog = None
        self.download_notification = None
        self.find_bar = None
        self.bookmarks_bar = None
        self.context_menu_handler = None
        
        # Extension support
        self._init_extensions()
        
        # Hub sync
        self._init_hub_sync()
        
    def _init_extensions(self):
        """Initialize extension and user script managers"""
        from ..extensions import ExtensionManager, UserScriptManager
        
        self.extension_manager = ExtensionManager()
        self.userscript_manager = UserScriptManager()
        
        try:
            self.extension_manager.load_extensions()
            self.userscript_manager.load_scripts()
        except Exception as e:
            print(f"Warning: Failed to load extensions: {e}")
            
    def _init_hub_sync(self):
        """Initialize RyxHub synchronization"""
        try:
            from ..sync import HubSyncClient, SessionSync
            
            self.hub_client = HubSyncClient()
            self.session_sync = SessionSync(self.hub_client)
            
            # Register AI command handler
            self.hub_client.on("ai_command", self._handle_hub_ai_command)
            
            # Start in background
            self.hub_client.start()
        except Exception as e:
            print(f"Warning: Hub sync disabled: {e}")
            self.hub_client = None
            self.session_sync = None
            
    def _handle_hub_ai_command(self, data: dict):
        """Handle AI command from RyxHub"""
        action = data.get("action", "")
        if action == "navigate":
            url = data.get("url", "")
            if url:
                self._navigate(url)
        elif action == "close_tab":
            self._close_current_tab()
        elif action == "summarize":
            self._ai_summarize_page()
        
    def _connect_to_ai_backend(self):
        """Initialize the AI client with the localhost URL."""
        import requests
        self.ai_client = requests.Session()
        self.ai_client.headers.update({'Content-Type': 'application/json'})
        self.ai_client.base_url = self.config.ai_endpoint

    def _select_all(self):
        """Run JavaScript to select all text on the current page."""
        if self.tabs and self.active_tab_idx < len(self.tabs):
            active_tab = self.tabs[self.active_tab_idx]
            active_tab.webview.run_javascript("document.body.select();", None, None)

    def _get_page_info(self) -> dict:
        """Returns the current page's title and URL as a dictionary."""
        if self.tabs and self.active_tab_idx < len(self.tabs):
            active_tab = self.tabs[self.active_tab_idx]
            return {
                "title": active_tab.title,
                "url": active_tab.url
            }
        return {"title": "", "url": ""}

    def run(self):
        """Start the browser"""
        log.info("Starting RyxSurf...")
        self.app = Gtk.Application(application_id='ai.ryx.surf')
        self.app.connect('activate', self._on_activate)
        
        # Setup application-level actions and accelerators BEFORE run
        self._setup_app_actions(self.app)
        
        self.app.run(None)
    
    def _setup_app_actions(self, app):
        """Setup GIO actions with accelerators for reliable shortcuts"""
        from gi.repository import Gio
        
        actions = [
            ("focus-url", "<Control>l", lambda: self._focus_url_bar()),
            ("new-tab", "<Control>t", lambda: self._new_tab()),
            ("close-tab", "<Control>w", lambda: self._close_tab()),
            ("reload", "<Control>r", lambda: self._reload()),
            ("toggle-sidebar", "<Control>b", lambda: self._toggle_sidebar()),
            ("reload-f5", "F5", lambda: self._reload()),
            ("focus-url-f6", "F6", lambda: self._focus_url_bar()),
            ("fullscreen", "F11", lambda: self._toggle_fullscreen()),
            ("next-tab", "<Control>Tab", lambda: self._next_tab()),
            ("prev-tab", "<Control><Shift>Tab", lambda: self._prev_tab()),
            ("reopen-tab", "<Control><Shift>t", lambda: self._reopen_closed_tab()),
            ("find", "<Control>f", lambda: self._show_find_bar()),
            ("bookmark", "<Control>d", lambda: self._toggle_bookmark()),
        ]
        
        for name, accel, callback in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda a, p, cb=callback: cb())
            app.add_action(action)
            app.set_accels_for_action(f"app.{name}", [accel])
            log.info(f"App action: {name} = {accel}")
        
    def _on_activate(self, app):
        """Called when GTK app is ready"""
        log.info("GTK activate - building UI")
        start_time = time.time()
        
        # Hold the application to keep it running
        app.hold()
        
        self.window = Gtk.ApplicationWindow(application=app)
        self.window.set_title("RyxSurf")
        
        # Set reasonable default size (not fullscreen)
        start_fullscreen = self.settings.get("start_fullscreen", False)
        if start_fullscreen:
            self.window.set_default_size(1920, 1080)
        else:
            self.window.set_default_size(1200, 800)
        
        # Release hold when window is destroyed
        self.window.connect('destroy', lambda w: self._on_window_destroy(app))
        
        # Apply CSS styling
        self._apply_css()
        log.info(f"CSS applied in {(time.time() - start_time)*1000:.0f}ms")
        
        # Zen Browser style layout:
        # [LEFT SIDEBAR] | [RIGHT: URL BAR + WEBVIEW]
        
        # Main horizontal layout: sidebar on left, content on right
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.window.set_child(self.main_box)
        
        # Create tab sidebar FIRST (left side, always visible)
        self._create_tab_sidebar()
        self.tab_sidebar.set_visible(True)  # Always visible by default
        self.sidebar_visible = True
        
        # Right side: vertical box with URL bar on top, webview below
        self.right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.right_box.set_hexpand(True)
        self.right_box.set_vexpand(True)
        self.main_box.append(self.right_box)
        
        # Content area for webviews (must be created BEFORE url bar for auto-hide)
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.content_box.set_vexpand(True)
        self.content_box.set_hexpand(True)
        
        # Create persistent URL bar at the top (always visible)
        self._create_url_bar()
        self.url_bar_visible = True
        self.url_bar_box.set_visible(True)
        
        # Create bookmarks bar (hidden by default, below URL bar)
        self._create_bookmarks_bar()
        
        # Create find bar (hidden by default)
        self._create_find_bar()
        
        # Add content box after URL bar
        self.right_box.append(self.content_box)
        
        # Create AI sidebar (hidden by default, right side of content)
        self._create_ai_sidebar()
        
        # Create download notification
        self._create_download_notification()
        
        # Create context menu handler
        self._create_context_menu_handler()
        
        log.info(f"UI built in {(time.time() - start_time)*1000:.0f}ms")
        
        # Restore session or create initial tab
        if self.settings.get("restore_session_on_startup", True):
            log.info("Attempting to restore session...")
            self._restore_session()
            log.info(f"Session restore complete, tabs: {len(self.tabs)}")
        
        # Create initial tab if no tabs restored
        if not self.tabs:
            log.info(f"No tabs restored, creating new tab with homepage: {self.config.homepage}")
            self._new_tab(self.config.homepage)
        else:
            log.info(f"Tabs restored: {len(self.tabs)}, switching to active tab")
            self._switch_to_tab(self.active_tab_idx)
        
        # Setup keybinds
        self._setup_keybinds()
        
        # Start tab unload monitor
        self._start_tab_unload_monitor()
        
        log.info(f"Browser ready in {(time.time() - start_time)*1000:.0f}ms")
        
        self.window.present()
        
    def _on_window_destroy(self, app):
        """Handle window destruction - save session"""
        self._save_session()
        self.history_manager.close()
        self._stop_tab_unload_monitor()
        app.release()
    
    def _apply_css(self):
        """Apply ultra-minimal compact UI styling"""
        css = """
        /* ═══════════════════════════════════════════════════════════════
           ULTRA MINIMAL - Pure dark, no fluff
           ═══════════════════════════════════════════════════════════════ */
        window {
            background: #0a0a0c;
        }
        
        /* ═══════════════════════════════════════════════════════════════
           TAB SIDEBAR - Fixed 120px width (10% of ~1200px)
           ═══════════════════════════════════════════════════════════════ */
        .tab-sidebar {
            background: #0a0a0c;
            border-right: 1px solid #151518;
            padding: 4px;
            min-width: 120px;
            max-width: 120px;
        }
        
        /* Workspace bar - now in URL bar, compact style */
        .workspace-bar {
            padding: 0 4px;
        }
        
        .workspace-btn {
            background: transparent;
            border: none;
            color: #444;
            padding: 4px 6px;
            border-radius: 4px;
            font-size: 12px;
            min-width: 24px;
            min-height: 24px;
        }
        
        .workspace-btn:hover {
            background: #1a1a20;
            color: #888;
        }
        
        .workspace-btn.active {
            background: #1f1f28;
            color: #7c3aed;
        }
        
        .tab-btn {
            background: transparent;
            border: none;
            border-radius: 6px;
            padding: 4px;
        }
        
        .tab-btn:hover {
            background: #1a1a20;
        }
        
        .tab-btn.active {
            background: #1f1f28;
        }
        
        .tab-btn.unloaded {
            opacity: 0.5;
        }
        
        .tab-icon {
            color: #666;
            font-size: 12px;
            font-weight: 500;
            font-family: system-ui, sans-serif;
        }
        
        .tab-btn.active .tab-icon {
            color: #7c3aed;
        }
        
        .tab-btn:hover .tab-icon {
            color: #888;
        }
        
        .new-tab-btn {
            background: transparent;
            border: none;
            color: #444;
            border-radius: 6px;
            padding: 8px;
            font-size: 16px;
        }
        
        .new-tab-btn:hover {
            background: #1a1a20;
            color: #7c3aed;
        }
        
        /* Legacy tab-item styles (for expanded mode) */
        .tab-item {
            background: transparent;
            border: none;
            border-radius: 4px;
            padding: 4px 6px;
            margin: 1px 0;
            min-height: 24px;
        }
        
        .tab-item.active {
            background: #1f1f28;
            border-left: 2px solid #7c3aed;
            padding-left: 4px;
        }
        
        .tab-title {
            color: #777;
            font-size: 11px;
            font-weight: 400;
        }
        
        .tab-item.active .tab-title {
            color: #bbb;
        }
        
        .tab-favicon {
            color: #555;
            font-size: 8px;
        }
        
        .tab-item.active .tab-favicon {
            color: #7c3aed;
        }
        
        .tab-close {
            background: transparent;
            border: none;
            color: #444;
            padding: 2px 4px;
            border-radius: 3px;
            font-size: 10px;
            min-width: 14px;
            min-height: 14px;
            opacity: 0;
        }
        
        .tab-btn:hover .tab-close {
            opacity: 1;
        }
        
        .tab-close:hover {
            background: #ff4444;
            color: #fff;
        }
        
        /* ═══════════════════════════════════════════════════════════════
           URL BAR - Compact centered layout
           ═══════════════════════════════════════════════════════════════ */
        .url-bar {
            background: #0e0e12;
            padding: 4px 12px;
            min-height: 32px;
            border-bottom: 1px solid #1a1a1f;
        }
        
        .nav-btn {
            background: transparent;
            border: none;
            color: #555;
            border-radius: 4px;
            padding: 4px 8px;
            min-width: 24px;
            min-height: 24px;
            font-size: 12px;
        }
        
        .nav-btn:hover {
            background: #1a1a20;
            color: #999;
        }
        
        .nav-btn:disabled {
            color: #333;
        }
        
        .url-entry {
            background: #151518;
            color: #999;
            border: none;
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 12px;
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            min-height: 22px;
            caret-color: #7c3aed;
        }
        
        .url-entry:focus {
            background: #1a1a20;
            color: #ddd;
            outline: none;
        }
        
        .security-icon {
            color: #555;
            font-size: 11px;
            padding: 0 4px;
        }
        
        .security-icon.secure {
            color: #22c55e;
        }
        
        /* ═══════════════════════════════════════════════════════════════
           SCROLLBARS - Invisible until hover
           ═══════════════════════════════════════════════════════════════ */
        scrollbar {
            background: transparent;
        }
        
        scrollbar slider {
            background: rgba(255, 255, 255, 0.08);
            border-radius: 4px;
            min-width: 4px;
        }
        
        scrollbar slider:hover {
            background: rgba(124, 58, 237, 0.4);
        }
        
        /* ═══════════════════════════════════════════════════════════════
           SUGGESTIONS POPUP
           ═══════════════════════════════════════════════════════════════ */
        .suggestions-popover {
            background: #0e0e12;
            border: 1px solid #1a1a1f;
            border-radius: 6px;
        }
        
        .suggestion-row {
            padding: 6px 10px;
        }
        
        .suggestion-row:hover {
            background: #1a1a20;
        }
        
        .suggestion-title {
            color: #ccc;
            font-size: 12px;
        }
        
        .suggestion-url {
            color: #555;
            font-size: 10px;
        }
        
        .quick-suggestion {
            background: #1a1a20;
        }
        
        .quick-icon {
            color: #7c3aed;
        }
        
        .quick-domain {
            color: #999;
            font-size: 12px;
        }
        
        /* ═══════════════════════════════════════════════════════════════
           FIND BAR - Minimal
           ═══════════════════════════════════════════════════════════════ */
        .find-bar {
            background: #0e0e12;
            border-top: 1px solid #1a1a1f;
            padding: 4px 8px;
        }
        
        .find-entry {
            background: #151518;
            color: #ccc;
            border: none;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
            min-height: 22px;
        }
        
        /* ═══════════════════════════════════════════════════════════════
           TOOLTIPS - Minimal
           ═══════════════════════════════════════════════════════════════ */
        tooltip {
            background: #151518;
            color: #999;
            border: 1px solid #1a1a1f;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 10px;
        }
        
        /* ═══════════════════════════════════════════════════════════════
           AI SIDEBAR - Hidden by default
           ═══════════════════════════════════════════════════════════════ */
        .ai-sidebar {
            background: #0e0e12;
            border-left: 1px solid #1a1a1f;
            min-width: 280px;
        }
        
        /* ═══════════════════════════════════════════════════════════════
           TAB COUNT - Subtle
           ═══════════════════════════════════════════════════════════════ */
        .tab-count {
            color: #444;
            font-size: 10px;
            padding: 4px;
        }
        
        /* ═══════════════════════════════════════════════════════════════
           NEW TAB BUTTON
           ═══════════════════════════════════════════════════════════════ */
        .new-tab-btn {
            background: transparent;
            border: none;
            color: #444;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 14px;
        }
        
        .new-tab-btn:hover {
            background: #1a1a20;
            color: #888;
        }
        """
        
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css.encode('utf-8'))
        
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def _create_url_bar(self):
        """Create compact URL bar with useful controls"""
        self.url_bar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.url_bar_box.add_css_class("url-bar")
        self.url_bar_box.set_spacing(8)
        self.url_bar_box.set_hexpand(True)
        
        # Left side: Back/Forward/Reload buttons (compact)
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        
        self.back_btn = Gtk.Button(label="←")
        self.back_btn.add_css_class("nav-btn")
        self.back_btn.set_tooltip_text("Back (Alt+←)")
        self.back_btn.connect("clicked", lambda _: self._history_back())
        nav_box.append(self.back_btn)
        
        self.forward_btn = Gtk.Button(label="→")
        self.forward_btn.add_css_class("nav-btn")
        self.forward_btn.set_tooltip_text("Forward (Alt+→)")
        self.forward_btn.connect("clicked", lambda _: self._history_forward())
        nav_box.append(self.forward_btn)
        
        self.reload_btn = Gtk.Button(label="↻")
        self.reload_btn.add_css_class("nav-btn")
        self.reload_btn.set_tooltip_text("Reload (F5)")
        self.reload_btn.connect("clicked", lambda _: self._reload())
        nav_box.append(self.reload_btn)
        
        self.url_bar_box.append(nav_box)
        
        # Workspace buttons (after reload, before URL) - like Hyprland workspaces
        workspace_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        workspace_box.add_css_class("workspace-bar")
        
        self.workspace_buttons = {}
        for ws_id, ws_info in WORKSPACES.items():
            btn = Gtk.Button(label=ws_info["icon"])
            btn.add_css_class("workspace-btn")
            btn.set_tooltip_text(ws_info["name"])
            if ws_id == self.current_workspace:
                btn.add_css_class("active")
            btn.connect("clicked", lambda _, wid=ws_id: self._switch_workspace(wid))
            workspace_box.append(btn)
            self.workspace_buttons[ws_id] = btn
        
        self.url_bar_box.append(workspace_box)
        
        # Center: URL entry (60% width)
        url_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        url_container.set_hexpand(True)
        url_container.set_halign(Gtk.Align.CENTER)
        
        # Security icon
        self.security_icon = Gtk.Label(label="")
        self.security_icon.add_css_class("security-icon")
        url_container.append(self.security_icon)
        
        # URL entry - NOT full width
        self.url_entry = Gtk.Entry()
        self.url_entry.set_size_request(500, -1)  # Fixed 500px width
        self.url_entry.add_css_class("url-entry")
        self.url_entry.set_placeholder_text("Search or URL")
        self.url_entry.connect("activate", self._on_url_entry_activate)
        self.url_entry.connect("changed", self._on_url_entry_changed)
        url_container.append(self.url_entry)
        
        self.url_bar_box.append(url_container)
        
        # Right side: Useful buttons
        right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        right_box.set_halign(Gtk.Align.END)
        
        # Bookmark button
        self.bookmark_btn = Gtk.Button(label="☆")
        self.bookmark_btn.add_css_class("nav-btn")
        self.bookmark_btn.set_tooltip_text("Bookmark (Ctrl+D)")
        self.bookmark_btn.connect("clicked", lambda _: self._toggle_bookmark())
        right_box.append(self.bookmark_btn)
        
        # Tab count
        self.tab_count_label = Gtk.Label(label="1")
        self.tab_count_label.add_css_class("tab-count")
        self.tab_count_label.set_tooltip_text("Open tabs")
        right_box.append(self.tab_count_label)
        
        # Downloads button
        downloads_btn = Gtk.Button(label="↓")
        downloads_btn.add_css_class("nav-btn")
        downloads_btn.set_tooltip_text("Downloads (Ctrl+J)")
        downloads_btn.connect("clicked", lambda _: self._show_downloads())
        right_box.append(downloads_btn)
        
        # Menu button
        menu_btn = Gtk.Button(label="≡")
        menu_btn.add_css_class("nav-btn")
        menu_btn.set_tooltip_text("Menu")
        menu_btn.connect("clicked", lambda _: self._show_settings())
        right_box.append(menu_btn)
        
        self.url_bar_box.append(right_box)
        
        # Create suggestions popover
        self._create_suggestions_popover()
        
        # Add URL bar to right_box
        self.right_box.prepend(self.url_bar_box)
        
    def _create_suggestions_popover(self):
        """Create the history suggestions popover for URL bar"""
        self._suggestions_popup = Gtk.Popover()
        self._suggestions_popup.set_parent(self.url_entry)
        self._suggestions_popup.add_css_class("suggestions-popover")
        self._suggestions_popup.set_autohide(True)
        
        # List box for suggestions
        self._suggestions_list = Gtk.ListBox()
        self._suggestions_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._suggestions_list.connect("row-activated", self._on_suggestion_activated)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(300)
        scroll.set_propagate_natural_height(True)
        scroll.set_child(self._suggestions_list)
        
        self._suggestions_popup.set_child(scroll)
        
    def _on_url_entry_changed(self, entry: Gtk.Entry):
        """Handle URL entry text changes - simplified, no popups"""
        # Just update the text, no suggestions blocking input
        pass
    
    def _create_quick_suggestion_row(self, name: str, url: str) -> Gtk.ListBoxRow:
        """Create a quick domain suggestion row"""
        row = Gtk.ListBoxRow()
        row.suggestion_url = url
        row.add_css_class("suggestion-row")
        row.add_css_class("quick-suggestion")
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        
        # Icon
        icon = Gtk.Label(label="→")
        icon.add_css_class("quick-icon")
        box.append(icon)
        
        # Domain name
        label = Gtk.Label(label=f"{name}.com")
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        label.add_css_class("quick-domain")
        box.append(label)
        
        row.set_child(box)
        return row
        
    def _create_suggestion_row(self, entry_data) -> Gtk.ListBoxRow:
        """Create a suggestion row widget"""
        row = Gtk.ListBoxRow()
        row.suggestion_url = entry_data.url
        row.add_css_class("suggestion-row")
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(4)
        box.set_margin_bottom(4)
        
        # Title
        title = Gtk.Label(label=entry_data.title[:50] or entry_data.url[:50])
        title.set_halign(Gtk.Align.START)
        title.add_css_class("suggestion-title")
        title.set_ellipsize(Pango.EllipsizeMode.END)
        box.append(title)
        
        # URL
        url_label = Gtk.Label(label=entry_data.url[:60])
        url_label.set_halign(Gtk.Align.START)
        url_label.add_css_class("suggestion-url")
        url_label.set_ellipsize(Pango.EllipsizeMode.END)
        box.append(url_label)
        
        row.set_child(box)
        return row
        
    def _on_suggestion_activated(self, listbox, row):
        """Handle suggestion selection"""
        if row and hasattr(row, 'suggestion_url'):
            self.url_entry.set_text(row.suggestion_url)
            self._suggestions_popup.popdown()
            self._navigate_current(row.suggestion_url)
    
    def _create_tab_sidebar(self):
        """Create compact sidebar - ONLY tabs, no workspaces (those go in URL bar)"""
        self.tab_sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.tab_sidebar.add_css_class("tab-sidebar")
        # Fixed width: prevent expansion
        self.tab_sidebar.set_size_request(120, -1)
        self.tab_sidebar.set_hexpand(False)  # Critical: prevent horizontal expansion
        
        # Scrollable area for tabs
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.set_hexpand(False)  # Prevent scroll area from expanding
        
        self.tab_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.tab_list_box.set_hexpand(False)
        scroll.set_child(self.tab_list_box)
        self.tab_sidebar.append(scroll)
        
        # New tab button at bottom
        new_tab_btn = Gtk.Button(label="+")
        new_tab_btn.add_css_class("new-tab-btn")
        new_tab_btn.set_tooltip_text("New Tab (Ctrl+T)")
        new_tab_btn.connect("clicked", lambda _: self._new_tab())
        self.tab_sidebar.append(new_tab_btn)
        
        # Prepend to main_box so it's on the left
        self.main_box.prepend(self.tab_sidebar)
    
    def _create_download_notification(self):
        """Create the download notification widget"""
        self.download_notification = DownloadNotification(self.download_manager)
        # Add to right_box (bottom of content area)
        self.right_box.append(self.download_notification)
    
    def _create_bookmarks_bar(self):
        """Create the bookmarks bar (hidden by default)"""
        from ..ui.bookmarks_bar import BookmarksBar
        self.bookmarks_bar = BookmarksBar(
            bookmark_manager=self.bookmark_manager,
            on_navigate=self._navigate_current
        )
        self.right_box.append(self.bookmarks_bar)
        
    def _create_find_bar(self):
        """Create the find-in-page bar (hidden by default)"""
        from ..ui.find_bar import FindBar
        self.find_bar = FindBar(get_webview_callback=self._get_current_webview)
        self.right_box.append(self.find_bar)
        
    def _create_context_menu_handler(self):
        """Create the context menu handler"""
        from ..ui.context_menu import ContextMenuHandler
        self.context_menu_handler = ContextMenuHandler(
            on_open_new_tab=self._new_tab,
            on_save_image=self._save_image,
            on_inspect=self._inspect_element
        )
        
    def _get_current_webview(self) -> Optional[WebKit.WebView]:
        """Get the current tab's webview"""
        if self.tabs:
            return self.tabs[self.active_tab_idx].webview
        return None
        
    def _save_image(self, url: str):
        """Save image from URL - triggers download"""
        if self.tabs:
            webview = self.tabs[self.active_tab_idx].webview
            # Navigate to image URL to trigger download
            webview.download_uri(url)
            
    def _inspect_element(self):
        """Open web inspector"""
        if self.tabs:
            webview = self.tabs[self.active_tab_idx].webview
            inspector = webview.get_inspector()
            inspector.show()
    
    def _create_ai_sidebar(self):
        """Create the AI sidebar (hidden by default)"""
        self.ai_sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.ai_sidebar.add_css_class("ai-sidebar")
        self.ai_sidebar.set_visible(False)
        # Will be appended after webview
    
    def _on_url_entry_activate(self, entry: Gtk.Entry):
        """Handle URL entry activation (Enter key) - SIMPLE: just navigate"""
        text = entry.get_text().strip()
        log.info(f"URL entry activate: '{text}'")
        
        if not text:
            return
        
        # Close any suggestions
        if hasattr(self, '_suggestions_popup') and self._suggestions_popup:
            self._suggestions_popup.popdown()
        
        # Quick domain shortcuts
        QUICK_DOMAINS = {
            "yt": "https://www.youtube.com",
            "youtube": "https://www.youtube.com",
            "g": "https://www.google.com",
            "google": "https://www.google.com",
            "gh": "https://github.com",
            "github": "https://github.com",
            "r": "https://www.reddit.com",
            "reddit": "https://www.reddit.com",
            "tw": "https://twitter.com",
            "x": "https://x.com",
        }
        
        lower_text = text.lower()
        
        # Check quick domains first
        if lower_text in QUICK_DOMAINS:
            url = QUICK_DOMAINS[lower_text]
            log.info(f"Quick domain: {url}")
            self._navigate_current(url)
        elif text.startswith("!"):
            # AI command
            log.info("AI command detected")
            self._handle_ai_command(text[1:])
        elif text.startswith("?"):
            # Search
            query = quote_plus(text[1:])
            url = f"https://google.com/search?q={query}"
            log.info(f"Search: {url}")
            self._navigate_current(url)
        elif "." in text or text.startswith("http"):
            # URL
            url = text if text.startswith("http") else f"https://{text}"
            log.info(f"URL: {url}")
            self._navigate_current(url)
        else:
            # Default to search
            query = quote_plus(text)
            url = f"https://google.com/search?q={query}"
            log.info(f"Search (default): {url}")
            self._navigate_current(url)
        
        # Return focus to webview
        if self.tabs:
            self.tabs[self.active_tab_idx].webview.grab_focus()
        
    def _setup_keybinds(self):
        """Setup keyboard shortcuts using GTK4 ShortcutController"""
        log.info("Setting up keybinds with ShortcutController...")
        
        # Use GTK4 ShortcutController for reliable keybinds even with WebKit
        shortcut_controller = Gtk.ShortcutController()
        shortcut_controller.set_scope(Gtk.ShortcutScope.GLOBAL)
        
        # Define shortcuts
        shortcuts = [
            ("<Control>l", "focus-url", self._focus_url_bar),
            ("<Control>t", "new-tab", self._new_tab),
            ("<Control>w", "close-tab", self._close_tab),
            ("<Control>r", "reload", self._reload),
            ("<Control>b", "toggle-sidebar", self._toggle_sidebar),
            ("<Control><Shift>t", "reopen-tab", self._reopen_closed_tab),
            ("F5", "reload-f5", self._reload),
            ("F6", "focus-url-f6", self._focus_url_bar),
            ("F11", "fullscreen", self._toggle_fullscreen),
            ("Escape", "escape", self._handle_escape),
        ]
        
        for accel, name, callback in shortcuts:
            trigger = Gtk.ShortcutTrigger.parse_string(accel)
            if trigger:
                def make_callback(cb, n):
                    def wrapper(widget, variant):
                        print(f"!!! SHORTCUT TRIGGERED: {n}", flush=True)
                        log.info(f"Shortcut triggered: {n}")
                        cb()
                        return True
                    return wrapper
                action = Gtk.CallbackAction.new(make_callback(callback, name))
                shortcut = Gtk.Shortcut.new(trigger, action)
                shortcut_controller.add_shortcut(shortcut)
                log.info(f"Added shortcut: {accel} -> {name}")
        
        self.window.add_controller(shortcut_controller)
        
        # Also keep EventControllerKey for other keys
        controller = Gtk.EventControllerKey()
        controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        controller.connect('key-pressed', self._on_key_press)
        self.window.add_controller(controller)
        
        log.info("Keybinds setup complete")
    
    def _handle_escape(self):
        """Handle Escape key"""
        if self.url_entry and self.url_entry.has_focus():
            if self.tabs:
                self.tabs[self.active_tab_idx].webview.grab_focus()
            self._hide_url_bar()
        elif hasattr(self, 'hint_mode') and self.hint_mode and self.hint_mode.active:
            self.hint_mode.deactivate()
        return True
    
    def _on_webview_key_press(self, controller, keyval, keycode, state):
        """Handle key press events from WebView - intercept browser shortcuts"""
        ctrl_pressed = bool(state & Gdk.ModifierType.CONTROL_MASK)
        shift_pressed = bool(state & Gdk.ModifierType.SHIFT_MASK)
        
        key_name = Gdk.keyval_name(keyval)
        if key_name is None:
            return Gdk.EVENT_PROPAGATE
        
        log.info(f"WebView Key: {key_name}, Ctrl: {ctrl_pressed}")
        
        # Handle browser shortcuts
        if ctrl_pressed and not shift_pressed:
            if key_name in ('l', 'L'):
                log.info("Ctrl+L detected - focusing URL bar")
                self._show_url_bar(pin=True)
                self._focus_url_bar()
                return Gdk.EVENT_STOP
            elif key_name in ('t', 'T'):
                self._new_tab()
                return Gdk.EVENT_STOP
            elif key_name in ('w', 'W'):
                self._close_tab()
                return Gdk.EVENT_STOP
            elif key_name in ('r', 'R'):
                self._reload()
                return Gdk.EVENT_STOP
            elif key_name in ('b', 'B'):
                self._toggle_sidebar()
                return Gdk.EVENT_STOP
        
        if ctrl_pressed and shift_pressed:
            if key_name in ('t', 'T'):
                self._reopen_closed_tab()
                return Gdk.EVENT_STOP
        
        if key_name == 'Escape':
            self._handle_escape()
            return Gdk.EVENT_STOP
        
        if key_name == 'F5':
            self._reload()
            return Gdk.EVENT_STOP
        
        if key_name == 'F6':
            self._focus_url_bar()
            return Gdk.EVENT_STOP
        
        if key_name == 'F11':
            self._toggle_fullscreen()
            return Gdk.EVENT_STOP
        
        return Gdk.EVENT_PROPAGATE
        
    def _on_key_press(self, controller, keyval, keycode, state):
        """Handle key press events"""
        # Get modifier state
        ctrl_pressed = bool(state & Gdk.ModifierType.CONTROL_MASK)
        shift_pressed = bool(state & Gdk.ModifierType.SHIFT_MASK)
        super_pressed = bool(state & Gdk.ModifierType.SUPER_MASK)
        
        key_name = Gdk.keyval_name(keyval)
        if key_name is None:
            return Gdk.EVENT_PROPAGATE
        
        # Debug: Log key events
        log.info(f"Key: {key_name}, Ctrl: {ctrl_pressed}, Shift: {shift_pressed}")
        
        # Escape - hide URL bar and close overlays
        if key_name == 'Escape':
            if self.url_entry and self.url_entry.has_focus():
                # Unfocus URL entry and return to webview
                if self.tabs:
                    self.tabs[self.active_tab_idx].webview.grab_focus()
                self._hide_url_bar()
                return Gdk.EVENT_STOP
            if self.url_bar_visible:
                self._hide_url_bar()
                return Gdk.EVENT_STOP
            self._close_overlays()
            return Gdk.EVENT_STOP
        
        # Ctrl-based shortcuts (case insensitive matching)
        if ctrl_pressed and not shift_pressed:
            if key_name in ('t', 'T'):
                self._new_tab()
                return Gdk.EVENT_STOP
            elif key_name in ('w', 'W'):
                self._close_tab()
                return Gdk.EVENT_STOP
            elif key_name in ('l', 'L'):
                self._show_url_bar(pin=True)
                self._focus_url_bar()
                return Gdk.EVENT_STOP
            elif key_name in ('g', 'G'):
                # Super+G / Ctrl+G - show URL bar
                self._show_url_bar(pin=True)
                self._focus_url_bar()
                return Gdk.EVENT_STOP
            elif key_name in ('b', 'B'):
                self._toggle_sidebar()
                return Gdk.EVENT_STOP
            elif key_name in ('r', 'R'):
                self._reload()
                return Gdk.EVENT_STOP
            elif key_name in ('f', 'F'):
                # Ctrl+F - Find in page
                self._show_find_bar()
                return Gdk.EVENT_STOP
            elif key_name in ('d', 'D'):
                # Ctrl+D - Toggle bookmark
                self._toggle_bookmark()
                return Gdk.EVENT_STOP
            elif key_name == 'Tab':
                self._next_tab()
                return Gdk.EVENT_STOP
            elif key_name in ('Down', 'KP_Down'):
                # Ctrl+Down - Next tab
                self._next_tab()
                return Gdk.EVENT_STOP
            elif key_name in ('Up', 'KP_Up'):
                # Ctrl+Up - Previous tab
                self._prev_tab()
                return Gdk.EVENT_STOP
            elif key_name in ('1', '2', '3', '4', '5', '6', '7', '8', '9'):
                self._goto_tab(int(key_name) - 1)
                return Gdk.EVENT_STOP
            elif key_name == 'comma':
                # Ctrl+, - Open settings
                self._show_settings()
                return Gdk.EVENT_STOP
            elif key_name in ('plus', 'equal', 'KP_Add'):
                # Ctrl++ - Zoom in
                self._zoom_in()
                return Gdk.EVENT_STOP
            elif key_name in ('minus', 'KP_Subtract'):
                # Ctrl+- - Zoom out
                self._zoom_out()
                return Gdk.EVENT_STOP
            elif key_name in ('0', 'KP_0'):
                # Ctrl+0 - Reset zoom
                self._zoom_reset()
                return Gdk.EVENT_STOP
            elif key_name in ('h', 'H'):
                # Ctrl+H - History
                self._show_history()
                return Gdk.EVENT_STOP
            elif key_name in ('j', 'J'):
                # Ctrl+J - Downloads
                self._show_downloads()
                return Gdk.EVENT_STOP
            elif key_name in ('p', 'P'):
                # Ctrl+P - Print (disabled for now)
                return Gdk.EVENT_STOP
            elif key_name in ('s', 'S'):
                # Ctrl+S - Save page
                self._save_page()
                return Gdk.EVENT_STOP
            elif key_name in ('u', 'U'):
                # Ctrl+U - View source
                self._view_source()
                return Gdk.EVENT_STOP
            elif key_name in ('y', 'Y'):
                # Ctrl+Y - Copy URL
                self._copy_url()
                return Gdk.EVENT_STOP
            elif key_name == 'Left':
                # Ctrl+Left - Back
                self._history_back()
                return Gdk.EVENT_STOP
            elif key_name == 'Right':
                # Ctrl+Right - Forward
                self._history_forward()
                return Gdk.EVENT_STOP
            elif key_name in ('i', 'I'):
                # Ctrl+I - Picture-in-Picture
                self._toggle_pip()
                return Gdk.EVENT_STOP
        
        # Ctrl+Shift shortcuts
        if ctrl_pressed and shift_pressed:
            if key_name in ('a', 'A'):
                self._toggle_ai_sidebar()
                return Gdk.EVENT_STOP
            elif key_name in ('s', 'S'):
                self._save_session()
                return Gdk.EVENT_STOP
            elif key_name in ('r', 'R'):
                self._hard_reload()
                return Gdk.EVENT_STOP
            elif key_name in ('b', 'B'):
                # Ctrl+Shift+B - Toggle bookmarks bar
                self._toggle_bookmarks_bar()
                return Gdk.EVENT_STOP
            elif key_name in ('u', 'U'):
                # Ctrl+Shift+U - Toggle URL bar visibility
                self._toggle_url_bar()
                return Gdk.EVENT_STOP
            elif key_name == 'ISO_Left_Tab' or key_name == 'Tab':
                self._prev_tab()
                return Gdk.EVENT_STOP
            elif key_name in ('t', 'T'):
                # Ctrl+Shift+T - Reopen closed tab
                self._reopen_closed_tab()
                return Gdk.EVENT_STOP
            elif key_name in ('p', 'P'):
                # Ctrl+Shift+P - Screenshot
                self._take_screenshot()
                return Gdk.EVENT_STOP
            elif key_name in ('e', 'E'):
                # Ctrl+Shift+E - Restore from escape
                self._restore_from_escape()
                return Gdk.EVENT_STOP
            elif key_name in ('v', 'V'):
                # Ctrl+Shift+V - Split view
                self._toggle_split_view()
                return Gdk.EVENT_STOP
            elif key_name in ('x', 'X'):
                # Ctrl+Shift+X - Clear site data
                self._clear_site_data()
                return Gdk.EVENT_STOP
            elif key_name in ('m', 'M'):
                # Ctrl+Shift+M - Performance overlay
                self._show_performance_overlay()
                return Gdk.EVENT_STOP
            elif key_name in ('k', 'K'):
                # Ctrl+Shift+K - Kill tab scripts
                self._kill_tab_scripts()
                return Gdk.EVENT_STOP
            elif key_name in ('n', 'N'):
                # Ctrl+Shift+N - New private window (placeholder)
                return Gdk.EVENT_STOP
            elif key_name in ('Delete', 'BackSpace'):
                # Ctrl+Shift+Delete - Clear history
                return Gdk.EVENT_STOP
        
        # Super key shortcuts (workspaces like Hyprland)
        super_pressed = bool(state & Gdk.ModifierType.SUPER_MASK)
        if super_pressed and not ctrl_pressed and not alt_pressed:
            # Super+1-5 for workspaces
            workspace_keys = {'1': 'chill', '2': 'school', '3': 'work', '4': 'research', '5': 'private'}
            if key_name in workspace_keys:
                self._switch_workspace(workspace_keys[key_name])
                return Gdk.EVENT_STOP
            elif key_name == 'Escape':
                # Super+Escape - Quick escape (panic button)
                self._quick_escape()
                return Gdk.EVENT_STOP
        
        # Alt shortcuts
        alt_pressed = bool(state & Gdk.ModifierType.ALT_MASK)
        if alt_pressed and not ctrl_pressed:
            if key_name == 'Left':
                # Alt+Left - Back
                self._history_back()
                return Gdk.EVENT_STOP
            elif key_name == 'Right':
                # Alt+Right - Forward
                self._history_forward()
                return Gdk.EVENT_STOP
            elif key_name == 'Home':
                # Alt+Home - Go home
                self._go_home()
                return Gdk.EVENT_STOP
        
        # F-keys
        if key_name == 'F5':
            self._reload()
            return Gdk.EVENT_STOP
        elif key_name == 'F6':
            # F6 - Focus URL bar
            self._show_url_bar(pin=True)
            self._focus_url_bar()
            return Gdk.EVENT_STOP
        
        # F11 - True fullscreen (hide all UI)
        if key_name == 'F11':
            self._toggle_fullscreen()
            return Gdk.EVENT_STOP
        
        # Super key shortcuts (for AI features)
        if super_pressed and not ctrl_pressed:
            if shift_pressed and key_name in ('a', 'A'):
                self._summarize_page()
                return Gdk.EVENT_STOP
            elif key_name == 'x':
                self._dismiss_popup()
                return Gdk.EVENT_STOP
            elif key_name in ('c', 'C'):
                # Super+C - Auto-clean page (aggressive)
                self._auto_clean_page()
                return Gdk.EVENT_STOP
            elif key_name in ('r', 'R'):
                # Super+R - Reader mode
                self._toggle_reader_mode()
                return Gdk.EVENT_STOP
        
        # F for link hints (only when Ctrl not pressed and not in URL entry)
        if not ctrl_pressed and key_name in ('f', 'F'):
            if self.url_entry and not self.url_entry.has_focus():
                if not self._is_focused_on_input():
                    self._hint_mode()
                    return Gdk.EVENT_STOP
        
        # Backspace - Go back (when not in input)
        if key_name == 'BackSpace' and not ctrl_pressed and not shift_pressed:
            if self.url_entry and not self.url_entry.has_focus():
                if not self._is_focused_on_input():
                    self._history_back()
                    return Gdk.EVENT_STOP
            
        return Gdk.EVENT_PROPAGATE
    
    def _toggle_fullscreen(self):
        """Toggle true fullscreen mode (hide all UI)"""
        if not hasattr(self, '_is_fullscreen'):
            self._is_fullscreen = False
        
        self._is_fullscreen = not self._is_fullscreen
        
        if self._is_fullscreen:
            # Hide sidebar and URL bar
            self.tab_sidebar.set_visible(False)
            self.sidebar_visible = False
            self._hide_url_bar()
            self.url_bar_pinned = False
            self.url_bar_box.set_visible(False)
            if self.url_bar_indicator:
                self.url_bar_indicator.set_visible(False)
            self.window.fullscreen()
        else:
            # Restore UI
            self.tab_sidebar.set_visible(True)
            self.sidebar_visible = True
            self.url_bar_box.set_visible(True)
            if self.url_bar_indicator:
                self.url_bar_indicator.set_visible(True)
            self.window.unfullscreen()
    
    def _show_history(self):
        """Show browsing history in a popup"""
        # For now, open history in new tab
        self._new_tab("about:history")
    
    def _show_downloads(self):
        """Show downloads manager"""
        if hasattr(self, 'download_manager'):
            self.download_manager.show()
    
    def _save_page(self):
        """Save current page as HTML or MHTML"""
        if not self.tabs:
            return
        tab = self.tabs[self.active_tab_idx]
        if not tab.url or tab.url == "about:blank":
            return
            
        # Create file chooser dialog
        dialog = Gtk.FileDialog()
        dialog.set_title("Save Page As")
        
        # Suggest filename based on page title
        safe_title = "".join(c for c in (tab.title or "page") if c.isalnum() or c in " -_").strip()
        dialog.set_initial_name(f"{safe_title[:50]}.html")
        
        # Setup file filters
        html_filter = Gtk.FileFilter()
        html_filter.set_name("HTML files")
        html_filter.add_mime_type("text/html")
        html_filter.add_pattern("*.html")
        html_filter.add_pattern("*.htm")
        
        filter_model = Gio.ListStore.new(Gtk.FileFilter)
        filter_model.append(html_filter)
        dialog.set_filters(filter_model)
        
        def on_save_response(dialog, result):
            try:
                file = dialog.save_finish(result)
                if file:
                    path = file.get_path()
                    # Get page HTML and save
                    tab.webview.run_javascript(
                        "document.documentElement.outerHTML",
                        None,
                        lambda wv, res, p=path: self._finish_save_page(wv, res, p),
                        path
                    )
            except Exception as e:
                log.error(f"Save failed: {e}")
        
        dialog.save(self.window, None, on_save_response)
    
    def _finish_save_page(self, webview, result, path):
        """Complete page save after getting HTML content"""
        try:
            js_result = webview.run_javascript_finish(result)
            if js_result:
                html = js_result.get_js_value().to_string()
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(html)
                log.info(f"Page saved to {path}")
        except Exception as e:
            log.error(f"Failed to save page: {e}")
    
    def _view_source(self):
        """View page source"""
        if not self.tabs:
            return
        tab = self.tabs[self.active_tab_idx]
        if tab.url:
            self._new_tab(f"view-source:{tab.url}")
        
    def _setup_url_bar_auto_hide(self):
        """Setup auto-hide behavior for URL bar"""
        # Click detection on content area
        click_controller = Gtk.GestureClick()
        click_controller.connect("pressed", self._on_content_click)
        self.content_box.add_controller(click_controller)
    
    def _on_indicator_hover(self, controller, x, y):
        """Show URL bar when hovering over the indicator"""
        self._show_url_bar()
    
    def _on_content_click(self, gesture, n_press, x, y):
        """Hide URL bar when clicking on content"""
        if self.url_bar_visible and not self.url_bar_pinned:
            self._hide_url_bar()
    
    def _show_url_bar(self, pin: bool = False):
        """Show the URL bar"""
        self.url_bar_visible = True
        self.url_bar_pinned = pin
        self.url_bar_box.set_visible(True)
        self.url_bar_box.remove_css_class("hidden")
        if self.url_bar_indicator:
            self.url_bar_indicator.set_visible(False)
        
        # Cancel any pending hide timeout
        if self._url_bar_hide_timeout:
            GLib.source_remove(self._url_bar_hide_timeout)
            self._url_bar_hide_timeout = None
    
    def _hide_url_bar(self):
        """Hide the URL bar, show thin indicator"""
        if self.url_bar_pinned:
            return
        self.url_bar_visible = False
        self.url_bar_box.add_css_class("hidden")
        if self.url_bar_indicator:
            self.url_bar_indicator.set_visible(True)
        
        # Actually hide after animation
        GLib.timeout_add(200, lambda: self.url_bar_box.set_visible(False) or False)
    
    def _toggle_url_bar(self):
        """Toggle URL bar visibility (Ctrl+Shift+U)"""
        if self.url_bar_visible:
            self.url_bar_pinned = False  # Allow hiding
            self._hide_url_bar()
            if self.url_bar_indicator:
                self.url_bar_indicator.set_visible(False)  # Also hide indicator
        else:
            self._show_url_bar(pin=True)
    
    def _schedule_url_bar_hide(self):
        """Schedule URL bar to hide after delay"""
        if self._url_bar_hide_timeout:
            GLib.source_remove(self._url_bar_hide_timeout)
        
        delay = self.settings.get("url_bar_hide_delay_ms", 1500)
        self._url_bar_hide_timeout = GLib.timeout_add(delay, self._auto_hide_url_bar)
    
    def _auto_hide_url_bar(self):
        """Auto-hide callback"""
        if not self.url_bar_pinned and self.settings.get("url_bar_auto_hide", True):
            self._hide_url_bar()
        self._url_bar_hide_timeout = None
        return False

    def _new_tab(self, url: str = "about:blank"):
        """Create a new tab"""
        webview = WebKit.WebView()
        
        # Add key controller to WebView to capture keys before WebKit processes them
        webview_key_controller = Gtk.EventControllerKey()
        webview_key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        webview_key_controller.connect('key-pressed', self._on_webview_key_press)
        webview.add_controller(webview_key_controller)
        
        # Configure WebView settings with GPU acceleration
        settings = webview.get_settings()
        settings.set_enable_javascript(True)
        settings.set_enable_developer_extras(True)
        settings.set_javascript_can_open_windows_automatically(False)
        
        # GPU acceleration settings
        settings.set_hardware_acceleration_policy(WebKit.HardwareAccelerationPolicy.ALWAYS)
        settings.set_enable_webgl(True)
        settings.set_enable_smooth_scrolling(self.settings.get("smooth_scrolling", True))
        
        # Additional performance settings
        settings.set_enable_page_cache(True)
        settings.set_enable_back_forward_navigation_gestures(True)
        
        # Media settings
        settings.set_enable_media_stream(True)
        settings.set_media_playback_requires_user_gesture(False)
        
        # Dark mode for web content
        webview.set_background_color(Gdk.RGBA(red=0.05, green=0.05, blue=0.07, alpha=1.0))
        
        # Set initial title based on URL
        initial_title = "New Tab"
        if url and url != "about:blank":
            # Extract domain for initial title
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                initial_title = parsed.netloc or url[:30]
            except:
                initial_title = url[:30]
        
        tab = Tab(
            id=len(self.tabs),
            webview=webview,
            url=url,
            title=initial_title,
            last_active=time.time()
        )
        
        # Connect signals for navigation
        webview.connect('notify::title', lambda w, pspec, t=tab: self._on_title_change(t))
        webview.connect('notify::uri', lambda w, pspec, t=tab: self._on_uri_change(t))
        webview.connect('load-changed', lambda w, e, t=tab: self._on_load_changed(w, e, t))
        webview.connect('load-failed', self._on_load_failed)
        
        # Connect download handler
        network_session = webview.get_network_session()
        network_session.connect('download-started', self._on_download_started)
        
        # Setup context menu handler
        if self.context_menu_handler:
            self.context_menu_handler.setup_webview(webview)
        
        self.tabs.append(tab)
        self._switch_to_tab(len(self.tabs) - 1)
        
        # Setup extensions for this webview
        if hasattr(self, 'extension_manager'):
            self.extension_manager.setup_webview(webview)
        
        # Sync tab opened event
        if hasattr(self, 'hub_client') and self.hub_client:
            self.hub_client.sync_tab_opened(tab.id, url, tab.title)
        
        # Load the URL after adding to tabs
        if url and url != "about:blank":
            webview.load_uri(url)
        else:
            # New tab - load internal new tab page, show and focus URL bar
            self._load_newtab_page(webview)
            self._show_url_bar(pin=True)
            GLib.idle_add(self._focus_url_bar)
        
        self._update_tab_sidebar()
        self._update_window_title()
    
    def _load_newtab_page(self, webview):
        """Load simple blank new tab page"""
        # Simple about:blank instead of HTML to avoid multiple load events
        # The URL bar is the main focus for new tabs anyway
        webview.load_uri("about:blank")
        
    def _close_tab(self, idx: Optional[int] = None):
        """Close a tab - save to closed_tabs for Ctrl+Shift+T restore"""
        if idx is None:
            idx = self.active_tab_idx
            
        if len(self.tabs) <= 1:
            # Don't close last tab, just clear it
            self.tabs[0].webview.load_uri("about:blank")
            return
        
        # Save closed tab info for restore
        closed_tab = self.tabs[idx]
        if not hasattr(self, '_closed_tabs'):
            self._closed_tabs = []
        self._closed_tabs.append({
            'url': closed_tab.url,
            'title': closed_tab.title,
            'scroll_position': closed_tab.scroll_position
        })
        # Keep only last 10 closed tabs
        self._closed_tabs = self._closed_tabs[-10:]
        
        # Sync tab close event
        if hasattr(self, 'hub_client') and self.hub_client:
            self.hub_client.sync_tab_closed(closed_tab.id)
            
        self.tabs.pop(idx)
        if self.active_tab_idx >= len(self.tabs):
            self.active_tab_idx = len(self.tabs) - 1
        self._switch_to_tab(self.active_tab_idx)
        self._update_tab_sidebar()
    
    def _reopen_closed_tab(self):
        """Reopen the last closed tab (Ctrl+Shift+T)"""
        if not hasattr(self, '_closed_tabs') or not self._closed_tabs:
            return
        
        tab_info = self._closed_tabs.pop()
        self._new_tab(tab_info['url'])
    
    def _go_home(self):
        """Navigate to homepage"""
        if self.tabs:
            homepage = self.settings.get("homepage", "https://www.google.com")
            self.tabs[self.active_tab_idx].webview.load_uri(homepage)
        
    def _switch_to_tab(self, idx: int):
        """Switch to a specific tab, reload if unloaded"""
        if 0 <= idx < len(self.tabs):
            self.active_tab_idx = idx
            tab = self.tabs[idx]
            
            # Update last active time
            tab.last_active = time.time()
            
            # Reload if unloaded
            if tab.is_unloaded:
                self._reload_unloaded_tab(tab)
            
            # Apply tab's zoom level
            tab.webview.set_zoom_level(tab.zoom_level)
            
            self._update_content_view()
            # Update URL bar with current tab's URL
            if self.url_entry and self.tabs:
                self.url_entry.set_text(self.tabs[idx].url or "")
            
            # Update security icon
            self._update_security_icon(tab.url)
            
            # Update bookmark icon
            self._update_bookmark_icon(tab.url)
            
    def _goto_tab(self, idx: int):
        """Go to tab by number (0-indexed)"""
        self._switch_to_tab(idx)
        
    def _update_content_view(self):
        """Update the main content area with current tab's webview"""
        log.info(f"_update_content_view: tabs={len(self.tabs) if self.tabs else 0}, content_box={self.content_box}")
        # Remove old webviews from content_box
        child = self.content_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            if isinstance(child, WebKit.WebView):
                self.content_box.remove(child)
            child = next_child
            
        # Add current tab's webview
        if self.tabs:
            tab = self.tabs[self.active_tab_idx]
            log.info(f"Adding webview to content_box: tab={tab.id}, url={tab.url}")
            
            # Remove AI sidebar temporarily if it's in the way
            if self.ai_sidebar.get_parent():
                self.content_box.remove(self.ai_sidebar)
            
            # Add webview
            tab.webview.set_hexpand(True)
            tab.webview.set_vexpand(True)
            self.content_box.append(tab.webview)
            log.info("Webview added to content_box")
            
            # Re-add AI sidebar at the end
            if self.ai_sidebar.get_visible():
                self.content_box.append(self.ai_sidebar)
    
    def _update_tab_sidebar(self):
        """Update the tab sidebar with compact tab titles"""
        if not hasattr(self, 'tab_list_box'):
            return
            
        # Clear existing
        child = self.tab_list_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.tab_list_box.remove(child)
            child = next_child
        
        # Update tab count
        if hasattr(self, 'tab_count_label') and self.tab_count_label:
            self.tab_count_label.set_text(str(len(self.tabs)))
        
        # Add tabs with truncated titles
        for i, tab in enumerate(self.tabs):
            btn = Gtk.Button()
            btn.add_css_class("tab-btn")
            btn.set_size_request(-1, 28)  # Full width, compact height
            
            if i == self.active_tab_idx:
                btn.add_css_class("active")
            if tab.is_unloaded:
                btn.add_css_class("unloaded")
            
            # Create horizontal box for icon + title
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            box.set_margin_start(6)
            box.set_margin_end(6)
            
            # Icon based on state
            if hasattr(tab, 'is_loading') and tab.is_loading:
                indicator = Gtk.Spinner()
                indicator.start()
                indicator.set_size_request(12, 12)
                box.append(indicator)
            else:
                # Favicon placeholder or first letter of title/domain
                title_for_icon = tab.title if tab.title and tab.title != "New Tab" else ""
                if not title_for_icon and tab.url:
                    # Extract domain for icon
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(tab.url)
                        title_for_icon = parsed.netloc or ""
                    except:
                        pass
                
                first_char = title_for_icon[0].upper() if title_for_icon and title_for_icon[0].isalpha() else "●"
                icon_label = Gtk.Label(label=first_char)
                icon_label.add_css_class("tab-favicon")
                box.append(icon_label)
            
            # Title - show actual title or domain or "New Tab"
            # Extended to 25 chars for better readability
            if tab.title and tab.title != "New Tab":
                title_text = tab.title[:25]
            elif tab.url and tab.url != "about:blank":
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(tab.url)
                    title_text = parsed.netloc[:25] if parsed.netloc else "New Tab"
                except:
                    title_text = "New Tab"
            else:
                title_text = "New Tab"
                
            title_label = Gtk.Label(label=title_text)
            title_label.add_css_class("tab-title")
            title_label.set_halign(Gtk.Align.START)
            title_label.set_hexpand(True)
            title_label.set_ellipsize(Pango.EllipsizeMode.END)
            box.append(title_label)
            
            btn.set_child(box)
            btn.set_tooltip_text(tab.title or tab.url or "New Tab")
            btn.connect("clicked", lambda _, idx=i: self._switch_to_tab(idx))
            
            # Middle-click to close
            middle = Gtk.GestureClick()
            middle.set_button(2)
            middle.connect("pressed", lambda g, n, x, y, idx=i: self._close_tab(idx))
            btn.add_controller(middle)
            
            # Right-click to close
            right = Gtk.GestureClick()
            right.set_button(3)
            right.connect("pressed", lambda g, n, x, y, idx=i: self._close_tab(idx))
            btn.add_controller(right)
            
            self.tab_list_box.append(btn)
        
        # Update tab count
        if hasattr(self, 'tab_count_label') and self.tab_count_label:
            count = len(self.tabs)
            unloaded = sum(1 for t in self.tabs if t.is_unloaded)
            if unloaded > 0:
                self.tab_count_label.set_text(f"{count}({unloaded})")
            else:
                self.tab_count_label.set_text(str(count))
    
    def _setup_tab_drag(self, btn: Gtk.Button, tab_idx: int):
        """Setup drag source and drop target for tab reordering"""
        # Drag source
        drag_source = Gtk.DragSource()
        drag_source.set_actions(Gdk.DragAction.MOVE)
        drag_source.connect("prepare", lambda ds, x, y, idx=tab_idx: self._on_tab_drag_prepare(idx))
        drag_source.connect("drag-begin", self._on_tab_drag_begin)
        btn.add_controller(drag_source)
        
        # Drop target
        drop_target = Gtk.DropTarget.new(int, Gdk.DragAction.MOVE)
        drop_target.connect("drop", lambda dt, value, x, y, idx=tab_idx: self._on_tab_drop(value, idx))
        drop_target.connect("enter", self._on_tab_drag_enter)
        drop_target.connect("leave", self._on_tab_drag_leave)
        btn.add_controller(drop_target)
    
    def _on_tab_drag_prepare(self, tab_idx: int):
        """Prepare drag data"""
        return Gdk.ContentProvider.new_for_value(tab_idx)
    
    def _on_tab_drag_begin(self, drag_source, drag):
        """Handle drag start"""
        pass  # Could add visual feedback here
    
    def _on_tab_drag_enter(self, drop_target, x, y):
        """Handle drag entering a tab button"""
        widget = drop_target.get_widget()
        if widget:
            widget.add_css_class("drop-target")
        return Gdk.DragAction.MOVE
    
    def _on_tab_drag_leave(self, drop_target):
        """Handle drag leaving a tab button"""
        widget = drop_target.get_widget()
        if widget:
            widget.remove_css_class("drop-target")
    
    def _on_tab_drop(self, source_idx: int, target_idx: int) -> bool:
        """Handle tab drop - reorder tabs"""
        if source_idx == target_idx:
            return False
        
        # Get the tab being moved
        tab = self.tabs.pop(source_idx)
        
        # Adjust target index if source was before target
        if source_idx < target_idx:
            target_idx -= 1
        
        # Insert at new position
        self.tabs.insert(target_idx, tab)
        
        # Update active tab index if needed
        if self.active_tab_idx == source_idx:
            self.active_tab_idx = target_idx
        elif source_idx < self.active_tab_idx <= target_idx:
            self.active_tab_idx -= 1
        elif target_idx <= self.active_tab_idx < source_idx:
            self.active_tab_idx += 1
        
        # Refresh sidebar
        self._update_tab_sidebar()
        
        return True
    
    def _update_tab_count(self):
        """Update the tab count label in URL bar"""
        if self.tab_count_label:
            count = len(self.tabs)
            unloaded = sum(1 for t in self.tabs if t.is_unloaded)
            if unloaded > 0:
                self.tab_count_label.set_text(f"{count} ({unloaded}z)")
            else:
                self.tab_count_label.set_text(str(count))
    
    def _start_tab_unload_monitor(self):
        """Start monitoring tabs for inactivity and unload them"""
        # Check every 30 seconds
        self._tab_unload_timeout = GLib.timeout_add_seconds(30, self._check_tab_unload)
        
    def _stop_tab_unload_monitor(self):
        """Stop the tab unload monitor"""
        if self._tab_unload_timeout:
            GLib.source_remove(self._tab_unload_timeout)
            self._tab_unload_timeout = None
    
    def _check_tab_unload(self) -> bool:
        """Check for inactive tabs and unload them"""
        now = time.time()
        unload_threshold = self._unload_after_seconds
        
        for i, tab in enumerate(self.tabs):
            # Skip active tab and already unloaded tabs
            if i == self.active_tab_idx or tab.is_unloaded:
                continue
                
            inactive_time = now - tab.last_active
            if inactive_time > unload_threshold:
                self._unload_tab(tab)
                
        return True  # Continue monitoring
    
    def _unload_tab(self, tab: Tab):
        """Unload a tab to save memory"""
        if tab.is_unloaded:
            return
            
        # Save scroll position
        tab.webview.evaluate_javascript(
            "window.scrollY",
            -1, None, None, None,
            lambda src, result: self._save_scroll_position(tab, src, result)
        )
        
        # Load blank page to free memory
        tab.webview.load_uri("about:blank")
        tab.is_unloaded = True
        
        self._update_tab_sidebar()
        
    def _save_scroll_position(self, tab: Tab, source, result):
        """Save scroll position from JS callback"""
        try:
            js_result = source.evaluate_javascript_finish(result)
            if js_result:
                tab.scroll_position = int(js_result.to_double())
        except:
            pass
    
    def _reload_unloaded_tab(self, tab: Tab):
        """Reload a previously unloaded tab"""
        if not tab.is_unloaded:
            return
            
        tab.is_unloaded = False
        if tab.url and tab.url != "about:blank":
            tab.webview.load_uri(tab.url)
            
            # Restore scroll position after load - use one-shot handler ID to disconnect
            if tab.scroll_position > 0:
                def restore_scroll(webview, load_event, t=tab):
                    if load_event == WebKit.LoadEvent.FINISHED and t.scroll_position > 0:
                        webview.evaluate_javascript(
                            f"window.scrollTo(0, {t.scroll_position})",
                            -1, None, None, None, None, None
                        )
                        scroll_pos = t.scroll_position
                        t.scroll_position = 0
                        # Disconnect this handler - we use the handler_id stored on the tab
                        if hasattr(t, '_scroll_restore_handler') and t._scroll_restore_handler:
                            try:
                                webview.disconnect(t._scroll_restore_handler)
                            except:
                                pass
                            t._scroll_restore_handler = None
                
                # Store handler ID so we can disconnect it
                tab._scroll_restore_handler = tab.webview.connect('load-changed', restore_scroll)
        
        self._update_tab_sidebar()
    
    def _on_download_started(self, session, download: WebKit.Download):
        """Handle a new download"""
        self.download_manager.handle_download(download)
        
    def _on_download_progress(self, info: DownloadInfo):
        """Handle download progress update"""
        # Notification widget handles display
        pass
        
    def _on_download_complete(self, info: DownloadInfo):
        """Handle download completion"""
        print(f"Download complete: {info.filename}")
        
    def _on_download_failed(self, info: DownloadInfo):
        """Handle download failure"""
        print(f"Download failed: {info.filename} - {info.error_message}")
    
    def _restore_session(self):
        """Restore session from disk on startup"""
        session_file = Path.home() / ".config" / "ryxsurf" / "sessions" / f"{self.current_session}.json"
        if not session_file.exists():
            return
            
        try:
            session_data = json.loads(session_file.read_text())
            
            for tab_data in session_data.get("tabs", []):
                url = tab_data.get("url", "about:blank")
                # Create tab but don't load yet (lazy loading)
                webview = WebKit.WebView()
                
                # Apply WebView settings
                settings = webview.get_settings()
                settings.set_enable_javascript(True)
                settings.set_hardware_acceleration_policy(WebKit.HardwareAccelerationPolicy.ALWAYS)
                settings.set_enable_webgl(True)
                settings.set_enable_smooth_scrolling(self.settings.get("smooth_scrolling", True))
                settings.set_enable_page_cache(True)
                
                tab = Tab(
                    id=len(self.tabs),
                    webview=webview,
                    title=tab_data.get("title", "New Tab"),
                    url=url,
                    is_unloaded=True,  # Start unloaded for memory efficiency
                    last_active=time.time(),
                    zoom_level=tab_data.get("zoom_level", 1.0)
                )
                
                # Connect signals
                webview.connect('notify::title', lambda w, pspec, t=tab: self._on_title_change(t))
                webview.connect('notify::uri', lambda w, pspec, t=tab: self._on_uri_change(t))
                webview.connect('load-changed', lambda w, e, t=tab: self._on_load_changed(w, e, t))
                webview.connect('load-failed', self._on_load_failed)
                
                # Connect download handler
                network_session = webview.get_network_session()
                network_session.connect('download-started', self._on_download_started)
                
                # Setup context menu handler
                if self.context_menu_handler:
                    self.context_menu_handler.setup_webview(webview)
                
                self.tabs.append(tab)
                
            # Switch to active tab and load it
            active_idx = session_data.get("active_tab", 0)
            if 0 <= active_idx < len(self.tabs):
                self.active_tab_idx = active_idx
                # Load the active tab
                if self.tabs:
                    tab = self.tabs[active_idx]
                    tab.is_unloaded = False
                    if tab.url and tab.url != "about:blank":
                        tab.webview.load_uri(tab.url)
                    # CRITICAL: Add webview to content box!
                    self._update_content_view()
                        
            self._update_tab_sidebar()
            
        except Exception as e:
            print(f"Failed to restore session: {e}")
    
    def _navigate_current(self, url: str):
        """Navigate the current tab to a URL"""
        log.info(f"_navigate_current called: url={url}, tabs={len(self.tabs) if self.tabs else 0}")
        if not self.tabs:
            log.warning("No tabs to navigate!")
            return
        
        tab = self.tabs[self.active_tab_idx]
        log.info(f"Navigating tab {self.active_tab_idx} to {url}")
        tab.url = url
        tab.webview.load_uri(url)
        
        # Update URL bar
        if self.url_entry:
            self.url_entry.set_text(url)
    
    def _on_load_changed(self, webview, load_event, tab: Tab = None):
        """Handle page load state changes"""
        # Only log significant events to reduce spam
        if load_event == WebKit.LoadEvent.STARTED:
            # Page started loading - update title immediately
            uri = webview.get_uri()
            if uri and tab:
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(uri)
                    tab.title = f"Loading {parsed.netloc}..." if parsed.netloc else "Loading..."
                except:
                    tab.title = "Loading..."
                self._update_tab_sidebar()
                self._update_window_title()
        elif load_event == WebKit.LoadEvent.REDIRECTED:
            # Handle redirects - update URL
            uri = webview.get_uri()
            if uri and tab:
                tab.url = uri
        elif load_event == WebKit.LoadEvent.COMMITTED:
            # Page content started arriving - try to get real title
            title = webview.get_title()
            if title and tab:
                tab.title = title
                self._update_tab_sidebar()
                self._update_window_title()
        elif load_event == WebKit.LoadEvent.FINISHED:
            # Update URL bar and title when page finishes loading
            uri = webview.get_uri()
            title = webview.get_title()
            
            if tab:
                tab.title = title or tab.title
                tab.url = uri or tab.url
                tab.is_loaded = True
                tab.last_active = time.time()  # Update activity time
                self._update_tab_sidebar()
                self._update_window_title()
                
                # Apply per-site zoom
                saved_zoom = self._get_site_zoom(uri)
                if saved_zoom != 1.0:
                    tab.zoom_level = saved_zoom
                    webview.set_zoom_level(saved_zoom)
                
                # Add to history
                if uri and not uri.startswith("about:"):
                    self.history_manager.add_visit(uri, title or "")
                    
                # Inject user scripts
                if hasattr(self, 'userscript_manager') and uri:
                    self.userscript_manager.inject_user_scripts(webview, uri, "document-idle")
                
                # Inject dark mode preference CSS
                self._inject_dark_mode_css(webview)
            
            if uri and self.url_entry:
                # Only update if this is the active tab's webview
                if self.tabs and self.tabs[self.active_tab_idx].webview == webview:
                    self.url_entry.set_text(uri)
            
            # Schedule URL bar auto-hide after load
            if self.settings.get("url_bar_auto_hide", True):
                self._schedule_url_bar_hide()
    
    def _inject_dark_mode_css(self, webview):
        """Inject CSS to enforce dark mode on pages that don't support it natively"""
        # Check if dark mode enforcement is enabled
        enforce_dark = self.settings.get("force_dark_mode", True)
        
        js = f"""
        (function() {{
            // Set color-scheme meta tag if not present
            if (!document.querySelector('meta[name="color-scheme"]')) {{
                var meta = document.createElement('meta');
                meta.name = 'color-scheme';
                meta.content = 'dark light';
                document.head.appendChild(meta);
            }}
            
            // Set color-scheme on html element
            document.documentElement.style.colorScheme = 'dark';
            
            // Aggressive dark mode for sites that don't support it
            var enforceDark = {str(enforce_dark).lower()};
            if (enforceDark) {{
                // Check if page is already dark (bg color check)
                var bg = window.getComputedStyle(document.body).backgroundColor;
                var rgb = bg.match(/\\d+/g);
                if (rgb && rgb.length >= 3) {{
                    var brightness = (parseInt(rgb[0]) + parseInt(rgb[1]) + parseInt(rgb[2])) / 3;
                    // Only inject if background is light (brightness > 128)
                    if (brightness > 128) {{
                        var darkStyle = document.getElementById('ryxsurf-dark-mode');
                        if (!darkStyle) {{
                            darkStyle = document.createElement('style');
                            darkStyle.id = 'ryxsurf-dark-mode';
                            darkStyle.textContent = `
                                html {{
                                    filter: invert(90%) hue-rotate(180deg) !important;
                                }}
                                img, video, picture, canvas, svg, [style*="background-image"] {{
                                    filter: invert(100%) hue-rotate(180deg) !important;
                                }}
                            `;
                            document.head.appendChild(darkStyle);
                        }}
                    }}
                }}
            }}
        }})();
        """
        webview.evaluate_javascript(js, -1, None, None, None, None, None)
    
    def _on_load_failed(self, webview, load_event, failing_uri, error):
        """Handle page load failures with minimal dark error page"""
        print(f"Load failed for {failing_uri}: {error.message if error else 'Unknown error'}")
        error_msg = error.message if error else 'Unknown error'
        error_html = f"""
        <html>
        <head><style>
            body {{ 
                background: #0a0a0c; 
                color: #666; 
                font-family: 'JetBrains Mono', monospace;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
            }}
            h1 {{ color: #ff4444; font-size: 18px; margin-bottom: 20px; }}
            .url {{ color: #444; font-size: 12px; word-break: break-all; max-width: 500px; text-align: center; }}
            .error {{ color: #555; font-size: 11px; margin-top: 10px; }}
            .actions {{ margin-top: 30px; }}
            a {{ 
                color: #7c3aed; 
                text-decoration: none;
                padding: 8px 16px;
                border: 1px solid #7c3aed;
                border-radius: 4px;
                margin: 0 8px;
            }}
            a:hover {{ background: #7c3aed; color: #fff; }}
        </style></head>
        <body>
            <h1>Page failed to load</h1>
            <p class="url">{failing_uri}</p>
            <p class="error">{error_msg}</p>
            <div class="actions">
                <a href="javascript:location.reload()">Retry</a>
                <a href="javascript:history.back()">Back</a>
            </div>
        </body>
        </html>
        """
        webview.load_html(error_html, failing_uri)
        return True
            
    def _scroll(self, down: bool = True):
        """Scroll the current page"""
        if not self.tabs:
            return
        webview = self.tabs[self.active_tab_idx].webview
        direction = 100 if down else -100
        webview.evaluate_javascript(
            f"window.scrollBy(0, {direction})",
            -1, None, None, None, None
        )
        
    def _history_back(self):
        """Go back in history"""
        if self.tabs:
            self.tabs[self.active_tab_idx].webview.go_back()
            
    def _history_forward(self):
        """Go forward in history"""
        if self.tabs:
            self.tabs[self.active_tab_idx].webview.go_forward()
            
    def _focus_url_bar(self):
        """Focus the URL bar for input"""
        log.info("_focus_url_bar called")
        self._show_url_bar(pin=True)
        if self.url_entry:
            log.info("Focusing URL entry...")
            self.url_entry.grab_focus()
            self.url_entry.select_region(0, -1)  # Select all text
        else:
            log.warning("url_entry is None!")
    
    def _update_window_title(self):
        """Update window title with current tab info"""
        if self.tabs and self.window:
            tab = self.tabs[self.active_tab_idx]
            self.window.set_title(f"{tab.title} - RyxSurf")

    def _handle_url_input(self, text: str, input_type):
        """Handle input from URL bar (legacy method)"""
        if input_type == "url":
            url = text if text.startswith('http') else 'https://' + text
            self._navigate_current(url)
        elif input_type == "search":
            query = quote_plus(text)
            self._navigate_current(f'https://google.com/search?q={query}')
        elif input_type == "ai":
            self._handle_ai_command(text)
        
    def _send_to_ai(self, prompt: str) -> str:
        """Send a prompt to the AI and return the response"""
        response = self.ai_client.post(
            self.ai_client.base_url + '/generate',
            json={'prompt': prompt}
        )
        return response.json().get('response', '')

    def _handle_ai_command(self, text: str):
        """Handle AI commands"""
        response = self._send_to_ai(text)
        self._process_ai_response(response)
    def _process_ai_response(self, response: str):
        """Process AI response and display it in the browser"""
        print(response)
    def _show_ai_bar(self):
        """Show AI command bar overlay"""
        # Create overlay if not exists
        if not hasattr(self, 'ai_bar_overlay') or self.ai_bar_overlay is None:
            self._create_ai_bar()
        
        self.ai_bar_overlay.set_visible(True)
        self.ai_bar_entry.grab_focus()
    
    def _create_ai_bar(self):
        """Create the AI command bar overlay"""
        # Overlay container
        self.ai_bar_overlay = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.ai_bar_overlay.set_halign(Gtk.Align.CENTER)
        self.ai_bar_overlay.set_valign(Gtk.Align.START)
        self.ai_bar_overlay.set_margin_top(100)
        self.ai_bar_overlay.add_css_class("ai-bar-overlay")
        
        # Style the overlay
        css = b"""
        .ai-bar-overlay {
            background: rgba(40, 42, 54, 0.95);
            border-radius: 12px;
            padding: 16px;
            min-width: 500px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
            border: 1px solid rgba(189, 147, 249, 0.3);
        }
        .ai-bar-entry {
            background: rgba(68, 71, 90, 0.8);
            border: 1px solid rgba(189, 147, 249, 0.5);
            border-radius: 8px;
            padding: 12px 16px;
            font-size: 16px;
            color: #f8f8f2;
            min-width: 400px;
        }
        .ai-bar-entry:focus {
            border-color: #bd93f9;
            box-shadow: 0 0 8px rgba(189, 147, 249, 0.3);
        }
        .ai-bar-label {
            color: #bd93f9;
            font-size: 12px;
            margin-bottom: 8px;
        }
        .ai-response {
            background: rgba(68, 71, 90, 0.5);
            border-radius: 8px;
            padding: 12px;
            margin-top: 12px;
            color: #f8f8f2;
            font-size: 14px;
            max-height: 300px;
        }
        """
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        # Label
        label = Gtk.Label(label="🤖 AI Command (Esc to close)")
        label.add_css_class("ai-bar-label")
        self.ai_bar_overlay.append(label)
        
        # Entry
        self.ai_bar_entry = Gtk.Entry()
        self.ai_bar_entry.add_css_class("ai-bar-entry")
        self.ai_bar_entry.set_placeholder_text("summarize this page, click login, dismiss popup...")
        self.ai_bar_overlay.append(self.ai_bar_entry)
        
        # Response area
        self.ai_response_label = Gtk.Label()
        self.ai_response_label.add_css_class("ai-response")
        self.ai_response_label.set_wrap(True)
        self.ai_response_label.set_visible(False)
        self.ai_bar_overlay.append(self.ai_response_label)
        
        # Connect signals
        self.ai_bar_entry.connect("activate", self._on_ai_bar_activate)
        
        # Add key handler for Escape
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_ai_bar_key)
        self.ai_bar_entry.add_controller(key_controller)
        
        # Add to main overlay
        self.main_overlay.add_overlay(self.ai_bar_overlay)
        self.ai_bar_overlay.set_visible(False)
    
    def _on_ai_bar_key(self, controller, keyval, keycode, state):
        """Handle key presses in AI bar"""
        if keyval == Gdk.KEY_Escape:
            self._hide_ai_bar()
            return True
        return False
    
    def _on_ai_bar_activate(self, entry):
        """Handle AI command submission"""
        command = entry.get_text().strip()
        if not command:
            return
        
        # Show loading
        self.ai_response_label.set_text("🔄 Processing...")
        self.ai_response_label.set_visible(True)
        
        # Process in background
        GLib.idle_add(self._process_ai_command, command)
    
    def _process_ai_command(self, command: str):
        """Process AI command and execute actions"""
        import asyncio
        from ..ai.agent import BrowserAgent, PageContext, ActionExecutor
        
        # Get page context
        current_tab = self.tabs[self.active_tab_idx]
        
        # Create agent with config
        config = type('Config', (), {
            'ai_endpoint': 'http://localhost:8001/v1',
            'ai_model': 'qwen2.5-7b-awq'
        })()
        agent = BrowserAgent(config)
        
        # Simple page context
        page_ctx = PageContext(
            url=current_tab.url,
            title=current_tab.title,
            text_content="",  # Will be filled by JS
            links=[],
            forms=[],
            has_popup=False,
            has_newsletter=False
        )
        
        # Run async in thread
        try:
            loop = asyncio.new_event_loop()
            actions = loop.run_until_complete(agent.process_command(command, page_ctx))
            loop.close()
            
            if actions:
                # Execute first action
                action = actions[0]
                js = ActionExecutor.get_js_for_action(action)
                current_tab.webview.evaluate_javascript(js, -1, None, None, None, None, None)
                
                self.ai_response_label.set_text(f"✅ {action.action_type.value}: {action.target or 'done'}")
            else:
                self.ai_response_label.set_text("❓ Could not understand command")
        except Exception as e:
            self.ai_response_label.set_text(f"❌ Error: {str(e)[:50]}")
        
        # Clear entry
        self.ai_bar_entry.set_text("")
        
        # Auto-hide after 2 seconds
        GLib.timeout_add(2000, self._hide_ai_bar)
        
        return False  # Don't repeat
    
    def _hide_ai_bar(self):
        """Hide AI command bar"""
        if hasattr(self, 'ai_bar_overlay') and self.ai_bar_overlay:
            self.ai_bar_overlay.set_visible(False)
            self.ai_response_label.set_visible(False)
        return False
        
    def _toggle_sidebar(self):
        """Toggle tab sidebar visibility"""
        self.sidebar_visible = not self.sidebar_visible
        self.tab_sidebar.set_visible(self.sidebar_visible)
        
    def _hint_mode(self):
        """Enter hint mode for keyboard link clicking"""
        if not self.tabs:
            return
            
        current_webview = self.tabs[self.active_tab_idx].webview
        hint_injection_js = self.hint_mode.get_hint_injection_js()
        
        # Execute JS and get elements, then show overlays
        current_webview.evaluate_javascript(
            hint_injection_js,
            -1,
            None,
            None,
            None,
            self._on_hints_found,
            None
        )
    
    def _on_hints_found(self, webview, result, user_data):
        """Handle hint elements found by JS"""
        import json
        
        try:
            js_result = webview.evaluate_javascript_finish(result)
            if js_result:
                elements_json = js_result.to_string()
                elements = json.loads(elements_json)
                
                if not elements:
                    return
                
                # Generate labels for elements
                labels = self.hint_mode.generate_labels(len(elements))
                
                # Create hints with labels
                hints = []
                for i, elem in enumerate(elements):
                    if i < len(labels):
                        hints.append({
                            'label': labels[i],
                            'selector': elem.get('selector', ''),
                            'x': elem.get('x', 0),
                            'y': elem.get('y', 0)
                        })
                
                # Store hints for matching
                from ..ui.hints import Hint
                self.hint_mode.hints = [
                    Hint(
                        label=h['label'],
                        selector=h['selector'],
                        element_type='',
                        text='',
                        x=h['x'],
                        y=h['y']
                    ) for h in hints
                ]
                
                # Inject overlay JS
                overlay_js = self.hint_mode.get_overlay_js(hints)
                self.tabs[self.active_tab_idx].webview.evaluate_javascript(
                    overlay_js, -1, None, None, None, None, None
                )
                
                self.hint_mode.active = True
                self.hint_mode.current_input = ""
                
        except Exception as e:
            print(f"Hint mode error: {e}")
    
    def _handle_hint_input(self, char: str):
        """Handle keyboard input during hint mode"""
        if not self.hint_mode.active:
            return False
        
        matching = self.hint_mode.filter_hints(char)
        
        if len(matching) == 1:
            # Found exact match - click it!
            hint = matching[0]
            click_js = self.hint_mode.get_click_js(hint.selector)
            self.tabs[self.active_tab_idx].webview.evaluate_javascript(
                click_js, -1, None, None, None, None, None
            )
            self.hint_mode.reset()
            return True
        elif len(matching) == 0:
            # No match - exit hint mode
            clear_js = self.hint_mode.get_clear_hints_js()
            self.tabs[self.active_tab_idx].webview.evaluate_javascript(
                clear_js, -1, None, None, None, None, None
            )
            self.hint_mode.reset()
            return True
        else:
            # Multiple matches - highlight matching prefix
            # Update overlay to show which hints still match
            return True
        
        return False

    def _summarize_page(self):
        """Get and summarize the page text"""
        current_webview = self.tabs[self.active_tab_idx].webview
        current_webview.run_javascript(
            "document.body.innerText",
            None,
            self._on_get_page_text
        )

    def _dismiss_popup(self):
        """Remove modal/popup elements via JavaScript"""
        if not self.tabs:
            return
        current_webview = self.tabs[self.active_tab_idx].webview
        current_webview.run_javascript(
            """
            const popups = document.querySelectorAll('[class*="popup"], [class*="modal"], [class*="overlay"], [class*="cookie"], [class*="newsletter"]');
            popups.forEach(popup => popup.remove());
            document.body.style.overflow = 'auto'; // Restore body scrolling
            """,
            None,
            None
        )
    
    def _auto_clean_page(self):
        """Aggressive page cleaning - remove all annoyances permanently"""
        if not self.tabs:
            return
        
        tab = self.tabs[self.active_tab_idx]
        
        # Get domain for saving clean rules
        from urllib.parse import urlparse
        domain = urlparse(tab.url).netloc if tab.url else ""
        
        js = """
        (function() {
            // Common annoyance selectors
            const annoyances = [
                // Popups and modals
                '[class*="popup"]', '[class*="modal"]', '[class*="overlay"]',
                '[class*="dialog"]', '[class*="lightbox"]',
                // Cookie banners
                '[class*="cookie"]', '[class*="gdpr"]', '[class*="consent"]',
                '[class*="privacy"]', '#cookie', '.cookie-banner',
                // Newsletter popups
                '[class*="newsletter"]', '[class*="subscribe"]', '[class*="signup"]',
                // Social widgets
                '[class*="social-share"]', '.fb-like', '.twitter-share',
                // Fixed elements that cover content
                '[style*="position: fixed"]',
                // Ads
                '[class*="ad-"]', '[class*="ads-"]', '[id*="google_ads"]',
                '.adsbygoogle', '[class*="advertisement"]',
                // Interstitials
                '[class*="interstitial"]', '[class*="paywall"]'
            ];
            
            let removed = 0;
            annoyances.forEach(sel => {
                try {
                    document.querySelectorAll(sel).forEach(el => {
                        // Don't remove if it's the main content
                        if (!el.matches('main, article, #content, .content, .post, .article')) {
                            el.remove();
                            removed++;
                        }
                    });
                } catch(e) {}
            });
            
            // Restore scrolling
            document.body.style.overflow = 'auto';
            document.documentElement.style.overflow = 'auto';
            
            // Remove blur effects
            document.querySelectorAll('[style*="blur"]').forEach(el => {
                el.style.filter = 'none';
            });
            
            console.log('RyxSurf: Removed ' + removed + ' annoyances');
            return removed;
        })();
        """
        
        def on_clean_done(webview, result):
            try:
                js_result = webview.evaluate_javascript_finish(result)
                if js_result:
                    count = int(js_result.to_double())
                    print(f"Auto-clean: Removed {count} annoyances from {domain}")
            except Exception as e:
                print(f"Auto-clean error: {e}")
        
        tab.webview.evaluate_javascript(js, -1, None, None, None, on_clean_done)

    def _on_get_page_text(self, result, error):
        if error:
            print(f"Error getting page text: {error}")
            return
        page_text = result.get_string()
        
        # Summarize with AI
        GLib.idle_add(self._summarize_with_ai, page_text)
    
    def _summarize_with_ai(self, page_text: str):
        """Send page text to AI for summarization"""
        import aiohttp
        import asyncio
        
        # Truncate to fit context
        max_chars = 8000
        if len(page_text) > max_chars:
            page_text = page_text[:max_chars] + "..."
        
        async def get_summary():
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8001/v1/chat/completions",
                    json={
                        "model": "qwen2.5-7b-awq",
                        "messages": [
                            {"role": "system", "content": "You are a concise summarizer. Summarize the following web page content in 3-5 bullet points. Be brief."},
                            {"role": "user", "content": f"Summarize this page:\n\n{page_text}"}
                        ],
                        "max_tokens": 300,
                        "temperature": 0.3
                    }
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"]
                    return "Failed to get summary"
        
        try:
            loop = asyncio.new_event_loop()
            summary = loop.run_until_complete(get_summary())
            loop.close()
            
            # Show summary in overlay
            self._show_summary_overlay(summary)
        except Exception as e:
            self._show_summary_overlay(f"Error: {str(e)}")
        
        return False
    
    def _show_summary_overlay(self, summary: str):
        """Show summary in a nice overlay"""
        # Create overlay if needed
        if not hasattr(self, 'summary_overlay') or self.summary_overlay is None:
            self._create_summary_overlay()
        
        self.summary_label.set_text(summary)
        self.summary_overlay.set_visible(True)
        
        # Auto-hide after 10 seconds
        GLib.timeout_add(10000, lambda: self.summary_overlay.set_visible(False) or False)
    
    def _create_summary_overlay(self):
        """Create summary overlay"""
        self.summary_overlay = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.summary_overlay.set_halign(Gtk.Align.END)
        self.summary_overlay.set_valign(Gtk.Align.END)
        self.summary_overlay.set_margin_end(20)
        self.summary_overlay.set_margin_bottom(20)
        
        # Style
        css = b"""
        .summary-overlay {
            background: rgba(14, 14, 18, 0.95);
            border-radius: 8px;
            padding: 12px;
            min-width: 300px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
            border: 1px solid #1a1a1f;
        }
        .summary-title {
            color: #7c3aed;
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 6px;
        }
        .summary-text {
            color: #f8f8f2;
            font-size: 13px;
            line-height: 1.5;
        }
        """
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        self.summary_overlay.add_css_class("summary-overlay")
        
        title = Gtk.Label(label="📝 Page Summary")
        title.add_css_class("summary-title")
        title.set_halign(Gtk.Align.START)
        self.summary_overlay.append(title)
        
        self.summary_label = Gtk.Label()
        self.summary_label.add_css_class("summary-text")
        self.summary_label.set_wrap(True)
        self.summary_label.set_max_width_chars(50)
        self.summary_label.set_halign(Gtk.Align.START)
        self.summary_overlay.append(self.summary_label)
        
        self.main_overlay.add_overlay(self.summary_overlay)
        self.summary_overlay.set_visible(False)
    
    def _close_overlays(self):
        """Close any open overlays/bars"""
        # Also dismiss AI overlays
        self._ai_dismiss()
    
    def _reload(self):
        """Reload current page"""
        if self.tabs:
            self.tabs[self.active_tab_idx].webview.reload()
    
    def _hard_reload(self):
        """Hard reload (bypass cache)"""
        if self.tabs:
            self.tabs[self.active_tab_idx].webview.reload_bypass_cache()
    
    def _next_tab(self):
        """Switch to next tab"""
        if self.tabs:
            next_idx = (self.active_tab_idx + 1) % len(self.tabs)
            self._switch_to_tab(next_idx)
    
    def _prev_tab(self):
        """Switch to previous tab"""
        if self.tabs:
            prev_idx = (self.active_tab_idx - 1) % len(self.tabs)
            self._switch_to_tab(prev_idx)
    
    def _toggle_ai_sidebar(self):
        """Toggle AI sidebar visibility"""
        visible = self.ai_sidebar.get_visible()
        self.ai_sidebar.set_visible(not visible)
        
        if not visible:
            # Add to content box if not already there
            if not self.ai_sidebar.get_parent():
                self.content_box.append(self.ai_sidebar)
        else:
            # Remove from content box
            if self.ai_sidebar.get_parent():
                self.content_box.remove(self.ai_sidebar)
    
    def _is_focused_on_input(self) -> bool:
        """Check if focus is on an input element in the webview"""
        # For now, return False - proper implementation would check via JS
        # This is a placeholder that allows 'F' to work for link hints
        return False
        
    def _ai_summarize(self):
        """AI: Summarize current page"""
        self._summarize_page()
        
    def _ai_dismiss(self):
        """AI: Dismiss popup/overlay - Enhanced with more selectors"""
        if self.tabs:
            webview = self.tabs[self.active_tab_idx].webview
            # Comprehensive overlay removal script
            webview.evaluate_javascript("""
                (function() {
                    let removed = 0;
                    
                    // Common overlay selectors
                    const selectors = [
                        '[class*="popup"]', '[class*="modal"]', '[class*="overlay"]',
                        '[class*="dialog"]', '[id*="popup"]', '[id*="modal"]',
                        '[class*="newsletter"]', '[class*="subscribe"]',
                        '[class*="cookie"]', '[class*="consent"]', '[class*="gdpr"]',
                        '[class*="paywall"]', '[role="dialog"]', '[aria-modal="true"]',
                        '[class*="banner"]', '[class*="notification"]'
                    ];
                    
                    selectors.forEach(sel => {
                        document.querySelectorAll(sel).forEach(el => {
                            const style = window.getComputedStyle(el);
                            if (style.position === 'fixed' || style.position === 'absolute') {
                                const rect = el.getBoundingClientRect();
                                if (rect.width > 100 && rect.height > 100) {
                                    el.remove();
                                    removed++;
                                }
                            }
                        });
                    });
                    
                    // Remove backdrop elements
                    document.querySelectorAll('[class*="backdrop"], [class*="overlay-bg"]').forEach(el => {
                        el.remove();
                        removed++;
                    });
                    
                    // Re-enable scrolling
                    document.body.style.overflow = 'auto';
                    document.body.style.position = '';
                    document.documentElement.style.overflow = 'auto';
                    
                    // Remove blur effects
                    document.querySelectorAll('[style*="blur"]').forEach(el => {
                        el.style.filter = '';
                    });
                    
                    console.log('Removed ' + removed + ' overlays');
                })();
            """, -1, None, None, None, None, None)
        
    def _switch_session(self):
        """Switch to a different session with UI"""
        self._show_session_switcher()
    
    def _show_session_switcher(self):
        """Show session switcher overlay"""
        if not hasattr(self, 'session_switcher') or self.session_switcher is None:
            self._create_session_switcher()
        
        # Load available sessions
        self._load_session_list()
        self.session_switcher.set_visible(True)
    
    def _create_session_switcher(self):
        """Create session switcher UI"""
        self.session_switcher = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.session_switcher.set_halign(Gtk.Align.CENTER)
        self.session_switcher.set_valign(Gtk.Align.CENTER)
        
        css = b"""
        .session-switcher {
            background: rgba(40, 42, 54, 0.98);
            border-radius: 12px;
            padding: 20px;
            min-width: 300px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.6);
            border: 1px solid rgba(255, 121, 198, 0.3);
        }
        .session-title {
            color: #ff79c6;
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 12px;
        }
        .session-item {
            background: rgba(68, 71, 90, 0.6);
            border-radius: 8px;
            padding: 12px;
            margin: 4px 0;
            color: #f8f8f2;
        }
        .session-item:hover {
            background: rgba(189, 147, 249, 0.3);
        }
        """
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        self.session_switcher.add_css_class("session-switcher")
        
        title = Gtk.Label(label="📁 Switch Session")
        title.add_css_class("session-title")
        self.session_switcher.append(title)
        
        # Session list
        self.session_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.session_switcher.append(self.session_list)
        
        # New session button
        new_btn = Gtk.Button(label="+ New Session")
        new_btn.connect("clicked", self._on_new_session)
        self.session_switcher.append(new_btn)
        
        # Key handler
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_session_key)
        self.session_switcher.add_controller(key_controller)
        
        self.main_overlay.add_overlay(self.session_switcher)
        self.session_switcher.set_visible(False)
    
    def _load_session_list(self):
        """Load and display available sessions"""
        # Clear existing
        while child := self.session_list.get_first_child():
            self.session_list.remove(child)
        
        # Load sessions from disk
        session_dir = Path.home() / ".config" / "ryxsurf" / "sessions"
        if session_dir.exists():
            for session_file in session_dir.glob("*.json"):
                name = session_file.stem
                btn = Gtk.Button(label=name)
                btn.add_css_class("session-item")
                btn.connect("clicked", lambda b, n=name: self._load_session(n))
                self.session_list.append(btn)
    
    def _on_session_key(self, controller, keyval, keycode, state):
        """Handle keys in session switcher"""
        if keyval == Gdk.KEY_Escape:
            self.session_switcher.set_visible(False)
            return True
        return False
    
    def _on_new_session(self, button):
        """Create new session"""
        self._save_current_session("new_session")
        self.session_switcher.set_visible(False)
        
    def _on_title_change(self, tab: Tab):
        """Handle page title change"""
        new_title = tab.webview.get_title()
        if new_title:
            tab.title = new_title
            self._update_tab_sidebar()
            self._update_window_title()
        
    def _on_uri_change(self, tab: Tab):
        """Handle URL change"""
        new_uri = tab.webview.get_uri()
        if new_uri:
            tab.url = new_uri
            # Update URL bar if this is the active tab
            if self.tabs and self.tabs[self.active_tab_idx] == tab and self.url_entry:
                self.url_entry.set_text(new_uri)
                # Update security icon
                self._update_security_icon(new_uri)
                # Update bookmark icon
                self._update_bookmark_icon(new_uri)
    
    def _show_settings(self):
        """Show settings dialog"""
        if self.settings_dialog and self.settings_dialog.get_visible():
            self.settings_dialog.close()
            return
        
        # Create settings dialog
        self.settings_dialog = Gtk.Window(title="RyxSurf Settings")
        self.settings_dialog.set_transient_for(self.window)
        self.settings_dialog.set_modal(True)
        self.settings_dialog.set_default_size(450, 400)
        self.settings_dialog.add_css_class("settings-dialog")
        
        # Main content box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        
        # Header
        header = Gtk.Label(label="⚙️ Settings")
        header.add_css_class("settings-header")
        header.set_halign(Gtk.Align.START)
        main_box.append(header)
        
        # Homepage setting
        homepage_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        homepage_label = Gtk.Label(label="Homepage:")
        homepage_label.set_halign(Gtk.Align.START)
        homepage_label.set_hexpand(False)
        homepage_entry = Gtk.Entry()
        homepage_entry.set_text(self.settings.get("homepage", "https://www.google.com"))
        homepage_entry.set_hexpand(True)
        homepage_box.append(homepage_label)
        homepage_box.append(homepage_entry)
        main_box.append(homepage_box)
        
        # Auto-hide URL bar toggle
        autohide_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        autohide_label = Gtk.Label(label="Auto-hide URL bar:")
        autohide_label.set_halign(Gtk.Align.START)
        autohide_label.set_hexpand(True)
        autohide_switch = Gtk.Switch()
        autohide_switch.set_active(self.settings.get("url_bar_auto_hide", True))
        autohide_box.append(autohide_label)
        autohide_box.append(autohide_switch)
        main_box.append(autohide_box)
        
        # Smooth scrolling toggle
        scroll_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        scroll_label = Gtk.Label(label="Smooth scrolling:")
        scroll_label.set_halign(Gtk.Align.START)
        scroll_label.set_hexpand(True)
        scroll_switch = Gtk.Switch()
        scroll_switch.set_active(self.settings.get("smooth_scrolling", True))
        scroll_box.append(scroll_label)
        scroll_box.append(scroll_switch)
        main_box.append(scroll_box)
        
        # GPU acceleration toggle
        gpu_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        gpu_label = Gtk.Label(label="GPU acceleration:")
        gpu_label.set_halign(Gtk.Align.START)
        gpu_label.set_hexpand(True)
        gpu_switch = Gtk.Switch()
        gpu_switch.set_active(self.settings.get("gpu_acceleration", True))
        gpu_box.append(gpu_label)
        gpu_box.append(gpu_switch)
        main_box.append(gpu_box)
        
        # Separator
        sep1 = Gtk.Separator()
        sep1.set_margin_top(8)
        sep1.set_margin_bottom(8)
        main_box.append(sep1)
        
        # UI Section header
        ui_header = Gtk.Label(label="UI Elements")
        ui_header.add_css_class("settings-section")
        ui_header.set_halign(Gtk.Align.START)
        main_box.append(ui_header)
        
        # Show bookmarks bar toggle
        bookmarks_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        bookmarks_label = Gtk.Label(label="Show bookmarks bar:")
        bookmarks_label.set_halign(Gtk.Align.START)
        bookmarks_label.set_hexpand(True)
        bookmarks_switch = Gtk.Switch()
        bookmarks_switch.set_active(self.settings.get("show_bookmarks_bar", False))
        bookmarks_box.append(bookmarks_label)
        bookmarks_box.append(bookmarks_switch)
        main_box.append(bookmarks_box)
        
        # Show download notifications toggle
        downloads_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        downloads_label = Gtk.Label(label="Download notifications:")
        downloads_label.set_halign(Gtk.Align.START)
        downloads_label.set_hexpand(True)
        downloads_switch = Gtk.Switch()
        downloads_switch.set_active(self.settings.get("show_download_notifications", True))
        downloads_box.append(downloads_label)
        downloads_box.append(downloads_switch)
        main_box.append(downloads_box)
        
        # Separator
        sep2 = Gtk.Separator()
        sep2.set_margin_top(8)
        sep2.set_margin_bottom(8)
        main_box.append(sep2)
        
        # Privacy Section header
        privacy_header = Gtk.Label(label="Privacy & Data")
        privacy_header.add_css_class("settings-section")
        privacy_header.set_halign(Gtk.Align.START)
        main_box.append(privacy_header)
        
        # Block trackers toggle
        tracker_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        tracker_label = Gtk.Label(label="Block known trackers:")
        tracker_label.set_halign(Gtk.Align.START)
        tracker_label.set_hexpand(True)
        tracker_switch = Gtk.Switch()
        tracker_switch.set_active(self.settings.get("block_trackers", True))
        tracker_box.append(tracker_label)
        tracker_box.append(tracker_switch)
        main_box.append(tracker_box)
        
        # Clear data buttons
        clear_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        clear_cache_btn = Gtk.Button(label="Clear Cache")
        clear_cache_btn.connect("clicked", lambda _: self._clear_cache("soft"))
        clear_box.append(clear_cache_btn)
        
        clear_all_btn = Gtk.Button(label="Clear All Data")
        clear_all_btn.add_css_class("destructive-action")
        clear_all_btn.connect("clicked", lambda _: self._clear_cache("hard"))
        clear_box.append(clear_all_btn)
        
        main_box.append(clear_box)
        
        # Save button
        save_btn = Gtk.Button(label="Save Settings")
        save_btn.set_margin_top(20)
        
        def on_save(_):
            self.settings["homepage"] = homepage_entry.get_text()
            self.settings["url_bar_auto_hide"] = autohide_switch.get_active()
            self.settings["smooth_scrolling"] = scroll_switch.get_active()
            self.settings["gpu_acceleration"] = gpu_switch.get_active()
            self.settings["show_bookmarks_bar"] = bookmarks_switch.get_active()
            self.settings["show_download_notifications"] = downloads_switch.get_active()
            self.settings["block_trackers"] = tracker_switch.get_active()
            save_settings(self.settings)
            self.settings_dialog.close()
        
        save_btn.connect("clicked", on_save)
        main_box.append(save_btn)
        
        # Close on Escape
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", lambda c, k, kc, s: 
            self.settings_dialog.close() if Gdk.keyval_name(k) == "Escape" else None)
        self.settings_dialog.add_controller(key_controller)
        
        self.settings_dialog.set_child(main_box)
        self.settings_dialog.present()
        
    def _load_session(self, session_name: str):
        """Load a session from a JSON file and recreate tabs"""
        session_file = Path.home() / ".config" / "ryxsurf" / "sessions" / f"{session_name}.json"
        if session_file.exists():
            session_data = json.loads(session_file.read_text())
            self.current_session = session_data["name"]
            self.tabs = []
            for tab_data in session_data["tabs"]:
                webview = WebKit.WebView()
                
                # Apply WebView settings
                settings = webview.get_settings()
                settings.set_enable_javascript(True)
                settings.set_hardware_acceleration_policy(WebKit.HardwareAccelerationPolicy.ALWAYS)
                settings.set_enable_webgl(True)
                settings.set_enable_smooth_scrolling(self.settings.get("smooth_scrolling", True))
                
                tab = Tab(
                    id=len(self.tabs),
                    webview=webview,
                    title=tab_data["title"],
                    url=tab_data["url"],
                    zoom_level=tab_data.get("zoom_level", 1.0)
                )
                
                # Connect signals with proper captured tab reference
                webview.connect('notify::title', lambda w, pspec, t=tab: self._on_title_change(t))
                webview.connect('notify::uri', lambda w, pspec, t=tab: self._on_uri_change(t))
                webview.connect('load-changed', lambda w, e, t=tab: self._on_load_changed(w, e, t))
                webview.connect('load-failed', self._on_load_failed)
                
                # Setup context menu handler
                if self.context_menu_handler:
                    self.context_menu_handler.setup_webview(webview)
                
                self.tabs.append(tab)
                
                # Load URL after tab is added
                webview.load_uri(tab_data["url"])
                
                # Apply zoom level
                webview.set_zoom_level(tab.zoom_level)
            
            self.active_tab_idx = session_data["active_tab"]
            self._switch_to_tab(self.active_tab_idx)
            self._update_window_title()

    def shutdown(self):
        """Clean shutdown"""
        # Save session
        self._save_session()
        # Stop monitors
        self._stop_tab_unload_monitor()
        # Close history database
        self.history_manager.close()
        if self.app:
            self.app.quit()
            
    def _save_session(self):
        """Save current session to disk with full tab state"""
        session_data = {
            "name": self.current_session,
            "tabs": [
                {
                    "url": t.url,
                    "title": t.title,
                    "scroll_position": t.scroll_position,
                    "is_unloaded": t.is_unloaded,
                    "zoom_level": t.zoom_level
                }
                for t in self.tabs
            ],
            "active_tab": self.active_tab_idx
        }
        
        session_file = Path.home() / ".config" / "ryxsurf" / "sessions" / f"{self.current_session}.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(json.dumps(session_data, indent=2))

    # ==================== NEW FEATURES ====================
    
    def _show_find_bar(self):
        """Show the find-in-page bar"""
        if self.find_bar:
            self.find_bar.show()
            
    def _toggle_bookmarks_bar(self):
        """Toggle bookmarks bar visibility"""
        if self.bookmarks_bar:
            self.bookmarks_bar.toggle()
            self.bookmarks_visible = self.bookmarks_bar.get_visible()
            
    def _toggle_bookmark(self):
        """Toggle bookmark for current page"""
        if not self.tabs:
            return
            
        tab = self.tabs[self.active_tab_idx]
        if not tab.url or tab.url == "about:blank":
            return
            
        is_bookmarked, bookmark = self.bookmark_manager.toggle(
            url=tab.url,
            title=tab.title
        )
        
        self._update_bookmark_icon(tab.url)
        
        # Refresh bookmarks bar if visible
        if self.bookmarks_bar and self.bookmarks_bar.get_visible():
            self.bookmarks_bar.refresh()
            
    def _update_bookmark_icon(self, url: str):
        """Update bookmark icon based on whether URL is bookmarked"""
        if not self.bookmark_icon:
            return
            
        if url and self.bookmark_manager.is_bookmarked(url):
            self.bookmark_icon.set_label("★")
            self.bookmark_icon.add_css_class("bookmarked")
            self.bookmark_icon.set_tooltip_text("Remove bookmark (Ctrl+D)")
        else:
            self.bookmark_icon.set_label("☆")
            self.bookmark_icon.remove_css_class("bookmarked")
            self.bookmark_icon.set_tooltip_text("Bookmark this page (Ctrl+D)")
            
    def _update_security_icon(self, url: str):
        """Update security icon based on URL protocol"""
        if not self.security_icon:
            return
            
        if not url:
            self.security_icon.set_label("")
            self.security_icon.set_tooltip_text("")
            return
            
        if url.startswith("https://"):
            self.security_icon.set_label("🔒")
            self.security_icon.set_tooltip_text("Secure connection (HTTPS)")
            self.security_icon.add_css_class("secure")
            self.security_icon.remove_css_class("insecure")
        elif url.startswith("http://"):
            self.security_icon.set_label("⚠️")
            self.security_icon.set_tooltip_text("Not secure (HTTP)")
            self.security_icon.add_css_class("insecure")
            self.security_icon.remove_css_class("secure")
        elif url.startswith("file://"):
            self.security_icon.set_label("📁")
            self.security_icon.set_tooltip_text("Local file")
            self.security_icon.remove_css_class("secure")
            self.security_icon.remove_css_class("insecure")
        else:
            self.security_icon.set_label("")
            self.security_icon.set_tooltip_text("")
            
    def _zoom_in(self):
        """Zoom in on current tab and save per-site preference"""
        if not self.tabs:
            return
            
        tab = self.tabs[self.active_tab_idx]
        tab.zoom_level = min(tab.zoom_level + 0.1, 3.0)  # Max 300%
        tab.webview.set_zoom_level(tab.zoom_level)
        self._save_site_zoom(tab.url, tab.zoom_level)
        
    def _zoom_out(self):
        """Zoom out on current tab and save per-site preference"""
        if not self.tabs:
            return
            
        tab = self.tabs[self.active_tab_idx]
        tab.zoom_level = max(tab.zoom_level - 0.1, 0.3)  # Min 30%
        tab.webview.set_zoom_level(tab.zoom_level)
        self._save_site_zoom(tab.url, tab.zoom_level)
        
    def _zoom_reset(self):
        """Reset zoom to 100% on current tab"""
        if not self.tabs:
            return
            
        tab = self.tabs[self.active_tab_idx]
        tab.zoom_level = 1.0
        tab.webview.set_zoom_level(1.0)
        self._save_site_zoom(tab.url, 1.0)
    
    def _save_site_zoom(self, url: str, zoom: float):
        """Save zoom level for a site"""
        if not url:
            return
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        if not domain:
            return
        
        zoom_file = Path.home() / ".config" / "ryxsurf" / "site_zoom.json"
        zoom_data = {}
        if zoom_file.exists():
            try:
                zoom_data = json.loads(zoom_file.read_text())
            except:
                pass
        
        if zoom == 1.0 and domain in zoom_data:
            del zoom_data[domain]  # Remove default zoom
        elif zoom != 1.0:
            zoom_data[domain] = zoom
        
        zoom_file.parent.mkdir(parents=True, exist_ok=True)
        zoom_file.write_text(json.dumps(zoom_data, indent=2))
    
    def _get_site_zoom(self, url: str) -> float:
        """Get saved zoom level for a site"""
        if not url:
            return 1.0
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        if not domain:
            return 1.0
        
        zoom_file = Path.home() / ".config" / "ryxsurf" / "site_zoom.json"
        if zoom_file.exists():
            try:
                zoom_data = json.loads(zoom_file.read_text())
                return zoom_data.get(domain, 1.0)
            except:
                pass
        return 1.0
    
    def _toggle_reader_mode(self):
        """Toggle reader mode - clean article view"""
        if not self.tabs:
            return
        
        tab = self.tabs[self.active_tab_idx]
        
        # JavaScript to extract and display article content
        js = """
        (function() {
            if (document.body.classList.contains('ryxsurf-reader')) {
                // Exit reader mode
                location.reload();
                return;
            }
            
            // Simple reader mode implementation
            let article = document.querySelector('article') || 
                         document.querySelector('[role="main"]') ||
                         document.querySelector('main') ||
                         document.querySelector('.post-content') ||
                         document.querySelector('.article-content');
            
            if (!article) {
                // Fallback: use body content
                article = document.body;
            }
            
            let title = document.title;
            let content = article.innerHTML;
            
            document.body.innerHTML = `
                <style>
                    body.ryxsurf-reader {
                        background: #0a0a0c !important;
                        color: #ccc !important;
                        font-family: Georgia, serif !important;
                        font-size: 18px !important;
                        line-height: 1.8 !important;
                        max-width: 700px !important;
                        margin: 40px auto !important;
                        padding: 20px !important;
                    }
                    body.ryxsurf-reader h1, body.ryxsurf-reader h2 {
                        color: #fff !important;
                    }
                    body.ryxsurf-reader a {
                        color: #7c3aed !important;
                    }
                    body.ryxsurf-reader img {
                        max-width: 100% !important;
                        height: auto !important;
                    }
                </style>
                <h1>${title}</h1>
                ${content}
            `;
            document.body.classList.add('ryxsurf-reader');
        })();
        """
        tab.webview.evaluate_javascript(js, -1, None, None, None, None, None)
    
    def _take_screenshot(self):
        """Take a screenshot of the current page"""
        if not self.tabs:
            return
        
        tab = self.tabs[self.active_tab_idx]
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = Path.home() / "Pictures" / f"ryxsurf_{timestamp}.png"
        
        # Ensure directory exists
        filename.parent.mkdir(parents=True, exist_ok=True)
        
        def on_snapshot_ready(webview, result):
            try:
                texture = webview.get_snapshot_finish(result)
                if texture:
                    # Save texture to file
                    texture.save_to_png(str(filename))
                    print(f"Screenshot saved: {filename}")
            except Exception as e:
                print(f"Screenshot failed: {e}")
        
        tab.webview.get_snapshot(
            WebKit.SnapshotRegion.VISIBLE,
            WebKit.SnapshotOptions.NONE,
            None,
            on_snapshot_ready
        )
    
    def _toggle_pip(self):
        """Toggle Picture-in-Picture for video on current page"""
        if not self.tabs:
            return
        
        tab = self.tabs[self.active_tab_idx]
        
        # JavaScript to toggle PiP on the first video found
        js = """
        (function() {
            const video = document.querySelector('video');
            if (!video) {
                console.log('No video found');
                return;
            }
            
            if (document.pictureInPictureElement) {
                document.exitPictureInPicture();
            } else if (document.pictureInPictureEnabled) {
                video.requestPictureInPicture().catch(e => console.log(e));
            }
        })();
        """
        tab.webview.evaluate_javascript(js, -1, None, None, None, None, None)
    
    def _copy_url(self):
        """Copy current URL to clipboard"""
        if not self.tabs:
            return
        
        url = self.tabs[self.active_tab_idx].url
        if url:
            clipboard = Gdk.Display.get_default().get_clipboard()
            clipboard.set(url)
            print(f"Copied: {url}")
    
    def _clear_cache(self, level: str = "soft"):
        """Clear browser cache and data
        
        level: "soft" = just cache, "hard" = cache + cookies + history
        """
        context = WebKit.WebContext.get_default()
        data_manager = context.get_website_data_manager()
        
        if level == "soft":
            # Just cache
            types = WebKit.WebsiteDataTypes.DISK_CACHE | WebKit.WebsiteDataTypes.MEMORY_CACHE
            print("Clearing cache...")
        else:
            # Everything
            types = (
                WebKit.WebsiteDataTypes.DISK_CACHE |
                WebKit.WebsiteDataTypes.MEMORY_CACHE |
                WebKit.WebsiteDataTypes.COOKIES |
                WebKit.WebsiteDataTypes.LOCAL_STORAGE |
                WebKit.WebsiteDataTypes.SESSION_STORAGE |
                WebKit.WebsiteDataTypes.INDEXEDDB_DATABASES
            )
            print("Clearing all data...")
        
        data_manager.clear(types, 0, None, None)
        print(f"Cache cleared ({level})")
    
    def _clear_site_data(self):
        """Clear data for current site only"""
        if not self.tabs:
            return
        
        url = self.tabs[self.active_tab_idx].url
        if not url:
            return
        
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        
        context = WebKit.WebContext.get_default()
        data_manager = context.get_website_data_manager()
        
        # Fetch and clear data for this domain
        def on_fetch(dm, result):
            try:
                data_list = dm.fetch_finish(result)
                for data in data_list:
                    if domain in data.get_name():
                        types = data.get_types()
                        dm.remove(types, [data], None, None)
                        print(f"Cleared data for: {domain}")
            except Exception as e:
                print(f"Error clearing site data: {e}")
        
        data_manager.fetch(
            WebKit.WebsiteDataTypes.ALL,
            None,
            on_fetch
        )
    
    def _switch_workspace(self, workspace_id: str):
        """Switch to a different workspace"""
        if workspace_id == self.current_workspace:
            return
        
        # Save current tabs to current workspace
        self.workspace_tabs[self.current_workspace] = self.tabs.copy()
        
        # Update UI
        if hasattr(self, 'workspace_buttons'):
            for ws_id, btn in self.workspace_buttons.items():
                if ws_id == workspace_id:
                    btn.add_css_class("active")
                else:
                    btn.remove_css_class("active")
        
        # Switch workspace
        self.current_workspace = workspace_id
        
        # Load tabs from new workspace
        if self.workspace_tabs[workspace_id]:
            self.tabs = self.workspace_tabs[workspace_id]
            self.active_tab_idx = min(self.active_tab_idx, len(self.tabs) - 1)
            self._switch_to_tab(self.active_tab_idx)
        else:
            # New workspace - create empty tab
            self.tabs = []
            self._new_tab()
        
        self._update_tab_sidebar()
        self._update_window_title()
        
        ws_info = WORKSPACES.get(workspace_id, {})
        print(f"Switched to workspace: {ws_info.get('name', workspace_id)}")
    
    def _quick_escape(self):
        """Hide all tabs and show neutral page (panic button)"""
        # Save current state
        self._escape_backup = {
            'tabs': self.tabs.copy(),
            'active': self.active_tab_idx,
            'workspace': self.current_workspace
        }
        
        # Clear and show neutral tab
        self.tabs = []
        webview = WebKit.WebView()
        self._apply_webview_settings(webview)
        
        # Neutral page
        html = '''<!DOCTYPE html>
<html><head><style>
body { background: #0a0a0c; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
.msg { color: #333; font-size: 11px; font-family: monospace; }
</style></head>
<body><div class="msg">Press Ctrl+Shift+E to restore</div></body></html>'''
        webview.load_html(html, "about:blank")
        
        tab = Tab(
            webview=webview,
            id=str(int(time.time() * 1000)),
            url="about:blank",
            title="New Tab",
            last_active=time.time()
        )
        self.tabs.append(tab)
        self.active_tab_idx = 0
        self._switch_to_tab(0)
        self._update_tab_sidebar()
        self._update_window_title()
    
    def _restore_from_escape(self):
        """Restore tabs after quick escape"""
        if hasattr(self, '_escape_backup') and self._escape_backup:
            self.tabs = self._escape_backup['tabs']
            self.active_tab_idx = self._escape_backup['active']
            self._switch_to_tab(self.active_tab_idx)
            self._update_tab_sidebar()
            self._update_window_title()
            self._escape_backup = None
    
    def _toggle_split_view(self):
        """Toggle split view - show two tabs side by side"""
        if len(self.tabs) < 2:
            print("Need at least 2 tabs for split view")
            return
        
        if hasattr(self, '_split_mode') and self._split_mode:
            # Exit split mode
            self._split_mode = False
            self._switch_to_tab(self.active_tab_idx)
            print("Split view disabled")
        else:
            # Enter split mode - show current tab + next tab
            self._split_mode = True
            
            # Clear content
            while child := self.content_box.get_first_child():
                self.content_box.remove(child)
            
            # Create paned container
            paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
            paned.set_hexpand(True)
            paned.set_vexpand(True)
            
            # Left tab (current)
            left_tab = self.tabs[self.active_tab_idx]
            left_tab.webview.set_hexpand(True)
            left_tab.webview.set_vexpand(True)
            paned.set_start_child(left_tab.webview)
            
            # Right tab (next)
            right_idx = (self.active_tab_idx + 1) % len(self.tabs)
            right_tab = self.tabs[right_idx]
            right_tab.webview.set_hexpand(True)
            right_tab.webview.set_vexpand(True)
            paned.set_end_child(right_tab.webview)
            
            # Set 50/50 split
            paned.set_position(self.window.get_width() // 2)
            
            self.content_box.append(paned)
            print("Split view enabled")
    
    def _hard_reload(self):
        """Hard reload - bypass cache"""
        if not self.tabs:
            return
        webview = self.tabs[self.active_tab_idx].webview
        webview.reload_bypass_cache()
    
    def _show_performance_overlay(self):
        """Show performance overlay with tab resource usage"""
        if hasattr(self, '_perf_overlay') and self._perf_overlay:
            self._perf_overlay.destroy()
            self._perf_overlay = None
            return
        
        # Create overlay window
        self._perf_overlay = Gtk.Window(title="Tab Performance")
        self._perf_overlay.set_transient_for(self.window)
        self._perf_overlay.set_default_size(300, 200)
        self._perf_overlay.add_css_class("perf-overlay")
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)
        
        header = Gtk.Label(label="📊 Tab Performance")
        header.set_halign(Gtk.Align.START)
        header.add_css_class("perf-header")
        box.append(header)
        
        # Tab list with status
        for i, tab in enumerate(self.tabs):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            
            # Status indicator
            if tab.is_unloaded:
                status = "💤"
                status_text = "Unloaded"
            elif i == self.active_tab_idx:
                status = "🟢"
                status_text = "Active"
            else:
                status = "🔵"
                status_text = "Loaded"
            
            status_label = Gtk.Label(label=status)
            row.append(status_label)
            
            # Title (truncated)
            title = tab.title[:25] if tab.title else "New Tab"
            title_label = Gtk.Label(label=title)
            title_label.set_hexpand(True)
            title_label.set_halign(Gtk.Align.START)
            title_label.set_ellipsize(Pango.EllipsizeMode.END)
            row.append(title_label)
            
            # Kill button for active tabs
            if not tab.is_unloaded and i != self.active_tab_idx:
                kill_btn = Gtk.Button(label="⏸")
                kill_btn.set_tooltip_text("Unload tab")
                kill_btn.connect("clicked", lambda _, t=tab: self._unload_tab(t))
                row.append(kill_btn)
            
            box.append(row)
        
        # Summary
        loaded = sum(1 for t in self.tabs if not t.is_unloaded)
        unloaded = len(self.tabs) - loaded
        summary = Gtk.Label(label=f"Loaded: {loaded} | Unloaded: {unloaded}")
        summary.set_margin_top(8)
        summary.add_css_class("perf-summary")
        box.append(summary)
        
        # Close on Escape
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", lambda c, k, kc, s: 
            self._perf_overlay.destroy() if Gdk.keyval_name(k) == "Escape" else None)
        self._perf_overlay.add_controller(key_controller)
        
        self._perf_overlay.set_child(box)
        self._perf_overlay.present()
    
    def _kill_tab_scripts(self):
        """Stop all scripts/timers in current tab"""
        if not self.tabs:
            return
        
        tab = self.tabs[self.active_tab_idx]
        # Inject script to clear intervals and timeouts
        js = """
        (function() {
            // Clear all intervals
            for (let i = 1; i < 99999; i++) {
                window.clearInterval(i);
                window.clearTimeout(i);
            }
            // Stop animations
            document.querySelectorAll('*').forEach(el => {
                el.style.animation = 'none';
                el.style.transition = 'none';
            });
            console.log('RyxSurf: Killed all timers and animations');
        })();
        """
        tab.webview.evaluate_javascript(js, -1, None, None, None, None, None)
        print("Killed scripts and animations in current tab")


@dataclass
class Config:
    """Browser configuration"""
    homepage: str = "https://www.google.com"  # Could point to local SearXNG
    session_dir: Path = field(default_factory=lambda: Path.home() / ".config" / "ryxsurf" / "sessions")
    extensions_dir: Path = field(default_factory=lambda: Path.home() / ".config" / "ryxsurf" / "extensions")
    
    # AI settings
    ai_endpoint: str = "http://localhost:8001/v1"
    ai_model: str = "qwen2.5-7b-awq"  # Fast model for browser actions
    
    # Memory optimization
    unload_after_seconds: int = 300  # 5 minutes
    max_loaded_tabs: int = 10
    
    @classmethod
    def load(cls) -> 'Config':
        """Load config from file or return defaults"""
        config_file = Path.home() / ".config" / "ryxsurf" / "config.json"
        if config_file.exists():
            data = json.loads(config_file.read_text())
            return cls(**data)
        return cls()

def main():
    """Entry point for RyxSurf browser"""
    config = Config.load()
    browser = Browser(config)
    browser.run()


if __name__ == "__main__":
    main()
