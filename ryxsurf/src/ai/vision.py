"""
RyxSurf AI Vision - Page Understanding

Extracts structured information from pages for AI:
- Page layout analysis
- Popup/overlay detection
- Form identification
- Main content extraction
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class PageElement:
    """A significant element on the page"""
    element_type: str  # link, button, form, popup, article, etc.
    selector: str
    text: str
    position: Dict[str, int]  # x, y, width, height
    attributes: Dict[str, str] = field(default_factory=dict)


@dataclass
class PageAnalysis:
    """Complete page analysis for AI context"""
    url: str
    title: str
    
    # Content
    main_content: str  # Extracted article/main text
    headings: List[str] = field(default_factory=list)
    
    # Interactive elements
    links: List[PageElement] = field(default_factory=list)
    buttons: List[PageElement] = field(default_factory=list)
    forms: List[PageElement] = field(default_factory=list)
    inputs: List[PageElement] = field(default_factory=list)
    
    # Overlays/popups
    popups: List[PageElement] = field(default_factory=list)
    has_cookie_banner: bool = False
    has_newsletter_popup: bool = False
    has_paywall: bool = False
    
    # Metadata
    language: str = "en"
    is_article: bool = False
    word_count: int = 0


class PageVision:
    """
    Analyzes page content for AI understanding.
    
    Injects JavaScript to extract:
    - Page structure
    - Interactive elements
    - Popup/overlay detection
    - Main content
    """
    
    def get_analysis_js(self) -> str:
        """JavaScript to analyze page and return structured data"""
        return """
        (function() {
            const analysis = {
                url: window.location.href,
                title: document.title,
                main_content: '',
                headings: [],
                links: [],
                buttons: [],
                forms: [],
                inputs: [],
                popups: [],
                has_cookie_banner: false,
                has_newsletter_popup: false,
                has_paywall: false,
                language: document.documentElement.lang || 'en',
                is_article: false,
                word_count: 0
            };
            
            // Extract main content
            const contentSelectors = ['article', 'main', '.content', '.post', '.entry', '#content'];
            for (const sel of contentSelectors) {
                const el = document.querySelector(sel);
                if (el) {
                    analysis.main_content = el.innerText.substring(0, 10000);
                    analysis.is_article = sel === 'article';
                    break;
                }
            }
            
            if (!analysis.main_content) {
                analysis.main_content = document.body.innerText.substring(0, 10000);
            }
            
            analysis.word_count = analysis.main_content.split(/\\s+/).length;
            
            // Extract headings
            document.querySelectorAll('h1, h2, h3').forEach(h => {
                const text = h.innerText.trim();
                if (text) analysis.headings.push(text.substring(0, 100));
            });
            
            // Extract links (visible only)
            document.querySelectorAll('a[href]').forEach(a => {
                const rect = a.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0 && rect.top < window.innerHeight * 2) {
                    analysis.links.push({
                        element_type: 'link',
                        selector: getSelector(a),
                        text: (a.innerText || a.getAttribute('aria-label') || '').substring(0, 50).trim(),
                        position: {x: Math.round(rect.left), y: Math.round(rect.top), width: Math.round(rect.width), height: Math.round(rect.height)},
                        attributes: {href: a.href}
                    });
                }
            });
            
            // Limit links
            analysis.links = analysis.links.slice(0, 50);
            
            // Extract buttons
            document.querySelectorAll('button, [role="button"], input[type="submit"]').forEach(btn => {
                const rect = btn.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    analysis.buttons.push({
                        element_type: 'button',
                        selector: getSelector(btn),
                        text: (btn.innerText || btn.value || btn.getAttribute('aria-label') || '').substring(0, 50).trim(),
                        position: {x: Math.round(rect.left), y: Math.round(rect.top), width: Math.round(rect.width), height: Math.round(rect.height)},
                        attributes: {}
                    });
                }
            });
            
            // Detect popups/overlays
            const popupSelectors = [
                '[class*="popup"]', '[class*="modal"]', '[class*="overlay"]',
                '[class*="dialog"]', '[id*="popup"]', '[id*="modal"]',
                '[role="dialog"]', '[aria-modal="true"]'
            ];
            
            popupSelectors.forEach(sel => {
                document.querySelectorAll(sel).forEach(el => {
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    
                    if ((style.position === 'fixed' || style.position === 'absolute') && 
                        rect.width > 100 && rect.height > 100 &&
                        style.display !== 'none' && style.visibility !== 'hidden') {
                        
                        const text = el.innerText.toLowerCase();
                        
                        analysis.popups.push({
                            element_type: 'popup',
                            selector: getSelector(el),
                            text: el.innerText.substring(0, 200).trim(),
                            position: {x: Math.round(rect.left), y: Math.round(rect.top), width: Math.round(rect.width), height: Math.round(rect.height)},
                            attributes: {}
                        });
                        
                        // Detect specific popup types
                        if (text.includes('cookie') || text.includes('consent') || text.includes('gdpr')) {
                            analysis.has_cookie_banner = true;
                        }
                        if (text.includes('newsletter') || text.includes('subscribe') || text.includes('email')) {
                            analysis.has_newsletter_popup = true;
                        }
                        if (text.includes('subscribe') || text.includes('paywall') || text.includes('premium')) {
                            analysis.has_paywall = true;
                        }
                    }
                });
            });
            
            // Helper to generate selector
            function getSelector(el) {
                if (el.id) return '#' + el.id;
                let path = [];
                while (el && el.nodeType === Node.ELEMENT_NODE && path.length < 4) {
                    let sel = el.tagName.toLowerCase();
                    if (el.className && typeof el.className === 'string') {
                        const cls = el.className.trim().split(/\\s+/)[0];
                        if (cls && !cls.includes(':')) sel += '.' + cls;
                    }
                    path.unshift(sel);
                    el = el.parentNode;
                }
                return path.join(' > ');
            }
            
            return JSON.stringify(analysis);
        })()
        """
        
    def parse_analysis(self, json_str: str) -> PageAnalysis:
        """Parse JS analysis result into PageAnalysis"""
        import json
        
        try:
            data = json.loads(json_str)
        except:
            return PageAnalysis(url="", title="Parse Error")
            
        # Convert element dicts to PageElement objects
        def to_elements(items: List[Dict]) -> List[PageElement]:
            return [
                PageElement(
                    element_type=item.get("element_type", ""),
                    selector=item.get("selector", ""),
                    text=item.get("text", ""),
                    position=item.get("position", {}),
                    attributes=item.get("attributes", {})
                )
                for item in items
            ]
            
        return PageAnalysis(
            url=data.get("url", ""),
            title=data.get("title", ""),
            main_content=data.get("main_content", ""),
            headings=data.get("headings", []),
            links=to_elements(data.get("links", [])),
            buttons=to_elements(data.get("buttons", [])),
            forms=to_elements(data.get("forms", [])),
            inputs=to_elements(data.get("inputs", [])),
            popups=to_elements(data.get("popups", [])),
            has_cookie_banner=data.get("has_cookie_banner", False),
            has_newsletter_popup=data.get("has_newsletter_popup", False),
            has_paywall=data.get("has_paywall", False),
            language=data.get("language", "en"),
            is_article=data.get("is_article", False),
            word_count=data.get("word_count", 0)
        )
        
    def get_context_for_ai(self, analysis: PageAnalysis, max_length: int = 2000) -> str:
        """Format page analysis as context for AI"""
        parts = [
            f"Page: {analysis.title}",
            f"URL: {analysis.url}",
            f"Language: {analysis.language}",
            f"Type: {'Article' if analysis.is_article else 'Page'} ({analysis.word_count} words)",
        ]
        
        if analysis.has_cookie_banner:
            parts.append("⚠️ Has cookie banner")
        if analysis.has_newsletter_popup:
            parts.append("⚠️ Has newsletter popup")
        if analysis.has_paywall:
            parts.append("⚠️ Has paywall")
            
        if analysis.headings:
            parts.append(f"\nHeadings: {', '.join(analysis.headings[:5])}")
            
        if analysis.buttons:
            btn_texts = [b.text for b in analysis.buttons[:10] if b.text]
            parts.append(f"\nButtons: {', '.join(btn_texts)}")
            
        if analysis.popups:
            parts.append(f"\nPopups detected: {len(analysis.popups)}")
            for p in analysis.popups[:3]:
                parts.append(f"  - {p.text[:50]}")
                
        context = "\n".join(parts)
        
        # Add content summary if room
        remaining = max_length - len(context)
        if remaining > 200 and analysis.main_content:
            content_preview = analysis.main_content[:remaining-50].strip()
            context += f"\n\nContent preview:\n{content_preview}..."
            
        return context[:max_length]
