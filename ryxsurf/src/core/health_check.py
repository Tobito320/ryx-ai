"""
Health Check System

Monitors browser health and provides diagnostics.
"""

import logging
import time
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass

log = logging.getLogger("ryxsurf.health")


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    name: str
    status: str  # ok, warning, error
    message: str
    details: Optional[dict] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class HealthChecker:
    """Performs health checks on browser components"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.checks: List[HealthCheckResult] = []
    
    def check_all(self) -> List[HealthCheckResult]:
        """Run all health checks"""
        self.checks.clear()
        
        self.check_directories()
        self.check_settings()
        self.check_dependencies()
        self.check_performance()
        self.check_disk_space()
        self.check_memory()
        
        return self.checks
    
    def check_directories(self):
        """Check required directories exist"""
        required_dirs = [
            self.config_dir,
            self.config_dir / "data",
            self.config_dir / "cache",
        ]
        
        for dir_path in required_dirs:
            if not dir_path.exists():
                self.checks.append(HealthCheckResult(
                    name="directories",
                    status="error",
                    message=f"Missing directory: {dir_path}",
                    details={"path": str(dir_path)}
                ))
                return
        
        self.checks.append(HealthCheckResult(
            name="directories",
            status="ok",
            message="All required directories exist"
        ))
    
    def check_settings(self):
        """Check settings are valid"""
        settings_file = self.config_dir / "settings.json"
        
        if not settings_file.exists():
            self.checks.append(HealthCheckResult(
                name="settings",
                status="warning",
                message="Settings file not found (will use defaults)"
            ))
            return
        
        try:
            import json
            with open(settings_file) as f:
                settings = json.load(f)
            
            # Check for required keys
            required_keys = ["appearance", "privacy", "performance"]
            missing = [k for k in required_keys if k not in settings]
            
            if missing:
                self.checks.append(HealthCheckResult(
                    name="settings",
                    status="warning",
                    message=f"Missing settings keys: {', '.join(missing)}",
                    details={"missing_keys": missing}
                ))
            else:
                self.checks.append(HealthCheckResult(
                    name="settings",
                    status="ok",
                    message="Settings file is valid"
                ))
        
        except Exception as e:
            self.checks.append(HealthCheckResult(
                name="settings",
                status="error",
                message=f"Failed to load settings: {e}"
            ))
    
    def check_dependencies(self):
        """Check required dependencies"""
        dependencies = {
            "gi": "PyGObject (GTK)",
            "webkit2": "WebKit2GTK",
        }
        
        optional_deps = {
            "psutil": "Resource monitoring",
        }
        
        missing = []
        for module, name in dependencies.items():
            try:
                if module == "webkit2":
                    import gi
                    gi.require_version('WebKit', '6.0')
                    from gi.repository import WebKit
                else:
                    __import__(module)
            except Exception:
                missing.append(name)
        
        if missing:
            self.checks.append(HealthCheckResult(
                name="dependencies",
                status="error",
                message=f"Missing dependencies: {', '.join(missing)}",
                details={"missing": missing}
            ))
        else:
            self.checks.append(HealthCheckResult(
                name="dependencies",
                status="ok",
                message="All required dependencies available"
            ))
        
        # Check optional
        missing_optional = []
        for module, name in optional_deps.items():
            try:
                __import__(module)
            except Exception:
                missing_optional.append(name)
        
        if missing_optional:
            self.checks.append(HealthCheckResult(
                name="optional_dependencies",
                status="warning",
                message=f"Optional dependencies missing: {', '.join(missing_optional)}",
                details={"missing": missing_optional}
            ))
    
    def check_performance(self):
        """Check performance metrics"""
        from .perf_monitor import perf_monitor
        
        # Check startup time
        startup = perf_monitor.get_latest("startup_time")
        if startup:
            if startup > 2000:
                self.checks.append(HealthCheckResult(
                    name="performance",
                    status="warning",
                    message=f"Slow startup: {startup:.0f}ms (target: < 1000ms)",
                    details={"startup_ms": startup}
                ))
            else:
                self.checks.append(HealthCheckResult(
                    name="performance",
                    status="ok",
                    message=f"Startup time: {startup:.0f}ms"
                ))
        
        # Check memory
        memory = perf_monitor.get_latest("memory_usage")
        if memory:
            if memory > 2048:
                self.checks.append(HealthCheckResult(
                    name="memory",
                    status="warning",
                    message=f"High memory usage: {memory:.0f}MB",
                    details={"memory_mb": memory}
                ))
    
    def check_disk_space(self):
        """Check available disk space"""
        import shutil
        
        try:
            usage = shutil.disk_usage(self.config_dir)
            free_gb = usage.free / (1024 ** 3)
            
            if free_gb < 0.5:
                self.checks.append(HealthCheckResult(
                    name="disk_space",
                    status="error",
                    message=f"Low disk space: {free_gb:.1f}GB free",
                    details={"free_gb": free_gb}
                ))
            elif free_gb < 2:
                self.checks.append(HealthCheckResult(
                    name="disk_space",
                    status="warning",
                    message=f"Disk space running low: {free_gb:.1f}GB free",
                    details={"free_gb": free_gb}
                ))
            else:
                self.checks.append(HealthCheckResult(
                    name="disk_space",
                    status="ok",
                    message=f"Disk space: {free_gb:.1f}GB free"
                ))
        except Exception as e:
            log.error(f"Failed to check disk space: {e}")
    
    def check_memory(self):
        """Check system memory"""
        try:
            import psutil
            
            mem = psutil.virtual_memory()
            available_gb = mem.available / (1024 ** 3)
            percent = mem.percent
            
            if percent > 90:
                self.checks.append(HealthCheckResult(
                    name="system_memory",
                    status="error",
                    message=f"Low system memory: {percent:.0f}% used",
                    details={"available_gb": available_gb, "percent": percent}
                ))
            elif percent > 80:
                self.checks.append(HealthCheckResult(
                    name="system_memory",
                    status="warning",
                    message=f"High system memory: {percent:.0f}% used",
                    details={"available_gb": available_gb, "percent": percent}
                ))
            else:
                self.checks.append(HealthCheckResult(
                    name="system_memory",
                    status="ok",
                    message=f"System memory: {available_gb:.1f}GB available"
                ))
        except ImportError:
            pass  # psutil not available
    
    def get_summary(self) -> Dict[str, int]:
        """Get summary of check results"""
        summary = {"ok": 0, "warning": 0, "error": 0}
        
        for check in self.checks:
            summary[check.status] = summary.get(check.status, 0) + 1
        
        return summary
    
    def print_report(self):
        """Print health check report"""
        print("\n" + "="*60)
        print("🏥 HEALTH CHECK REPORT")
        print("="*60)
        
        for check in self.checks:
            icon = {
                "ok": "✓",
                "warning": "⚠",
                "error": "✗",
            }.get(check.status, "?")
            
            print(f"{icon} {check.name:20s} {check.status.upper():8s} {check.message}")
        
        print("-"*60)
        summary = self.get_summary()
        print(f"Total: {summary['ok']} OK, {summary['warning']} warnings, {summary['error']} errors")
        print("="*60 + "\n")
    
    def is_healthy(self) -> bool:
        """Check if browser is healthy"""
        summary = self.get_summary()
        return summary.get("error", 0) == 0


class AutoFix:
    """Automatic fixes for common issues"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
    
    def fix_missing_directories(self):
        """Create missing directories"""
        dirs = [
            self.config_dir,
            self.config_dir / "data",
            self.config_dir / "cache",
            self.config_dir / "data" / "containers",
        ]
        
        for dir_path in dirs:
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                log.info(f"Created directory: {dir_path}")
    
    def fix_settings(self):
        """Create default settings if missing"""
        settings_file = self.config_dir / "settings.json"
        
        if not settings_file.exists():
            from .settings_manager import SettingsManager
            
            settings = SettingsManager()
            settings.save()
            log.info("Created default settings file")
    
    def clear_cache(self):
        """Clear browser cache"""
        cache_dir = self.config_dir / "cache"
        
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)
            cache_dir.mkdir()
            log.info("Cleared cache")
    
    def optimize_database(self):
        """Optimize browser databases"""
        # Placeholder for future database optimization
        pass
    
    def run_all_fixes(self):
        """Run all automatic fixes"""
        log.info("Running auto-fixes...")
        
        self.fix_missing_directories()
        self.fix_settings()
        
        log.info("Auto-fixes complete")


def run_health_check(config_dir: Path, auto_fix: bool = False) -> bool:
    """
    Run health check and optionally fix issues
    
    Returns:
        True if healthy, False otherwise
    """
    checker = HealthChecker(config_dir)
    checker.check_all()
    checker.print_report()
    
    if auto_fix and not checker.is_healthy():
        print("\n🔧 Running auto-fixes...\n")
        fixer = AutoFix(config_dir)
        fixer.run_all_fixes()
        
        # Re-check
        print("\n🔄 Re-checking health...\n")
        checker.check_all()
        checker.print_report()
    
    return checker.is_healthy()
