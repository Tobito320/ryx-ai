"""
Instant Page Loading

Makes page loads feel instant through:
- Prerendering
- Aggressive caching
- Instant back/forward
- Predictive loading
"""

import logging
import time
from typing import Dict, Optional, Set, List
from dataclasses import dataclass, field
from collections import deque
import threading

log = logging.getLogger("ryxsurf.instant")


@dataclass
class CachedPage:
    """Cached page data"""
    url: str
    html: str
    resources: Dict[str, bytes] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    size_bytes: int = 0
    load_time: float = 0.0


@dataclass
class PrerenderedPage:
    """Prerendered page"""
    url: str
    timestamp: float = field(default_factory=time.time)
    is_ready: bool = False


class InstantLoad:
    """Instant page loading system"""
    
    def __init__(
        self,
        cache_size_mb: int = 100,
        max_cached_pages: int = 50,
        prerender_count: int = 1,
    ):
        self.cache_size_mb = cache_size_mb
        self.max_cached_pages = max_cached_pages
        self.prerender_count = prerender_count
        
        # Page cache
        self.cache: Dict[str, CachedPage] = {}
        self.cache_lru: deque = deque(maxlen=max_cached_pages)
        self.cache_size_bytes = 0
        
        # Prerendered pages
        self.prerendered: Dict[str, PrerenderedPage] = {}
        
        # Navigation history for instant back/forward
        self.history: deque = deque(maxlen=100)
        self.history_position = -1
        
        # Resources cache
        self.resource_cache: Dict[str, bytes] = {}
        self.resource_cache_size = 0
        self.max_resource_cache_size = 50 * 1024 * 1024  # 50MB
        
        # Statistics
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "prerender_hits": 0,
            "instant_loads": 0,
            "bytes_saved": 0,
        }
        
        self._lock = threading.Lock()
        self._enabled = True
        
        log.info("Instant load system initialized")
    
    def cache_page(self, url: str, html: str, resources: Dict[str, bytes] = None):
        """Cache a page for instant loading"""
        if not self._enabled:
            return
        
        # Calculate size
        size = len(html.encode('utf-8'))
        if resources:
            size += sum(len(data) for data in resources.values())
        
        with self._lock:
            # Check if we need to evict
            while (self.cache_size_bytes + size > self.cache_size_mb * 1024 * 1024 and 
                   len(self.cache) > 0):
                self._evict_oldest_page()
            
            # Cache the page
            cached = CachedPage(
                url=url,
                html=html,
                resources=resources or {},
                timestamp=time.time(),
                size_bytes=size,
            )
            
            self.cache[url] = cached
            self.cache_lru.append(url)
            self.cache_size_bytes += size
            
            log.debug(f"Cached page: {url[:60]} ({size // 1024}KB)")
    
    def get_cached_page(self, url: str) -> Optional[CachedPage]:
        """Get cached page if available"""
        with self._lock:
            if url in self.cache:
                self.stats["cache_hits"] += 1
                self.stats["instant_loads"] += 1
                
                # Move to end (most recently used)
                self.cache_lru.remove(url)
                self.cache_lru.append(url)
                
                log.info(f"✓ Cache hit: {url[:60]}")
                return self.cache[url]
            else:
                self.stats["cache_misses"] += 1
                return None
    
    def prerender_page(self, url: str) -> bool:
        """Start prerendering a page"""
        if not self._enabled:
            return False
        
        with self._lock:
            # Check if already prerendered
            if url in self.prerendered:
                return True
            
            # Limit concurrent prerenders
            if len(self.prerendered) >= self.prerender_count:
                # Remove oldest
                oldest = min(self.prerendered.items(), key=lambda x: x[1].timestamp)
                del self.prerendered[oldest[0]]
            
            # Start prerender
            self.prerendered[url] = PrerenderedPage(url=url)
            
        log.info(f"Prerendering: {url[:60]}")
        return True
    
    def is_prerendered(self, url: str) -> bool:
        """Check if page is prerendered and ready"""
        with self._lock:
            if url in self.prerendered:
                self.stats["prerender_hits"] += 1
                self.stats["instant_loads"] += 1
                return self.prerendered[url].is_ready
            return False
    
    def mark_prerendered_ready(self, url: str):
        """Mark prerendered page as ready"""
        with self._lock:
            if url in self.prerendered:
                self.prerendered[url].is_ready = True
                log.debug(f"Prerender ready: {url[:60]}")
    
    def add_to_history(self, url: str):
        """Add URL to navigation history"""
        with self._lock:
            # If navigating to new page (not back/forward)
            if self.history_position < len(self.history) - 1:
                # Remove forward history
                while len(self.history) > self.history_position + 1:
                    self.history.pop()
            
            self.history.append(url)
            self.history_position = len(self.history) - 1
    
    def can_go_back(self) -> bool:
        """Check if can go back"""
        return self.history_position > 0
    
    def can_go_forward(self) -> bool:
        """Check if can go forward"""
        return self.history_position < len(self.history) - 1
    
    def go_back(self) -> Optional[str]:
        """Get previous URL for instant back"""
        with self._lock:
            if self.can_go_back():
                self.history_position -= 1
                url = self.history[self.history_position]
                
                # Should be instant if cached
                if url in self.cache:
                    self.stats["instant_loads"] += 1
                
                return url
            return None
    
    def go_forward(self) -> Optional[str]:
        """Get next URL for instant forward"""
        with self._lock:
            if self.can_go_forward():
                self.history_position += 1
                url = self.history[self.history_position]
                
                # Should be instant if cached
                if url in self.cache:
                    self.stats["instant_loads"] += 1
                
                return url
            return None
    
    def cache_resource(self, url: str, data: bytes):
        """Cache a resource (image, CSS, JS)"""
        if not self._enabled:
            return
        
        size = len(data)
        
        with self._lock:
            # Check size limit
            while (self.resource_cache_size + size > self.max_resource_cache_size and
                   len(self.resource_cache) > 0):
                # Remove first item (simple FIFO)
                first_key = next(iter(self.resource_cache))
                removed_size = len(self.resource_cache[first_key])
                del self.resource_cache[first_key]
                self.resource_cache_size -= removed_size
            
            self.resource_cache[url] = data
            self.resource_cache_size += size
    
    def get_cached_resource(self, url: str) -> Optional[bytes]:
        """Get cached resource"""
        with self._lock:
            if url in self.resource_cache:
                self.stats["bytes_saved"] += len(self.resource_cache[url])
                return self.resource_cache[url]
            return None
    
    def clear_cache(self):
        """Clear all caches"""
        with self._lock:
            self.cache.clear()
            self.cache_lru.clear()
            self.cache_size_bytes = 0
            
            self.resource_cache.clear()
            self.resource_cache_size = 0
            
            self.prerendered.clear()
            
            log.info("All caches cleared")
    
    def clear_history(self):
        """Clear navigation history"""
        with self._lock:
            self.history.clear()
            self.history_position = -1
            log.info("Navigation history cleared")
    
    def get_stats(self) -> Dict:
        """Get instant load statistics"""
        with self._lock:
            total_requests = self.stats["cache_hits"] + self.stats["cache_misses"]
            hit_rate = (self.stats["cache_hits"] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                **self.stats,
                "cached_pages": len(self.cache),
                "cache_size_mb": self.cache_size_bytes / (1024 * 1024),
                "cached_resources": len(self.resource_cache),
                "resource_cache_mb": self.resource_cache_size / (1024 * 1024),
                "prerendered_pages": len(self.prerendered),
                "history_length": len(self.history),
                "cache_hit_rate": hit_rate,
                "enabled": self._enabled,
            }
    
    def _evict_oldest_page(self):
        """Evict oldest cached page"""
        if len(self.cache_lru) == 0:
            return
        
        oldest_url = self.cache_lru.popleft()
        if oldest_url in self.cache:
            size = self.cache[oldest_url].size_bytes
            del self.cache[oldest_url]
            self.cache_size_bytes -= size
            log.debug(f"Evicted page: {oldest_url[:60]}")
    
    def enable(self):
        """Enable instant loading"""
        self._enabled = True
        log.info("Instant load enabled")
    
    def disable(self):
        """Disable instant loading"""
        self._enabled = False
        log.info("Instant load disabled")


def create_instant_loader(**kwargs) -> InstantLoad:
    """Create instant load system"""
    return InstantLoad(**kwargs)
