"""
Tab Hibernation System

Automatically hibernates inactive tabs to save memory.
Wakes them instantly when needed.
"""

import time
import logging
from typing import Dict, Set, Optional, Callable
from dataclasses import dataclass, field
from threading import Timer

log = logging.getLogger("ryxsurf.hibernation")


@dataclass
class TabState:
    """Tab hibernation state"""
    tab_id: str
    url: str
    title: str
    last_active: float
    scroll_position: tuple = (0, 0)
    form_data: Dict = field(default_factory=dict)
    is_hibernated: bool = False
    memory_saved: int = 0  # MB


class TabHibernation:
    """Manages tab hibernation for memory optimization"""
    
    def __init__(
        self,
        idle_threshold: int = 300,  # 5 minutes
        aggressive_threshold: int = 600,  # 10 minutes
        memory_pressure_threshold: float = 0.8,  # 80% RAM usage
    ):
        self.idle_threshold = idle_threshold
        self.aggressive_threshold = aggressive_threshold
        self.memory_pressure_threshold = memory_pressure_threshold
        
        self.tabs: Dict[str, TabState] = {}
        self.hibernated_tabs: Set[str] = set()
        self.protected_tabs: Set[str] = set()  # Never hibernate
        
        self.wake_callback: Optional[Callable] = None
        self.hibernate_callback: Optional[Callable] = None
        
        self._monitor_timer: Optional[Timer] = None
        self._enabled = True
        
        log.info("Tab hibernation initialized")
    
    def register_tab(self, tab_id: str, url: str, title: str = ""):
        """Register a tab for hibernation monitoring"""
        if tab_id not in self.tabs:
            self.tabs[tab_id] = TabState(
                tab_id=tab_id,
                url=url,
                title=title,
                last_active=time.time()
            )
            log.debug(f"Registered tab for hibernation: {tab_id}")
    
    def mark_active(self, tab_id: str):
        """Mark tab as recently active"""
        if tab_id in self.tabs:
            self.tabs[tab_id].last_active = time.time()
            
            # Wake if hibernated
            if tab_id in self.hibernated_tabs:
                self.wake_tab(tab_id)
    
    def protect_tab(self, tab_id: str):
        """Protect tab from hibernation (e.g., playing media)"""
        self.protected_tabs.add(tab_id)
        log.debug(f"Protected tab from hibernation: {tab_id}")
    
    def unprotect_tab(self, tab_id: str):
        """Remove hibernation protection"""
        self.protected_tabs.discard(tab_id)
    
    def hibernate_tab(self, tab_id: str, force: bool = False) -> bool:
        """Hibernate a tab to save memory"""
        if tab_id not in self.tabs:
            return False
        
        if not force and tab_id in self.protected_tabs:
            log.debug(f"Tab {tab_id} is protected, skipping hibernation")
            return False
        
        tab = self.tabs[tab_id]
        if tab.is_hibernated:
            return True
        
        # Call callback to save state and unload
        if self.hibernate_callback:
            success = self.hibernate_callback(tab_id)
            if not success:
                log.warning(f"Failed to hibernate tab {tab_id}")
                return False
        
        tab.is_hibernated = True
        tab.memory_saved = self._estimate_memory_saved(tab)
        self.hibernated_tabs.add(tab_id)
        
        log.info(f"Hibernated tab {tab_id} ({tab.title[:30]}) - saved ~{tab.memory_saved}MB")
        return True
    
    def wake_tab(self, tab_id: str) -> bool:
        """Wake hibernated tab"""
        if tab_id not in self.tabs:
            return False
        
        tab = self.tabs[tab_id]
        if not tab.is_hibernated:
            return True
        
        # Call callback to restore
        if self.wake_callback:
            success = self.wake_callback(tab_id)
            if not success:
                log.warning(f"Failed to wake tab {tab_id}")
                return False
        
        tab.is_hibernated = False
        self.hibernated_tabs.discard(tab_id)
        
        log.info(f"Woke tab {tab_id} ({tab.title[:30]})")
        return True
    
    def check_and_hibernate(self, memory_pressure: float = 0.0) -> int:
        """Check tabs and hibernate idle ones"""
        if not self._enabled:
            return 0
        
        current_time = time.time()
        hibernated_count = 0
        
        # Determine threshold based on memory pressure
        if memory_pressure > self.memory_pressure_threshold:
            threshold = self.idle_threshold // 2  # More aggressive
            log.debug(f"High memory pressure ({memory_pressure:.0%}), using aggressive threshold")
        else:
            threshold = self.idle_threshold
        
        for tab_id, tab in self.tabs.items():
            if tab.is_hibernated or tab_id in self.protected_tabs:
                continue
            
            idle_time = current_time - tab.last_active
            
            if idle_time > threshold:
                if self.hibernate_tab(tab_id):
                    hibernated_count += 1
        
        if hibernated_count > 0:
            log.info(f"Hibernated {hibernated_count} tabs")
        
        return hibernated_count
    
    def get_hibernation_candidates(self, count: int = 5) -> list:
        """Get top N tabs that should be hibernated"""
        current_time = time.time()
        
        candidates = []
        for tab_id, tab in self.tabs.items():
            if tab.is_hibernated or tab_id in self.protected_tabs:
                continue
            
            idle_time = current_time - tab.last_active
            candidates.append((idle_time, tab_id, tab))
        
        # Sort by idle time (most idle first)
        candidates.sort(reverse=True)
        
        return [(tab_id, tab, idle_time) for idle_time, tab_id, tab in candidates[:count]]
    
    def get_total_memory_saved(self) -> int:
        """Get total memory saved by hibernation (MB)"""
        return sum(tab.memory_saved for tab in self.tabs.values() if tab.is_hibernated)
    
    def get_stats(self) -> Dict:
        """Get hibernation statistics"""
        total_tabs = len(self.tabs)
        hibernated = len(self.hibernated_tabs)
        active = total_tabs - hibernated
        memory_saved = self.get_total_memory_saved()
        
        return {
            "total_tabs": total_tabs,
            "active_tabs": active,
            "hibernated_tabs": hibernated,
            "protected_tabs": len(self.protected_tabs),
            "memory_saved_mb": memory_saved,
            "enabled": self._enabled,
        }
    
    def _estimate_memory_saved(self, tab: TabState) -> int:
        """Estimate memory saved by hibernating tab (MB)"""
        # Base memory per tab
        base = 50
        
        # Add more for complex pages
        if "youtube" in tab.url.lower():
            return base + 100  # Video players use lots of memory
        elif "google" in tab.url.lower() and "docs" in tab.url.lower():
            return base + 80  # Google Docs is heavy
        elif any(domain in tab.url.lower() for domain in ["facebook", "twitter", "reddit"]):
            return base + 60  # Social media has lots of scripts
        else:
            return base
    
    def enable(self):
        """Enable hibernation"""
        self._enabled = True
        log.info("Tab hibernation enabled")
    
    def disable(self):
        """Disable hibernation"""
        self._enabled = False
        log.info("Tab hibernation disabled")
    
    def clear(self):
        """Clear all hibernation data"""
        self.tabs.clear()
        self.hibernated_tabs.clear()
        self.protected_tabs.clear()
        log.info("Hibernation data cleared")


class SmartHibernation(TabHibernation):
    """Smart hibernation with ML-based predictions"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.access_patterns: Dict[str, list] = {}  # URL -> access times
        self.predictions: Dict[str, float] = {}  # tab_id -> probability of reuse
    
    def record_access(self, tab_id: str):
        """Record tab access for pattern learning"""
        if tab_id not in self.tabs:
            return
        
        tab = self.tabs[tab_id]
        url = tab.url
        
        if url not in self.access_patterns:
            self.access_patterns[url] = []
        
        self.access_patterns[url].append(time.time())
        
        # Keep only last 50 accesses
        self.access_patterns[url] = self.access_patterns[url][-50:]
        
        # Update prediction
        self._update_prediction(tab_id)
    
    def _update_prediction(self, tab_id: str):
        """Update reuse probability prediction"""
        if tab_id not in self.tabs:
            return
        
        tab = self.tabs[tab_id]
        url = tab.url
        
        if url not in self.access_patterns or len(self.access_patterns[url]) < 2:
            self.predictions[tab_id] = 0.5  # No data, assume medium probability
            return
        
        accesses = self.access_patterns[url]
        current_time = time.time()
        
        # Calculate average time between accesses
        intervals = [accesses[i] - accesses[i-1] for i in range(1, len(accesses))]
        avg_interval = sum(intervals) / len(intervals)
        
        # Time since last access
        time_since_last = current_time - tab.last_active
        
        # Probability decreases as time since last access increases
        if time_since_last < avg_interval:
            probability = 0.8  # High probability of reuse
        elif time_since_last < avg_interval * 2:
            probability = 0.5  # Medium probability
        else:
            probability = 0.2  # Low probability
        
        self.predictions[tab_id] = probability
        log.debug(f"Reuse probability for {tab_id}: {probability:.0%}")
    
    def get_smart_candidates(self, count: int = 5) -> list:
        """Get hibernation candidates using smart predictions"""
        candidates = []
        
        for tab_id, tab in self.tabs.items():
            if tab.is_hibernated or tab_id in self.protected_tabs:
                continue
            
            # Update predictions
            self._update_prediction(tab_id)
            
            probability = self.predictions.get(tab_id, 0.5)
            idle_time = time.time() - tab.last_active
            
            # Score: lower probability and longer idle time = better candidate
            score = (1 - probability) * idle_time
            
            candidates.append((score, tab_id, tab, probability))
        
        # Sort by score (highest first)
        candidates.sort(reverse=True)
        
        return [
            (tab_id, tab, probability) 
            for score, tab_id, tab, probability in candidates[:count]
        ]


def create_hibernation_manager(smart: bool = True, **kwargs) -> TabHibernation:
    """Create hibernation manager"""
    if smart:
        return SmartHibernation(**kwargs)
    else:
        return TabHibernation(**kwargs)
