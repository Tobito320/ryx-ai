"""
RyxSurf AI Integration - Browser Control Agent

This agent can:
- Click elements on the page
- Summarize page content
- Dismiss popups and overlays
- Fill forms
- Navigate based on natural language
"""

import aiohttp
import asyncio
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


class ActionType(Enum):
    """Types of actions the AI can perform"""
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    NAVIGATE = "navigate"
    SUMMARIZE = "summarize"
    DISMISS = "dismiss"
    EXTRACT = "extract"
    READ = "read"
    ZOOM = "zoom"


@dataclass
class BrowserAction:
    """A single action to perform in the browser"""
    action_type: ActionType
    target: Optional[str] = None  # CSS selector or description
    value: Optional[str] = None   # Text to type, URL to navigate, etc.
    confidence: float = 1.0


@dataclass
class PageContext:
    """Context about the current page for AI"""
    url: str
    title: str
    text_content: str  # Extracted text
    links: List[Dict[str, str]]  # [{text, href}, ...]
    forms: List[Dict[str, Any]]  # Form elements
    has_popup: bool
    has_newsletter: bool


class BrowserAgent:
    """
    AI agent that controls the browser.
    
    Uses the ryx AI backend for understanding and planning.
    Executes actions via JavaScript injection.
    """
    
    def __init__(self, config: 'Config'):
        self.config = config
        self.api_base = config.ai_endpoint
        self.model = config.ai_model
        
    async def process_command(self, command: str, page_context: PageContext) -> List[BrowserAction]:
        """
        Process a natural language command and return actions to perform.
        
        Examples:
            "summarize this page" -> [SUMMARIZE]
            "click the login button" -> [CLICK with selector]
            "dismiss this popup" -> [DISMISS]
            "search for python tutorials" -> [NAVIGATE to search]
        """
        prompt = self._build_prompt(command, page_context)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self._system_prompt()},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 500,
                    "temperature": 0.3
                }
            ) as resp:
                if resp.status != 200:
                    return []
                    
                data = await resp.json()
                response = data["choices"][0]["message"]["content"]
                return self._parse_actions(response)
                
    def _system_prompt(self) -> str:
        """System prompt for browser control"""
        return """You are a browser control AI. You help users interact with web pages.

When given a command, output ONE action in this format:
ACTION: <type>
TARGET: <css_selector or description>
VALUE: <optional value>

Action types:
- CLICK: Click an element
- TYPE: Type text into an input
- SCROLL: Scroll the page (TARGET: up/down/top/bottom)
- NAVIGATE: Go to a URL
- SUMMARIZE: Summarize the page content
- DISMISS: Remove popup/overlay
- EXTRACT: Extract specific information
- READ: Enable reader mode

Examples:
User: "click the login button"
ACTION: CLICK
TARGET: button:contains('Login'), .login-btn, #login

User: "dismiss this popup"
ACTION: DISMISS
TARGET: [class*="popup"], [class*="modal"]

User: "summarize this"
ACTION: SUMMARIZE
TARGET: main, article, .content

Be concise. Output only the action format, no explanations."""

    def _build_prompt(self, command: str, ctx: PageContext) -> str:
        """Build prompt with page context"""
        links_summary = ", ".join([l["text"][:30] for l in ctx.links[:10]])
        
        return f"""Page: {ctx.title}
URL: {ctx.url}
Has popup: {ctx.has_popup}
Links: {links_summary}

User command: {command}"""

    def _parse_actions(self, response: str) -> List[BrowserAction]:
        """Parse AI response into actions"""
        actions = []
        
        lines = response.strip().split('\n')
        current_action = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith("ACTION:"):
                if current_action.get("type"):
                    actions.append(self._make_action(current_action))
                current_action = {"type": line.split(":", 1)[1].strip()}
            elif line.startswith("TARGET:"):
                current_action["target"] = line.split(":", 1)[1].strip()
            elif line.startswith("VALUE:"):
                current_action["value"] = line.split(":", 1)[1].strip()
                
        if current_action.get("type"):
            actions.append(self._make_action(current_action))
            
        return actions
        
    def _make_action(self, data: dict) -> BrowserAction:
        """Create BrowserAction from parsed data"""
        try:
            action_type = ActionType(data["type"].lower())
        except ValueError:
            action_type = ActionType.CLICK
            
        return BrowserAction(
            action_type=action_type,
            target=data.get("target"),
            value=data.get("value")
        )


class ActionExecutor:
    """Executes BrowserActions via JavaScript"""
    
    @staticmethod
    def get_js_for_action(action: BrowserAction) -> str:
        """Generate JavaScript to execute an action"""
        
        if action.action_type == ActionType.CLICK:
            return f"""
                (function() {{
                    const selectors = '{action.target}'.split(', ');
                    for (const sel of selectors) {{
                        const el = document.querySelector(sel);
                        if (el) {{
                            el.click();
                            return 'clicked';
                        }}
                    }}
                    return 'not found';
                }})()
            """
            
        elif action.action_type == ActionType.DISMISS:
            return """
                (function() {
                    // Remove popups, modals, overlays
                    const selectors = [
                        '[class*="popup"]', '[class*="modal"]', '[class*="overlay"]',
                        '[id*="popup"]', '[id*="modal"]', '[class*="newsletter"]',
                        '[class*="subscribe"]', '[class*="cookie"]'
                    ];
                    let removed = 0;
                    selectors.forEach(sel => {
                        document.querySelectorAll(sel).forEach(el => {
                            const style = window.getComputedStyle(el);
                            if (style.position === 'fixed' || style.position === 'absolute') {
                                el.remove();
                                removed++;
                            }
                        });
                    });
                    // Re-enable scrolling
                    document.body.style.overflow = 'auto';
                    document.documentElement.style.overflow = 'auto';
                    // Remove backdrop
                    document.querySelectorAll('[class*="backdrop"]').forEach(el => el.remove());
                    return `removed ${removed} elements`;
                })()
            """
            
        elif action.action_type == ActionType.SCROLL:
            if action.target == "down":
                return "window.scrollBy(0, window.innerHeight * 0.8)"
            elif action.target == "up":
                return "window.scrollBy(0, -window.innerHeight * 0.8)"
            elif action.target == "top":
                return "window.scrollTo(0, 0)"
            elif action.target == "bottom":
                return "window.scrollTo(0, document.body.scrollHeight)"
            else:
                return "window.scrollBy(0, 300)"
                
        elif action.action_type == ActionType.TYPE:
            return f"""
                (function() {{
                    const el = document.querySelector('{action.target}');
                    if (el) {{
                        el.value = '{action.value}';
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        return 'typed';
                    }}
                    return 'not found';
                }})()
            """
            
        elif action.action_type == ActionType.EXTRACT:
            return f"""
                (function() {{
                    const el = document.querySelector('{action.target}') || document.body;
                    return el.innerText.substring(0, 5000);
                }})()
            """
            
        elif action.action_type == ActionType.READ:
            # Reader mode - extract main content
            return """
                (function() {
                    const article = document.querySelector('article') || 
                                   document.querySelector('main') ||
                                   document.querySelector('.content') ||
                                   document.querySelector('#content');
                    if (article) {
                        // Hide everything else
                        document.body.innerHTML = `
                            <div style="max-width: 800px; margin: 0 auto; padding: 20px; font-size: 18px; line-height: 1.6;">
                                ${article.innerHTML}
                            </div>
                        `;
                        return 'reader mode enabled';
                    }
                    return 'no article found';
                })()
            """
            
        return "// No action"
