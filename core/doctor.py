"""
Ryx AI - Doctor Command

Comprehensive health check and self-healing system that:
- Audits all system components
- Runs self-healing routines
- Reports gaps and suggests fixes
- Provides actionable recommendations

Usage:
    from core.doctor import run_doctor
    report = run_doctor()
    print(report.summary())
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class CheckResult:
    """Result of a single health check"""
    name: str
    status: HealthStatus
    message: str
    details: Optional[str] = None
    fix_suggestion: Optional[str] = None
    auto_fixed: bool = False


@dataclass
class DoctorReport:
    """Complete doctor report"""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    checks: List[CheckResult] = field(default_factory=list)
    auto_fixes_applied: int = 0
    total_issues: int = 0
    critical_issues: int = 0
    
    def add_check(self, result: CheckResult):
        """Add a check result"""
        self.checks.append(result)
        if result.status == HealthStatus.ERROR:
            self.total_issues += 1
            self.critical_issues += 1
        elif result.status == HealthStatus.WARNING:
            self.total_issues += 1
        if result.auto_fixed:
            self.auto_fixes_applied += 1
    
    @property
    def is_healthy(self) -> bool:
        """Check if system is overall healthy"""
        return self.critical_issues == 0
    
    def summary(self) -> str:
        """Generate human-readable summary"""
        lines = [
            "═" * 60,
            "  RYX AI - DOCTOR REPORT",
            "═" * 60,
            f"  Timestamp: {self.timestamp}",
            f"  Status: {'✅ HEALTHY' if self.is_healthy else '❌ ISSUES FOUND'}",
            "",
        ]
        
        # Group by status
        errors = [c for c in self.checks if c.status == HealthStatus.ERROR]
        warnings = [c for c in self.checks if c.status == HealthStatus.WARNING]
        healthy = [c for c in self.checks if c.status == HealthStatus.HEALTHY]
        
        if errors:
            lines.append("❌ ERRORS:")
            for check in errors:
                lines.append(f"   • {check.name}: {check.message}")
                if check.fix_suggestion:
                    lines.append(f"     💡 Fix: {check.fix_suggestion}")
            lines.append("")
        
        if warnings:
            lines.append("⚠️ WARNINGS:")
            for check in warnings:
                lines.append(f"   • {check.name}: {check.message}")
                if check.fix_suggestion:
                    lines.append(f"     💡 Fix: {check.fix_suggestion}")
            lines.append("")
        
        if healthy:
            lines.append("✅ HEALTHY:")
            for check in healthy:
                lines.append(f"   • {check.name}: {check.message}")
            lines.append("")
        
        # Summary stats
        lines.extend([
            "─" * 60,
            f"  Total Checks: {len(self.checks)}",
            f"  Issues: {self.total_issues} ({self.critical_issues} critical)",
            f"  Auto-Fixed: {self.auto_fixes_applied}",
            "═" * 60,
        ])
        
        return "\n".join(lines)


class Doctor:
    """
    System health checker and self-healer.
    
    Checks:
    - Ollama connectivity and models
    - Database integrity
    - Memory system health
    - Cache status
    - Configuration validity
    - VRAM status
    
    Self-healing:
    - Clears stale caches
    - Repairs database issues
    - Removes corrupted memory entries
    """
    
    def __init__(self, auto_heal: bool = True):
        self.auto_heal = auto_heal
        self.report = DoctorReport()
    
    def run_all_checks(self) -> DoctorReport:
        """Run all health checks"""
        print("🩺 Running Ryx AI Doctor...")
        print()
        
        # Core infrastructure
        self._check_ollama()
        self._check_database()
        self._check_memory_system()
        
        # Configuration
        self._check_config()
        self._check_paths()
        
        # Resources
        self._check_vram()
        self._check_disk_space()
        
        # Cache and cleanup
        self._check_cache()
        
        # Self-healing
        if self.auto_heal:
            self._run_self_healing()
        
        return self.report
    
    def _check_ollama(self):
        """Check Ollama connectivity and models"""
        try:
            import requests
            ollama_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            
            # Check connectivity
            resp = requests.get(f"{ollama_url}/api/tags", timeout=5)
            if resp.status_code != 200:
                self.report.add_check(CheckResult(
                    name="Ollama Service",
                    status=HealthStatus.ERROR,
                    message=f"HTTP {resp.status_code}",
                    fix_suggestion="Start Ollama: systemctl --user start ollama"
                ))
                return
            
            # Check models
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            
            if not models:
                self.report.add_check(CheckResult(
                    name="Ollama Models",
                    status=HealthStatus.WARNING,
                    message="No models installed",
                    fix_suggestion="Pull a model: ollama pull qwen2.5:7b"
                ))
            else:
                # Check for recommended models
                recommended = ["qwen2.5:1.5b", "qwen2.5-coder:14b", "mistral-nemo:12b"]
                missing = [m for m in recommended if not any(m in model for model in models)]
                
                if missing:
                    self.report.add_check(CheckResult(
                        name="Ollama Models",
                        status=HealthStatus.WARNING,
                        message=f"Missing recommended: {', '.join(missing)}",
                        details=f"Installed: {', '.join(models[:5])}",
                        fix_suggestion=f"Pull: ollama pull {missing[0]}"
                    ))
                else:
                    self.report.add_check(CheckResult(
                        name="Ollama Models",
                        status=HealthStatus.HEALTHY,
                        message=f"{len(models)} models available"
                    ))
            
            self.report.add_check(CheckResult(
                name="Ollama Service",
                status=HealthStatus.HEALTHY,
                message=f"Connected at {ollama_url}"
            ))
            
        except requests.exceptions.ConnectionError:
            self.report.add_check(CheckResult(
                name="Ollama Service",
                status=HealthStatus.ERROR,
                message="Cannot connect to Ollama",
                fix_suggestion="Start Ollama: systemctl --user start ollama"
            ))
        except Exception as e:
            self.report.add_check(CheckResult(
                name="Ollama Service",
                status=HealthStatus.ERROR,
                message=str(e)
            ))
    
    def _check_database(self):
        """Check database integrity"""
        try:
            from core.paths import get_data_dir
            import sqlite3
            
            data_dir = get_data_dir()
            db_files = list(data_dir.glob("*.db"))
            
            if not db_files:
                self.report.add_check(CheckResult(
                    name="Databases",
                    status=HealthStatus.WARNING,
                    message="No databases found",
                    details="Databases will be created on first use"
                ))
                return
            
            corrupt_dbs = []
            for db_file in db_files:
                try:
                    conn = sqlite3.connect(db_file)
                    conn.execute("SELECT 1")
                    conn.execute("PRAGMA integrity_check")
                    conn.close()
                except sqlite3.DatabaseError as e:
                    corrupt_dbs.append((db_file.name, str(e)))
            
            if corrupt_dbs:
                self.report.add_check(CheckResult(
                    name="Databases",
                    status=HealthStatus.ERROR,
                    message=f"Corrupted: {', '.join(db[0] for db in corrupt_dbs)}",
                    fix_suggestion="Delete and recreate corrupted databases"
                ))
            else:
                self.report.add_check(CheckResult(
                    name="Databases",
                    status=HealthStatus.HEALTHY,
                    message=f"{len(db_files)} databases healthy"
                ))
                
        except Exception as e:
            self.report.add_check(CheckResult(
                name="Databases",
                status=HealthStatus.ERROR,
                message=str(e)
            ))
    
    def _check_memory_system(self):
        """Check memory system health"""
        try:
            from core.memory import get_persistent_memory
            
            memory = get_persistent_memory()
            stats = memory.get_stats()
            
            total = stats.get("total_memories", 0)
            db_size = stats.get("db_size_mb", 0)
            
            if db_size > 100:  # Over 100MB
                self.report.add_check(CheckResult(
                    name="Memory System",
                    status=HealthStatus.WARNING,
                    message=f"Large memory database: {db_size:.1f}MB",
                    fix_suggestion="Run memory compaction: ryx /heal"
                ))
            else:
                self.report.add_check(CheckResult(
                    name="Memory System",
                    status=HealthStatus.HEALTHY,
                    message=f"{total} memories, {db_size:.1f}MB"
                ))
                
        except Exception as e:
            self.report.add_check(CheckResult(
                name="Memory System",
                status=HealthStatus.WARNING,
                message=f"Could not check: {e}"
            ))
    
    def _check_config(self):
        """Check configuration files"""
        try:
            from core.paths import get_config_dir
            import json
            
            config_dir = get_config_dir()
            required_configs = ["models.json", "settings.json"]
            
            missing = []
            invalid = []
            
            for config_name in required_configs:
                config_path = config_dir / config_name
                if not config_path.exists():
                    missing.append(config_name)
                else:
                    try:
                        with open(config_path) as f:
                            json.load(f)
                    except json.JSONDecodeError:
                        invalid.append(config_name)
            
            if invalid:
                self.report.add_check(CheckResult(
                    name="Configuration",
                    status=HealthStatus.ERROR,
                    message=f"Invalid JSON: {', '.join(invalid)}",
                    fix_suggestion="Fix JSON syntax in config files"
                ))
            elif missing:
                self.report.add_check(CheckResult(
                    name="Configuration",
                    status=HealthStatus.WARNING,
                    message=f"Missing: {', '.join(missing)}",
                    details="Using default configuration"
                ))
            else:
                self.report.add_check(CheckResult(
                    name="Configuration",
                    status=HealthStatus.HEALTHY,
                    message="All configs valid"
                ))
                
        except Exception as e:
            self.report.add_check(CheckResult(
                name="Configuration",
                status=HealthStatus.ERROR,
                message=str(e)
            ))
    
    def _check_paths(self):
        """Check required paths and permissions"""
        try:
            from core.paths import get_data_dir, get_config_dir, get_cache_dir
            
            paths_to_check = [
                ("Data", get_data_dir()),
                ("Config", get_config_dir()),
                ("Cache", get_cache_dir()),
            ]
            
            issues = []
            for name, path in paths_to_check:
                if not path.exists():
                    try:
                        path.mkdir(parents=True, exist_ok=True)
                    except PermissionError:
                        issues.append(f"{name}: Permission denied")
                elif not os.access(path, os.W_OK):
                    issues.append(f"{name}: Not writable")
            
            if issues:
                self.report.add_check(CheckResult(
                    name="Paths",
                    status=HealthStatus.ERROR,
                    message="; ".join(issues),
                    fix_suggestion="Check directory permissions"
                ))
            else:
                self.report.add_check(CheckResult(
                    name="Paths",
                    status=HealthStatus.HEALTHY,
                    message="All paths accessible"
                ))
                
        except Exception as e:
            self.report.add_check(CheckResult(
                name="Paths",
                status=HealthStatus.ERROR,
                message=str(e)
            ))
    
    def _check_vram(self):
        """Check VRAM status"""
        try:
            from core.vram_guard import get_vram_guard
            
            guard = get_vram_guard()
            status = guard.get_vram_status(refresh=True)
            
            if status.total_mb == 0:
                self.report.add_check(CheckResult(
                    name="VRAM",
                    status=HealthStatus.WARNING,
                    message="Could not detect VRAM",
                    details="ROCm tools may not be installed"
                ))
            elif not status.is_safe:
                self.report.add_check(CheckResult(
                    name="VRAM",
                    status=HealthStatus.WARNING,
                    message=f"High usage: {status.usage_percent:.1f}%",
                    fix_suggestion="Unload unused models to free VRAM"
                ))
            else:
                self.report.add_check(CheckResult(
                    name="VRAM",
                    status=HealthStatus.HEALTHY,
                    message=f"{status.used_mb}MB / {status.total_mb}MB ({status.usage_percent:.1f}%)"
                ))
                
        except ImportError:
            self.report.add_check(CheckResult(
                name="VRAM",
                status=HealthStatus.UNKNOWN,
                message="VRAM guard not available"
            ))
        except Exception as e:
            self.report.add_check(CheckResult(
                name="VRAM",
                status=HealthStatus.WARNING,
                message=f"Check failed: {e}"
            ))
    
    def _check_disk_space(self):
        """Check available disk space"""
        try:
            from core.paths import get_data_dir
            import shutil
            
            data_dir = get_data_dir()
            total, used, free = shutil.disk_usage(data_dir)
            
            free_gb = free / (1024 ** 3)
            
            if free_gb < 1:
                self.report.add_check(CheckResult(
                    name="Disk Space",
                    status=HealthStatus.ERROR,
                    message=f"Low disk space: {free_gb:.1f}GB free",
                    fix_suggestion="Free up disk space or clean caches"
                ))
            elif free_gb < 5:
                self.report.add_check(CheckResult(
                    name="Disk Space",
                    status=HealthStatus.WARNING,
                    message=f"Disk space low: {free_gb:.1f}GB free"
                ))
            else:
                self.report.add_check(CheckResult(
                    name="Disk Space",
                    status=HealthStatus.HEALTHY,
                    message=f"{free_gb:.1f}GB free"
                ))
                
        except Exception as e:
            self.report.add_check(CheckResult(
                name="Disk Space",
                status=HealthStatus.WARNING,
                message=f"Check failed: {e}"
            ))
    
    def _check_cache(self):
        """Check cache status and size"""
        try:
            from core.paths import get_cache_dir
            
            cache_dir = get_cache_dir()
            
            # Calculate cache size
            total_size = 0
            file_count = 0
            for root, dirs, files in os.walk(cache_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)
                    file_count += 1
            
            size_mb = total_size / (1024 * 1024)
            
            if size_mb > 500:  # Over 500MB
                self.report.add_check(CheckResult(
                    name="Cache",
                    status=HealthStatus.WARNING,
                    message=f"Large cache: {size_mb:.1f}MB ({file_count} files)",
                    fix_suggestion="Clear cache: ryx /heal aggressive"
                ))
            else:
                self.report.add_check(CheckResult(
                    name="Cache",
                    status=HealthStatus.HEALTHY,
                    message=f"{size_mb:.1f}MB ({file_count} files)"
                ))
                
        except Exception as e:
            self.report.add_check(CheckResult(
                name="Cache",
                status=HealthStatus.WARNING,
                message=f"Check failed: {e}"
            ))
    
    def _run_self_healing(self):
        """Run automatic self-healing routines"""
        try:
            from core.self_healer import SelfHealer
            
            healer = SelfHealer()
            result = healer.heal(aggressive=False)
            
            if result.entries_removed > 0:
                self.report.add_check(CheckResult(
                    name="Self-Healing",
                    status=HealthStatus.HEALTHY,
                    message=f"Cleaned {result.entries_removed} entries",
                    auto_fixed=True
                ))
            else:
                self.report.add_check(CheckResult(
                    name="Self-Healing",
                    status=HealthStatus.HEALTHY,
                    message="No cleanup needed"
                ))
                
        except Exception as e:
            self.report.add_check(CheckResult(
                name="Self-Healing",
                status=HealthStatus.WARNING,
                message=f"Could not run: {e}"
            ))


def run_doctor(auto_heal: bool = True) -> DoctorReport:
    """
    Run the doctor command and return a report.
    
    Args:
        auto_heal: Whether to automatically fix issues
        
    Returns:
        DoctorReport with all check results
    """
    doctor = Doctor(auto_heal=auto_heal)
    return doctor.run_all_checks()


def print_doctor_report(auto_heal: bool = True):
    """Run doctor and print the report"""
    report = run_doctor(auto_heal=auto_heal)
    print(report.summary())
    return report.is_healthy


if __name__ == "__main__":
    # Can be run directly: python -m core.doctor
    success = print_doctor_report()
    sys.exit(0 if success else 1)
