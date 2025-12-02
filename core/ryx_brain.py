"""
Ryx AI - Brain

Core intelligence for Ryx AI assistant.
Like Copilot CLI / Claude CLI - uses tools to get things done.

Key principles:
- NEVER say "Could you be more specific?" - ASK a specific question
- Use web search to ground answers (reduce hallucination)
- Follow-up questions use conversation context
- Action-oriented, not explanation-oriented
- German/English bilingual
"""

import os
import re
import json
import sqlite3
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum

from core.paths import get_data_dir


class Intent(Enum):
    """What the user wants to do"""
    OPEN_FILE = "open_file"
    OPEN_URL = "open_url"
    FIND_FILE = "find_file"
    FIND_PATH = "find_path"  # Where is X?
    SEARCH_WEB = "search_web"
    SCRAPE = "scrape"
    SCRAPE_HTML = "scrape_html"
    RUN_COMMAND = "run_command"
    SET_PREFERENCE = "set_pref"
    SWITCH_MODEL = "switch_model"
    CREATE_DOCUMENT = "create_doc"
    START_SERVICE = "start_svc"
    STOP_SERVICE = "stop_svc"
    RESTART = "restart"
    GET_INFO = "get_info"  # Date, time, system info
    LIST_MODELS = "list_models"
    CHAT = "chat"
    CONFIRM = "confirm"  # Waiting for y/n
    SELECT = "select"  # Waiting for number selection
    UNCLEAR = "unclear"  # Need to ask clarifying question
    # NEW: Complex coding tasks that need the phase system
    CODE_TASK = "code_task"  # Requires EXPLORE→PLAN→APPLY→VERIFY
    EXPLORE_REPO = "explore_repo"  # Just explore, no changes


@dataclass
class Plan:
    """Execution plan from supervisor"""
    intent: Intent
    target: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)
    steps: List[str] = field(default_factory=list)
    question: Optional[str] = None  # If we need to ask user
    confidence: float = 1.0
    requires_confirmation: bool = False
    fallback_intents: List[Intent] = field(default_factory=list)


@dataclass
class ConversationContext:
    """Tracks conversation state"""
    last_query: str = ""
    last_result: str = ""
    last_path: str = ""  # Last file/URL we talked about
    last_intent: Optional[Intent] = None
    pending_items: List[Dict] = field(default_factory=list)
    pending_plan: Optional[Plan] = None
    awaiting_confirmation: bool = False
    awaiting_selection: bool = False
    last_scraped: Optional[Dict] = None
    language: str = "auto"
    turn_count: int = 0


class KnowledgeBase:
    """Pre-loaded verified knowledge - NO LLM needed"""
    
    def __init__(self):
        self.data_dir = get_data_dir()
        self.knowledge_dir = self.data_dir / "knowledge"
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        self.arch_linux: Dict = {}
        self.websites: Dict = {}
        self.config_paths: Dict = {}
        self.aliases: Dict = {}
        
        self._load()
    
    def _load(self):
        arch_file = self.knowledge_dir / "arch_linux.json"
        if arch_file.exists():
            with open(arch_file) as f:
                self.arch_linux = json.load(f)
        
        self.config_paths = self.arch_linux.get("config_paths", {})
        self.websites = self.arch_linux.get("websites", {})
        self.aliases = self.arch_linux.get("aliases", {})
    
    def resolve_config_name(self, name: str) -> str:
        """Resolve aliases and typos to canonical name"""
        name_lower = name.lower().strip()
        
        # Direct alias
        if name_lower in self.aliases:
            return self.aliases[name_lower]
        
        # Common typos
        typo_map = {
            "hyperland": "hyprland",
            "hyperion": "hyprland",
            "hypr": "hyprland",
            "wayber": "waybar",
            "waybr": "waybar",
            "kity": "kitty",
            "neovim": "nvim",
            "vim": "nvim",
        }
        if name_lower in typo_map:
            return typo_map[name_lower]
        
        return name_lower
    
    def get_config_path(self, name: str) -> Optional[str]:
        """Get config file path, handling aliases and typos"""
        canonical = self.resolve_config_name(name)
        
        # Try direct lookup
        path = self.config_paths.get(canonical)
        if path:
            expanded = os.path.expanduser(path)
            return expanded
        
        # Try with _conf suffix
        path = self.config_paths.get(f"{canonical}_conf")
        if path:
            return os.path.expanduser(path)
        
        # Try partial match - but only if canonical is at least 4 chars
        # to avoid matching "man" in "pacman" etc.
        if len(canonical) >= 4:
            for key, val in self.config_paths.items():
                if canonical in key:
                    return os.path.expanduser(val)
        
        return None
    
    def get_website_url(self, name: str) -> Optional[str]:
        """Get URL for website name"""
        name_lower = name.lower().strip()
        
        # Direct match
        if name_lower in self.websites:
            return self.websites[name_lower]
        
        # Try without spaces
        no_space = name_lower.replace(" ", "")
        if no_space in self.websites:
            return self.websites[no_space]
        
        # Partial match
        for key, url in self.websites.items():
            if name_lower in key or key in name_lower:
                return url
        
        return None
    
    def save(self):
        arch_file = self.knowledge_dir / "arch_linux.json"
        with open(arch_file, 'w') as f:
            json.dump(self.arch_linux, f, indent=2, ensure_ascii=False)


class SmartCache:
    """Learning cache - stores successful resolutions"""
    
    def __init__(self):
        self.db_path = get_data_dir() / "smart_cache.db"
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS resolutions (
                query_hash TEXT PRIMARY KEY,
                query TEXT,
                intent TEXT,
                target TEXT,
                options TEXT,
                success_count INTEGER DEFAULT 1,
                fail_count INTEGER DEFAULT 0,
                last_used TEXT
            );
            
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated TEXT
            );
            
            CREATE TABLE IF NOT EXISTS learned_urls (
                name TEXT PRIMARY KEY,
                url TEXT,
                domain TEXT,
                created TEXT
            );
            
            CREATE TABLE IF NOT EXISTS model_config (
                role TEXT PRIMARY KEY,
                model_name TEXT,
                updated TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_query ON resolutions(query);
        """)
        conn.commit()
        conn.close()
    
    def _hash(self, text: str) -> str:
        normalized = re.sub(r'\s+', ' ', text.lower().strip())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def lookup(self, query: str) -> Optional[Plan]:
        """Check if we've successfully handled this before"""
        h = self._hash(query)
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT intent, target, options, success_count, fail_count FROM resolutions WHERE query_hash = ?",
            (h,)
        ).fetchone()
        conn.close()
        
        if row and row[3] > row[4]:  # More successes than failures
            try:
                return Plan(
                    intent=Intent(row[0]),
                    target=row[1],
                    options=json.loads(row[2]) if row[2] else {},
                    confidence=0.95
                )
            except:
                pass
        return None
    
    def store(self, query: str, plan: Plan, success: bool = True):
        """Store resolution result"""
        h = self._hash(query)
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        
        existing = conn.execute(
            "SELECT success_count, fail_count FROM resolutions WHERE query_hash = ?",
            (h,)
        ).fetchone()
        
        if existing:
            s, f = existing
            if success:
                s += 1
            else:
                f += 1
            conn.execute(
                "UPDATE resolutions SET success_count=?, fail_count=?, last_used=? WHERE query_hash=?",
                (s, f, now, h)
            )
        else:
            conn.execute(
                "INSERT INTO resolutions (query_hash, query, intent, target, options, success_count, fail_count, last_used) VALUES (?,?,?,?,?,?,?,?)",
                (h, query.lower()[:200], plan.intent.value, plan.target, json.dumps(plan.options), 
                 1 if success else 0, 0 if success else 1, now)
            )
        conn.commit()
        conn.close()
    
    def get_preference(self, key: str) -> Optional[str]:
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT value FROM preferences WHERE key=?", (key,)).fetchone()
        conn.close()
        return row[0] if row else None
    
    def set_preference(self, key: str, value: str):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO preferences (key, value, updated) VALUES (?,?,?)",
            (key, value, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    
    def get_model(self, role: str) -> Optional[str]:
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT model_name FROM model_config WHERE role=?", (role,)).fetchone()
        conn.close()
        return row[0] if row else None
    
    def set_model(self, role: str, model: str):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO model_config (role, model_name, updated) VALUES (?,?,?)",
            (role, model, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    
    def learn_url(self, name: str, url: str):
        domain = url.split('/')[2] if '/' in url else url
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO learned_urls (name, url, domain, created) VALUES (?,?,?,?)",
            (name.lower(), url, domain, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    
    def get_learned_url(self, name: str) -> Optional[str]:
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT url FROM learned_urls WHERE name=?", (name.lower(),)).fetchone()
        conn.close()
        return row[0] if row else None
    
    def cleanup(self):
        """Remove entries with more failures than successes"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM resolutions WHERE fail_count > success_count AND (success_count + fail_count) > 3")
        conn.commit()
        conn.close()


class ModelManager:
    """Manages model selection"""
    
    MODELS = {
        # Fast (1-3B) - cached lookups, simple tasks
        "fast": ["qwen2.5:1.5b", "qwen2.5:3b", "llama3.2:1b", "phi3:mini"],
        # Balanced (7B) - general use, chat
        "balanced": ["qwen2.5:7b", "mistral:7b"],
        # Smart (14B+) - complex tasks, precision
        "smart": ["qwen2.5-coder:14b", "gpt-oss:20b"],
        # Precision (20B+) - learning, document creation
        "precision": ["gpt-oss:20b", "huihui_ai/gpt-oss-abliterated:20b"],
    }
    
    def __init__(self, cache: SmartCache):
        self.cache = cache
        self.available: List[str] = []
        self._refresh()
    
    def _refresh(self):
        try:
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
            self.available = [line.split()[0] for line in result.stdout.strip().split('\n')[1:] if line.strip()]
        except:
            self.available = []
    
    def get(self, role: str, precision_mode: bool = False) -> str:
        """Get model for role"""
        # Check user preference
        saved = self.cache.get_model(role)
        if saved and saved in self.available:
            return saved
        
        # Precision mode uses bigger models
        if precision_mode and role not in ["precision", "smart"]:
            role = "precision"
        
        # Get from tier
        for model in self.MODELS.get(role, self.MODELS["fast"]):
            if model in self.available:
                return model
        
        # Fallback
        return self.available[0] if self.available else "qwen2.5:3b"
    
    def find(self, query: str) -> Optional[str]:
        """Find model by natural language query"""
        q = query.lower()
        
        # Direct match
        for model in self.available:
            if q in model.lower():
                return model
        
        # Aliases
        aliases = {
            "gpt": "gpt-oss:20b", "gpt oss": "gpt-oss:20b", "gpt 20": "gpt-oss:20b",
            "mistral": "mistral:7b", "qwen": "qwen2.5:3b", "qwen 3b": "qwen2.5:3b",
            "qwen 7b": "qwen2.5:7b", "qwen coder": "qwen2.5-coder:14b",
            "deepseek": "deepseek-coder:6.7b", "llama": "llama3.2:1b", "phi": "phi3:mini",
        }
        
        for alias, model in aliases.items():
            if alias in q and model in self.available:
                return model
        
        return None
    
    def get_categorized(self) -> Dict[str, List[str]]:
        """Get models organized by category"""
        result = {cat: [] for cat in self.MODELS}
        result["other"] = []
        
        categorized = set()
        for cat, models in self.MODELS.items():
            for model in models:
                if model in self.available:
                    result[cat].append(model)
                    categorized.add(model)
        
        for model in self.available:
            if model not in categorized:
                result["other"].append(model)
        
        return result


class RyxBrain:
    """
    Ryx AI Brain - Core intelligence
    
    - Understands intent, creates plan, handles errors
    - Executes plans using tools
    - Uses search to reduce hallucination
    """
    
    SUPERVISOR_PROMPT = '''Du bist Ryx AI auf Arch Linux + Hyprland.
Analysiere die Anfrage und bestimme den Intent.

KONTEXT:
- Letzte Anfrage: {last_query}
- Letztes Ergebnis: {last_result}
- Letzter Pfad: {last_path}
- Sprache: {language}

WICHTIGE REGELN:
1. Für NORMALE FRAGEN/CHAT → intent: "chat"
2. Für DATEI-OPERATIONEN → intent: "open_file" oder "find_file"
3. Für WEBSITES → intent: "open_url" oder "search_web"
4. NICHT raten wenn unklar → intent: "chat" und einfach antworten

INTENTS (nur diese verwenden):
- chat: Normale Unterhaltung, Fragen beantworten, Erklärungen
- open_file: Datei öffnen (target=Pfad)
- open_url: URL öffnen (target=URL)
- find_file: Datei suchen (target=Suchmuster)
- find_path: Pfad anzeigen (target=Name)
- search_web: Web-Suche (target=Query)
- switch_model: Modell wechseln (target=Modellname)
- get_info: Info abrufen (target=date/time)

BEISPIELE:
- "wie liest man schneller" → {{"intent": "chat"}}
- "wer ist linus" → {{"intent": "search_web", "target": "linus torvalds"}}
- "öffne hyprland config" → {{"intent": "open_file", "target": "~/.config/hypr/hyprland.conf"}}
- "youtube" → {{"intent": "open_url", "target": "https://youtube.com"}}
- "what model is this" → {{"intent": "chat"}}

ANTWORT NUR ALS JSON:
{{"intent": "<intent>", "target": "<ziel oder null>"}}

ANFRAGE: {prompt}'''

    def __init__(self, ollama_client):
        self.ollama = ollama_client
        self.kb = KnowledgeBase()
        self.cache = SmartCache()
        self.models = ModelManager(self.cache)
        self.ctx = ConversationContext()
        
        # Tools
        from core.tools import get_tools
        self.tools = get_tools()
        
        # Mode flags
        self.precision_mode = False
        self.browsing_enabled = True
        self.fail_count = 0
        
        # New agent system (can be toggled)
        self.use_new_agents = False
        self._executor = None
    
    def enable_new_agents(self, enabled: bool = True):
        """Enable/disable the new supervisor/operator agent system"""
        self.use_new_agents = enabled
        if enabled and self._executor is None:
            from core.execution import TaskExecutor
            self._executor = TaskExecutor(self.ollama, verbose=False)
    
    def understand(self, prompt: str) -> Plan:
        """
        Main entry: understand what user wants.
        Uses two-stage approach:
        1. Try fast resolution (cache, knowledge base, patterns)
        2. Fall back to LLM supervisor if needed
        """
        prompt = prompt.strip()
        self.ctx.last_query = prompt
        self.ctx.turn_count += 1
        
        # Detect language
        german = ['bitte', 'öffne', 'zeig', 'mach', 'wo ist', 'was ist', 'erstelle', 'wie', 'wer', 'warum']
        self.ctx.language = 'de' if any(g in prompt.lower() for g in german) else 'en'
        
        # Stage 1: Quick resolution (no LLM)
        
        # Handle y/n/number responses
        if self._is_quick_response(prompt):
            return self._handle_quick_response(prompt)
        
        # Handle context references ("open it", "edit that")
        plan = self._handle_context_reference(prompt)
        if plan:
            return plan
        
        # Check cache (skip in precision mode)
        if not self.precision_mode:
            cached = self.cache.lookup(prompt)
            if cached:
                return cached
        
        # Try knowledge-based resolution
        plan = self._resolve_from_knowledge(prompt)
        if plan:
            return plan
        
        # Check if this is a coding task that needs the phase system
        if self._is_code_task(prompt):
            return Plan(intent=Intent.CODE_TASK, target=prompt)
        
        # Check if this is clearly a chat question (not an action)
        if self._is_chat_question(prompt):
            return Plan(intent=Intent.CHAT)
        
        # Stage 2: LLM supervisor
        return self._supervisor_understand(prompt)
    
    def _is_code_task(self, prompt: str) -> bool:
        """Check if this is a coding task that needs EXPLORE→PLAN→APPLY→VERIFY"""
        p = prompt.lower()
        
        # Coding task indicators - actions that modify code
        code_indicators = [
            'add a ', 'add new', 'create a ', 'create new', 'implement ', 'build ',
            'fix ', 'bug ', 'error in', 'refactor ', 'change the ', 'change code',
            'update the ', 'modify the ', 'edit the code', 'write a ',
            'füge hinzu', 'erstelle', 'implementiere', 'baue',
            'fixe', 'fehler', 'ändere den', 'aktualisiere',
            'new function', 'new class', 'new method', 'new component',
            'new feature', 'new test', 'new style',
        ]
        
        # Context words that indicate coding
        code_context = [
            'code', 'function', 'class', 'module', 'method',
            'component', 'script', 'program', 'app', 'api',
            'handler', 'service', 'controller', 'model',
            'theme', 'style', 'color', 'css',  # UI/theme related
            '.py', '.js', '.ts', '.tsx', '.rs', '.go',
            'funktion', 'klasse', 'modul',
        ]
        
        # Exclusions - simple file operations (not coding)
        simple_ops = [
            'open ', 'öffne ', 'show ', 'zeig ', 'find ', 'finde ',
            'where ', 'wo ', 'config',  # Config is just opening files
        ]
        
        has_code_indicator = any(i in p for i in code_indicators)
        has_code_context = any(c in p for c in code_context)
        is_simple_op = any(p.startswith(s) or f' {s}' in p for s in simple_ops)
        
        return has_code_indicator and (has_code_context or len(p) > 30) and not is_simple_op
    
    def _is_chat_question(self, prompt: str) -> bool:
        """Check if this is clearly a conversational question, not an action request"""
        p = prompt.lower()
        
        # Question words that indicate chat/information seeking
        chat_starters = [
            'wie ', 'was ', 'wer ', 'warum ', 'wann ', 'welche',
            'how ', 'what ', 'who ', 'why ', 'when ', 'which ',
            'can you ', 'could you ', 'kannst du ', 'könntest du ',
            'tell me ', 'explain ', 'erkläre ', 'erzähl ',
            'is it ', 'ist es ', 'are ', 'sind ',
        ]
        
        # These indicate ACTION, not chat
        action_words = [
            'open', 'öffne', 'find', 'finde', 'search', 'suche',
            'config', 'edit', 'show file', 'zeig datei',
            'youtube', 'github', 'reddit',  # Known websites
        ]
        
        is_question = any(p.startswith(q) or f' {q}' in p for q in chat_starters)
        is_action = any(a in p for a in action_words)
        
        return is_question and not is_action
    
    def _is_quick_response(self, prompt: str) -> bool:
        """Check if this is a y/n/number response"""
        p = prompt.lower().strip()
        quick = {'y', 'yes', 'ja', 'n', 'no', 'nein', 'ok', 'okay', 'klar', 'sure'}
        return p in quick or p.isdigit() or p.startswith('the first') or p.startswith('das erste')
    
    def _handle_quick_response(self, prompt: str) -> Plan:
        """Handle y/n/number responses instantly"""
        p = prompt.lower().strip()
        
        # Pending confirmation
        if self.ctx.awaiting_confirmation and self.ctx.pending_plan:
            if p in {'y', 'yes', 'ja', 'ok', 'okay', 'klar', 'sure'}:
                plan = self.ctx.pending_plan
                self.ctx.pending_plan = None
                self.ctx.awaiting_confirmation = False
                return plan
            elif p in {'n', 'no', 'nein'}:
                self.ctx.pending_plan = None
                self.ctx.awaiting_confirmation = False
                return Plan(intent=Intent.CHAT, target="Abgebrochen." if self.ctx.language == 'de' else "Cancelled.")
        
        # Pending selection
        if self.ctx.awaiting_selection and self.ctx.pending_items:
            if p.isdigit():
                idx = int(p) - 1
                if 0 <= idx < len(self.ctx.pending_items):
                    item = self.ctx.pending_items[idx]
                    self.ctx.pending_items = []
                    self.ctx.awaiting_selection = False
                    
                    if 'url' in item:
                        return Plan(intent=Intent.OPEN_URL, target=item['url'])
                    elif 'path' in item:
                        return Plan(intent=Intent.OPEN_FILE, target=item['path'])
            
            elif 'first' in p or 'erste' in p:
                if self.ctx.pending_items:
                    item = self.ctx.pending_items[0]
                    self.ctx.pending_items = []
                    self.ctx.awaiting_selection = False
                    if 'url' in item:
                        return Plan(intent=Intent.OPEN_URL, target=item['url'])
                    elif 'path' in item:
                        return Plan(intent=Intent.OPEN_FILE, target=item['path'])
        
        return Plan(intent=Intent.CHAT, target="Nichts ausgewählt." if self.ctx.language == 'de' else "Nothing selected.")
    
    def _handle_context_reference(self, prompt: str) -> Optional[Plan]:
        """Handle 'open it', 'edit that', etc."""
        p = prompt.lower()
        
        refs_open = ['open it', 'edit it', 'open that', 'öffne es', 'öffne das', 'bearbeite es']
        refs_show = ['show it', 'zeig es', 'zeig das']
        
        if any(r in p for r in refs_open):
            # Use last path or single pending item
            if self.ctx.last_path and os.path.exists(self.ctx.last_path):
                return Plan(
                    intent=Intent.OPEN_FILE,
                    target=self.ctx.last_path,
                    options={"editor": self.cache.get_preference("editor") or "nvim"}
                )
            elif len(self.ctx.pending_items) == 1:
                item = self.ctx.pending_items[0]
                self.ctx.pending_items = []
                if 'path' in item:
                    return Plan(intent=Intent.OPEN_FILE, target=item['path'])
                elif 'url' in item:
                    return Plan(intent=Intent.OPEN_URL, target=item['url'])
        
        return None
    
    def _resolve_from_knowledge(self, prompt: str) -> Optional[Plan]:
        """Try to resolve using knowledge base - no LLM needed"""
        p = prompt.lower()
        
        # Date/time queries
        date_words = ['date', 'time', 'datum', 'zeit', 'uhrzeit', 'today', 'heute', 'what day', 'welcher tag']
        if any(d in p for d in date_words):
            return Plan(intent=Intent.GET_INFO, target="datetime")
        
        # Model queries - "what model", "which model", "current model"
        if 'model' in p:
            if any(w in p for w in ['what', 'which', 'current', 'welches', 'aktuell', 'this']):
                # Return current model info
                current = self.cache.get_model("default") or self.models.get("balanced", self.precision_mode)
                return Plan(intent=Intent.CHAT, target=f"Currently using: {current}")
            if any(w in p for w in ['list', 'show', 'zeig', 'all', 'available']):
                return Plan(intent=Intent.LIST_MODELS)
        
        # File finding patterns (check BEFORE configs and websites!)
        find_match = self._match_find_request(prompt)
        if find_match:
            return find_match
        
        # Config file patterns - VERY flexible matching
        config_match = self._match_config_request(prompt)
        if config_match:
            return config_match
        
        # Website patterns (check LAST - most aggressive)
        website_match = self._match_website_request(prompt)
        if website_match:
            return website_match
        
        return None
    
    def _match_config_request(self, prompt: str) -> Optional[Plan]:
        """Match config file requests - must have config intent"""
        p = prompt.lower()
        
        # Must have some indication this is about configs
        config_indicators = ['config', 'conf', 'konfiguration', 'settings', 'einstellung']
        action_indicators = ['open', 'edit', 'show', 'öffne', 'zeig', 'bearbeite', 'look at']
        
        has_config_word = any(c in p for c in config_indicators)
        has_action_word = any(a in p for a in action_indicators)
        
        # Need either config word OR action word + known config name
        if not has_config_word and not has_action_word:
            return None
        
        # Extract potential config name
        words = p.replace('config', '').replace('configuration', '').replace('conf', '').split()
        
        # Filter out action words
        skip = {'open', 'edit', 'show', 'öffne', 'zeig', 'bearbeite', 'in', 'new', 'same', 'terminal', 
                'neues', 'neuem', 'selben', 'diesem', 'the', 'my', 'mein', 'meine', 'look', 'at', 'for'}
        
        config_name = None
        for word in words:
            if word not in skip and len(word) > 2:
                # Check if it's a known config
                path = self.kb.get_config_path(word)
                if path:
                    config_name = word
                    break
        
        if not config_name:
            return None
        
        path = self.kb.get_config_path(config_name)
        if not path:
            return None
        
        # Check if asking "where is" vs "open"
        if 'where' in p or 'wo' in p or 'path' in p or 'pfad' in p:
            exists = os.path.exists(path)
            note = "" if exists else " (existiert nicht)" if self.ctx.language == 'de' else " (doesn't exist)"
            return Plan(intent=Intent.FIND_PATH, target=path + note)
        
        # Determine terminal mode
        terminal = "same"
        if 'new' in p or 'neues' in p or 'neuem' in p:
            terminal = "new"
        
        return Plan(
            intent=Intent.OPEN_FILE,
            target=path,
            options={
                "editor": self.cache.get_preference("editor") or "nvim",
                "terminal": terminal
            }
        )
    
    def _match_website_request(self, prompt: str) -> Optional[Plan]:
        """Match website opening requests"""
        p = prompt.lower().strip()
        
        # Skip if this looks like a search/scrape request
        if any(w in p for w in ['search for', 'scrape', 'suche nach', 'find info']):
            return None
        
        # Single word - check if it's a known website directly
        if ' ' not in p:
            url = self.kb.get_website_url(p)
            if url:
                browser = self.cache.get_preference("browser")
                return Plan(
                    intent=Intent.OPEN_URL,
                    target=url,
                    options={"browser": browser} if browser else {}
                )
            # Also check learned URLs
            url = self.cache.get_learned_url(p)
            if url:
                return Plan(intent=Intent.OPEN_URL, target=url)
        
        # Must have some indication they want a website
        website_intents = ['open', 'öffne', 'go to', 'browse', 'visit', 'show me', 'zeig mir']
        has_website_intent = any(w in p for w in website_intents)
        
        # Or must explicitly mention website-related words
        website_words = ['website', 'site', 'page', 'url', '.com', '.org', '.de', '.io', 'http']
        has_website_word = any(w in p for w in website_words)
        
        # Skip completely if no website intent AND prompt is too short/generic
        if not has_website_intent and not has_website_word:
            return None
        
        # Extract words and look for known websites
        words = p.split()
        skip = {'open', 'öffne', 'show', 'zeig', 'go', 'to', 'the', 'website', 'site', 'in', 'browser'}
        
        for word in words:
            if word not in skip:
                url = self.kb.get_website_url(word)
                if url:
                    browser = self.cache.get_preference("browser")
                    return Plan(
                        intent=Intent.OPEN_URL,
                        target=url,
                        options={"browser": browser} if browser else {}
                    )
                
                # Check learned URLs
                url = self.cache.get_learned_url(word)
                if url:
                    return Plan(intent=Intent.OPEN_URL, target=url)
        
        # Check if the whole phrase is a known site
        url = self.kb.get_website_url(p.strip())
        if url:
            return Plan(intent=Intent.OPEN_URL, target=url)
        
        # Only try as direct URL if it has a dot (actual domain pattern)
        for word in words:
            if word not in skip and '.' in word:
                # Looks like an actual domain
                url = f"https://{word}" if not word.startswith('http') else word
                return Plan(
                    intent=Intent.OPEN_URL,
                    target=url,
                    options={"browser": self.cache.get_preference("browser")}
                )
        
        return None
    
    def _match_find_request(self, prompt: str) -> Optional[Plan]:
        """Match file finding requests"""
        p = prompt.lower()
        
        find_words = ['find', 'locate', 'where is', 'wo ist', 'finde']
        # Note: removed 'search' and 'suche' - those are for web search
        if not any(f in p for f in find_words):
            return None
        
        # Don't match web search
        if any(w in p for w in ['online', 'web', 'internet', 'google', 'for']):
            return None
        
        # Check if this is a config request with typo (find hyperland config)
        config_keywords = ['config', 'conf', 'konfiguration']
        if any(k in p for k in config_keywords):
            # Try to find a config name
            for word in p.split():
                resolved = self.kb.resolve_config_name(word)
                path = self.kb.get_config_path(resolved)
                if path:
                    # Return the path, not open it
                    return Plan(intent=Intent.FIND_PATH, target=os.path.expanduser(path))
        
        # Extract search query
        for fw in find_words:
            if fw in p:
                query = p.split(fw)[-1].strip()
                # Remove common suffixes
                query = re.sub(r'\s*(file|files|datei|dateien|me)$', '', query).strip()
                # Remove "me" at start too
                query = re.sub(r'^me\s+', '', query).strip()
                if query:
                    return Plan(intent=Intent.FIND_FILE, target=query)
        
        return None
    
    def _supervisor_understand(self, prompt: str) -> Plan:
        """Use LLM supervisor to understand complex requests"""
        model = self.models.get("smart" if self.precision_mode else "balanced", self.precision_mode)
        
        context = {
            "last_query": self.ctx.last_query or "none",
            "last_result": (self.ctx.last_result or "none")[:100],
            "last_path": self.ctx.last_path or "none",
            "pending_items": str(self.ctx.pending_items[:3]) if self.ctx.pending_items else "none",
            "language": self.ctx.language,
            "prompt": prompt
        }
        
        response = self.ollama.generate(
            prompt=self.SUPERVISOR_PROMPT.format(**context),
            model=model,
            system="Du bist ein JSON-Parser. Antworte NUR mit validem JSON. Keine Erklärungen.",
            max_tokens=300,
            temperature=0.1
        )
        
        if response.error:
            self.fail_count += 1
            if self.fail_count >= 2:
                # Retry with bigger model
                self.fail_count = 0
                bigger = self.models.get("precision", True)
                return self._supervisor_understand(prompt)
            
            # Fallback: ask clarifying question
            return Plan(
                intent=Intent.UNCLEAR,
                question="Was genau möchtest du tun?" if self.ctx.language == 'de' else "What would you like me to do?"
            )
        
        return self._parse_supervisor_response(response.response, prompt)
    
    def _parse_supervisor_response(self, response: str, original: str) -> Plan:
        """Parse supervisor JSON response"""
        try:
            # Clean response
            clean = response.strip()
            if '```' in clean:
                clean = clean.split('```')[1]
                if clean.startswith('json'):
                    clean = clean[4:]
            clean = clean.strip()
            
            # Find JSON
            start = clean.find('{')
            end = clean.rfind('}') + 1
            if start >= 0 and end > start:
                clean = clean[start:end]
            
            data = json.loads(clean)
            
            intent_str = data.get("intent", "chat")
            intent_map = {
                "open_file": Intent.OPEN_FILE,
                "open_url": Intent.OPEN_URL,
                "find_file": Intent.FIND_FILE,
                "find_path": Intent.FIND_PATH,
                "search_web": Intent.SEARCH_WEB,
                "scrape": Intent.SCRAPE,
                "scrape_html": Intent.SCRAPE_HTML,
                "run_command": Intent.RUN_COMMAND,
                "set_pref": Intent.SET_PREFERENCE,
                "switch_model": Intent.SWITCH_MODEL,
                "create_doc": Intent.CREATE_DOCUMENT,
                "start_svc": Intent.START_SERVICE,
                "stop_svc": Intent.STOP_SERVICE,
                "restart": Intent.RESTART,
                "get_info": Intent.GET_INFO,
                "list_models": Intent.LIST_MODELS,
                "chat": Intent.CHAT,
                "confirm": Intent.CONFIRM,
                "select": Intent.SELECT,
                "unclear": Intent.UNCLEAR,
            }
            
            intent = intent_map.get(intent_str, Intent.CHAT)
            
            return Plan(
                intent=intent,
                target=data.get("target"),
                options=data.get("options", {}),
                question=data.get("question"),
                requires_confirmation=data.get("requires_confirm", False)
            )
            
        except json.JSONDecodeError:
            # Fallback: treat as chat response
            return Plan(intent=Intent.CHAT, target=response[:500])
    
    def execute(self, plan: Plan) -> Tuple[bool, str]:
        """Execute a plan and return result"""
        self.ctx.last_intent = plan.intent
        
        handlers = {
            Intent.OPEN_FILE: self._exec_open_file,
            Intent.OPEN_URL: self._exec_open_url,
            Intent.FIND_FILE: self._exec_find_file,
            Intent.FIND_PATH: self._exec_find_path,
            Intent.SEARCH_WEB: self._exec_search_web,
            Intent.SCRAPE: self._exec_scrape,
            Intent.SCRAPE_HTML: self._exec_scrape_html,
            Intent.RUN_COMMAND: self._exec_command,
            Intent.SET_PREFERENCE: self._exec_set_pref,
            Intent.SWITCH_MODEL: self._exec_switch_model,
            Intent.CREATE_DOCUMENT: self._exec_create_doc,
            Intent.START_SERVICE: self._exec_start_service,
            Intent.STOP_SERVICE: self._exec_stop_service,
            Intent.RESTART: self._exec_restart,
            Intent.GET_INFO: self._exec_get_info,
            Intent.LIST_MODELS: self._exec_list_models,
            Intent.CHAT: self._exec_chat,
            Intent.CONFIRM: self._exec_confirm,
            Intent.SELECT: self._exec_select,
            Intent.UNCLEAR: self._exec_unclear,
            Intent.CODE_TASK: self._exec_code_task,
            Intent.EXPLORE_REPO: self._exec_explore_repo,
        }
        
        handler = handlers.get(plan.intent, self._exec_chat)
        success, result = handler(plan)
        
        self.ctx.last_result = result
        
        # Cache successful resolutions
        if success and self.ctx.last_query:
            self.cache.store(self.ctx.last_query, plan, success)
        
        return success, result
    
    def _exec_code_task(self, plan: Plan) -> Tuple[bool, str]:
        """
        Execute a coding task using the phase system.
        EXPLORE → PLAN → APPLY → VERIFY
        """
        from core.phases import PhaseExecutor
        from core.printer import get_printer
        
        printer = get_printer()
        executor = PhaseExecutor(brain=self, printer=printer)
        
        # Start the task
        task = plan.target or self.ctx.last_query
        executor.start(task)
        
        # Run through all phases
        success = executor.run_to_completion()
        
        if success:
            # Summarize what was done
            changes = executor.state.changes
            if changes:
                summary = f"✓ Completed: {task}\n\nChanges made:"
                for c in changes:
                    summary += f"\n  - {c.action}: {c.file_path}"
                return True, summary
            else:
                return True, f"✓ Analyzed: {task}\n\nNo changes were needed."
        else:
            errors = executor.state.errors
            if errors:
                return False, f"✗ Failed: {errors[-1]}"
            return False, "✗ Task failed"
    
    def _exec_explore_repo(self, plan: Plan) -> Tuple[bool, str]:
        """Explore the repository and show structure"""
        from core.repo_explorer import get_explorer
        from core.printer import get_printer
        
        printer = get_printer()
        printer.step("Exploring repository")
        
        # Get current directory or specified path
        path = plan.target or os.getcwd()
        explorer = get_explorer(path)
        
        printer.substep("Scanning files...")
        repo_map = explorer.scan(force=True)
        
        printer.substep(f"Found {repo_map.file_count} files")
        
        # Build summary
        summary = explorer.get_summary()
        tree = explorer.get_tree(max_depth=2)
        
        return True, f"{summary}\n\nStructure:\n{tree}"
    
    def execute_with_agents(self, prompt: str) -> Tuple[bool, str]:
        """
        Execute using the new supervisor/operator agent system.
        
        This provides:
        - Intelligent task routing based on complexity
        - Multi-step planning for complex tasks
        - Automatic retry and error recovery
        - Tool-based execution
        """
        if self._executor is None:
            from core.execution import TaskExecutor
            self._executor = TaskExecutor(self.ollama, verbose=False)
        
        # Build context from current state
        from core.planning import Context as AgentContext
        context = AgentContext(
            cwd=os.getcwd(),
            recent_commands=[],  # Could track these
            last_result=self.ctx.last_result,
            language=self.ctx.language,
            editor=self.cache.get_preference("editor") or "nvim",
            terminal=self.cache.get_preference("terminal") or "kitty",
        )
        
        # Execute with new system
        result = self._executor.execute(prompt, context)
        
        # Update our context
        self.ctx.last_result = result.output
        
        return result.success, result.output
    
    def _exec_open_file(self, plan: Plan) -> Tuple[bool, str]:
        path = plan.target
        if not path:
            return False, "Welche Datei?" if self.ctx.language == 'de' else "Which file?"
        
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return False, f"Datei nicht gefunden: {path}" if self.ctx.language == 'de' else f"File not found: {path}"
        
        editor = plan.options.get("editor") or self.cache.get_preference("editor") or "nvim"
        terminal = plan.options.get("terminal", "same")
        
        try:
            if terminal == "new":
                term_app = self.cache.get_preference("terminal") or "kitty"
                subprocess.Popen([term_app, editor, path])
            else:
                subprocess.run([editor, path])
            
            self.ctx.last_path = path
            return True, f"✅ Geöffnet: {path}"
        except Exception as e:
            return False, f"Fehler: {e}"
    
    def _exec_open_url(self, plan: Plan) -> Tuple[bool, str]:
        url = plan.target
        if not url:
            return False, "Welche URL?" if self.ctx.language == 'de' else "Which URL?"
        
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        browser = plan.options.get("browser") or self.cache.get_preference("browser")
        
        try:
            if browser:
                try:
                    subprocess.Popen([browser, url])
                    return True, "✅ Im Browser geöffnet"
                except FileNotFoundError:
                    pass
            
            subprocess.Popen(["xdg-open", url])
            return True, "✅ Im Browser geöffnet"
        except Exception as e:
            return False, f"Fehler: {e}"
    
    def _exec_find_file(self, plan: Plan) -> Tuple[bool, str]:
        query = plan.target
        if not query:
            return False, "Was suchen?" if self.ctx.language == 'de' else "What to search?"
        
        # Build search
        patterns = [f"*{query}*", f"*{query.replace(' ', '*')}*"]
        dirs = [
            os.path.expanduser("~/.config"),
            os.path.expanduser("~"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Documents"),
        ]
        
        found = []
        for d in dirs:
            if not os.path.exists(d):
                continue
            for pattern in patterns:
                try:
                    result = subprocess.run(
                        ["find", d, "-maxdepth", "4", "-iname", pattern, "-type", "f"],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.stdout.strip():
                        found.extend(result.stdout.strip().split("\n"))
                except:
                    pass
        
        if found:
            unique = list(set(found))[:10]
            
            if len(unique) == 1:
                self.ctx.last_path = unique[0]
                return True, unique[0]
            else:
                self.ctx.pending_items = [{"path": p, "name": os.path.basename(p)} for p in unique]
                self.ctx.awaiting_selection = True
                lines = [f"{i+1}. {os.path.basename(p)}: {p}" for i, p in enumerate(unique)]
                return True, "Gefunden:\n" + "\n".join(lines) + "\n\nWelche? (Nummer)"
        
        return False, f"Keine Dateien gefunden für '{query}'"
    
    def _exec_find_path(self, plan: Plan) -> Tuple[bool, str]:
        """Just return the path without opening"""
        return True, plan.target or ""
    
    def _exec_search_web(self, plan: Plan) -> Tuple[bool, str]:
        """Search the web using the WebSearchTool"""
        query = plan.target
        if not query:
            return False, "Was suchen?"
        
        # Use the new web search tool (tries SearXNG first, then DuckDuckGo)
        result = self.tools.web_search.search(query, num_results=10)
        
        if not result.success:
            return False, result.error or "Search failed"
        
        if not result.data:
            return False, f"Keine Ergebnisse für '{query}'"
        
        # Store for selection
        self.ctx.pending_items = [{"url": r["url"], "title": r["title"]} for r in result.data]
        self.ctx.awaiting_selection = True
        
        return True, result.output + "\n\nWelches? (Nummer)"
    
    def _exec_scrape(self, plan: Plan) -> Tuple[bool, str]:
        """Scrape webpage using ScrapeTool"""
        target = plan.target
        if not target:
            return False, "Was scrapen?"
        
        # Resolve URL if needed
        if not target.startswith(('http://', 'https://')):
            url = self.cache.get_learned_url(target) or self.kb.get_website_url(target)
            if url:
                target = url
            else:
                # Offer to search for it
                return False, f"URL für '{target}' unbekannt. Soll ich danach suchen? (/search {target})"
        
        # Use the scrape tool
        result = self.tools.scrape.scrape(target)
        
        if result.success and result.data:
            self.ctx.last_scraped = result.data
            # Learn the URL for future use
            domain = result.data.get("domain", "")
            if domain:
                self.cache.learn_url(domain.split('.')[0], target)
        
        return result.success, result.output if result.success else result.error
    
    def _exec_scrape_html(self, plan: Plan) -> Tuple[bool, str]:
        target = plan.target
        if not target:
            return False, "Welche Website?"
        
        if not target.startswith(('http://', 'https://')):
            url = self.cache.get_learned_url(target) or self.kb.get_website_url(target)
            if url:
                target = url
            else:
                return False, f"URL für '{target}' unbekannt."
        
        try:
            import requests
            from bs4 import BeautifulSoup
            
            resp = requests.get(target, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Ryx/4.0"
            })
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Extract CSS
            css_content = []
            for style in soup.find_all('style'):
                css_content.append(style.string or "")
            for link in soup.find_all('link', rel='stylesheet'):
                href = link.get('href')
                if href:
                    try:
                        if not href.startswith('http'):
                            href = f"{target.rsplit('/', 1)[0]}/{href}"
                        css_resp = requests.get(href, timeout=5)
                        css_content.append(f"/* {href} */\n{css_resp.text}")
                    except:
                        pass
            
            # Save
            scrape_dir = get_data_dir() / "scrape"
            domain = target.split('/')[2] if '/' in target else target
            safe_name = re.sub(r'[^\w\-_.]', '_', domain)[:50]
            
            site_dir = scrape_dir / safe_name
            site_dir.mkdir(parents=True, exist_ok=True)
            
            html_file = site_dir / "index.html"
            css_file = site_dir / "styles.css"
            
            with open(html_file, 'w') as f:
                f.write(resp.text)
            with open(css_file, 'w') as f:
                f.write('\n\n'.join(css_content))
            
            return True, f"✅ HTML/CSS gescraped:\n   HTML: {html_file}\n   CSS: {css_file}"
            
        except Exception as e:
            return False, f"Fehler: {e}"
    
    def _exec_command(self, plan: Plan) -> Tuple[bool, str]:
        cmd = plan.target
        if not cmd:
            return False, "Welcher Befehl?"
        
        if plan.requires_confirmation:
            self.ctx.pending_plan = Plan(
                intent=Intent.RUN_COMMAND,
                target=cmd,
                requires_confirmation=False
            )
            self.ctx.awaiting_confirmation = True
            return True, f"Ausführen: {cmd}\nBist du sicher? (y/n)"
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            output = result.stdout or result.stderr
            return result.returncode == 0, output.strip() or "Ausgeführt"
        except subprocess.TimeoutExpired:
            return False, "Timeout"
        except Exception as e:
            return False, f"Fehler: {e}"
    
    def _exec_set_pref(self, plan: Plan) -> Tuple[bool, str]:
        key = plan.target
        value = plan.options.get("value", "")
        
        if key and value:
            self.cache.set_preference(key, value)
            return True, f"✅ {key} = {value}"
        
        return False, "Ungültige Einstellung"
    
    def _exec_switch_model(self, plan: Plan) -> Tuple[bool, str]:
        query = plan.target
        role = plan.options.get("role", "default")
        
        if not query:
            return False, "Welches Modell?"
        
        model = self.models.find(query)
        if model:
            self.cache.set_model(role, model)
            return True, f"✅ {role}: {model}"
        
        available = "\n".join([f"  - {m}" for m in self.models.available])
        return False, f"Modell '{query}' nicht gefunden.\n\nVerfügbar:\n{available}"
    
    def _exec_create_doc(self, plan: Plan) -> Tuple[bool, str]:
        topic = plan.target
        doc_type = plan.options.get("type", "lernzettel")
        
        if not topic:
            return False, "Welches Thema?"
        
        model = self.models.get("precision", True)
        
        prompt = f"""Erstelle einen {doc_type} über: {topic}

Format:
- Klare Überschriften
- Stichpunkte
- Wichtige Begriffe hervorheben
- Prüfungsrelevante Punkte
- Beispiele wenn hilfreich
- Max 2 Seiten

Sprache: Deutsch"""

        response = self.ollama.generate(
            prompt=prompt,
            model=model,
            system="Du erstellst präzise, gut strukturierte Lernmaterialien.",
            max_tokens=2000,
            temperature=0.3
        )
        
        if response.error:
            return False, f"Fehler: {response.error}"
        
        # Save
        docs_dir = get_data_dir() / "notes"
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        safe_topic = re.sub(r'[^\w\-_]', '_', topic)[:30]
        doc_file = docs_dir / f"{doc_type}_{safe_topic}_{datetime.now().strftime('%Y%m%d')}.md"
        
        with open(doc_file, 'w') as f:
            f.write(f"# {doc_type.title()}: {topic}\n\n")
            f.write(f"Erstellt: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n")
            f.write(response.response)
        
        self.ctx.last_path = str(doc_file)
        
        return True, f"✅ {doc_type.title()} erstellt:\n{doc_file}\n\nÖffnen? (y/n)"
    
    def _exec_start_service(self, plan: Plan) -> Tuple[bool, str]:
        service = (plan.target or "").lower()
        
        if service in ['searxng', 'searx', 'search']:
            try:
                import requests
                requests.get("http://localhost:8888", timeout=2)
                return True, "SearXNG läuft bereits"
            except:
                self.ctx.pending_plan = Plan(
                    intent=Intent.RUN_COMMAND,
                    target="docker run -d -p 8888:8080 --name searxng searxng/searxng"
                )
                self.ctx.awaiting_confirmation = True
                return True, "SearXNG starten? (y/n)"
        
        return False, f"Unbekannter Service: {service}"
    
    def _exec_stop_service(self, plan: Plan) -> Tuple[bool, str]:
        service = (plan.target or "").lower()
        
        if service in ['searxng', 'searx']:
            try:
                subprocess.run(["docker", "stop", "searxng"], capture_output=True, timeout=10)
                subprocess.run(["docker", "rm", "searxng"], capture_output=True, timeout=10)
                return True, "SearXNG gestoppt"
            except Exception as e:
                return False, f"Fehler: {e}"
        
        return False, f"Unbekannter Service: {service}"
    
    def _exec_restart(self, plan: Plan) -> Tuple[bool, str]:
        target = (plan.target or "").lower()
        
        if target in ['all', 'ryx', '']:
            self.ctx.pending_plan = Plan(
                intent=Intent.RUN_COMMAND,
                target="pkill -f ryx_main; sleep 1; ryx &"
            )
            self.ctx.awaiting_confirmation = True
            return True, "Ryx neustarten? (y/n)"
        
        return False, f"Neustart von '{target}' nicht unterstützt"
    
    def _exec_get_info(self, plan: Plan) -> Tuple[bool, str]:
        info_type = (plan.target or "").lower()
        now = datetime.now()
        
        if info_type in ['datetime', 'date', 'time', 'datum', 'zeit']:
            if self.ctx.language == 'de':
                return True, now.strftime("%A, %d. %B %Y - %H:%M Uhr")
            return True, now.strftime("%A, %B %d, %Y - %H:%M")
        
        return True, now.strftime("%Y-%m-%d %H:%M")
    
    def _exec_list_models(self, plan: Plan) -> Tuple[bool, str]:
        categorized = self.models.get_categorized()
        
        lines = ["📊 Verfügbare Modelle:\n"]
        
        for cat, models in categorized.items():
            if models:
                lines.append(f"\n{cat.upper()}:")
                for m in models:
                    lines.append(f"  • {m}")
        
        lines.append("\n\n⚙️ Aktuelle Einstellungen:")
        for role in ["default", "chatting", "precision", "fast"]:
            model = self.cache.get_model(role)
            if model:
                lines.append(f"  {role}: {model}")
        
        return True, "\n".join(lines)
    
    def _exec_chat(self, plan: Plan) -> Tuple[bool, str]:
        """
        Handle general chat - use web search for grounding when appropriate.
        Shows chain of thought for transparency.
        """
        from core.printer import get_printer
        printer = get_printer()
        
        if plan.target:
            return True, plan.target
        
        query = self.ctx.last_query
        
        # Determine if we should search first (for factual questions)
        should_search = self._should_search_first(query)
        search_context = ""
        search_results = []
        
        if should_search and self.browsing_enabled:
            printer.step("Searching web", f"'{query[:30]}...'")
            
            # Search web first for grounding
            search_result = self.tools.web_search.search(query, num_results=5)
            if search_result.success and search_result.data:
                search_results = search_result.data[:5]
                printer.substep(f"Found {len(search_results)} results")
                
                # Show top results briefly
                for r in search_results[:3]:
                    printer.search_result(r['title'][:60], r.get('content', '')[:80])
                
                # Build context from search results
                search_context = "\n\nSearch results to inform your answer:\n"
                for r in search_results:
                    search_context += f"- {r['title']}: {r.get('content', '')[:300]}\n"
                
                printer.step("Synthesizing answer from search results")
            else:
                printer.substep("No results found, using knowledge")
        
        # Generate response with search context
        model = self.models.get("balanced", self.precision_mode)
        printer.step("Thinking", f"[{model}]")
        
        system_prompt = """Du bist Ryx, ein hilfreicher AI-Assistent auf Arch Linux.
Antworte kurz und präzise. Wenn Suchergebnisse gegeben sind, nutze sie für deine Antwort.
Fasse die wichtigsten Informationen zusammen, statt nur Links zu zeigen."""
        
        if search_context:
            system_prompt += search_context
        
        response = self.ollama.generate(
            prompt=query,
            model=model,
            system=system_prompt,
            max_tokens=800,
            temperature=0.7
        )
        
        if response.error:
            return False, f"Fehler: {response.error}"
        
        return True, response.response
    
    def _should_search_first(self, query: str) -> bool:
        """Determine if we should search before answering"""
        q = query.lower()
        
        # Search for factual questions about things we might not know
        factual_indicators = [
            'what is', 'was ist', 'how to', 'wie',
            'explain', 'erkläre', 'tell me about', 'erzähl',
            'latest', 'newest', 'current', 'aktuell',
            'why does', 'warum', 'when did', 'wann',
            'documentation', 'docs', 'tutorial',
            'wer ist', 'who is',  # Questions about people
        ]
        
        # Don't search for personal/system questions
        personal_indicators = [
            'my', 'mein', 'config', 'file', 'datei',
            'open', 'öffne', 'find', 'finde', 'where',
            'hi', 'hello', 'hallo', 'hey',  # Greetings
        ]
        
        # Check if factual and not personal
        is_factual = any(f in q for f in factual_indicators)
        is_personal = any(p in q for p in personal_indicators)
        
        return is_factual and not is_personal
    
    def _exec_confirm(self, plan: Plan) -> Tuple[bool, str]:
        self.ctx.awaiting_confirmation = True
        self.ctx.pending_plan = plan
        return True, plan.question or "Bist du sicher? (y/n)"
    
    def _exec_select(self, plan: Plan) -> Tuple[bool, str]:
        self.ctx.awaiting_selection = True
        return True, plan.question or "Bitte wähle eine Option (Nummer)"
    
    def _exec_unclear(self, plan: Plan) -> Tuple[bool, str]:
        """Ask clarifying question - NEVER generic"""
        if plan.question:
            return True, plan.question
        
        query = self.ctx.last_query.lower() if self.ctx.last_query else ""
        
        # Generate specific question based on context
        if 'config' in query:
            return True, "Which config file? (e.g., hyprland, waybar, kitty)" if self.ctx.language == 'en' else "Welche Config-Datei? (z.B. hyprland, waybar, kitty)"
        elif 'open' in query or 'öffne' in query:
            return True, "What should I open? (file, website, or app?)" if self.ctx.language == 'en' else "Was soll ich öffnen? (Datei, Website, oder Programm?)"
        elif 'search' in query or 'suche' in query:
            return True, "Web search or local file search?" if self.ctx.language == 'en' else "Web-Suche oder lokale Dateisuche?"
        elif 'find' in query or 'finde' in query:
            return True, "What are you looking for? (filename or content)" if self.ctx.language == 'en' else "Was suchst du? (Dateiname oder Inhalt)"
        elif not query.strip():
            return True, "How can I help you?" if self.ctx.language == 'en' else "Wie kann ich dir helfen?"
        
        # Default with example
        examples = "Try: 'open youtube', 'find bashrc', 'hyprland config'" if self.ctx.language == 'en' else "Versuche: 'open youtube', 'find bashrc', 'hyprland config'"
        return True, f"I didn't understand that. {examples}" if self.ctx.language == 'en' else f"Das habe ich nicht verstanden. {examples}"
    
    def get_smarter(self) -> str:
        """Self-improvement: fix knowledge and clean cache"""
        self.cache.cleanup()
        
        updates = []
        
        # Verify and fix config paths
        for name, path in list(self.kb.config_paths.items()):
            expanded = os.path.expanduser(path)
            if not os.path.exists(expanded):
                # Try to find it
                try:
                    result = subprocess.run(
                        ["find", os.path.expanduser("~/.config"), "-name", f"*{name}*", "-type", "f"],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.stdout.strip():
                        found = result.stdout.strip().split('\n')[0]
                        self.kb.config_paths[name] = found
                        self.kb.arch_linux["config_paths"][name] = found
                        updates.append(f"Fixed: {name} → {found}")
                except:
                    pass
        
        if updates:
            self.kb.save()
        
        return "🧠 Self-improvement abgeschlossen\n" + "\n".join(updates) if updates else "Wissensbasis ist aktuell."
    
    def health_check(self) -> Dict[str, Any]:
        """Check system health - Ollama, models, etc."""
        health = {
            "ollama": False,
            "models": [],
            "default_model": None,
            "errors": []
        }
        
        try:
            # Check Ollama is reachable
            import requests
            response = requests.get(f"{self.ollama.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                health["ollama"] = True
                data = response.json()
                health["models"] = [m["name"] for m in data.get("models", [])]
                
                # Check if we have our preferred models
                preferred = ["qwen2.5:3b", "qwen2.5-coder:7b", "qwen2.5-coder:14b"]
                for model in preferred:
                    if any(model in m for m in health["models"]):
                        health["default_model"] = model
                        break
                
                if not health["models"]:
                    health["errors"].append("No models installed. Run: ollama pull qwen2.5:3b")
            else:
                health["errors"].append(f"Ollama returned status {response.status_code}")
        except requests.exceptions.ConnectionError:
            health["errors"].append("Cannot connect to Ollama. Is it running?")
        except Exception as e:
            health["errors"].append(f"Health check error: {e}")
        
        return health


# Global instance
_brain: Optional[RyxBrain] = None

def get_brain(ollama_client=None) -> RyxBrain:
    global _brain
    if _brain is None:
        if ollama_client is None:
            from core.ollama_client import OllamaClient
            from core.model_router import ModelRouter
            router = ModelRouter()
            ollama_client = OllamaClient(base_url=router.get_ollama_url())
        _brain = RyxBrain(ollama_client)
    return _brain
