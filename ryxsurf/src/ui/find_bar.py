"""
RyxSurf Find in Page Bar

Provides find-in-page functionality with:
- Match highlighting
- Navigation with Enter/Shift+Enter
- Match count display
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit', '6.0')

from gi.repository import Gtk, WebKit, Gdk


class FindBar(Gtk.Box):
    """
    Find-in-page bar widget.
    
    Activated with Ctrl+F, shows match count and allows
    navigation through matches.
    """
    
    def __init__(self, get_webview_callback):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        
        self.get_webview = get_webview_callback
        self._find_controller = None
        self._match_count = 0
        self._current_match = 0
        
        self._setup_ui()
        self._apply_css()
        self.set_visible(False)
        
    def _setup_ui(self):
        """Setup find bar UI"""
        self.add_css_class("find-bar")
        self.set_spacing(8)
        self.set_margin_start(100)
        self.set_margin_end(100)
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        self.set_halign(Gtk.Align.CENTER)
        
        # Find icon/label
        find_label = Gtk.Label(label="🔍")
        self.append(find_label)
        
        # Search entry
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Find in page...")
        self.entry.set_width_chars(30)
        self.entry.add_css_class("find-entry")
        self.entry.connect("activate", self._on_activate)
        self.entry.connect("changed", self._on_text_changed)
        
        # Key handler for Escape and navigation
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_press)
        self.entry.add_controller(key_controller)
        
        self.append(self.entry)
        
        # Match count label
        self.match_label = Gtk.Label(label="")
        self.match_label.add_css_class("match-count")
        self.append(self.match_label)
        
        # Previous button
        prev_btn = Gtk.Button(label="‹")
        prev_btn.set_tooltip_text("Previous match (Shift+Enter)")
        prev_btn.add_css_class("find-nav-btn")
        prev_btn.connect("clicked", lambda _: self._find_prev())
        self.append(prev_btn)
        
        # Next button
        next_btn = Gtk.Button(label="›")
        next_btn.set_tooltip_text("Next match (Enter)")
        next_btn.add_css_class("find-nav-btn")
        next_btn.connect("clicked", lambda _: self._find_next())
        self.append(next_btn)
        
        # Close button
        close_btn = Gtk.Button(label="✕")
        close_btn.set_tooltip_text("Close (Escape)")
        close_btn.add_css_class("find-close-btn")
        close_btn.connect("clicked", lambda _: self.hide())
        self.append(close_btn)
        
    def show(self):
        """Show the find bar and focus entry"""
        self.set_visible(True)
        self.entry.grab_focus()
        self.entry.select_region(0, -1)
        
        # Setup find controller for current webview
        webview = self.get_webview()
        if webview:
            self._find_controller = webview.get_find_controller()
            self._find_controller.connect("found-text", self._on_found_text)
            self._find_controller.connect("failed-to-find-text", self._on_not_found)
            
            # If there's existing text, search for it
            if self.entry.get_text():
                self._do_search()
        
    def hide(self):
        """Hide the find bar and clear highlights"""
        self.set_visible(False)
        
        # Clear search highlights
        if self._find_controller:
            self._find_controller.search_finish()
            self._find_controller = None
            
        self._match_count = 0
        self._current_match = 0
        self.match_label.set_text("")
        
    def _on_key_press(self, controller, keyval, keycode, state):
        """Handle key presses in find entry"""
        key_name = Gdk.keyval_name(keyval)
        shift_pressed = bool(state & Gdk.ModifierType.SHIFT_MASK)
        
        if key_name == "Escape":
            self.hide()
            # Return focus to webview
            webview = self.get_webview()
            if webview:
                webview.grab_focus()
            return Gdk.EVENT_STOP
            
        if key_name == "Return":
            if shift_pressed:
                self._find_prev()
            else:
                self._find_next()
            return Gdk.EVENT_STOP
            
        return Gdk.EVENT_PROPAGATE
        
    def _on_activate(self, entry):
        """Handle Enter key in entry"""
        self._find_next()
        
    def _on_text_changed(self, entry):
        """Handle text changes - do live search"""
        self._do_search()
        
    def _do_search(self):
        """Perform the search"""
        text = self.entry.get_text()
        
        if not text or not self._find_controller:
            self.match_label.set_text("")
            if self._find_controller:
                self._find_controller.search_finish()
            return
            
        # Configure search options
        options = WebKit.FindOptions.CASE_INSENSITIVE | WebKit.FindOptions.WRAP_AROUND
        
        # Start search
        self._find_controller.search(text, options, 1000)  # max 1000 matches
        
    def _find_next(self):
        """Find next match"""
        if self._find_controller and self.entry.get_text():
            self._find_controller.search_next()
            self._current_match = min(self._current_match + 1, self._match_count)
            self._update_match_label()
            
    def _find_prev(self):
        """Find previous match"""
        if self._find_controller and self.entry.get_text():
            self._find_controller.search_previous()
            self._current_match = max(self._current_match - 1, 1)
            self._update_match_label()
            
    def _on_found_text(self, controller, match_count):
        """Called when text is found"""
        self._match_count = match_count
        self._current_match = 1 if match_count > 0 else 0
        self._update_match_label()
        
    def _on_not_found(self, controller):
        """Called when text is not found"""
        self._match_count = 0
        self._current_match = 0
        self._update_match_label()
        
    def _update_match_label(self):
        """Update the match count label"""
        if self._match_count == 0:
            self.match_label.set_text("No matches")
            self.match_label.add_css_class("no-match")
            self.match_label.remove_css_class("has-match")
        else:
            self.match_label.set_text(f"{self._current_match}/{self._match_count}")
            self.match_label.add_css_class("has-match")
            self.match_label.remove_css_class("no-match")
            
    def _apply_css(self):
        """Apply find bar styling"""
        css = b"""
        .find-bar {
            background: rgba(40, 42, 54, 0.95);
            border-radius: 8px;
            padding: 6px 12px;
            border: 1px solid rgba(68, 71, 90, 0.8);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        
        .find-entry {
            background: rgba(30, 31, 41, 0.8);
            color: #f8f8f2;
            border: 1px solid rgba(68, 71, 90, 0.5);
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 14px;
        }
        
        .find-entry:focus {
            border-color: rgba(189, 147, 249, 0.6);
            box-shadow: 0 0 0 2px rgba(189, 147, 249, 0.15);
        }
        
        .match-count {
            color: #6272a4;
            font-size: 13px;
            min-width: 60px;
        }
        
        .match-count.has-match {
            color: #50fa7b;
        }
        
        .match-count.no-match {
            color: #ff5555;
        }
        
        .find-nav-btn, .find-close-btn {
            background: rgba(68, 71, 90, 0.6);
            color: #f8f8f2;
            border: none;
            border-radius: 6px;
            min-width: 28px;
            min-height: 28px;
            padding: 4px 8px;
        }
        
        .find-nav-btn:hover, .find-close-btn:hover {
            background: rgba(98, 114, 164, 0.8);
        }
        
        .find-close-btn {
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
