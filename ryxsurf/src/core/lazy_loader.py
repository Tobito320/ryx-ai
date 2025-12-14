"""
Lazy Loader - Efficient Module Loading

Defers loading of heavy modules until actually needed.
Improves browser startup time significantly.
"""

import importlib
import logging
from typing import Any, Optional, Dict, Callable
from functools import wraps

log = logging.getLogger("ryxsurf.lazy_loader")


class LazyModule:
    """Lazy-loaded module wrapper"""
    
    def __init__(self, module_name: str):
        self.module_name = module_name
        self._module: Optional[Any] = None
        self._loading = False
    
    def _load(self):
        """Load the module"""
        if self._module is not None or self._loading:
            return
        
        self._loading = True
        try:
            log.info(f"Lazy loading: {self.module_name}")
            self._module = importlib.import_module(self.module_name)
        except Exception as e:
            log.error(f"Failed to lazy load {self.module_name}: {e}")
            self._module = None
        finally:
            self._loading = False
    
    def __getattr__(self, name: str):
        """Get attribute from loaded module"""
        if self._module is None:
            self._load()
        
        if self._module is None:
            raise ImportError(f"Module {self.module_name} failed to load")
        
        return getattr(self._module, name)
    
    def is_loaded(self) -> bool:
        """Check if module is loaded"""
        return self._module is not None


class LazyLoader:
    """Manager for lazy-loaded modules"""
    
    def __init__(self):
        self.modules: Dict[str, LazyModule] = {}
        self.loaded_count = 0
        self.start_time = None
    
    def register(self, alias: str, module_name: str) -> LazyModule:
        """Register a module for lazy loading"""
        if alias not in self.modules:
            self.modules[alias] = LazyModule(module_name)
            log.debug(f"Registered lazy module: {alias} -> {module_name}")
        return self.modules[alias]
    
    def get(self, alias: str) -> Optional[LazyModule]:
        """Get a lazy module by alias"""
        return self.modules.get(alias)
    
    def preload(self, *aliases: str):
        """Preload specific modules"""
        for alias in aliases:
            if alias in self.modules:
                module = self.modules[alias]
                if not module.is_loaded():
                    module._load()
                    self.loaded_count += 1
    
    def preload_async(self, *aliases: str):
        """Preload modules in background"""
        import threading
        
        def _preload():
            self.preload(*aliases)
        
        thread = threading.Thread(target=_preload, daemon=True)
        thread.start()
    
    def get_stats(self) -> dict:
        """Get loading statistics"""
        total = len(self.modules)
        loaded = sum(1 for m in self.modules.values() if m.is_loaded())
        
        return {
            "total_modules": total,
            "loaded_modules": loaded,
            "pending_modules": total - loaded,
            "load_percentage": (loaded / total * 100) if total > 0 else 0,
        }


class FeatureRegistry:
    """Registry for lazy-loaded features"""
    
    def __init__(self, lazy_loader: LazyLoader):
        self.lazy_loader = lazy_loader
        self.features: Dict[str, dict] = {}
    
    def register_feature(self, name: str, module_alias: str, 
                        class_name: str, init_fn: Optional[Callable] = None,
                        priority: int = 5, dependencies: list = None):
        """
        Register a feature for lazy loading
        
        Args:
            name: Feature name
            module_alias: Alias in lazy_loader
            class_name: Class to instantiate
            init_fn: Optional initialization function
            priority: Load priority (1=critical, 10=low)
            dependencies: List of feature names this depends on
        """
        self.features[name] = {
            "module_alias": module_alias,
            "class_name": class_name,
            "init_fn": init_fn,
            "priority": priority,
            "dependencies": dependencies or [],
            "instance": None,
            "loaded": False,
        }
        log.debug(f"Registered feature: {name} (priority: {priority})")
    
    def load_feature(self, name: str, *args, **kwargs) -> Any:
        """Load and initialize a feature"""
        if name not in self.features:
            log.warning(f"Feature not found: {name}")
            return None
        
        feature = self.features[name]
        
        # Already loaded?
        if feature["loaded"] and feature["instance"]:
            return feature["instance"]
        
        # Load dependencies first
        for dep in feature["dependencies"]:
            if not self.is_loaded(dep):
                log.debug(f"Loading dependency: {dep} for {name}")
                self.load_feature(dep)
        
        try:
            # Get module
            module = self.lazy_loader.get(feature["module_alias"])
            if module is None:
                log.error(f"Module not found: {feature['module_alias']}")
                return None
            
            # Get class
            cls = getattr(module, feature["class_name"])
            
            # Initialize
            if feature["init_fn"]:
                instance = feature["init_fn"](cls, *args, **kwargs)
            else:
                instance = cls(*args, **kwargs)
            
            feature["instance"] = instance
            feature["loaded"] = True
            
            log.info(f"Loaded feature: {name}")
            return instance
            
        except Exception as e:
            log.error(f"Failed to load feature {name}: {e}")
            return None
    
    def get_feature(self, name: str) -> Optional[Any]:
        """Get a feature instance (load if needed)"""
        if name not in self.features:
            return None
        
        feature = self.features[name]
        if not feature["loaded"]:
            return self.load_feature(name)
        
        return feature["instance"]
    
    def is_loaded(self, name: str) -> bool:
        """Check if feature is loaded"""
        if name not in self.features:
            return False
        return self.features[name]["loaded"]
    
    def preload_by_priority(self, max_priority: int = 3):
        """Preload features up to a priority level"""
        to_load = [
            (name, f) for name, f in self.features.items()
            if f["priority"] <= max_priority and not f["loaded"]
        ]
        
        # Sort by priority
        to_load.sort(key=lambda x: x[1]["priority"])
        
        for name, _ in to_load:
            self.load_feature(name)
    
    def preload_async(self, max_priority: int = 7):
        """Preload features in background"""
        import threading
        
        def _preload():
            self.preload_by_priority(max_priority)
        
        thread = threading.Thread(target=_preload, daemon=True)
        thread.start()


def lazy_method(feature_name: str):
    """Decorator to lazy-load a feature before calling method"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get feature registry from self
            if not hasattr(self, 'feature_registry'):
                raise AttributeError("Object must have feature_registry attribute")
            
            # Load feature if not loaded
            if not self.feature_registry.is_loaded(feature_name):
                log.debug(f"Lazy loading feature: {feature_name} for method {func.__name__}")
                self.feature_registry.load_feature(feature_name)
            
            # Call original method
            return func(self, *args, **kwargs)
        
        return wrapper
    return decorator


# Module aliases for lazy loading
LAZY_MODULES = {
    # Core features
    "split_view": "ryxsurf.src.core.split_view",
    "resource_limiter": "ryxsurf.src.core.resource_limiter",
    "reader_mode": "ryxsurf.src.core.reader_mode",
    "tab_groups": "ryxsurf.src.core.tab_groups",
    "container_tabs": "ryxsurf.src.core.container_tabs",
    "force_dark": "ryxsurf.src.core.force_dark",
    "shortcuts": "ryxsurf.src.core.shortcuts",
    
    # Heavy imports
    "psutil": "psutil",  # Resource monitoring
    "PIL": "PIL",  # Image processing (if used)
}


def create_lazy_loader() -> LazyLoader:
    """Create and configure lazy loader"""
    loader = LazyLoader()
    
    for alias, module_name in LAZY_MODULES.items():
        loader.register(alias, module_name)
    
    return loader


def create_feature_registry(lazy_loader: LazyLoader) -> FeatureRegistry:
    """Create and configure feature registry"""
    registry = FeatureRegistry(lazy_loader)
    
    # Register all features with priorities
    # Priority: 1=critical (load at startup), 5=medium (load on first use), 10=low (load on demand)
    
    # Critical features (always load)
    registry.register_feature(
        name="settings",
        module_alias="settings_manager",
        class_name="SettingsManager",
        priority=1
    )
    
    # Medium priority (load on first use)
    registry.register_feature(
        name="split_view",
        module_alias="split_view",
        class_name="SplitView",
        priority=5
    )
    
    registry.register_feature(
        name="reader_mode",
        module_alias="reader_mode",
        class_name="ReaderMode",
        priority=5
    )
    
    registry.register_feature(
        name="shortcuts",
        module_alias="shortcuts",
        class_name="ShortcutManager",
        priority=3
    )
    
    registry.register_feature(
        name="tab_groups",
        module_alias="tab_groups",
        class_name="TabGroupManager",
        priority=6
    )
    
    registry.register_feature(
        name="force_dark",
        module_alias="force_dark",
        class_name="SmartDarkMode",
        priority=6
    )
    
    # Low priority (only load when needed)
    registry.register_feature(
        name="resource_limiter",
        module_alias="resource_limiter",
        class_name="ResourceLimiter",
        priority=7,
        dependencies=["psutil"]  # Requires psutil module
    )
    
    registry.register_feature(
        name="container_tabs",
        module_alias="container_tabs",
        class_name="ContainerManager",
        priority=8
    )
    
    return registry


class StartupOptimizer:
    """Optimizes browser startup"""
    
    def __init__(self):
        self.metrics = {
            "start_time": 0,
            "modules_loaded": 0,
            "features_loaded": 0,
            "ui_ready_time": 0,
            "full_ready_time": 0,
        }
    
    def mark_start(self):
        """Mark startup beginning"""
        import time
        self.metrics["start_time"] = time.time()
    
    def mark_ui_ready(self):
        """Mark UI ready"""
        import time
        self.metrics["ui_ready_time"] = time.time() - self.metrics["start_time"]
        log.info(f"UI ready in {self.metrics['ui_ready_time']:.2f}s")
    
    def mark_full_ready(self):
        """Mark fully ready"""
        import time
        self.metrics["full_ready_time"] = time.time() - self.metrics["start_time"]
        log.info(f"Fully ready in {self.metrics['full_ready_time']:.2f}s")
    
    def print_metrics(self):
        """Print startup metrics"""
        print("\n" + "="*50)
        print("🚀 STARTUP METRICS")
        print("="*50)
        print(f"UI Ready:    {self.metrics['ui_ready_time']:.3f}s")
        print(f"Full Ready:  {self.metrics['full_ready_time']:.3f}s")
        print(f"Modules:     {self.metrics['modules_loaded']}")
        print(f"Features:    {self.metrics['features_loaded']}")
        print("="*50 + "\n")
