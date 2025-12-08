"""
RyxSurf Bookmarks Bar

Horizontal bar showing bookmark buttons for quick access.
Toggle with Ctrl+Shift+B.
"""

import gi
gi.require_version('Gtk', '4.0')

from gi.repository import Gtk, Gdk, Pango
from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.bookmarks import BookmarkManager, Bookmark


class BookmarksBar(Gtk.Box):
    """
    Horizontal bookmarks bar widget.
    
    Shows bookmarks from the bookmark bar (no folder).
    Hidden by default, toggle with Ctrl+Shift+B.
    """
    
    def __init__(self, bookmark_manager: 'BookmarkManager', on_navigate: Callable[[str], None]):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        
        self.bookmark_manager = bookmark_manager
        self.on_navigate = on_navigate
        
        self._setup_ui()
        self._apply_css()
        self.set_visible(False)
        
    def _setup_ui(self):
        """Setup bookmarks bar UI"""
        self.add_css_class("bookmarks-bar")
        self.set_spacing(4)
        self.set_margin_start(10)
        self.set_margin_end(10)
        self.set_margin_top(2)
        self.set_margin_bottom(2)
        
        # Scrollable container for bookmarks
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.scroll.set_hexpand(True)
        
        self.bookmarks_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.scroll.set_child(self.bookmarks_box)
        self.append(self.scroll)
        
    def refresh(self):
        """Refresh bookmarks from manager"""
        # Clear existing
        while child := self.bookmarks_box.get_first_child():
            self.bookmarks_box.remove(child)
            
        # Add bookmark buttons
        for bookmark in self.bookmark_manager.get_bar_bookmarks():
            btn = self._create_bookmark_button(bookmark)
            self.bookmarks_box.append(btn)
            
    def _create_bookmark_button(self, bookmark: 'Bookmark') -> Gtk.Button:
        """Create a bookmark button"""
        # Truncate title
        title = bookmark.title[:20] if len(bookmark.title) > 20 else bookmark.title
        if not title:
            title = bookmark.domain or bookmark.url[:20]
        
        btn = Gtk.Button(label=f"★ {title}")
        btn.add_css_class("bookmark-btn")
        btn.set_tooltip_text(f"{bookmark.title}\n{bookmark.url}")
        
        # Left-click to navigate
        btn.connect("clicked", lambda _, url=bookmark.url: self.on_navigate(url))
        
        # Right-click for context menu
        gesture = Gtk.GestureClick()
        gesture.set_button(3)  # Right button
        gesture.connect("pressed", lambda g, n, x, y, bm=bookmark: self._show_context_menu(g, bm, x, y))
        btn.add_controller(gesture)
        
        return btn
        
    def _show_context_menu(self, gesture, bookmark: 'Bookmark', x: float, y: float):
        """Show context menu for bookmark"""
        menu = Gtk.PopoverMenu()
        
        menu_model = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        menu_model.set_margin_start(8)
        menu_model.set_margin_end(8)
        menu_model.set_margin_top(8)
        menu_model.set_margin_bottom(8)
        
        # Delete bookmark option
        delete_btn = Gtk.Button(label="Remove bookmark")
        delete_btn.add_css_class("bookmark-menu-item")
        delete_btn.connect("clicked", lambda _: self._delete_bookmark(bookmark, menu))
        menu_model.append(delete_btn)
        
        menu.set_child(menu_model)
        
        # Position and show
        widget = gesture.get_widget()
        menu.set_parent(widget)
        menu.popup()
        
    def _delete_bookmark(self, bookmark: 'Bookmark', menu: Gtk.PopoverMenu):
        """Delete a bookmark"""
        self.bookmark_manager.remove(bookmark.url)
        menu.popdown()
        self.refresh()
        
    def show(self):
        """Show the bookmarks bar"""
        self.refresh()
        self.set_visible(True)
        
    def hide(self):
        """Hide the bookmarks bar"""
        self.set_visible(False)
        
    def toggle(self):
        """Toggle visibility"""
        if self.get_visible():
            self.hide()
        else:
            self.show()
            
    def _apply_css(self):
        """Apply bookmarks bar styling"""
        css = b"""
        .bookmarks-bar {
            background: rgba(40, 42, 54, 0.85);
            border-bottom: 1px solid rgba(68, 71, 90, 0.5);
            padding: 4px 8px;
            min-height: 32px;
        }
        
        .bookmark-btn {
            background: rgba(68, 71, 90, 0.4);
            color: #f8f8f2;
            border: none;
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 12px;
        }
        
        .bookmark-btn:hover {
            background: rgba(98, 114, 164, 0.6);
        }
        
        .bookmark-menu-item {
            background: transparent;
            color: #f8f8f2;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }
        
        .bookmark-menu-item:hover {
            background: rgba(255, 85, 85, 0.3);
            color: #ff5555;
        }
        """
        
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css)
        
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
