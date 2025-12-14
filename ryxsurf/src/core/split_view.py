"""
Split View - Zen Browser Feature

Allows viewing multiple tabs side-by-side.
Supports 2, 3, or 4 tab layouts with resizable panes.
"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
from typing import List, Optional, Tuple, Callable
import logging

log = logging.getLogger("ryxsurf.split_view")


class SplitPane(Gtk.Box):
    """A single pane in split view"""
    
    def __init__(self, tab_id: int, webview):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.tab_id = tab_id
        self.webview = webview
        
        self.add_css_class("split-pane")
        
        # Header with tab info
        self._create_header()
        
        # Webview container
        self.append(webview)
    
    def _create_header(self):
        """Create minimal header for the pane"""
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header.add_css_class("split-pane-header")
        header.set_spacing(4)
        
        # Tab title
        self.title_label = Gtk.Label(label="Loading...")
        self.title_label.add_css_class("split-pane-title")
        self.title_label.set_halign(Gtk.Align.START)
        self.title_label.set_hexpand(True)
        self.title_label.set_ellipsize(3)  # ELLIPSIZE_END
        header.append(self.title_label)
        
        # Close button
        close_btn = Gtk.Button(label="×")
        close_btn.add_css_class("split-pane-close")
        close_btn.connect("clicked", lambda _: self.emit_close())
        header.append(close_btn)
        
        self.prepend(header)
    
    def update_title(self, title: str):
        """Update pane title"""
        self.title_label.set_text(title[:40])
    
    def emit_close(self):
        """Signal to close this pane"""
        # Will be connected by SplitView
        pass


class SplitView:
    """Manages split view layouts"""
    
    def __init__(self, on_layout_change: Callable):
        self.on_layout_change = on_layout_change
        self.layout: str = "single"  # single, vertical, horizontal, grid
        self.panes: List[SplitPane] = []
        self.container: Optional[Gtk.Box] = None
    
    def set_layout(self, layout: str, tabs: List[Tuple[int, any]]):
        """
        Set split view layout
        
        Args:
            layout: single, vertical, horizontal, grid (2x2)
            tabs: List of (tab_id, webview) tuples
        """
        if layout not in ["single", "vertical", "horizontal", "grid"]:
            log.warning(f"Invalid layout: {layout}")
            return
        
        self.layout = layout
        self.panes.clear()
        
        # Clear existing container
        if self.container:
            self._clear_container()
        
        # Create new layout
        if layout == "single":
            self.container = None
            return
        elif layout == "vertical":
            self.container = self._create_vertical_layout(tabs)
        elif layout == "horizontal":
            self.container = self._create_horizontal_layout(tabs)
        elif layout == "grid":
            self.container = self._create_grid_layout(tabs)
        
        self.on_layout_change(self.container)
    
    def _create_vertical_layout(self, tabs: List[Tuple[int, any]]) -> Gtk.Box:
        """Create vertical split (side-by-side)"""
        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        container.add_css_class("split-view")
        container.set_homogeneous(True)
        container.set_spacing(1)
        
        for tab_id, webview in tabs[:2]:  # Max 2 for vertical
            pane = SplitPane(tab_id, webview)
            self.panes.append(pane)
            container.append(pane)
        
        return container
    
    def _create_horizontal_layout(self, tabs: List[Tuple[int, any]]) -> Gtk.Box:
        """Create horizontal split (top-bottom)"""
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        container.add_css_class("split-view")
        container.set_homogeneous(True)
        container.set_spacing(1)
        
        for tab_id, webview in tabs[:2]:  # Max 2 for horizontal
            pane = SplitPane(tab_id, webview)
            self.panes.append(pane)
            container.append(pane)
        
        return container
    
    def _create_grid_layout(self, tabs: List[Tuple[int, any]]) -> Gtk.Box:
        """Create 2x2 grid layout"""
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        container.add_css_class("split-view")
        container.set_homogeneous(True)
        container.set_spacing(1)
        
        # Top row
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        top_row.set_homogeneous(True)
        top_row.set_spacing(1)
        
        for tab_id, webview in tabs[:2]:
            pane = SplitPane(tab_id, webview)
            self.panes.append(pane)
            top_row.append(pane)
        
        container.append(top_row)
        
        # Bottom row
        if len(tabs) > 2:
            bottom_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            bottom_row.set_homogeneous(True)
            bottom_row.set_spacing(1)
            
            for tab_id, webview in tabs[2:4]:
                pane = SplitPane(tab_id, webview)
                self.panes.append(pane)
                bottom_row.append(pane)
            
            container.append(bottom_row)
        
        return container
    
    def _clear_container(self):
        """Clear all panes from container"""
        if not self.container:
            return
        
        child = self.container.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.container.remove(child)
            child = next_child
    
    def update_pane_title(self, tab_id: int, title: str):
        """Update title for a specific pane"""
        for pane in self.panes:
            if pane.tab_id == tab_id:
                pane.update_title(title)
                break
    
    def get_active_layout(self) -> str:
        """Get current layout type"""
        return self.layout
    
    def is_split_active(self) -> bool:
        """Check if split view is active"""
        return self.layout != "single"
    
    def get_pane_count(self) -> int:
        """Get number of active panes"""
        return len(self.panes)
