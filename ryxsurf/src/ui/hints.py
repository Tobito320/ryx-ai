"""
RyxSurf Hint Mode - Keyboard Link Navigation

Implements vimium-style link hints:
1. Press Super+f to enter hint mode
2. Letters appear over clickable elements
3. Type letters to click the element
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Callable


@dataclass
class Hint:
    """A single hint label for an element"""
    label: str          # The hint letters (e.g., "as", "df")
    selector: str       # CSS selector to find element
    element_type: str   # link, button, input, etc.
    text: str           # Element text/aria-label
    x: int              # Position for overlay
    y: int


class HintMode:
    """
    Manages hint mode for keyboard-based clicking.
    
    Flow:
    1. User presses Super+f
    2. We inject JS to find all clickable elements
    3. Generate hint labels and show overlay
    4. User types letters
    5. We click the matching element
    """
    
    # Characters used for hints (home row + easy reach)
    HINT_CHARS = "asdfghjkl"
    
    def __init__(self):
        self.active = False
        self.hints: List[Hint] = []
        self.current_input = ""
        
    def generate_labels(self, count: int) -> List[str]:
        """
        Generate hint labels for N elements.
        
        For small counts: single letters (a, s, d, f...)
        For larger counts: two letters (as, ad, af...)
        """
        chars = self.HINT_CHARS
        labels = []
        
        if count <= len(chars):
            # Single character labels
            labels = list(chars[:count])
        else:
            # Two character labels
            for c1 in chars:
                for c2 in chars:
                    labels.append(c1 + c2)
                    if len(labels) >= count:
                        break
                if len(labels) >= count:
                    break
                    
        return labels[:count]
        
    def get_hint_injection_js(self) -> str:
        """
        JavaScript to inject for finding clickable elements
        and creating hint overlays.
        """
        return """
        (function() {
            // Remove existing hints
            document.querySelectorAll('.ryxsurf-hint').forEach(el => el.remove());
            
            // Find clickable elements
            const selectors = [
                'a[href]',
                'button',
                'input[type="submit"]',
                'input[type="button"]',
                '[role="button"]',
                '[onclick]',
                'label[for]',
                'select',
                'textarea',
                'input:not([type="hidden"])'
            ];
            
            const elements = [];
            const seen = new Set();
            
            selectors.forEach(sel => {
                document.querySelectorAll(sel).forEach(el => {
                    // Skip hidden elements
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) return;
                    if (rect.top < 0 || rect.top > window.innerHeight) return;
                    if (rect.left < 0 || rect.left > window.innerWidth) return;
                    
                    // Skip duplicates
                    const key = `${rect.left},${rect.top}`;
                    if (seen.has(key)) return;
                    seen.add(key);
                    
                    elements.push({
                        selector: generateSelector(el),
                        type: el.tagName.toLowerCase(),
                        text: (el.textContent || el.value || el.getAttribute('aria-label') || '').substring(0, 50).trim(),
                        x: Math.round(rect.left),
                        y: Math.round(rect.top),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height)
                    });
                });
            });
            
            // Generate unique selector for element
            function generateSelector(el) {
                if (el.id) return '#' + el.id;
                
                let path = [];
                while (el && el.nodeType === Node.ELEMENT_NODE) {
                    let selector = el.tagName.toLowerCase();
                    if (el.className && typeof el.className === 'string') {
                        const classes = el.className.trim().split(/\\s+/).slice(0, 2);
                        if (classes.length) {
                            selector += '.' + classes.join('.');
                        }
                    }
                    path.unshift(selector);
                    el = el.parentNode;
                    if (path.length > 3) break;
                }
                return path.join(' > ');
            }
            
            return JSON.stringify(elements);
        })()
        """
        
    def get_overlay_js(self, hints: List[Dict]) -> str:
        """Generate JS to show hint overlays"""
        hints_json = str(hints).replace("'", '"')
        
        return f"""
        (function() {{
            const hints = {hints_json};
            
            // Create style
            const style = document.createElement('style');
            style.textContent = `
                .ryxsurf-hint {{
                    position: fixed;
                    z-index: 2147483647;
                    background: #282a36;
                    color: #f8f8f2;
                    border: 2px solid #bd93f9;
                    border-radius: 3px;
                    padding: 2px 5px;
                    font-family: monospace;
                    font-size: 12px;
                    font-weight: bold;
                    text-transform: uppercase;
                    pointer-events: none;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.5);
                }}
                .ryxsurf-hint-match {{
                    color: #50fa7b;
                }}
            `;
            document.head.appendChild(style);
            
            // Create hint elements
            hints.forEach(hint => {{
                const el = document.createElement('div');
                el.className = 'ryxsurf-hint';
                el.textContent = hint.label;
                el.style.left = hint.x + 'px';
                el.style.top = hint.y + 'px';
                el.dataset.label = hint.label;
                el.dataset.selector = hint.selector;
                document.body.appendChild(el);
            }});
        }})()
        """
        
    def get_click_js(self, selector: str) -> str:
        """Generate JS to click an element"""
        return f"""
        (function() {{
            // Remove hints first
            document.querySelectorAll('.ryxsurf-hint').forEach(el => el.remove());
            
            // Find and click element
            const el = document.querySelector('{selector}');
            if (el) {{
                el.focus();
                el.click();
                return 'clicked';
            }}
            return 'not found';
        }})()
        """
        
    def get_clear_hints_js(self) -> str:
        """JS to remove hint overlays"""
        return """
        document.querySelectorAll('.ryxsurf-hint').forEach(el => el.remove());
        """
        
    def filter_hints(self, input_char: str) -> List[Hint]:
        """Filter hints based on typed character"""
        self.current_input += input_char.lower()
        
        matching = [h for h in self.hints if h.label.startswith(self.current_input)]
        
        return matching
        
    def reset(self):
        """Reset hint mode state"""
        self.active = False
        self.hints = []
        self.current_input = ""
