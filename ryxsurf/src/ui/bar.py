"""
RyxSurf URL Bar - Minimal URL/Command Input

A popup overlay for:
- Entering URLs
- AI commands (prefix with !)
- Quick searches (prefix with ?)
"""

import gi
gi.require_version('Gtk', '4.0')

from gi.repository import Gtk, Gdk, GLib
from typing import Callable, Optional
from enum import Enum


class InputType(Enum):
    URL = "url"
    AI_COMMAND = "ai"
    SEARCH = "search"


class URLBar:
    """
    Minimal URL/command bar overlay.
    
    Activated by Super+g (URL) or Super+a (AI).
    Styled to match Hyprland/Dracula aesthetic.
    """
    
    def __init__(self, on_submit: Callable[[str, InputType], None]):
        self.on_submit = on_submit
        self.overlay: Optional[Gtk.Window] = None
        self.entry: Optional[Gtk.Entry] = None
        self.input_type = InputType.URL
        
    def show(self, parent: Gtk.Window, input_type: InputType = InputType.URL, initial_text: str = ""):
        """Show the URL bar overlay"""
        self.input_type = input_type
        
        # Create overlay window
        self.overlay = Gtk.Window()
        self.overlay.set_transient_for(parent)
        self.overlay.set_modal(True)
        self.overlay.set_decorated(False)
        
        # Position at top center
        self.overlay.set_default_size(600, -1)
        
        # Main container with styling
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        
        # Label showing mode
        mode_label = Gtk.Label()
        if input_type == InputType.AI_COMMAND:
            mode_label.set_text("AI Command")
            mode_label.add_css_class("ai-mode")
        elif input_type == InputType.SEARCH:
            mode_label.set_text("Search")
            mode_label.add_css_class("search-mode")
        else:
            mode_label.set_text("Go to URL")
            mode_label.add_css_class("url-mode")
        mode_label.set_halign(Gtk.Align.START)
        box.append(mode_label)
        
        # Entry field
        self.entry = Gtk.Entry()
        self.entry.set_text(initial_text)
        self.entry.set_placeholder_text(self._get_placeholder())
        self.entry.add_css_class("url-entry")
        
        # Connect signals
        self.entry.connect("activate", self._on_activate)
        
        # Key handler for escape
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_press)
        self.entry.add_controller(key_controller)
        
        box.append(self.entry)
        
        # Add CSS
        self._apply_css()
        
        self.overlay.set_child(box)
        self.overlay.present()
        
        # Focus entry
        self.entry.grab_focus()
        
    def show_centered(self):
        """Show the URL bar overlay centered on the screen"""
        screen = Gdk.Display.get_default().get_monitors()[0].get_geometry()
        screen_width = screen.width
        screen_height = screen.height
        
        x_position = (screen_width - 600) // 2
        y_position = 50
        
        self.overlay.move(x_position, y_position)
        self.overlay.present()
        
    def _get_placeholder(self) -> str:
        if self.input_type == InputType.AI_COMMAND:
            return "Ask AI: summarize, dismiss popup, click login..."
        elif self.input_type == InputType.SEARCH:
            return "Search the web..."
        else:
            return "Enter URL or search term..."
            
    def _on_activate(self, entry: Gtk.Entry):
        """Handle enter key"""
        text = entry.get_text().strip()
        if text:
            # Detect type from prefix
            if text.startswith("!"):
                self.on_submit(text[1:], InputType.AI_COMMAND)
            elif text.startswith("?"):
                self.on_submit(text[1:], InputType.SEARCH)
            elif self.input_type == InputType.AI_COMMAND:
                self.on_submit(text, InputType.AI_COMMAND)
            elif "." in text or text.startswith("http"):
                self.on_submit(text, InputType.URL)
            else:
                self.on_submit(text, InputType.SEARCH)
                
        self.hide()
        
    def _on_key_press(self, controller, keyval, keycode, state):
        """Handle escape to close"""
        if Gdk.keyval_name(keyval) == "Escape":
            self.hide()
            return True
        return False
        
    def hide(self):
        """Hide the overlay"""
        if self.overlay:
            self.overlay.close()
            self.overlay = None
            
    def _apply_css(self):
        """Apply Dracula-themed CSS"""
        css = b"""
        window {
            background: #282a36;
            border: 2px solid #bd93f9;
            border-radius: 8px;
        }
        
        .url-entry {
            background: #44475a;
            color: #f8f8f2;
            border: none;
            border-radius: 4px;
            padding: 12px;
            font-size: 16px;
            margin-top: 8px;
        }
        
        .url-entry:focus {
            outline: none;
            box-shadow: 0 0 0 2px #bd93f9;
        }
        
        label {
            color: #6272a4;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
        }
        
        .ai-mode {
            color: #ff79c6;
        }
        
        .search-mode {
            color: #50fa7b;
        }
        
        .url-mode {
            color: #8be9fd;
        }
        """
        
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css)
        
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )