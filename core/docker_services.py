"""
Ryx AI - Docker Service Manager

Manages all Ryx Docker services:
- vLLM (GPU inference server)
- RyxHub (Web UI)
- RyxSurf (future - browsing agent)
- SearXNG (privacy search)

All services are Docker containers, started on demand.
"""

import os
import subprocess
import json
import time
import logging
import sys
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# VISUAL STARTUP DISPLAY
# ═══════════════════════════════════════════════════════════════

class ServiceStartupDisplay:
    """
    Visual display for service startup with live timer and status updates.
    
    Shows:
    ┌─────────────────────────────────────────────────────────────┐
    │ 🚀 Starting vLLM                                            │
    │                                                             │
    │   ◐ Loading model into GPU...              [00:42]         │
    │   ○ Initializing API server                                 │
    │   ○ Health check                                            │
    │                                                             │
    │   Expected: ~2-5 minutes for large models                   │
    └─────────────────────────────────────────────────────────────┘
    """
    
    # Spinner animation frames
    SPINNER = ['◐', '◓', '◑', '◒']
    
    # Expected startup times (in seconds) for user info
    EXPECTED_TIMES = {
        'vllm': (120, 300),      # 2-5 minutes
        'ryxhub': (10, 30),      # 10-30 seconds
        'searxng': (5, 15),      # 5-15 seconds
        'ryxsurf': (10, 30),     # 10-30 seconds
    }
    
    # Startup phases per service
    PHASES = {
        'vllm': [
            ('Pulling container image', 30),
            ('Loading model into GPU', 180),
            ('Initializing API server', 30),
            ('Health check', 10),
        ],
        'ryxhub': [
            ('Starting frontend', 10),
            ('Starting API server', 10),
            ('Health check', 5),
        ],
        'searxng': [
            ('Starting container', 5),
            ('Initializing search engine', 5),
            ('Health check', 3),
        ],
        'ryxsurf': [
            ('Starting browser service', 10),
            ('Initializing automation', 10),
            ('Health check', 5),
        ],
    }
    
    def __init__(self, service_name: str, quiet: bool = False):
        self.service_name = service_name.lower()
        self.quiet = quiet
        self.start_time = time.time()
        self.current_phase = 0
        self.phases = self.PHASES.get(self.service_name, [('Starting', 30)])
        self.spinner_idx = 0
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_status = ""
        
    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS"""
        mins = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{mins:02d}:{secs:02d}"
    
    def _get_expected_time_str(self) -> str:
        """Get expected time range as string"""
        times = self.EXPECTED_TIMES.get(self.service_name, (30, 120))
        min_time = times[0] // 60
        max_time = times[1] // 60
        if min_time == 0:
            return f"~{times[0]}-{times[1]}s"
        return f"~{min_time}-{max_time} min"
    
    def _clear_line(self):
        """Clear current terminal line"""
        if not self.quiet:
            sys.stdout.write('\r\033[K')
            sys.stdout.flush()
    
    def _render(self):
        """Render the current status display"""
        if self.quiet:
            return
            
        elapsed = time.time() - self.start_time
        elapsed_str = self._format_time(elapsed)
        
        # Get terminal width
        try:
            import shutil
            width = min(shutil.get_terminal_size().columns, 100)  # Cap at 100 for readability
        except:
            width = 80
        
        # Build output
        lines = []
        
        # Header
        service_display = self.service_name.upper()
        header_text = f"│ 🚀 Starting {service_display}"
        header_padding = width - len(header_text) - 1
        
        lines.append(f"╭{'─' * (width - 2)}╮")
        lines.append(f"{header_text}{' ' * header_padding}│")
        lines.append(f"│{' ' * (width - 2)}│")
        
        # Phases
        for i, (phase_name, _) in enumerate(self.phases):
            spinner = self.SPINNER[self.spinner_idx % 4] if i == self.current_phase else '○'
            if i < self.current_phase:
                spinner = '✓'
            
            if i == self.current_phase:
                status_line = f"   {spinner} {phase_name}"
                timer = f"[{elapsed_str}]"
                padding = width - len(status_line) - len(timer) - 4
                if padding < 1:
                    padding = 1
                full_line = f"│{status_line}{' ' * padding}{timer}  │"
            else:
                status_line = f"│   {spinner} {phase_name}"
                padding = width - len(status_line) - 1
                full_line = f"{status_line}{' ' * padding}│"
            
            lines.append(full_line)
        
        lines.append(f"│{' ' * (width - 2)}│")
        
        # Expected time info
        expected = f"   Expected: {self._get_expected_time_str()}"
        expected_padding = width - len(expected) - 3
        lines.append(f"│{expected}{' ' * expected_padding}│")
        lines.append(f"╰{'─' * (width - 2)}╯")
        
        # Clear previous output and print new
        if self._last_status:
            # Move cursor up and clear lines
            num_lines = self._last_status.count('\n') + 1
            sys.stdout.write(f'\033[{num_lines}A\033[J')
        
        output = '\n'.join(lines)
        sys.stdout.write(output + '\n')
        sys.stdout.flush()
        self._last_status = output
    
    def _animation_loop(self):
        """Background thread for spinner animation"""
        while not self._stop_event.is_set():
            self._render()
            self.spinner_idx += 1
            self._stop_event.wait(0.2)  # 200ms update for smoother display
    
    def start(self):
        """Start the visual display"""
        if self.quiet:
            return
            
        self.start_time = time.time()
        self.current_phase = 0
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._animation_loop, daemon=True)
        self._thread.start()
    
    def advance_phase(self, phase_name: Optional[str] = None):
        """Advance to next phase or set specific phase"""
        if phase_name:
            # Find phase by name
            for i, (name, _) in enumerate(self.phases):
                if phase_name.lower() in name.lower():
                    self.current_phase = i
                    break
        else:
            self.current_phase = min(self.current_phase + 1, len(self.phases) - 1)
        
        if not self.quiet:
            self._render()
    
    def set_status(self, status: str):
        """Update status message"""
        if self.current_phase < len(self.phases):
            # Update phase name temporarily
            old_phase = self.phases[self.current_phase]
            self.phases[self.current_phase] = (status, old_phase[1])
            self._render()
    
    def finish(self, success: bool = True, message: str = ""):
        """Complete the display"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=0.5)
        
        if self.quiet:
            return
            
        elapsed = time.time() - self.start_time
        elapsed_str = self._format_time(elapsed)
        
        # Get terminal width
        try:
            import shutil
            width = shutil.get_terminal_size().columns
        except:
            width = 80
        
        # Clear previous output
        if self._last_status:
            num_lines = self._last_status.count('\n') + 1
            sys.stdout.write(f'\033[{num_lines}A')
            for _ in range(num_lines):
                sys.stdout.write('\033[K\n')
            sys.stdout.write(f'\033[{num_lines}A')
        
        # Final status
        if success:
            icon = '✅'
            status = f'Started in {elapsed_str}'
            color = '\033[32m'  # Green
        else:
            icon = '❌'
            status = f'Failed after {elapsed_str}'
            color = '\033[31m'  # Red
        
        service_display = self.service_name.upper()
        print(f"{color}{icon} {service_display} - {status}\033[0m")
        if message:
            print(f"   {message}")
        print()


def with_startup_display(service_name: str, quiet: bool = False):
    """
    Decorator/context manager for visual startup display.
    
    Usage:
        with with_startup_display('vllm') as display:
            display.advance_phase('Loading model')
            # ... do work ...
            display.advance_phase('Health check')
    """
    class DisplayContext:
        def __init__(self):
            self.display = ServiceStartupDisplay(service_name, quiet=quiet)
        
        def __enter__(self):
            self.display.start()
            return self.display
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            success = exc_type is None
            message = str(exc_val) if exc_val else ""
            self.display.finish(success=success, message=message)
            return False
    
    return DisplayContext()


class ServiceStatus(Enum):
    """Service status"""
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    ERROR = "error"
    NOT_FOUND = "not_found"


@dataclass
class ServiceConfig:
    """Configuration for a Docker service"""
    name: str
    container_name: str
    compose_file: Optional[str] = None
    image: Optional[str] = None
    ports: List[str] = field(default_factory=list)
    health_url: Optional[str] = None
    health_timeout: int = 30
    description: str = ""
    gpu_required: bool = False
    
    def __post_init__(self):
        if not self.compose_file and not self.image:
            raise ValueError(f"Service {self.name} needs either compose_file or image")


# ═══════════════════════════════════════════════════════════════
# SERVICE DEFINITIONS
# ═══════════════════════════════════════════════════════════════

SERVICES: Dict[str, ServiceConfig] = {
    "vllm": ServiceConfig(
        name="vllm",
        container_name="ryx-vllm",
        compose_file="docker/vllm/docker-compose.yml",
        ports=["8001:8001"],
        health_url="http://localhost:8001/health",
        health_timeout=120,  # vLLM takes time to load models
        description="GPU inference server (vLLM + ROCm)",
        gpu_required=True
    ),
    
    "ryxhub": ServiceConfig(
        name="ryxhub",
        container_name="ryx-hub",
        compose_file="docker/ryxhub/docker-compose.yml",
        ports=["5173:5173", "8420:8420"],
        health_url="http://localhost:5173",
        health_timeout=30,
        description="Ryx Web UI Dashboard (Frontend: 5173, API: 8420)"
    ),
    
    "searxng": ServiceConfig(
        name="searxng",
        container_name="ryx-searxng",
        image="searxng/searxng:latest",
        ports=["8888:8080"],
        health_url="http://localhost:8888",
        health_timeout=15,
        description="Privacy-first search engine"
    ),
    
    # Future
    "ryxsurf": ServiceConfig(
        name="ryxsurf",
        container_name="ryx-surf",
        compose_file="docker/ryxsurf/docker-compose.yml",
        ports=["9000:9000"],
        health_url="http://localhost:9000/health",
        health_timeout=30,
        description="Autonomous browsing agent"
    ),
}


class DockerServiceManager:
    """
    Manages Docker services for Ryx.
    
    Usage:
        manager = DockerServiceManager()
        manager.start("vllm")
        manager.start("ryxhub")
        manager.status()
        manager.stop("ryxhub")
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        if project_root:
            self.project_root = Path(project_root)
        else:
            # Auto-detect
            self.project_root = Path(__file__).parent.parent
        
        self.runtime_dir = self.project_root / "data" / "runtime"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        
        # Check Docker availability
        self._docker_available = self._check_docker()
    
    def _check_docker(self) -> bool:
        """Check if Docker is available"""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _get_container_status(self, container_name: str) -> ServiceStatus:
        """Get status of a Docker container"""
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Status}}", container_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return ServiceStatus.NOT_FOUND
            
            status = result.stdout.strip()
            if status == "running":
                return ServiceStatus.RUNNING
            elif status in ["created", "restarting"]:
                return ServiceStatus.STARTING
            else:
                return ServiceStatus.STOPPED
                
        except Exception as e:
            logger.error(f"Error checking container {container_name}: {e}")
            return ServiceStatus.ERROR
    
    def _wait_for_health(self, service: ServiceConfig, display: Optional[ServiceStartupDisplay] = None) -> bool:
        """Wait for service to become healthy with visual feedback"""
        if not service.health_url:
            return True
        
        import requests
        
        if display:
            display.advance_phase('Health check')
        
        start_time = time.time()
        check_count = 0
        while time.time() - start_time < service.health_timeout:
            try:
                resp = requests.get(service.health_url, timeout=2)
                if resp.status_code < 500:
                    return True
            except Exception:
                pass
            
            # Update status periodically
            check_count += 1
            if display and check_count % 5 == 0:
                elapsed = int(time.time() - start_time)
                display.set_status(f"Health check ({elapsed}s / {service.health_timeout}s)")
            
            time.sleep(1)
        
        return False
    
    def start(self, service_name: str, wait: bool = True, quiet: bool = False) -> Dict[str, Any]:
        """
        Start a Docker service with visual feedback.
        
        Args:
            service_name: Name of the service (vllm, ryxhub, searxng, etc.)
            wait: Wait for service to become healthy
            quiet: Suppress visual output
            
        Returns:
            Dict with success, status, urls, error, elapsed_time
        """
        start_time = time.time()
        
        if not self._docker_available:
            return {
                "success": False,
                "error": "Docker is not available. Please install and start Docker."
            }
        
        service_name = service_name.lower()
        if service_name not in SERVICES:
            available = ", ".join(SERVICES.keys())
            return {
                "success": False,
                "error": f"Unknown service: {service_name}. Available: {available}"
            }
        
        service = SERVICES[service_name]
        
        # Check if already running
        current_status = self._get_container_status(service.container_name)
        if current_status == ServiceStatus.RUNNING:
            if not quiet:
                print(f"✅ {service.name.upper()} - Already running")
            return {
                "success": True,
                "status": "already_running",
                "message": f"{service.name} is already running",
                "urls": self._get_service_urls(service),
                "elapsed_time": 0
            }
        
        # Create visual display
        display = ServiceStartupDisplay(service_name, quiet=quiet)
        display.start()
        
        try:
            if service.compose_file:
                # Use docker-compose
                compose_path = self.project_root / service.compose_file
                
                if not compose_path.exists():
                    display.finish(success=False, message=f"Compose file not found: {compose_path}")
                    return {
                        "success": False,
                        "error": f"Compose file not found: {compose_path}"
                    }
                
                display.advance_phase('Pulling')
                
                result = subprocess.run(
                    ["docker", "compose", "-f", str(compose_path), "up", "-d"],
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 min for image pulls
                )
                
            else:
                # Use docker run directly
                cmd = [
                    "docker", "run", "-d",
                    "--name", service.container_name,
                ]
                
                # Add GPU support if needed
                if service.gpu_required:
                    cmd.extend([
                        "--device", "/dev/kfd",
                        "--device", "/dev/dri",
                        "--group-add", "video",
                        "--group-add", "render",
                        "--security-opt", "seccomp=unconfined",
                    ])
                
                # Add ports
                for port in service.ports:
                    cmd.extend(["-p", port])
                
                cmd.append(service.image)
                
                display.advance_phase('Starting container')
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600
                )
            
            if result.returncode != 0:
                display.finish(success=False, message=result.stderr[:100] if result.stderr else "Unknown error")
                return {
                    "success": False,
                    "error": f"Failed to start {service.name}: {result.stderr}",
                    "elapsed_time": time.time() - start_time
                }
            
            # Advance to loading phase (for vLLM this is the longest phase)
            if service_name == 'vllm':
                display.advance_phase('Loading model')
            else:
                display.advance_phase('Initializing')
            
            # Wait for health check
            if wait:
                if self._wait_for_health(service, display):
                    elapsed = time.time() - start_time
                    urls = self._get_service_urls(service)
                    url_str = urls[0] if urls else ""
                    display.finish(success=True, message=url_str)
                    return {
                        "success": True,
                        "status": "running",
                        "message": f"{service.name} started successfully",
                        "urls": urls,
                        "elapsed_time": elapsed
                    }
                else:
                    elapsed = time.time() - start_time
                    display.finish(success=True, message="Health check timeout - service may still be starting")
                    return {
                        "success": True,
                        "status": "starting",
                        "message": f"{service.name} started but health check pending",
                        "urls": self._get_service_urls(service),
                        "elapsed_time": elapsed
                    }
            
            elapsed = time.time() - start_time
            display.finish(success=True, message=f"Started (not waiting for health)")
            return {
                "success": True,
                "status": "starting",
                "message": f"{service.name} starting...",
                "urls": self._get_service_urls(service),
                "elapsed_time": elapsed
            }
            
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            display.finish(success=False, message="Process timeout")
            return {
                "success": False,
                "error": f"Timeout starting {service.name}",
                "elapsed_time": elapsed
            }
        except Exception as e:
            elapsed = time.time() - start_time
            display.finish(success=False, message=str(e)[:80])
            return {
                "success": False,
                "error": f"Error starting {service.name}: {e}",
                "elapsed_time": elapsed
            }
    
    def stop(self, service_name: str) -> Dict[str, Any]:
        """Stop a Docker service"""
        if not self._docker_available:
            return {"success": False, "error": "Docker is not available"}
        
        service_name = service_name.lower()
        if service_name not in SERVICES:
            return {"success": False, "error": f"Unknown service: {service_name}"}
        
        service = SERVICES[service_name]
        
        try:
            if service.compose_file:
                compose_path = self.project_root / service.compose_file
                if compose_path.exists():
                    subprocess.run(
                        ["docker", "compose", "-f", str(compose_path), "down"],
                        capture_output=True,
                        timeout=30
                    )
            else:
                subprocess.run(
                    ["docker", "stop", service.container_name],
                    capture_output=True,
                    timeout=30
                )
                subprocess.run(
                    ["docker", "rm", service.container_name],
                    capture_output=True,
                    timeout=10
                )
            
            return {
                "success": True,
                "message": f"{service.name} stopped"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error stopping {service.name}: {e}"
            }
    
    def restart(self, service_name: str) -> Dict[str, Any]:
        """Restart a Docker service"""
        self.stop(service_name)
        time.sleep(1)
        return self.start(service_name)
    
    def status(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get status of one or all services.
        
        Args:
            service_name: Specific service, or None for all
            
        Returns:
            Dict with service statuses
        """
        if service_name:
            services = {service_name: SERVICES.get(service_name)}
            if not services[service_name]:
                return {"success": False, "error": f"Unknown service: {service_name}"}
        else:
            services = SERVICES
        
        result = {}
        for name, service in services.items():
            if service is None:
                continue
                
            status = self._get_container_status(service.container_name)
            result[name] = {
                "status": status.value,
                "description": service.description,
                "urls": self._get_service_urls(service) if status == ServiceStatus.RUNNING else [],
                "gpu_required": service.gpu_required
            }
        
        return {"success": True, "services": result}
    
    def _get_service_urls(self, service: ServiceConfig) -> List[str]:
        """Get URLs for a running service"""
        urls = []
        for port_mapping in service.ports:
            host_port = port_mapping.split(":")[0]
            urls.append(f"http://localhost:{host_port}")
        return urls
    
    def logs(self, service_name: str, lines: int = 50) -> Dict[str, Any]:
        """Get logs from a service"""
        service = SERVICES.get(service_name.lower())
        if not service:
            return {"success": False, "error": f"Unknown service: {service_name}"}
        
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", str(lines), service.container_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return {
                "success": True,
                "logs": result.stdout + result.stderr
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# Convenience functions
_manager: Optional[DockerServiceManager] = None


def get_docker_manager() -> DockerServiceManager:
    """Get singleton Docker service manager"""
    global _manager
    if _manager is None:
        _manager = DockerServiceManager()
    return _manager


def start_service(name: str, quiet: bool = False) -> Dict[str, Any]:
    """Start a Docker service by name with visual feedback"""
    return get_docker_manager().start(name, quiet=quiet)


def stop_service(name: str) -> Dict[str, Any]:
    """Stop a Docker service by name"""
    return get_docker_manager().stop(name)


def service_status(name: Optional[str] = None) -> Dict[str, Any]:
    """Get status of services"""
    return get_docker_manager().status(name)
