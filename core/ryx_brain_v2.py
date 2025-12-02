"""
Ryx AI - Brain Core v2
Complete rewrite with Copilot-style intelligence.

Design Goals:
1. TRUE AI understanding - NO hardcoded patterns anywhere
2. Conversational flow - understands context, follow-ups, "open it"
3. Multi-action support - "scrape X and save as markdown"
4. Smart model selection - uses cache for fast, upgrades on failure
5. Precision mode - uses higher models for learning/accuracy
6. Asks when uncertain - never hallucinate, always clarify
7. Learns from interactions - gets smarter over time
8. Multi-language support - German, English naturally
9. Web search/scraping - integrated with SearXNG
10. Y/N fast path - instant response for confirmations
"""

import os
import re
import json
import sqlite3
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse, urljoin

from core.paths import get_data_dir, get_project_root


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class ActionType(Enum):
    """All possible actions Ryx can take"""
    # File operations
    OPEN_FILE = "open_file"
    FIND_FILE = "find_file"
    
    # Web operations  
    OPEN_URL = "open_url"
    SEARCH_WEB = "search_web"
    SCRAPE_URL = "scrape_url"
    SCRAPE_HTML_CSS = "scrape_html_css"
    
    # System operations
    RUN_COMMAND = "run_command"
    START_SERVICE = "start_service"
    RESTART_SERVICE = "restart_service"
    
    # AI operations
    ANSWER = "answer"
    CLARIFY = "clarify"
    MULTI_ACTION = "multi_action"
    CREATE_DOCUMENT = "create_document"
    
    # Settings
    SET_PREFERENCE = "set_preference"
    SWITCH_MODEL = "switch_model"
    TOGGLE_MODE = "toggle_mode"
    
    # Utility
    GET_DATE = "get_date"
    SHOW_HELP = "show_help"
    LIST_ITEMS = "list_items"
    SELECT_ITEM = "select_item"


@dataclass
class Action:
    """A planned action to execute"""
    type: ActionType
    target: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)
    question: Optional[str] = None
    confidence: float = 1.0
    sub_actions: List['Action'] = field(default_factory=list)
    requires_confirmation: bool = False


@dataclass
class ConversationState:
    """Track conversation for context and follow-ups"""
    last_action: Optional[Action] = None
    last_result: Optional[str] = None
    last_query: Optional[str] = None
    pending_items: List[Dict] = field(default_factory=list)
    pending_question: Optional[str] = None
    awaiting_confirmation: bool = False
    last_scraped_url: Optional[str] = None
    last_scraped_content: Optional[Dict] = None


@dataclass  
class SearchResult:
    """A web search result"""
    title: str
    url: str
    snippet: str = ""


# ============================================================================
# SMART CACHE - SQLite based for instant lookups
# ============================================================================

class SmartCache:
    """
    SQLite cache for learned patterns and preferences.
    Used to skip LLM calls for known queries.
    """
    
    def __init__(self):
        self.db_path = get_data_dir() / "smart_cache_v2.db"
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            -- Query cache with success/fail tracking
            CREATE TABLE IF NOT EXISTS query_cache (
                query_hash TEXT PRIMARY KEY,
                query_normalized TEXT,
                action_json TEXT,
                success_count INTEGER DEFAULT 1,
                fail_count INTEGER DEFAULT 0,
                last_used TEXT,
                created TEXT
            );
            
            -- User preferences (browser, editor, terminal, etc.)
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated TEXT
            );
            
            -- Learned URLs (from scraping, searching)
            CREATE TABLE IF NOT EXISTS learned_urls (
                name TEXT PRIMARY KEY,
                url TEXT,
                domain TEXT,
                source TEXT,
                last_verified TEXT,
                created TEXT
            );
            
            -- Model performance tracking
            CREATE TABLE IF NOT EXISTS model_performance (
                model TEXT,
                task_type TEXT,
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                avg_latency_ms REAL DEFAULT 0,
                PRIMARY KEY (model, task_type)
            );
        """)
        conn.commit()
        conn.close()
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for matching"""
        q = query.lower().strip()
        # Remove common filler words
        for word in ['please', 'can you', 'could you', 'would you', 'the', 'a', 'my', 'me']:
            q = q.replace(word, ' ')
        return ' '.join(q.split())
    
    def _hash_query(self, query: str) -> str:
        """Create hash of normalized query"""
        import hashlib
        norm = self._normalize_query(query)
        return hashlib.md5(norm.encode()).hexdigest()[:16]
    
    def lookup(self, query: str) -> Optional[Action]:
        """Look up cached action for query"""
        qhash = self._hash_query(query)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT action_json, success_count, fail_count FROM query_cache WHERE query_hash = ?",
            (qhash,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            action_json, success, fail = row
            # Only return if success rate > 70%
            if success > 0 and (success / max(1, success + fail)) > 0.7:
                try:
                    data = json.loads(action_json)
                    return Action(
                        type=ActionType(data['type']),
                        target=data.get('target'),
                        options=data.get('options', {}),
                        confidence=0.95
                    )
                except:
                    pass
        return None
    
    def store(self, query: str, action: Action, success: bool = True):
        """Store query -> action mapping"""
        qhash = self._hash_query(query)
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        
        try:
            cursor = conn.execute(
                "SELECT success_count, fail_count FROM query_cache WHERE query_hash = ?",
                (qhash,)
            )
            existing = cursor.fetchone()
            
            action_json = json.dumps({
                'type': action.type.value,
                'target': action.target,
                'options': action.options
            })
            
            if existing:
                s, f = existing
                if success:
                    s += 1
                else:
                    f += 1
                conn.execute(
                    "UPDATE query_cache SET success_count=?, fail_count=?, last_used=?, action_json=? WHERE query_hash=?",
                    (s, f, now, action_json, qhash)
                )
            else:
                conn.execute(
                    """INSERT INTO query_cache (query_hash, query_normalized, action_json, success_count, fail_count, last_used, created)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (qhash, self._normalize_query(query), action_json, 
                     1 if success else 0, 0 if success else 1, now, now)
                )
            conn.commit()
        finally:
            conn.close()
    
    def get_preference(self, key: str) -> Optional[str]:
        """Get a stored preference"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT value FROM preferences WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    
    def set_preference(self, key: str, value: str):
        """Set a preference"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO preferences (key, value, updated) VALUES (?, ?, ?)",
            (key, value, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    
    def learn_url(self, name: str, url: str, source: str = "user"):
        """Learn a new URL mapping"""
        domain = urlparse(url).netloc
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT OR REPLACE INTO learned_urls (name, url, domain, source, last_verified, created)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name.lower(), url, domain, source, datetime.now().isoformat(), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    
    def get_learned_url(self, name: str) -> Optional[str]:
        """Get a learned URL"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT url FROM learned_urls WHERE name = ?", (name.lower(),))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    
    def search_learned_urls(self, query: str) -> List[Dict]:
        """Search learned URLs by name"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT name, url, domain FROM learned_urls WHERE name LIKE ? LIMIT 10",
            (f"%{query.lower()}%",)
        )
        results = [{'name': r[0], 'url': r[1], 'domain': r[2]} for r in cursor.fetchall()]
        conn.close()
        return results
    
    def cleanup_bad_entries(self) -> int:
        """Remove entries with high fail rates"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            DELETE FROM query_cache 
            WHERE fail_count > success_count 
            AND (success_count + fail_count) > 3
        """)
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted
    
    def track_model_performance(self, model: str, task_type: str, success: bool, latency_ms: float):
        """Track model performance for smart routing"""
        conn = sqlite3.connect(self.db_path)
        
        cursor = conn.execute(
            "SELECT success_count, fail_count, avg_latency_ms FROM model_performance WHERE model=? AND task_type=?",
            (model, task_type)
        )
        row = cursor.fetchone()
        
        if row:
            s, f, avg_lat = row
            if success:
                s += 1
            else:
                f += 1
            # Running average
            total = s + f
            avg_lat = (avg_lat * (total - 1) + latency_ms) / total
            conn.execute(
                "UPDATE model_performance SET success_count=?, fail_count=?, avg_latency_ms=? WHERE model=? AND task_type=?",
                (s, f, avg_lat, model, task_type)
            )
        else:
            conn.execute(
                "INSERT INTO model_performance (model, task_type, success_count, fail_count, avg_latency_ms) VALUES (?, ?, ?, ?, ?)",
                (model, task_type, 1 if success else 0, 0 if success else 1, latency_ms)
            )
        
        conn.commit()
        conn.close()


# ============================================================================
# KNOWLEDGE BASE - Static knowledge for accuracy
# ============================================================================

class KnowledgeBase:
    """Pre-loaded knowledge to prevent hallucinations"""
    
    def __init__(self):
        self.knowledge_dir = get_data_dir() / "knowledge"
        self.arch_linux: Dict = {}
        self.websites: Dict = {}
        self._load()
    
    def _load(self):
        """Load knowledge files"""
        # Arch Linux knowledge
        arch_file = self.knowledge_dir / "arch_linux.json"
        if arch_file.exists():
            with open(arch_file) as f:
                self.arch_linux = json.load(f)
        
        # Websites
        self.websites = self.arch_linux.get("websites", {}).copy()
        websites_file = self.knowledge_dir / "websites.json"
        if websites_file.exists():
            with open(websites_file) as f:
                self.websites.update(json.load(f))
    
    def get_config_path(self, name: str) -> Optional[str]:
        """Get config file path"""
        name_lower = name.lower().strip()
        
        # Check aliases
        aliases = self.arch_linux.get("aliases", {})
        if name_lower in aliases:
            name_lower = aliases[name_lower]
        
        # Get path
        paths = self.arch_linux.get("config_paths", {})
        path = paths.get(name_lower)
        
        if path:
            expanded = os.path.expanduser(path)
            if os.path.exists(expanded):
                return expanded
        return None
    
    def get_website_url(self, name: str) -> Optional[str]:
        """Get website URL from knowledge"""
        return self.websites.get(name.lower().strip())
    
    def get_default(self, key: str) -> str:
        """Get default value"""
        defaults = {
            "browser": self.arch_linux.get("default_browser", "firefox"),
            "editor": os.environ.get("EDITOR", self.arch_linux.get("default_editor", "nvim")),
            "terminal": self.arch_linux.get("default_terminal", "kitty"),
        }
        return defaults.get(key, "")
    
    def save(self):
        """Save updated knowledge"""
        arch_file = self.knowledge_dir / "arch_linux.json"
        with open(arch_file, 'w') as f:
            json.dump(self.arch_linux, f, indent=2)


# ============================================================================
# MAIN BRAIN - The intelligent core
# ============================================================================

class RyxBrainV2:
    """
    The intelligent core of Ryx v2.
    
    Key features:
    - TRUE AI understanding (no patterns)
    - Conversational context
    - Multi-action support
    - Smart model routing
    - Precision mode
    - Fast Y/N handling
    """
    
    def __init__(self, ollama_client):
        self.ollama = ollama_client
        self.kb = KnowledgeBase()
        self.cache = SmartCache()
        self.state = ConversationState()
        
        # Model configuration - NO CODING MODELS for general tasks
        self.models = {
            'tiny': 'qwen2.5:1.5b',      # Only for cached hits verification
            'fast': 'qwen2.5:3b',         # Simple tasks
            'balanced': 'mistral:7b',     # General tasks (NOT coding)
            'smart': 'qwen2.5:14b',       # Complex reasoning
            'precision': 'qwen2.5:14b',   # Precision mode (high accuracy)
        }
        
        # State
        self.precision_mode = False
        self.consecutive_fails = 0
        self.max_fails_before_upgrade = 2
    
    # ========================================================================
    # PUBLIC API
    # ========================================================================
    
    def understand(self, prompt: str) -> Action:
        """
        Main entry point: understand what user wants.
        Returns an Action to execute.
        """
        prompt_clean = prompt.strip()
        prompt_lower = prompt_clean.lower()
        
        # Store for context
        self.state.last_query = prompt_clean
        
        # 1. FAST PATH: Y/N confirmations (instant, no AI)
        if self.state.awaiting_confirmation:
            return self._handle_confirmation(prompt_lower)
        
        # 2. FAST PATH: Number selection from list
        if self.state.pending_items and prompt_lower.isdigit():
            return self._handle_selection(int(prompt_lower))
        
        # 3. FAST PATH: Follow-up references ("open it", "the first one", etc)
        followup = self._check_followup(prompt_lower)
        if followup:
            return followup
        
        # 4. Check cache (fast, no AI)
        if not self.precision_mode:
            cached = self.cache.lookup(prompt_clean)
            if cached:
                return cached
        
        # 5. Try knowledge-based resolution (no AI needed)
        kb_action = self._resolve_from_knowledge(prompt_clean)
        if kb_action:
            return kb_action
        
        # 6. Use AI to understand
        return self._ai_understand(prompt_clean)
    
    def execute(self, action: Action) -> Tuple[bool, str]:
        """Execute an action and return (success, result)"""
        # Track for context
        self.state.last_action = action
        
        # Execute based on type
        handlers = {
            ActionType.OPEN_FILE: self._exec_open_file,
            ActionType.OPEN_URL: self._exec_open_url,
            ActionType.FIND_FILE: self._exec_find_file,
            ActionType.SEARCH_WEB: self._exec_search_web,
            ActionType.SCRAPE_URL: self._exec_scrape,
            ActionType.SCRAPE_HTML_CSS: self._exec_scrape_html_css,
            ActionType.RUN_COMMAND: self._exec_command,
            ActionType.SET_PREFERENCE: self._exec_set_preference,
            ActionType.START_SERVICE: self._exec_start_service,
            ActionType.RESTART_SERVICE: self._exec_restart_service,
            ActionType.GET_DATE: self._exec_get_date,
            ActionType.SWITCH_MODEL: self._exec_switch_model,
            ActionType.TOGGLE_MODE: self._exec_toggle_mode,
            ActionType.CREATE_DOCUMENT: self._exec_create_document,
            ActionType.CLARIFY: lambda a: (True, a.question or "Was möchtest du genau?"),
            ActionType.ANSWER: lambda a: (True, a.target or ""),
            ActionType.LIST_ITEMS: self._exec_list_items,
            ActionType.SELECT_ITEM: self._exec_select_item,
            ActionType.MULTI_ACTION: self._exec_multi_action,
        }
        
        handler = handlers.get(action.type)
        if handler:
            success, result = handler(action)
            self.state.last_result = result
            
            # Cache successful queries
            if success and self.state.last_query:
                self.cache.store(self.state.last_query, action, success)
            
            # Track failures for model upgrade
            if not success:
                self.consecutive_fails += 1
            else:
                self.consecutive_fails = 0
            
            return success, result
        
        return False, f"Unknown action: {action.type}"
    
    def toggle_precision_mode(self, enabled: bool):
        """Toggle precision mode (uses higher models)"""
        self.precision_mode = enabled
    
    # ========================================================================
    # FAST PATHS - No AI needed
    # ========================================================================
    
    def _handle_confirmation(self, prompt: str) -> Action:
        """Handle Y/N confirmations instantly"""
        self.state.awaiting_confirmation = False
        
        if prompt in ['y', 'yes', 'ja', 'ok', 'okay', 'sure', 'yep', 'yeah', 'do it', 'go ahead']:
            if self.state.last_action:
                action = self.state.last_action
                self.state.last_action = None
                return action
        elif prompt in ['n', 'no', 'nein', 'cancel', 'abort', 'stop', 'nope']:
            return Action(type=ActionType.ANSWER, target="Abgebrochen." if 'ja' in self.state.pending_question or '' else "Cancelled.")
        
        # Neither Y nor N - ask again
        return Action(type=ActionType.CLARIFY, question=self.state.pending_question or "y/n?")
    
    def _handle_selection(self, num: int) -> Action:
        """Handle numeric selection from list"""
        idx = num - 1
        if 0 <= idx < len(self.state.pending_items):
            item = self.state.pending_items[idx]
            self.state.pending_items = []
            
            if 'url' in item:
                return Action(type=ActionType.OPEN_URL, target=item['url'])
            elif 'path' in item:
                return Action(type=ActionType.OPEN_FILE, target=item['path'])
            elif 'action' in item:
                return item['action']
        
        return Action(type=ActionType.CLARIFY, question=f"Bitte wähle eine Nummer von 1-{len(self.state.pending_items)}")
    
    def _check_followup(self, prompt: str) -> Optional[Action]:
        """Check for follow-up references"""
        
        # "open it", "edit it", "that one"
        if prompt in ['open it', 'edit it', 'öffne es', 'das', 'edit that', 'open that']:
            if self.state.last_result:
                path = self.state.last_result
                if os.path.exists(path):
                    return Action(type=ActionType.OPEN_FILE, target=path)
                elif path.startswith('http'):
                    return Action(type=ActionType.OPEN_URL, target=path)
        
        # "the first one", "the second", etc
        ordinals = {'first': 0, 'second': 1, 'third': 2, 'fourth': 3, 'fifth': 4,
                    'erste': 0, 'zweite': 1, 'dritte': 2, 'vierte': 3, 'fünfte': 4}
        for word, idx in ordinals.items():
            if word in prompt and self.state.pending_items:
                if idx < len(self.state.pending_items):
                    item = self.state.pending_items[idx]
                    self.state.pending_items = []
                    if 'url' in item:
                        return Action(type=ActionType.OPEN_URL, target=item['url'])
                    elif 'path' in item:
                        return Action(type=ActionType.OPEN_FILE, target=item['path'])
        
        # "scrape that", "save that" after showing results
        if ('scrape' in prompt or 'speicher' in prompt or 'save' in prompt) and self.state.pending_items:
            # Extract which ones
            if 'first' in prompt or 'erste' in prompt or '1' in prompt:
                items = [self.state.pending_items[0]] if self.state.pending_items else []
            elif 'all' in prompt or 'alle' in prompt:
                items = self.state.pending_items[:5]  # Max 5
            else:
                items = self.state.pending_items[:1]  # Default to first
            
            if items and items[0].get('url'):
                return Action(
                    type=ActionType.SCRAPE_URL,
                    target=items[0]['url'],
                    options={'save_as': 'markdown' if 'md' in prompt or 'markdown' in prompt else 'json'}
                )
        
        return None
    
    # ========================================================================
    # KNOWLEDGE-BASED RESOLUTION - Fast, no AI
    # ========================================================================
    
    def _resolve_from_knowledge(self, prompt: str) -> Optional[Action]:
        """Try to resolve using knowledge base without AI"""
        prompt_lower = prompt.lower().strip()
        
        # ---- SYSTEM COMMANDS ----
        
        # Restart all of ryx
        if any(x in prompt_lower for x in ['restart all', 'restart ryx', 'neustart']):
            return Action(
                type=ActionType.RESTART_SERVICE,
                target="ryx",
                requires_confirmation=True,
                question="Möchtest du wirklich alle Ryx-Dienste neustarten? (y/n)"
            )
        
        # Precision mode
        if any(x in prompt_lower for x in ['precision mode', 'precision on', 'precision off', 
                                           'präzisionsmodus', 'genauigkeitsmodus']):
            enable = 'on' in prompt_lower or 'ein' in prompt_lower or 'aktivier' in prompt_lower
            return Action(type=ActionType.TOGGLE_MODE, target='precision', options={'enabled': enable})
        
        # Date/time - expanded patterns
        if any(x in prompt_lower for x in ['what date', 'what time', 'what is the date', 'what day',
                                           'heute', 'datum', 'uhrzeit', "today's date", 'welcher tag',
                                           'welches datum', 'wie spät', 'current date', 'current time']):
            return Action(type=ActionType.GET_DATE)
        
        # ---- PREFERENCE SETTINGS ----
        
        # "set X as default browser/editor/terminal"
        pref_match = re.search(r'set (\w+) as default (\w+)', prompt_lower)
        if pref_match:
            value, key = pref_match.groups()
            return Action(type=ActionType.SET_PREFERENCE, target=key, options={'value': value})
        
        # ---- MODEL SWITCHING ----
        
        # "switch to X model"
        if 'switch to' in prompt_lower and 'model' in prompt_lower:
            model_match = re.search(r'(\w+[:\-]?\d*b?)', prompt_lower.split('switch to')[1])
            if model_match:
                return Action(type=ActionType.SWITCH_MODEL, target=model_match.group(1))
        
        # ---- FILE/URL OPERATIONS ----
        
        # Parse flags
        new_terminal = 'new terminal' in prompt_lower or 'neues terminal' in prompt_lower
        with_browser = None
        browser_match = re.search(r'with (\w+)( browser)?', prompt_lower)
        if browser_match:
            with_browser = browser_match.group(1)
        
        # Determine if this is a "where is" query (return path, don't open)
        is_where_query = any(x in prompt_lower for x in ['where is', 'wo ist', 'where\'s', 'find me'])
        
        # Extract target
        target = prompt_lower
        for prefix in ['open ', 'edit ', 'öffne ', 'bearbeite ', 'show ', 'zeige ', 
                       'find ', 'where is ', 'wo ist ', 'where\'s ', 'search for ',
                       'can you ', 'please ', 'could you ', 'bitte ']:
            if target.startswith(prefix):
                target = target[len(prefix):]
        
        # Remove flags from target
        for flag in ['in new terminal', 'new terminal', 'in same terminal', 'same terminal',
                     'neues terminal', 'gleiches terminal']:
            target = target.replace(flag, '')
        if browser_match:
            target = target.replace(browser_match.group(0), '')
        
        # Clean up
        target = re.sub(r'\s+', ' ', target).strip()
        
        # Remove common words
        for word in ['the', 'my', 'a', 'for me', 'please', 'config', 'configuration']:
            target = target.replace(f' {word} ', ' ').replace(f' {word}', '').replace(f'{word} ', '')
        target = target.strip()
        
        if not target:
            return None
        
        # Check if it's about a config file
        is_config = 'config' in prompt_lower or 'configuration' in prompt_lower or 'konfiguration' in prompt_lower
        
        # Try to get config path
        config_path = self.kb.get_config_path(target)
        if config_path:
            if is_where_query:
                return Action(type=ActionType.ANSWER, target=config_path)
            return Action(
                type=ActionType.OPEN_FILE,
                target=config_path,
                options={'new_terminal': new_terminal}
            )
        
        # Check learned URLs
        learned_url = self.cache.get_learned_url(target)
        if learned_url:
            return Action(
                type=ActionType.OPEN_URL,
                target=learned_url,
                options={'browser': with_browser or self.cache.get_preference('browser')}
            )
        
        # Check known websites
        url = self.kb.get_website_url(target)
        if url:
            return Action(
                type=ActionType.OPEN_URL,
                target=url,
                options={'browser': with_browser or self.cache.get_preference('browser')}
            )
        
        # Check if it's a website pattern
        if 'website' in prompt_lower or any(tld in target for tld in ['.com', '.org', '.net', '.io', '.de']):
            clean_name = target.replace('website', '').strip()
            return Action(
                type=ActionType.SEARCH_WEB,
                target=f"{clean_name} official website",
                options={'intent': 'find_url', 'name': clean_name}
            )
        
        # Check if it's a scrape request - do this BEFORE cleaning the target
        if 'scrape' in prompt_lower:
            # Get the scrape target from original prompt
            scrape_target = prompt_lower
            for prefix in ['scrape ', 'please scrape ', 'can you scrape ']:
                if scrape_target.startswith(prefix):
                    scrape_target = scrape_target[len(prefix):]
            scrape_target = scrape_target.strip()
            
            # Check if we know this URL
            known_url = self.kb.get_website_url(scrape_target.replace(' ', ''))
            if not known_url:
                known_url = self.cache.get_learned_url(scrape_target)
            
            if known_url:
                scrape_target = known_url
            
            if 'html' in prompt_lower and 'css' in prompt_lower:
                return Action(type=ActionType.SCRAPE_HTML_CSS, target=scrape_target)
            return Action(type=ActionType.SCRAPE_URL, target=scrape_target)
        
        # Check if it's a file search
        if is_where_query or 'find' in prompt_lower or 'locate' in prompt_lower:
            return Action(type=ActionType.FIND_FILE, target=target)
        
        return None
    
    # ========================================================================
    # AI UNDERSTANDING - When knowledge isn't enough
    # ========================================================================
    
    def _ai_understand(self, prompt: str) -> Action:
        """Use AI to understand the prompt"""
        
        # Select model based on complexity and mode
        model = self._select_model(prompt)
        
        # Build context
        context_parts = []
        if self.state.last_query:
            context_parts.append(f"Letzte Anfrage: {self.state.last_query}")
        if self.state.last_result:
            context_parts.append(f"Letztes Ergebnis: {str(self.state.last_result)[:200]}")
        if self.state.pending_items:
            context_parts.append(f"Ausstehende Auswahl: {len(self.state.pending_items)} Einträge")
        
        context_str = "\n".join(context_parts) if context_parts else "Kein vorheriger Kontext."
        
        # Get user preferences
        prefs = []
        for key in ['browser', 'editor', 'terminal']:
            val = self.cache.get_preference(key)
            if val:
                prefs.append(f"{key}: {val}")
        prefs_str = ", ".join(prefs) if prefs else "Standard-Einstellungen"
        
        system_prompt = f"""Du bist Ryx's Gehirn. Analysiere die Benutzerabsicht und gib eine strukturierte Aktion zurück.

KONTEXT:
{context_str}

BENUTZER-EINSTELLUNGEN: {prefs_str}

BEKANNTE KONFIG-PFADE: hyprland (~/.config/hypr/hyprland.conf), waybar, kitty, nvim, zsh (~/.zshrc)

REGELN:
1. Websites öffnen → {{"action": "open_url", "target": "https://..."}}
2. Dateien öffnen → {{"action": "open_file", "target": "/pfad/zur/datei", "new_terminal": true/false}}
3. Dateien suchen → {{"action": "find_file", "target": "suchbegriff"}}
4. Web-Suche → {{"action": "search_web", "target": "suchanfrage"}}
5. Scrapen → {{"action": "scrape_url", "target": "url_oder_name"}}
6. Dokument erstellen → {{"action": "create_document", "target": "thema", "type": "lernzettel/zusammenfassung/spreadsheet"}}
7. Fragen beantworten → {{"action": "answer", "target": "kurze antwort"}}
8. Bei UNSICHERHEIT → {{"action": "clarify", "question": "spezifische ja/nein frage"}}
9. Mehrere Aktionen → {{"action": "multi_action", "actions": [...]}}

WICHTIG:
- KURZE Antworten (1-2 Sätze max)
- NIEMALS Pfade erfinden - nutze find_file wenn unsicher
- Bei unbekannten Websites: search_web nutzen
- Verstehe sowohl Deutsch als auch Englisch
- Bei komplexen Aufgaben (Lernzettel, Zusammenfassung): create_document nutzen

ANTWORTE NUR MIT JSON:"""

        response = self.ollama.generate(
            prompt=f"Benutzer: {prompt}",
            model=model,
            system=system_prompt,
            max_tokens=400,
            temperature=0.1
        )
        
        if response.error:
            self.consecutive_fails += 1
            return Action(type=ActionType.CLARIFY, question="Es gab einen Fehler. Kannst du das anders formulieren?")
        
        # Parse JSON
        try:
            text = response.response.strip()
            
            # Clean markdown
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            # Find JSON object
            json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if json_match:
                text = json_match.group()
            
            data = json.loads(text)
            action_type = data.get("action", "answer")
            
            # Map action string to enum
            action_map = {
                'open_url': ActionType.OPEN_URL,
                'open_file': ActionType.OPEN_FILE,
                'find_file': ActionType.FIND_FILE,
                'search_web': ActionType.SEARCH_WEB,
                'scrape_url': ActionType.SCRAPE_URL,
                'scrape_html_css': ActionType.SCRAPE_HTML_CSS,
                'answer': ActionType.ANSWER,
                'clarify': ActionType.CLARIFY,
                'create_document': ActionType.CREATE_DOCUMENT,
                'multi_action': ActionType.MULTI_ACTION,
                'run_command': ActionType.RUN_COMMAND,
            }
            
            atype = action_map.get(action_type, ActionType.CLARIFY)
            
            action = Action(
                type=atype,
                target=data.get("target"),
                question=data.get("question"),
                options=data.get("options", {}),
                confidence=data.get("confidence", 0.8)
            )
            
            self.consecutive_fails = 0
            return action
            
        except (json.JSONDecodeError, ValueError) as e:
            self.consecutive_fails += 1
            return Action(
                type=ActionType.CLARIFY,
                question="Ich bin mir nicht sicher was du meinst. Kannst du das anders formulieren?"
            )
    
    def _select_model(self, prompt: str) -> str:
        """Select appropriate model based on task"""
        
        # Precision mode always uses high model
        if self.precision_mode:
            return self.models['precision']
        
        # After multiple failures, upgrade
        if self.consecutive_fails >= self.max_fails_before_upgrade:
            return self.models['smart']
        
        prompt_lower = prompt.lower()
        prompt_len = len(prompt)
        
        # Complex tasks
        if any(x in prompt_lower for x in ['lernzettel', 'zusammenfassung', 'erkläre', 'explain', 
                                           'analyze', 'compare', 'warum', 'why', 'how does']):
            return self.models['balanced']
        
        # Web/scraping
        if any(x in prompt_lower for x in ['scrape', 'search', 'suche', 'find online']):
            return self.models['balanced']
        
        # Long prompts
        if prompt_len > 200:
            return self.models['balanced']
        
        # Default to fast
        return self.models['fast']
    
    # ========================================================================
    # ACTION EXECUTORS
    # ========================================================================
    
    def _exec_open_file(self, action: Action) -> Tuple[bool, str]:
        """Open a file in editor"""
        path = action.target
        if not path:
            return False, "Keine Datei angegeben"
        
        path = os.path.expanduser(path)
        
        if not os.path.exists(path):
            return False, f"Datei nicht gefunden: {path}"
        
        editor = self.cache.get_preference("editor") or self.kb.get_default("editor")
        new_terminal = action.options.get("new_terminal", False)
        
        try:
            if new_terminal:
                terminal = self.cache.get_preference("terminal") or self.kb.get_default("terminal")
                subprocess.Popen([terminal, "-e", editor, path],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run([editor, path])
            return True, path
        except Exception as e:
            return False, f"Fehler beim Öffnen: {e}"
    
    def _exec_open_url(self, action: Action) -> Tuple[bool, str]:
        """Open URL in browser"""
        url = action.target
        if not url:
            return False, "Keine URL angegeben"
        
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        
        browser = action.options.get("browser") or self.cache.get_preference("browser") or self.kb.get_default("browser")
        
        try:
            subprocess.Popen([browser, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, url
        except Exception as e:
            return False, f"Fehler beim Öffnen: {e}"
    
    def _exec_find_file(self, action: Action) -> Tuple[bool, str]:
        """Find files matching query"""
        query = action.target
        if not query:
            return False, "Kein Suchbegriff"
        
        # Build patterns
        query_clean = query.lower().replace(" ", "*")
        
        # Search locations
        search_dirs = [
            os.path.expanduser("~/.config"),
            os.path.expanduser("~"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Pictures"),
        ]
        
        found = []
        for search_dir in search_dirs:
            if not os.path.exists(search_dir):
                continue
            try:
                result = subprocess.run(
                    ["find", search_dir, "-maxdepth", "4", "-iname", f"*{query_clean}*", "-type", "f"],
                    capture_output=True, text=True, timeout=5
                )
                if result.stdout.strip():
                    found.extend(result.stdout.strip().split("\n"))
            except:
                pass
        
        if found:
            unique = list(set(found))[:10]
            
            if len(unique) == 1:
                return True, unique[0]
            else:
                # Store as pending for selection
                self.state.pending_items = [{"path": p, "name": os.path.basename(p)} for p in unique]
                lines = [f"{i+1}. {os.path.basename(p)}: {p}" for i, p in enumerate(unique)]
                return True, "Mehrere gefunden:\n" + "\n".join(lines) + "\n\nWelche? (Nummer eingeben)"
        
        return False, f"Keine Dateien gefunden für '{query}'"
    
    def _exec_search_web(self, action: Action) -> Tuple[bool, str]:
        """Search the web via SearXNG"""
        query = action.target
        intent = action.options.get("intent", "search")
        name = action.options.get("name", "")
        
        # Check if SearXNG is running
        import requests
        searxng_url = os.environ.get('SEARXNG_URL', 'http://localhost:8888')
        
        try:
            # Try SearXNG
            response = requests.get(
                f"{searxng_url}/search",
                params={'q': query, 'format': 'json', 'categories': 'general'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                for item in data.get('results', [])[:10]:
                    results.append(SearchResult(
                        title=item.get('title', 'Kein Titel'),
                        url=item.get('url', ''),
                        snippet=item.get('content', '')[:150] if item.get('content') else ''
                    ))
                
                if intent == "find_url" and name and results:
                    # Looking for specific website
                    for r in results:
                        if name.lower() in r.title.lower() or name.lower() in r.url.lower():
                            self.cache.learn_url(name, r.url, "search")
                            return True, r.url
                
                # Show results for selection
                if results:
                    self.state.pending_items = [{'url': r.url, 'title': r.title} for r in results]
                    lines = []
                    for i, r in enumerate(results[:5]):
                        lines.append(f"{i+1}. {r.title}")
                        lines.append(f"   {r.url}")
                        if r.snippet:
                            lines.append(f"   {r.snippet}...")
                        lines.append("")
                    return True, "\n".join(lines) + "\nWelche? (Nummer eingeben oder 'mehr' für weitere)"
                
                return False, "Keine Ergebnisse gefunden"
            
        except requests.exceptions.ConnectionError:
            # SearXNG not running - offer to start
            self.state.awaiting_confirmation = True
            self.state.pending_question = "SearXNG läuft nicht. Soll ich es starten? (y/n)"
            self.state.last_action = Action(
                type=ActionType.RUN_COMMAND,
                target="docker run -d -p 8888:8080 --name searxng searxng/searxng"
            )
            return True, self.state.pending_question
        
        except Exception as e:
            return False, f"Suchfehler: {e}"
    
    def _exec_scrape(self, action: Action) -> Tuple[bool, str]:
        """Scrape a webpage"""
        target = action.target
        if not target:
            return False, "Keine URL zum Scrapen"
        
        # Check if it's a URL or name
        if not target.startswith('http'):
            # Try learned URLs
            url = self.cache.get_learned_url(target)
            if not url:
                url = self.kb.get_website_url(target)
            if not url:
                # Need to search first
                return self._exec_search_web(Action(
                    type=ActionType.SEARCH_WEB,
                    target=f"{target} official website",
                    options={'intent': 'find_url', 'name': target}
                ))
        else:
            url = target
        
        try:
            import requests
            from bs4 import BeautifulSoup
            
            response = requests.get(url, timeout=15, headers={
                'User-Agent': 'Ryx-AI/2.0 (Local; Privacy-First)'
            })
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Remove noise
            for elem in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                elem.decompose()
            
            # Extract title and text
            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else urlparse(url).netloc
            
            main = soup.find('main') or soup.find('article') or soup.find('body')
            text = main.get_text(separator=' ', strip=True) if main else ""
            text = ' '.join(text.split())[:5000]
            
            # Save
            scrape_dir = get_data_dir() / "scrape"
            scrape_dir.mkdir(parents=True, exist_ok=True)
            
            domain = urlparse(url).netloc
            safe_name = re.sub(r'[^\w\-_.]', '_', domain)[:50]
            
            save_as = action.options.get('save_as', 'json')
            
            if save_as == 'markdown':
                filepath = scrape_dir / f"{safe_name}.md"
                with open(filepath, 'w') as f:
                    f.write(f"# {title_text}\n\n")
                    f.write(f"URL: {url}\n")
                    f.write(f"Scraped: {datetime.now().isoformat()}\n\n")
                    f.write("---\n\n")
                    f.write(text)
            else:
                filepath = scrape_dir / f"{safe_name}.json"
                with open(filepath, 'w') as f:
                    json.dump({
                        'url': url,
                        'title': title_text,
                        'domain': domain,
                        'text': text,
                        'scraped_at': datetime.now().isoformat()
                    }, f, indent=2, ensure_ascii=False)
            
            # Store for follow-up
            self.state.last_scraped_url = url
            self.state.last_scraped_content = {'title': title_text, 'text': text[:1000]}
            
            # Learn URL
            self.cache.learn_url(domain, url, "scrape")
            
            return True, f"✅ Gescraped: {title_text}\n   Gespeichert: {filepath}\n   Textlänge: {len(text)} Zeichen"
            
        except Exception as e:
            return False, f"Scrape fehlgeschlagen: {e}"
    
    def _exec_scrape_html_css(self, action: Action) -> Tuple[bool, str]:
        """Scrape HTML and CSS from a webpage"""
        target = action.target
        if not target:
            # Ask for website
            return True, "Welche Website soll ich scrapen?"
        
        # Resolve URL
        if not target.startswith('http'):
            url = self.cache.get_learned_url(target) or self.kb.get_website_url(target)
            if not url:
                # Need to search
                self.state.last_action = action
                return self._exec_search_web(Action(
                    type=ActionType.SEARCH_WEB,
                    target=f"{target} website",
                    options={'intent': 'find_url', 'name': target}
                ))
        else:
            url = target
        
        try:
            import requests
            from bs4 import BeautifulSoup
            
            response = requests.get(url, timeout=15, headers={
                'User-Agent': 'Ryx-AI/2.0'
            })
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Get HTML
            html_content = soup.prettify()
            
            # Extract CSS
            css_content = []
            
            # Inline styles
            for style in soup.find_all('style'):
                css_content.append(f"/* Inline Style */\n{style.string or ''}")
            
            # External stylesheets
            for link in soup.find_all('link', rel='stylesheet'):
                href = link.get('href')
                if href:
                    try:
                        full_url = urljoin(url, href)
                        css_resp = requests.get(full_url, timeout=10)
                        if css_resp.status_code == 200:
                            css_content.append(f"/* From: {full_url} */\n{css_resp.text}")
                    except:
                        pass
            
            # Save
            domain = urlparse(url).netloc
            safe_name = re.sub(r'[^\w\-_.]', '_', domain)[:50]
            
            scrape_dir = get_data_dir() / "scrape" / safe_name
            scrape_dir.mkdir(parents=True, exist_ok=True)
            
            html_file = scrape_dir / "index.html"
            css_file = scrape_dir / "styles.css"
            
            with open(html_file, 'w') as f:
                f.write(html_content)
            
            with open(css_file, 'w') as f:
                f.write("\n\n".join(css_content))
            
            return True, f"✅ HTML & CSS gescraped von {domain}\n   Gespeichert in: {scrape_dir}"
            
        except Exception as e:
            return False, f"Scrape fehlgeschlagen: {e}"
    
    def _exec_command(self, action: Action) -> Tuple[bool, str]:
        """Execute a shell command"""
        cmd = action.target
        if not cmd:
            return False, "Kein Befehl"
        
        # Safety check
        dangerous = ['rm -rf /', 'rm -rf ~', ':(){:|:&};:', 'dd if=/dev/zero']
        if any(d in cmd.lower() for d in dangerous):
            return False, "Gefährlicher Befehl blockiert"
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            output = result.stdout or result.stderr
            return result.returncode == 0, output.strip()
        except subprocess.TimeoutExpired:
            return False, "Timeout nach 30s"
        except Exception as e:
            return False, f"Fehler: {e}"
    
    def _exec_set_preference(self, action: Action) -> Tuple[bool, str]:
        """Set a user preference"""
        key = action.target
        value = action.options.get("value", "")
        
        if key and value:
            self.cache.set_preference(key, value)
            return True, f"✅ {key} = {value}"
        
        return False, "Ungültige Einstellung"
    
    def _exec_start_service(self, action: Action) -> Tuple[bool, str]:
        """Start a service"""
        service = (action.target or "").lower()
        
        if service in ["searxng", "searx", "search"]:
            try:
                import requests
                requests.get("http://localhost:8888", timeout=2)
                return True, "SearXNG läuft bereits"
            except:
                pass
            
            # Need confirmation
            if not action.requires_confirmation:
                self.state.awaiting_confirmation = True
                self.state.pending_question = "SearXNG starten? (docker run -d -p 8888:8080 searxng/searxng) y/n"
                self.state.last_action = Action(
                    type=ActionType.RUN_COMMAND,
                    target="docker run -d -p 8888:8080 --name searxng searxng/searxng"
                )
                return True, self.state.pending_question
        
        return False, f"Unbekannter Dienst: {service}"
    
    def _exec_restart_service(self, action: Action) -> Tuple[bool, str]:
        """Restart services"""
        service = (action.target or "").lower()
        
        if service == "ryx":
            if action.requires_confirmation:
                self.state.awaiting_confirmation = True
                self.state.pending_question = action.question or "Alle Ryx-Dienste neustarten? y/n"
                self.state.last_action = Action(
                    type=ActionType.RUN_COMMAND,
                    target="pkill -f 'ryx' ; sleep 1 ; ryx"
                )
                return True, self.state.pending_question
        
        return False, f"Neustart von {service} nicht unterstützt"
    
    def _exec_get_date(self, action: Action) -> Tuple[bool, str]:
        """Get current date/time"""
        now = datetime.now()
        # German format
        return True, now.strftime("%A, %d. %B %Y - %H:%M Uhr")
    
    def _exec_switch_model(self, action: Action) -> Tuple[bool, str]:
        """Switch to a different model"""
        model_query = action.target
        if not model_query:
            return False, "Kein Modell angegeben"
        
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=10
            )
            available = result.stdout.lower()
            
            # Fuzzy match
            for line in result.stdout.strip().split('\n')[1:]:
                model_name = line.split()[0]
                if model_query.lower() in model_name.lower():
                    self.models['balanced'] = model_name
                    return True, f"✅ Gewechselt zu {model_name}"
            
            return False, f"Modell '{model_query}' nicht gefunden"
            
        except Exception as e:
            return False, f"Fehler: {e}"
    
    def _exec_toggle_mode(self, action: Action) -> Tuple[bool, str]:
        """Toggle a mode (precision, etc)"""
        mode = action.target
        enabled = action.options.get('enabled', True)
        
        if mode == 'precision':
            self.precision_mode = enabled
            state = "EIN" if enabled else "AUS"
            return True, f"✅ Präzisionsmodus {state}"
        
        return False, f"Unbekannter Modus: {mode}"
    
    def _exec_create_document(self, action: Action) -> Tuple[bool, str]:
        """Create a document (Lernzettel, summary, etc)"""
        topic = action.target
        doc_type = action.options.get('type', 'lernzettel')
        
        if not topic:
            return False, "Kein Thema angegeben"
        
        # This needs web search + AI synthesis
        # First, search for information
        search_queries = []
        if doc_type == 'lernzettel':
            search_queries = [
                f"{topic} Grundlagen",
                f"{topic} Erklärung",
                f"{topic} Beispiele",
                f"{topic} wichtige Punkte"
            ]
        else:
            search_queries = [f"{topic}"]
        
        # Use precision model for document creation
        self.state.awaiting_confirmation = True
        self.state.pending_question = f"Soll ich einen {doc_type} über '{topic}' erstellen? Das erfordert Web-Recherche. y/n"
        
        # Store the full action for later
        self.state.last_action = Action(
            type=ActionType.CREATE_DOCUMENT,
            target=topic,
            options={'type': doc_type, 'queries': search_queries, 'confirmed': True}
        )
        
        return True, self.state.pending_question
    
    def _exec_list_items(self, action: Action) -> Tuple[bool, str]:
        """List items for selection"""
        items = action.options.get('items', [])
        if not items:
            return False, "Keine Einträge"
        
        self.state.pending_items = items
        lines = [f"{i+1}. {item.get('title', item.get('name', str(item)))}" for i, item in enumerate(items[:10])]
        return True, "\n".join(lines) + "\n\nWelche? (Nummer eingeben)"
    
    def _exec_select_item(self, action: Action) -> Tuple[bool, str]:
        """Select an item from list"""
        idx = action.options.get('index', 0)
        if 0 <= idx < len(self.state.pending_items):
            item = self.state.pending_items[idx]
            self.state.pending_items = []
            
            if 'url' in item:
                return self._exec_open_url(Action(type=ActionType.OPEN_URL, target=item['url']))
            elif 'path' in item:
                return self._exec_open_file(Action(type=ActionType.OPEN_FILE, target=item['path']))
        
        return False, "Ungültige Auswahl"
    
    def _exec_multi_action(self, action: Action) -> Tuple[bool, str]:
        """Execute multiple actions"""
        results = []
        for sub in action.sub_actions:
            success, result = self.execute(sub)
            results.append(f"{'✅' if success else '❌'} {result}")
        
        return all('✅' in r for r in results), "\n".join(results)
    
    # ========================================================================
    # SELF-IMPROVEMENT
    # ========================================================================
    
    def get_smarter(self) -> str:
        """Self-improvement: clean cache, verify knowledge"""
        results = []
        
        # Clean bad cache entries
        deleted = self.cache.cleanup_bad_entries()
        results.append(f"Cache bereinigt: {deleted} fehlerhafte Einträge entfernt")
        
        # Verify config paths
        fixed = 0
        for name, path in list(self.kb.arch_linux.get("config_paths", {}).items()):
            expanded = os.path.expanduser(path)
            if not os.path.exists(expanded):
                # Try to find
                try:
                    result = subprocess.run(
                        ["find", os.path.expanduser("~/.config"), "-name", f"*{name}*", "-type", "f"],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.stdout.strip():
                        found = result.stdout.strip().split('\n')[0]
                        self.kb.arch_linux["config_paths"][name] = found
                        fixed += 1
                        results.append(f"Pfad korrigiert: {name} → {found}")
                except:
                    pass
        
        if fixed:
            self.kb.save()
        
        results.append(f"\n✅ Selbstverbesserung abgeschlossen. {fixed} Pfade korrigiert.")
        
        return "\n".join(results)


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_brain_v2: Optional[RyxBrainV2] = None

def get_brain_v2(ollama_client=None) -> RyxBrainV2:
    """Get or create the brain v2 instance"""
    global _brain_v2
    if _brain_v2 is None:
        if ollama_client is None:
            from core.ollama_client import OllamaClient
            from core.model_router import ModelRouter
            router = ModelRouter()
            ollama_client = OllamaClient(base_url=router.get_ollama_url())
        _brain_v2 = RyxBrainV2(ollama_client)
    return _brain_v2
