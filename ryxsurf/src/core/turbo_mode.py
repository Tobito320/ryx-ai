"""
Turbo Mode

Ultra-fast browsing by aggressively blocking content.
Inspired by Opera GX turbo mode.
"""

import logging
from typing import Set, List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

log = logging.getLogger("ryxsurf.turbo")


class TurboLevel(Enum):
    """Turbo mode levels"""
    OFF = 0
    LIGHT = 1
    MEDIUM = 2
    EXTREME = 3


@dataclass
class BlockingRules:
    """Content blocking rules for turbo mode"""
    block_images: bool = False
    block_videos: bool = False
    block_ads: bool = True
    block_trackers: bool = True
    block_analytics: bool = True
    block_social: bool = False
    block_fonts: bool = False
    block_animations: bool = False
    compress_images: bool = True
    defer_javascript: bool = False
    disable_smooth_scroll: bool = False
    reduce_animations: bool = True


class TurboMode:
    """Turbo mode for ultra-fast browsing"""
    
    def __init__(self):
        self.level = TurboLevel.OFF
        self.rules = BlockingRules()
        
        # Built-in block lists
        self.ad_domains = self._load_ad_domains()
        self.tracker_domains = self._load_tracker_domains()
        self.analytics_domains = self._load_analytics_domains()
        self.social_domains = self._load_social_domains()
        
        # Custom rules
        self.custom_blocks: Set[str] = set()
        self.whitelist: Set[str] = set()
        
        # Statistics
        self.stats = {
            "blocked_requests": 0,
            "blocked_ads": 0,
            "blocked_trackers": 0,
            "blocked_images": 0,
            "blocked_videos": 0,
            "bytes_saved": 0,
        }
        
        log.info("Turbo mode initialized")
    
    def set_level(self, level: TurboLevel):
        """Set turbo mode level"""
        self.level = level
        
        if level == TurboLevel.OFF:
            self.rules = BlockingRules()
        elif level == TurboLevel.LIGHT:
            self.rules = BlockingRules(
                block_ads=True,
                block_trackers=True,
                block_analytics=True,
                compress_images=True,
                reduce_animations=True,
            )
        elif level == TurboLevel.MEDIUM:
            self.rules = BlockingRules(
                block_ads=True,
                block_trackers=True,
                block_analytics=True,
                block_social=True,
                compress_images=True,
                defer_javascript=True,
                reduce_animations=True,
            )
        elif level == TurboLevel.EXTREME:
            self.rules = BlockingRules(
                block_images=True,
                block_videos=True,
                block_ads=True,
                block_trackers=True,
                block_analytics=True,
                block_social=True,
                block_fonts=True,
                block_animations=True,
                defer_javascript=True,
                disable_smooth_scroll=True,
            )
        
        log.info(f"Turbo mode set to: {level.name}")
    
    def should_block(self, url: str, resource_type: str = "other") -> bool:
        """Check if resource should be blocked"""
        if self.level == TurboLevel.OFF:
            return False
        
        # Check whitelist
        if self._is_whitelisted(url):
            return False
        
        # Check custom blocks
        if url in self.custom_blocks:
            self.stats["blocked_requests"] += 1
            return True
        
        # Block by resource type
        if resource_type == "image" and self.rules.block_images:
            self.stats["blocked_images"] += 1
            self.stats["blocked_requests"] += 1
            return True
        
        if resource_type == "media" and self.rules.block_videos:
            self.stats["blocked_videos"] += 1
            self.stats["blocked_requests"] += 1
            return True
        
        # Block by domain
        if self.rules.block_ads and self._is_ad_domain(url):
            self.stats["blocked_ads"] += 1
            self.stats["blocked_requests"] += 1
            return True
        
        if self.rules.block_trackers and self._is_tracker_domain(url):
            self.stats["blocked_trackers"] += 1
            self.stats["blocked_requests"] += 1
            return True
        
        if self.rules.block_analytics and self._is_analytics_domain(url):
            self.stats["blocked_requests"] += 1
            return True
        
        if self.rules.block_social and self._is_social_domain(url):
            self.stats["blocked_requests"] += 1
            return True
        
        return False
    
    def get_content_filter_css(self) -> str:
        """Get CSS rules for content filtering"""
        css_rules = []
        
        if self.rules.block_animations:
            css_rules.append("""
                * {
                    animation: none !important;
                    transition: none !important;
                }
            """)
        
        if self.rules.reduce_animations:
            css_rules.append("""
                * {
                    animation-duration: 0.15s !important;
                    transition-duration: 0.15s !important;
                }
            """)
        
        if self.rules.disable_smooth_scroll:
            css_rules.append("""
                html {
                    scroll-behavior: auto !important;
                }
            """)
        
        if self.rules.block_fonts:
            css_rules.append("""
                @font-face {
                    font-family: 'fallback';
                    src: local('sans-serif');
                }
                * {
                    font-family: sans-serif !important;
                }
            """)
        
        return "\n".join(css_rules)
    
    def get_javascript_blocks(self) -> List[str]:
        """Get JavaScript functions to block"""
        blocks = []
        
        if self.rules.block_analytics:
            blocks.extend([
                "window.ga = function() {};",
                "window.gtag = function() {};",
                "window._gaq = [];",
                "window.dataLayer = [];",
            ])
        
        if self.rules.block_social:
            blocks.extend([
                "window.FB = undefined;",
                "window.twttr = undefined;",
            ])
        
        return blocks
    
    def add_custom_block(self, pattern: str):
        """Add custom block rule"""
        self.custom_blocks.add(pattern)
        log.debug(f"Added custom block: {pattern}")
    
    def add_to_whitelist(self, domain: str):
        """Add domain to whitelist"""
        self.whitelist.add(domain)
        log.debug(f"Added to whitelist: {domain}")
    
    def get_stats(self) -> Dict:
        """Get blocking statistics"""
        return {
            **self.stats,
            "level": self.level.name,
            "enabled": self.level != TurboLevel.OFF,
        }
    
    def reset_stats(self):
        """Reset statistics"""
        for key in self.stats:
            self.stats[key] = 0
        log.info("Turbo mode stats reset")
    
    def _is_whitelisted(self, url: str) -> bool:
        """Check if URL is whitelisted"""
        return any(domain in url for domain in self.whitelist)
    
    def _is_ad_domain(self, url: str) -> bool:
        """Check if URL is an ad domain"""
        return any(domain in url for domain in self.ad_domains)
    
    def _is_tracker_domain(self, url: str) -> bool:
        """Check if URL is a tracker domain"""
        return any(domain in url for domain in self.tracker_domains)
    
    def _is_analytics_domain(self, url: str) -> bool:
        """Check if URL is an analytics domain"""
        return any(domain in url for domain in self.analytics_domains)
    
    def _is_social_domain(self, url: str) -> bool:
        """Check if URL is a social media domain"""
        return any(domain in url for domain in self.social_domains)
    
    def _load_ad_domains(self) -> Set[str]:
        """Load ad domains list"""
        return {
            "doubleclick.net",
            "googlesyndication.com",
            "googleadservices.com",
            "adservice.google.com",
            "pagead2.googlesyndication.com",
            "afs.googlesyndication.com",
            "ads.yahoo.com",
            "advertising.com",
            "adnxs.com",
            "advertising.amazon.com",
            "ads.facebook.com",
            "ads.twitter.com",
            "ads.pinterest.com",
            "ads.reddit.com",
            "ad.doubleclick.net",
            "static.ads-twitter.com",
            "pubads.g.doubleclick.net",
        }
    
    def _load_tracker_domains(self) -> Set[str]:
        """Load tracker domains list"""
        return {
            "google-analytics.com",
            "googletagmanager.com",
            "connect.facebook.net",
            "scorecardresearch.com",
            "quantserve.com",
            "hotjar.com",
            "mouseflow.com",
            "crazy egg.com",
            "luckyorange.com",
            "inspectlet.com",
            "clicktale.net",
            "mixpanel.com",
            "segment.io",
            "amplitude.com",
            "heap analytics.io",
        }
    
    def _load_analytics_domains(self) -> Set[str]:
        """Load analytics domains list"""
        return {
            "google-analytics.com",
            "analytics.google.com",
            "stats.g.doubleclick.net",
            "mc.yandex.ru",
            "analytics.twitter.com",
            "analytics.facebook.com",
            "analytics.yahoo.com",
            "statcounter.com",
            "omniture.com",
            "chartbeat.com",
        }
    
    def _load_social_domains(self) -> Set[str]:
        """Load social media domains list"""
        return {
            "facebook.com/plugins",
            "facebook.com/tr",
            "connect.facebook.net",
            "platform.twitter.com",
            "twitter.com/widgets",
            "instagram.com/embed",
            "pinterest.com/widgets",
            "linkedin.com/widgets",
            "platform.linkedin.com",
            "reddit.com/static",
            "badges.reddit.com",
        }


def create_turbo_mode() -> TurboMode:
    """Create turbo mode instance"""
    return TurboMode()
