# -*- coding: utf-8 -*-
"""
RyxHub Core - Zentraler Orchestrator für alle Ryx-Services
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, List
from pathlib import Path
import logging
import json

from .service_registry import ServiceRegistry, ServiceInfo, ServiceStatus
from .event_bus import EventBus, Event, EventType

logger = logging.getLogger(__name__)


@dataclass
class HubConfig:
    """Konfiguration für RyxHub"""
    # API
    host: str = "127.0.0.1"
    port: int = 8420  # Ryx default port
    enable_api: bool = True
    enable_websocket: bool = True
    
    # Services
    auto_start_services: bool = True
    service_timeout: float = 30.0
    health_check_interval: float = 60.0
    
    # Persistence
    state_dir: Path = field(default_factory=lambda: Path.home() / ".ryx" / "hub")
    persist_state: bool = True
    
    # Security
    require_auth: bool = False
    api_key: Optional[str] = None
    
    # Features
    enable_voice: bool = False
    enable_hardware: bool = False
    enable_agents: bool = True


class RyxHub:
    """
    RyxHub - Zentraler Orchestrator für das Ryx Ökosystem
    
    RyxHub verwaltet:
    - Service Lifecycle (Start, Stop, Restart)
    - Inter-Service-Kommunikation via EventBus
    - Health Monitoring
    - API für externe Zugriffe
    
    Architecture:
    ```
    ┌─────────────────────────────────────────────────┐
    │                    RyxHub                        │
    │  ┌────────────┐  ┌────────────┐  ┌───────────┐  │
    │  │  EventBus  │  │  Registry  │  │    API    │  │
    │  └─────┬──────┘  └─────┬──────┘  └─────┬─────┘  │
    │        │               │               │        │
    └────────┼───────────────┼───────────────┼────────┘
             │               │               │
    ┌────────▼───────────────▼───────────────▼────────┐
    │                    Services                      │
    │  ┌─────────┐  ┌─────────┐  ┌─────────┐         │
    │  │  Brain  │  │  Voice  │  │Hardware │  ...    │
    │  └─────────┘  └─────────┘  └─────────┘         │
    └─────────────────────────────────────────────────┘
    ```
    
    Usage:
        hub = RyxHub()
        await hub.start()
        
        # Register a service
        hub.register_service("brain", brain_instance)
        
        # Send command to service
        result = await hub.call("brain", "process", {"text": "Hello"})
        
        # Subscribe to events
        hub.on("brain.response", handle_response)
        
        await hub.stop()
    """
    
    def __init__(self, config: Optional[HubConfig] = None):
        self.config = config or HubConfig()
        
        # Core components
        self.registry = ServiceRegistry()
        self.event_bus = EventBus()
        
        # State
        self._running = False
        self._api_server = None
        self._health_task: Optional[asyncio.Task] = None
        
        # Built-in services
        self._services: Dict[str, Any] = {}
        
    async def start(self) -> bool:
        """Starte RyxHub"""
        if self._running:
            return True
            
        logger.info("Starting RyxHub...")
        
        # State directory
        self.config.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Load persisted state
        if self.config.persist_state:
            await self._load_state()
            
        # Start event bus
        await self.event_bus.start()
        
        # Start built-in services
        if self.config.enable_voice:
            await self._init_voice_service()
            
        if self.config.enable_hardware:
            await self._init_hardware_service()
            
        # Start API if enabled
        if self.config.enable_api:
            await self._start_api()
            
        # Start health monitor
        self._health_task = asyncio.create_task(self._health_monitor_loop())
        
        self._running = True
        
        # Emit startup event
        await self.event_bus.emit(Event(
            type=EventType.SYSTEM,
            source="hub",
            data={"action": "started"}
        ))
        
        logger.info(f"RyxHub started on {self.config.host}:{self.config.port}")
        return True
        
    async def stop(self):
        """Stoppe RyxHub"""
        if not self._running:
            return
            
        logger.info("Stopping RyxHub...")
        
        # Emit shutdown event
        await self.event_bus.emit(Event(
            type=EventType.SYSTEM,
            source="hub",
            data={"action": "stopping"}
        ))
        
        # Stop health monitor
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
                
        # Stop all services
        for name in list(self.registry.list_services()):
            await self.stop_service(name)
            
        # Stop API
        if self._api_server:
            await self._stop_api()
            
        # Stop event bus
        await self.event_bus.stop()
        
        # Persist state
        if self.config.persist_state:
            await self._save_state()
            
        self._running = False
        logger.info("RyxHub stopped")
        
    async def register_service(
        self,
        name: str,
        service: Any,
        capabilities: Optional[List[str]] = None
    ) -> bool:
        """
        Registriere einen Service bei RyxHub
        
        Args:
            name: Eindeutiger Service-Name
            service: Service-Instanz (muss start/stop haben)
            capabilities: Liste von Fähigkeiten
            
        Returns:
            True wenn erfolgreich
        """
        info = ServiceInfo(
            name=name,
            capabilities=capabilities or [],
            status=ServiceStatus.STOPPED
        )
        
        self.registry.register(name, info)
        self._services[name] = service
        
        # Auto-start if configured
        if self.config.auto_start_services:
            await self.start_service(name)
            
        await self.event_bus.emit(Event(
            type=EventType.SERVICE,
            source="hub",
            data={"action": "registered", "service": name}
        ))
        
        logger.info(f"Service registered: {name}")
        return True
        
    async def start_service(self, name: str) -> bool:
        """Starte einen registrierten Service"""
        if name not in self._services:
            logger.error(f"Service not found: {name}")
            return False
            
        service = self._services[name]
        info = self.registry.get(name)
        
        if info.status == ServiceStatus.RUNNING:
            return True
            
        try:
            info.status = ServiceStatus.STARTING
            
            # Start service
            if hasattr(service, 'start'):
                result = await service.start() if asyncio.iscoroutinefunction(service.start) else service.start()
                if result is False:
                    info.status = ServiceStatus.ERROR
                    return False
                    
            info.status = ServiceStatus.RUNNING
            
            await self.event_bus.emit(Event(
                type=EventType.SERVICE,
                source=name,
                data={"action": "started"}
            ))
            
            logger.info(f"Service started: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start service {name}: {e}")
            info.status = ServiceStatus.ERROR
            info.error = str(e)
            return False
            
    async def stop_service(self, name: str) -> bool:
        """Stoppe einen laufenden Service"""
        if name not in self._services:
            return False
            
        service = self._services[name]
        info = self.registry.get(name)
        
        if info.status == ServiceStatus.STOPPED:
            return True
            
        try:
            info.status = ServiceStatus.STOPPING
            
            if hasattr(service, 'stop'):
                if asyncio.iscoroutinefunction(service.stop):
                    await service.stop()
                else:
                    service.stop()
                    
            info.status = ServiceStatus.STOPPED
            
            await self.event_bus.emit(Event(
                type=EventType.SERVICE,
                source=name,
                data={"action": "stopped"}
            ))
            
            logger.info(f"Service stopped: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop service {name}: {e}")
            return False
            
    async def call(
        self,
        service: str,
        method: str,
        params: Optional[Dict] = None,
        timeout: Optional[float] = None
    ) -> Any:
        """
        Rufe eine Methode auf einem Service auf
        
        Args:
            service: Service-Name
            method: Methoden-Name
            params: Parameter-Dict
            timeout: Timeout in Sekunden
            
        Returns:
            Ergebnis der Methode
        """
        if service not in self._services:
            raise ValueError(f"Service not found: {service}")
            
        svc = self._services[service]
        info = self.registry.get(service)
        
        if info.status != ServiceStatus.RUNNING:
            raise RuntimeError(f"Service not running: {service}")
            
        if not hasattr(svc, method):
            raise AttributeError(f"Method not found: {service}.{method}")
            
        func = getattr(svc, method)
        timeout = timeout or self.config.service_timeout
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(**(params or {})),
                    timeout=timeout
                )
            else:
                result = func(**(params or {}))
                
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Service call timeout: {service}.{method}")
            raise
        except Exception as e:
            logger.error(f"Service call failed: {service}.{method} - {e}")
            raise
            
    def on(self, event_pattern: str, callback: Callable):
        """
        Registriere Event-Handler
        
        Args:
            event_pattern: Event-Pattern (z.B. "brain.response", "*.error")
            callback: Handler-Funktion
        """
        self.event_bus.subscribe(event_pattern, callback)
        
    async def emit(self, event: Event):
        """Emit ein Event"""
        await self.event_bus.emit(event)
        
    def get_service_status(self, name: str) -> Optional[ServiceInfo]:
        """Status eines Services abrufen"""
        return self.registry.get(name)
        
    def list_services(self) -> List[str]:
        """Liste aller registrierten Services"""
        return self.registry.list_services()
        
    def get_hub_status(self) -> dict:
        """Gesamtstatus von RyxHub"""
        return {
            "running": self._running,
            "host": self.config.host,
            "port": self.config.port,
            "services": {
                name: {
                    "status": self.registry.get(name).status.value,
                    "capabilities": self.registry.get(name).capabilities
                }
                for name in self.registry.list_services()
            },
            "features": {
                "voice": self.config.enable_voice,
                "hardware": self.config.enable_hardware,
                "agents": self.config.enable_agents,
                "api": self.config.enable_api,
                "websocket": self.config.enable_websocket
            }
        }
        
    async def _init_voice_service(self):
        """Initialisiere Voice-Service"""
        try:
            from ..voice import VoiceInterface
            voice = VoiceInterface()
            await self.register_service("voice", voice, [
                "listen", "speak", "wake_word"
            ])
        except ImportError as e:
            logger.warning(f"Voice service not available: {e}")
            
    async def _init_hardware_service(self):
        """Initialisiere Hardware-Service"""
        try:
            from ..hardware import HardwareManager
            hw = HardwareManager()
            await self.register_service("hardware", hw, [
                "camera", "face_detection", "presence"
            ])
        except ImportError as e:
            logger.warning(f"Hardware service not available: {e}")
            
    async def _start_api(self):
        """Starte HTTP/WebSocket API"""
        from .api import HubAPI
        self._api_server = HubAPI(self)
        await self._api_server.start(self.config.host, self.config.port)
        
    async def _stop_api(self):
        """Stoppe API Server"""
        if self._api_server:
            await self._api_server.stop()
            
    async def _health_monitor_loop(self):
        """Health-Check Loop für alle Services"""
        while self._running:
            try:
                for name in self.registry.list_services():
                    info = self.registry.get(name)
                    if info.status == ServiceStatus.RUNNING:
                        service = self._services.get(name)
                        
                        # Check health
                        if hasattr(service, 'health_check'):
                            try:
                                if asyncio.iscoroutinefunction(service.health_check):
                                    healthy = await asyncio.wait_for(
                                        service.health_check(),
                                        timeout=5.0
                                    )
                                else:
                                    healthy = service.health_check()
                                    
                                if not healthy:
                                    logger.warning(f"Service unhealthy: {name}")
                                    info.status = ServiceStatus.UNHEALTHY
                                    
                            except asyncio.TimeoutError:
                                logger.warning(f"Health check timeout: {name}")
                                info.status = ServiceStatus.UNHEALTHY
                            except Exception as e:
                                logger.error(f"Health check error for {name}: {e}")
                                
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                
            await asyncio.sleep(self.config.health_check_interval)
            
    async def _load_state(self):
        """Lade persistierten State"""
        state_file = self.config.state_dir / "hub_state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                logger.debug(f"Loaded state from {state_file}")
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")
                
    async def _save_state(self):
        """Speichere State"""
        state_file = self.config.state_dir / "hub_state.json"
        try:
            state = {
                "services": self.list_services(),
                "config": {
                    "host": self.config.host,
                    "port": self.config.port
                }
            }
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            logger.debug(f"Saved state to {state_file}")
        except Exception as e:
            logger.warning(f"Failed to save state: {e}")
