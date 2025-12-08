"""
RyxSurf - Full-featured Adwaita Browser
Professional UI with all essential features.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('WebKit', '6.0')

from gi.repository import Gtk, Adw, WebKit, GLib, Gdk, Gio, Pango
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict
from urllib.parse import urlparse, quote_plus
import json
import time
import os

# Paths
CONFIG_DIR = Path.home() / ".config" / "ryxsurf"
DATA_DIR = Path.home() / ".local" / "share" / "ryxsurf"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

SESSION_FILE = DATA_DIR / "session.json"
HISTORY_FILE = DATA_DIR / "history.json"
BOOKMARKS_FILE = DATA_DIR / "bookmarks.json"

# Default settings
DEFAULTS = {
    "homepage": "about:newtab",
    "search_engine": "https://duckduckgo.com/?q=",
    "restore_session": True,
    "dark_mode": True,
}


@dataclass
class Tab:
    """Browser tab"""
    webview: WebKit.WebView
    title: str = "New Tab"
    url: str = "about:blank"
    loading: bool = False
    can_go_back: bool = False
    can_go_forward: bool = False
    last_active: float = field(default_factory=time.time)
    is_unloaded: bool = False


class HistoryManager:
    """Manages browsing history"""
    def __init__(self):
        self.entries: List[Dict] = []
        self._load()
    
    def _load(self):
        if HISTORY_FILE.exists():
            try:
                self.entries = json.loads(HISTORY_FILE.read_text())[-1000:]  # Keep last 1000
            except:
                self.entries = []
    
    def save(self):
        HISTORY_FILE.write_text(json.dumps(self.entries[-1000:], indent=2))
    
    def add(self, url: str, title: str):
        if url and not url.startswith("about:"):
            self.entries.append({
                "url": url,
                "title": title or url,
                "time": time.time()
            })
    
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        query = query.lower()
        matches = []
        seen = set()
        for e in reversed(self.entries):
            if query in e["url"].lower() or query in e.get("title", "").lower():
                if e["url"] not in seen:
                    seen.add(e["url"])
                    matches.append(e)
                    if len(matches) >= limit:
                        break
        return matches


class BookmarkManager:
    """Manages bookmarks"""
    def __init__(self):
        self.bookmarks: List[Dict] = []
        self._load()
    
    def _load(self):
        if BOOKMARKS_FILE.exists():
            try:
                self.bookmarks = json.loads(BOOKMARKS_FILE.read_text())
            except:
                self.bookmarks = []
    
    def save(self):
        BOOKMARKS_FILE.write_text(json.dumps(self.bookmarks, indent=2))
    
    def add(self, url: str, title: str):
        if not self.exists(url):
            self.bookmarks.append({"url": url, "title": title or url})
            self.save()
    
    def remove(self, url: str):
        self.bookmarks = [b for b in self.bookmarks if b["url"] != url]
        self.save()
    
    def exists(self, url: str) -> bool:
        return any(b["url"] == url for b in self.bookmarks)


class SessionManager:
    """Manages tab sessions"""
    def __init__(self):
        self.data = {"tabs": [], "active": 0}
    
    def save(self, tabs: List[Tab], active: int):
        self.data = {
            "tabs": [{"url": t.url, "title": t.title} for t in tabs if t.url != "about:newtab"],
            "active": active
        }
        SESSION_FILE.write_text(json.dumps(self.data, indent=2))
    
    def load(self) -> tuple:
        if SESSION_FILE.exists():
            try:
                self.data = json.loads(SESSION_FILE.read_text())
                return self.data.get("tabs", []), self.data.get("active", 0)
            except:
                pass
        return [], 0


class RyxSurfWindow(Adw.ApplicationWindow):
    """Main browser window"""
    
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("RyxSurf")
        self.set_default_size(1400, 900)
        
        # State
        self.tabs: List[Tab] = []
        self.active_tab = 0
        self.is_fullscreen = False
        
        # Managers
        self.history = HistoryManager()
        self.bookmarks = BookmarkManager()
        self.session = SessionManager()
        
        # Build UI
        self._build_ui()
        self._setup_keybinds()
        self._apply_css()
        
        # Restore session or open new tab
        self._restore_session()
        
        # Auto-save session periodically
        GLib.timeout_add_seconds(30, self._auto_save)
        
        # Tab unloading check (every 60s)
        GLib.timeout_add_seconds(60, self._check_unload_tabs)
    
    def _build_ui(self):
        """Build the complete UI"""
        # Main horizontal split
        # Toast overlay for notifications
        self.toast_overlay = Adw.ToastOverlay()
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.toast_overlay.set_child(self.main_box)
        self.set_content(self.toast_overlay)
        
        # === LEFT SIDEBAR ===
        self.sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.sidebar.set_size_request(240, -1)
        self.sidebar.add_css_class("sidebar")
        
        # Sidebar header
        sidebar_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        sidebar_header.add_css_class("sidebar-header")
        sidebar_header.set_margin_start(12)
        sidebar_header.set_margin_end(8)
        sidebar_header.set_margin_top(8)
        sidebar_header.set_margin_bottom(8)
        
        tabs_label = Gtk.Label(label="Tabs")
        tabs_label.add_css_class("sidebar-title")
        tabs_label.set_hexpand(True)
        tabs_label.set_halign(Gtk.Align.START)
        sidebar_header.append(tabs_label)
        
        new_tab_btn = Gtk.Button(icon_name="tab-new-symbolic")
        new_tab_btn.add_css_class("flat")
        new_tab_btn.add_css_class("circular")
        new_tab_btn.set_tooltip_text("New Tab (Ctrl+T)")
        new_tab_btn.connect("clicked", lambda _: self._new_tab())
        sidebar_header.append(new_tab_btn)
        
        self.sidebar.append(sidebar_header)
        
        # Tab list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        
        self.tab_list = Gtk.ListBox()
        self.tab_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.tab_list.add_css_class("navigation-sidebar")
        self.tab_list.connect("row-selected", self._on_tab_selected)
        scroll.set_child(self.tab_list)
        self.sidebar.append(scroll)
        
        # Sidebar footer with bookmarks toggle
        sidebar_footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        sidebar_footer.add_css_class("sidebar-footer")
        sidebar_footer.set_margin_start(8)
        sidebar_footer.set_margin_end(8)
        sidebar_footer.set_margin_bottom(8)
        
        bookmarks_btn = Gtk.Button(icon_name="user-bookmarks-symbolic")
        bookmarks_btn.add_css_class("flat")
        bookmarks_btn.set_tooltip_text("Bookmarks")
        bookmarks_btn.connect("clicked", lambda _: self._show_bookmarks())
        sidebar_footer.append(bookmarks_btn)
        
        history_btn = Gtk.Button(icon_name="document-open-recent-symbolic")
        history_btn.add_css_class("flat")
        history_btn.set_tooltip_text("History")
        history_btn.connect("clicked", lambda _: self._show_history())
        sidebar_footer.append(history_btn)
        
        settings_btn = Gtk.Button(icon_name="emblem-system-symbolic")
        settings_btn.add_css_class("flat")
        settings_btn.set_tooltip_text("Settings")
        sidebar_footer.append(settings_btn)
        
        self.sidebar.append(sidebar_footer)
        self.main_box.append(self.sidebar)
        
        # === RIGHT CONTENT ===
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.set_hexpand(True)
        
        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        toolbar.add_css_class("toolbar")
        toolbar.set_spacing(6)
        toolbar.set_margin_start(8)
        toolbar.set_margin_end(8)
        toolbar.set_margin_top(6)
        toolbar.set_margin_bottom(6)
        
        # Navigation buttons
        self.back_btn = Gtk.Button(icon_name="go-previous-symbolic")
        self.back_btn.add_css_class("flat")
        self.back_btn.set_tooltip_text("Back (Alt+←)")
        self.back_btn.connect("clicked", lambda _: self._go_back())
        toolbar.append(self.back_btn)
        
        self.fwd_btn = Gtk.Button(icon_name="go-next-symbolic")
        self.fwd_btn.add_css_class("flat")
        self.fwd_btn.set_tooltip_text("Forward (Alt+→)")
        self.fwd_btn.connect("clicked", lambda _: self._go_forward())
        toolbar.append(self.fwd_btn)
        
        self.reload_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        self.reload_btn.add_css_class("flat")
        self.reload_btn.set_tooltip_text("Reload (Ctrl+R)")
        self.reload_btn.connect("clicked", lambda _: self._reload())
        toolbar.append(self.reload_btn)
        
        self.home_btn = Gtk.Button(icon_name="go-home-symbolic")
        self.home_btn.add_css_class("flat")
        self.home_btn.set_tooltip_text("Home")
        self.home_btn.connect("clicked", lambda _: self._go_home())
        toolbar.append(self.home_btn)
        
        # URL entry with suggestions
        url_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        url_box.set_hexpand(True)
        url_box.add_css_class("url-box")
        
        self.security_icon = Gtk.Image(icon_name="channel-insecure-symbolic")
        self.security_icon.add_css_class("security-icon")
        self.security_icon.set_margin_start(8)
        url_box.append(self.security_icon)
        
        self.url_entry = Gtk.Entry()
        self.url_entry.set_hexpand(True)
        self.url_entry.set_placeholder_text("Search or enter URL...")
        self.url_entry.add_css_class("url-entry")
        self.url_entry.connect("activate", self._on_url_activate)
        self.url_entry.connect("changed", self._on_url_changed)
        url_box.append(self.url_entry)
        
        self.bookmark_btn = Gtk.Button(icon_name="non-starred-symbolic")
        self.bookmark_btn.add_css_class("flat")
        self.bookmark_btn.set_tooltip_text("Bookmark (Ctrl+D)")
        self.bookmark_btn.connect("clicked", lambda _: self._toggle_bookmark())
        url_box.append(self.bookmark_btn)
        
        toolbar.append(url_box)
        
        # Progress indicator (loading)
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.add_css_class("osd")
        self.progress_bar.set_visible(False)
        
        # Find bar (hidden by default)
        self.find_bar = self._create_find_bar()
        self.find_bar.set_visible(False)
        
        # Menu
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu_btn.add_css_class("flat")
        menu_btn.set_tooltip_text("Menu")
        menu_btn.set_menu_model(self._create_menu())
        toolbar.append(menu_btn)
        
        content_box.append(toolbar)
        content_box.append(self.progress_bar)
        content_box.append(self.find_bar)
        
        # WebView stack
        self.webview_stack = Gtk.Stack()
        self.webview_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.webview_stack.set_vexpand(True)
        self.webview_stack.set_hexpand(True)
        content_box.append(self.webview_stack)
        
        # Status bar
        self.status_bar = Gtk.Label()
        self.status_bar.add_css_class("status-bar")
        self.status_bar.set_halign(Gtk.Align.START)
        self.status_bar.set_margin_start(8)
        self.status_bar.set_margin_bottom(4)
        self.status_bar.set_visible(False)
        content_box.append(self.status_bar)
        
        self.main_box.append(content_box)
        
        # URL suggestions popup
        self._create_suggestions_popup()
    
    def _create_find_bar(self) -> Gtk.Box:
        """Create find-in-page bar"""
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bar.add_css_class("find-bar")
        bar.set_margin_start(8)
        bar.set_margin_end(8)
        bar.set_margin_top(4)
        bar.set_margin_bottom(4)
        
        self.find_entry = Gtk.Entry()
        self.find_entry.set_placeholder_text("Find in page...")
        self.find_entry.set_hexpand(True)
        self.find_entry.connect("activate", lambda _: self._find_next())
        self.find_entry.connect("changed", lambda _: self._find_text())
        bar.append(self.find_entry)
        
        self.find_count = Gtk.Label(label="")
        self.find_count.add_css_class("dim-label")
        bar.append(self.find_count)
        
        prev_btn = Gtk.Button(icon_name="go-up-symbolic")
        prev_btn.add_css_class("flat")
        prev_btn.connect("clicked", lambda _: self._find_prev())
        bar.append(prev_btn)
        
        next_btn = Gtk.Button(icon_name="go-down-symbolic")
        next_btn.add_css_class("flat")
        next_btn.connect("clicked", lambda _: self._find_next())
        bar.append(next_btn)
        
        close_btn = Gtk.Button(icon_name="window-close-symbolic")
        close_btn.add_css_class("flat")
        close_btn.connect("clicked", lambda _: self._close_find())
        bar.append(close_btn)
        
        return bar
    
    def _create_menu(self) -> Gio.Menu:
        """Create app menu"""
        menu = Gio.Menu()
        
        section1 = Gio.Menu()
        section1.append("New Tab", "win.new-tab")
        section1.append("New Window", "win.new-window")
        menu.append_section(None, section1)
        
        section2 = Gio.Menu()
        section2.append("Find in Page", "win.find")
        section2.append("Zoom In", "win.zoom-in")
        section2.append("Zoom Out", "win.zoom-out")
        section2.append("Reset Zoom", "win.zoom-reset")
        menu.append_section(None, section2)
        
        section3 = Gio.Menu()
        section3.append("Fullscreen", "win.fullscreen")
        section3.append("Toggle Sidebar", "win.toggle-sidebar")
        menu.append_section(None, section3)
        
        section4 = Gio.Menu()
        section4.append("Downloads", "win.downloads")
        section4.append("History", "win.history")
        section4.append("Bookmarks", "win.bookmarks")
        menu.append_section(None, section4)
        
        return menu
    
    def _create_suggestions_popup(self):
        """Create URL suggestions popup"""
        self.suggestions_popup = Gtk.Popover()
        self.suggestions_popup.set_parent(self.url_entry)
        self.suggestions_popup.set_has_arrow(False)
        self.suggestions_popup.add_css_class("suggestions-popup")
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(300)
        scroll.set_propagate_natural_height(True)
        
        self.suggestions_list = Gtk.ListBox()
        self.suggestions_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.suggestions_list.connect("row-activated", self._on_suggestion_activated)
        scroll.set_child(self.suggestions_list)
        
        self.suggestions_popup.set_child(scroll)
    
    def _apply_css(self):
        """Apply custom CSS"""
        css = """
        .sidebar {
            background: alpha(@window_bg_color, 0.95);
            border-right: 1px solid alpha(@borders, 0.5);
        }
        .sidebar-header {
            padding: 8px;
        }
        .sidebar-title {
            font-weight: 600;
            font-size: 13px;
        }
        .sidebar-footer {
            padding: 4px;
            border-top: 1px solid alpha(@borders, 0.3);
        }
        .toolbar {
            background: alpha(@headerbar_bg_color, 0.9);
            border-bottom: 1px solid alpha(@borders, 0.3);
        }
        .url-box {
            background: alpha(@view_bg_color, 0.8);
            border-radius: 8px;
            border: 1px solid alpha(@borders, 0.5);
        }
        .url-box:focus-within {
            border-color: @accent_bg_color;
            box-shadow: 0 0 0 2px alpha(@accent_bg_color, 0.3);
        }
        .url-entry {
            background: transparent;
            border: none;
            box-shadow: none;
            padding: 6px 8px;
        }
        .security-icon {
            opacity: 0.6;
        }
        .security-icon.secure {
            color: @success_color;
            opacity: 1;
        }
        .status-bar {
            font-size: 11px;
            color: alpha(@view_fg_color, 0.6);
        }
        .find-bar {
            background: @view_bg_color;
            border-radius: 6px;
            padding: 4px 8px;
        }
        .tab-row.loading .tab-title {
            font-style: italic;
        }
        .tab-row.unloaded {
            opacity: 0.6;
        }
        .tab-row.unloaded .tab-title {
            font-style: italic;
            color: alpha(@view_fg_color, 0.5);
        }
        .suggestions-popup {
            background: @popover_bg_color;
            min-width: 400px;
        }
        """
        
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def _setup_keybinds(self):
        """Setup keyboard shortcuts"""
        ctrl = Gtk.EventControllerKey()
        ctrl.connect("key-pressed", self._on_key_press)
        self.add_controller(ctrl)
        
        # Actions
        action = Gio.SimpleAction.new("new-tab", None)
        action.connect("activate", lambda a, p: self._new_tab())
        self.add_action(action)
        
        action = Gio.SimpleAction.new("find", None)
        action.connect("activate", lambda a, p: self._show_find())
        self.add_action(action)
        
        action = Gio.SimpleAction.new("fullscreen", None)
        action.connect("activate", lambda a, p: self._toggle_fullscreen())
        self.add_action(action)
        
        action = Gio.SimpleAction.new("toggle-sidebar", None)
        action.connect("activate", lambda a, p: self._toggle_sidebar())
        self.add_action(action)
        
        action = Gio.SimpleAction.new("zoom-in", None)
        action.connect("activate", lambda a, p: self._zoom(0.1))
        self.add_action(action)
        
        action = Gio.SimpleAction.new("zoom-out", None)
        action.connect("activate", lambda a, p: self._zoom(-0.1))
        self.add_action(action)
        
        action = Gio.SimpleAction.new("zoom-reset", None)
        action.connect("activate", lambda a, p: self._zoom_reset())
        self.add_action(action)
    
    def _on_key_press(self, ctrl, keyval, keycode, state):
        """Handle key presses"""
        ctrl_pressed = state & Gdk.ModifierType.CONTROL_MASK
        alt_pressed = state & Gdk.ModifierType.ALT_MASK
        shift_pressed = state & Gdk.ModifierType.SHIFT_MASK
        
        if ctrl_pressed:
            if keyval == Gdk.KEY_t:
                self._new_tab()
                return True
            elif keyval == Gdk.KEY_w:
                self._close_tab()
                return True
            elif keyval == Gdk.KEY_l:
                self.url_entry.grab_focus()
                self.url_entry.select_region(0, -1)
                return True
            elif keyval == Gdk.KEY_r:
                if shift_pressed:
                    self._hard_reload()
                else:
                    self._reload()
                return True
            elif keyval == Gdk.KEY_f:
                self._show_find()
                return True
            elif keyval == Gdk.KEY_d:
                self._toggle_bookmark()
                return True
            elif keyval == Gdk.KEY_Tab:
                if shift_pressed:
                    self._prev_tab()
                else:
                    self._next_tab()
                return True
            elif keyval == Gdk.KEY_plus or keyval == Gdk.KEY_equal:
                self._zoom(0.1)
                return True
            elif keyval == Gdk.KEY_minus:
                self._zoom(-0.1)
                return True
            elif keyval == Gdk.KEY_0:
                self._zoom_reset()
                return True
            elif keyval == Gdk.KEY_b:
                self._toggle_sidebar()
                return True
            elif keyval >= Gdk.KEY_1 and keyval <= Gdk.KEY_9:
                idx = keyval - Gdk.KEY_1
                if idx < len(self.tabs):
                    self._switch_to_tab(idx)
                return True
        
        if alt_pressed:
            if keyval == Gdk.KEY_Left:
                self._go_back()
                return True
            elif keyval == Gdk.KEY_Right:
                self._go_forward()
                return True
        
        if keyval == Gdk.KEY_F11:
            self._toggle_fullscreen()
            return True
        
        if keyval == Gdk.KEY_Escape:
            if self.find_bar.get_visible():
                self._close_find()
                return True
            if self.is_fullscreen:
                self._toggle_fullscreen()
                return True
        
        return False
    
    # === TAB MANAGEMENT ===
    
    def _new_tab(self, url: str = None):
        """Create new tab"""
        webview = WebKit.WebView()
        
        # Settings
        settings = webview.get_settings()
        settings.set_enable_javascript(True)
        settings.set_hardware_acceleration_policy(WebKit.HardwareAccelerationPolicy.ALWAYS)
        settings.set_enable_webgl(True)
        settings.set_enable_smooth_scrolling(True)
        settings.set_enable_developer_extras(True)
        settings.set_enable_back_forward_navigation_gestures(True)
        settings.set_media_playback_requires_user_gesture(False)
        
        tab = Tab(webview=webview, url=url or "about:newtab")
        
        # Signals
        webview.connect("notify::title", lambda w, p: self._on_title_changed(tab))
        webview.connect("notify::uri", lambda w, p: self._on_uri_changed(tab))
        webview.connect("notify::estimated-load-progress", lambda w, p: self._on_progress(tab))
        webview.connect("load-changed", lambda w, e: self._on_load_changed(tab, e))
        webview.connect("mouse-target-changed", self._on_mouse_target)
        webview.connect("decide-policy", self._on_decide_policy)
        
        # Download handler
        network_session = webview.get_network_session()
        network_session.connect("download-started", self._on_download_started)
        
        self.tabs.append(tab)
        idx = len(self.tabs) - 1
        
        # Add to stack
        self.webview_stack.add_named(webview, f"tab-{idx}")
        
        # Update UI
        self._update_tab_list()
        self._switch_to_tab(idx)
        
        # Load
        if url:
            webview.load_uri(url)
        else:
            self._load_newtab_page(webview)
            GLib.idle_add(lambda: self.url_entry.grab_focus())
    
    def _close_tab(self, idx: int = None):
        """Close tab"""
        if idx is None:
            idx = self.active_tab
        
        if len(self.tabs) <= 1:
            tab = self.tabs[0]
            tab.webview.load_uri("about:blank")
            self._load_newtab_page(tab.webview)
            tab.title = "New Tab"
            tab.url = "about:newtab"
            self._update_tab_list()
            return
        
        # Remove
        webview = self.tabs[idx].webview
        self.webview_stack.remove(webview)
        self.tabs.pop(idx)
        
        # Rename remaining tabs in stack
        for i, tab in enumerate(self.tabs):
            # Stack children need consistent naming
            pass
        
        if self.active_tab >= len(self.tabs):
            self.active_tab = len(self.tabs) - 1
        
        self._update_tab_list()
        self._switch_to_tab(self.active_tab)
    
    def _switch_to_tab(self, idx: int):
        """Switch to tab"""
        if 0 <= idx < len(self.tabs):
            self.active_tab = idx
            tab = self.tabs[idx]
            
            # Reload if unloaded
            if tab.is_unloaded:
                self._reload_unloaded_tab(idx)
            
            # Update last active
            tab.last_active = time.time()
            
            # Need to find the webview in stack
            for i, t in enumerate(self.tabs):
                child = self.webview_stack.get_child_by_name(f"tab-{i}")
                if child == tab.webview:
                    self.webview_stack.set_visible_child(tab.webview)
                    break
            else:
                # Fallback - set by webview directly
                self.webview_stack.set_visible_child(tab.webview)
            
            # Update URL bar
            if tab.url and tab.url != "about:newtab":
                self.url_entry.set_text(tab.url)
            else:
                self.url_entry.set_text("")
            
            self._update_nav_buttons()
            self._update_bookmark_btn()
            self._update_security_icon()
            self.set_title(f"{tab.title} - RyxSurf")
            
            # Select in sidebar
            row = self.tab_list.get_row_at_index(idx)
            if row:
                self.tab_list.select_row(row)
    
    def _next_tab(self):
        self._switch_to_tab((self.active_tab + 1) % len(self.tabs))
    
    def _prev_tab(self):
        self._switch_to_tab((self.active_tab - 1) % len(self.tabs))
    
    def _update_tab_list(self):
        """Update sidebar tab list"""
        # Clear
        while row := self.tab_list.get_row_at_index(0):
            self.tab_list.remove(row)
        
        # Add tabs
        for i, tab in enumerate(self.tabs):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.add_css_class("tab-row")
            row.set_margin_start(8)
            row.set_margin_end(4)
            row.set_margin_top(4)
            row.set_margin_bottom(4)
            
            if tab.loading:
                row.add_css_class("loading")
                icon = Gtk.Spinner()
                icon.start()
            elif tab.is_unloaded:
                row.add_css_class("unloaded")
                icon = Gtk.Image(icon_name="content-loading-symbolic")
            else:
                icon = Gtk.Image(icon_name="web-browser-symbolic")
            icon.set_size_request(16, 16)
            row.append(icon)
            
            # Title & URL
            text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            text_box.set_hexpand(True)
            
            title_text = tab.title or "New Tab"
            if tab.is_unloaded:
                title_text = f"💤 {title_text}"
            title = Gtk.Label(label=title_text)
            title.add_css_class("tab-title")
            title.set_halign(Gtk.Align.START)
            title.set_ellipsize(Pango.EllipsizeMode.END)
            title.set_max_width_chars(20)
            text_box.append(title)
            
            url_label = Gtk.Label(label=self._format_url(tab.url))
            url_label.add_css_class("dim-label")
            url_label.add_css_class("caption")
            url_label.set_halign(Gtk.Align.START)
            url_label.set_ellipsize(Pango.EllipsizeMode.END)
            url_label.set_max_width_chars(25)
            text_box.append(url_label)
            
            row.append(text_box)
            
            # Close button
            close_btn = Gtk.Button(icon_name="window-close-symbolic")
            close_btn.add_css_class("flat")
            close_btn.add_css_class("circular")
            close_btn.set_valign(Gtk.Align.CENTER)
            close_btn.connect("clicked", lambda _, idx=i: self._close_tab(idx))
            row.append(close_btn)
            
            list_row = Gtk.ListBoxRow()
            list_row.set_child(row)
            self.tab_list.append(list_row)
        
        # Select active
        row = self.tab_list.get_row_at_index(self.active_tab)
        if row:
            self.tab_list.select_row(row)
    
    def _on_tab_selected(self, listbox, row):
        if row:
            idx = row.get_index()
            if idx != self.active_tab and idx < len(self.tabs):
                self._switch_to_tab(idx)
    
    def _format_url(self, url: str) -> str:
        if not url or url == "about:newtab":
            return ""
        return url.replace("https://", "").replace("http://", "").replace("www.", "")[:35]
    
    # === NAVIGATION ===
    
    def _on_url_activate(self, entry):
        """Navigate to URL"""
        text = entry.get_text().strip()
        if not text:
            return
        
        self.suggestions_popup.popdown()
        
        # Determine if URL or search
        if self._is_url(text):
            if not text.startswith(("http://", "https://")):
                text = "https://" + text
            self.tabs[self.active_tab].webview.load_uri(text)
        else:
            # Search
            url = DEFAULTS["search_engine"] + quote_plus(text)
            self.tabs[self.active_tab].webview.load_uri(url)
    
    def _is_url(self, text: str) -> bool:
        """Check if text looks like a URL"""
        if " " in text:
            return False
        if text.startswith(("http://", "https://", "file://")):
            return True
        if "." in text and not text.endswith("."):
            parts = text.split(".")
            if len(parts[-1]) >= 2:
                return True
        if text.startswith("localhost") or text.startswith("127."):
            return True
        return False
    
    def _on_url_changed(self, entry):
        """Show suggestions as user types"""
        text = entry.get_text().strip()
        if len(text) < 2:
            self.suggestions_popup.popdown()
            return
        
        # Get suggestions
        history_matches = self.history.search(text, 5)
        bookmark_matches = [b for b in self.bookmarks.bookmarks 
                          if text.lower() in b["url"].lower() or text.lower() in b["title"].lower()][:3]
        
        # Clear list
        while row := self.suggestions_list.get_row_at_index(0):
            self.suggestions_list.remove(row)
        
        if not history_matches and not bookmark_matches:
            self.suggestions_popup.popdown()
            return
        
        # Add bookmarks first
        for b in bookmark_matches:
            row = self._create_suggestion_row(b["title"], b["url"], "★")
            self.suggestions_list.append(row)
        
        # Add history
        for h in history_matches:
            row = self._create_suggestion_row(h["title"], h["url"], "⏱")
            self.suggestions_list.append(row)
        
        self.suggestions_popup.popup()
    
    def _create_suggestion_row(self, title: str, url: str, icon: str) -> Gtk.ListBoxRow:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(4)
        box.set_margin_bottom(4)
        
        icon_label = Gtk.Label(label=icon)
        box.append(icon_label)
        
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        text_box.set_hexpand(True)
        
        title_label = Gtk.Label(label=title[:50])
        title_label.set_halign(Gtk.Align.START)
        title_label.set_ellipsize(Pango.EllipsizeMode.END)
        text_box.append(title_label)
        
        url_label = Gtk.Label(label=url[:60])
        url_label.add_css_class("dim-label")
        url_label.add_css_class("caption")
        url_label.set_halign(Gtk.Align.START)
        url_label.set_ellipsize(Pango.EllipsizeMode.END)
        text_box.append(url_label)
        
        box.append(text_box)
        
        row = Gtk.ListBoxRow()
        row.set_child(box)
        row.url = url
        return row
    
    def _on_suggestion_activated(self, listbox, row):
        if row and hasattr(row, 'url'):
            self.url_entry.set_text(row.url)
            self.suggestions_popup.popdown()
            self._on_url_activate(self.url_entry)
    
    def _go_back(self):
        if self.tabs and self.tabs[self.active_tab].webview.can_go_back():
            self.tabs[self.active_tab].webview.go_back()
    
    def _go_forward(self):
        if self.tabs and self.tabs[self.active_tab].webview.can_go_forward():
            self.tabs[self.active_tab].webview.go_forward()
    
    def _reload(self):
        if self.tabs:
            self.tabs[self.active_tab].webview.reload()
    
    def _hard_reload(self):
        if self.tabs:
            self.tabs[self.active_tab].webview.reload_bypass_cache()
    
    def _go_home(self):
        if self.tabs:
            self._load_newtab_page(self.tabs[self.active_tab].webview)
    
    def _update_nav_buttons(self):
        if self.tabs:
            webview = self.tabs[self.active_tab].webview
            self.back_btn.set_sensitive(webview.can_go_back())
            self.fwd_btn.set_sensitive(webview.can_go_forward())
    
    # === WEBVIEW SIGNALS ===
    
    def _on_title_changed(self, tab: Tab):
        tab.title = tab.webview.get_title() or "New Tab"
        self._update_tab_list()
        if tab == self.tabs[self.active_tab]:
            self.set_title(f"{tab.title} - RyxSurf")
    
    def _on_uri_changed(self, tab: Tab):
        uri = tab.webview.get_uri()
        if uri:
            tab.url = uri
            # Add to history
            if not uri.startswith("about:"):
                self.history.add(uri, tab.title)
            
            if tab == self.tabs[self.active_tab]:
                if not uri.startswith("about:"):
                    self.url_entry.set_text(uri)
                self._update_security_icon()
                self._update_bookmark_btn()
        
        self._update_nav_buttons()
        self._update_tab_list()
    
    def _on_progress(self, tab: Tab):
        progress = tab.webview.get_estimated_load_progress()
        if tab == self.tabs[self.active_tab]:
            if progress < 1.0:
                self.progress_bar.set_visible(True)
                self.progress_bar.set_fraction(progress)
            else:
                self.progress_bar.set_visible(False)
    
    def _on_load_changed(self, tab: Tab, event):
        if event == WebKit.LoadEvent.STARTED:
            tab.loading = True
        elif event == WebKit.LoadEvent.FINISHED:
            tab.loading = False
        self._update_tab_list()
    
    def _on_mouse_target(self, webview, hit_test, modifiers):
        """Show link URL in status bar on hover"""
        if hit_test.context_is_link():
            uri = hit_test.get_link_uri()
            self.status_bar.set_text(uri)
            self.status_bar.set_visible(True)
        else:
            self.status_bar.set_visible(False)
    
    def _on_decide_policy(self, webview, decision, decision_type):
        """Handle navigation decisions (e.g., open in new tab)"""
        if decision_type == WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            nav_action = decision.get_navigation_action()
            if nav_action.get_mouse_button() == 2:  # Middle click
                uri = nav_action.get_request().get_uri()
                self._new_tab(uri)
                decision.ignore()
                return True
        return False
    
    # === SECURITY & BOOKMARKS ===
    
    def _update_security_icon(self):
        if self.tabs:
            url = self.tabs[self.active_tab].url
            if url and url.startswith("https://"):
                self.security_icon.set_from_icon_name("channel-secure-symbolic")
                self.security_icon.add_css_class("secure")
            else:
                self.security_icon.set_from_icon_name("channel-insecure-symbolic")
                self.security_icon.remove_css_class("secure")
    
    def _update_bookmark_btn(self):
        if self.tabs:
            url = self.tabs[self.active_tab].url
            if self.bookmarks.exists(url):
                self.bookmark_btn.set_icon_name("starred-symbolic")
            else:
                self.bookmark_btn.set_icon_name("non-starred-symbolic")
    
    def _toggle_bookmark(self):
        if not self.tabs:
            return
        tab = self.tabs[self.active_tab]
        if self.bookmarks.exists(tab.url):
            self.bookmarks.remove(tab.url)
        else:
            self.bookmarks.add(tab.url, tab.title)
        self._update_bookmark_btn()
    
    # === FIND ===
    
    def _show_find(self):
        self.find_bar.set_visible(True)
        self.find_entry.grab_focus()
    
    def _close_find(self):
        self.find_bar.set_visible(False)
        if self.tabs:
            finder = self.tabs[self.active_tab].webview.get_find_controller()
            finder.search_finish()
    
    def _find_text(self):
        if not self.tabs:
            return
        text = self.find_entry.get_text()
        if text:
            finder = self.tabs[self.active_tab].webview.get_find_controller()
            finder.search(text, WebKit.FindOptions.CASE_INSENSITIVE | WebKit.FindOptions.WRAP_AROUND, 1000)
    
    def _find_next(self):
        if self.tabs:
            finder = self.tabs[self.active_tab].webview.get_find_controller()
            finder.search_next()
    
    def _find_prev(self):
        if self.tabs:
            finder = self.tabs[self.active_tab].webview.get_find_controller()
            finder.search_previous()
    
    # === ZOOM ===
    
    def _zoom(self, delta: float):
        if self.tabs:
            webview = self.tabs[self.active_tab].webview
            current = webview.get_zoom_level()
            webview.set_zoom_level(max(0.25, min(5.0, current + delta)))
    
    def _zoom_reset(self):
        if self.tabs:
            self.tabs[self.active_tab].webview.set_zoom_level(1.0)
    
    # === UI TOGGLES ===
    
    def _toggle_fullscreen(self):
        if self.is_fullscreen:
            self.unfullscreen()
            self.sidebar.set_visible(True)
        else:
            self.fullscreen()
            self.sidebar.set_visible(False)
        self.is_fullscreen = not self.is_fullscreen
    
    def _toggle_sidebar(self):
        self.sidebar.set_visible(not self.sidebar.get_visible())
    
    # === HISTORY & BOOKMARKS VIEWS ===
    
    def _show_bookmarks(self):
        # TODO: Full bookmarks view
        pass
    
    def _show_history(self):
        # TODO: Full history view
        pass
    
    # === SESSION ===
    
    def _restore_session(self):
        """Restore previous session"""
        tabs_data, active = self.session.load()
        if tabs_data:
            for t in tabs_data:
                self._new_tab(t.get("url"))
            if active < len(self.tabs):
                self._switch_to_tab(active)
        else:
            self._new_tab()
    
    def _auto_save(self) -> bool:
        """Auto-save session"""
        self.session.save(self.tabs, self.active_tab)
        self.history.save()
        return True  # Keep timer running
    
    def _check_unload_tabs(self) -> bool:
        """Unload inactive tabs to save memory (5 min threshold)"""
        now = time.time()
        threshold = 300  # 5 minutes
        max_loaded = 8
        
        # Count loaded tabs
        loaded = [t for t in self.tabs if not t.is_unloaded]
        
        if len(loaded) > max_loaded:
            # Find oldest inactive tabs
            inactive = [(i, t) for i, t in enumerate(self.tabs) 
                       if not t.is_unloaded and i != self.active_tab 
                       and (now - t.last_active) > threshold]
            
            # Sort by last active, oldest first
            inactive.sort(key=lambda x: x[1].last_active)
            
            # Unload excess tabs
            to_unload = len(loaded) - max_loaded
            for i, (idx, tab) in enumerate(inactive):
                if i >= to_unload:
                    break
                self._unload_tab(idx)
        
        return True  # Keep timer
    
    def _unload_tab(self, idx: int):
        """Unload a tab to free memory"""
        tab = self.tabs[idx]
        if tab.is_unloaded or idx == self.active_tab:
            return
        
        # Save URL before unloading
        tab.is_unloaded = True
        tab.webview.load_uri("about:blank")
        self._update_tab_list()
        self._show_toast(f"Unloaded: {tab.title[:30]}")
    
    def _reload_unloaded_tab(self, idx: int):
        """Reload an unloaded tab"""
        tab = self.tabs[idx]
        if tab.is_unloaded and tab.url and tab.url != "about:blank":
            tab.webview.load_uri(tab.url)
            tab.is_unloaded = False
            tab.last_active = time.time()
    
    # === DOWNLOADS ===
    
    def _on_download_started(self, session, download):
        """Handle download start"""
        # Set download destination
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(exist_ok=True)
        
        response = download.get_response()
        suggested = response.get_suggested_filename() if response else None
        if not suggested:
            uri = download.get_request().get_uri()
            suggested = uri.split("/")[-1].split("?")[0] or "download"
        
        dest = downloads_dir / suggested
        # Handle duplicates
        counter = 1
        while dest.exists():
            stem = dest.stem
            if stem.endswith(f"_{counter-1}"):
                stem = stem.rsplit("_", 1)[0]
            dest = downloads_dir / f"{stem}_{counter}{dest.suffix}"
            counter += 1
        
        download.set_destination(str(dest))
        
        # Track progress
        download.connect("notify::estimated-progress", self._on_download_progress)
        download.connect("finished", self._on_download_finished)
        download.connect("failed", self._on_download_failed)
        
        # Show notification
        self._show_toast(f"Downloading: {suggested}")
    
    def _on_download_progress(self, download, pspec):
        """Update download progress"""
        progress = download.get_estimated_progress()
        # Could update a downloads panel here
    
    def _on_download_finished(self, download):
        """Download completed"""
        dest = download.get_destination()
        filename = Path(dest).name if dest else "file"
        self._show_toast(f"Downloaded: {filename}")
    
    def _on_download_failed(self, download, error):
        """Download failed"""
        self._show_toast("Download failed", error=True)
    
    def _show_toast(self, message: str, error: bool = False):
        """Show a toast notification"""
        toast = Adw.Toast.new(message)
        toast.set_timeout(3)
        # Need a toast overlay - add to window
        if not hasattr(self, 'toast_overlay'):
            return
        self.toast_overlay.add_toast(toast)
    
    # === NEW TAB PAGE ===
    
    def _load_newtab_page(self, webview):
        html = '''<!DOCTYPE html>
<html><head>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    background: linear-gradient(135deg, #1e1e2e 0%, #181825 100%);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
    color: #cdd6f4;
    gap: 32px;
}
.logo {
    font-size: 52px;
    font-weight: 300;
    background: linear-gradient(135deg, #cba6f7, #89b4fa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -1px;
}
.subtitle {
    color: #6c7086;
    font-size: 14px;
    margin-top: -20px;
}
.search-container {
    display: flex;
    align-items: center;
    background: rgba(49, 50, 68, 0.6);
    border: 1px solid rgba(147, 153, 178, 0.2);
    border-radius: 28px;
    padding: 14px 24px;
    width: 580px;
    transition: all 200ms;
    backdrop-filter: blur(10px);
}
.search-container:focus-within {
    background: rgba(49, 50, 68, 0.9);
    border-color: #cba6f7;
    box-shadow: 0 0 0 3px rgba(203, 166, 247, 0.15);
}
.search-icon { color: #6c7086; margin-right: 14px; font-size: 18px; }
.search-input {
    flex: 1;
    background: none;
    border: none;
    color: #cdd6f4;
    font-size: 16px;
    outline: none;
}
.search-input::placeholder { color: #6c7086; }
.shortcuts {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 16px;
    margin-top: 20px;
}
.shortcut {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    padding: 20px 16px;
    background: rgba(49, 50, 68, 0.4);
    border: 1px solid rgba(147, 153, 178, 0.1);
    border-radius: 16px;
    text-decoration: none;
    color: inherit;
    min-width: 90px;
    transition: all 200ms;
}
.shortcut:hover {
    background: rgba(49, 50, 68, 0.7);
    transform: translateY(-4px);
    border-color: rgba(203, 166, 247, 0.3);
}
.shortcut-icon { font-size: 28px; }
.shortcut-name { font-size: 12px; color: #a6adc8; }
.keyboard-hints {
    position: fixed;
    bottom: 28px;
    display: flex;
    gap: 24px;
    color: #45475a;
    font-size: 12px;
}
kbd {
    background: rgba(69, 71, 90, 0.6);
    padding: 4px 8px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 11px;
    margin-right: 4px;
}
</style></head><body>
<div class="logo">RyxSurf</div>
<div class="subtitle">Fast. Private. Keyboard-driven.</div>
<div class="search-container">
    <span class="search-icon">🔍</span>
    <input class="search-input" placeholder="Search with DuckDuckGo or enter URL..." autofocus
        onkeydown="if(event.key==='Enter'){let q=this.value.trim();if(!q)return;let isUrl=q.includes('.')&&!q.includes(' ');window.location=isUrl?(q.startsWith('http')?q:'https://'+q):'https://duckduckgo.com/?q='+encodeURIComponent(q)}">
</div>
<div class="shortcuts">
    <a class="shortcut" href="https://github.com"><div class="shortcut-icon">🐙</div><div class="shortcut-name">GitHub</div></a>
    <a class="shortcut" href="https://youtube.com"><div class="shortcut-icon">📺</div><div class="shortcut-name">YouTube</div></a>
    <a class="shortcut" href="https://reddit.com"><div class="shortcut-icon">🔮</div><div class="shortcut-name">Reddit</div></a>
    <a class="shortcut" href="https://twitter.com"><div class="shortcut-icon">🐦</div><div class="shortcut-name">Twitter</div></a>
    <a class="shortcut" href="https://news.ycombinator.com"><div class="shortcut-icon">🍊</div><div class="shortcut-name">HN</div></a>
    <a class="shortcut" href="https://duckduckgo.com"><div class="shortcut-icon">🦆</div><div class="shortcut-name">Search</div></a>
</div>
<div class="keyboard-hints">
    <span><kbd>Ctrl+T</kbd>New tab</span>
    <span><kbd>Ctrl+W</kbd>Close</span>
    <span><kbd>Ctrl+L</kbd>URL bar</span>
    <span><kbd>Ctrl+F</kbd>Find</span>
    <span><kbd>Ctrl+B</kbd>Sidebar</span>
    <span><kbd>F11</kbd>Fullscreen</span>
</div>
</body></html>'''
        webview.load_html(html, "about:newtab")


class RyxSurfApp(Adw.Application):
    """Main application"""
    
    def __init__(self):
        super().__init__(application_id="ai.ryx.surf")
        self.connect("activate", self._on_activate)
    
    def _on_activate(self, app):
        win = RyxSurfWindow(app)
        win.present()


def main():
    app = RyxSurfApp()
    app.run()


if __name__ == "__main__":
    main()
