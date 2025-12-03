# -*- coding: utf-8 -*-
"""
RyxHub API - REST und WebSocket API für externe Zugriffe
"""

import asyncio
import json
from typing import Optional, Dict, Any, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from .hub import RyxHub

logger = logging.getLogger(__name__)


class HubAPI:
    """
    HTTP/WebSocket API für RyxHub
    
    Endpoints:
    - GET /status - Hub-Status
    - GET /services - Liste aller Services
    - GET /services/{name} - Service-Details
    - POST /services/{name}/call - Service-Methode aufrufen
    - POST /chat - Chat mit Brain-Service
    - WS /ws - WebSocket für Events
    
    Usage:
        api = HubAPI(hub)
        await api.start("0.0.0.0", 8420)
        
        # In Browser/Client:
        # curl http://localhost:8420/status
        # wscat -c ws://localhost:8420/ws
    """
    
    def __init__(self, hub: 'RyxHub'):
        self.hub = hub
        self._app = None
        self._runner = None
        self._site = None
        self._websockets: set = set()
        
    async def start(self, host: str, port: int):
        """Starte API Server"""
        try:
            from aiohttp import web
        except ImportError:
            logger.warning("aiohttp not installed. API disabled.")
            return
            
        self._app = web.Application()
        self._setup_routes()
        
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        
        self._site = web.TCPSite(self._runner, host, port)
        await self._site.start()
        
        # Subscribe to all events for WebSocket broadcast
        self.hub.event_bus.subscribe("*", self._broadcast_event)
        
        logger.info(f"API started on http://{host}:{port}")
        
    async def stop(self):
        """Stoppe API Server"""
        # Close WebSocket connections
        for ws in list(self._websockets):
            await ws.close()
            
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()
            
        logger.info("API stopped")
        
    def _setup_routes(self):
        """Setup API Routes"""
        from aiohttp import web
        
        self._app.router.add_get("/", self._handle_root)
        self._app.router.add_get("/status", self._handle_status)
        self._app.router.add_get("/services", self._handle_services)
        self._app.router.add_get("/services/{name}", self._handle_service_detail)
        self._app.router.add_post("/services/{name}/call", self._handle_service_call)
        self._app.router.add_post("/chat", self._handle_chat)
        self._app.router.add_get("/ws", self._handle_websocket)
        
        # CORS middleware
        self._app.middlewares.append(self._cors_middleware)
        
    @staticmethod
    async def _cors_middleware(app, handler):
        """CORS Middleware"""
        async def middleware_handler(request):
            from aiohttp import web
            
            if request.method == "OPTIONS":
                return web.Response(headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization"
                })
                
            response = await handler(request)
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response
            
        return middleware_handler
        
    async def _handle_root(self, request):
        """Root-Endpoint"""
        from aiohttp import web
        
        return web.json_response({
            "name": "RyxHub",
            "version": "1.0.0",
            "endpoints": {
                "/status": "Hub status",
                "/services": "List services",
                "/services/{name}": "Service details",
                "/services/{name}/call": "Call service method",
                "/chat": "Chat with Brain",
                "/ws": "WebSocket events"
            }
        })
        
    async def _handle_status(self, request):
        """Status-Endpoint"""
        from aiohttp import web
        
        return web.json_response(self.hub.get_hub_status())
        
    async def _handle_services(self, request):
        """Services-Liste"""
        from aiohttp import web
        
        services = {}
        for name in self.hub.list_services():
            info = self.hub.get_service_status(name)
            if info:
                services[name] = info.to_dict()
                
        return web.json_response({"services": services})
        
    async def _handle_service_detail(self, request):
        """Service-Details"""
        from aiohttp import web
        
        name = request.match_info["name"]
        info = self.hub.get_service_status(name)
        
        if not info:
            return web.json_response(
                {"error": f"Service not found: {name}"},
                status=404
            )
            
        return web.json_response(info.to_dict())
        
    async def _handle_service_call(self, request):
        """Service-Methode aufrufen"""
        from aiohttp import web
        
        name = request.match_info["name"]
        
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response(
                {"error": "Invalid JSON"},
                status=400
            )
            
        method = body.get("method")
        params = body.get("params", {})
        
        if not method:
            return web.json_response(
                {"error": "Missing 'method' field"},
                status=400
            )
            
        try:
            result = await self.hub.call(name, method, params)
            return web.json_response({
                "success": True,
                "result": result
            })
        except ValueError as e:
            return web.json_response(
                {"error": str(e)},
                status=404
            )
        except Exception as e:
            return web.json_response(
                {"error": str(e)},
                status=500
            )
            
    async def _handle_chat(self, request):
        """Chat mit Brain-Service"""
        from aiohttp import web
        
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response(
                {"error": "Invalid JSON"},
                status=400
            )
            
        message = body.get("message")
        if not message:
            return web.json_response(
                {"error": "Missing 'message' field"},
                status=400
            )
            
        try:
            # Versuche brain service zu nutzen
            result = await self.hub.call("brain", "process", {"text": message})
            return web.json_response({
                "success": True,
                "response": result
            })
        except ValueError:
            return web.json_response(
                {"error": "Brain service not available"},
                status=503
            )
        except Exception as e:
            return web.json_response(
                {"error": str(e)},
                status=500
            )
            
    async def _handle_websocket(self, request):
        """WebSocket-Handler für Event-Streaming"""
        from aiohttp import web
        
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self._websockets.add(ws)
        logger.debug("WebSocket client connected")
        
        try:
            # Send initial status
            await ws.send_json({
                "type": "connected",
                "data": self.hub.get_hub_status()
            })
            
            # Handle incoming messages
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_ws_message(ws, data)
                    except json.JSONDecodeError:
                        await ws.send_json({"error": "Invalid JSON"})
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
                    
        finally:
            self._websockets.discard(ws)
            logger.debug("WebSocket client disconnected")
            
        return ws
        
    async def _handle_ws_message(self, ws, data: dict):
        """Handle WebSocket-Nachricht"""
        action = data.get("action")
        
        if action == "subscribe":
            pattern = data.get("pattern", "*")
            await ws.send_json({
                "type": "subscribed",
                "pattern": pattern
            })
            
        elif action == "call":
            service = data.get("service")
            method = data.get("method")
            params = data.get("params", {})
            
            try:
                result = await self.hub.call(service, method, params)
                await ws.send_json({
                    "type": "result",
                    "data": result
                })
            except Exception as e:
                await ws.send_json({
                    "type": "error",
                    "error": str(e)
                })
                
        elif action == "chat":
            message = data.get("message")
            try:
                result = await self.hub.call("brain", "process", {"text": message})
                await ws.send_json({
                    "type": "response",
                    "data": result
                })
            except Exception as e:
                await ws.send_json({
                    "type": "error",
                    "error": str(e)
                })
                
    async def _broadcast_event(self, event):
        """Broadcast Event an alle WebSocket-Clients"""
        if not self._websockets:
            return
            
        message = {
            "type": "event",
            "data": event.to_dict()
        }
        
        # Broadcast to all connected clients
        for ws in list(self._websockets):
            try:
                await ws.send_json(message)
            except Exception:
                # Client disconnected
                self._websockets.discard(ws)
