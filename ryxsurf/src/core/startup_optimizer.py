"""
Startup Optimizer

Optimizes browser startup by:
1. Deferring heavy imports
2. Lazy loading features
3. Background initialization
4. Efficient resource allocation
"""

import time
import logging
from pathlib import Path
from typing import Optional, List, Callable
import threading

log = logging.getLogger("ryxsurf.startup")


class StartupSequence:
    """Manages browser startup sequence"""
    
    def __init__(self):
        self.start_time = time.time()
        self.phases = {
            "init": 0,
            "ui_skeleton": 0,
            "essential_features": 0,
            "ui_complete": 0,
            "background_load": 0,
            "full_ready": 0,
        }
        self.current_phase = None
    
    def begin_phase(self, phase_name: str):
        """Mark beginning of phase"""
        self.current_phase = phase_name
        self.phases[phase_name] = time.time() - self.start_time
        log.info(f"⏱️  Phase '{phase_name}' at {self.phases[phase_name]:.3f}s")
    
    def get_elapsed(self) -> float:
        """Get total elapsed time"""
        return time.time() - self.start_time
    
    def print_summary(self):
        """Print startup summary"""
        total = self.get_elapsed()
        
        print("\n" + "="*60)
        print("🚀 STARTUP SEQUENCE COMPLETE")
        print("="*60)
        
        for phase, timestamp in self.phases.items():
            if timestamp > 0:
                percentage = (timestamp / total * 100) if total > 0 else 0
                print(f"  {phase:20s} {timestamp:6.3f}s  ({percentage:5.1f}%)")
        
        print("-"*60)
        print(f"  {'TOTAL':20s} {total:6.3f}s")
        print("="*60 + "\n")


class BackgroundInitializer:
    """Initializes features in background"""
    
    def __init__(self):
        self.tasks: List[tuple] = []
        self.running = False
        self.thread: Optional[threading.Thread] = None
    
    def add_task(self, name: str, func: Callable, *args, **kwargs):
        """Add initialization task"""
        self.tasks.append((name, func, args, kwargs))
        log.debug(f"Added background task: {name}")
    
    def start(self):
        """Start background initialization"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_tasks, daemon=True)
        self.thread.start()
        log.info(f"Started background initialization ({len(self.tasks)} tasks)")
    
    def _run_tasks(self):
        """Run all tasks"""
        for name, func, args, kwargs in self.tasks:
            try:
                log.debug(f"Background: {name}")
                start = time.time()
                func(*args, **kwargs)
                elapsed = time.time() - start
                log.debug(f"Background: {name} completed in {elapsed:.3f}s")
            except Exception as e:
                log.error(f"Background task '{name}' failed: {e}")
        
        self.running = False
        log.info("Background initialization complete")
    
    def wait(self, timeout: Optional[float] = None):
        """Wait for background tasks to complete"""
        if self.thread:
            self.thread.join(timeout=timeout)


class CacheManager:
    """Manages startup cache"""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cache_file(self, key: str) -> Path:
        """Get cache file path"""
        return self.cache_dir / f"{key}.cache"
    
    def has_cache(self, key: str, max_age_hours: int = 24) -> bool:
        """Check if cache exists and is fresh"""
        cache_file = self.get_cache_file(key)
        
        if not cache_file.exists():
            return False
        
        # Check age
        age = time.time() - cache_file.stat().st_mtime
        max_age = max_age_hours * 3600
        
        return age < max_age
    
    def load_cache(self, key: str) -> Optional[bytes]:
        """Load from cache"""
        cache_file = self.get_cache_file(key)
        
        try:
            return cache_file.read_bytes()
        except Exception as e:
            log.warning(f"Failed to load cache '{key}': {e}")
            return None
    
    def save_cache(self, key: str, data: bytes):
        """Save to cache"""
        cache_file = self.get_cache_file(key)
        
        try:
            cache_file.write_bytes(data)
            log.debug(f"Saved cache: {key}")
        except Exception as e:
            log.warning(f"Failed to save cache '{key}': {e}")
    
    def clear_cache(self, key: Optional[str] = None):
        """Clear cache"""
        if key:
            cache_file = self.get_cache_file(key)
            if cache_file.exists():
                cache_file.unlink()
                log.debug(f"Cleared cache: {key}")
        else:
            # Clear all
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink()
            log.info("Cleared all caches")


class ResourcePool:
    """Manages shared resources efficiently"""
    
    def __init__(self):
        self.resources = {}
        self.locks = {}
    
    def get_or_create(self, key: str, factory: Callable) -> any:
        """Get resource or create if doesn't exist"""
        import threading
        
        if key not in self.locks:
            self.locks[key] = threading.Lock()
        
        with self.locks[key]:
            if key not in self.resources:
                log.debug(f"Creating resource: {key}")
                self.resources[key] = factory()
            return self.resources[key]
    
    def release(self, key: str):
        """Release a resource"""
        if key in self.resources:
            del self.resources[key]
            log.debug(f"Released resource: {key}")


class MinimalBrowserShell:
    """Minimal browser shell for fast startup"""
    
    def __init__(self):
        self.window = None
        self.url_bar = None
        self.webview_container = None
        self.status_bar = None
    
    def create_shell(self) -> any:
        """Create minimal UI shell"""
        import gi
        gi.require_version('Gtk', '4.0')
        from gi.repository import Gtk
        
        # Window
        self.window = Gtk.Window(title="RyxSurf")
        self.window.set_default_size(1200, 800)
        
        # Main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # URL bar (minimal)
        self.url_bar = Gtk.Entry()
        self.url_bar.set_placeholder_text("Loading...")
        main_box.append(self.url_bar)
        
        # Webview container
        self.webview_container = Gtk.Box()
        self.webview_container.set_vexpand(True)
        main_box.append(self.webview_container)
        
        # Status bar
        self.status_bar = Gtk.Label(label="Initializing...")
        self.status_bar.set_halign(Gtk.Align.START)
        main_box.append(self.status_bar)
        
        self.window.set_child(main_box)
        
        return self.window
    
    def set_status(self, text: str):
        """Update status"""
        if self.status_bar:
            self.status_bar.set_text(text)
    
    def add_webview(self, webview):
        """Add webview to container"""
        if self.webview_container:
            self.webview_container.append(webview)


class StartupOptimizer:
    """Main startup optimizer"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.sequence = StartupSequence()
        self.background = BackgroundInitializer()
        self.cache = CacheManager(config_dir / "cache")
        self.resources = ResourcePool()
        self.shell = MinimalBrowserShell()
    
    def phase_1_core_init(self):
        """Phase 1: Core initialization (critical only)"""
        self.sequence.begin_phase("init")
        
        # Initialize logging (already done)
        # Load minimal config
        # Create directories
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
        (self.config_dir / "data").mkdir(exist_ok=True)
        (self.config_dir / "cache").mkdir(exist_ok=True)
    
    def phase_2_ui_skeleton(self) -> any:
        """Phase 2: Create minimal UI skeleton"""
        self.sequence.begin_phase("ui_skeleton")
        
        # Create minimal window
        window = self.shell.create_shell()
        
        # Show window immediately
        window.present()
        
        return window
    
    def phase_3_essential_features(self):
        """Phase 3: Load only essential features"""
        self.sequence.begin_phase("essential_features")
        
        # Load settings (critical)
        self.shell.set_status("Loading settings...")
        
        # Load keyboard shortcuts (high priority)
        self.shell.set_status("Loading shortcuts...")
        
        # Create first webview
        self.shell.set_status("Creating browser engine...")
    
    def phase_4_ui_complete(self):
        """Phase 4: Complete UI (tab bar, sidebar, etc.)"""
        self.sequence.begin_phase("ui_complete")
        
        self.shell.set_status("Building interface...")
        
        # Add tab bar
        # Add sidebar
        # Add toolbar
        # Apply theme/CSS
    
    def phase_5_background_load(self):
        """Phase 5: Load remaining features in background"""
        self.sequence.begin_phase("background_load")
        
        self.shell.set_status("Ready (loading features...)")
        
        # Schedule background tasks
        self.background.add_task("resource_limiter", self._load_resource_limiter)
        self.background.add_task("tab_groups", self._load_tab_groups)
        self.background.add_task("container_tabs", self._load_container_tabs)
        self.background.add_task("reader_mode", self._load_reader_mode)
        self.background.add_task("force_dark", self._load_force_dark)
        
        # Start background loading
        self.background.start()
    
    def phase_6_full_ready(self):
        """Phase 6: Fully ready"""
        self.sequence.begin_phase("full_ready")
        
        self.shell.set_status("Ready")
        
        # Print metrics
        self.sequence.print_summary()
    
    # Feature loaders (called in background)
    
    def _load_resource_limiter(self):
        """Load resource limiter"""
        from .resource_limiter import ResourceLimiter
        # Initialize...
    
    def _load_tab_groups(self):
        """Load tab groups"""
        from .tab_groups import TabGroupManager
        # Initialize...
    
    def _load_container_tabs(self):
        """Load container tabs"""
        from .container_tabs import ContainerManager
        # Initialize...
    
    def _load_reader_mode(self):
        """Load reader mode"""
        from .reader_mode import ReaderMode
        # Initialize...
    
    def _load_force_dark(self):
        """Load force dark mode"""
        from .force_dark import SmartDarkMode
        # Initialize...
    
    def optimize_startup(self, app) -> any:
        """Run optimized startup sequence"""
        try:
            # Phase 1: Core init (< 50ms target)
            self.phase_1_core_init()
            
            # Phase 2: Show window ASAP (< 200ms target)
            window = self.phase_2_ui_skeleton()
            
            # Phase 3: Essential features only (< 500ms target)
            self.phase_3_essential_features()
            
            # Phase 4: Complete UI (< 800ms target)
            self.phase_4_ui_complete()
            
            # Phase 5: Background loading (async)
            self.phase_5_background_load()
            
            # Phase 6: Mark ready
            self.phase_6_full_ready()
            
            return window
            
        except Exception as e:
            log.error(f"Startup failed: {e}")
            raise


def create_fast_startup_config():
    """Create configuration for fast startup"""
    return {
        # Lazy load these features
        "lazy_features": [
            "split_view",
            "resource_limiter",
            "tab_groups",
            "container_tabs",
            "reader_mode",
            "force_dark",
        ],
        
        # Load these immediately
        "immediate_features": [
            "settings",
            "shortcuts",
        ],
        
        # Preload in background
        "background_features": [
            "history",
            "bookmarks",
            "downloads",
        ],
        
        # Startup targets (milliseconds)
        "targets": {
            "window_visible": 200,
            "first_paint": 300,
            "interactive": 500,
            "full_ready": 1000,
        },
        
        # Cache settings
        "cache": {
            "enable": True,
            "max_age_hours": 24,
            "cache_items": [
                "theme_css",
                "icon_cache",
                "font_cache",
            ],
        },
    }
