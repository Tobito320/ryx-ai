# -*- coding: utf-8 -*-
"""
Service Registry - Verwaltung aller Ryx-Services
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Status eines Services"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    UNHEALTHY = "unhealthy"


@dataclass
class ServiceInfo:
    """Informationen über einen registrierten Service"""
    name: str
    capabilities: List[str] = field(default_factory=list)
    status: ServiceStatus = ServiceStatus.STOPPED
    version: str = "1.0.0"
    description: str = ""
    
    # Runtime info
    started_at: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    error: Optional[str] = None
    
    # Metrics
    request_count: int = 0
    error_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "capabilities": self.capabilities,
            "status": self.status.value,
            "version": self.version,
            "description": self.description,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "error": self.error,
            "request_count": self.request_count,
            "error_count": self.error_count
        }


class ServiceRegistry:
    """
    Registry für alle Ryx-Services
    
    Ermöglicht:
    - Service Discovery
    - Capability-based Lookup
    - Status Tracking
    
    Usage:
        registry = ServiceRegistry()
        
        # Register
        registry.register("brain", ServiceInfo(
            name="brain",
            capabilities=["chat", "code", "plan"]
        ))
        
        # Lookup by capability
        services = registry.find_by_capability("chat")
        
        # Get status
        info = registry.get("brain")
        print(info.status)
    """
    
    def __init__(self):
        self._services: Dict[str, ServiceInfo] = {}
        
    def register(self, name: str, info: ServiceInfo) -> bool:
        """Registriere einen Service"""
        if name in self._services:
            logger.warning(f"Service already registered: {name}")
            return False
            
        self._services[name] = info
        logger.debug(f"Service registered: {name}")
        return True
        
    def unregister(self, name: str) -> bool:
        """Entferne Service aus Registry"""
        if name not in self._services:
            return False
            
        del self._services[name]
        logger.debug(f"Service unregistered: {name}")
        return True
        
    def get(self, name: str) -> Optional[ServiceInfo]:
        """Service-Info abrufen"""
        return self._services.get(name)
        
    def update(self, name: str, **kwargs) -> bool:
        """Service-Info aktualisieren"""
        info = self._services.get(name)
        if not info:
            return False
            
        for key, value in kwargs.items():
            if hasattr(info, key):
                setattr(info, key, value)
                
        return True
        
    def list_services(self) -> List[str]:
        """Liste aller Service-Namen"""
        return list(self._services.keys())
        
    def find_by_capability(self, capability: str) -> List[ServiceInfo]:
        """Finde Services mit bestimmter Capability"""
        return [
            info for info in self._services.values()
            if capability in info.capabilities
        ]
        
    def find_by_status(self, status: ServiceStatus) -> List[ServiceInfo]:
        """Finde Services mit bestimmtem Status"""
        return [
            info for info in self._services.values()
            if info.status == status
        ]
        
    def get_running_services(self) -> List[str]:
        """Liste laufender Services"""
        return [
            name for name, info in self._services.items()
            if info.status == ServiceStatus.RUNNING
        ]
        
    def get_unhealthy_services(self) -> List[str]:
        """Liste ungesunder Services"""
        return [
            name for name, info in self._services.items()
            if info.status in (ServiceStatus.ERROR, ServiceStatus.UNHEALTHY)
        ]
        
    def to_dict(self) -> dict:
        """Alle Services als Dict"""
        return {
            name: info.to_dict()
            for name, info in self._services.items()
        }
