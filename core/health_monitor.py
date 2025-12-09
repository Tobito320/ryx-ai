"""
Ryx AI - Health Monitor
Continuous system monitoring with automatic healing capabilities
"""

import os
import time
import sqlite3
import requests
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from core.paths import get_project_root, get_data_dir, get_config_dir, get_runtime_dir

# Optional dependency
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

class HealthStatus(Enum):
    """System health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"

class IncidentSeverity(Enum):
    """Incident severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class HealthCheck:
    """Result of a health check"""
    component: str
    status: HealthStatus
    message: str
    timestamp: datetime
    details: Dict[str, Any]

@dataclass
class Incident:
    """A system incident"""
    incident_id: str
    component: str
    severity: IncidentSeverity
    description: str
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    auto_fixed: bool = False
    fix_attempts: int = 0
    resolution: Optional[str] = None

class HealthMonitor:
    """
    Monitors system health and automatically fixes issues

    Features:
    - Continuous Monitoring: Checks every 30 seconds
    - Auto-Detect: Identifies issues (vLLM down, service not responding, DB corrupt)
    - Auto-Fix: Automatically repairs common issues
    - Incident Logging: Tracks all incidents and resolutions
    - Resource Monitoring: Tracks disk, memory, VRAM usage
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Initialize health monitor with database and monitoring settings"""
        if db_path is None:
            db_path = get_project_root() / "data" / "health_monitor.db"

        self.db_path = db_path
        
        # LLM backend URLs
        self.ollama_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.vllm_url = "http://localhost:8001"  # vLLM API endpoint (backup)
        
        self.check_interval = 30  # seconds
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None

        # Health state
        self.current_status = HealthStatus.HEALTHY
        self.last_checks: Dict[str, HealthCheck] = {}
        self.active_incidents: Dict[str, Incident] = {}

        # Initialize database
        self._init_db()

    def _init_db(self):
        """Initialize health monitoring database"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Health checks history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                component TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                timestamp TEXT NOT NULL,
                details TEXT
            )
        """)

        # Incidents
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                incident_id TEXT PRIMARY KEY,
                component TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT,
                detected_at TEXT NOT NULL,
                resolved_at TEXT,
                auto_fixed INTEGER DEFAULT 0,
                fix_attempts INTEGER DEFAULT 0,
                resolution TEXT
            )
        """)

        # Resource metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resource_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cpu_percent REAL,
                memory_percent REAL,
                disk_percent REAL,
                vram_used_mb INTEGER,
                vllm_responsive INTEGER
            )
        """)

        conn.commit()
        conn.close()

    def start_monitoring(self):
        """Start background monitoring thread"""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop monitoring thread"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                self.run_health_checks()
                time.sleep(self.check_interval)
            except Exception as e:
                # Don't let monitoring crash
                pass

    def run_health_checks(self) -> Dict[str, HealthCheck]:
        """Run all health checks"""
        checks = {}

        # Check Ollama service (primary backend)
        checks["ollama"] = self._check_ollama()
        
        # Check vLLM service (backup backend)
        checks["vllm"] = self._check_vllm()

        # Check database
        checks["database"] = self._check_database()

        # Check disk space
        checks["disk"] = self._check_disk_space()

        # Check memory
        checks["memory"] = self._check_memory()

        # Check VRAM (if applicable)
        checks["vram"] = self._check_vram()

        # Update overall status
        self.last_checks = checks
        self._update_overall_status(checks)

        # Log checks to database
        self._log_health_checks(checks)

        # Check for issues and auto-fix
        self._handle_issues(checks)

        return checks

    def _check_ollama(self) -> HealthCheck:
        """Check Ollama service health (primary backend)"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)

            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                model_names = [m.get("name", "unknown") for m in models]
                
                if models:
                    return HealthCheck(
                        component="ollama",
                        status=HealthStatus.HEALTHY,
                        message=f"Ollama running with {len(models)} models",
                        timestamp=datetime.now(),
                        details={"models": model_names, "model_count": len(models)}
                    )
                else:
                    return HealthCheck(
                        component="ollama",
                        status=HealthStatus.DEGRADED,
                        message="Ollama running but no models loaded. Run: ollama pull qwen2.5-coder:14b",
                        timestamp=datetime.now(),
                        details={"models": [], "model_count": 0}
                    )
            else:
                return HealthCheck(
                    component="ollama",
                    status=HealthStatus.DEGRADED,
                    message=f"Ollama returned status {response.status_code}",
                    timestamp=datetime.now(),
                    details={"status_code": response.status_code}
                )

        except requests.exceptions.ConnectionError:
            return HealthCheck(
                component="ollama",
                status=HealthStatus.CRITICAL,
                message="Ollama not running. Run: ollama serve",
                timestamp=datetime.now(),
                details={"error": "connection_refused"}
            )
        except Exception as e:
            return HealthCheck(
                component="ollama",
                status=HealthStatus.UNHEALTHY,
                message=f"Ollama check failed: {str(e)}",
                timestamp=datetime.now(),
                details={"error": str(e)}
            )

    def _check_vllm(self) -> HealthCheck:
        """Check vLLM service health"""
        try:
            response = requests.get(f"{self.vllm_url}/health", timeout=5)

            if response.status_code == 200:
                return HealthCheck(
                    component="vllm",
                    status=HealthStatus.HEALTHY,
                    message="vLLM running",
                    timestamp=datetime.now(),
                    details={"status": "healthy"}
                )
            else:
                return HealthCheck(
                    component="vllm",
                    status=HealthStatus.DEGRADED,
                    message=f"vLLM returned status {response.status_code}",
                    timestamp=datetime.now(),
                    details={"status_code": response.status_code}
                )

        except requests.exceptions.ConnectionError:
            return HealthCheck(
                component="vllm",
                status=HealthStatus.CRITICAL,
                message="vLLM service not responding. Run: ryx restart",
                timestamp=datetime.now(),
                details={"error": "connection_refused"}
            )
        except Exception as e:
            return HealthCheck(
                component="vllm",
                status=HealthStatus.UNHEALTHY,
                message=f"vLLM check failed: {str(e)}",
                timestamp=datetime.now(),
                details={"error": str(e)}
            )

    def _check_database(self) -> HealthCheck:
        """Check database health"""
        try:
            # Check main RAG database
            rag_db = get_project_root() / "data" / "rag_knowledge.db"

            if not rag_db.exists():
                return HealthCheck(
                    component="database",
                    status=HealthStatus.UNHEALTHY,
                    message="RAG database missing",
                    timestamp=datetime.now(),
                    details={"missing": str(rag_db)}
                )

            # Try to connect and query
            conn = sqlite3.connect(rag_db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM quick_responses")
            count = cursor.fetchone()[0]
            conn.close()

            return HealthCheck(
                component="database",
                status=HealthStatus.HEALTHY,
                message=f"Database operational, {count} cached responses",
                timestamp=datetime.now(),
                details={"cached_responses": count}
            )

        except sqlite3.DatabaseError as e:
            return HealthCheck(
                component="database",
                status=HealthStatus.CRITICAL,
                message=f"Database corrupted: {str(e)}",
                timestamp=datetime.now(),
                details={"error": str(e)}
            )
        except Exception as e:
            return HealthCheck(
                component="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database check failed: {str(e)}",
                timestamp=datetime.now(),
                details={"error": str(e)}
            )

    def _check_disk_space(self) -> HealthCheck:
        """Check disk space"""
        if not PSUTIL_AVAILABLE:
            return HealthCheck(
                component="disk",
                status=HealthStatus.HEALTHY,
                message="Disk monitoring not available (psutil not installed)",
                timestamp=datetime.now(),
                details={"monitoring": False}
            )

        try:
            usage = psutil.disk_usage(str(Path.home()))
            percent_used = usage.percent

            if percent_used > 95:
                status = HealthStatus.CRITICAL
                message = f"Disk critically full: {percent_used:.1f}%"
            elif percent_used > 85:
                status = HealthStatus.UNHEALTHY
                message = f"Disk space low: {percent_used:.1f}%"
            elif percent_used > 75:
                status = HealthStatus.DEGRADED
                message = f"Disk space: {percent_used:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk space: {percent_used:.1f}%"

            return HealthCheck(
                component="disk",
                status=status,
                message=message,
                timestamp=datetime.now(),
                details={
                    "percent_used": percent_used,
                    "free_gb": usage.free / (1024**3)
                }
            )

        except Exception as e:
            return HealthCheck(
                component="disk",
                status=HealthStatus.UNHEALTHY,
                message=f"Disk check failed: {str(e)}",
                timestamp=datetime.now(),
                details={"error": str(e)}
            )

    def _check_memory(self) -> HealthCheck:
        """Check memory usage"""
        if not PSUTIL_AVAILABLE:
            return HealthCheck(
                component="memory",
                status=HealthStatus.HEALTHY,
                message="Memory monitoring not available (psutil not installed)",
                timestamp=datetime.now(),
                details={"monitoring": False}
            )

        try:
            memory = psutil.virtual_memory()
            percent_used = memory.percent

            if percent_used > 95:
                status = HealthStatus.CRITICAL
                message = f"Memory critically high: {percent_used:.1f}%"
            elif percent_used > 85:
                status = HealthStatus.UNHEALTHY
                message = f"Memory high: {percent_used:.1f}%"
            elif percent_used > 75:
                status = HealthStatus.DEGRADED
                message = f"Memory: {percent_used:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory: {percent_used:.1f}%"

            return HealthCheck(
                component="memory",
                status=status,
                message=message,
                timestamp=datetime.now(),
                details={
                    "percent_used": percent_used,
                    "available_gb": memory.available / (1024**3)
                }
            )

        except Exception as e:
            return HealthCheck(
                component="memory",
                status=HealthStatus.UNHEALTHY,
                message=f"Memory check failed: {str(e)}",
                timestamp=datetime.now(),
                details={"error": str(e)}
            )

    def _check_vram(self) -> HealthCheck:
        """Check VRAM usage (AMD GPU)"""
        try:
            # Try to get VRAM info using rocm-smi (for AMD GPUs)
            result = subprocess.run(
                ["rocm-smi", "--showmeminfo", "vram"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Parse output
                # This is a simplified check - adjust based on actual output
                return HealthCheck(
                    component="vram",
                    status=HealthStatus.HEALTHY,
                    message="VRAM available",
                    timestamp=datetime.now(),
                    details={"available": True}
                )
            else:
                return HealthCheck(
                    component="vram",
                    status=HealthStatus.HEALTHY,
                    message="VRAM check not available",
                    timestamp=datetime.now(),
                    details={"available": False}
                )

        except FileNotFoundError:
            # rocm-smi not installed, skip check
            return HealthCheck(
                component="vram",
                status=HealthStatus.HEALTHY,
                message="VRAM monitoring not available",
                timestamp=datetime.now(),
                details={"monitoring": False}
            )
        except Exception as e:
            return HealthCheck(
                component="vram",
                status=HealthStatus.HEALTHY,
                message="VRAM check skipped",
                timestamp=datetime.now(),
                details={"error": str(e)}
            )

    def _update_overall_status(self, checks: Dict[str, HealthCheck]):
        """Update overall system status based on checks"""
        statuses = [check.status for check in checks.values()]

        if HealthStatus.CRITICAL in statuses:
            self.current_status = HealthStatus.CRITICAL
        elif HealthStatus.UNHEALTHY in statuses:
            self.current_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            self.current_status = HealthStatus.DEGRADED
        else:
            self.current_status = HealthStatus.HEALTHY

    def _handle_issues(self, checks: Dict[str, HealthCheck]):
        """Handle detected issues with auto-fix"""
        for component, check in checks.items():
            if check.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
                self._try_auto_fix(check)

    def _try_auto_fix(self, check: HealthCheck):
        """Try to automatically fix an issue"""
        component = check.component

        # Create or update incident
        incident_id = f"{component}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if component not in self.active_incidents:
            incident = Incident(
                incident_id=incident_id,
                component=component,
                severity=IncidentSeverity.ERROR if check.status == HealthStatus.UNHEALTHY else IncidentSeverity.CRITICAL,
                description=check.message,
                detected_at=datetime.now()
            )
            self.active_incidents[component] = incident
        else:
            incident = self.active_incidents[component]

        # Try component-specific fixes
        fixed = False

        if component == "ollama":
            fixed = self._fix_ollama()
        elif component == "vllm":
            fixed = self._fix_vllm()
        elif component == "database":
            fixed = self._fix_database()
        elif component == "memory":
            fixed = self._fix_memory()

        incident.fix_attempts += 1

        if fixed:
            incident.auto_fixed = True
            incident.resolved_at = datetime.now()
            incident.resolution = "Auto-fixed successfully"
            self._log_incident(incident)
            del self.active_incidents[component]
        else:
            self._log_incident(incident)

    def _fix_ollama(self) -> bool:
        """
        Try to fix Ollama service by restarting it.
        Ollama is simpler than vLLM - just restart the service.
        """
        try:
            # Try systemctl restart first (if running as service)
            result = subprocess.run(
                ["systemctl", "--user", "restart", "ollama"],
                capture_output=True,
                timeout=10
            )

            if result.returncode == 0:
                # Wait for service to be ready
                for delay in [1, 2, 4]:
                    time.sleep(delay)
                    try:
                        response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
                        if response.status_code == 200:
                            return True
                    except:
                        continue
                return False

            # Try starting ollama directly
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

            # Wait for service to be ready
            for delay in [1, 2, 4]:
                time.sleep(delay)
                try:
                    response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
                    if response.status_code == 200:
                        return True
                except:
                    continue

            return False

        except Exception:
            return False

    def _fix_vllm(self) -> bool:
        """
        Try to fix vLLM service by restarting the Docker container
        """
        try:
            import subprocess
            
            # Try to restart vLLM container
            result = subprocess.run(
                ["docker", "restart", "ryx-vllm"],
                capture_output=True,
                timeout=30
            )

            if result.returncode == 0:
                # Wait for service to be ready
                for delay in [2, 4, 8]:
                    time.sleep(delay)
                    try:
                        response = requests.get(f"{self.vllm_url}/health", timeout=5)
                        if response.status_code == 200:
                            return True
                    except:
                        continue

                return False
            else:
                return False

        except Exception:
            return False

    def _fix_database(self) -> bool:
        """Try to fix database issues"""
        try:
            rag_db = get_project_root() / "data" / "rag_knowledge.db"

            # Check for backup
            backup = rag_db.parent / f"{rag_db.stem}_backup.db"

            if backup.exists():
                # Restore from backup
                import shutil
                shutil.copy(backup, rag_db)
                return True
            else:
                # Recreate database with schema
                conn = sqlite3.connect(rag_db)
                cursor = conn.cursor()

                # Create tables (simplified - should match rag_system.py)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS quick_responses (
                        prompt_hash TEXT PRIMARY KEY,
                        response TEXT NOT NULL,
                        model_used TEXT,
                        ttl_seconds INTEGER DEFAULT 86400,
                        created_at TEXT,
                        last_used TEXT,
                        use_count INTEGER DEFAULT 0
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge (
                        query_hash TEXT PRIMARY KEY,
                        file_type TEXT,
                        file_path TEXT NOT NULL,
                        content_preview TEXT,
                        last_accessed TEXT,
                        access_count INTEGER DEFAULT 0,
                        confidence REAL DEFAULT 1.0
                    )
                """)

                conn.commit()
                conn.close()
                return True

        except Exception:
            return False

    def _fix_memory(self) -> bool:
        """Try to fix memory issues"""
        try:
            # Trigger model unloading if orchestrator is available
            # This would need to be connected to the orchestrator
            # For now, just return False (manual intervention needed)
            return False
        except Exception:
            return False

    def _log_health_checks(self, checks: Dict[str, HealthCheck]):
        """Log health checks to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for component, check in checks.items():
            cursor.execute("""
                INSERT INTO health_checks
                (component, status, message, timestamp, details)
                VALUES (?, ?, ?, ?, ?)
            """, (
                check.component,
                check.status.value,
                check.message,
                check.timestamp.isoformat(),
                str(check.details)
            ))

        conn.commit()
        conn.close()

    def _log_incident(self, incident: Incident):
        """Log incident to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO incidents
            (incident_id, component, severity, description, detected_at, resolved_at, auto_fixed, fix_attempts, resolution)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            incident.incident_id,
            incident.component,
            incident.severity.value,
            incident.description,
            incident.detected_at.isoformat(),
            incident.resolved_at.isoformat() if incident.resolved_at else None,
            1 if incident.auto_fixed else 0,
            incident.fix_attempts,
            incident.resolution
        ))

        conn.commit()
        conn.close()

    def is_healthy(self) -> bool:
        """Check if system is healthy"""
        return self.current_status == HealthStatus.HEALTHY

    def get_status(self) -> Dict[str, Any]:
        """Get current health status"""
        return {
            "overall_status": self.current_status.value,
            "last_checks": {
                comp: {
                    "status": check.status.value,
                    "message": check.message,
                    "timestamp": check.timestamp.isoformat()
                }
                for comp, check in self.last_checks.items()
            },
            "active_incidents": len(self.active_incidents),
            "monitoring": self.monitoring
        }

    def get_incident_history(self, limit: int = 10) -> List[Dict]:
        """Get recent incidents"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM incidents
            ORDER BY detected_at DESC
            LIMIT ?
        """, (limit,))

        incidents = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return incidents

    def check_and_fix_vllm(self) -> Dict[str, Any]:
        """
        On-demand vLLM health check and auto-fix

        Returns:
            {
                'healthy': bool,
                'error': Optional[str],
                'fixed': bool,
                'message': str
            }
        """
        # Run vLLM check
        check = self._check_vllm()

        if check.status == HealthStatus.HEALTHY:
            return {
                'healthy': True,
                'error': None,
                'fixed': False,
                'message': check.message
            }

        # Try to fix the issue
        fixed = self._fix_vllm()

        # Verify fix
        if fixed:
            verify_check = self._check_vllm()
            if verify_check.status == HealthStatus.HEALTHY:
                return {
                    'healthy': True,
                    'error': None,
                    'fixed': True,
                    'message': 'vLLM auto-fixed successfully'
                }

        return {
            'healthy': False,
            'error': check.message,
            'fixed': False,
            'message': f'Failed to fix vLLM: {check.message}. Run: ryx restart'
        }

    @property
    def overall_status(self) -> HealthStatus:
        """Get current overall health status"""
        return self.current_status
