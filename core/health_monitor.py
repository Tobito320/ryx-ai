"""
Ryx AI - Health Monitor
Continuously monitors system health and automatically repairs issues
"""

import json
import time
import logging
import subprocess
import threading
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Overall system health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class IssueType(Enum):
    """Types of issues the system can detect and fix"""
    OLLAMA_DOWN = "ollama_down"
    OLLAMA_404 = "ollama_404"
    MODEL_NOT_FOUND = "model_not_found"
    DATABASE_CORRUPT = "database_corrupt"
    CONFIG_INVALID = "config_invalid"
    HIGH_MEMORY = "high_memory"
    DISK_FULL = "disk_full"


@dataclass
class HealthCheck:
    """Result of a health check"""
    component: str
    status: HealthStatus
    last_check: float
    message: str
    auto_repair_available: bool = False


@dataclass
class IncidentLog:
    """Log entry for a system incident"""
    issue_type: IssueType
    description: str
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    auto_fixed: bool = False
    fix_action: Optional[str] = None
    resolution: Optional[str] = None


class HealthMonitor:
    """
    Monitors system health and automatically fixes common issues:
    - Ollama service management
    - Database integrity
    - Configuration validation
    - Resource monitoring
    - Self-repair mechanisms
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.home() / "ryx-ai"
        self.ollama_url = "http://localhost:11434"
        
        # State
        self.checks: Dict[str, HealthCheck] = {}
        self.incidents: List[IncidentLog] = []
        self.overall_status = HealthStatus.UNKNOWN
        
        # Monitoring thread
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._monitor_interval = 30  # seconds
        
        # Fix callbacks
        self._fix_handlers: Dict[IssueType, Callable] = {
            IssueType.OLLAMA_DOWN: self._fix_ollama_down,
            IssueType.MODEL_NOT_FOUND: self._fix_model_not_found,
            IssueType.DATABASE_CORRUPT: self._fix_database_corrupt,
            IssueType.CONFIG_INVALID: self._fix_config_invalid,
        }
        
        # Load incident history
        self._load_incidents()
    
    def _load_incidents(self):
        """Load incident history from disk"""
        incident_file = self.project_root / "data" / "incidents.json"
        try:
            if incident_file.exists():
                with open(incident_file, 'r') as f:
                    data = json.load(f)
                    # Convert back to IncidentLog objects
                    for item in data[-100:]:  # Keep last 100
                        self.incidents.append(IncidentLog(
                            issue_type=IssueType(item["issue_type"]),
                            description=item["description"],
                            detected_at=datetime.fromisoformat(item["detected_at"]),
                            resolved_at=datetime.fromisoformat(item["resolved_at"]) if item.get("resolved_at") else None,
                            auto_fixed=item.get("auto_fixed", False),
                            fix_action=item.get("fix_action"),
                            resolution=item.get("resolution")
                        ))
        except Exception as e:
            logger.warning(f"Failed to load incident history: {e}")
    
    def _save_incidents(self):
        """Save incident history to disk"""
        incident_file = self.project_root / "data" / "incidents.json"
        incident_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            data = []
            for incident in self.incidents[-100:]:  # Keep last 100
                data.append({
                    "issue_type": incident.issue_type.value,
                    "description": incident.description,
                    "detected_at": incident.detected_at.isoformat(),
                    "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
                    "auto_fixed": incident.auto_fixed,
                    "fix_action": incident.fix_action,
                    "resolution": incident.resolution
                })
            
            with open(incident_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save incident history: {e}")
    
    def start_monitoring(self):
        """Start background health monitoring"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            logger.warning("Monitor already running")
            return
        
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Health monitoring started")
    
    def stop_monitoring(self):
        """Stop background health monitoring"""
        if self._monitor_thread:
            self._stop_event.set()
            self._monitor_thread.join(timeout=5)
            logger.info("Health monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while not self._stop_event.is_set():
            try:
                self.run_health_checks()
            except Exception as e:
                logger.error(f"Error in health check: {e}")
            
            self._stop_event.wait(self._monitor_interval)
    
    def run_health_checks(self) -> Dict[str, HealthCheck]:
        """Run all health checks"""
        self.checks = {}
        
        # Check Ollama service
        self.checks['ollama'] = self._check_ollama()
        
        # Check database
        self.checks['database'] = self._check_database()
        
        # Check configuration
        self.checks['config'] = self._check_config()
        
        # Check disk space
        self.checks['disk'] = self._check_disk_space()
        
        # Check memory
        self.checks['memory'] = self._check_memory()
        
        # Update overall status
        self._update_overall_status()
        
        return self.checks
    
    def _check_ollama(self) -> HealthCheck:
        """Check if Ollama service is running and responsive"""
        try:
            import requests
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            
            if response.status_code == 200:
                return HealthCheck(
                    component="ollama",
                    status=HealthStatus.HEALTHY,
                    last_check=time.time(),
                    message="Ollama service is running normally"
                )
            elif response.status_code == 404:
                # Auto-fix 404 issues
                self._report_and_fix(IssueType.OLLAMA_404, "Ollama returned 404")
                return HealthCheck(
                    component="ollama",
                    status=HealthStatus.DEGRADED,
                    last_check=time.time(),
                    message="Ollama returned 404, attempting auto-repair",
                    auto_repair_available=True
                )
            else:
                return HealthCheck(
                    component="ollama",
                    status=HealthStatus.DEGRADED,
                    last_check=time.time(),
                    message=f"Ollama returned unexpected status: {response.status_code}"
                )
        except requests.exceptions.ConnectionError:
            # Ollama not running
            self._report_and_fix(IssueType.OLLAMA_DOWN, "Ollama service not responding")
            return HealthCheck(
                component="ollama",
                status=HealthStatus.CRITICAL,
                last_check=time.time(),
                message="Ollama service is down, attempting restart",
                auto_repair_available=True
            )
        except Exception as e:
            return HealthCheck(
                component="ollama",
                status=HealthStatus.CRITICAL,
                last_check=time.time(),
                message=f"Failed to check Ollama: {e}"
            )
    
    def _check_database(self) -> HealthCheck:
        """Check database integrity"""
        try:
            db_path = self.project_root / "data" / "rag_knowledge.db"
            
            if not db_path.exists():
                return HealthCheck(
                    component="database",
                    status=HealthStatus.DEGRADED,
                    last_check=time.time(),
                    message="Database file missing, will be created on next use"
                )
            
            # Try to connect and run integrity check
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()
            
            if result[0] == "ok":
                return HealthCheck(
                    component="database",
                    status=HealthStatus.HEALTHY,
                    last_check=time.time(),
                    message="Database integrity verified"
                )
            else:
                self._report_and_fix(IssueType.DATABASE_CORRUPT, f"Database integrity check failed: {result[0]}")
                return HealthCheck(
                    component="database",
                    status=HealthStatus.CRITICAL,
                    last_check=time.time(),
                    message=f"Database corrupt: {result[0]}",
                    auto_repair_available=True
                )
        except Exception as e:
            return HealthCheck(
                component="database",
                status=HealthStatus.CRITICAL,
                last_check=time.time(),
                message=f"Database check failed: {e}"
            )
    
    def _check_config(self) -> HealthCheck:
        """Check configuration files"""
        try:
            config_dir = self.project_root / "configs"
            required_configs = ["settings.json", "models.json", "permissions.json"]
            
            missing = []
            invalid = []
            
            for config_file in required_configs:
                path = config_dir / config_file
                if not path.exists():
                    missing.append(config_file)
                else:
                    try:
                        with open(path, 'r') as f:
                            json.load(f)
                    except json.JSONDecodeError:
                        invalid.append(config_file)
            
            if missing or invalid:
                msg = []
                if missing:
                    msg.append(f"Missing: {', '.join(missing)}")
                if invalid:
                    msg.append(f"Invalid: {', '.join(invalid)}")
                
                self._report_and_fix(IssueType.CONFIG_INVALID, "; ".join(msg))
                return HealthCheck(
                    component="config",
                    status=HealthStatus.DEGRADED,
                    last_check=time.time(),
                    message="; ".join(msg),
                    auto_repair_available=True
                )
            
            return HealthCheck(
                component="config",
                status=HealthStatus.HEALTHY,
                last_check=time.time(),
                message="All configuration files valid"
            )
        except Exception as e:
            return HealthCheck(
                component="config",
                status=HealthStatus.DEGRADED,
                last_check=time.time(),
                message=f"Config check failed: {e}"
            )
    
    def _check_disk_space(self) -> HealthCheck:
        """Check available disk space"""
        try:
            result = subprocess.run(
                ['df', '-h', str(self.project_root)],
                capture_output=True,
                text=True
            )
            
            # Parse df output
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                fields = lines[1].split()
                usage_pct = int(fields[4].rstrip('%'))
                
                if usage_pct >= 95:
                    return HealthCheck(
                        component="disk",
                        status=HealthStatus.CRITICAL,
                        last_check=time.time(),
                        message=f"Disk usage critical: {usage_pct}%"
                    )
                elif usage_pct >= 85:
                    return HealthCheck(
                        component="disk",
                        status=HealthStatus.DEGRADED,
                        last_check=time.time(),
                        message=f"Disk usage high: {usage_pct}%"
                    )
                else:
                    return HealthCheck(
                        component="disk",
                        status=HealthStatus.HEALTHY,
                        last_check=time.time(),
                        message=f"Disk usage: {usage_pct}%"
                    )
            
            return HealthCheck(
                component="disk",
                status=HealthStatus.UNKNOWN,
                last_check=time.time(),
                message="Could not determine disk usage"
            )
        except Exception as e:
            return HealthCheck(
                component="disk",
                status=HealthStatus.UNKNOWN,
                last_check=time.time(),
                message=f"Disk check failed: {e}"
            )
    
    def _check_memory(self) -> HealthCheck:
        """Check system memory usage"""
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
            
            mem_total = int([line for line in meminfo.split('\n') if 'MemTotal' in line][0].split()[1])
            mem_available = int([line for line in meminfo.split('\n') if 'MemAvailable' in line][0].split()[1])
            
            usage_pct = int((1 - mem_available / mem_total) * 100)
            
            if usage_pct >= 95:
                return HealthCheck(
                    component="memory",
                    status=HealthStatus.CRITICAL,
                    last_check=time.time(),
                    message=f"Memory usage critical: {usage_pct}%"
                )
            elif usage_pct >= 85:
                return HealthCheck(
                    component="memory",
                    status=HealthStatus.DEGRADED,
                    last_check=time.time(),
                    message=f"Memory usage high: {usage_pct}%"
                )
            else:
                return HealthCheck(
                    component="memory",
                    status=HealthStatus.HEALTHY,
                    last_check=time.time(),
                    message=f"Memory usage: {usage_pct}%"
                )
        except Exception as e:
            return HealthCheck(
                component="memory",
                status=HealthStatus.UNKNOWN,
                last_check=time.time(),
                message=f"Memory check failed: {e}"
            )
    
    def _update_overall_status(self):
        """Update overall system status based on component checks"""
        if any(check.status == HealthStatus.CRITICAL for check in self.checks.values()):
            self.overall_status = HealthStatus.CRITICAL
        elif any(check.status == HealthStatus.DEGRADED for check in self.checks.values()):
            self.overall_status = HealthStatus.DEGRADED
        elif all(check.status == HealthStatus.HEALTHY for check in self.checks.values()):
            self.overall_status = HealthStatus.HEALTHY
        else:
            self.overall_status = HealthStatus.UNKNOWN
    
    def _report_and_fix(self, issue_type: IssueType, description: str):
        """Report an issue and attempt auto-fix"""
        # Create incident
        incident = IncidentLog(
            issue_type=issue_type,
            description=description,
            detected_at=datetime.now()
        )
        
        logger.warning(f"Issue detected: {issue_type.value} - {description}")
        
        # Attempt auto-fix
        if issue_type in self._fix_handlers:
            try:
                fix_result = self._fix_handlers[issue_type]()
                incident.auto_fixed = fix_result['success']
                incident.fix_action = fix_result['action']
                incident.resolution = fix_result['message']
                incident.resolved_at = datetime.now()
                
                if fix_result['success']:
                    logger.info(f"Auto-fixed: {issue_type.value} - {fix_result['message']}")
                else:
                    logger.error(f"Auto-fix failed: {issue_type.value} - {fix_result['message']}")
            except Exception as e:
                logger.error(f"Auto-fix exception: {e}")
                incident.resolution = f"Fix failed with exception: {e}"
        
        self.incidents.append(incident)
        self._save_incidents()
    
    def _fix_ollama_down(self) -> Dict:
        """Attempt to restart Ollama service"""
        try:
            # Try systemctl restart
            result = subprocess.run(
                ['systemctl', '--user', 'restart', 'ollama'],
                capture_output=True,
                timeout=10
            )
            
            if result.returncode == 0:
                time.sleep(2)  # Wait for service to start
                return {
                    'success': True,
                    'action': 'systemctl restart ollama',
                    'message': 'Ollama service restarted successfully'
                }
            
            # Try starting ollama directly
            subprocess.Popen(['ollama', 'serve'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
            
            return {
                'success': True,
                'action': 'ollama serve',
                'message': 'Started Ollama service'
            }
        except Exception as e:
            return {
                'success': False,
                'action': 'restart attempt',
                'message': f'Failed to restart: {e}'
            }
    
    def _fix_model_not_found(self) -> Dict:
        """Attempt to download missing model"""
        return {
            'success': False,
            'action': 'download model',
            'message': 'Model download requires user confirmation'
        }
    
    def _fix_database_corrupt(self) -> Dict:
        """Attempt to repair corrupt database"""
        try:
            db_path = self.project_root / "data" / "rag_knowledge.db"
            backup_path = db_path.with_suffix('.db.backup')
            
            # Backup current database
            if db_path.exists():
                import shutil
                shutil.copy2(db_path, backup_path)
            
            # Try to recover
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Dump and restore
            with open(backup_path.with_suffix('.sql'), 'w') as f:
                for line in conn.iterdump():
                    f.write(f"{line}\n")
            
            conn.close()
            
            # Create new database
            db_path.unlink()
            conn = sqlite3.connect(str(db_path))
            
            with open(backup_path.with_suffix('.sql'), 'r') as f:
                conn.executescript(f.read())
            
            conn.close()
            
            return {
                'success': True,
                'action': 'database rebuild',
                'message': 'Database rebuilt from backup'
            }
        except Exception as e:
            return {
                'success': False,
                'action': 'database repair',
                'message': f'Repair failed: {e}'
            }
    
    def _fix_config_invalid(self) -> Dict:
        """Attempt to restore default configuration"""
        try:
            # This would restore default configs
            # Implementation depends on where defaults are stored
            return {
                'success': False,
                'action': 'config restore',
                'message': 'Config restore requires manual intervention'
            }
        except Exception as e:
            return {
                'success': False,
                'action': 'config restore',
                'message': f'Restore failed: {e}'
            }
    
    def get_status(self) -> Dict:
        """Get current health status"""
        return {
            'overall_status': self.overall_status.value,
            'checks': {
                name: {
                    'status': check.status.value,
                    'message': check.message,
                    'last_check_ago': time.time() - check.last_check
                }
                for name, check in self.checks.items()
            },
            'recent_incidents': [
                {
                    'type': inc.issue_type.value,
                    'description': inc.description,
                    'detected_at': inc.detected_at.isoformat(),
                    'auto_fixed': inc.auto_fixed,
                    'resolution': inc.resolution
                }
                for inc in self.incidents[-10:]
            ]
        }
