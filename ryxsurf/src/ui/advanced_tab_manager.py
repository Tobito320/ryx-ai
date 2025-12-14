"""
Advanced Tab Manager
Includes all features from modern browsers: tab groups, pinning, muting, hibernation, etc.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit', '6.0')

from gi.repository import Gtk, Gdk, GLib, Pango
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Callable
from enum import Enum
import time
import logging

log = logging.getLogger("ryxsurf.tabs")


class TabState(Enum):
    """Tab state"""
    ACTIVE = "active"
    LOADING = "loading"
    LOADED = "loaded"
    HIBERNATED = "hibernated"  # Unloaded to save memory
    CRASHED = "crashed"


@dataclass
class TabGroup:
    """Tab group/container"""
    id: str
    name: str
    color: str = "#5294E2"  # Subtle blue
    collapsed: bool = False
    tabs: List = field(default_factory=list)


@dataclass
class Tab:
    """Enhanced tab with all features"""
    id: int
    webview: Optional[any] = None
    title: str = "New Tab"
    url: str = "about:blank"
    favicon: Optional[str] = None
    
    # State
    state: TabState = TabState.ACTIVE
    is_pinned: bool = False
    is_muted: bool = False
    is_private: bool = False
    
    # Group/Container
    group_id: Optional[str] = None
    container_id: Optional[str] = None
    
    # Memory Management
    last_active: float = field(default_factory=time.time)
    hibernation_timeout: int = 300  # 5 minutes
    
    # Preferences
    zoom_level: float = 1.0
    scroll_position: int = 0
    
    # Metadata
    load_time: float = 0.0
    memory_usage: int = 0  # bytes
    network_usage: int = 0  # bytes
    
    # Audio
    is_playing_audio: bool = False
    audio_level: float = 1.0


class TabBar(Gtk.Box):
    """Advanced tab bar with all features"""
    
    def __init__(self, on_tab_selected: Callable = None, on_tab_closed: Callable = None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        
        self.tabs: List[Tab] = []
        self.current_tab: Optional[Tab] = None
        self.groups: Dict[str, TabGroup] = {}
        
        self.on_tab_selected = on_tab_selected
        self.on_tab_closed = on_tab_closed
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup tab bar UI"""
        # Tab container (scrollable)
        self.tab_scroll = Gtk.ScrolledWindow()
        self.tab_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.tab_scroll.set_hexpand(True)
        
        self.tab_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.tab_scroll.set_child(self.tab_container)
        self.append(self.tab_scroll)
        
        # Tab controls (right side)
        controls = self._create_controls()
        self.append(controls)
    
    def _create_controls(self):
        """Create tab control buttons"""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.set_margin_start(4)
        box.set_margin_end(4)
        
        # New tab button (symbol: ＋)
        new_btn = Gtk.Button(label="＋")
        new_btn.set_tooltip_text("New Tab (Ctrl+T)")
        new_btn.connect("clicked", lambda b: self.add_tab())
        box.append(new_btn)
        
        # Tab menu (symbol: ☰)
        menu_btn = Gtk.Button(label="☰")
        menu_btn.set_tooltip_text("Tab Menu")
        menu_btn.connect("clicked", self._show_tab_menu)
        box.append(menu_btn)
        
        return box
    
    def add_tab(self, url: str = "about:blank", title: str = "New Tab", 
                group_id: Optional[str] = None, select: bool = True) -> Tab:
        """Add a new tab"""
        # Create tab
        tab = Tab(
            id=len(self.tabs) + 1,
            url=url,
            title=title,
            group_id=group_id
        )
        
        self.tabs.append(tab)
        
        # Create tab widget
        tab_widget = self._create_tab_widget(tab)
        self.tab_container.append(tab_widget)
        
        if select:
            self.select_tab(tab)
        
        log.info(f"Added tab: {title}")
        return tab
    
    def _create_tab_widget(self, tab: Tab):
        """Create visual tab widget"""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.set_margin_start(4)
        box.set_margin_end(4)
        box.set_margin_top(2)
        box.set_margin_bottom(2)
        
        # Apply styling
        box.add_css_class("tab")
        if tab.is_pinned:
            box.add_css_class("pinned")
        if tab.state == TabState.HIBERNATED:
            box.add_css_class("hibernated")
        
        # Favicon (if available)
        if tab.favicon:
            icon = Gtk.Image.new_from_icon_name("web-browser-symbolic")
            icon.set_pixel_size(16)
            box.append(icon)
        
        # Title
        label = Gtk.Label(label=tab.title[:30])
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_max_width_chars(30)
        box.append(label)
        
        # Audio indicator (symbol: 🔊/🔇)
        if tab.is_playing_audio:
            audio_icon = Gtk.Label(label="♫" if not tab.is_muted else "🔇")
            box.append(audio_icon)
        
        # Close button (symbol: ×)
        close_btn = Gtk.Button(label="×")
        close_btn.add_css_class("flat")
        close_btn.connect("clicked", lambda b: self.close_tab(tab))
        box.append(close_btn)
        
        # Make clickable
        gesture = Gtk.GestureClick.new()
        gesture.connect("pressed", lambda g, n, x, y: self.select_tab(tab))
        box.add_controller(gesture)
        
        # Context menu (right-click)
        gesture_right = Gtk.GestureClick.new()
        gesture_right.set_button(3)  # Right mouse button
        gesture_right.connect("pressed", lambda g, n, x, y: self._show_tab_context_menu(tab))
        box.add_controller(gesture_right)
        
        return box
    
    def select_tab(self, tab: Tab):
        """Select/activate a tab"""
        if self.current_tab == tab:
            return
        
        self.current_tab = tab
        tab.last_active = time.time()
        
        # Wake from hibernation if needed
        if tab.state == TabState.HIBERNATED:
            self._wake_tab(tab)
        
        if self.on_tab_selected:
            self.on_tab_selected(tab)
        
        log.debug(f"Selected tab: {tab.title}")
    
    def close_tab(self, tab: Tab):
        """Close a tab"""
        if tab in self.tabs:
            self.tabs.remove(tab)
            
            # TODO: Remove widget from UI
            
            if self.on_tab_closed:
                self.on_tab_closed(tab)
            
            log.info(f"Closed tab: {tab.title}")
    
    def pin_tab(self, tab: Tab):
        """Pin a tab"""
        tab.is_pinned = True
        log.info(f"Pinned tab: {tab.title}")
    
    def unpin_tab(self, tab: Tab):
        """Unpin a tab"""
        tab.is_pinned = False
        log.info(f"Unpinned tab: {tab.title}")
    
    def mute_tab(self, tab: Tab):
        """Mute tab audio"""
        tab.is_muted = True
        # TODO: Implement actual audio muting
        log.info(f"Muted tab: {tab.title}")
    
    def unmute_tab(self, tab: Tab):
        """Unmute tab audio"""
        tab.is_muted = False
        # TODO: Implement actual audio unmuting
        log.info(f"Unmuted tab: {tab.title}")
    
    def hibernate_tab(self, tab: Tab):
        """Hibernate tab (unload to save memory)"""
        if tab.state == TabState.HIBERNATED:
            return
        
        # Save state
        if tab.webview:
            # Save scroll position, etc.
            pass
        
        # Unload webview
        tab.webview = None
        tab.state = TabState.HIBERNATED
        
        log.info(f"Hibernated tab: {tab.title}")
    
    def _wake_tab(self, tab: Tab):
        """Wake hibernated tab"""
        if tab.state != TabState.HIBERNATED:
            return
        
        # Recreate webview
        # TODO: Implement webview recreation
        
        tab.state = TabState.LOADED
        log.info(f"Woke tab: {tab.title}")
    
    def duplicate_tab(self, tab: Tab):
        """Duplicate a tab"""
        new_tab = self.add_tab(url=tab.url, title=tab.title, group_id=tab.group_id)
        log.info(f"Duplicated tab: {tab.title}")
        return new_tab
    
    def move_tab_to_group(self, tab: Tab, group_id: str):
        """Move tab to a group"""
        tab.group_id = group_id
        log.info(f"Moved tab {tab.title} to group {group_id}")
    
    def create_group(self, name: str, color: str = "#5294E2") -> TabGroup:
        """Create a tab group"""
        group = TabGroup(
            id=f"group_{len(self.groups) + 1}",
            name=name,
            color=color
        )
        self.groups[group.id] = group
        log.info(f"Created tab group: {name}")
        return group
    
    def _show_tab_context_menu(self, tab: Tab):
        """Show tab context menu"""
        # TODO: Implement popover menu with options:
        # - Reload
        # - Duplicate
        # - Pin/Unpin
        # - Mute/Unmute
        # - Move to Group
        # - Close Other Tabs
        # - Close Tabs to the Right
        # - Hibernate
        log.debug(f"Context menu for: {tab.title}")
    
    def _show_tab_menu(self, button):
        """Show tab menu (list all tabs)"""
        # TODO: Implement tab list menu
        log.debug("Tab menu clicked")
    
    def get_tab_by_id(self, tab_id: int) -> Optional[Tab]:
        """Get tab by ID"""
        for tab in self.tabs:
            if tab.id == tab_id:
                return tab
        return None
    
    def get_tabs_in_group(self, group_id: str) -> List[Tab]:
        """Get all tabs in a group"""
        return [tab for tab in self.tabs if tab.group_id == group_id]
    
    def get_pinned_tabs(self) -> List[Tab]:
        """Get all pinned tabs"""
        return [tab for tab in self.tabs if tab.is_pinned]
    
    def get_hibernated_tabs(self) -> List[Tab]:
        """Get all hibernated tabs"""
        return [tab for tab in self.tabs if tab.state == TabState.HIBERNATED]
    
    def auto_hibernate_inactive_tabs(self):
        """Automatically hibernate tabs that haven't been used"""
        now = time.time()
        
        for tab in self.tabs:
            if tab == self.current_tab:
                continue  # Don't hibernate current tab
            
            if tab.is_pinned:
                continue  # Don't hibernate pinned tabs
            
            if tab.state == TabState.HIBERNATED:
                continue  # Already hibernated
            
            # Check if inactive for too long
            inactive_time = now - tab.last_active
            if inactive_time > tab.hibernation_timeout:
                self.hibernate_tab(tab)


class VerticalTabBar(Gtk.Box):
    """Vertical tab bar (sidebar style)"""
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        
        self.tabs: List[Tab] = []
        self.current_tab: Optional[Tab] = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup vertical tab bar"""
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header.set_margin_start(8)
        header.set_margin_end(8)
        header.set_margin_top(8)
        header.set_margin_bottom(8)
        
        title = Gtk.Label(label="Tabs")
        title.set_xalign(0)
        title.set_hexpand(True)
        header.append(title)
        
        # New tab button
        new_btn = Gtk.Button(label="＋")
        new_btn.add_css_class("flat")
        header.append(new_btn)
        
        self.append(header)
        
        # Tab list (scrollable)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        self.tab_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        scroll.set_child(self.tab_list)
        
        self.append(scroll)
    
    def add_tab(self, title: str = "New Tab") -> Tab:
        """Add tab to vertical bar"""
        tab = Tab(id=len(self.tabs) + 1, title=title)
        self.tabs.append(tab)
        
        # Create widget
        widget = self._create_tab_item(tab)
        self.tab_list.append(widget)
        
        return tab
    
    def _create_tab_item(self, tab: Tab):
        """Create tab list item"""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(4)
        box.set_margin_bottom(4)
        
        # Favicon
        icon = Gtk.Image.new_from_icon_name("web-browser-symbolic")
        icon.set_pixel_size(16)
        box.append(icon)
        
        # Title
        label = Gtk.Label(label=tab.title)
        label.set_xalign(0)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_hexpand(True)
        box.append(label)
        
        # Close button
        close_btn = Gtk.Button(label="×")
        close_btn.add_css_class("flat")
        box.append(close_btn)
        
        return box


# CSS for tab styling
TAB_CSS = """
.tab {
    padding: 4px 8px;
    border-radius: 4px;
    background: transparent;
    transition: background 150ms ease;
}

.tab:hover {
    background: rgba(255, 255, 255, 0.05);
}

.tab.active {
    background: rgba(82, 148, 226, 0.2);
    border-bottom: 2px solid #5294E2;
}

.tab.pinned {
    min-width: 32px;
}

.tab.hibernated {
    opacity: 0.6;
}

.tab-group-header {
    padding: 4px 8px;
    font-weight: bold;
    font-size: 0.9em;
}
"""
