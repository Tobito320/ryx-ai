"""
RyxSurf Hub Sync - Synchronization with RyxHub

Provides bidirectional sync between RyxSurf browser and RyxHub:
- Session sync (tabs, bookmarks, history)
- AI command forwarding
- Real-time event streaming

Uses WebSocket for real-time updates, REST for one-off operations.
"""

import json
import asyncio
import threading
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, asdict
from pathlib import Path
import time

import gi
gi.require_version('GLib', '2.0')
from gi.repository import GLib


@dataclass
class SyncEvent:
    """Event to be synced with RyxHub"""
    type: str  # tab_opened, tab_closed, navigation, bookmark_added, etc.
    data: Dict[str, Any]
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class HubSyncClient:
    """
    Client for syncing RyxSurf with RyxHub.
    
    Features:
    - Automatic reconnection
    - Event queuing when disconnected
    - Callbacks for incoming events
    """
    
    def __init__(self, hub_url: str = "http://localhost:8420"):
        self.hub_url = hub_url
        self.ws_url = hub_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
        
        self._ws = None
        self._connected = False
        self._reconnect_task = None
        self._event_queue: List[SyncEvent] = []
        self._callbacks: Dict[str, List[Callable]] = {}
        
        # Thread for async operations
        self._loop = None
        self._thread = None
        
    def start(self):
        """Start the sync client in background thread"""
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
    def _run_loop(self):
        """Run asyncio event loop in thread"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect_loop())
        
    async def _connect_loop(self):
        """Maintain WebSocket connection with reconnection"""
        try:
            import websockets
        except ImportError:
            print("websockets not installed. Hub sync disabled.")
            return
            
        while True:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    self._ws = ws
                    self._connected = True
                    print("✓ Connected to RyxHub")
                    
                    # Flush queued events
                    await self._flush_queue()
                    
                    # Listen for messages
                    async for message in ws:
                        await self._handle_message(message)
                        
            except Exception as e:
                self._connected = False
                print(f"Hub sync disconnected: {e}")
                
            # Wait before reconnecting
            await asyncio.sleep(5)
            
    async def _flush_queue(self):
        """Send queued events after reconnection"""
        while self._event_queue:
            event = self._event_queue.pop(0)
            await self._send_event(event)
            
    async def _send_event(self, event: SyncEvent):
        """Send event to RyxHub"""
        if self._ws and self._connected:
            try:
                await self._ws.send(json.dumps({
                    "action": "browser_event",
                    "event": asdict(event)
                }))
            except Exception as e:
                print(f"Failed to send event: {e}")
                self._event_queue.append(event)
                
    async def _handle_message(self, message: str):
        """Handle incoming message from RyxHub"""
        try:
            data = json.loads(message)
            event_type = data.get("type", "unknown")
            
            # Call registered callbacks
            if event_type in self._callbacks:
                for callback in self._callbacks[event_type]:
                    GLib.idle_add(callback, data.get("data", {}))
                    
            # Handle special events
            if event_type == "ai_command":
                # AI command from RyxHub
                if "ai_command" in self._callbacks:
                    for callback in self._callbacks["ai_command"]:
                        GLib.idle_add(callback, data.get("data", {}))
                        
        except json.JSONDecodeError:
            pass
            
    def on(self, event_type: str, callback: Callable):
        """Register callback for event type"""
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)
        
    def emit(self, event_type: str, data: Dict[str, Any]):
        """Emit event to RyxHub"""
        event = SyncEvent(type=event_type, data=data)
        
        if self._connected and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._send_event(event),
                self._loop
            )
        else:
            self._event_queue.append(event)
            
    def sync_tab_opened(self, tab_id: int, url: str, title: str):
        """Sync tab opened event"""
        self.emit("tab_opened", {
            "tab_id": tab_id,
            "url": url,
            "title": title
        })
        
    def sync_tab_closed(self, tab_id: int):
        """Sync tab closed event"""
        self.emit("tab_closed", {"tab_id": tab_id})
        
    def sync_navigation(self, tab_id: int, url: str, title: str):
        """Sync navigation event"""
        self.emit("navigation", {
            "tab_id": tab_id,
            "url": url,
            "title": title
        })
        
    def sync_session(self, session_name: str, tabs: List[Dict]):
        """Sync current session state"""
        self.emit("session_sync", {
            "session": session_name,
            "tabs": tabs
        })
        
    def request_ai_action(self, action: str, context: Dict[str, Any], callback: Callable):
        """Request AI action from RyxHub brain"""
        self.on("ai_response", callback)
        self.emit("ai_request", {
            "action": action,
            "context": context
        })
        
    @property
    def is_connected(self) -> bool:
        return self._connected


class SessionSync:
    """
    Handles session synchronization between RyxSurf and disk/RyxHub.
    
    Syncs:
    - Tab URLs and positions
    - Scroll positions
    - Session groups (work/personal/etc)
    """
    
    SYNC_FILE = Path.home() / ".config" / "ryxsurf" / "sync_state.json"
    
    def __init__(self, hub_client: Optional[HubSyncClient] = None):
        self.hub_client = hub_client
        self._state = self._load_state()
        
    def _load_state(self) -> Dict:
        """Load sync state from disk"""
        if self.SYNC_FILE.exists():
            try:
                return json.loads(self.SYNC_FILE.read_text())
            except json.JSONDecodeError:
                pass
        return {
            "sessions": {},
            "last_sync": 0,
            "device_id": self._get_device_id()
        }
        
    def _save_state(self):
        """Save sync state to disk"""
        self.SYNC_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._state["last_sync"] = time.time()
        self.SYNC_FILE.write_text(json.dumps(self._state, indent=2))
        
    def _get_device_id(self) -> str:
        """Get unique device identifier"""
        import socket
        return socket.gethostname()
        
    def save_session(self, name: str, tabs: List[Dict]):
        """Save session state"""
        self._state["sessions"][name] = {
            "tabs": tabs,
            "updated": time.time()
        }
        self._save_state()
        
        # Sync to hub if connected
        if self.hub_client and self.hub_client.is_connected:
            self.hub_client.sync_session(name, tabs)
            
    def get_session(self, name: str) -> Optional[List[Dict]]:
        """Get session tabs"""
        session = self._state["sessions"].get(name)
        if session:
            return session.get("tabs", [])
        return None
        
    def list_sessions(self) -> List[str]:
        """List all session names"""
        return list(self._state["sessions"].keys())
        
    def merge_remote_session(self, name: str, remote_tabs: List[Dict]):
        """Merge remote session with local (conflict resolution)"""
        local = self._state["sessions"].get(name, {})
        local_tabs = local.get("tabs", [])
        local_updated = local.get("updated", 0)
        
        # For now: remote wins if newer, merge URLs otherwise
        # TODO: Smarter conflict resolution
        merged_urls = set()
        merged_tabs = []
        
        for tab in remote_tabs + local_tabs:
            url = tab.get("url", "")
            if url and url not in merged_urls:
                merged_urls.add(url)
                merged_tabs.append(tab)
                
        self._state["sessions"][name] = {
            "tabs": merged_tabs,
            "updated": time.time()
        }
        self._save_state()
        
        return merged_tabs
