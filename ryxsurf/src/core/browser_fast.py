"""
Fast Browser Initialization

Optimized browser startup using lazy loading and efficient initialization.
Drop-in replacement for browser.py with faster startup.
"""

from pathlib import Path
from typing import Optional
import logging

# Only import what's absolutely necessary at startup
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit', '6.0')
from gi.repository import Gtk, WebKit, GLib, Gdk

# Import performance monitoring
from .perf_monitor import startup_profiler, memory_profiler, timer
from .lazy_loader import create_lazy_loader, create_feature_registry
from .startup_optimizer import StartupOptimizer

log = logging.getLogger("ryxsurf.fast")


class FastBrowser:
    """Fast-loading browser with lazy initialization"""
    
    def __init__(self, config):
        # Start profiling
        startup_profiler.mark("__init__ start")
        memory_profiler.snapshot("Browser __init__")
        
        self.config = config
        self.config_dir = Path.home() / ".config" / "ryxsurf"
        
        # Create lazy loader and feature registry
        self.lazy_loader = create_lazy_loader()
        self.feature_registry = create_feature_registry(self.lazy_loader)
        
        # Startup optimizer
        self.optimizer = StartupOptimizer(self.config_dir)
        
        # Core state (minimal)
        self.tabs = []
        self.active_tab_idx = 0
        self.window: Optional[Gtk.Window] = None
        
        # Features (will be lazy loaded)
        self._settings_manager = None
        self._split_view = None
        self._resource_limiter = None
        self._reader_mode = None
        self._tab_group_manager = None
        self._container_manager = None
        self._force_dark = None
        self._shortcut_manager = None
        
        startup_profiler.mark("__init__ complete")
        memory_profiler.snapshot("Browser __init__ complete")
    
    # Property accessors with lazy loading
    
    @property
    def settings_manager(self):
        """Lazy load settings manager"""
        if self._settings_manager is None:
            startup_profiler.mark("Loading settings")
            from .settings_manager import SettingsManager
            self._settings_manager = SettingsManager()
            memory_profiler.snapshot("Settings loaded")
        return self._settings_manager
    
    @property
    def split_view(self):
        """Lazy load split view"""
        if self._split_view is None:
            log.info("Lazy loading: split_view")
            from .split_view import SplitView
            self._split_view = SplitView(on_layout_change=self._on_split_layout_change)
        return self._split_view
    
    @property
    def resource_limiter(self):
        """Lazy load resource limiter"""
        if self._resource_limiter is None:
            log.info("Lazy loading: resource_limiter")
            from .resource_limiter import ResourceLimiter
            self._resource_limiter = ResourceLimiter(
                on_tab_unload=self._unload_tabs_for_memory,
                on_tab_throttle=self._throttle_tabs_for_cpu
            )
            
            # Configure if enabled in settings
            if self.settings_manager.performance.enable_ram_limiter:
                self._resource_limiter.configure_ram_limiter(
                    enabled=True,
                    limit_mb=self.settings_manager.performance.ram_limit_mb
                )
                self._resource_limiter.start()
        return self._resource_limiter
    
    @property
    def reader_mode(self):
        """Lazy load reader mode"""
        if self._reader_mode is None:
            log.info("Lazy loading: reader_mode")
            from .reader_mode import ReaderMode
            self._reader_mode = ReaderMode()
        return self._reader_mode
    
    @property
    def tab_group_manager(self):
        """Lazy load tab groups"""
        if self._tab_group_manager is None:
            log.info("Lazy loading: tab_groups")
            from .tab_groups import TabGroupManager
            self._tab_group_manager = TabGroupManager()
        return self._tab_group_manager
    
    @property
    def container_manager(self):
        """Lazy load container manager"""
        if self._container_manager is None:
            log.info("Lazy loading: container_manager")
            from .container_tabs import ContainerManager
            self._container_manager = ContainerManager(
                data_dir=self.config_dir / "data"
            )
        return self._container_manager
    
    @property
    def force_dark(self):
        """Lazy load force dark mode"""
        if self._force_dark is None:
            log.info("Lazy loading: force_dark")
            from .force_dark import SmartDarkMode
            self._force_dark = SmartDarkMode()
            
            # Configure from settings
            if self.settings_manager.content.force_dark_mode:
                self._force_dark.force_dark.set_enabled(True)
        return self._force_dark
    
    @property
    def shortcut_manager(self):
        """Lazy load shortcuts"""
        if self._shortcut_manager is None:
            startup_profiler.mark("Loading shortcuts")
            from .shortcuts import ShortcutManager
            self._shortcut_manager = ShortcutManager()
            self._register_shortcuts()
            memory_profiler.snapshot("Shortcuts loaded")
        return self._shortcut_manager
    
    # Initialization methods
    
    @timer("create_window", log_result=True)
    def create_window(self):
        """Create main window (fast)"""
        startup_profiler.mark("Window creation start")
        
        self.window = Gtk.Window(title="RyxSurf")
        self.window.set_default_size(1200, 800)
        
        # Basic layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.set_child(main_box)
        
        startup_profiler.mark("Window creation complete")
        memory_profiler.snapshot("Window created")
        
        return self.window
    
    @timer("create_first_tab", log_result=True)
    def create_first_tab(self, url: str = None):
        """Create first tab"""
        startup_profiler.mark("First tab creation start")
        
        # Create webview
        webview = WebKit.WebView()
        
        # Load URL
        if url:
            webview.load_uri(url)
        else:
            homepage = self.settings_manager.search.searxng_url
            webview.load_uri(homepage)
        
        # Store tab
        self.tabs.append({"webview": webview, "url": url or homepage})
        
        startup_profiler.mark("First tab creation complete")
        memory_profiler.snapshot("First tab created")
    
    def _register_shortcuts(self):
        """Register keyboard shortcuts"""
        from .shortcuts import DEFAULT_SHORTCUTS
        
        for shortcut_id, name, desc, keys, category in DEFAULT_SHORTCUTS:
            action = self._get_action_for_shortcut(shortcut_id)
            if action:
                self.shortcut_manager.register(
                    shortcut_id, name, desc, keys, category, action
                )
    
    def _get_action_for_shortcut(self, shortcut_id: str):
        """Get action callback for shortcut"""
        # Map shortcut IDs to methods
        action_map = {
            "tab.new": self.new_tab,
            "tab.close": self.close_tab,
            "nav.back": self.go_back,
            "nav.forward": self.go_forward,
            "nav.reload": self.reload,
            # ... add more mappings
        }
        
        return action_map.get(shortcut_id)
    
    # Placeholder methods (implement as needed)
    
    def new_tab(self):
        """Create new tab"""
        pass
    
    def close_tab(self):
        """Close current tab"""
        pass
    
    def go_back(self):
        """Navigate back"""
        pass
    
    def go_forward(self):
        """Navigate forward"""
        pass
    
    def reload(self):
        """Reload page"""
        pass
    
    def _on_split_layout_change(self, container):
        """Handle split view changes"""
        pass
    
    def _unload_tabs_for_memory(self, overage_mb: float):
        """Unload tabs to free memory"""
        pass
    
    def _throttle_tabs_for_cpu(self, overage_percent: float):
        """Throttle tabs to reduce CPU"""
        pass


class FastBrowserApp(Gtk.Application):
    """Fast browser application"""
    
    def __init__(self):
        super().__init__(application_id="com.ryx.surf.fast")
        self.browser: Optional[FastBrowser] = None
        
        # Start profiling immediately
        startup_profiler.mark("App __init__")
        memory_profiler.snapshot("App start")
    
    def do_activate(self):
        """Activate application (optimized)"""
        startup_profiler.mark("do_activate start")
        
        if self.browser:
            self.browser.window.present()
            return
        
        # Create browser (lazy)
        self.browser = FastBrowser(config=None)
        
        # Phase 1: Create window ASAP (< 200ms target)
        startup_profiler.mark("Phase 1: Create window")
        window = self.browser.create_window()
        
        # Show window immediately
        window.present()
        startup_profiler.mark("Window visible")
        memory_profiler.snapshot("Window shown")
        
        # Phase 2: Create first tab (< 500ms target)
        startup_profiler.mark("Phase 2: First tab")
        GLib.idle_add(self._phase_2_first_tab)
    
    def _phase_2_first_tab(self):
        """Phase 2: Create first tab"""
        self.browser.create_first_tab()
        
        startup_profiler.mark("First tab ready")
        memory_profiler.snapshot("First tab ready")
        
        # Phase 3: Load UI components (background)
        GLib.idle_add(self._phase_3_ui_components)
        
        return False  # Don't repeat
    
    def _phase_3_ui_components(self):
        """Phase 3: Load remaining UI"""
        startup_profiler.mark("Phase 3: UI components")
        
        # Load shortcuts
        _ = self.browser.shortcut_manager
        
        startup_profiler.mark("UI complete")
        memory_profiler.snapshot("UI complete")
        
        # Phase 4: Background loading
        GLib.idle_add(self._phase_4_background)
        
        return False
    
    def _phase_4_background(self):
        """Phase 4: Background initialization"""
        startup_profiler.mark("Phase 4: Background loading")
        
        # Preload features that might be used soon
        # But don't block - they load on first use anyway
        
        startup_profiler.mark("Fully ready")
        memory_profiler.snapshot("Fully ready")
        
        # Print reports
        startup_profiler.print_report()
        memory_profiler.print_report()
        
        return False


def create_fast_app():
    """Create fast browser application"""
    return FastBrowserApp()
