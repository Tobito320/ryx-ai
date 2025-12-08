"""
RyxSurf Context Menu

Right-click context menu with:
- Open link in new tab
- Copy link
- Save image
- Inspect element
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit', '6.0')

from gi.repository import Gtk, WebKit, Gdk, GLib
from typing import Callable, Optional


class ContextMenuHandler:
    """
    Handles right-click context menus for WebViews.
    
    Features:
    - Open link in new tab
    - Copy link address
    - Save image as
    - Inspect element
    """
    
    def __init__(
        self,
        on_open_new_tab: Callable[[str], None],
        on_save_image: Callable[[str], None],
        on_inspect: Callable[[], None]
    ):
        self.on_open_new_tab = on_open_new_tab
        self.on_save_image = on_save_image
        self.on_inspect = on_inspect
        
        self._apply_css()
        
    def setup_webview(self, webview: WebKit.WebView):
        """Connect context menu handler to a WebView"""
        webview.connect("context-menu", self._on_context_menu)
        
    def _on_context_menu(self, webview: WebKit.WebView, context_menu: WebKit.ContextMenu, 
                         hit_test_result: WebKit.HitTestResult) -> bool:
        """Handle context menu creation"""
        # Clear default menu
        context_menu.remove_all()
        
        # Check what was clicked
        is_link = hit_test_result.context_is_link()
        is_image = hit_test_result.context_is_image()
        is_media = hit_test_result.context_is_media()
        is_editable = hit_test_result.context_is_editable()
        is_selection = hit_test_result.context_is_selection()
        
        link_uri = hit_test_result.get_link_uri()
        image_uri = hit_test_result.get_image_uri()
        media_uri = hit_test_result.get_media_uri()
        
        # --- Link items ---
        if is_link and link_uri:
            # Open in new tab
            open_action = WebKit.ContextMenuItem.new_from_stock_action(
                WebKit.ContextMenuAction.OPEN_LINK_IN_NEW_WINDOW
            )
            # Override the stock action with our custom handler
            open_item = WebKit.ContextMenuItem.new_with_submenu(
                "Open link in new tab",
                WebKit.ContextMenu()
            )
            context_menu.append(
                self._create_action_item("Open link in new tab", lambda: self.on_open_new_tab(link_uri))
            )
            
            # Copy link
            context_menu.append(
                self._create_action_item("Copy link address", lambda: self._copy_to_clipboard(link_uri))
            )
            
            context_menu.append(WebKit.ContextMenuItem.new_separator())
            
        # --- Image items ---
        if is_image and image_uri:
            context_menu.append(
                self._create_action_item("Open image in new tab", lambda: self.on_open_new_tab(image_uri))
            )
            
            context_menu.append(
                self._create_action_item("Copy image address", lambda: self._copy_to_clipboard(image_uri))
            )
            
            context_menu.append(
                self._create_action_item("Save image as...", lambda: self.on_save_image(image_uri))
            )
            
            context_menu.append(WebKit.ContextMenuItem.new_separator())
            
        # --- Selection items ---
        if is_selection:
            # Add copy stock action
            copy_action = WebKit.ContextMenuItem.new_from_stock_action(
                WebKit.ContextMenuAction.COPY
            )
            context_menu.append(copy_action)
            
            context_menu.append(WebKit.ContextMenuItem.new_separator())
            
        # --- Editable items ---
        if is_editable:
            # Standard edit actions
            context_menu.append(
                WebKit.ContextMenuItem.new_from_stock_action(WebKit.ContextMenuAction.CUT)
            )
            context_menu.append(
                WebKit.ContextMenuItem.new_from_stock_action(WebKit.ContextMenuAction.COPY)
            )
            context_menu.append(
                WebKit.ContextMenuItem.new_from_stock_action(WebKit.ContextMenuAction.PASTE)
            )
            context_menu.append(
                WebKit.ContextMenuItem.new_from_stock_action(WebKit.ContextMenuAction.SELECT_ALL)
            )
            
            context_menu.append(WebKit.ContextMenuItem.new_separator())
            
        # --- Always available items ---
        
        # Back/Forward
        context_menu.append(
            WebKit.ContextMenuItem.new_from_stock_action(WebKit.ContextMenuAction.GO_BACK)
        )
        context_menu.append(
            WebKit.ContextMenuItem.new_from_stock_action(WebKit.ContextMenuAction.GO_FORWARD)
        )
        context_menu.append(
            WebKit.ContextMenuItem.new_from_stock_action(WebKit.ContextMenuAction.RELOAD)
        )
        
        context_menu.append(WebKit.ContextMenuItem.new_separator())
        
        # Inspect element
        context_menu.append(
            self._create_action_item("Inspect element", self.on_inspect)
        )
        
        # Return False to show the menu, True to suppress it
        return False
        
    def _create_action_item(self, label: str, callback: Callable) -> WebKit.ContextMenuItem:
        """Create a context menu item with a custom action"""
        from gi.repository import Gio
        
        # Create a simple action
        action = Gio.SimpleAction.new(label.lower().replace(" ", "_"), None)
        action.connect("activate", lambda a, p: callback())
        
        item = WebKit.ContextMenuItem.new_from_stock_action_with_label(
            WebKit.ContextMenuAction.CUSTOM,
            label
        )
        
        # Store callback for later execution
        item._custom_callback = callback
        
        return item
        
    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard"""
        display = Gdk.Display.get_default()
        clipboard = display.get_clipboard()
        clipboard.set(text)
        
    def _apply_css(self):
        """Apply context menu styling"""
        css = b"""
        menu, menuitem {
            background: #282a36;
            color: #f8f8f2;
        }
        
        menuitem:hover {
            background: #44475a;
        }
        
        menuitem:disabled {
            color: #6272a4;
        }
        """
        
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css)
        
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
