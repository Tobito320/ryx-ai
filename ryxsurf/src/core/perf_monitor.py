"""
Performance Monitor

Real-time performance tracking and optimization suggestions.
"""

import time
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from collections import deque

log = logging.getLogger("ryxsurf.perf")


@dataclass
class PerfMetric:
    """Performance metric"""
    name: str
    value: float
    unit: str
    timestamp: float
    category: str = "general"


@dataclass
class PerfThreshold:
    """Performance threshold"""
    name: str
    warning: float
    critical: float
    unit: str


class PerfTimer:
    """Simple performance timer"""
    
    def __init__(self, name: str, log_result: bool = False):
        self.name = name
        self.log_result = log_result
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        self.end_time = time.perf_counter()
        elapsed = self.elapsed_ms()
        
        if self.log_result:
            if elapsed > 100:
                log.warning(f"⏱️  {self.name}: {elapsed:.1f}ms (SLOW)")
            else:
                log.debug(f"⏱️  {self.name}: {elapsed:.1f}ms")
    
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds"""
        if self.start_time is None:
            return 0
        
        end = self.end_time or time.perf_counter()
        return (end - self.start_time) * 1000


class PerformanceMonitor:
    """Monitors browser performance"""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.metrics: Dict[str, deque] = {}
        self.thresholds: Dict[str, PerfThreshold] = {}
        self.warnings: List[str] = []
        self._init_thresholds()
    
    def _init_thresholds(self):
        """Initialize performance thresholds"""
        self.thresholds = {
            "startup_time": PerfThreshold("startup_time", 1000, 2000, "ms"),
            "tab_switch_time": PerfThreshold("tab_switch_time", 100, 300, "ms"),
            "page_load_time": PerfThreshold("page_load_time", 2000, 5000, "ms"),
            "memory_usage": PerfThreshold("memory_usage", 1024, 2048, "MB"),
            "cpu_usage": PerfThreshold("cpu_usage", 50, 80, "%"),
            "frame_time": PerfThreshold("frame_time", 16.7, 33.3, "ms"),  # 60fps, 30fps
        }
    
    def record(self, name: str, value: float, unit: str = "", category: str = "general"):
        """Record a performance metric"""
        if name not in self.metrics:
            self.metrics[name] = deque(maxlen=self.window_size)
        
        metric = PerfMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=time.time(),
            category=category
        )
        
        self.metrics[name].append(metric)
        
        # Check thresholds
        if name in self.thresholds:
            self._check_threshold(name, value)
    
    def _check_threshold(self, name: str, value: float):
        """Check if value exceeds thresholds"""
        threshold = self.thresholds[name]
        
        if value >= threshold.critical:
            warning = f"CRITICAL: {name} = {value:.1f}{threshold.unit} (threshold: {threshold.critical}{threshold.unit})"
            self.warnings.append(warning)
            log.error(warning)
        elif value >= threshold.warning:
            warning = f"WARNING: {name} = {value:.1f}{threshold.unit} (threshold: {threshold.warning}{threshold.unit})"
            self.warnings.append(warning)
            log.warning(warning)
    
    def get_average(self, name: str) -> Optional[float]:
        """Get average of metric"""
        if name not in self.metrics or not self.metrics[name]:
            return None
        
        values = [m.value for m in self.metrics[name]]
        return sum(values) / len(values)
    
    def get_latest(self, name: str) -> Optional[float]:
        """Get latest metric value"""
        if name not in self.metrics or not self.metrics[name]:
            return None
        
        return self.metrics[name][-1].value
    
    def get_stats(self, name: str) -> Optional[dict]:
        """Get statistics for metric"""
        if name not in self.metrics or not self.metrics[name]:
            return None
        
        values = [m.value for m in self.metrics[name]]
        
        return {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "count": len(values),
            "latest": values[-1],
        }
    
    def get_warnings(self, recent_only: bool = True) -> List[str]:
        """Get performance warnings"""
        if recent_only:
            # Return last 10 warnings
            return self.warnings[-10:]
        return self.warnings.copy()
    
    def clear_warnings(self):
        """Clear warnings"""
        self.warnings.clear()
    
    def get_suggestions(self) -> List[str]:
        """Get optimization suggestions"""
        suggestions = []
        
        # Check startup time
        startup = self.get_average("startup_time")
        if startup and startup > 1500:
            suggestions.append("Consider enabling lazy loading to improve startup time")
        
        # Check memory usage
        memory = self.get_latest("memory_usage")
        if memory and memory > 1500:
            suggestions.append("Enable tab unloading to reduce memory usage")
        
        # Check CPU usage
        cpu = self.get_average("cpu_usage")
        if cpu and cpu > 60:
            suggestions.append("Enable CPU limiter to reduce resource usage")
        
        # Check frame time
        frame_time = self.get_average("frame_time")
        if frame_time and frame_time > 20:
            suggestions.append("Reduce animations or enable hardware acceleration")
        
        return suggestions
    
    def print_summary(self):
        """Print performance summary"""
        print("\n" + "="*60)
        print("📊 PERFORMANCE SUMMARY")
        print("="*60)
        
        for name, metrics in self.metrics.items():
            if not metrics:
                continue
            
            stats = self.get_stats(name)
            threshold = self.thresholds.get(name)
            
            unit = metrics[0].unit
            avg = stats["avg"]
            
            status = "✓"
            if threshold:
                if avg >= threshold.critical:
                    status = "✗"
                elif avg >= threshold.warning:
                    status = "⚠"
            
            print(f"{status} {name:20s} {avg:8.1f}{unit:5s} (min: {stats['min']:.1f}, max: {stats['max']:.1f})")
        
        # Suggestions
        suggestions = self.get_suggestions()
        if suggestions:
            print("\n💡 Optimization Suggestions:")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"  {i}. {suggestion}")
        
        print("="*60 + "\n")


class StartupProfiler:
    """Profiles browser startup"""
    
    def __init__(self):
        self.timings: Dict[str, float] = {}
        self.start_time = time.perf_counter()
    
    def mark(self, label: str):
        """Mark a point in startup"""
        elapsed = (time.perf_counter() - self.start_time) * 1000
        self.timings[label] = elapsed
        log.info(f"🏁 {label}: {elapsed:.1f}ms")
    
    def get_timings(self) -> Dict[str, float]:
        """Get all timings"""
        return self.timings.copy()
    
    def print_report(self):
        """Print startup report"""
        if not self.timings:
            return
        
        print("\n" + "="*60)
        print("🚀 STARTUP PROFILE")
        print("="*60)
        
        total = max(self.timings.values())
        
        for label, timing in sorted(self.timings.items(), key=lambda x: x[1]):
            percentage = (timing / total * 100) if total > 0 else 0
            print(f"  {timing:7.1f}ms ({percentage:5.1f}%)  {label}")
        
        print("-"*60)
        print(f"  {total:7.1f}ms (100.0%)  TOTAL")
        print("="*60 + "\n")


class MemoryProfiler:
    """Profiles memory usage"""
    
    def __init__(self):
        self.snapshots: List[tuple] = []
    
    def snapshot(self, label: str = ""):
        """Take memory snapshot"""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            
            snapshot = {
                "label": label,
                "timestamp": time.time(),
                "rss": mem_info.rss / 1024 / 1024,  # MB
                "vms": mem_info.vms / 1024 / 1024,  # MB
            }
            
            self.snapshots.append((label, snapshot))
            log.debug(f"📊 Memory: {snapshot['rss']:.1f}MB RSS, {snapshot['vms']:.1f}MB VMS - {label}")
            
            return snapshot
        except ImportError:
            log.warning("psutil not available for memory profiling")
            return None
    
    def print_report(self):
        """Print memory report"""
        if not self.snapshots:
            return
        
        print("\n" + "="*60)
        print("💾 MEMORY PROFILE")
        print("="*60)
        
        for label, snapshot in self.snapshots:
            print(f"  {snapshot['rss']:8.1f} MB RSS  {snapshot['vms']:8.1f} MB VMS  {label}")
        
        if len(self.snapshots) > 1:
            first_rss = self.snapshots[0][1]['rss']
            last_rss = self.snapshots[-1][1]['rss']
            delta = last_rss - first_rss
            print("-"*60)
            print(f"  {delta:+8.1f} MB      Memory growth")
        
        print("="*60 + "\n")


# Global instances
perf_monitor = PerformanceMonitor()
startup_profiler = StartupProfiler()
memory_profiler = MemoryProfiler()


def timer(name: str, log_result: bool = False):
    """Decorator to time function execution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with PerfTimer(name, log_result) as t:
                result = func(*args, **kwargs)
            
            # Record metric
            perf_monitor.record(name, t.elapsed_ms(), "ms", "function")
            
            return result
        return wrapper
    return decorator
