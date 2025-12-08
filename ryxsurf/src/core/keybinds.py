"""
RyxSurf Keybind Manager
"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk

class KeybindManager:
    def __init__(self, window):
        self.window = window
        self.setup_keybindings()

    def setup_keybindings(self):
        # Create an event controller for key presses
        key_controller = Gtk.EventControllerKey.new(self.window)
        key_controller.connect("key-pressed", self.on_key_pressed)

    def on_key_pressed(self, controller, keyval, keycode, state):
        # Check for Ctrl+T
        if keyval == Gdk.KEY_t and state & Gdk.ModifierType.CONTROL_MASK:
            self.new_tab()
            return True

        # Check for Ctrl+W
        elif keyval == Gdk.KEY_w and state & Gdk.ModifierType.CONTROL_MASK:
            self.close_tab()
            return True

        # Check for Ctrl+L
        elif keyval == Gdk.KEY_l and state & Gdk.ModifierType.CONTROL_MASK:
            self.focus_url()
            return True

        # Check for Ctrl+Shift+A
        elif keyval == Gdk.KEY_a and state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK):
            self.toggle_ai_sidebar()
            return True

        return False

    def new_tab(self):
        print("New tab")

    def close_tab(self):
        print("Close tab")

    def focus_url(self):
        print("Focus URL")

    def toggle_ai_sidebar(self):
        print("Toggle AI sidebar")

# Example usage
if __name__ == "__main__":
    app = Gtk.Application()
    app.connect("activate", lambda app: KeybindManager(app.get_active_window()))
    app.run()