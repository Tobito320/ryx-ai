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
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


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
        ports=["5173:5173", "8000:8000"],
        health_url="http://localhost:5173",
        health_timeout=30,
        description="Ryx Web UI Dashboard"
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
    
    def _wait_for_health(self, service: ServiceConfig) -> bool:
        """Wait for service to become healthy"""
        if not service.health_url:
            return True
        
        import requests
        
        start_time = time.time()
        while time.time() - start_time < service.health_timeout:
            try:
                resp = requests.get(service.health_url, timeout=2)
                if resp.status_code < 500:
                    return True
            except Exception:
                pass
            time.sleep(1)
        
        return False
    
    def start(self, service_name: str, wait: bool = True) -> Dict[str, Any]:
        """
        Start a Docker service.
        
        Args:
            service_name: Name of the service (vllm, ryxhub, searxng, etc.)
            wait: Wait for service to become healthy
            
        Returns:
            Dict with success, status, urls, error
        """
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
            return {
                "success": True,
                "status": "already_running",
                "message": f"{service.name} is already running",
                "urls": self._get_service_urls(service)
            }
        
        try:
            if service.compose_file:
                # Use docker-compose
                compose_path = self.project_root / service.compose_file
                
                if not compose_path.exists():
                    return {
                        "success": False,
                        "error": f"Compose file not found: {compose_path}"
                    }
                
                result = subprocess.run(
                    ["docker", "compose", "-f", str(compose_path), "up", "-d"],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 min for image pulls
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
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Failed to start {service.name}: {result.stderr}"
                }
            
            # Wait for health check
            if wait:
                logger.info(f"Waiting for {service.name} to become healthy...")
                if self._wait_for_health(service):
                    return {
                        "success": True,
                        "status": "running",
                        "message": f"{service.name} started successfully",
                        "urls": self._get_service_urls(service)
                    }
                else:
                    return {
                        "success": True,
                        "status": "starting",
                        "message": f"{service.name} started but health check pending",
                        "urls": self._get_service_urls(service)
                    }
            
            return {
                "success": True,
                "status": "starting",
                "message": f"{service.name} starting...",
                "urls": self._get_service_urls(service)
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Timeout starting {service.name}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error starting {service.name}: {e}"
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


def start_service(name: str) -> Dict[str, Any]:
    """Start a Docker service by name"""
    return get_docker_manager().start(name)


def stop_service(name: str) -> Dict[str, Any]:
    """Stop a Docker service by name"""
    return get_docker_manager().stop(name)


def service_status(name: Optional[str] = None) -> Dict[str, Any]:
    """Get status of services"""
    return get_docker_manager().status(name)
