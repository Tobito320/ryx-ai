"""
RyxSurf Tab Memory Manager

Handles automatic tab unloading to save memory:
- Tracks tab activity
- Unloads inactive tabs after timeout
- Reloads tabs on focus
- Limits max loaded tabs
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from threading import Thread
import asyncio


@dataclass
class TabMemoryState:
    """Memory state for a single tab"""
    tab_id: int
    url: str
    title: str
    last_active: float = field(default_factory=time.time)
    is_loaded: bool = True
    memory_mb: float = 0.0  # Estimated memory usage
    scroll_position: int = 0


class TabMemoryManager:
    """
    Manages tab memory by unloading inactive tabs.
    
    Strategy:
    1. Track when each tab was last active
    2. After unload_after_seconds of inactivity, unload tab
    3. Keep only max_loaded_tabs loaded at once
    4. On tab focus, reload if unloaded
    """
    
    def __init__(
        self,
        unload_after_seconds: int = 300,
        max_loaded_tabs: int = 10,
        on_unload: Optional[Callable[[int], None]] = None,
        on_reload: Optional[Callable[[int, str], None]] = None
    ):
        self.unload_after = unload_after_seconds
        self.max_loaded = max_loaded_tabs
        self.on_unload = on_unload
        self.on_reload = on_reload
        
        self.tabs: Dict[int, TabMemoryState] = {}
        self._running = False
        self._monitor_thread: Optional[Thread] = None
        
    def register_tab(self, tab_id: int, url: str, title: str = ""):
        """Register a new tab"""
        self.tabs[tab_id] = TabMemoryState(
            tab_id=tab_id,
            url=url,
            title=title,
            last_active=time.time(),
            is_loaded=True
        )
        
        # Check if we need to unload oldest
        self._check_limits()
        
    def unregister_tab(self, tab_id: int):
        """Remove a closed tab"""
        if tab_id in self.tabs:
            del self.tabs[tab_id]
            
    def mark_active(self, tab_id: int):
        """Mark a tab as active (user switched to it)"""
        if tab_id in self.tabs:
            self.tabs[tab_id].last_active = time.time()
            
            # Reload if unloaded
            if not self.tabs[tab_id].is_loaded:
                self._reload_tab(tab_id)
                
    def update_url(self, tab_id: int, url: str, title: str = ""):
        """Update tab URL (after navigation)"""
        if tab_id in self.tabs:
            self.tabs[tab_id].url = url
            self.tabs[tab_id].title = title
            self.tabs[tab_id].last_active = time.time()
            
    def save_scroll_position(self, tab_id: int, position: int):
        """Save scroll position before unloading"""
        if tab_id in self.tabs:
            self.tabs[tab_id].scroll_position = position
            
    def get_scroll_position(self, tab_id: int) -> int:
        """Get saved scroll position for reload"""
        if tab_id in self.tabs:
            return self.tabs[tab_id].scroll_position
        return 0
        
    def is_loaded(self, tab_id: int) -> bool:
        """Check if tab is currently loaded"""
        if tab_id in self.tabs:
            return self.tabs[tab_id].is_loaded
        return False
        
    def get_loaded_count(self) -> int:
        """Get number of currently loaded tabs"""
        return sum(1 for t in self.tabs.values() if t.is_loaded)
        
    def get_memory_usage(self) -> float:
        """Get estimated total memory usage in MB"""
        return sum(t.memory_mb for t in self.tabs.values() if t.is_loaded)
        
    def _check_limits(self):
        """Check and enforce tab limits"""
        loaded = [t for t in self.tabs.values() if t.is_loaded]
        
        if len(loaded) > self.max_loaded:
            # Sort by last active, unload oldest
            loaded.sort(key=lambda t: t.last_active)
            
            to_unload = len(loaded) - self.max_loaded
            for i in range(to_unload):
                self._unload_tab(loaded[i].tab_id)
                
    def _unload_tab(self, tab_id: int):
        """Unload a tab to free memory"""
        if tab_id not in self.tabs:
            return
            
        tab = self.tabs[tab_id]
        if not tab.is_loaded:
            return  # Already unloaded
            
        tab.is_loaded = False
        
        if self.on_unload:
            self.on_unload(tab_id)
            
    def _reload_tab(self, tab_id: int):
        """Reload a previously unloaded tab"""
        if tab_id not in self.tabs:
            return
            
        tab = self.tabs[tab_id]
        if tab.is_loaded:
            return  # Already loaded
            
        tab.is_loaded = True
        tab.last_active = time.time()
        
        if self.on_reload:
            self.on_reload(tab_id, tab.url)
            
    def start_monitor(self):
        """Start background monitoring thread"""
        if self._running:
            return
            
        self._running = True
        self._monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
    def stop_monitor(self):
        """Stop background monitoring"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
            
    def _monitor_loop(self):
        """Background loop to check for inactive tabs"""
        while self._running:
            now = time.time()
            
            for tab in list(self.tabs.values()):
                if not tab.is_loaded:
                    continue
                    
                inactive_time = now - tab.last_active
                
                if inactive_time > self.unload_after:
                    self._unload_tab(tab.tab_id)
                    
            # Check every 30 seconds
            time.sleep(30)
            
    def get_stats(self) -> Dict:
        """Get memory manager stats"""
        loaded = [t for t in self.tabs.values() if t.is_loaded]
        unloaded = [t for t in self.tabs.values() if not t.is_loaded]
        
        return {
            "total_tabs": len(self.tabs),
            "loaded_tabs": len(loaded),
            "unloaded_tabs": len(unloaded),
            "estimated_memory_mb": self.get_memory_usage(),
            "max_loaded": self.max_loaded,
            "unload_after_seconds": self.unload_after
        }
