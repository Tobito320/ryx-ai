# -*- coding: utf-8 -*-
"""
RyxHub - Zentrales Control-Center für das Ryx Ökosystem

RyxHub ist der Orchestrator, der alle Ryx-Komponenten verwaltet:
- Ryx CLI/Brain
- RyxVoice
- RyxHardware (Kamera, Sensoren)
- RyxSurf (geplant)
- Agent-Services

Bietet:
- REST/WebSocket API
- Service Discovery
- Health Monitoring
- Zentrale Konfiguration
"""

from .hub import RyxHub, HubConfig
from .service_registry import ServiceRegistry, ServiceInfo
from .event_bus import EventBus, Event
from .api import HubAPI

__all__ = [
    'RyxHub',
    'HubConfig',
    'ServiceRegistry',
    'ServiceInfo',
    'EventBus',
    'Event',
    'HubAPI',
]
