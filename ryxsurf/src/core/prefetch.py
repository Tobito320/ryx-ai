"""
Smart Prefetch System

Predicts and preloads pages before user clicks.
Preconnects to likely domains.
"""

import logging
import time
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from urllib.parse import urlparse
import threading

log = logging.getLogger("ryxsurf.prefetch")


@dataclass
class NavigationPattern:
    """Navigation pattern data"""
    from_url: str
    to_url: str
    count: int = 1
    last_seen: float = field(default_factory=time.time)
    avg_delay: float = 0.0  # Average time between navigation


@dataclass
class DomainInfo:
    """Domain information for preconnect"""
    domain: str
    visit_count: int = 0
    last_visit: float = 0.0
    avg_load_time: float = 0.0
    is_preconnected: bool = False


class PrefetchEngine:
    """Smart prefetching engine"""
    
    def __init__(
        self,
        max_predictions: int = 10,
        confidence_threshold: float = 0.3,
        max_history: int = 1000,
    ):
        self.max_predictions = max_predictions
        self.confidence_threshold = confidence_threshold
        self.max_history = max_history
        
        # Navigation patterns
        self.patterns: Dict[str, Dict[str, NavigationPattern]] = defaultdict(dict)
        
        # Recent navigation history
        self.history: deque = deque(maxlen=max_history)
        
        # Domain statistics
        self.domains: Dict[str, DomainInfo] = {}
        
        # Currently prefetched URLs
        self.prefetched: Set[str] = set()
        self.prefetch_in_progress: Set[str] = set()
        
        # Callbacks
        self.prefetch_callback: Optional[callable] = None
        self.preconnect_callback: Optional[callable] = None
        
        self._enabled = True
        self._lock = threading.Lock()
        
        log.info("Prefetch engine initialized")
    
    def record_navigation(self, from_url: str, to_url: str, delay: float = 0.0):
        """Record a navigation for pattern learning"""
        if not self._enabled:
            return
        
        with self._lock:
            # Update pattern
            if from_url not in self.patterns:
                self.patterns[from_url] = {}
            
            if to_url in self.patterns[from_url]:
                pattern = self.patterns[from_url][to_url]
                pattern.count += 1
                pattern.last_seen = time.time()
                
                # Update average delay
                pattern.avg_delay = (pattern.avg_delay * (pattern.count - 1) + delay) / pattern.count
            else:
                self.patterns[from_url][to_url] = NavigationPattern(
                    from_url=from_url,
                    to_url=to_url,
                    count=1,
                    last_seen=time.time(),
                    avg_delay=delay
                )
            
            # Add to history
            self.history.append((from_url, to_url, time.time()))
            
            # Update domain info
            self._update_domain_info(to_url)
            
            log.debug(f"Recorded navigation: {from_url[:50]} -> {to_url[:50]}")
    
    def predict_next_pages(self, current_url: str, count: int = 5) -> List[Tuple[str, float]]:
        """Predict next pages user might navigate to"""
        if not self._enabled or current_url not in self.patterns:
            return []
        
        predictions = []
        
        with self._lock:
            for to_url, pattern in self.patterns[current_url].items():
                # Calculate confidence based on:
                # 1. Visit count (more visits = higher confidence)
                # 2. Recency (recent patterns more relevant)
                # 3. Total patterns from this URL (normalize)
                
                total_from_url = sum(p.count for p in self.patterns[current_url].values())
                frequency_score = pattern.count / total_from_url
                
                # Recency score (decay over 30 days)
                age_seconds = time.time() - pattern.last_seen
                age_days = age_seconds / 86400
                recency_score = max(0, 1 - (age_days / 30))
                
                # Combined confidence
                confidence = (frequency_score * 0.7 + recency_score * 0.3)
                
                if confidence >= self.confidence_threshold:
                    predictions.append((to_url, confidence))
        
        # Sort by confidence
        predictions.sort(key=lambda x: x[1], reverse=True)
        
        return predictions[:count]
    
    def get_preconnect_domains(self, current_url: str, count: int = 3) -> List[str]:
        """Get domains to preconnect based on likely navigation"""
        predictions = self.predict_next_pages(current_url, count * 2)
        
        domains = []
        for url, confidence in predictions:
            domain = self._extract_domain(url)
            if domain and domain not in domains:
                domains.append(domain)
                if len(domains) >= count:
                    break
        
        return domains
    
    def should_prefetch(self, url: str) -> bool:
        """Check if URL should be prefetched"""
        if not self._enabled:
            return False
        
        # Don't prefetch if already done
        if url in self.prefetched or url in self.prefetch_in_progress:
            return False
        
        # Don't prefetch certain types
        parsed = urlparse(url)
        ext = parsed.path.split('.')[-1].lower() if '.' in parsed.path else ''
        
        # Skip large files
        skip_extensions = {'pdf', 'zip', 'mp4', 'avi', 'mkv', 'exe', 'dmg', 'iso'}
        if ext in skip_extensions:
            return False
        
        # Skip streaming sites (too much bandwidth)
        skip_domains = {'youtube.com', 'twitch.tv', 'netflix.com', 'vimeo.com'}
        if any(domain in parsed.netloc for domain in skip_domains):
            return False
        
        return True
    
    def prefetch_url(self, url: str, priority: int = 0) -> bool:
        """Prefetch a URL"""
        if not self.should_prefetch(url):
            return False
        
        with self._lock:
            self.prefetch_in_progress.add(url)
        
        # Call prefetch callback
        if self.prefetch_callback:
            success = self.prefetch_callback(url, priority)
            
            with self._lock:
                self.prefetch_in_progress.discard(url)
                if success:
                    self.prefetched.add(url)
                    log.info(f"Prefetched: {url[:60]}")
                else:
                    log.warning(f"Failed to prefetch: {url[:60]}")
            
            return success
        
        return False
    
    def preconnect_domain(self, domain: str) -> bool:
        """Preconnect to a domain"""
        if not self._enabled:
            return False
        
        with self._lock:
            if domain not in self.domains:
                self.domains[domain] = DomainInfo(domain=domain)
            
            domain_info = self.domains[domain]
            
            if domain_info.is_preconnected:
                return True
        
        # Call preconnect callback
        if self.preconnect_callback:
            success = self.preconnect_callback(domain)
            
            if success:
                with self._lock:
                    self.domains[domain].is_preconnected = True
                log.info(f"Preconnected to: {domain}")
            
            return success
        
        return False
    
    def auto_prefetch_and_preconnect(self, current_url: str):
        """Automatically prefetch and preconnect for current page"""
        if not self._enabled:
            return
        
        # Get predictions
        predictions = self.predict_next_pages(current_url, self.max_predictions)
        
        # Prefetch top predictions
        for url, confidence in predictions[:3]:  # Top 3
            if confidence >= self.confidence_threshold * 1.5:  # Higher threshold
                # Prefetch in background
                threading.Thread(
                    target=self.prefetch_url,
                    args=(url,),
                    kwargs={"priority": int(confidence * 100)},
                    daemon=True
                ).start()
        
        # Preconnect to likely domains
        domains = self.get_preconnect_domains(current_url, 3)
        for domain in domains:
            threading.Thread(
                target=self.preconnect_domain,
                args=(domain,),
                daemon=True
            ).start()
    
    def clear_prefetch_cache(self):
        """Clear prefetched URLs"""
        with self._lock:
            self.prefetched.clear()
            log.info("Prefetch cache cleared")
    
    def get_stats(self) -> Dict:
        """Get prefetch statistics"""
        with self._lock:
            total_patterns = sum(len(targets) for targets in self.patterns.values())
            
            return {
                "total_patterns": total_patterns,
                "unique_sources": len(self.patterns),
                "history_size": len(self.history),
                "prefetched_count": len(self.prefetched),
                "in_progress": len(self.prefetch_in_progress),
                "known_domains": len(self.domains),
                "enabled": self._enabled,
            }
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return ""
    
    def _update_domain_info(self, url: str):
        """Update domain statistics"""
        domain = self._extract_domain(url)
        if not domain:
            return
        
        if domain not in self.domains:
            self.domains[domain] = DomainInfo(domain=domain)
        
        info = self.domains[domain]
        info.visit_count += 1
        info.last_visit = time.time()
    
    def enable(self):
        """Enable prefetching"""
        self._enabled = True
        log.info("Prefetch engine enabled")
    
    def disable(self):
        """Disable prefetching"""
        self._enabled = False
        log.info("Prefetch engine disabled")
    
    def export_patterns(self) -> Dict:
        """Export navigation patterns for persistence"""
        with self._lock:
            return {
                "patterns": {
                    from_url: {
                        to_url: {
                            "count": p.count,
                            "last_seen": p.last_seen,
                            "avg_delay": p.avg_delay,
                        }
                        for to_url, p in targets.items()
                    }
                    for from_url, targets in self.patterns.items()
                },
                "domains": {
                    domain: {
                        "visit_count": info.visit_count,
                        "last_visit": info.last_visit,
                        "avg_load_time": info.avg_load_time,
                    }
                    for domain, info in self.domains.items()
                }
            }
    
    def import_patterns(self, data: Dict):
        """Import navigation patterns"""
        with self._lock:
            # Import patterns
            if "patterns" in data:
                for from_url, targets in data["patterns"].items():
                    self.patterns[from_url] = {}
                    for to_url, pattern_data in targets.items():
                        self.patterns[from_url][to_url] = NavigationPattern(
                            from_url=from_url,
                            to_url=to_url,
                            count=pattern_data["count"],
                            last_seen=pattern_data["last_seen"],
                            avg_delay=pattern_data.get("avg_delay", 0.0)
                        )
            
            # Import domains
            if "domains" in data:
                for domain, info_data in data["domains"].items():
                    self.domains[domain] = DomainInfo(
                        domain=domain,
                        visit_count=info_data["visit_count"],
                        last_visit=info_data["last_visit"],
                        avg_load_time=info_data.get("avg_load_time", 0.0)
                    )
            
            log.info(f"Imported {len(self.patterns)} patterns and {len(self.domains)} domains")


def create_prefetch_engine(**kwargs) -> PrefetchEngine:
    """Create prefetch engine"""
    return PrefetchEngine(**kwargs)
