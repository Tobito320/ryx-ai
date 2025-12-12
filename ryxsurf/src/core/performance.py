"""
RyxSurf Performance Optimization Module

Implements:
- Lazy loading for faster startup
- Resource limiting (RAM/CPU/GPU)
- Tab suspension and hibernation
- Preloading and prefetching
- Cache management
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit', '6.0')
from gi.repository import Gtk, WebKit, GLib
from pathlib import Path
from typing import Optional, Dict, List
import psutil
import time
import json
import threading


class PerformanceMonitor:
    """Monitor system resources and browser performance"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.metrics = {
            "cpu_percent": 0.0,
            "ram_mb": 0.0,
            "gpu_percent": 0.0,
            "network_mbps": 0.0,
            "tabs_loaded": 0,
            "tabs_total": 0,
        }
        self.limits = {
            "ram_mb": 4096,
            "cpu_percent": 50,
            "gpu_percent": 90,
            "network_mbps": 0,  # 0 = unlimited
        }
        self.monitoring = False
        
    def start_monitoring(self, interval_ms: int = 1000):
        """Start resource monitoring"""
        self.monitoring = True
        GLib.timeout_add(interval_ms, self._update_metrics)
        
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring = False
        
    def _update_metrics(self) -> bool:
        """Update performance metrics"""
        if not self.monitoring:
            return False
            
        try:
            # CPU usage
            self.metrics["cpu_percent"] = self.process.cpu_percent()
            
            # RAM usage
            mem = self.process.memory_info()
            self.metrics["ram_mb"] = mem.rss / 1024 / 1024
            
            # GPU usage (if available)
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                if gpus:
                    self.metrics["gpu_percent"] = gpus[0].load * 100
            except:
                pass
                
            # Network usage
            net = psutil.net_io_counters()
            self.metrics["network_mbps"] = (net.bytes_sent + net.bytes_recv) / 1024 / 1024
            
        except Exception as e:
            print(f"Error updating metrics: {e}")
            
        return True
        
    def is_over_limit(self, resource: str) -> bool:
        """Check if a resource is over its limit"""
        if resource not in self.limits or self.limits[resource] == 0:
            return False
        return self.metrics.get(resource, 0) > self.limits[resource]
        
    def get_metrics(self) -> Dict:
        """Get current metrics"""
        return self.metrics.copy()
        
    def set_limit(self, resource: str, limit: float):
        """Set resource limit"""
        self.limits[resource] = limit


class LazyLoader:
    """Lazy load browser components for faster startup"""
    
    def __init__(self):
        self.loaded_components = set()
        self.pending_components = {}
        
    def register(self, component_name: str, load_func: callable, priority: int = 0):
        """Register a component for lazy loading
        
        Args:
            component_name: Unique component identifier
            load_func: Function to call when loading
            priority: Higher priority loads first (0-10)
        """
        self.pending_components[component_name] = {
            "load_func": load_func,
            "priority": priority,
            "loaded": False,
        }
        
    def load(self, component_name: str) -> bool:
        """Load a specific component"""
        if component_name in self.loaded_components:
            return True
            
        if component_name not in self.pending_components:
            return False
            
        component = self.pending_components[component_name]
        try:
            component["load_func"]()
            component["loaded"] = True
            self.loaded_components.add(component_name)
            return True
        except Exception as e:
            print(f"Error loading component {component_name}: {e}")
            return False
            
    def load_all(self, async_load: bool = True):
        """Load all pending components"""
        # Sort by priority
        sorted_components = sorted(
            self.pending_components.items(),
            key=lambda x: x[1]["priority"],
            reverse=True
        )
        
        for name, component in sorted_components:
            if not component["loaded"]:
                if async_load:
                    # Load in background
                    threading.Thread(target=self.load, args=(name,)).start()
                else:
                    self.load(name)
                    
    def is_loaded(self, component_name: str) -> bool:
        """Check if component is loaded"""
        return component_name in self.loaded_components


class TabSuspender:
    """Suspend and hibernate tabs to save resources"""
    
    def __init__(self, performance_monitor: PerformanceMonitor):
        self.monitor = performance_monitor
        self.suspended_tabs = {}
        self.tab_last_active = {}
        self.suspend_timeout = 300  # 5 minutes
        self.max_loaded_tabs = 10
        
    def start_auto_suspend(self, interval_ms: int = 30000):
        """Start automatic tab suspension"""
        GLib.timeout_add(interval_ms, self._check_tabs)
        
    def _check_tabs(self) -> bool:
        """Check tabs and suspend if needed"""
        current_time = time.time()
        
        # Sort tabs by last active time
        tabs_by_activity = sorted(
            self.tab_last_active.items(),
            key=lambda x: x[1]
        )
        
        # Check if we need to suspend tabs
        loaded_count = len(self.tab_last_active) - len(self.suspended_tabs)
        
        # Suspend old tabs if over limit
        if loaded_count > self.max_loaded_tabs:
            for tab_id, last_active in tabs_by_activity:
                if tab_id not in self.suspended_tabs:
                    if current_time - last_active > self.suspend_timeout:
                        self.suspend_tab(tab_id)
                        loaded_count -= 1
                        if loaded_count <= self.max_loaded_tabs:
                            break
                            
        # Also suspend if RAM is over limit
        if self.monitor.is_over_limit("ram_mb"):
            for tab_id, last_active in tabs_by_activity:
                if tab_id not in self.suspended_tabs:
                    self.suspend_tab(tab_id)
                    if not self.monitor.is_over_limit("ram_mb"):
                        break
                        
        return True
        
    def suspend_tab(self, tab_id: int) -> bool:
        """Suspend a tab (save state and unload)"""
        if tab_id in self.suspended_tabs:
            return False
            
        # Tab will be saved by caller
        self.suspended_tabs[tab_id] = {
            "suspended_at": time.time(),
        }
        print(f"Tab {tab_id} suspended")
        return True
        
    def resume_tab(self, tab_id: int) -> bool:
        """Resume a suspended tab"""
        if tab_id not in self.suspended_tabs:
            return False
            
        del self.suspended_tabs[tab_id]
        self.tab_last_active[tab_id] = time.time()
        print(f"Tab {tab_id} resumed")
        return True
        
    def mark_active(self, tab_id: int):
        """Mark tab as recently active"""
        self.tab_last_active[tab_id] = time.time()
        
    def is_suspended(self, tab_id: int) -> bool:
        """Check if tab is suspended"""
        return tab_id in self.suspended_tabs


class PreloadManager:
    """Preload and prefetch resources"""
    
    def __init__(self):
        self.preload_queue = []
        self.prefetch_dns = set()
        self.prefetch_links = set()
        
    def preload_page(self, url: str):
        """Preload a page in background"""
        if url not in self.preload_queue:
            self.preload_queue.append(url)
            GLib.idle_add(self._preload_next)
            
    def _preload_next(self):
        """Preload next page in queue"""
        if not self.preload_queue:
            return False
            
        url = self.preload_queue.pop(0)
        # Create hidden webview to preload
        webview = WebKit.WebView()
        webview.load_uri(url)
        # Will be garbage collected when done
        return False
        
    def prefetch_dns_for_url(self, url: str):
        """Prefetch DNS for a URL"""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        if domain and domain not in self.prefetch_dns:
            self.prefetch_dns.add(domain)
            # DNS prefetching handled by WebKit
            
    def suggest_prefetch(self, links: List[str]):
        """Suggest links to prefetch based on user behavior"""
        # Simple heuristic: prefetch first few links
        for link in links[:3]:
            if link not in self.prefetch_links:
                self.prefetch_links.add(link)
                self.prefetch_dns_for_url(link)


class CacheManager:
    """Manage browser cache efficiently"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or (Path.home() / ".cache" / "ryxsurf")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.memory_cache_size_mb = 512
        self.disk_cache_size_mb = 1024
        
    def get_cache_size(self) -> float:
        """Get current cache size in MB"""
        total = 0
        for path in self.cache_dir.rglob("*"):
            if path.is_file():
                total += path.stat().st_size
        return total / 1024 / 1024
        
    def clear_cache(self, older_than_days: int = 0):
        """Clear cache (optionally only old entries)"""
        import shutil
        from datetime import datetime, timedelta
        
        if older_than_days == 0:
            # Clear all
            shutil.rmtree(self.cache_dir, ignore_errors=True)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            print("Cache cleared")
        else:
            # Clear only old files
            cutoff = datetime.now() - timedelta(days=older_than_days)
            removed = 0
            for path in self.cache_dir.rglob("*"):
                if path.is_file():
                    mtime = datetime.fromtimestamp(path.stat().st_mtime)
                    if mtime < cutoff:
                        path.unlink()
                        removed += 1
            print(f"Removed {removed} old cache entries")
            
    def optimize_cache(self):
        """Optimize cache by removing least used items"""
        # Get all cache files with access time
        files = []
        for path in self.cache_dir.rglob("*"):
            if path.is_file():
                files.append((path, path.stat().st_atime))
                
        # Sort by access time (least recently used first)
        files.sort(key=lambda x: x[1])
        
        # Remove until under size limit
        current_size = self.get_cache_size()
        for path, _ in files:
            if current_size <= self.disk_cache_size_mb:
                break
            size = path.stat().st_size / 1024 / 1024
            path.unlink()
            current_size -= size
            
        print(f"Cache optimized, size: {current_size:.1f}MB")


class StartupOptimizer:
    """Optimize browser startup time"""
    
    def __init__(self):
        self.startup_time = None
        self.init_phases = {}
        
    def start_timing(self):
        """Start timing startup"""
        self.startup_time = time.time()
        
    def mark_phase(self, phase_name: str):
        """Mark a startup phase completion"""
        if self.startup_time is None:
            return
        elapsed = time.time() - self.startup_time
        self.init_phases[phase_name] = elapsed
        print(f"Startup phase '{phase_name}': {elapsed:.3f}s")
        
    def finish_timing(self):
        """Finish startup timing"""
        if self.startup_time is None:
            return
        total = time.time() - self.startup_time
        print(f"Total startup time: {total:.3f}s")
        self.startup_time = None
        return total
        
    def get_startup_report(self) -> Dict:
        """Get startup timing report"""
        return {
            "phases": self.init_phases.copy(),
            "total": sum(self.init_phases.values()),
        }
        
    def save_report(self, path: Optional[Path] = None):
        """Save startup report to file"""
        report = self.get_startup_report()
        path = path or (Path.home() / ".config" / "ryxsurf" / "startup_report.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(report, f, indent=2)


# Global instances
performance_monitor = PerformanceMonitor()
lazy_loader = LazyLoader()
preload_manager = PreloadManager()
cache_manager = CacheManager()
startup_optimizer = StartupOptimizer()
