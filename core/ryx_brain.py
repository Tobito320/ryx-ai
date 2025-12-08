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

Now with Tool-Only Mode for structured LLM outputs.
"""

import os
import re
import json
import sqlite3
import subprocess
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum

from core.paths import get_data_dir

logger = logging.getLogger(__name__)

# Import tool schema for Tool-Only Mode
try:
    from core.tool_schema import (
        ToolCall, ToolCallSequence, get_parser, 
        TOOL_ONLY_SYSTEM_PROMPT, get_tool_prompt
    )
    TOOL_SCHEMA_AVAILABLE = True
except ImportError:
    TOOL_SCHEMA_AVAILABLE = False


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
    created_files: List[str] = field(default_factory=list)  # Files created in code tasks
    last_task_files: List[str] = field(default_factory=list)  # Files from last code task


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
        # Don't cache service commands - they should always be re-evaluated
        nocache_intents = {'start_svc', 'stop_svc', 'restart', 'get_info'}
        if plan.intent.value in nocache_intents:
            return
        
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
    """Manages model selection - vLLM only (auto-detects)"""
    
    def __init__(self, cache: SmartCache):
        self.cache = cache
        self.available: List[str] = []
        self._detector = None
        self._refresh()
    
    def _refresh(self):
        """Refresh available models from vLLM using detector"""
        from core.model_detector import get_detector
        
        self._detector = get_detector()
        model_info = self._detector.detect()
        
        if model_info:
            self.available = [model_info.path]
        else:
            self.available = []
    
    def get(self, role: str, precision_mode: bool = False) -> str:
        """Get model for role - returns whatever vLLM is serving"""
        # Since vLLM serves one model, always return that
        if self.available:
            return self.available[0]
        
        # Fallback - try to detect again
        self._refresh()
        return self.available[0] if self.available else "unknown"
    
    def find(self, query: str) -> Optional[str]:
        """Find model by natural language query"""
        q = query.lower().strip()
        
        # Remove common prefixes
        for prefix in ['benutze', 'verwende', 'use', 'nutze', 'model', 'bitte', 'please']:
            q = q.replace(prefix, '').strip()
        
        # Exact match first
        for model in self.available:
            if q == model.lower():
                return model
        
        # Partial match
        for model in self.available:
            if q in model.lower() or model.lower() in q:
                return model
        
        # Fuzzy match - handle "qwen2.5:7" -> "qwen2.5:7b"
        for model in self.available:
            model_base = model.lower().replace('b', '').replace('-', '').replace('_', '')
            q_base = q.replace('b', '').replace('-', '').replace('_', '')
            if q_base in model_base or model_base.startswith(q_base):
                return model
        
        # Category match (fast, balanced, smart, precision)
        categories = {
            "fast": ["qwen2.5:1.5b", "qwen2.5:3b", "llama3.2:1b"],
            "balanced": ["qwen2.5:7b", "mistral:7b"],
            "smart": ["qwen2.5-coder:14b", "gpt-oss:20b"],
            "precision": ["gpt-oss:20b"],
        }
        for cat, models in categories.items():
            if cat in q:
                for m in models:
                    if m in self.available:
                        return m
        
        # Aliases
        aliases = {
            "gpt": "gpt-oss:20b", "gpt oss": "gpt-oss:20b", "gpt 20": "gpt-oss:20b",
            "mistral": "mistral:7b", "qwen": "qwen2.5:3b", "qwen 3b": "qwen2.5:3b",
            "qwen 7": "qwen2.5:7b", "qwen 7b": "qwen2.5:7b", 
            "qwen 1.5": "qwen2.5:1.5b", "qwen coder": "qwen2.5-coder:14b",
            "deepseek": "deepseek-coder:6.7b", "llama": "llama3.2:1b", "phi": "phi3:mini",
            "coder": "qwen2.5-coder:14b", "14b": "qwen2.5-coder:14b",
        }
        
        for alias, model in aliases.items():
            if alias in q and model in self.available:
                return model
        
        return None
    
    def get_categorized(self) -> Dict[str, List[str]]:
        """Get models organized by category"""
        # Refresh to get latest
        self._refresh()
        
        result = {cat: [] for cat in self.MODELS}
        result["other"] = []
        result["vllm"] = []
        
        categorized = set()
        for cat, models in self.MODELS.items():
            for model in models:
                if model in self.available:
                    result[cat].append(model)
                    categorized.add(model)
        
        for model in self.available:
            if model not in categorized:
                # Check if it's a vLLM model (path-like)
                if '/' in model or 'models' in model.lower():
                    result["vllm"].append(model)
                else:
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

    def __init__(self, llm_client):
        self.llm = llm_client
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
        
        # Response style (set by session_loop)
        self.response_style = "normal"  # normal, concise, explanatory, learning, formal
        
        # Conversation history for context (keeps last 10 messages)
        self._recent_messages: List[Dict[str, str]] = []
        
        # New agent system (can be toggled)
        self.use_new_agents = False
        self._executor = None
    
    def add_message(self, role: str, content: str):
        """Add a message to recent history for context"""
        self._recent_messages.append({'role': role, 'content': content})
        # Keep only last 10 messages
        if len(self._recent_messages) > 10:
            self._recent_messages = self._recent_messages[-10:]
    
    def enable_new_agents(self, enabled: bool = True):
        """Enable/disable the new supervisor/operator agent system"""
        self.use_new_agents = enabled
        if enabled and self._executor is None:
            from core.execution import TaskExecutor
            self._executor = TaskExecutor(self.llm, verbose=False)
    
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
        
        # Handle "show sources" after a search
        if self._is_show_sources(prompt):
            return self._handle_show_sources()
        
        # Handle y/n/number responses
        if self._is_quick_response(prompt):
            return self._handle_quick_response(prompt)
        
        # Handle follow-up modifiers ("shorter", "kürzer", "more detail")
        if self._is_followup_modifier(prompt):
            return Plan(intent=Intent.CHAT, options={"followup": True})
        
        # Handle context references ("open it", "edit that")
        plan = self._handle_context_reference(prompt)
        if plan:
            return plan
        
        # Check cache (skip in precision mode)
        if not self.precision_mode:
            cached = self.cache.lookup(prompt)
            if cached:
                return cached
        
        # IMPORTANT: Check for code tasks BEFORE knowledge resolution
        # This ensures "create file.py" goes to CODE_TASK, not OPEN_FILE
        if self._is_code_task(prompt):
            return Plan(intent=Intent.CODE_TASK, target=prompt)
        
        # Try knowledge-based resolution
        plan = self._resolve_from_knowledge(prompt)
        if plan:
            return plan
        
        # Check if this is smalltalk/greeting (should NOT trigger web search)
        if self._is_smalltalk(prompt):
            return Plan(intent=Intent.CHAT)
        
        # Check if this is clearly a chat question (not an action)
        if self._is_chat_question(prompt):
            return Plan(intent=Intent.CHAT)
        
        # Stage 2: LLM supervisor
        return self._supervisor_understand(prompt)
    
    def _is_code_task(self, prompt: str) -> bool:
        """Check if this is a coding task that needs EXPLORE→PLAN→APPLY→VERIFY"""
        p = prompt.lower()
        
        # Direct file creation patterns (high priority)
        import re
        # Match: "create file.py" or "create path/to/file.py"
        file_create_pattern = r'create\s+[\w/]+\.(py|js|ts|go|rs|java|sh|yaml|json|md)'
        if re.search(file_create_pattern, p):
            return True
        
        # Move file patterns - these are code/file management tasks
        if re.search(r'move\s+\S+\.(py|js|ts|go|rs|java)\s+to', p):
            return True
        if re.search(r'move\s+\S+/\S+\s+to', p):
            return True
        
        # Delete file/directory patterns
        if re.search(r'delete\s+(the\s+)?(file|directory|folder|src/)', p):
            return True
        
        # Modify file patterns - these should be code tasks, not file opens
        file_modify_pattern = r'(modifiziere|ändere|update|modify|change|fix|edit)\s+(the\s+)?(file\s+)?\w+\.(py|js|ts|html|css|go|rs|java)'
        if re.search(file_modify_pattern, p):
            return True
        
        # Direct "edit file" patterns
        if re.search(r'edit\s+(the\s+)?file', p):
            return True
        if re.search(r'add\s+(this\s+)?(exact\s+)?import', p):
            return True
        if re.search(r'add\s+.*import.*line', p):
            return True
        if re.search(r'add\s+.+\s+to\s+.+\.(py|js|ts|go)', p):
            return True
        # File path + action patterns
        if re.search(r'in\s+\S+\.(py|js|ts|go)\s*,?\s*(add|insert|modify)', p):
            return True
        # Pattern: "In some/path.py, ..." or "in some/path.py:" - anything referencing a file path with action
        if re.search(r'in\s+\S+/\S+\.(py|js|ts|go)\s*[,:.]', p):
            return True
        # Pattern: "replace ... with" in a file context
        if 'replace' in p and ('.py' in p or '.js' in p or '.ts' in p):
            return True
        # "add this line" patterns
        if re.search(r'add\s+(this\s+)?line', p):
            return True
        # Patterns with .py file mentioned
        if '.py' in p and any(x in p for x in ['add ', 'insert ', 'modify ', 'update ', 'change ']):
            return True
        
        # Coding task indicators - actions that modify code
        code_indicators = [
            'add a ', 'add new', 'create a ', 'create new', 'implement ', 'build ',
            'fix ', 'bug ', 'error in', 'refactor ', 'change the ', 'change code',
            'update the ', 'modify the ', 'edit the code', 'write a ', 'write code',
            'füge hinzu', 'erstelle', 'implementiere', 'baue',
            'fixe', 'fehler', 'ändere den', 'aktualisiere', 'modifiziere',
            'korrigiere', 'repariere', 'verbessere',  # German fix words
            'new function', 'new class', 'new method', 'new component',
            'new feature', 'new test', 'new style',
            'create function', 'create class', 'create module',
            'make a function', 'make a class', 'make a script',
        ]
        
        # Context words that indicate coding
        code_context = [
            'code', 'function', 'class', 'module', 'method',
            'component', 'script', 'program', 'app', 'api',
            'handler', 'service', 'controller', 'model',
            'theme', 'style', 'color', 'css',  # UI/theme related
            '.py', '.js', '.ts', '.tsx', '.rs', '.go', '.html', '.css',
            'funktion', 'klasse', 'modul', 'datei',
        ]
        
        # Exclusions - simple file operations (not coding)
        simple_ops = [
            'open ', 'öffne ', 'show ', 'zeig ', 'find ', 'finde ',
            'where ', 'wo ',
        ]
        
        # Content creation - NOT code tasks (spreadsheets, summaries, explanations)
        content_words = [
            'tabelle', 'spreadsheet', 'zusammenfassung', 'summary',
            'erklärung', 'explanation', 'lern', 'learn', 'prüfung', 'exam',
            'liste', 'list of', 'übersicht', 'overview', 'cheat sheet',
            'notizen', 'notes', 'axiome', 'theorie', 'theory', 'konzept',
            'definition', 'beispiel', 'example', 'deutsch', 'german',
            'english', 'mathe', 'math', 'schule', 'school', 'uni',
        ]
        
        has_code_indicator = any(i in p for i in code_indicators)
        has_code_context = any(c in p for c in code_context)
        is_simple_op = any(p.startswith(s) for s in simple_ops)
        is_content_creation = any(c in p for c in content_words)
        
        # If it's content creation (learning materials, etc.), it's NOT a code task
        if is_content_creation:
            return False
        
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
    
    def _is_smalltalk(self, prompt: str) -> bool:
        """Check if this is smalltalk/greeting that shouldn't trigger web search"""
        p = prompt.lower().strip()
        
        # Common greetings and smalltalk (German + English)
        smalltalk = [
            # Greetings
            'hi', 'hello', 'hey', 'hallo', 'moin', 'servus', 'guten tag',
            'good morning', 'good evening', 'guten morgen', 'guten abend',
            # How are you
            'wie gehts', 'wie geht es', 'wie geht es dir', 'wie gehts dir',
            'how are you', "how's it going", 'whats up', "what's up",
            'was geht', 'alles klar', 'alles gut',
            # Thanks
            'danke', 'thanks', 'thank you', 'thx', 'vielen dank', 'merci',
            # Bye
            'bye', 'tschüss', 'ciao', 'bis dann', 'see you', 'auf wiedersehen',
            # Acknowledgment
            'ok', 'okay', 'alright', 'got it', 'verstanden', 'cool', 'nice',
        ]
        
        return p in smalltalk or any(p.startswith(s + ' ') or p.startswith(s + ',') for s in smalltalk)
    
    def _is_followup_modifier(self, prompt: str) -> bool:
        """Check if this is a follow-up modifier like 'shorter', 'kürzer', 'more detail'"""
        p = prompt.lower().strip()
        
        # Single word or short phrase modifiers
        modifiers = [
            # Shorter
            'shorter', 'shorter please', 'kürzer', 'kurz', 'kurzer', 'kurzfassung',
            'brief', 'briefly', 'summarize', 'summary', 'zusammenfassung',
            'tldr', 'tl;dr',
            # Longer/more detail
            'longer', 'more', 'more detail', 'more details', 'elaborate',
            'explain more', 'länger', 'mehr', 'mehr detail', 'ausführlicher',
            'expand', 'go on', 'continue',
            # Simpler
            'simpler', 'simple', 'easy', 'einfacher', 'einfach',
            'eli5', 'like im 5', 'for beginners', 'für anfänger',
            # Different format
            'as list', 'as bullet points', 'als liste', 'in steps', 'step by step',
            # Language switch
            'in english', 'in german', 'auf deutsch', 'auf englisch',
            # Repeat/rephrase
            'again', 'repeat', 'rephrase', 'nochmal', 'anders',
        ]
        
        return p in modifiers or any(p.startswith(m + ' ') or p == m for m in modifiers)
    
    def _is_show_sources(self, prompt: str) -> bool:
        """Check if user is asking for search sources"""
        p = prompt.lower().strip()
        patterns = [
            'show sources', 'show me sources', 'sources', 'quellen',
            'zeig quellen', 'zeig mir quellen', 'what sources', 'welche quellen',
            'links', 'show links', 'zeig links', 'where from', 'woher'
        ]
        return p in patterns or any(p.startswith(pat) for pat in patterns)
    
    def _handle_show_sources(self) -> Plan:
        """Show sources from the last search"""
        if not self.ctx.pending_items:
            return Plan(intent=Intent.CHAT, target="Keine Quellen verfügbar. Zuerst suchen!")
        
        # Format sources nicely
        lines = ["📚 **Quellen:**\n"]
        for i, item in enumerate(self.ctx.pending_items[:5]):
            title = item.get('title', 'Untitled')
            url = item.get('url', '')
            lines.append(f"[{i+1}] {title}")
            lines.append(f"    {url}\n")
        
        return Plan(intent=Intent.CHAT, target="\n".join(lines))
    
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
        """Handle 'open it', 'edit that', 'öffne das mal', etc."""
        p = prompt.lower()
        
        # References to open/edit something (exclude German filler words)
        refs_open = ['open it', 'edit it', 'open that', 'öffne es', 'öffne das', 'bearbeite es', 
                     'open the', 'show that']
        refs_show = ['show it', 'zeig es', 'zeig das']
        
        # Check if this references recently created/worked files
        if any(r in p for r in refs_open) or 'open the' in p or 'öffne die' in p:
            # First check: recently created files from code tasks
            if hasattr(self.ctx, 'created_files') and self.ctx.created_files:
                # Return the most recently created file
                last_file = self.ctx.created_files[-1]
                return Plan(
                    intent=Intent.OPEN_FILE,
                    target=last_file,
                    options={"editor": self.cache.get_preference("editor") or "nvim"}
                )
            
            # Second check: last_path from context
            if self.ctx.last_path and os.path.exists(self.ctx.last_path):
                return Plan(
                    intent=Intent.OPEN_FILE,
                    target=self.ctx.last_path,
                    options={"editor": self.cache.get_preference("editor") or "nvim"}
                )
            
            # Third check: single pending item
            if len(self.ctx.pending_items) == 1:
                item = self.ctx.pending_items[0]
                self.ctx.pending_items = []
                if 'path' in item:
                    return Plan(intent=Intent.OPEN_FILE, target=item['path'])
                elif 'url' in item:
                    return Plan(intent=Intent.OPEN_URL, target=item['url'])
            
            # Check if referring to code task results
            if self.ctx.last_intent == Intent.CODE_TASK and self.ctx.last_result:
                # Extract any file paths from the last result
                import re
                paths = re.findall(r'(?:→|Target:)\s*([^\s\n]+\.\w+)', self.ctx.last_result)
                if paths:
                    for path in paths:
                        if os.path.exists(path):
                            return Plan(intent=Intent.OPEN_FILE, target=path)
                        # Try with cwd
                        full_path = os.path.join(os.getcwd(), path)
                        if os.path.exists(full_path):
                            return Plan(intent=Intent.OPEN_FILE, target=full_path)
        
        return None
    
    def _resolve_from_knowledge(self, prompt: str) -> Optional[Plan]:
        """Try to resolve using knowledge base - no LLM needed"""
        p = prompt.lower()
        
        # Service status queries
        service_words = ['service', 'status', 'dienst', 'ryxhub', 'hub']
        status_words = ['status', 'running', 'läuft', 'aktiv', 'zeige', 'show']
        if any(s in p for s in service_words) and any(st in p for st in status_words):
            return Plan(intent=Intent.GET_INFO, target="service_status")
        
        # Start/Stop service - also catch "öffne hub", "launch hub", etc.
        start_words = ['starte', 'start', 'öffne', 'launch', 'aktiviere', 'turn on', 'enable']
        stop_words = ['stoppe', 'stop', 'beende', 'schließe', 'kill', 'turn off', 'disable']
        
        # vLLM/LLM service
        vllm_names = ['vllm', 'v-llm', 'llm', 'model', 'inference', 'gpu', 'ai model']
        if any(s in p for s in vllm_names):
            if any(w in p for w in stop_words):
                return Plan(intent=Intent.STOP_SERVICE, target="vllm")
            elif any(w in p for w in start_words):
                return Plan(intent=Intent.START_SERVICE, target="vllm")
        
        # RyxHub service
        hub_names = ['ryxhub', 'ryx hub', 'hub', 'webui', 'service', 'dashboard', 'web interface']
        if any(s in p for s in hub_names):
            if any(w in p for w in stop_words):
                return Plan(intent=Intent.STOP_SERVICE, target="ryxhub")
            elif any(w in p for w in start_words):
                return Plan(intent=Intent.START_SERVICE, target="ryxhub")
        
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
        
        # Filter out action words and German filler words
        skip = {'open', 'edit', 'show', 'öffne', 'zeig', 'bearbeite', 'in', 'new', 'same', 'terminal', 
                'neues', 'neuem', 'selben', 'diesem', 'the', 'my', 'mein', 'meine', 'look', 'at', 'for',
                # German filler words that shouldn't be interpreted as config names
                'mal', 'doch', 'halt', 'bitte', 'jetzt', 'gleich', 'dann', 'noch', 'auch', 'nur',
                'einfach', 'schnell', 'kurz', 'eben', 'gerade', 'einmal', 'nochmal', 'erstmal'}
        
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
        # Use new model router
        from core.model_router import select_model
        model_config = select_model(prompt)
        model = model_config.name
        
        context = {
            "last_query": self.ctx.last_query or "none",
            "last_result": (self.ctx.last_result or "none")[:100],
            "last_path": self.ctx.last_path or "none",
            "pending_items": str(self.ctx.pending_items[:3]) if self.ctx.pending_items else "none",
            "language": self.ctx.language,
            "prompt": prompt
        }
        
        response = self.llm.generate(
            prompt=self.SUPERVISOR_PROMPT.format(**context),
            model=model,
            system="Du bist ein JSON-Parser. Antworte NUR mit validem JSON. Keine Erklärungen.",
            max_tokens=300,
            temperature=0.1
        )
        
        if response.error:
            self.fail_count += 1
            if self.fail_count >= 2:
                # Retry with fallback model
                self.fail_count = 0
                from core.model_router import get_router, ModelRole
                fallback = get_router().get_model_by_role(ModelRole.FALLBACK)
                response = self.llm.generate(
                    prompt=self.SUPERVISOR_PROMPT.format(**context),
                    model=fallback.name,
                    system="Du bist ein JSON-Parser. Antworte NUR mit validem JSON.",
                    max_tokens=300,
                    temperature=0.1
                )
            
            if response.error:
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
        
        # Cache successful resolutions (but not code tasks - they should always be re-evaluated)
        if success and self.ctx.last_query and plan.intent != Intent.CODE_TASK:
            # Also don't cache if the query looks like a code task (safety check)
            if not self._is_code_task(self.ctx.last_query):
                self.cache.store(self.ctx.last_query, plan, success)
        
        return success, result
    
    def _exec_code_task(self, plan: Plan) -> Tuple[bool, str]:
        """
        Execute a coding task using the phase system.
        EXPLORE → PLAN → APPLY → VERIFY
        
        Uses autonomous retry mode for self-healing when issues are detected.
        """
        from core.phases import PhaseExecutor
        import os
        try:
            from core.cli_ui import get_ui
        except ImportError:
            from core.rich_ui import get_ui
        
        ui = get_ui()
        
        # Get the working directory - this is where files should be created
        working_dir = os.getcwd()
        
        executor = PhaseExecutor(brain=self, ui=ui, working_dir=working_dir)
        
        # Start the task
        task = plan.target or self.ctx.last_query
        executor.start(task)
        
        # Run through all phases with autonomous retry enabled
        # This allows ryx to self-heal without human intervention
        success = executor.run_to_completion(autonomous_retries=3)
        
        if success:
            # Summarize what was done
            changes = executor.state.changes
            if changes:
                summary = f"✓ Completed: {task}\n\nFiles created/modified:"
                created_files = []
                for c in changes:
                    summary += f"\n  ✓ {c.file_path}"
                    created_files.append(c.file_path)
                
                # Store created files for context ("open that")
                self.ctx.created_files = created_files
                self.ctx.last_task_files = created_files
                if created_files:
                    self.ctx.last_path = created_files[-1]
                
                summary += f"\n\nÖffnen? (Nummer oder 'öffne das')"
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
        try:
            from core.cli_ui import get_ui
        except ImportError:
            from core.rich_ui import get_ui
        
        ui = get_ui()
        ui.phase_start("EXPLORE", "Scanning repository")
        
        # Get current directory or specified path
        path = plan.target or os.getcwd()
        explorer = get_explorer(path)
        
        ui.task_start("Scanning files")
        repo_map = explorer.scan(force=True)
        ui.task_done("Scanning files", f"Found {repo_map.file_count} files")
        
        # Build summary
        summary = explorer.get_summary()
        tree = explorer.get_tree(max_depth=2)
        
        ui.phase_done("EXPLORE", f"{repo_map.file_count} files indexed")
        
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
            self._executor = TaskExecutor(self.llm, verbose=False)
        
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
    
    def execute_with_tools(self, task: str, max_iterations: int = 10) -> Tuple[bool, str]:
        """
        Execute a task using Tool-Only Mode.
        
        The LLM generates structured tool calls, which are executed one by one.
        Results are fed back to the LLM for the next action.
        
        Args:
            task: The task description
            max_iterations: Maximum number of tool call iterations
            
        Returns:
            (success, result_message)
        """
        if not TOOL_SCHEMA_AVAILABLE:
            return False, "Tool schema not available"
        
        from core.agent_tools import get_agent_tools
        tools = get_agent_tools()
        
        # Get relevant files for context
        context_files = []
        try:
            from ryx_pkg.repo import RepoExplorer
            explorer = RepoExplorer(verbose=False)
            context_files = explorer.find_for_task(task, max_files=10)
        except Exception as e:
            logger.debug(f"RepoExplorer not available: {e}")
        
        # Build initial context
        context = ""
        if context_files:
            context = "Available files:\n" + "\n".join(f"  - {f}" for f in context_files)
        
        messages = []
        results = []
        
        for iteration in range(max_iterations):
            # Build prompt with history
            if messages:
                history = "\n\nPrevious actions:\n"
                for msg in messages[-5:]:  # Last 5 messages
                    history += f"  {msg}\n"
                full_context = context + history
            else:
                full_context = context
            
            # Generate tool call
            response = self.llm.generate_tool_call(
                task=task,
                context=full_context,
                available_files=context_files,
                max_tokens=1500
            )
            
            if response.error:
                return False, f"LLM error: {response.error}"
            
            if not response.tool_calls:
                # No valid tool calls - treat raw response as completion
                return True, response.response
            
            # Execute each tool call
            for tool_call in response.tool_calls:
                if tool_call.tool == "complete":
                    # Task completion signal
                    final_message = tool_call.params.get("message", "Task completed")
                    if results:
                        return True, f"{final_message}\n\nActions taken:\n" + "\n".join(results)
                    return True, final_message
                
                # Execute the tool
                result = tools.execute(tool_call.tool, **tool_call.params)
                
                # Record result
                if result.success:
                    result_msg = f"✓ {tool_call.tool}: {result.output[:100]}"
                else:
                    result_msg = f"✗ {tool_call.tool}: {result.error or 'Failed'}"
                
                results.append(result_msg)
                messages.append(f"{tool_call.tool}({tool_call.params}) -> {result_msg}")
                
                logger.debug(f"Tool call: {tool_call.tool} -> {result.success}")
            
            # Check if marked as complete
            if response.is_complete:
                if results:
                    return True, "Task completed.\n\nActions:\n" + "\n".join(results)
                return True, "Task completed"
        
        # Max iterations reached
        return False, f"Max iterations ({max_iterations}) reached.\n\nActions so far:\n" + "\n".join(results)
    
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
        """Search the web and synthesize an answer from results"""
        query = plan.target
        if not query:
            return False, "Was suchen?"
        
        # Use the new web search tool (tries SearXNG first, then DuckDuckGo)
        result = self.tools.web_search.search(query, num_results=5)
        
        if not result.success:
            return False, result.error or "Search failed"
        
        if not result.data:
            return False, f"Keine Ergebnisse für '{query}'"
        
        # Store sources for follow-up
        self.ctx.pending_items = [{"url": r.get("url", ""), "title": r.get("title", ""), "snippet": r.get("snippet", "")} for r in result.data]
        self.ctx.last_query = query
        
        # Build context from snippets
        context_parts = []
        for i, r in enumerate(result.data[:5]):
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            url = r.get("url", "")
            context_parts.append(f"[{i+1}] {title}\n{snippet}\n")
        
        search_context = "\n".join(context_parts)
        
        # Synthesize answer using LLM
        synth_prompt = f"""Based on these search results, answer the user's question.
Be concise and direct. Cite sources with [1], [2], etc.

Question: {query}

Search Results:
{search_context}

Answer (be concise, 2-3 sentences max):"""

        # Apply response style
        style_adjustments = {
            "concise": "ONE sentence only. Essential facts only. No filler.",
            "explanatory": "Explain in detail with context and examples.",
            "learning": "Teach step-by-step, help the user understand.",
            "formal": "Use professional, formal language.",
        }
        if self.response_style in style_adjustments:
            synth_prompt = synth_prompt.replace(
                "be concise, 2-3 sentences max",
                style_adjustments[self.response_style]
            )

        try:
            resp = self.llm.generate(
                prompt=synth_prompt,
                model=self.models.get("balanced"),
                max_tokens=300 if self.response_style == "concise" else 500,
                temperature=0.3
            )
            
            if resp.response:
                # Add note about showing sources
                answer = resp.response.strip()
                # Store for follow-up context
                self.add_message('assistant', answer)
                return True, f"{answer}\n\n[dim]'show sources' für Quellen[/]"
        except Exception as e:
            logger.warning(f"Synthesis failed: {e}")
        
        # Fallback: just show results
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

        response = self.llm.generate(
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
        
        # vLLM - GPU inference
        if service in ['vllm', 'llm', 'model', 'inference', 'gpu']:
            try:
                from core.docker_services import start_service
                result = start_service("vllm")
                
                if result.get('success'):
                    return True, "✅ vLLM starting...\n  • Container: ryx-vllm\n  • Port: http://localhost:8001\n  • Model: Qwen2.5-Coder-14B-AWQ"
                else:
                    error = result.get('error', 'Unknown error')
                    if 'already' in error.lower() or 'running' in error.lower():
                        return True, "ℹ️ vLLM already running at http://localhost:8001"
                    return False, f"❌ Failed to start vLLM: {error}"
            except ImportError:
                return False, "❌ docker_services not found"
            except Exception as e:
                return False, f"❌ Error: {e}"
        
        # RyxHub - Web UI
        if service in ['ryxhub', 'hub', 'webui', 'ui']:
            try:
                from core.service_manager import ServiceManager
                manager = ServiceManager()
                result = manager.start_ryxhub()
                
                if result.get('success'):
                    info = result.get('info', [])
                    return True, "✅ RyxHub gestartet:\n" + "\n".join(f"  • {i}" for i in info)
                else:
                    error = result.get('error', 'Unbekannter Fehler')
                    # If already running, show info
                    if 'already running' in error.lower():
                        info = result.get('info', ['http://localhost:5173'])
                        return True, "ℹ️ RyxHub läuft bereits:\n" + "\n".join(f"  • {i}" for i in info)
                    return False, f"❌ Fehler beim Starten: {error}"
            except ImportError:
                return False, "❌ ServiceManager nicht gefunden"
            except Exception as e:
                return False, f"❌ Fehler: {e}"
        
        # SearXNG - Search engine
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
        
        # vLLM - GPU inference
        if service in ['vllm', 'llm', 'model', 'inference', 'gpu']:
            try:
                from core.docker_services import stop_service
                result = stop_service("vllm")
                
                if result.get('success'):
                    return True, "✅ vLLM stopped"
                else:
                    error = result.get('error', 'Unknown error')
                    if 'not running' in error.lower():
                        return True, "ℹ️ vLLM was not running"
                    return False, f"❌ Failed to stop vLLM: {error}"
            except ImportError:
                return False, "❌ docker_services not found"
            except Exception as e:
                return False, f"❌ Error: {e}"
        
        # RyxHub - Web UI
        if service in ['ryxhub', 'hub', 'webui', 'ui']:
            try:
                from core.service_manager import ServiceManager
                manager = ServiceManager()
                result = manager.stop_ryxhub()
                
                if result.get('success'):
                    stopped = result.get('stopped', [])
                    return True, "✅ RyxHub gestoppt:\n" + "\n".join(f"  • {s}" for s in stopped)
                else:
                    error = result.get('error', 'Unbekannter Fehler')
                    if 'not running' in error.lower():
                        return True, "ℹ️ RyxHub läuft nicht"
                    return False, f"❌ Fehler: {error}"
            except ImportError:
                return False, "❌ ServiceManager nicht gefunden"
            except Exception as e:
                return False, f"❌ Fehler: {e}"
        
        # SearXNG - Search engine
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
        
        if info_type in ['service_status', 'status', 'services']:
            from core.service_manager import ServiceManager
            manager = ServiceManager()
            status = manager.get_status()
            
            lines = ["🔍 Service Status:\n"]
            for svc, info in status.items():
                state = "🟢 Running" if info.get('running') else "🔴 Stopped"
                lines.append(f"  {svc}: {state}")
                if info.get('ports'):
                    for port_info in info['ports']:
                        lines.append(f"    └─ {port_info}")
            
            return True, "\n".join(lines)
        
        return True, now.strftime("%Y-%m-%d %H:%M")
    
    def _exec_list_models(self, plan: Plan) -> Tuple[bool, str]:
        """List models from vLLM - shows what's actually loaded"""
        import requests
        
        vllm_url = os.environ.get('VLLM_BASE_URL', 'http://localhost:8001')
        lines = []
        
        try:
            resp = requests.get(f"{vllm_url}/v1/models", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                loaded_models = [m["id"] for m in data.get("data", [])]
                
                if loaded_models:
                    lines.append("Loaded Models (vLLM):")
                    for m in loaded_models:
                        # Show short name
                        short_name = m.split('/')[-1] if '/' in m else m
                        lines.append(f"  ✓ {short_name}")
                        lines.append(f"    Path: {m}")
                else:
                    lines.append("No models loaded in vLLM")
            else:
                lines.append(f"vLLM returned status {resp.status_code}")
        except requests.exceptions.ConnectionError:
            lines.append("vLLM not running")
            lines.append("Start with: ryx start vllm")
        except Exception as e:
            lines.append(f"Error checking models: {e}")
        
        # Show available models on disk
        models_dir = "/home/tobi/vllm-models"
        if os.path.exists(models_dir):
            lines.append("\nAvailable on disk:")
            for size in ["small", "medium", "large"]:
                size_path = os.path.join(models_dir, size)
                if os.path.exists(size_path):
                    for category in os.listdir(size_path):
                        cat_path = os.path.join(size_path, category)
                        if os.path.isdir(cat_path):
                            for model in os.listdir(cat_path):
                                model_path = os.path.join(cat_path, model)
                                if os.path.isdir(model_path):
                                    lines.append(f"  • {model} ({size}/{category})")
        
        return True, "\n".join(lines)
    
    def _exec_chat(self, plan: Plan) -> Tuple[bool, str]:
        """
        Handle general chat - use web search for grounding when appropriate.
        Shows chain of thought with Rich UI for transparency.
        
        IMPORTANT: Uses conversation context to maintain coherence.
        Follow-up requests like "shorter" / "kürzer" use previous response.
        """
        try:
            from core.cli_ui import get_ui
        except ImportError:
            from core.rich_ui import get_ui
        ui = get_ui()
        
        # Return target directly for cancel messages, sources display, and other pre-set responses
        if plan.target and (plan.target.startswith(("Abgebrochen", "Cancelled", "Nichts", "📚", "Keine Quellen", "No sources"))
                           or "Quellen" in plan.target):
            return True, plan.target
        
        query = self.ctx.last_query
        
        # ══════════════════════════════════════════════════════════════════════
        # FOLLOW-UP DETECTION: Check if this is a modifier to previous response
        # ══════════════════════════════════════════════════════════════════════
        is_followup = plan.options.get("followup", False) or self._is_followup_modifier(query)
        
        # Build conversation context from recent history
        conversation_context = ""
        last_assistant_msg = ""
        if hasattr(self, '_recent_messages') and self._recent_messages:
            # Get last 6 messages for context
            for msg in self._recent_messages[-6:]:
                role = msg.get('role', 'user')
                content = msg.get('content', '')[:800]
                if content and content != "__STREAMED__":
                    conversation_context += f"{role}: {content}\n"
                    if role == 'assistant':
                        last_assistant_msg = content
        
        # For follow-ups, we MUST have context
        if is_followup and not last_assistant_msg:
            return True, "I don't have a previous response to modify. What would you like to know?" if self.ctx.language == 'en' else "Ich habe keine vorherige Antwort zum Anpassen. Was möchtest du wissen?"
        
        # Determine if we should search first (for factual questions)
        # DON'T search for follow-ups!
        should_search = self._should_search_first(query) and not is_followup
        search_context = ""
        search_results = []
        
        if should_search and self.browsing_enabled:
            # Use new visual searching indicator
            if hasattr(ui, 'searching'):
                ui.searching(query[:40])
            else:
                ui.step_start(f"Searching '{query[:35]}...'")
            
            # Search web first for grounding
            search_result = self.tools.web_search.search(query, num_results=5)
            if search_result.success and search_result.data:
                search_results = search_result.data[:5]
                if hasattr(ui, 'searching'):
                    ui.searching(query[:40], len(search_results))
                ui.step_done("Search", f"{len(search_results)} results")
                
                # Show top results
                ui.search_results(search_results, query=query, limit=3)
                
                # IMPORTANT: Store sources for /sources and "show sources" command
                self.ctx.pending_items = [
                    {"url": r.get("url", ""), "title": r.get("title", ""), "snippet": r.get("content", "")} 
                    for r in search_results
                ]
                self.ctx.last_query = query
                
                # Build context from search results - include more content for educational queries
                search_context = "\n\nSuchergebnisse - NUTZE DIESE INFORMATIONEN für deine Antwort:\n"
                for i, r in enumerate(search_results, 1):
                    content = r.get('content', '')[:500]  # More content per result
                    search_context += f"[{i}] {r['title']}: {content}\n\n"
            else:
                ui.step_done("Search", "no results")
        
        # Select model based on precision mode BEFORE other checks
        from core.model_router import get_router, ModelRole
        if self.precision_mode:
            model = get_router().get_model_by_role(ModelRole.REASON).name
        else:
            from core.model_router import select_model
            model_config = select_model(query)
            model = model_config.name
        
        # Build style-specific instructions
        style = getattr(self, 'response_style', 'normal')
        
        # CONCISE MODE: Detect greetings and force ultra-short responses
        query_lower = query.lower().strip()
        greeting_responses = {
            'hi': 'Hey!',
            'hey': 'Hi!',
            'hello': 'Hey!',
            'hallo': 'Hey!',
            'hii': 'Hey!',
            'heyy': 'Hi!',
            'yo': 'Yo!',
            'sup': 'Hey!',
            'hi!': 'Hey!',
            'hey!': 'Hi!',
            'hello!': 'Hey!',
        }
        
        # Check for greeting + simple question patterns
        how_are_you_patterns = ['how are you', 'wie gehts', 'how r u', 'whats up', "what's up", 'wassup']
        
        if style == 'concise':
            # Instant response for pure greetings
            if query_lower in greeting_responses:
                instant = greeting_responses[query_lower]
                ui.stream_start(model)
                ui.stream_token(instant)
                ui.stream_end()
                self.add_message('assistant', instant)
                return True, "__STREAMED__"
            
            # Short response for "how are you" type questions
            if any(p in query_lower for p in how_are_you_patterns):
                instant = "Good, thanks! You?"
                ui.stream_start(model)
                ui.stream_token(instant)
                ui.stream_end()
                self.add_message('assistant', instant)
                return True, "__STREAMED__"
        
        style_instructions = {
            'normal': "Be clear and helpful. Keep responses focused.",
            'concise': """ULTRA CONCISE MODE - CRITICAL RULES:
- For greetings: ONE word or TWO words MAX ("Hey!", "Good, you?")
- For simple questions: ONE sentence ONLY
- For complex questions: MAX 2 sentences
- NEVER use phrases like "I'm an AI", "I don't have feelings", "As an assistant"
- NO filler, NO pleasantries, NO repetition
- Respond like a friend texting, not a formal assistant
- Examples: "hi" → "Hey!", "how are you" → "Good, you?", "what time is it" → "Check your system clock." """,
            'explanatory': "Explain in detail with examples, context, and background information.",
            'learning': "Teach step-by-step like for a student - with context, examples, and memory aids.",
            'formal': "Respond formally and professionally, as in documentation."
        }
        style_hint = style_instructions.get(style, style_instructions['normal'])
        
        # Reduce max_tokens for concise mode
        max_tokens = 100 if style == 'concise' else 800
        
        # Build system prompt with follow-up awareness
        if is_followup:
            system_prompt = f"""Du bist Ryx, ein hilfreicher AI-Assistent.

Der User hat eine Folgeanfrage zu deiner letzten Antwort gestellt.
DEINE LETZTE ANTWORT WAR:
{last_assistant_msg}

USER FRAGT JETZT: "{query}"

STIL: {style_hint}

Passe deine Antwort entsprechend an:
- "kürzer/shorter" → Fasse die Kernpunkte in 1-2 Sätzen zusammen
- "mehr/more" → Gib mehr Details zu deiner Antwort
- "anders/different" → Erkläre es auf andere Weise

Antworte DIREKT auf das Thema deiner letzten Antwort!"""
        else:
            system_prompt = f"""Du bist Ryx, ein hilfreicher AI-Assistent auf Arch Linux.
{style_hint}

WICHTIG für Suchergebnisse:
- Wenn du die exakten Fakten NICHT in den Suchergebnissen findest, sage ehrlich: "Die Suchergebnisse enthalten nicht alle Details. Hier ist was ich weiß, bitte verifiziere:"
- Erfinde KEINE Fakten die nicht in den Quellen stehen
- Zitiere mit [1], [2], etc."""
            
            if conversation_context:
                system_prompt += f"\n\nBisheriges Gespräch:\n{conversation_context}"
            
            if search_context:
                system_prompt += search_context
        
        # Show synthesizing indicator before streaming
        if hasattr(ui, 'synthesizing'):
            ui.synthesizing("Generating response...")
        
        # Stream the response token by token
        ui.stream_start(model)
        full_response = ""
        
        try:
            for token in self.llm.generate_stream(
                prompt=query,
                model=model,
                system=system_prompt,
                max_tokens=max_tokens,
                temperature=0.7
            ):
                ui.stream_token(token)
                full_response += token
            
            # Only show stats if we got actual content
            if full_response.strip():
                ui.stream_end()
                self.add_message('assistant', full_response.strip())
                return True, "__STREAMED__"
            else:
                # Empty response - don't show misleading stats
                ui._stream_state = None  # Cancel stream without stats
                return True, "I couldn't generate a response. Please try rephrasing."
            
        except Exception as e:
            ui.stream_end()
            return False, f"Fehler: {e}"
    
    def _should_search_first(self, query: str) -> bool:
        """Determine if we should search before answering"""
        q = query.lower().strip()
        
        # Short conversational queries - NEVER search
        short_greetings = [
            'hi', 'hello', 'hallo', 'hey', 'wie gehts', 'wie geht', 
            'how are you', 'whats up', 'was geht', 'yo', 'moin',
            'guten tag', 'guten morgen', 'guten abend', 'good morning',
            'danke', 'thanks', 'ok', 'okay', 'ja', 'nein', 'yes', 'no',
            'shorter', 'kürzer', 'longer', 'mehr', 'show sources', 'sources'
        ]
        if q in short_greetings or any(q.startswith(g) for g in short_greetings):
            return False
        
        # Very short queries without question words are conversational
        # But allow single technical terms (5+ chars that are alpha)
        if len(q) < 5:
            return False
        
        # Don't search for personal/system questions
        personal_indicators = [
            'my', 'mein', 'config', 'file', 'datei',
            'open', 'öffne', 'find', 'finde',
        ]
        # But DO search for educational content creation
        educational_keywords = [
            'lern', 'axiom', 'theorie', 'prüfung', 'exam', 'schule', 'school',
            'watzlawick', 'kommunikation', 'definition', 'konzept',
        ]
        is_educational = any(e in q for e in educational_keywords)
        
        if any(p in q for p in personal_indicators) and not is_educational:
            return False
        
        # Search for factual questions - be more aggressive
        factual_indicators = [
            'what is', 'was ist', 'what are', 'was sind',
            'how to', 'how do', 'wie macht man', 'wie kann ich',
            'explain', 'erkläre', 'tell me about', 'erzähl mir',
            'latest', 'newest', 'current', 'aktuell',
            'why does', 'warum', 'when did', 'wann',
            'documentation', 'docs', 'tutorial',
            'wer ist', 'who is', 'where is', 'wo ist',
            'difference between', 'unterschied zwischen',
            'best', 'beste', 'recommended', 'empfohlen',
            'axiom', 'theorie', 'definition', 'lern-tabelle', 'übersicht',
        ]
        
        # "wie" needs more context (avoid "wie gehts" matching)
        has_wie = 'wie ' in q and len(q) > 15 and 'gehts' not in q and 'geht' not in q
        
        # Single word that could be a topic (e.g., "hyprland", "wayland")
        is_single_topic = ' ' not in q and len(q) > 4 and q.isalpha()
        
        return any(f in q for f in factual_indicators) or has_wie or is_single_topic
    
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
        """Check system health - vLLM only"""
        health = {
            "backend_available": False,
            "vllm": False,
            "models": [],
            "default_model": None,
            "errors": []
        }
        
        import requests
        
        # Check vLLM first (preferred)
        try:
            response = requests.get("http://localhost:8001/health", timeout=3)
            if response.status_code == 200:
                health["vllm"] = True
                health["backend_available"] = True
                health["vllm"] = True
                # Get actual model from vLLM
                try:
                    import requests
                    resp = requests.get(f"{self.llm.base_url}/v1/models", timeout=5)
                    if resp.status_code == 200:
                        models = resp.json().get("data", [])
                        if models:
                            health["models"] = [m["id"] for m in models]
                            health["default_model"] = models[0]["id"]
                except:
                    health["models"] = ["qwen2.5-7b-gptq"]
                    health["default_model"] = "qwen2.5-7b-gptq"
                return health
        except:
            pass
        
        # Check if this is a vLLM wrapper
        if hasattr(self.llm, 'backend'):
            try:
                backend_health = self.llm.backend.health_check()
                if backend_health.get("healthy"):
                    health["vllm"] = True
                    health["backend_available"] = True
                    # Get actual model
                    try:
                        import requests
                        resp = requests.get(f"{self.llm.base_url}/v1/models", timeout=5)
                        if resp.status_code == 200:
                            models = resp.json().get("data", [])
                            if models:
                                health["models"] = [m["id"] for m in models]
                                health["default_model"] = models[0]["id"]
                    except:
                        health["models"] = ["qwen2.5-7b-gptq"]
                        health["default_model"] = "qwen2.5-7b-gptq"
                    return health
            except:
                pass
        
        # Try vLLM directly (in case wrapper doesn't have backend attribute)
        try:
            import requests
            resp = requests.get("http://localhost:8001/health", timeout=5)
            if resp.status_code == 200:
                health["vllm"] = True
                health["backend_available"] = True
                resp = requests.get("http://localhost:8001/v1/models", timeout=5)
                if resp.status_code == 200:
                    models = resp.json().get("data", [])
                    if models:
                        health["models"] = [m["id"] for m in models]
                        health["default_model"] = models[0]["id"]
                return health
        except:
            pass
        
        # No backend available
        health["errors"].append("No LLM backend. Run: ryx start vllm")
        
        return health


# Global instance
_brain: Optional[RyxBrain] = None

def get_brain(llm_client=None, prefer_vllm: bool = True) -> RyxBrain:
    """
    Get or create the global RyxBrain instance.
    
    Args:
        llm_client: Optional LLMBackend/VLLMBackend client
        prefer_vllm: Always True - we only use vLLM now
    """
    global _brain
    if _brain is None:
        # If a backend was provided, wrap it
        if llm_client is not None:
            from core.llm_backend import VLLMBackend, LLMBackend
            if isinstance(llm_client, (VLLMBackend, LLMBackend)):
                _brain = RyxBrain(_VLLMWrapper(llm_client))
                return _brain
            else:
                _brain = RyxBrain(llm_client)
                return _brain
        
        # Try vLLM (only backend now)
        try:
            from core.llm_backend import VLLMBackend
            backend = VLLMBackend()
            health = backend.health_check()
            if health.get("healthy"):
                _brain = RyxBrain(_VLLMWrapper(backend))
                return _brain
        except Exception as e:
            logger.warning(f"vLLM not available: {e}")
        
        raise RuntimeError("vLLM not running. Start with: ryx start vllm")
    return _brain


class _VLLMResponse:
    """Response object for vLLM responses"""
    def __init__(self, response: str = "", error: str = None):
        self.response = response
        self.error = error


class _VLLMWrapper:
    """
    Wrapper to make VLLMBackend compatible with RyxBrain interface.
    
    IMPORTANT: vLLM serves ONE model at a time. We ALWAYS use that model.
    """
    
    def __init__(self, backend):
        self.backend = backend
        self.base_url = backend.base_url
        self.current_model = None
        # Detect actual model from vLLM using detector
        self._detect_model()
    
    def _detect_model(self):
        """Detect which model vLLM is actually serving"""
        from core.model_detector import get_detector
        
        detector = get_detector(self.base_url)
        model_info = detector.detect()
        
        if model_info:
            self.current_model = model_info.path
            logger.info(f"Detected vLLM model: {model_info.name}")
        else:
            self.current_model = "unknown"
            logger.warning("Could not detect model from vLLM")
    
    def generate(self, prompt: str, system: str = "", model: str = None, **kwargs) -> '_VLLMResponse':
        """Generate response - ALWAYS uses vLLM's served model"""
        # Ignore passed model - vLLM only serves one model
        resp = self.backend.generate(prompt, system=system, model=self.current_model, **kwargs)
        return _VLLMResponse(response=resp.response, error=resp.error)
    
    def generate_stream(self, prompt: str, system: str = "", **kwargs):
        """Stream response - ALWAYS uses vLLM's served model"""
        # Remove any model from kwargs - we use current_model
        kwargs.pop('model', None)
        return self.backend.generate_stream(prompt, system=system, model=self.current_model, **kwargs)
    
    def generate_tool_call(self, prompt: str, tools: list, **kwargs) -> '_VLLMResponse':
        """Generate with tools - for now just regular generation"""
        return self.generate(prompt, **kwargs)
    
    def list_models(self) -> list:
        """List available models"""
        return [{"name": self.current_model}]
