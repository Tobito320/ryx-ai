"""
Resource Limiter - Opera GX Feature

Active monitoring and limiting of RAM and CPU usage.
Throttles tabs when limits are exceeded.
"""

import psutil
import threading
import time
from typing import Callable, Optional
import logging

log = logging.getLogger("ryxsurf.resource_limiter")


class ResourceMonitor:
    """Monitors system resource usage"""
    
    def __init__(self):
        self.process = psutil.Process()
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._callbacks = []
    
    def start(self, interval: float = 1.0):
        """Start monitoring resources"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
        log.info("Resource monitoring started")
    
    def stop(self):
        """Stop monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
        log.info("Resource monitoring stopped")
    
    def _monitor_loop(self, interval: float):
        """Main monitoring loop"""
        while self._monitoring:
            try:
                stats = self.get_stats()
                for callback in self._callbacks:
                    callback(stats)
            except Exception as e:
                log.error(f"Monitor error: {e}")
            
            time.sleep(interval)
    
    def get_stats(self) -> dict:
        """Get current resource usage stats"""
        try:
            # Memory info
            mem_info = self.process.memory_info()
            ram_mb = mem_info.rss / 1024 / 1024
            
            # CPU usage
            cpu_percent = self.process.cpu_percent(interval=0.1)
            
            # Child processes (tabs)
            children = self.process.children(recursive=True)
            child_ram = sum(c.memory_info().rss for c in children) / 1024 / 1024
            child_cpu = sum(c.cpu_percent(interval=0.1) for c in children)
            
            return {
                "ram_mb": ram_mb,
                "child_ram_mb": child_ram,
                "total_ram_mb": ram_mb + child_ram,
                "cpu_percent": cpu_percent,
                "child_cpu_percent": child_cpu,
                "total_cpu_percent": cpu_percent + child_cpu,
                "process_count": len(children) + 1,
            }
        except Exception as e:
            log.error(f"Failed to get stats: {e}")
            return {}
    
    def add_callback(self, callback: Callable):
        """Add callback for resource updates"""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """Remove callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)


class RAMLimiter:
    """Limits RAM usage by unloading tabs"""
    
    def __init__(self, monitor: ResourceMonitor, on_tab_unload: Callable):
        self.monitor = monitor
        self.on_tab_unload = on_tab_unload
        self.enabled = False
        self.limit_mb = 4096
        self.monitor.add_callback(self._check_limit)
    
    def set_enabled(self, enabled: bool):
        """Enable/disable RAM limiting"""
        self.enabled = enabled
        log.info(f"RAM limiter {'enabled' if enabled else 'disabled'}")
    
    def set_limit(self, limit_mb: int):
        """Set RAM limit in MB"""
        self.limit_mb = limit_mb
        log.info(f"RAM limit set to {limit_mb} MB")
    
    def _check_limit(self, stats: dict):
        """Check if RAM limit exceeded"""
        if not self.enabled:
            return
        
        total_ram = stats.get("total_ram_mb", 0)
        if total_ram > self.limit_mb:
            overage = total_ram - self.limit_mb
            log.warning(f"RAM limit exceeded: {total_ram:.0f} MB / {self.limit_mb} MB (over by {overage:.0f} MB)")
            self.on_tab_unload(overage)


class CPULimiter:
    """Limits CPU usage by throttling tabs"""
    
    def __init__(self, monitor: ResourceMonitor, on_tab_throttle: Callable):
        self.monitor = monitor
        self.on_tab_throttle = on_tab_throttle
        self.enabled = False
        self.limit_percent = 50
        self.monitor.add_callback(self._check_limit)
    
    def set_enabled(self, enabled: bool):
        """Enable/disable CPU limiting"""
        self.enabled = enabled
        log.info(f"CPU limiter {'enabled' if enabled else 'disabled'}")
    
    def set_limit(self, limit_percent: int):
        """Set CPU limit as percentage"""
        self.limit_percent = limit_percent
        log.info(f"CPU limit set to {limit_percent}%")
    
    def _check_limit(self, stats: dict):
        """Check if CPU limit exceeded"""
        if not self.enabled:
            return
        
        total_cpu = stats.get("total_cpu_percent", 0)
        if total_cpu > self.limit_percent:
            overage = total_cpu - self.limit_percent
            log.warning(f"CPU limit exceeded: {total_cpu:.1f}% / {self.limit_percent}% (over by {overage:.1f}%)")
            self.on_tab_throttle(overage)


class ResourceLimiter:
    """Main resource limiter manager"""
    
    def __init__(self, on_tab_unload: Callable, on_tab_throttle: Callable):
        self.monitor = ResourceMonitor()
        self.ram_limiter = RAMLimiter(self.monitor, on_tab_unload)
        self.cpu_limiter = CPULimiter(self.monitor, on_tab_throttle)
        
        # Stats callback for UI
        self._stats_callbacks = []
    
    def start(self):
        """Start resource monitoring and limiting"""
        self.monitor.add_callback(self._broadcast_stats)
        self.monitor.start()
    
    def stop(self):
        """Stop resource monitoring"""
        self.monitor.stop()
    
    def configure_ram_limiter(self, enabled: bool, limit_mb: int):
        """Configure RAM limiter"""
        self.ram_limiter.set_enabled(enabled)
        self.ram_limiter.set_limit(limit_mb)
    
    def configure_cpu_limiter(self, enabled: bool, limit_percent: int):
        """Configure CPU limiter"""
        self.cpu_limiter.set_enabled(enabled)
        self.cpu_limiter.set_limit(limit_percent)
    
    def get_current_stats(self) -> dict:
        """Get current resource usage"""
        return self.monitor.get_stats()
    
    def add_stats_callback(self, callback: Callable):
        """Add callback for stats updates (for UI)"""
        self._stats_callbacks.append(callback)
    
    def _broadcast_stats(self, stats: dict):
        """Broadcast stats to all registered callbacks"""
        for callback in self._stats_callbacks:
            try:
                callback(stats)
            except Exception as e:
                log.error(f"Stats callback error: {e}")


class NetworkLimiter:
    """Network bandwidth limiter (Opera GX feature)"""
    
    def __init__(self):
        self.enabled = False
        self.limit_kbps = 0
        self._last_bytes = 0
        self._last_time = time.time()
    
    def set_enabled(self, enabled: bool):
        """Enable/disable network limiting"""
        self.enabled = enabled
        log.info(f"Network limiter {'enabled' if enabled else 'disabled'}")
    
    def set_limit(self, limit_kbps: int):
        """Set network limit in KB/s"""
        self.limit_kbps = limit_kbps
        log.info(f"Network limit set to {limit_kbps} KB/s")
    
    def get_current_speed(self) -> float:
        """Get current network speed in KB/s"""
        try:
            net_io = psutil.net_io_counters()
            current_bytes = net_io.bytes_sent + net_io.bytes_recv
            current_time = time.time()
            
            if self._last_bytes > 0:
                delta_bytes = current_bytes - self._last_bytes
                delta_time = current_time - self._last_time
                speed_kbps = (delta_bytes / 1024) / delta_time if delta_time > 0 else 0
            else:
                speed_kbps = 0
            
            self._last_bytes = current_bytes
            self._last_time = current_time
            
            return speed_kbps
        except Exception as e:
            log.error(f"Failed to get network speed: {e}")
            return 0
    
    def should_throttle(self) -> bool:
        """Check if network should be throttled"""
        if not self.enabled:
            return False
        
        current = self.get_current_speed()
        return current > self.limit_kbps
