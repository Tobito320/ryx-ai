#!/usr/bin/env python3
"""
RyxSurf - Optimized Startup
Ultra-fast browser startup with lazy loading and minimal UI.
"""

import sys
import time
from pathlib import Path

# Startup timer
_start_time = time.time()

# Add ryxsurf to path
RYXSURF_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(RYXSURF_ROOT))

# Minimal imports for fastest startup
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit', '6.0')
from gi.repository import Gtk, WebKit, GLib, Gdk, Gio

# Lazy imports (loaded on demand)
_lazy_modules = {}

def lazy_import(module_path: str):
    """Lazy import a module"""
    if module_path not in _lazy_modules:
        import importlib
        _lazy_modules[module_path] = importlib.import_module(module_path)
    return _lazy_modules[module_path]


class MinimalBrowser(Gtk.Application):
    """Minimal browser with ultra-fast startup"""
    
    def __init__(self):
        super().__init__(
            application_id='io.github.ryxsurf.optimized',
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.window = None
        self.webview = None
        self.url_entry = None
        self.features_loaded = False
        
    def do_activate(self):
        """Create minimal UI immediately"""
        if self.window:
            self.window.present()
            return
        
        # Phase 1: Create window skeleton (< 100ms target)
        self.window = Gtk.ApplicationWindow(application=self)
        self.window.set_title("RyxSurf")
        self.window.set_default_size(1400, 900)
        
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.set_child(main_box)
        
        # Top bar (minimal)
        top_bar = self._create_minimal_top_bar()
        main_box.append(top_bar)
        
        # WebView container
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        
        # Create WebView with optimizations
        self.webview = self._create_optimized_webview()
        scroll.set_child(self.webview)
        main_box.append(scroll)
        
        # Show window ASAP
        self.window.present()
        
        elapsed = (time.time() - _start_time) * 1000
        print(f"✓ Window visible in {elapsed:.0f}ms")
        
        # Phase 2: Load homepage
        GLib.idle_add(self._load_homepage)
        
        # Phase 3: Load features in background
        GLib.timeout_add(100, self._load_features_background)
        
    def _create_minimal_top_bar(self):
        """Create minimal top bar (symbols, no clutter)"""
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        bar.set_margin_start(8)
        bar.set_margin_end(8)
        bar.set_margin_top(4)
        bar.set_margin_bottom(4)
        
        # Back button (symbol: ←)
        back_btn = Gtk.Button(label="←")
        back_btn.set_tooltip_text("Back (Alt+Left)")
        back_btn.connect("clicked", lambda b: self.webview.go_back())
        bar.append(back_btn)
        
        # Forward button (symbol: →)
        fwd_btn = Gtk.Button(label="→")
        fwd_btn.set_tooltip_text("Forward (Alt+Right)")
        fwd_btn.connect("clicked", lambda b: self.webview.go_forward())
        bar.append(fwd_btn)
        
        # Reload button (symbol: ⟳)
        reload_btn = Gtk.Button(label="⟳")
        reload_btn.set_tooltip_text("Reload (Ctrl+R)")
        reload_btn.connect("clicked", lambda b: self.webview.reload())
        bar.append(reload_btn)
        
        # URL entry (clean, minimal)
        self.url_entry = Gtk.Entry()
        self.url_entry.set_hexpand(True)
        self.url_entry.set_placeholder_text("Search or enter URL...")
        self.url_entry.connect("activate", self._on_url_activate)
        self.url_entry.set_margin_start(8)
        self.url_entry.set_margin_end(8)
        bar.append(self.url_entry)
        
        # Settings button (symbol: ⚙)
        settings_btn = Gtk.Button(label="⚙")
        settings_btn.set_tooltip_text("Settings (Ctrl+,)")
        settings_btn.connect("clicked", self._on_settings_clicked)
        bar.append(settings_btn)
        
        return bar
    
    def _create_optimized_webview(self):
        """Create WebView with performance optimizations"""
        webview = WebKit.WebView()
        
        # Get settings
        settings = webview.get_settings()
        
        # Performance optimizations
        settings.set_enable_javascript(True)
        settings.set_enable_webgl(True)
        settings.set_hardware_acceleration_policy(WebKit.HardwareAccelerationPolicy.ALWAYS)
        settings.set_enable_smooth_scrolling(True)
        settings.set_enable_back_forward_navigation_gestures(True)
        
        # Privacy
        settings.set_enable_dns_prefetching(True)  # Faster page loads
        
        # Reduce memory
        settings.set_enable_page_cache(True)
        
        # Connect load signals
        webview.connect("load-changed", self._on_load_changed)
        webview.connect("notify::uri", self._on_uri_changed)
        webview.connect("notify::title", self._on_title_changed)
        
        return webview
    
    def _load_homepage(self):
        """Load homepage"""
        homepage = "http://localhost:8888"  # SearXNG
        self.webview.load_uri(homepage)
        return False  # Don't repeat
    
    def _load_features_background(self):
        """Load additional features in background"""
        if self.features_loaded:
            return False
        
        try:
            # Load features lazily
            print("→ Loading features...")
            
            # Load history (lazy)
            # history = lazy_import('src.core.history')
            
            # Load bookmarks (lazy)
            # bookmarks = lazy_import('src.core.bookmarks')
            
            # Load downloads (lazy)
            # downloads = lazy_import('src.core.downloads')
            
            self.features_loaded = True
            
            elapsed = (time.time() - _start_time) * 1000
            print(f"✓ Fully loaded in {elapsed:.0f}ms")
            
        except Exception as e:
            print(f"✗ Feature loading failed: {e}")
        
        return False  # Don't repeat
    
    def _on_url_activate(self, entry):
        """Handle URL entry activation"""
        text = entry.get_text().strip()
        if not text:
            return
        
        # Smart URL handling
        if ' ' in text or (not '.' in text and not text.startswith('localhost')):
            # Search query
            search_url = f"http://localhost:8888/search?q={text.replace(' ', '+')}"
            self.webview.load_uri(search_url)
        elif text.startswith(('http://', 'https://')):
            # Full URL
            self.webview.load_uri(text)
        elif text.startswith('localhost'):
            # Localhost
            self.webview.load_uri(f"http://{text}")
        else:
            # Add https://
            self.webview.load_uri(f"https://{text}")
    
    def _on_load_changed(self, webview, event):
        """Handle load state changes"""
        if event == WebKit.LoadEvent.STARTED:
            self.url_entry.set_placeholder_text("Loading...")
        elif event == WebKit.LoadEvent.FINISHED:
            self.url_entry.set_placeholder_text("Search or enter URL...")
    
    def _on_uri_changed(self, webview, param):
        """Update URL entry when page changes"""
        uri = webview.get_uri()
        if uri:
            self.url_entry.set_text(uri)
    
    def _on_title_changed(self, webview, param):
        """Update window title"""
        title = webview.get_title()
        if title:
            self.window.set_title(f"{title} - RyxSurf")
    
    def _on_settings_clicked(self, button):
        """Open settings (lazy load)"""
        print("Settings clicked (not implemented yet)")


def main():
    """Main entry point"""
    print("🚀 Starting RyxSurf (optimized)...")
    
    app = MinimalBrowser()
    exit_code = app.run(sys.argv)
    
    total_time = (time.time() - _start_time) * 1000
    print(f"\n✓ Total startup: {total_time:.0f}ms")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
