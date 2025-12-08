"""
RyxSurf - Adwaita-based Browser
Clean, minimal, professional UI using libadwaita.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('WebKit', '6.0')

from gi.repository import Gtk, Adw, WebKit, GLib, Gdk, Gio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List
import json
import time

# Config
CONFIG_DIR = Path.home() / ".config" / "ryxsurf"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class Tab:
    """Browser tab data"""
    webview: WebKit.WebView
    title: str = "New Tab"
    url: str = "about:blank"
    favicon: Optional[str] = None


class RyxSurfWindow(Adw.ApplicationWindow):
    """Main browser window using Adwaita"""
    
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("RyxSurf")
        self.set_default_size(1200, 800)
        
        self.tabs: List[Tab] = []
        self.active_tab = 0
        
        self._build_ui()
        self._setup_keybinds()
        self._new_tab()
    
    def _build_ui(self):
        """Build the Adwaita UI"""
        # Main layout: sidebar + content
        self.split_view = Adw.OverlaySplitView()
        self.split_view.set_collapsed(False)
        self.split_view.set_show_sidebar(True)
        self.split_view.set_min_sidebar_width(200)
        self.split_view.set_max_sidebar_width(300)
        self.set_content(self.split_view)
        
        # === SIDEBAR (tabs) ===
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar_box.add_css_class("sidebar")
        
        # Sidebar header
        sidebar_header = Adw.HeaderBar()
        sidebar_header.set_show_end_title_buttons(False)
        sidebar_header.set_show_start_title_buttons(False)
        sidebar_header.set_title_widget(Gtk.Label(label="Tabs"))
        
        # New tab button in header
        new_tab_btn = Gtk.Button(icon_name="tab-new-symbolic")
        new_tab_btn.add_css_class("flat")
        new_tab_btn.connect("clicked", lambda _: self._new_tab())
        sidebar_header.pack_end(new_tab_btn)
        
        sidebar_box.append(sidebar_header)
        
        # Tab list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        
        self.tab_list = Gtk.ListBox()
        self.tab_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.tab_list.add_css_class("navigation-sidebar")
        self.tab_list.connect("row-selected", self._on_tab_selected)
        scroll.set_child(self.tab_list)
        sidebar_box.append(scroll)
        
        self.split_view.set_sidebar(sidebar_box)
        
        # === CONTENT (toolbar + webview) ===
        content_box = Adw.ToolbarView()
        
        # Top toolbar with navigation
        header = Adw.HeaderBar()
        header.set_show_start_title_buttons(False)
        
        # Navigation buttons
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        
        self.back_btn = Gtk.Button(icon_name="go-previous-symbolic")
        self.back_btn.add_css_class("flat")
        self.back_btn.set_tooltip_text("Back")
        self.back_btn.connect("clicked", lambda _: self._go_back())
        nav_box.append(self.back_btn)
        
        self.fwd_btn = Gtk.Button(icon_name="go-next-symbolic")
        self.fwd_btn.add_css_class("flat")
        self.fwd_btn.set_tooltip_text("Forward")
        self.fwd_btn.connect("clicked", lambda _: self._go_forward())
        nav_box.append(self.fwd_btn)
        
        self.reload_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        self.reload_btn.add_css_class("flat")
        self.reload_btn.set_tooltip_text("Reload")
        self.reload_btn.connect("clicked", lambda _: self._reload())
        nav_box.append(self.reload_btn)
        
        header.pack_start(nav_box)
        
        # URL entry - centered, takes most space
        self.url_entry = Gtk.Entry()
        self.url_entry.set_hexpand(True)
        self.url_entry.set_placeholder_text("Search or enter URL...")
        self.url_entry.add_css_class("url-entry")
        self.url_entry.connect("activate", self._on_url_activate)
        header.set_title_widget(self.url_entry)
        
        # Menu button
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu_btn.add_css_class("flat")
        header.pack_end(menu_btn)
        
        content_box.add_top_bar(header)
        
        # WebView container
        self.webview_stack = Gtk.Stack()
        self.webview_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        content_box.set_content(self.webview_stack)
        
        self.split_view.set_content(content_box)
    
    def _setup_keybinds(self):
        """Setup keyboard shortcuts"""
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self._on_key_press)
        self.add_controller(controller)
    
    def _on_key_press(self, controller, keyval, keycode, state):
        ctrl = state & Gdk.ModifierType.CONTROL_MASK
        
        if ctrl:
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
                self._reload()
                return True
            elif keyval == Gdk.KEY_Tab:
                self._next_tab()
                return True
        
        return False
    
    def _new_tab(self, url: str = None):
        """Create new tab"""
        webview = WebKit.WebView()
        settings = webview.get_settings()
        settings.set_enable_javascript(True)
        settings.set_hardware_acceleration_policy(WebKit.HardwareAccelerationPolicy.ALWAYS)
        settings.set_enable_webgl(True)
        settings.set_enable_smooth_scrolling(True)
        
        tab = Tab(webview=webview, url=url or "about:blank")
        
        # Connect signals
        webview.connect("notify::title", lambda w, p: self._on_title_changed(tab))
        webview.connect("notify::uri", lambda w, p: self._on_uri_changed(tab))
        
        self.tabs.append(tab)
        
        # Add to stack
        self.webview_stack.add_named(webview, f"tab-{len(self.tabs)-1}")
        
        # Add to tab list
        self._update_tab_list()
        
        # Switch to new tab
        self._switch_to_tab(len(self.tabs) - 1)
        
        # Load URL or new tab page
        if url:
            webview.load_uri(url)
        else:
            self._load_newtab_page(webview)
            GLib.idle_add(lambda: self.url_entry.grab_focus())
    
    def _load_newtab_page(self, webview):
        """Load beautiful new tab page"""
        html = '''<!DOCTYPE html>
<html><head><style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-family: system-ui, -apple-system, sans-serif;
    color: #e8e8e8;
    gap: 32px;
}
.logo {
    font-size: 56px;
    font-weight: 300;
    background: linear-gradient(90deg, #a855f7, #6366f1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -2px;
}
.search-box {
    display: flex;
    align-items: center;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 28px;
    padding: 12px 24px;
    width: 560px;
    transition: all 200ms;
}
.search-box:focus-within {
    background: rgba(255,255,255,0.12);
    border-color: rgba(168,85,247,0.5);
    box-shadow: 0 0 0 4px rgba(168,85,247,0.15);
}
.search-icon { color: #888; margin-right: 12px; font-size: 18px; }
.search-input {
    flex: 1;
    background: none;
    border: none;
    color: #fff;
    font-size: 16px;
    outline: none;
}
.search-input::placeholder { color: #666; }
.shortcuts {
    display: flex;
    gap: 20px;
    margin-top: 24px;
}
.shortcut {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    padding: 20px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    text-decoration: none;
    color: inherit;
    width: 100px;
    transition: all 200ms;
}
.shortcut:hover {
    background: rgba(255,255,255,0.08);
    transform: translateY(-4px);
    border-color: rgba(168,85,247,0.3);
}
.shortcut-icon { font-size: 28px; }
.shortcut-name { font-size: 12px; color: #888; }
.hint {
    position: fixed;
    bottom: 24px;
    color: #555;
    font-size: 13px;
}
kbd {
    background: rgba(255,255,255,0.1);
    padding: 3px 8px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 12px;
}
</style></head><body>
<div class="logo">RyxSurf</div>
<div class="search-box">
    <span class="search-icon">🔍</span>
    <input class="search-input" placeholder="Search or enter URL..." autofocus
        onkeydown="if(event.key==='Enter'){let q=this.value;window.location=q.includes('.')?'https://'+q.replace(/^https?:\\/\\//,''):'https://duckduckgo.com/?q='+encodeURIComponent(q)}">
</div>
<div class="shortcuts">
    <a class="shortcut" href="https://github.com"><div class="shortcut-icon">🐙</div><div class="shortcut-name">GitHub</div></a>
    <a class="shortcut" href="https://youtube.com"><div class="shortcut-icon">▶️</div><div class="shortcut-name">YouTube</div></a>
    <a class="shortcut" href="https://reddit.com"><div class="shortcut-icon">🔮</div><div class="shortcut-name">Reddit</div></a>
    <a class="shortcut" href="https://duckduckgo.com"><div class="shortcut-icon">🦆</div><div class="shortcut-name">Search</div></a>
    <a class="shortcut" href="https://twitter.com"><div class="shortcut-icon">🐦</div><div class="shortcut-name">Twitter</div></a>
</div>
<div class="hint"><kbd>Ctrl+T</kbd> New tab · <kbd>Ctrl+L</kbd> Focus URL · <kbd>Ctrl+W</kbd> Close tab</div>
</body></html>'''
        webview.load_html(html, "about:newtab")
    
    def _update_tab_list(self):
        """Update the sidebar tab list"""
        # Clear existing
        while True:
            row = self.tab_list.get_row_at_index(0)
            if row:
                self.tab_list.remove(row)
            else:
                break
        
        # Add tabs
        for i, tab in enumerate(self.tabs):
            row = Adw.ActionRow()
            row.set_title(tab.title or "New Tab")
            row.set_subtitle(self._truncate_url(tab.url))
            row.add_css_class("tab-row")
            
            # Close button
            close_btn = Gtk.Button(icon_name="window-close-symbolic")
            close_btn.add_css_class("flat")
            close_btn.add_css_class("circular")
            close_btn.set_valign(Gtk.Align.CENTER)
            close_btn.connect("clicked", lambda _, idx=i: self._close_tab(idx))
            row.add_suffix(close_btn)
            
            self.tab_list.append(row)
        
        # Select active
        if self.tabs:
            row = self.tab_list.get_row_at_index(self.active_tab)
            if row:
                self.tab_list.select_row(row)
    
    def _truncate_url(self, url: str, max_len: int = 40) -> str:
        """Truncate URL for display"""
        if not url:
            return ""
        url = url.replace("https://", "").replace("http://", "").replace("www.", "")
        return url[:max_len] + "..." if len(url) > max_len else url
    
    def _on_tab_selected(self, listbox, row):
        """Handle tab selection from sidebar"""
        if row:
            idx = row.get_index()
            if idx != self.active_tab:
                self._switch_to_tab(idx)
    
    def _switch_to_tab(self, idx: int):
        """Switch to tab by index"""
        if 0 <= idx < len(self.tabs):
            self.active_tab = idx
            tab = self.tabs[idx]
            self.webview_stack.set_visible_child_name(f"tab-{idx}")
            self.url_entry.set_text(tab.url if tab.url != "about:newtab" else "")
            self._update_nav_buttons()
    
    def _close_tab(self, idx: int = None):
        """Close tab"""
        if idx is None:
            idx = self.active_tab
        
        if len(self.tabs) <= 1:
            # Reset single tab
            self.tabs[0].webview.load_uri("about:blank")
            self._load_newtab_page(self.tabs[0].webview)
            return
        
        # Remove from stack
        webview = self.tabs[idx].webview
        self.webview_stack.remove(webview)
        
        # Remove from list
        self.tabs.pop(idx)
        
        # Adjust active tab
        if self.active_tab >= len(self.tabs):
            self.active_tab = len(self.tabs) - 1
        
        self._update_tab_list()
        self._switch_to_tab(self.active_tab)
    
    def _next_tab(self):
        """Switch to next tab"""
        if self.tabs:
            self._switch_to_tab((self.active_tab + 1) % len(self.tabs))
    
    def _on_url_activate(self, entry):
        """Handle URL entry activation"""
        text = entry.get_text().strip()
        if not text:
            return
        
        # Check if it's a URL or search
        if "." in text and " " not in text:
            if not text.startswith(("http://", "https://")):
                text = "https://" + text
            self.tabs[self.active_tab].webview.load_uri(text)
        else:
            # Search
            query = text.replace(" ", "+")
            self.tabs[self.active_tab].webview.load_uri(f"https://duckduckgo.com/?q={query}")
    
    def _on_title_changed(self, tab: Tab):
        """Handle title change"""
        tab.title = tab.webview.get_title() or "New Tab"
        self._update_tab_list()
        if tab == self.tabs[self.active_tab]:
            self.set_title(f"{tab.title} - RyxSurf")
    
    def _on_uri_changed(self, tab: Tab):
        """Handle URI change"""
        tab.url = tab.webview.get_uri() or "about:blank"
        if tab == self.tabs[self.active_tab]:
            if tab.url != "about:newtab":
                self.url_entry.set_text(tab.url)
        self._update_nav_buttons()
    
    def _update_nav_buttons(self):
        """Update navigation button sensitivity"""
        if self.tabs:
            webview = self.tabs[self.active_tab].webview
            self.back_btn.set_sensitive(webview.can_go_back())
            self.fwd_btn.set_sensitive(webview.can_go_forward())
    
    def _go_back(self):
        if self.tabs:
            self.tabs[self.active_tab].webview.go_back()
    
    def _go_forward(self):
        if self.tabs:
            self.tabs[self.active_tab].webview.go_forward()
    
    def _reload(self):
        if self.tabs:
            self.tabs[self.active_tab].webview.reload()


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
