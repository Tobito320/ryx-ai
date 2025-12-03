# -*- coding: utf-8 -*-
"""
Event Bus - Zentrales Event-System für Inter-Service-Kommunikation
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Callable, Any
from enum import Enum
from datetime import datetime
import fnmatch
import logging
import uuid

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event-Typen"""
    SYSTEM = "system"       # Hub lifecycle events
    SERVICE = "service"     # Service lifecycle events
    REQUEST = "request"     # Incoming requests
    RESPONSE = "response"   # Responses
    ERROR = "error"         # Errors
    LOG = "log"            # Log messages
    METRIC = "metric"      # Metrics
    CUSTOM = "custom"      # User-defined events


@dataclass
class Event:
    """Ein Event im EventBus"""
    type: EventType
    source: str  # Service/Component name
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    target: Optional[str] = None  # Optional: specific target service
    reply_to: Optional[str] = None  # For request-response pattern
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "target": self.target,
            "reply_to": self.reply_to
        }


class EventBus:
    """
    Zentraler Event-Bus für Ryx
    
    Features:
    - Publish/Subscribe Pattern
    - Pattern-based Subscriptions (wildcards)
    - Async Event Delivery
    - Request-Response Pattern
    
    Patterns:
    - "brain.response" - Exakte Subscription
    - "brain.*" - Alle Events von brain
    - "*.error" - Alle Error-Events
    - "*" - Alle Events
    
    Usage:
        bus = EventBus()
        await bus.start()
        
        # Subscribe
        bus.subscribe("brain.response", handle_response)
        bus.subscribe("*.error", handle_error)
        
        # Publish
        await bus.emit(Event(
            type=EventType.RESPONSE,
            source="brain",
            data={"text": "Hello!"}
        ))
        
        # Request-Response
        response = await bus.request(
            "voice",
            {"action": "speak", "text": "Hello"}
        )
    """
    
    def __init__(self, max_queue_size: int = 1000):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._running = False
        self._dispatch_task: Optional[asyncio.Task] = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        
    async def start(self):
        """Starte Event-Verarbeitung"""
        if self._running:
            return
            
        self._running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        logger.debug("EventBus started")
        
    async def stop(self):
        """Stoppe Event-Verarbeitung"""
        self._running = False
        
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
                
        # Cancel pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
                
        logger.debug("EventBus stopped")
        
    def subscribe(self, pattern: str, callback: Callable):
        """
        Registriere Event-Handler
        
        Args:
            pattern: Event-Pattern (z.B. "brain.*", "*.error")
            callback: Handler-Funktion (sync oder async)
        """
        if pattern not in self._subscribers:
            self._subscribers[pattern] = []
            
        self._subscribers[pattern].append(callback)
        logger.debug(f"Subscribed to pattern: {pattern}")
        
    def unsubscribe(self, pattern: str, callback: Callable):
        """Entferne Event-Handler"""
        if pattern in self._subscribers:
            try:
                self._subscribers[pattern].remove(callback)
            except ValueError:
                pass
                
    async def emit(self, event: Event):
        """
        Emit ein Event
        
        Args:
            event: Das zu sendende Event
        """
        if not self._running:
            logger.warning("EventBus not running, event dropped")
            return
            
        try:
            await asyncio.wait_for(
                self._queue.put(event),
                timeout=1.0
            )
        except asyncio.TimeoutError:
            logger.warning(f"Event queue full, dropped: {event.type}")
            
    def emit_sync(self, event: Event):
        """Synchrones Emit (für non-async Contexte)"""
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning(f"Event queue full, dropped: {event.type}")
            
    async def request(
        self,
        target: str,
        data: Dict[str, Any],
        timeout: float = 30.0
    ) -> Optional[Dict]:
        """
        Request-Response Pattern
        
        Args:
            target: Ziel-Service
            data: Request-Daten
            timeout: Timeout in Sekunden
            
        Returns:
            Response-Daten oder None bei Timeout
        """
        request_id = str(uuid.uuid4())
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future
        
        try:
            # Emit request
            await self.emit(Event(
                type=EventType.REQUEST,
                source="hub",
                target=target,
                data=data,
                reply_to=request_id
            ))
            
            # Wait for response
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"Request timeout: {target}")
            return None
        finally:
            del self._pending_requests[request_id]
            
    async def _dispatch_loop(self):
        """Event-Dispatch-Loop"""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )
                await self._dispatch(event)
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Dispatch error: {e}")
                
    async def _dispatch(self, event: Event):
        """Verteile Event an Subscriber"""
        event_key = f"{event.source}.{event.type.value}"
        
        # Handle response to pending request
        if event.type == EventType.RESPONSE and event.reply_to:
            future = self._pending_requests.get(event.reply_to)
            if future and not future.done():
                future.set_result(event.data)
                return
                
        # Find matching subscribers
        for pattern, callbacks in self._subscribers.items():
            if self._matches_pattern(pattern, event_key, event):
                for callback in callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(event)
                        else:
                            callback(event)
                    except Exception as e:
                        logger.error(f"Subscriber error for {pattern}: {e}")
                        
    def _matches_pattern(self, pattern: str, event_key: str, event: Event) -> bool:
        """Prüfe ob Pattern zum Event passt"""
        # Wildcard matching
        if pattern == "*":
            return True
            
        # fnmatch-style matching
        if fnmatch.fnmatch(event_key, pattern):
            return True
            
        # Separate source/type matching
        if "." in pattern:
            p_source, p_type = pattern.split(".", 1)
            if p_source in ("*", event.source) and p_type in ("*", event.type.value):
                return True
                
        return False
        
    def get_subscriber_count(self, pattern: Optional[str] = None) -> int:
        """Anzahl Subscriber"""
        if pattern:
            return len(self._subscribers.get(pattern, []))
        return sum(len(cbs) for cbs in self._subscribers.values())
        
    def get_queue_size(self) -> int:
        """Aktuelle Queue-Größe"""
        return self._queue.qsize()
