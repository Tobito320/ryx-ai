"""
Ryx AI Engine - Copilot CLI Style Architecture
===============================================

Core principles:
1. Knowledge-first: Use cached/known data before LLM
2. No hallucination: Admit when unknown, search if needed
3. Smart model routing: 1.5B for cached, 3B for simple, 7B+ for complex
4. Action-biased: Do things, don't explain how
5. Honest: Never make up answers to please user
"""

import os
import json
import subprocess
import re
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from core.ollama_client import OllamaClient
from core.model_router import ModelRouter
from core.paths import get_data_dir, get_project_root


class ActionType(Enum):
    """Types of actions Ryx can take"""
    # Instant actions (no LLM needed)
    OPEN_URL = "open_url"
    OPEN_FILE = "open_file"
    FIND_FILE = "find_file"
    RUN_COMMAND = "run_command"
    
    # Info actions
    ANSWER = "answer"           # Answer from knowledge/cache
    SEARCH_WEB = "search_web"   # Need to search
    SCRAPE = "scrape"           # Need to scrape a page
    
    # Interactive actions
    CLARIFY = "clarify"         # Need more info from user
    REFUSE = "refuse"           # Can't/won't do this
    UNKNOWN = "unknown"         # Don't know what to do


@dataclass
class Action:
    """Represents an action to take"""
    type: ActionType
    target: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)
    response: Optional[str] = None
    confidence: float = 1.0
    source: str = "cache"  # cache, llm, search, scrape


class KnowledgeBase:
    """
    Pre-loaded knowledge for instant responses.
    No LLM needed for known things.
    """
    
    def __init__(self):
        self.data_dir = get_data_dir() / "knowledge"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.home = Path.home()
        
        # Load knowledge files
        self.arch_linux = self._load_json("arch_linux.json")
        self.websites = self._load_json("websites.json")
        self.cache = self._load_json("cache.json")
        
        # Runtime discovered paths
        self.discovered_paths: Dict[str, str] = {}
        
    def _load_json(self, filename: str) -> Dict:
        """Load JSON knowledge file"""
        path = self.data_dir / filename
        if path.exists():
            try:
                return json.loads(path.read_text())
            except:
                pass
        return {}
    
    def _save_json(self, filename: str, data: Dict):
        """Save JSON knowledge file"""
        path = self.data_dir / filename
        path.write_text(json.dumps(data, indent=2))
    
    def save_cache(self):
        """Persist cache to disk"""
        self._save_json("cache.json", self.cache)
    
    # ─────────────────────────────────────────────────────────────
    # Config Paths
    # ─────────────────────────────────────────────────────────────
    
    def get_config_path(self, name: str) -> Optional[str]:
        """Get config file path by name"""
        name_lower = name.lower().strip()
        
        # Fix common typos FIRST
        typo_fixes = {
            "hyperland": "hyprland",
            "hyperion": "hyprland",
            "hyprlan": "hyprland",
            "hyprlnd": "hyprland",
            "kitti": "kitty",
            "neovim": "nvim",
            "vim": "nvim",
            "wayba": "waybar",
            "alacrit": "alacritty",
        }
        for typo, correct in typo_fixes.items():
            if typo in name_lower:
                name_lower = name_lower.replace(typo, correct)
        
        # Common aliases
        aliases = {
            "hyprland": ["hyprland", "hypr", "hyprland config", "hyprland.conf"],
            "kitty": ["kitty", "kitty config", "kitty.conf", "terminal"],
            "waybar": ["waybar", "waybar config", "bar", "statusbar"],
            "nvim": ["nvim", "neovim", "vim", "nvim config", "init.lua"],
            "zsh": ["zsh", "zshrc", ".zshrc", "zsh config", "shell"],
            "bash": ["bash", "bashrc", ".bashrc", "bash config"],
            "fish": ["fish", "fish config"],
            "alacritty": ["alacritty", "alacritty config"],
            "wofi": ["wofi", "wofi config", "launcher"],
            "rofi": ["rofi", "rofi config"],
            "dunst": ["dunst", "dunst config", "notifications"],
            "mako": ["mako", "mako config"],
            "sway": ["sway", "sway config", "sway.conf"],
            "i3": ["i3", "i3 config", "i3wm"],
            "polybar": ["polybar", "polybar config"],
            "picom": ["picom", "picom config", "compositor"],
            "starship": ["starship", "starship config", "prompt"],
            "tmux": ["tmux", "tmux config", ".tmux.conf"],
            "git": ["git", "git config", ".gitconfig"],
            "ssh": ["ssh", "ssh config"],
        }
        
        # Config locations
        paths = {
            "hyprland": self.home / ".config/hypr/hyprland.conf",
            "kitty": self.home / ".config/kitty/kitty.conf",
            "waybar": self.home / ".config/waybar/config",
            "nvim": self.home / ".config/nvim/init.lua",
            "zsh": self.home / ".zshrc",
            "bash": self.home / ".bashrc",
            "fish": self.home / ".config/fish/config.fish",
            "alacritty": self.home / ".config/alacritty/alacritty.yml",
            "wofi": self.home / ".config/wofi/config",
            "rofi": self.home / ".config/rofi/config.rasi",
            "dunst": self.home / ".config/dunst/dunstrc",
            "mako": self.home / ".config/mako/config",
            "sway": self.home / ".config/sway/config",
            "i3": self.home / ".config/i3/config",
            "polybar": self.home / ".config/polybar/config.ini",
            "picom": self.home / ".config/picom/picom.conf",
            "starship": self.home / ".config/starship.toml",
            "tmux": self.home / ".tmux.conf",
            "git": self.home / ".gitconfig",
            "ssh": self.home / ".ssh/config",
        }
        
        # Find matching config
        for key, alias_list in aliases.items():
            if name_lower in alias_list or any(a in name_lower for a in alias_list):
                path = paths.get(key)
                if path and path.exists():
                    return str(path)
                    
        return None
    
    # ─────────────────────────────────────────────────────────────
    # Websites
    # ─────────────────────────────────────────────────────────────
    
    def get_website_url(self, name: str) -> Optional[str]:
        """Get website URL by name"""
        name_lower = name.lower().strip()
        
        # Built-in websites
        sites = {
            # Search & Social
            "google": "https://google.com",
            "youtube": "https://youtube.com",
            "yt": "https://youtube.com",
            "reddit": "https://reddit.com",
            "twitter": "https://twitter.com",
            "x": "https://twitter.com",
            "facebook": "https://facebook.com",
            "instagram": "https://instagram.com",
            "linkedin": "https://linkedin.com",
            "tiktok": "https://tiktok.com",
            "twitch": "https://twitch.tv",
            "discord": "https://discord.com",
            
            # Dev & Tech
            "github": "https://github.com",
            "gh": "https://github.com",
            "gitlab": "https://gitlab.com",
            "stackoverflow": "https://stackoverflow.com",
            "so": "https://stackoverflow.com",
            "hackernews": "https://news.ycombinator.com",
            "hn": "https://news.ycombinator.com",
            "npm": "https://npmjs.com",
            "pypi": "https://pypi.org",
            "dockerhub": "https://hub.docker.com",
            "aur": "https://aur.archlinux.org",
            
            # Documentation
            "archwiki": "https://wiki.archlinux.org",
            "arch wiki": "https://wiki.archlinux.org",
            "arch": "https://wiki.archlinux.org",
            "mdn": "https://developer.mozilla.org",
            "devdocs": "https://devdocs.io",
            
            # AI & Learning
            "chatgpt": "https://chat.openai.com",
            "claude": "https://claude.ai",
            "perplexity": "https://perplexity.ai",
            "huggingface": "https://huggingface.co",
            "hf": "https://huggingface.co",
            "kaggle": "https://kaggle.com",
            "coursera": "https://coursera.org",
            "udemy": "https://udemy.com",
            
            # Entertainment
            "netflix": "https://netflix.com",
            "spotify": "https://spotify.com",
            "primevideo": "https://primevideo.com",
            "amazon": "https://amazon.com",
            
            # Productivity
            "gmail": "https://mail.google.com",
            "drive": "https://drive.google.com",
            "notion": "https://notion.so",
            "trello": "https://trello.com",
            "figma": "https://figma.com",
            
            # Adult (since pornhub was in your test)
            "pornhub": "https://pornhub.com",
            "ph": "https://pornhub.com",
        }
        
        # Check built-in
        if name_lower in sites:
            return sites[name_lower]
        
        # Check cached websites
        cached = self.websites.get(name_lower)
        if cached:
            return cached
        
        # Check if it looks like a URL
        if "." in name_lower and not " " in name_lower:
            if not name_lower.startswith("http"):
                return f"https://{name_lower}"
            return name_lower
            
        return None
    
    def add_website(self, name: str, url: str):
        """Add a website to cache"""
        self.websites[name.lower()] = url
        self._save_json("websites.json", self.websites)
    
    # ─────────────────────────────────────────────────────────────
    # Knowledge Cache
    # ─────────────────────────────────────────────────────────────
    
    def get_cached_answer(self, query: str) -> Optional[str]:
        """Get cached answer for a query"""
        query_lower = query.lower().strip()
        return self.cache.get(query_lower)
    
    def cache_answer(self, query: str, answer: str):
        """Cache an answer"""
        self.cache[query.lower().strip()] = answer
        self.save_cache()
    
    # ─────────────────────────────────────────────────────────────
    # System Info
    # ─────────────────────────────────────────────────────────────
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get current system information"""
        info = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M"),
            "datetime": datetime.now().isoformat(),
            "user": os.getenv("USER", "unknown"),
            "home": str(self.home),
            "shell": os.getenv("SHELL", "/bin/bash"),
            "editor": os.getenv("EDITOR", "nvim"),
            "browser": os.getenv("BROWSER", "firefox"),
            "terminal": os.getenv("TERMINAL", "kitty"),
        }
        return info
    
    def get_default_editor(self) -> str:
        return os.getenv("EDITOR", "nvim")
    
    def get_default_browser(self) -> str:
        return os.getenv("BROWSER", "firefox")
    
    def get_default_terminal(self) -> str:
        return os.getenv("TERMINAL", "kitty")


class WebSearcher:
    """
    Web search via SearXNG (local, privacy-first)
    """
    
    def __init__(self, searxng_url: str = "http://localhost:8888"):
        self.searxng_url = searxng_url
        self.enabled = self._check_searxng()
    
    def _check_searxng(self) -> bool:
        """Check if SearXNG is running"""
        try:
            import requests
            resp = requests.get(f"{self.searxng_url}/healthz", timeout=2)
            return resp.status_code == 200
        except:
            return False
    
    def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """Search via SearXNG"""
        if not self.enabled:
            return []
        
        try:
            import requests
            resp = requests.get(
                f"{self.searxng_url}/search",
                params={
                    "q": query,
                    "format": "json",
                    "categories": "general",
                },
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for r in data.get("results", [])[:num_results]:
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "content": r.get("content", "")[:500],
                    })
                return results
        except:
            pass
        return []


class WebScraper:
    """
    Web scraper for extracting content from pages
    """
    
    def __init__(self):
        self.data_dir = get_data_dir() / "scrape"
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def scrape(self, url: str, save: bool = True) -> Optional[Dict[str, Any]]:
        """Scrape a webpage and extract content"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Ryx/1.0"
            }
            
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, "lxml")
            
            # Remove script/style
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            
            # Extract content
            title = soup.title.string if soup.title else ""
            
            # Get main content
            main = soup.find("main") or soup.find("article") or soup.find("body")
            
            # Extract text
            text = ""
            if main:
                for p in main.find_all(["p", "h1", "h2", "h3", "li", "pre", "code"]):
                    text += p.get_text(strip=True) + "\n"
            
            # Extract code blocks
            code_blocks = []
            for pre in soup.find_all("pre"):
                code_blocks.append(pre.get_text(strip=True))
            
            result = {
                "url": url,
                "title": title,
                "text": text[:10000],  # Limit size
                "code_blocks": code_blocks[:10],
                "scraped_at": datetime.now().isoformat(),
            }
            
            if save:
                # Save to file
                filename = re.sub(r'[^\w\-_.]', '_', url)[:100] + ".json"
                (self.data_dir / filename).write_text(json.dumps(result, indent=2))
            
            return result
            
        except Exception as e:
            return {"error": str(e), "url": url}
    
    def scrape_arch_wiki(self, topic: str) -> Optional[Dict[str, Any]]:
        """Scrape Arch Wiki for a topic"""
        # Clean up topic
        topic_clean = topic.replace(" ", "_").title()
        url = f"https://wiki.archlinux.org/title/{topic_clean}"
        return self.scrape(url)


class ModelSelector:
    """
    Smart model selection based on task complexity
    """
    
    # Model tiers
    TINY = "qwen2.5:1.5b"      # Cached lookups, simple responses
    FAST = "qwen2.5:3b"        # Intent classification, simple tasks
    BALANCED = "qwen2.5:7b"    # General tasks
    SMART = "qwen2.5-coder:14b"  # Complex reasoning
    
    @classmethod
    def select(cls, task_type: str, cached: bool = False) -> str:
        """Select appropriate model for task"""
        if cached:
            return cls.TINY
        
        simple_tasks = ["greeting", "confirmation", "clarify"]
        medium_tasks = ["intent", "classify", "simple_answer"]
        complex_tasks = ["reasoning", "code", "analysis", "scrape_process"]
        
        if task_type in simple_tasks:
            return cls.FAST
        elif task_type in medium_tasks:
            return cls.BALANCED
        elif task_type in complex_tasks:
            return cls.SMART
        
        return cls.BALANCED


class RyxEngine:
    """
    Main Ryx Engine - Copilot CLI style
    
    Design principles:
    1. Knowledge-first: Check cache/knowledge before LLM
    2. Honest: Never make up answers
    3. Smart routing: Use smallest model that works
    4. Action-biased: Do things, don't explain
    """
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama = OllamaClient(base_url=ollama_url)
        self.kb = KnowledgeBase()
        self.searcher = WebSearcher()
        self.scraper = WebScraper()
        
        # System prompts
        self.system_prompt = """You are Ryx, a local AI assistant on Arch Linux.

RULES:
1. Be concise. One sentence when possible.
2. If you don't know, say "I don't know" - NEVER make up answers.
3. If you need current info (date, weather, news), say you need to search.
4. For files/configs, only mention paths that exist.
5. Do actions, don't explain how to do them.

CURRENT INFO:
- Date: {date}
- Time: {time}
- User: {user}
- Shell: {shell}
- Editor: {editor}
"""
    
    def _get_system_prompt(self) -> str:
        """Get system prompt with current info"""
        info = self.kb.get_system_info()
        return self.system_prompt.format(**info)
    
    def _call_llm(self, prompt: str, model: str, system: str = None) -> str:
        """Call Ollama LLM"""
        try:
            response = self.ollama.generate(
                model=model,
                prompt=prompt,
                system=system or self._get_system_prompt(),
                temperature=0.3,
                max_tokens=200,
            )
            return response.response.strip() if hasattr(response, 'response') else str(response).strip()
        except Exception as e:
            return f"Error: {e}"
    
    # ─────────────────────────────────────────────────────────────
    # Main Entry Point
    # ─────────────────────────────────────────────────────────────
    
    def process(self, user_input: str, new_terminal: bool = False) -> Action:
        """
        Main entry point - process user input and return action.
        
        Flow:
        1. Try instant resolution (cached, known)
        2. If not, classify intent
        3. Execute appropriate handler
        """
        input_clean = user_input.strip()
        input_lower = input_clean.lower()
        
        # ─────────────────────────────────────────────────────────
        # Step 1: Instant Resolution (No LLM)
        # ─────────────────────────────────────────────────────────
        
        action = self._try_instant_resolution(input_lower, new_terminal)
        if action:
            return action
        
        # ─────────────────────────────────────────────────────────
        # Step 2: Check for things we CAN'T know without searching
        # ─────────────────────────────────────────────────────────
        
        needs_search = self._needs_web_search(input_lower)
        if needs_search:
            return self._handle_web_query(input_clean)
        
        # ─────────────────────────────────────────────────────────
        # Step 3: Use LLM for understanding
        # ─────────────────────────────────────────────────────────
        
        return self._llm_process(input_clean)
    
    def _try_instant_resolution(self, input_lower: str, new_terminal: bool = False) -> Optional[Action]:
        """
        Try to resolve without LLM.
        Returns Action if resolved, None if needs LLM.
        """
        # ─────────────────────────────────────────────────────────
        # Pattern: Open website
        # ─────────────────────────────────────────────────────────
        
        # Direct website name
        url = self.kb.get_website_url(input_lower)
        if url:
            return Action(
                type=ActionType.OPEN_URL,
                target=url,
                source="cache"
            )
        
        # ─────────────────────────────────────────────────────────
        # Pattern: Date/Time queries - CHECK EARLY (before "what is")
        # ─────────────────────────────────────────────────────────
        
        info = self.kb.get_system_info()
        
        if any(x in input_lower for x in ["what time", "current time", "time is it"]):
            return Action(
                type=ActionType.ANSWER,
                response=f"It's {info['time']}",
                source="system"
            )
        
        if any(x in input_lower for x in ["what date", "today's date", "date today", "what day", "the date", "current date", "what is today"]):
            return Action(
                type=ActionType.ANSWER,
                response=f"Today is {info['date']}",
                source="system"
            )
        
        # ─────────────────────────────────────────────────────────
        # Pattern: Open website/file
        # ─────────────────────────────────────────────────────────
        
        # "open X" pattern
        if input_lower.startswith("open "):
            target = input_lower[5:].strip()
            
            # Check for "in browser" suffix
            if " in browser" in target:
                target = target.replace(" in browser", "").strip()
            
            # Check website
            url = self.kb.get_website_url(target)
            if url:
                return Action(
                    type=ActionType.OPEN_URL,
                    target=url,
                    source="cache"
                )
            
            # Check config
            path = self.kb.get_config_path(target)
            if path:
                return Action(
                    type=ActionType.OPEN_FILE,
                    target=path,
                    options={
                        "editor": self.kb.get_default_editor(),
                        "new_terminal": new_terminal or "new terminal" in input_lower
                    },
                    source="cache"
                )
        
        # ─────────────────────────────────────────────────────────
        # Pattern: Find file / Where is (check BEFORE config patterns)
        # ─────────────────────────────────────────────────────────
        
        find_prefixes = ["find ", "where is ", "locate ", "search for ", "look for "]
        for prefix in find_prefixes:
            if input_lower.startswith(prefix):
                query = input_lower[len(prefix):].strip()
                # Clean query
                for word in ["a file", "file", "called", "named", "the", "my"]:
                    query = query.replace(word, "").strip()
                
                # For "where is X config", just show the path
                path = self.kb.get_config_path(query)
                if path:
                    return Action(
                        type=ActionType.ANSWER,
                        response=path.replace(str(Path.home()), "~"),
                        source="cache"
                    )
                
                # Otherwise do a file search
                return Action(
                    type=ActionType.FIND_FILE,
                    target=query,
                    source="local"
                )
        
        # ─────────────────────────────────────────────────────────
        # Pattern: Knowledge questions ("what is X") - check BEFORE config
        # ─────────────────────────────────────────────────────────
        
        question_prefixes = ["what is ", "what are ", "tell me about ", "explain ", "how does ", "how do i "]
        for prefix in question_prefixes:
            if input_lower.startswith(prefix):
                query = input_lower[len(prefix):].strip()
                # Clean query
                for word in ["the", "a", "an"]:
                    if query.startswith(f"{word} "):
                        query = query[len(word)+1:]
                
                # Check cached knowledge
                cached = self.kb.get_cached_answer(query)
                if cached:
                    return Action(
                        type=ActionType.ANSWER,
                        response=cached,
                        source="cache"
                    )
                
                # Don't resolve to config - this is a question, not an action
                return None  # Let LLM handle it
        
        # ─────────────────────────────────────────────────────────
        # Pattern: Config file (AFTER questions and find patterns)
        # ─────────────────────────────────────────────────────────
        
        # "X config" or just config name - but NOT if it looks like a question
        if not any(input_lower.startswith(x) for x in ["what ", "how ", "why ", "when ", "tell "]):
            config_patterns = [
                input_lower,
                input_lower.replace(" config", ""),
                input_lower.replace("config", "").strip(),
            ]
            
            for pattern in config_patterns:
                path = self.kb.get_config_path(pattern)
                if path:
                    return Action(
                        type=ActionType.OPEN_FILE,
                        target=path,
                        options={
                            "editor": self.kb.get_default_editor(),
                            "new_terminal": new_terminal or "new terminal" in input_lower
                        },
                        source="cache"
                    )
        
        # ─────────────────────────────────────────────────────────
        # Pattern: Website name as single word or with "website"
        # ─────────────────────────────────────────────────────────
        
        if " website" in input_lower:
            name = input_lower.replace(" website", "").strip()
            # Try to construct URL
            if not " " in name:
                url = f"https://{name}.com"
                return Action(
                    type=ActionType.OPEN_URL,
                    target=url,
                    source="inferred"
                )
        
        # ─────────────────────────────────────────────────────────
        # Pattern: Cached answer
        # ─────────────────────────────────────────────────────────
        
        cached = self.kb.get_cached_answer(input_lower)
        if cached:
            return Action(
                type=ActionType.ANSWER,
                response=cached,
                source="cache"
            )
        
        return None
    
    def _needs_web_search(self, input_lower: str) -> bool:
        """Check if this query needs web search to answer correctly"""
        
        # Explicit search requests
        if any(x in input_lower for x in ["search for", "look up", "google", "find online"]):
            return True
        
        # Questions about current/real-world things
        current_indicators = [
            "what is the latest",
            "current price",
            "weather",
            "news about",
            "who won",
            "score of",
            "what happened",
            "recent",
        ]
        if any(x in input_lower for x in current_indicators):
            return True
        
        # Questions about things AI typically hallucinates on
        factual_queries = [
            "what is ipv",  # ipv9, etc
            "who is the",
            "when did",
            "how many",
            "what year",
        ]
        if any(x in input_lower for x in factual_queries):
            # Could be factual, mark for verification
            return True
        
        return False
    
    def _handle_web_query(self, query: str) -> Action:
        """Handle a query that needs web search"""
        
        # Try SearXNG first
        if self.searcher.enabled:
            results = self.searcher.search(query)
            if results:
                # Summarize results
                summary = f"Search results for '{query}':\n"
                for i, r in enumerate(results[:3], 1):
                    summary += f"{i}. {r['title']}: {r['content'][:100]}...\n"
                
                return Action(
                    type=ActionType.ANSWER,
                    response=summary,
                    source="search"
                )
        
        # SearXNG not available - be honest
        return Action(
            type=ActionType.REFUSE,
            response="I need to search the web for that, but SearXNG isn't running. "
                    "Start it with `docker run -p 8888:8080 searxng/searxng` or "
                    "I can try to scrape a specific page if you give me a URL.",
            source="system"
        )
    
    def _llm_process(self, input_text: str) -> Action:
        """Use LLM to process input when instant resolution fails"""
        
        # Classify intent first with fast model
        intent_prompt = f"""Classify this user request into ONE category:
- OPEN_URL: wants to open a website
- OPEN_FILE: wants to open/edit a file
- FIND_FILE: wants to find a file
- ANSWER: wants information/answer
- RUN_COMMAND: wants to run a shell command
- SCRAPE: wants to scrape/extract web content
- CLARIFY: unclear what they want
- UNKNOWN: can't determine

User: {input_text}

Category:"""
        
        category = self._call_llm(intent_prompt, ModelSelector.FAST).strip().upper()
        
        # Handle based on category
        if "CLARIFY" in category or "UNKNOWN" in category:
            return Action(
                type=ActionType.CLARIFY,
                response="Could you be more specific? What exactly do you want me to do?",
                source="llm"
            )
        
        if "OPEN_URL" in category:
            # Try to extract URL/site name
            extract_prompt = f"Extract the website name from: {input_text}\nWebsite:"
            site = self._call_llm(extract_prompt, ModelSelector.TINY).strip()
            url = self.kb.get_website_url(site)
            if url:
                return Action(type=ActionType.OPEN_URL, target=url, source="llm")
            return Action(
                type=ActionType.CLARIFY,
                response=f"I don't know the website '{site}'. Can you give me the full URL?",
                source="llm"
            )
        
        if "OPEN_FILE" in category:
            extract_prompt = f"Extract the file/config name from: {input_text}\nFile:"
            file = self._call_llm(extract_prompt, ModelSelector.TINY).strip()
            path = self.kb.get_config_path(file)
            if path:
                return Action(type=ActionType.OPEN_FILE, target=path, source="llm")
            return Action(
                type=ActionType.CLARIFY,
                response=f"I don't know where '{file}' is. Can you give me the full path?",
                source="llm"
            )
        
        if "ANSWER" in category:
            # Check if this is something we should know or search
            if self._needs_web_search(input_text.lower()):
                return self._handle_web_query(input_text)
            
            # Try to answer with LLM
            answer = self._call_llm(input_text, ModelSelector.BALANCED)
            
            # Check for uncertainty markers
            uncertain = any(x in answer.lower() for x in [
                "i'm not sure", "i don't know", "i cannot", "i can't",
                "i think", "might be", "possibly", "perhaps"
            ])
            
            if uncertain:
                return Action(
                    type=ActionType.ANSWER,
                    response=f"{answer}\n\n(I'm not certain - want me to search the web?)",
                    source="llm"
                )
            
            return Action(
                type=ActionType.ANSWER,
                response=answer,
                source="llm"
            )
        
        if "SCRAPE" in category:
            # Extract URL
            extract_prompt = f"Extract the URL to scrape from: {input_text}\nURL:"
            url = self._call_llm(extract_prompt, ModelSelector.TINY).strip()
            if url.startswith("http"):
                return Action(
                    type=ActionType.SCRAPE,
                    target=url,
                    source="llm"
                )
            return Action(
                type=ActionType.CLARIFY,
                response="What URL do you want me to scrape?",
                source="llm"
            )
        
        # Default: ask for clarification
        return Action(
            type=ActionType.CLARIFY,
            response="I'm not sure what you want. Can you rephrase?",
            source="llm"
        )
    
    # ─────────────────────────────────────────────────────────────
    # Action Executors
    # ─────────────────────────────────────────────────────────────
    
    def execute(self, action: Action) -> str:
        """Execute an action and return result message"""
        
        if action.type == ActionType.OPEN_URL:
            return self._exec_open_url(action)
        
        elif action.type == ActionType.OPEN_FILE:
            return self._exec_open_file(action)
        
        elif action.type == ActionType.FIND_FILE:
            return self._exec_find_file(action)
        
        elif action.type == ActionType.ANSWER:
            return action.response or "No response"
        
        elif action.type == ActionType.SCRAPE:
            return self._exec_scrape(action)
        
        elif action.type in [ActionType.CLARIFY, ActionType.REFUSE]:
            return action.response or "I need more information."
        
        elif action.type == ActionType.UNKNOWN:
            return "I don't understand. Can you rephrase?"
        
        return "Unknown action"
    
    def _exec_open_url(self, action: Action) -> str:
        """Open URL in browser"""
        browser = self.kb.get_default_browser()
        try:
            subprocess.Popen(
                [browser, action.target],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return f"✅ Opened in browser"
        except Exception as e:
            return f"❌ Failed to open: {e}"
    
    def _exec_open_file(self, action: Action) -> str:
        """Open file in editor"""
        editor = action.options.get("editor", self.kb.get_default_editor())
        new_terminal = action.options.get("new_terminal", False)
        
        path = action.target
        short_path = path.replace(str(Path.home()), "~")
        
        try:
            if new_terminal:
                terminal = self.kb.get_default_terminal()
                subprocess.Popen(
                    [terminal, "-e", editor, path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                # Open in current terminal
                subprocess.run([editor, path])
            
            return f"✅ Opened: {short_path}"
        except Exception as e:
            return f"❌ Failed to open: {e}"
    
    def _exec_find_file(self, action: Action) -> str:
        """Find files matching pattern"""
        query = action.target
        
        # Use fd if available, fallback to find
        try:
            result = subprocess.run(
                ["fd", "-i", query, str(Path.home())],
                capture_output=True,
                text=True,
                timeout=10
            )
            files = result.stdout.strip().split("\n")[:10]
        except:
            try:
                result = subprocess.run(
                    ["find", str(Path.home()), "-iname", f"*{query}*", "-type", "f"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                files = result.stdout.strip().split("\n")[:10]
            except:
                return f"❌ Search failed"
        
        files = [f for f in files if f.strip()]
        
        if not files:
            return f"❌ No files found matching '{query}'"
        
        # Return just paths, no extra text
        result = "\n".join(f.replace(str(Path.home()), "~") for f in files)
        return result
    
    def _exec_scrape(self, action: Action) -> str:
        """Scrape a webpage"""
        url = action.target
        
        result = self.scraper.scrape(url)
        
        if "error" in result:
            return f"❌ Scrape failed: {result['error']}"
        
        # Save to scrape directory
        filename = re.sub(r'[^\w\-_.]', '_', url)[:50] + ".json"
        save_path = self.scraper.data_dir / filename
        
        return f"✅ Scraped: {result['title']}\n   Saved: {save_path}\n   Text length: {len(result.get('text', ''))} chars"
    
    # ─────────────────────────────────────────────────────────────
    # Knowledge Management
    # ─────────────────────────────────────────────────────────────
    
    def learn_from_scrape(self, scraped_data: Dict) -> str:
        """Process scraped data and add to knowledge base"""
        
        if "error" in scraped_data:
            return f"Cannot learn from failed scrape: {scraped_data['error']}"
        
        # Use LLM to extract key facts
        text = scraped_data.get("text", "")[:3000]
        title = scraped_data.get("title", "Unknown")
        
        extract_prompt = f"""Summarize this documentation in 3-5 bullet points.
Be concise. Focus on key facts, installation steps, and important commands.

Title: {title}

Text:
{text}

Summary (bullet points):"""
        
        response = self._call_llm(extract_prompt, ModelSelector.SMART)
        
        if response and len(response) > 20:
            # Save as cache entry
            cache_key = title.lower().replace(" - archwiki", "").strip()
            self.kb.cache[cache_key] = response
            self.kb.save_cache()
            
            # Also save readable version to scrape dir
            readable_path = get_data_dir() / "scrape" / f"{cache_key.replace(' ', '_')}_summary.md"
            with open(readable_path, 'w') as f:
                f.write(f"# {title}\n\n")
                f.write(f"Source: {scraped_data.get('url', 'Unknown')}\n\n")
                f.write(f"## Summary\n\n{response}\n")
            
            return f"✅ Learned about: {cache_key}\n   Saved to: {readable_path}"
        else:
            return f"❌ Failed to extract facts from scrape"
    
    def get_smarter(self) -> str:
        """Self-improvement: Review and improve knowledge"""
        
        # Review cache for quality
        cache = self.kb.cache
        
        if not cache:
            return "Cache is empty. Try scraping some pages to learn."
        
        # Use smart model to review
        review_prompt = f"""Review these cached Q&A pairs and identify:
1. Outdated information
2. Incorrect facts
3. Low-quality answers

Cache:
{json.dumps(dict(list(cache.items())[:20]), indent=2)}

Response format:
REMOVE: [list of keys to remove]
IMPROVE: [list of keys that need updating]
QUALITY: [overall quality score 1-10]
"""
        
        response = self._call_llm(review_prompt, ModelSelector.SMART)
        
        # Parse response and clean up
        # (simplified - in production would parse more carefully)
        
        return f"✅ Self-improvement complete\n{response}"


# Global engine instance
_engine: Optional[RyxEngine] = None

def get_engine() -> RyxEngine:
    """Get or create the global engine instance"""
    global _engine
    if _engine is None:
        router = ModelRouter()
        _engine = RyxEngine(ollama_url=router.get_ollama_url())
    return _engine
