"""
RyxSurf Tab Sidebar - Minimal Tab List

A toggleable sidebar showing:
- Current tabs with favicons
- Session indicator
- Quick session switch
"""

import gi
gi.require_version('Gtk', '4.0')

from gi.repository import Gtk, Gdk, GLib, Pango
from typing import List, Callable, Optional
from dataclasses import dataclass


@dataclass
class TabInfo:
    """Tab information for display"""
    id: int
    title: str
    url: str
    favicon: Optional[str] = None
    is_active: bool = False
    is_loading: bool = False
    is_unloaded: bool = False


class TabSidebar(Gtk.Box):
    """
    Vertical tab sidebar.
    
    Features:
    - Compact tab list with favicons
    - Session color indicator
    - Click to switch, middle-click to close
    - Keyboard navigation
    """
    
    def __init__(
        self,
        on_tab_select: Callable[[int], None],
        on_tab_close: Callable[[int], None],
        on_session_click: Callable[[], None]
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        
        self.on_tab_select = on_tab_select
        self.on_tab_close = on_tab_close
        self.on_session_click = on_session_click
        
        self.tabs: List[TabInfo] = []
        self.session_name = "default"
        self.session_color = "#bd93f9"
        
        self._setup_ui()
        self._apply_css()
        
    def _setup_ui(self):
        """Setup sidebar UI"""
        self.set_size_request(250, -1)
        self.add_css_class("tab-sidebar")
        
        # Session header
        self.session_button = Gtk.Button()
        self.session_button.add_css_class("session-button")
        self.session_button.connect("clicked", lambda _: self.on_session_click())
        
        session_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        self.session_indicator = Gtk.Box()
        self.session_indicator.set_size_request(12, 12)
        self.session_indicator.add_css_class("session-indicator")
        session_box.append(self.session_indicator)
        
        self.session_label = Gtk.Label(label="Default")
        self.session_label.set_halign(Gtk.Align.START)
        self.session_label.set_hexpand(True)
        session_box.append(self.session_label)
        
        self.session_button.set_child(session_box)
        self.append(self.session_button)
        
        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.append(sep)
        
        # Tab list (scrollable)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        
        self.tab_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.tab_list.set_margin_top(4)
        self.tab_list.set_margin_bottom(4)
        scroll.set_child(self.tab_list)
        
        self.append(scroll)
        
    def update_tabs(self, tabs: List[TabInfo]):
        """Update the tab list"""
        self.tabs = tabs
        
        # Clear existing
        while child := self.tab_list.get_first_child():
            self.tab_list.remove(child)
            
        # Add tabs
        for tab in tabs:
            row = self._create_tab_row(tab)
            self.tab_list.append(row)
            
    def _create_tab_row(self, tab: TabInfo) -> Gtk.Button:
        """Create a single tab row"""
        btn = Gtk.Button()
        btn.add_css_class("tab-row")
        if tab.is_active:
            btn.add_css_class("active")
        if tab.is_unloaded:
            btn.add_css_class("unloaded")
            
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        
        # Favicon placeholder
        favicon = Gtk.Label(label="●")
        favicon.add_css_class("favicon")
        box.append(favicon)
        
        # Title (truncated)
        title = Gtk.Label(label=tab.title[:30])
        title.set_halign(Gtk.Align.START)
        title.set_hexpand(True)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        title.add_css_class("tab-title")
        box.append(title)
        
        # Close button (shown on hover via CSS)
        close_btn = Gtk.Button(label="×")
        close_btn.add_css_class("tab-close")
        close_btn.connect("clicked", lambda _, tid=tab.id: self.on_tab_close(tid))
        box.append(close_btn)
        
        btn.set_child(box)
        btn.connect("clicked", lambda _, tid=tab.id: self.on_tab_select(tid))
        
        return btn
        
    def set_session(self, name: str, color: str):
        """Update session display"""
        self.session_name = name
        self.session_color = color
        self.session_label.set_text(name.title())
        
        # Update indicator color via CSS custom property workaround
        self.session_indicator.set_name(f"session-{color.replace('#', '')}")
        
    def _apply_css(self):
        """Apply sidebar CSS"""
        css = b"""
        .tab-sidebar {
            background: #21222c;
            border-right: 1px solid #44475a;
        }
        
        .session-button {
            background: transparent;
            border: none;
            border-radius: 0;
            padding: 12px;
        }
        
        .session-button:hover {
            background: #44475a;
        }
        
        .session-indicator {
            background: #bd93f9;
            border-radius: 50%;
        }
        
        .tab-row {
            background: transparent;
            border: none;
            border-radius: 4px;
            margin: 0 4px;
        }
        
        .tab-row:hover {
            background: #44475a;
        }
        
        .tab-row.active {
            background: #44475a;
            border-left: 3px solid #bd93f9;
        }
        
        .tab-row.unloaded .tab-title {
            color: #6272a4;
            font-style: italic;
        }
        
        .favicon {
            color: #6272a4;
            font-size: 10px;
        }
        
        .tab-title {
            color: #f8f8f2;
            font-size: 13px;
        }
        
        .tab-close {
            background: transparent;
            border: none;
            color: #6272a4;
            opacity: 0;
            padding: 2px 6px;
            border-radius: 4px;
        }
        
        .tab-row:hover .tab-close {
            opacity: 1;
        }
        
        .tab-close:hover {
            background: #ff5555;
            color: #f8f8f2;
        }
        """
        
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css)
        
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
