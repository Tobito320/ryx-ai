"""
Force Dark Mode - Opera GX Feature

Applies dark theme to all websites using CSS injection.
Smart detection to avoid breaking already-dark sites.
"""

from typing import List
import logging

log = logging.getLogger("ryxsurf.force_dark")


class ForceDarkMode:
    """Manages force dark mode for web pages"""
    
    def __init__(self):
        self.enabled = False
        self.exclude_list: List[str] = []
        
        # CSS for force dark mode
        self.dark_css = """
        /* Force Dark Mode CSS */
        
        html {
            background-color: #1a1a1a !important;
        }
        
        body {
            background-color: #1a1a1a !important;
            color: #e0e0e0 !important;
        }
        
        /* Text elements */
        p, span, div, li, td, th, label, a, h1, h2, h3, h4, h5, h6 {
            color: #e0e0e0 !important;
            background-color: transparent !important;
        }
        
        /* Links */
        a {
            color: #6699ff !important;
        }
        
        a:visited {
            color: #9966ff !important;
        }
        
        /* Inputs and forms */
        input, textarea, select {
            background-color: #2a2a2a !important;
            color: #e0e0e0 !important;
            border-color: #444 !important;
        }
        
        input::placeholder, textarea::placeholder {
            color: #666 !important;
        }
        
        /* Buttons */
        button {
            background-color: #3a3a3a !important;
            color: #e0e0e0 !important;
            border-color: #555 !important;
        }
        
        /* Containers */
        div, section, article, aside, nav, header, footer, main {
            background-color: #1a1a1a !important;
            border-color: #333 !important;
        }
        
        /* Tables */
        table {
            background-color: #1a1a1a !important;
            border-color: #333 !important;
        }
        
        th {
            background-color: #2a2a2a !important;
        }
        
        tr:nth-child(even) {
            background-color: #222 !important;
        }
        
        /* Code blocks */
        pre, code {
            background-color: #0a0a0a !important;
            color: #e0e0e0 !important;
        }
        
        /* Images - reduce brightness slightly */
        img {
            opacity: 0.9;
            transition: opacity 0.2s;
        }
        
        img:hover {
            opacity: 1;
        }
        
        /* Videos */
        video {
            opacity: 0.95;
        }
        
        /* Scrollbars */
        ::-webkit-scrollbar {
            background-color: #1a1a1a !important;
        }
        
        ::-webkit-scrollbar-thumb {
            background-color: #444 !important;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background-color: #555 !important;
        }
        
        /* Selection */
        ::selection {
            background-color: #3a5a7a !important;
            color: #fff !important;
        }
        
        /* Modals and overlays */
        [role="dialog"], .modal, .overlay {
            background-color: #2a2a2a !important;
            color: #e0e0e0 !important;
        }
        
        /* Cards */
        .card, [class*="card"] {
            background-color: #2a2a2a !important;
            border-color: #333 !important;
        }
        
        /* Shadows - reduce or remove */
        * {
            box-shadow: none !important;
            text-shadow: none !important;
        }
        """
        
        # JavaScript to detect if site is already dark
        self.detection_script = """
        (function() {
            // Check if site is already dark
            const body = document.body;
            const html = document.documentElement;
            
            // Get background colors
            const bodyBg = window.getComputedStyle(body).backgroundColor;
            const htmlBg = window.getComputedStyle(html).backgroundColor;
            
            // Parse RGB values
            function getLuminance(rgb) {
                const match = rgb.match(/\\d+/g);
                if (!match || match.length < 3) return 255;
                
                const r = parseInt(match[0]);
                const g = parseInt(match[1]);
                const b = parseInt(match[2]);
                
                // Calculate relative luminance
                return (0.299 * r + 0.587 * g + 0.114 * b);
            }
            
            const bodyLum = getLuminance(bodyBg);
            const htmlLum = getLuminance(htmlBg);
            
            // If background is already dark (luminance < 100), don't apply
            if (bodyLum < 100 || htmlLum < 100) {
                return { alreadyDark: true };
            }
            
            // Check for dark mode indicators
            const darkModeIndicators = [
                'dark-mode',
                'dark-theme',
                'night-mode',
                'theme-dark',
            ];
            
            const classes = (body.className + ' ' + html.className).toLowerCase();
            for (const indicator of darkModeIndicators) {
                if (classes.includes(indicator)) {
                    return { alreadyDark: true };
                }
            }
            
            return { alreadyDark: false };
        })();
        """
    
    def set_enabled(self, enabled: bool):
        """Enable or disable force dark mode"""
        self.enabled = enabled
        log.info(f"Force dark mode {'enabled' if enabled else 'disabled'}")
    
    def add_to_exclude_list(self, domain: str):
        """Add domain to exclude list"""
        if domain not in self.exclude_list:
            self.exclude_list.append(domain)
            log.info(f"Added {domain} to force dark exclude list")
    
    def remove_from_exclude_list(self, domain: str):
        """Remove domain from exclude list"""
        if domain in self.exclude_list:
            self.exclude_list.remove(domain)
            log.info(f"Removed {domain} from force dark exclude list")
    
    def is_excluded(self, url: str) -> bool:
        """Check if URL is in exclude list"""
        for domain in self.exclude_list:
            if domain in url:
                return True
        return False
    
    def should_apply(self, url: str) -> bool:
        """Check if force dark mode should be applied to this URL"""
        if not self.enabled:
            return False
        
        if self.is_excluded(url):
            return False
        
        # Don't apply to local pages
        if url.startswith('file://') or url.startswith('about:'):
            return False
        
        return True
    
    def get_inject_css(self) -> str:
        """Get CSS to inject for force dark mode"""
        return self.dark_css
    
    def get_detection_script(self) -> str:
        """Get JavaScript to detect if site is already dark"""
        return self.detection_script


class SmartDarkMode:
    """Enhanced dark mode with smart detection"""
    
    def __init__(self):
        self.force_dark = ForceDarkMode()
        self.site_preferences: dict = {}  # domain -> prefer_light/prefer_dark
    
    def set_site_preference(self, domain: str, prefer_light: bool):
        """Set preference for a specific site"""
        self.site_preferences[domain] = "light" if prefer_light else "dark"
        
        if prefer_light:
            self.force_dark.add_to_exclude_list(domain)
        else:
            self.force_dark.remove_from_exclude_list(domain)
    
    def get_site_preference(self, domain: str) -> str:
        """Get preference for a site (light/dark/auto)"""
        return self.site_preferences.get(domain, "auto")
    
    def should_apply_to_page(self, url: str, is_already_dark: bool) -> bool:
        """Determine if dark mode should be applied"""
        from urllib.parse import urlparse
        
        try:
            domain = urlparse(url).netloc
            preference = self.get_site_preference(domain)
            
            if preference == "light":
                return False
            elif preference == "dark":
                return True
            else:  # auto
                # Don't apply if site is already dark
                if is_already_dark:
                    return False
                return self.force_dark.should_apply(url)
        except Exception as e:
            log.error(f"Error checking dark mode: {e}")
            return False
