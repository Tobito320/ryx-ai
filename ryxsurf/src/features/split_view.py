"""
RyxSurf Split View & Picture-in-Picture
View multiple tabs side by side or floating
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit', '6.0')
from gi.repository import Gtk, WebKit, Gdk, GLib
from typing import Optional, List, Tuple
from enum import Enum
from pathlib import Path

# Theme imports (with fallback)
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from ui.theme import COLORS, SYMBOLS, SPACING
except ImportError:
    COLORS = {"border_subtle": "rgba(255,255,255,0.06)", "bg_secondary": "rgba(25,25,28,1.0)", "border_normal": "rgba(255,255,255,0.10)"}
    SYMBOLS = {"close": "×"}
    SPACING = {"xs": 4, "sm": 8}


class SplitOrientation(Enum):
    """Split view orientation"""
    HORIZONTAL = "horizontal"  # Side by side
    VERTICAL = "vertical"      # Top and bottom
    GRID = "grid"              # 2x2 grid


class SplitView(Gtk.Box):
    """Container for split view tabs"""
    
    def __init__(self, orientation: SplitOrientation = SplitOrientation.HORIZONTAL):
        if orientation == SplitOrientation.VERTICAL:
            super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        else:
            super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
            
        self.split_orientation = orientation
        self.panes = []
        self.active_pane = 0
        
        # Apply styling
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(f"""
            box {{
                background-color: {COLORS['border_subtle']};
            }}
        """.encode())
        self.get_style_context().add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
    def add_pane(self, widget: Gtk.Widget, ratio: float = 1.0) -> int:
        """Add a pane to the split view
        
        Args:
            widget: Widget to display in pane
            ratio: Size ratio (1.0 = equal size)
            
        Returns:
            Pane index
        """
        pane_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        pane_box.set_hexpand(True)
        pane_box.set_vexpand(True)
        
        # Pane header
        header = self._create_pane_header(len(self.panes))
        pane_box.append(header)
        
        # Content
        pane_box.append(widget)
        
        self.append(pane_box)
        self.panes.append({
            "box": pane_box,
            "widget": widget,
            "ratio": ratio,
        })
        
        return len(self.panes) - 1
        
    def _create_pane_header(self, pane_index: int) -> Gtk.Box:
        """Create header for a pane"""
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=SPACING['xs'])
        header.set_margin_start(SPACING['xs'])
        header.set_margin_end(SPACING['xs'])
        header.set_margin_top(SPACING['xs'])
        header.set_margin_bottom(SPACING['xs'])
        
        # Apply styling
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(f"""
            box {{
                background-color: {COLORS['bg_secondary']};
                border-bottom: 1px solid {COLORS['border_subtle']};
            }}
        """.encode())
        header.get_style_context().add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
        # Pane indicator
        indicator = Gtk.Label(label=f"Pane {pane_index + 1}")
        indicator.set_halign(Gtk.Align.START)
        indicator.set_hexpand(True)
        indicator.get_style_context().add_class("dim-label")
        header.append(indicator)
        
        # Swap button
        if pane_index > 0:
            swap_btn = Gtk.Button()
            swap_btn.set_label("⇄")
            swap_btn.set_tooltip_text("Swap with previous pane")
            swap_btn.get_style_context().add_class("flat")
            swap_btn.connect("clicked", lambda w: self._swap_panes(pane_index, pane_index - 1))
            header.append(swap_btn)
            
        # Close button
        close_btn = Gtk.Button()
        close_btn.set_label(SYMBOLS['close'])
        close_btn.set_tooltip_text("Close pane")
        close_btn.get_style_context().add_class("flat")
        close_btn.connect("clicked", lambda w: self._close_pane(pane_index))
        header.append(close_btn)
        
        return header
        
    def _swap_panes(self, index1: int, index2: int):
        """Swap two panes"""
        if 0 <= index1 < len(self.panes) and 0 <= index2 < len(self.panes):
            # Swap in list
            self.panes[index1], self.panes[index2] = self.panes[index2], self.panes[index1]
            
            # Rebuild UI
            self._rebuild()
            
    def _close_pane(self, index: int):
        """Close a pane"""
        if 0 <= index < len(self.panes):
            pane = self.panes.pop(index)
            self.remove(pane["box"])
            
            if len(self.panes) == 0:
                self.emit("all-panes-closed")
                
    def _rebuild(self):
        """Rebuild the split view"""
        # Remove all children
        while True:
            child = self.get_first_child()
            if child is None:
                break
            self.remove(child)
            
        # Re-add panes
        for i, pane in enumerate(self.panes):
            pane_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            pane_box.set_hexpand(True)
            pane_box.set_vexpand(True)
            
            header = self._create_pane_header(i)
            pane_box.append(header)
            pane_box.append(pane["widget"])
            
            self.append(pane_box)
            pane["box"] = pane_box
            
    def remove_pane(self, index: int):
        """Remove a pane by index"""
        self._close_pane(index)
        
    def get_pane_count(self) -> int:
        """Get number of panes"""
        return len(self.panes)
        
    def set_active_pane(self, index: int):
        """Set the active pane"""
        if 0 <= index < len(self.panes):
            self.active_pane = index
            

class PictureInPicture(Gtk.Window):
    """Floating picture-in-picture window"""
    
    def __init__(self, webview: WebKit.WebView, title: str = "Picture in Picture"):
        super().__init__(title=title)
        self.set_default_size(480, 270)
        self.set_decorated(True)
        self.set_deletable(True)
        
        # Keep on top
        self.set_modal(False)
        
        # Main container
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(box)
        
        # Controls bar
        controls = self._create_controls()
        box.append(controls)
        
        # WebView
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(webview)
        box.append(scroll)
        
        self.webview = webview
        
        # Make draggable
        self._setup_drag()
        
    def _create_controls(self) -> Gtk.Box:
        """Create PiP controls"""
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=SPACING['sm'])
        controls.set_margin_start(SPACING['sm'])
        controls.set_margin_end(SPACING['sm'])
        controls.set_margin_top(SPACING['xs'])
        controls.set_margin_bottom(SPACING['xs'])
        
        # Apply styling
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(f"""
            box {{
                background-color: {COLORS['bg_secondary']};
                border-bottom: 1px solid {COLORS['border_normal']};
            }}
        """.encode())
        controls.get_style_context().add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_ellipsize(3)  # END
        title_label.set_halign(Gtk.Align.START)
        title_label.set_hexpand(True)
        controls.append(title_label)
        self.title_label = title_label
        
        # Return to tab button
        return_btn = Gtk.Button()
        return_btn.set_label("↩")
        return_btn.set_tooltip_text("Return to tab")
        return_btn.get_style_context().add_class("flat")
        return_btn.connect("clicked", lambda w: self.emit("return-to-tab"))
        controls.append(return_btn)
        
        # Opacity slider
        opacity_btn = Gtk.Button()
        opacity_btn.set_label("◐")
        opacity_btn.set_tooltip_text("Adjust opacity")
        opacity_btn.get_style_context().add_class("flat")
        opacity_btn.connect("clicked", lambda w: self._toggle_opacity())
        controls.append(opacity_btn)
        
        # Size buttons
        for size, label in [("small", "S"), ("medium", "M"), ("large", "L")]:
            btn = Gtk.Button()
            btn.set_label(label)
            btn.set_tooltip_text(f"Size: {size}")
            btn.get_style_context().add_class("flat")
            btn.connect("clicked", lambda w, s=size: self._set_size(s))
            controls.append(btn)
            
        # Close button
        close_btn = Gtk.Button()
        close_btn.set_label(SYMBOLS['close'])
        close_btn.get_style_context().add_class("flat")
        close_btn.connect("clicked", lambda w: self.close())
        controls.append(close_btn)
        
        return controls
        
    def _setup_drag(self):
        """Setup window dragging"""
        # GTK4 handles this automatically with decorated window
        pass
        
    def _toggle_opacity(self):
        """Toggle between opaque and semi-transparent"""
        current = self.get_opacity()
        if current >= 1.0:
            self.set_opacity(0.7)
        elif current >= 0.7:
            self.set_opacity(0.5)
        else:
            self.set_opacity(1.0)
            
    def _set_size(self, size: str):
        """Set PiP window size"""
        sizes = {
            "small": (320, 180),
            "medium": (480, 270),
            "large": (640, 360),
        }
        if size in sizes:
            width, height = sizes[size]
            self.set_default_size(width, height)
            
    def update_title(self, title: str):
        """Update PiP title"""
        self.title_label.set_text(title)


class SplitViewManager:
    """Manage split views and PiP windows"""
    
    def __init__(self, main_window: Gtk.Window):
        self.main_window = main_window
        self.split_views: List[SplitView] = []
        self.pip_windows: List[PictureInPicture] = []
        
    def create_split_view(self, orientation: SplitOrientation = SplitOrientation.HORIZONTAL) -> SplitView:
        """Create a new split view"""
        split = SplitView(orientation)
        split.connect("all-panes-closed", lambda w: self._on_split_closed(w))
        self.split_views.append(split)
        return split
        
    def _on_split_closed(self, split_view: SplitView):
        """Handle split view closed"""
        if split_view in self.split_views:
            self.split_views.remove(split_view)
            
    def create_pip(self, webview: WebKit.WebView, title: str = "Picture in Picture") -> PictureInPicture:
        """Create a new PiP window"""
        pip = PictureInPicture(webview, title)
        pip.set_transient_for(self.main_window)
        pip.connect("return-to-tab", lambda w: self._on_pip_return(w))
        pip.connect("close-request", lambda w: self._on_pip_closed(w))
        self.pip_windows.append(pip)
        pip.present()
        return pip
        
    def _on_pip_return(self, pip: PictureInPicture):
        """Handle return to tab from PiP"""
        # Emit signal for main window to handle
        self.emit("pip-return-to-tab", pip)
        pip.close()
        
    def _on_pip_closed(self, pip: PictureInPicture):
        """Handle PiP window closed"""
        if pip in self.pip_windows:
            self.pip_windows.remove(pip)
        return False  # Allow close
        
    def close_all_pip(self):
        """Close all PiP windows"""
        for pip in self.pip_windows[:]:
            pip.close()
        self.pip_windows.clear()
        
    def get_pip_count(self) -> int:
        """Get number of active PiP windows"""
        return len(self.pip_windows)


# Register custom signals
from gi.repository import GObject
GObject.signal_new("all-panes-closed", SplitView, GObject.SignalFlags.RUN_FIRST, None, ())
GObject.signal_new("return-to-tab", PictureInPicture, GObject.SignalFlags.RUN_FIRST, None, ())
GObject.signal_new("pip-return-to-tab", SplitViewManager, GObject.SignalFlags.RUN_FIRST, None, (object,))
