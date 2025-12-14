"""
Performance Tests

Tests for startup time, memory usage, and lazy loading.
"""

import pytest
import time
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestStartupPerformance:
    """Test startup performance"""
    
    def test_lazy_loader_creation(self):
        """Test lazy loader creates quickly"""
        from src.core.lazy_loader import create_lazy_loader
        
        start = time.perf_counter()
        loader = create_lazy_loader()
        elapsed = time.perf_counter() - start
        
        assert elapsed < 0.01, f"Lazy loader took {elapsed:.3f}s (should be < 10ms)"
        assert len(loader.modules) > 0
    
    def test_feature_registry_creation(self):
        """Test feature registry creates quickly"""
        from src.core.lazy_loader import create_lazy_loader, create_feature_registry
        
        loader = create_lazy_loader()
        
        start = time.perf_counter()
        registry = create_feature_registry(loader)
        elapsed = time.perf_counter() - start
        
        assert elapsed < 0.01, f"Feature registry took {elapsed:.3f}s (should be < 10ms)"
        assert len(registry.features) > 0
    
    def test_settings_load_time(self):
        """Test settings load quickly"""
        from src.core.settings_manager import SettingsManager
        
        start = time.perf_counter()
        settings = SettingsManager()
        elapsed = time.perf_counter() - start
        
        assert elapsed < 0.1, f"Settings took {elapsed:.3f}s (should be < 100ms)"
    
    def test_perf_monitor_overhead(self):
        """Test performance monitor has minimal overhead"""
        from src.core.perf_monitor import PerfTimer
        
        # Time without monitoring
        start = time.perf_counter()
        for _ in range(1000):
            pass
        baseline = time.perf_counter() - start
        
        # Time with monitoring
        start = time.perf_counter()
        for _ in range(1000):
            with PerfTimer("test"):
                pass
        monitored = time.perf_counter() - start
        
        overhead = monitored - baseline
        overhead_percent = (overhead / baseline) * 100 if baseline > 0 else 0
        
        assert overhead_percent < 20, f"Monitoring overhead: {overhead_percent:.1f}% (should be < 20%)"


class TestLazyLoading:
    """Test lazy loading functionality"""
    
    def test_lazy_module_not_loaded_initially(self):
        """Test modules don't load until accessed"""
        from src.core.lazy_loader import LazyModule
        
        module = LazyModule("os")
        assert not module.is_loaded()
    
    def test_lazy_module_loads_on_access(self):
        """Test module loads on first access"""
        from src.core.lazy_loader import LazyModule
        
        module = LazyModule("os")
        _ = module.path  # Access attribute
        assert module.is_loaded()
    
    def test_lazy_loader_preload(self):
        """Test preloading specific modules"""
        from src.core.lazy_loader import LazyLoader
        
        loader = LazyLoader()
        loader.register("json", "json")
        loader.register("sys", "sys")
        
        assert not loader.modules["json"].is_loaded()
        
        loader.preload("json")
        
        assert loader.modules["json"].is_loaded()
        assert not loader.modules["sys"].is_loaded()


class TestPerformanceMonitor:
    """Test performance monitoring"""
    
    def test_record_metric(self):
        """Test recording a metric"""
        from src.core.perf_monitor import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        monitor.record("test_metric", 42.5, "ms")
        
        latest = monitor.get_latest("test_metric")
        assert latest == 42.5
    
    def test_threshold_warning(self):
        """Test threshold warnings"""
        from src.core.perf_monitor import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        # Record value above warning threshold
        monitor.record("startup_time", 1500, "ms")  # Warning at 1000ms
        
        warnings = monitor.get_warnings()
        assert len(warnings) > 0
    
    def test_get_stats(self):
        """Test statistics calculation"""
        from src.core.perf_monitor import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        monitor.record("test", 10, "ms")
        monitor.record("test", 20, "ms")
        monitor.record("test", 30, "ms")
        
        stats = monitor.get_stats("test")
        assert stats["min"] == 10
        assert stats["max"] == 30
        assert stats["avg"] == 20
        assert stats["count"] == 3


class TestMemoryUsage:
    """Test memory usage"""
    
    @pytest.mark.skipif(
        not pytest.importorskip("psutil"),
        reason="psutil not available"
    )
    def test_memory_profiler(self):
        """Test memory profiler"""
        from src.core.perf_monitor import MemoryProfiler
        
        profiler = MemoryProfiler()
        
        snapshot1 = profiler.snapshot("start")
        assert snapshot1 is not None
        assert "rss" in snapshot1
        
        # Allocate some memory
        data = [0] * 1000000
        
        snapshot2 = profiler.snapshot("after_alloc")
        assert snapshot2["rss"] >= snapshot1["rss"]
        
        del data


class TestBuildSystem:
    """Test build system"""
    
    def test_makefile_exists(self):
        """Test Makefile exists"""
        makefile = Path(__file__).parent.parent / "Makefile"
        assert makefile.exists()
    
    def test_rebuild_script_exists(self):
        """Test rebuild script exists"""
        script = Path(__file__).parent.parent / "rebuild.sh"
        assert script.exists()
        assert script.stat().st_mode & 0o111  # Executable


class TestFeatureIntegration:
    """Test feature integration"""
    
    def test_all_features_registered(self):
        """Test all features are registered"""
        from src.core.lazy_loader import create_lazy_loader, create_feature_registry
        
        loader = create_lazy_loader()
        registry = create_feature_registry(loader)
        
        expected_features = [
            "split_view",
            "reader_mode",
            "shortcuts",
            "tab_groups",
            "force_dark",
            "resource_limiter",
            "container_tabs",
        ]
        
        for feature in expected_features:
            assert feature in registry.features
    
    def test_feature_priorities(self):
        """Test features have correct priorities"""
        from src.core.lazy_loader import create_lazy_loader, create_feature_registry
        
        loader = create_lazy_loader()
        registry = create_feature_registry(loader)
        
        # Critical features should have low priority numbers
        assert registry.features["shortcuts"]["priority"] <= 3
        
        # Non-critical features should have higher priority
        assert registry.features["container_tabs"]["priority"] >= 7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
