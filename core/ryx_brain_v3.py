"""
Ryx AI - Brain V3: Copilot-Style Intelligence

Core principles:
1. AI understands intent - NO hardcoded patterns
2. Asks clarifying questions - NEVER assumes
3. Chains multiple actions from single prompt
4. Remembers conversation context
5. Uses appropriate models - precision mode for accuracy
6. Speaks your language naturally (German/English)
7. Does things, doesn't explain how to do them

Inspired by GitHub Copilot CLI design.
"""

import os
import re
import json
import sqlite3
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from core.paths import get_data_dir


class ActionType(Enum):
    """All possible actions Ryx can take"""
    # Basic
    RESPOND = "respond"           # Just say something
    CLARIFY = "clarify"           # Ask clarifying question
    CONFIRM = "confirm"           # Ask yes/no confirmation
    
    # Files
    OPEN_FILE = "open_file"       # Open file in editor
    FIND_FILE = "find_file"       # Search for files
    READ_FILE = "read_file"       # Read file contents
    
    # Web
    OPEN_URL = "open_url"         # Open URL in browser
    SEARCH_WEB = "search_web"     # Web search
    SCRAPE_URL = "scrape_url"     # Scrape webpage
    SCRAPE_HTML = "scrape_html"   # Scrape HTML/CSS
    
    # System
    RUN_COMMAND = "run_command"   # Execute shell command
    SET_PREFERENCE = "set_pref"   # Set user preference
    SWITCH_MODEL = "switch_model" # Change AI model
    
    # Services
    START_SERVICE = "start_svc"   # Start a service
    STOP_SERVICE = "stop_svc"     # Stop a service
    RESTART_SERVICE = "restart"   # Restart services
    
    # Learning
    LEARN = "learn"               # Learn from content
    GET_SMARTER = "smarter"       # Self-improvement
    
    # Utility
    GET_DATE = "get_date"         # Current date/time
    LIST_MODELS = "list_models"   # Show available models
    SHOW_HELP = "show_help"       # Display help
    
    # Complex/Multi-step
    CREATE_DOCUMENT = "create_doc"  # Create study sheet, etc.
    MULTI_ACTION = "multi"          # Multiple actions


@dataclass
class Action:
    """A single action to execute"""
    type: ActionType
    target: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False
    question: Optional[str] = None  # Question to ask user
    confidence: float = 1.0


@dataclass
class ConversationState:
    """Tracks conversation context"""
    last_query: str = ""
    last_result: str = ""
    last_action: Optional[Action] = None
    pending_items: List[Dict] = field(default_factory=list)
    pending_action: Optional[Action] = None
    pending_question: Optional[str] = None
    last_scraped_content: Optional[Dict] = None
    language: str = "auto"  # 'en', 'de', 'auto'


class SmartCache:
    """
    Intelligent caching with learning.
    Stores successful resolutions and learns from failures.
    """
    
    def __init__(self):
        self.db_path = get_data_dir() / "smart_cache_v3.db"
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS cache (
                query_hash TEXT PRIMARY KEY,
                query TEXT,
                action_type TEXT,
                target TEXT,
                options TEXT,
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                last_used TEXT,
                created TEXT
            );
            
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated TEXT
            );
            
            CREATE TABLE IF NOT EXISTS learned_urls (
                name TEXT PRIMARY KEY,
                url TEXT,
                source TEXT,
                created TEXT
            );
            
            CREATE TABLE IF NOT EXISTS model_config (
                role TEXT PRIMARY KEY,
                model_name TEXT,
                updated TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_query ON cache(query);
        """)
        conn.commit()
        conn.close()
    
    def _hash_query(self, query: str) -> str:
        normalized = re.sub(r'\s+', ' ', query.lower().strip())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def lookup(self, query: str) -> Optional[Action]:
        """Look up cached action for query"""
        query_hash = self._hash_query(query)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT action_type, target, options, success_count, fail_count FROM cache WHERE query_hash = ?",
            (query_hash,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row and row[3] > row[4]:  # More successes than failures
            try:
                return Action(
                    type=ActionType(row[0]),
                    target=row[1],
                    options=json.loads(row[2]) if row[2] else {},
                    confidence=0.95
                )
            except:
                pass
        return None
    
    def store(self, query: str, action: Action, success: bool = True):
        """Store action result"""
        query_hash = self._hash_query(query)
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        
        cursor = conn.execute(
            "SELECT success_count, fail_count FROM cache WHERE query_hash = ?",
            (query_hash,)
        )
        existing = cursor.fetchone()
        
        if existing:
            s, f = existing
            if success:
                s += 1
            else:
                f += 1
            conn.execute(
                "UPDATE cache SET success_count = ?, fail_count = ?, last_used = ? WHERE query_hash = ?",
                (s, f, now, query_hash)
            )
        else:
            conn.execute(
                """INSERT INTO cache (query_hash, query, action_type, target, options, success_count, fail_count, last_used, created)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (query_hash, query.lower().strip(), action.type.value, action.target,
                 json.dumps(action.options), 1 if success else 0, 0 if success else 1, now, now)
            )
        conn.commit()
        conn.close()
    
    def get_preference(self, key: str) -> Optional[str]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT value FROM preferences WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    
    def set_preference(self, key: str, value: str):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO preferences (key, value, updated) VALUES (?, ?, ?)",
            (key, value, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    
    def get_model_for_role(self, role: str) -> Optional[str]:
        """Get configured model for a role (default, chatting, coding, precision)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT model_name FROM model_config WHERE role = ?", (role,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    
    def set_model_for_role(self, role: str, model_name: str):
        """Set model for a role"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO model_config (role, model_name, updated) VALUES (?, ?, ?)",
            (role, model_name, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    
    def learn_url(self, name: str, url: str, source: str = "user"):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO learned_urls (name, url, source, created) VALUES (?, ?, ?, ?)",
            (name.lower(), url, source, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    
    def get_learned_url(self, name: str) -> Optional[str]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT url FROM learned_urls WHERE name = ?", (name.lower(),))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    
    def cleanup_bad_entries(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            DELETE FROM cache 
            WHERE fail_count > success_count 
            AND (success_count + fail_count) > 3
        """)
        conn.commit()
        conn.close()


class KnowledgeBase:
    """Pre-loaded verified knowledge"""
    
    def __init__(self):
        self.knowledge_dir = get_data_dir() / "knowledge"
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.arch_linux: Dict = {}
        self.websites: Dict = {}
        self._load_knowledge()
    
    def _load_knowledge(self):
        arch_file = self.knowledge_dir / "arch_linux.json"
        if arch_file.exists():
            with open(arch_file) as f:
                self.arch_linux = json.load(f)
        
        self.websites = self.arch_linux.get("websites", {}).copy()
        
        websites_file = self.knowledge_dir / "websites.json"
        if websites_file.exists():
            with open(websites_file) as f:
                self.websites.update(json.load(f))
    
    def get_config_path(self, name: str, must_exist: bool = True) -> Optional[str]:
        name_lower = name.lower().strip()
        
        # Handle typos/variations
        name_map = {
            "hyperland": "hyprland",
            "hypr": "hyprland",
            "hyperion": "hyprland",
        }
        name_lower = name_map.get(name_lower, name_lower)
        
        aliases = self.arch_linux.get("aliases", {})
        if name_lower in aliases:
            name_lower = aliases[name_lower]
        
        paths = self.arch_linux.get("config_paths", {})
        path = paths.get(name_lower)
        
        if path:
            expanded = os.path.expanduser(path)
            if os.path.exists(expanded):
                return expanded
            elif not must_exist:
                # Return expected path even if doesn't exist
                return expanded
        return None
    
    def get_website_url(self, name: str) -> Optional[str]:
        return self.websites.get(name.lower().strip())
    
    def save_knowledge(self):
        arch_file = self.knowledge_dir / "arch_linux.json"
        with open(arch_file, 'w') as f:
            json.dump(self.arch_linux, f, indent=2)


class ModelManager:
    """Manages model selection and switching"""
    
    # Model categories
    CATEGORIES = {
        "chatting": ["qwen2.5:3b", "qwen2.5:7b", "mistral:7b", "gpt-oss:20b", "llama2-uncensored:7b"],
        "coding": ["qwen2.5-coder:14b", "deepseek-coder:6.7b", "second_constantine/deepseek-coder-v2:16b"],
        "precision": ["gpt-oss:20b", "mistral:7b", "qwen2.5:7b"],
        "fast": ["qwen2.5:1.5b", "qwen2.5:3b", "llama3.2:1b", "phi3:mini"],
        "heavy": ["SimonPu/Qwen3-Coder:30B-Instruct_Q4_K_XL", "huihui_ai/gpt-oss-abliterated:20b"],
    }
    
    def __init__(self, cache: SmartCache):
        self.cache = cache
        self.available_models: List[str] = []
        self._refresh_available()
    
    def _refresh_available(self):
        """Get list of available models from Ollama"""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=10
            )
            self.available_models = []
            for line in result.stdout.strip().split('\n')[1:]:
                if line.strip():
                    model_name = line.split()[0]
                    self.available_models.append(model_name)
        except:
            self.available_models = []
    
    def get_categorized_models(self) -> Dict[str, List[Dict]]:
        """Get models organized by category"""
        self._refresh_available()
        
        result = {
            "chatting": [],
            "coding": [],
            "precision": [],
            "fast": [],
            "heavy": [],
            "other": []
        }
        
        categorized = set()
        for cat, models in self.CATEGORIES.items():
            for model in models:
                if model in self.available_models:
                    result[cat].append({
                        "name": model,
                        "available": True
                    })
                    categorized.add(model)
        
        # Add uncategorized
        for model in self.available_models:
            if model not in categorized:
                result["other"].append({
                    "name": model,
                    "available": True
                })
        
        return result
    
    def find_model(self, query: str) -> Optional[str]:
        """Find a model by natural language query"""
        query_lower = query.lower()
        
        # Direct match
        for model in self.available_models:
            if query_lower in model.lower():
                return model
        
        # Common aliases
        aliases = {
            "gpt": "gpt-oss:20b",
            "gpt oss": "gpt-oss:20b",
            "gpt-oss": "gpt-oss:20b",
            "gpt 20": "gpt-oss:20b",
            "gpt 20b": "gpt-oss:20b",
            "mistral": "mistral:7b",
            "qwen": "qwen2.5:3b",
            "qwen 3b": "qwen2.5:3b",
            "qwen 7b": "qwen2.5:7b",
            "qwen coder": "qwen2.5-coder:14b",
            "deepseek": "deepseek-coder:6.7b",
            "llama": "llama3.2:1b",
            "phi": "phi3:mini",
            "uncensored": "llama2-uncensored:7b",
            "abliterated": "huihui_ai/gpt-oss-abliterated:20b",
        }
        
        for alias, model in aliases.items():
            if alias in query_lower and model in self.available_models:
                return model
        
        return None
    
    def get_model(self, role: str, precision_mode: bool = False) -> str:
        """Get appropriate model for role"""
        # Check user preference first
        saved = self.cache.get_model_for_role(role)
        if saved and saved in self.available_models:
            return saved
        
        # Precision mode uses bigger models
        if precision_mode:
            saved = self.cache.get_model_for_role("precision")
            if saved and saved in self.available_models:
                return saved
            for model in self.CATEGORIES["precision"]:
                if model in self.available_models:
                    return model
        
        # Role-based defaults
        defaults = {
            "default": "qwen2.5:3b",
            "chatting": "mistral:7b",
            "intent": "qwen2.5:3b",
            "fast": "qwen2.5:1.5b",
            "precision": "gpt-oss:20b",
        }
        
        default = defaults.get(role, "qwen2.5:3b")
        if default in self.available_models:
            return default
        
        # Fallback to first available
        return self.available_models[0] if self.available_models else "qwen2.5:3b"


class RyxBrainV3:
    """
    The intelligent core of Ryx v3.
    
    Key improvements:
    - Truly conversational with follow-up understanding
    - Multi-action from single prompt
    - Dynamic model selection
    - No "Could you be more specific?" when context is clear
    """
    
    # System prompt for understanding intent
    INTENT_PROMPT = '''Du bist Ryx, ein präziser AI-Assistent für Arch Linux + Hyprland.
Analysiere die Anfrage und gib eine JSON-Aktion zurück.

Kontext:
- User: Arch Linux, Hyprland, nvim, kitty terminal
- Sprache: Antworte in der Sprache der Anfrage
- Stil: Kurz, direkt, handlungsorientiert

Vorherige Aktion: {last_action}
Vorheriges Ergebnis: {last_result}
Ausstehende Items: {pending_items}

WICHTIG:
- Wenn der User "open it", "edit it", "ja", "yes" sagt -> nutze den Kontext
- Wenn User eine Zahl sagt -> wähle aus der Liste
- Wenn unklar -> frage SPEZIFISCH (nicht "Could you be more specific?")
- Bei Typos wie "hyperland" -> verstehe "hyprland"

Aktionen:
- open_file: Datei öffnen (target: Pfad, options: {{editor, terminal: "new"/"same"}})
- open_url: URL öffnen (target: URL, options: {{browser}})
- find_file: Datei suchen (target: Suchmuster)
- search_web: Web-Suche (target: Query)
- scrape_url: Webseite scrapen (target: URL oder Name)
- scrape_html: HTML/CSS scrapen (target: URL)
- respond: Nur antworten (target: Antwort-Text)
- clarify: Nachfrage stellen (target: Frage)
- confirm: Bestätigung einholen (target: Aktion, question: Frage)
- run_command: Befehl ausführen (target: Befehl, requires_confirm: true)
- set_pref: Einstellung setzen (target: Key, options: {{value}})
- switch_model: Model wechseln (target: Modell-Name oder Rolle)
- create_doc: Dokument erstellen (target: Thema, options: {{type: "lernzettel"/"zusammenfassung"}})
- start_svc: Service starten (target: Service-Name)
- restart: Neustarten (target: "all" oder Service)
- get_date: Datum/Zeit
- list_models: Modelle anzeigen

Antwort NUR als JSON:
{{"type": "<action>", "target": "<ziel>", "options": {{}}, "question": "<falls nötig>"}}

Anfrage: {prompt}'''

    def __init__(self, ollama_client):
        self.ollama = ollama_client
        self.kb = KnowledgeBase()
        self.cache = SmartCache()
        self.state = ConversationState()
        self.models = ModelManager(self.cache)
        
        # Mode flags
        self.precision_mode = False
        self.browsing_enabled = True
        self.fail_count = 0
        self.max_fails_before_upgrade = 2
    
    def toggle_precision_mode(self, enabled: bool):
        """Toggle precision mode (uses larger models)"""
        self.precision_mode = enabled
    
    def toggle_browsing(self, enabled: bool):
        """Toggle web browsing capability"""
        self.browsing_enabled = enabled
    
    def understand(self, prompt: str) -> Action:
        """
        Main entry: understand what user wants.
        Returns Action to execute.
        """
        prompt_clean = prompt.strip()
        prompt_lower = prompt_clean.lower()
        
        self.state.last_query = prompt_clean
        
        # Detect language
        german_indicators = ['bitte', 'wo ist', 'öffne', 'zeig', 'mach', 'erstelle', 'suche nach']
        self.state.language = 'de' if any(g in prompt_lower for g in german_indicators) else 'en'
        
        # Handle quick responses (y/n/numbers) - instant, no LLM
        if self._is_quick_response(prompt_lower):
            return self._handle_quick_response(prompt_lower)
        
        # Handle context references
        context_action = self._handle_context_reference(prompt_lower)
        if context_action:
            return context_action
        
        # Check cache first (instant if found)
        if not self.precision_mode:
            cached = self.cache.lookup(prompt_clean)
            if cached:
                return cached
        
        # Try knowledge-based resolution (no LLM needed)
        kb_action = self._try_knowledge_resolution(prompt_clean)
        if kb_action:
            return kb_action
        
        # Use LLM to understand
        model = self._select_model(prompt_clean)
        return self._llm_understand(prompt_clean, model)
    
    def _is_quick_response(self, prompt: str) -> bool:
        """Check if this is a quick y/n/number response"""
        quick = {'y', 'yes', 'ja', 'n', 'no', 'nein', 'ok', 'okay', 'sure', 'klar'}
        return prompt in quick or prompt.isdigit() or prompt.startswith('the ')
    
    def _handle_quick_response(self, prompt: str) -> Action:
        """Handle y/n/number responses instantly"""
        # Pending confirmation?
        if self.state.pending_action:
            if prompt in {'y', 'yes', 'ja', 'ok', 'okay', 'sure', 'klar'}:
                action = self.state.pending_action
                self.state.pending_action = None
                self.state.pending_question = None
                return action
            elif prompt in {'n', 'no', 'nein'}:
                self.state.pending_action = None
                self.state.pending_question = None
                return Action(type=ActionType.RESPOND, target="Abgebrochen." if self.state.language == 'de' else "Cancelled.")
        
        # Pending list selection?
        if self.state.pending_items:
            if prompt.isdigit():
                idx = int(prompt) - 1
                if 0 <= idx < len(self.state.pending_items):
                    item = self.state.pending_items[idx]
                    self.state.pending_items = []
                    
                    if 'url' in item:
                        return Action(type=ActionType.OPEN_URL, target=item['url'])
                    elif 'path' in item:
                        return Action(type=ActionType.OPEN_FILE, target=item['path'])
                    elif 'action' in item:
                        return item['action']
            
            elif 'first' in prompt or 'erste' in prompt:
                if self.state.pending_items:
                    item = self.state.pending_items[0]
                    self.state.pending_items = []
                    if 'url' in item:
                        return Action(type=ActionType.OPEN_URL, target=item['url'])
                    elif 'path' in item:
                        return Action(type=ActionType.OPEN_FILE, target=item['path'])
        
        return Action(type=ActionType.RESPOND, target="Nichts ausgewählt." if self.state.language == 'de' else "Nothing selected.")
    
    def _handle_context_reference(self, prompt: str) -> Optional[Action]:
        """Handle references to previous results"""
        references = {
            'open it', 'edit it', 'open that', 'edit that',
            'öffne es', 'bearbeite es', 'öffne das', 'zeig mir das'
        }
        
        if prompt in references:
            if self.state.last_result and os.path.exists(self.state.last_result):
                return Action(
                    type=ActionType.OPEN_FILE,
                    target=self.state.last_result,
                    options={"editor": self.cache.get_preference("editor") or "nvim"}
                )
            elif self.state.pending_items and len(self.state.pending_items) == 1:
                item = self.state.pending_items[0]
                if 'path' in item:
                    return Action(type=ActionType.OPEN_FILE, target=item['path'])
                elif 'url' in item:
                    return Action(type=ActionType.OPEN_URL, target=item['url'])
        
        return None
    
    def _try_knowledge_resolution(self, prompt: str) -> Optional[Action]:
        """Try to resolve using knowledge base - no LLM needed"""
        prompt_lower = prompt.lower()
        
        # Date/time - check FIRST before anything else
        date_keywords = ['date', 'time', 'datum', 'zeit', 'uhrzeit', 'today', 'heute', 'what day', 'welcher tag']
        if any(d in prompt_lower for d in date_keywords):
            return Action(type=ActionType.GET_DATE)
        
        # Config file requests
        config_patterns = [
            (r'(?:open|edit|show|öffne|zeig)?\s*(?:my\s+)?(\w+)\s*(?:config|conf|configuration|konfiguration)?(?:\s+(?:in\s+)?(?:new|neues?|same|selben?|diesem?)\s*(?:terminal)?)?', 'config'),
            (r'where\s+is\s+(\w+)\s*(?:config)?', 'find_config'),
            (r'wo\s+ist\s+(\w+)\s*(?:config)?', 'find_config'),
        ]
        
        for pattern, action_type in config_patterns:
            match = re.search(pattern, prompt_lower)
            if match:
                name = match.group(1)
                
                # For "where is" - return expected path even if doesn't exist
                if action_type == 'find_config' or 'where' in prompt_lower or 'wo' in prompt_lower:
                    path = self.kb.get_config_path(name, must_exist=False)
                    if path:
                        exists_note = "" if os.path.exists(path) else " (Datei existiert nicht)" if self.state.language == 'de' else " (file does not exist)"
                        return Action(type=ActionType.RESPOND, target=path + exists_note)
                else:
                    # For open/edit - file must exist
                    path = self.kb.get_config_path(name, must_exist=True)
                    if path:
                        terminal = "same"
                        if 'new' in prompt_lower or 'neues' in prompt_lower or 'neuem' in prompt_lower:
                            terminal = "new"
                        
                        return Action(
                            type=ActionType.OPEN_FILE,
                            target=path,
                            options={
                                "editor": self.cache.get_preference("editor") or "nvim",
                                "terminal": terminal
                            }
                        )
        
        # Website requests - check multi-word names first, then single words
        skip_words = {'the', 'a', 'an', 'das', 'die', 'der', 'what', 'is', 'was', 'ist', 
                      'where', 'wo', 'how', 'wie', 'when', 'wann', 'why', 'warum',
                      'open', 'find', 'search', 'show', 'öffne', 'zeig', 'suche'}
        
        # First check full phrase (e.g., "arch wiki")
        url = self.kb.get_website_url(prompt_lower.strip())
        if url:
            browser = self.cache.get_preference("browser")
            return Action(
                type=ActionType.OPEN_URL,
                target=url,
                options={"browser": browser} if browser else {}
            )
        
        # Check learned URLs for full phrase
        url = self.cache.get_learned_url(prompt_lower.strip())
        if url:
            return Action(type=ActionType.OPEN_URL, target=url)
        
        # Then check individual words
        words = prompt_lower.split()
        for word in words:
            if word not in skip_words:
                url = self.kb.get_website_url(word)
                if url:
                    browser = self.cache.get_preference("browser")
                    return Action(
                        type=ActionType.OPEN_URL,
                        target=url,
                        options={"browser": browser} if browser else {}
                    )
                
                # Check learned URLs
                url = self.cache.get_learned_url(word)
                if url:
                    return Action(type=ActionType.OPEN_URL, target=url)
        
        return None
    
    def _select_model(self, prompt: str) -> str:
        """Select appropriate model for the task"""
        if self.precision_mode:
            return self.models.get_model("precision", precision_mode=True)
        
        # Short/simple queries -> fast model
        if len(prompt) < 50:
            return self.models.get_model("fast")
        
        # Complex requests -> balanced
        return self.models.get_model("default")
    
    def _llm_understand(self, prompt: str, model: str) -> Action:
        """Use LLM to understand intent"""
        # Build context for prompt
        context = {
            "last_action": self.state.last_action.type.value if self.state.last_action else "none",
            "last_result": self.state.last_result[:100] if self.state.last_result else "none",
            "pending_items": str(self.state.pending_items[:5]) if self.state.pending_items else "none",
            "prompt": prompt
        }
        
        full_prompt = self.INTENT_PROMPT.format(**context)
        
        response = self.ollama.generate(
            prompt=full_prompt,
            model=model,
            system="Du bist ein JSON-Parser. Antworte NUR mit validem JSON.",
            max_tokens=300,
            temperature=0.1
        )
        
        if response.error:
            self.fail_count += 1
            if self.fail_count >= self.max_fails_before_upgrade:
                # Retry with larger model
                self.fail_count = 0
                bigger = self.models.get_model("precision", precision_mode=True)
                return self._llm_understand(prompt, bigger)
            
            return Action(
                type=ActionType.RESPOND,
                target="Ich konnte die Anfrage nicht verstehen. Bitte anders formulieren."
                if self.state.language == 'de' else
                "I couldn't understand that. Please rephrase."
            )
        
        # Parse JSON response
        return self._parse_llm_response(response.response, prompt)
    
    def _parse_llm_response(self, response: str, original_prompt: str) -> Action:
        """Parse LLM JSON response into Action"""
        try:
            # Clean response
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            clean = clean.strip()
            
            # Find JSON object
            start = clean.find('{')
            end = clean.rfind('}') + 1
            if start >= 0 and end > start:
                clean = clean[start:end]
            
            data = json.loads(clean)
            
            action_type_str = data.get("type", "respond")
            
            # Map string to ActionType
            type_map = {
                "open_file": ActionType.OPEN_FILE,
                "open_url": ActionType.OPEN_URL,
                "find_file": ActionType.FIND_FILE,
                "search_web": ActionType.SEARCH_WEB,
                "scrape_url": ActionType.SCRAPE_URL,
                "scrape_html": ActionType.SCRAPE_HTML,
                "respond": ActionType.RESPOND,
                "clarify": ActionType.CLARIFY,
                "confirm": ActionType.CONFIRM,
                "run_command": ActionType.RUN_COMMAND,
                "set_pref": ActionType.SET_PREFERENCE,
                "switch_model": ActionType.SWITCH_MODEL,
                "create_doc": ActionType.CREATE_DOCUMENT,
                "start_svc": ActionType.START_SERVICE,
                "restart": ActionType.RESTART_SERVICE,
                "get_date": ActionType.GET_DATE,
                "list_models": ActionType.LIST_MODELS,
            }
            
            action_type = type_map.get(action_type_str, ActionType.RESPOND)
            
            return Action(
                type=action_type,
                target=data.get("target"),
                options=data.get("options", {}),
                question=data.get("question"),
                requires_confirmation=data.get("requires_confirm", False)
            )
            
        except json.JSONDecodeError:
            # Fallback: treat response as direct answer
            return Action(type=ActionType.RESPOND, target=response[:500])
    
    def execute(self, action: Action) -> Tuple[bool, str]:
        """Execute an action and return result"""
        self.state.last_action = action
        
        handlers = {
            ActionType.RESPOND: self._exec_respond,
            ActionType.CLARIFY: self._exec_clarify,
            ActionType.CONFIRM: self._exec_confirm,
            ActionType.OPEN_FILE: self._exec_open_file,
            ActionType.FIND_FILE: self._exec_find_file,
            ActionType.OPEN_URL: self._exec_open_url,
            ActionType.SEARCH_WEB: self._exec_search_web,
            ActionType.SCRAPE_URL: self._exec_scrape,
            ActionType.SCRAPE_HTML: self._exec_scrape_html,
            ActionType.RUN_COMMAND: self._exec_command,
            ActionType.SET_PREFERENCE: self._exec_set_preference,
            ActionType.SWITCH_MODEL: self._exec_switch_model,
            ActionType.START_SERVICE: self._exec_start_service,
            ActionType.RESTART_SERVICE: self._exec_restart,
            ActionType.GET_DATE: self._exec_get_date,
            ActionType.LIST_MODELS: self._exec_list_models,
            ActionType.CREATE_DOCUMENT: self._exec_create_document,
        }
        
        handler = handlers.get(action.type, self._exec_respond)
        success, result = handler(action)
        
        self.state.last_result = result
        
        # Cache successful resolutions
        if success and self.state.last_query:
            self.cache.store(self.state.last_query, action, success)
        
        return success, result
    
    def _exec_respond(self, action: Action) -> Tuple[bool, str]:
        return True, action.target or ""
    
    def _exec_clarify(self, action: Action) -> Tuple[bool, str]:
        return True, action.target or "Was meinst du genau?"
    
    def _exec_confirm(self, action: Action) -> Tuple[bool, str]:
        self.state.pending_action = action
        self.state.pending_question = action.question
        return True, action.question or "Bist du sicher? (y/n)"
    
    def _exec_open_file(self, action: Action) -> Tuple[bool, str]:
        path = action.target
        if not path:
            return False, "Kein Dateipfad angegeben"
        
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return False, f"Datei nicht gefunden: {path}"
        
        editor = action.options.get("editor") or self.cache.get_preference("editor") or "nvim"
        terminal = action.options.get("terminal", "same")
        
        try:
            if terminal == "new":
                term_app = self.cache.get_preference("terminal") or "kitty"
                subprocess.Popen([term_app, editor, path])
            else:
                # Open in same terminal (requires user to be in interactive mode)
                subprocess.run([editor, path])
            
            self.state.last_result = path
            return True, f"✅ Geöffnet: {path}"
        except Exception as e:
            return False, f"Fehler: {e}"
    
    def _exec_find_file(self, action: Action) -> Tuple[bool, str]:
        query = action.target
        if not query:
            return False, "Was soll ich suchen?"
        
        # Build search patterns
        patterns = [f"*{query}*", f"*{query.replace(' ', '*')}*"]
        
        search_dirs = [
            os.path.expanduser("~/.config"),
            os.path.expanduser("~"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Documents"),
        ]
        
        found = []
        for search_dir in search_dirs:
            if not os.path.exists(search_dir):
                continue
            
            for pattern in patterns:
                try:
                    result = subprocess.run(
                        ["find", search_dir, "-maxdepth", "4", "-iname", pattern, "-type", "f"],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.stdout.strip():
                        found.extend(result.stdout.strip().split("\n"))
                except:
                    pass
        
        if found:
            unique = list(set(found))[:10]
            
            if len(unique) == 1:
                self.state.last_result = unique[0]
                return True, unique[0]
            else:
                self.state.pending_items = [{"path": p, "name": os.path.basename(p)} for p in unique]
                result_lines = [f"{i+1}. {os.path.basename(p)}: {p}" for i, p in enumerate(unique)]
                return True, "Gefunden:\n" + "\n".join(result_lines) + "\n\nWelche? (Nummer eingeben)"
        
        return False, f"Keine Dateien gefunden für '{query}'"
    
    def _exec_open_url(self, action: Action) -> Tuple[bool, str]:
        url = action.target
        if not url:
            return False, "Keine URL angegeben"
        
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        browser = action.options.get("browser") or self.cache.get_preference("browser")
        
        try:
            if browser:
                # Try the preferred browser first
                try:
                    subprocess.Popen([browser, url])
                    return True, "✅ Im Browser geöffnet"
                except FileNotFoundError:
                    # Browser not found, fall back to xdg-open
                    pass
            
            # Default: use xdg-open
            subprocess.Popen(["xdg-open", url])
            return True, "✅ Im Browser geöffnet"
        except Exception as e:
            return False, f"Fehler: {e}"
    
    def _exec_search_web(self, action: Action) -> Tuple[bool, str]:
        query = action.target
        if not query:
            return False, "Was soll ich suchen?"
        
        # Check if SearXNG is running
        try:
            import requests
            requests.get("http://localhost:8888", timeout=2)
        except:
            # Offer to start it
            self.state.pending_action = Action(
                type=ActionType.RUN_COMMAND,
                target="docker run -d -p 8888:8080 --name searxng searxng/searxng"
            )
            return False, "SearXNG läuft nicht. Soll ich es starten? (y/n)"
        
        # Perform search
        try:
            import requests
            response = requests.get(
                "http://localhost:8888/search",
                params={"q": query, "format": "json"},
                timeout=10
            )
            data = response.json()
            results = data.get("results", [])[:10]
            
            if not results:
                return False, f"Keine Ergebnisse für '{query}'"
            
            # Format results
            lines = []
            self.state.pending_items = []
            
            for i, r in enumerate(results):
                title = r.get("title", "Kein Titel")
                url = r.get("url", "")
                lines.append(f"{i+1}. {title}")
                lines.append(f"   {url}")
                self.state.pending_items.append({"url": url, "title": title})
            
            intent = action.options.get("intent")
            name = action.options.get("name")
            
            # If looking for specific URL, try to match
            if intent == "find_url" and name:
                for r in results:
                    if name.lower() in r.get("title", "").lower() or name.lower() in r.get("url", "").lower():
                        url = r.get("url")
                        self.cache.learn_url(name, url, "search")
                        return True, f"Gefunden: {url}\nSoll ich es öffnen? (y/n)"
            
            return True, "\n".join(lines) + "\n\nWelches? (Nummer eingeben)"
            
        except Exception as e:
            return False, f"Suche fehlgeschlagen: {e}"
    
    def _exec_scrape(self, action: Action) -> Tuple[bool, str]:
        target = action.target
        if not target:
            return False, "Was soll ich scrapen?"
        
        # If not a URL, search for it first
        if not target.startswith(('http://', 'https://')):
            # Check if we know this URL
            known_url = self.cache.get_learned_url(target) or self.kb.get_website_url(target)
            if known_url:
                target = known_url
            else:
                return False, f"Ich kenne '{target}' nicht. Bitte gib eine vollständige URL an oder lass mich erst danach suchen: /search {target}"
        
        try:
            import requests
            from bs4 import BeautifulSoup
            
            response = requests.get(target, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Ryx/3.0"
            })
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove scripts and styles
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            
            text = soup.get_text(separator='\n', strip=True)
            title = soup.title.string if soup.title else target
            
            # Save
            scrape_dir = get_data_dir() / "scrape"
            scrape_dir.mkdir(parents=True, exist_ok=True)
            
            domain = target.split('/')[2] if '/' in target else target
            safe_name = re.sub(r'[^\w\-_.]', '_', domain)[:50]
            
            data = {
                "url": target,
                "title": title,
                "domain": domain,
                "text": text[:50000],
                "scraped_at": datetime.now().isoformat()
            }
            
            scrape_file = scrape_dir / f"{safe_name}.json"
            with open(scrape_file, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.state.last_scraped_content = data
            
            return True, f"✅ Gescraped: {title}\n   Gespeichert: {scrape_file}\n   Text: {len(text)} Zeichen\n\nWas möchtest du damit machen?"
            
        except Exception as e:
            return False, f"Scrape fehlgeschlagen: {e}"
    
    def _exec_scrape_html(self, action: Action) -> Tuple[bool, str]:
        """Scrape HTML and CSS from a webpage"""
        target = action.target
        if not target:
            return False, "Welche Website?"
        
        if not target.startswith(('http://', 'https://')):
            known_url = self.cache.get_learned_url(target) or self.kb.get_website_url(target)
            if known_url:
                target = known_url
            else:
                return False, f"URL für '{target}' unbekannt. Bitte vollständige URL angeben."
        
        try:
            import requests
            from bs4 import BeautifulSoup
            
            response = requests.get(target, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Ryx/3.0"
            })
            soup = BeautifulSoup(response.text, 'html.parser')
            
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
                        css_content.append(f"/* From: {href} */\n{css_resp.text}")
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
                f.write(response.text)
            
            with open(css_file, 'w') as f:
                f.write('\n\n'.join(css_content))
            
            return True, f"✅ HTML/CSS gescraped:\n   HTML: {html_file}\n   CSS: {css_file}"
            
        except Exception as e:
            return False, f"Scrape fehlgeschlagen: {e}"
    
    def _exec_command(self, action: Action) -> Tuple[bool, str]:
        cmd = action.target
        if not cmd:
            return False, "Kein Befehl angegeben"
        
        if action.requires_confirmation:
            self.state.pending_action = Action(
                type=ActionType.RUN_COMMAND,
                target=cmd,
                requires_confirmation=False
            )
            return True, f"Befehl ausführen: {cmd}\nBist du sicher? (y/n)"
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            output = result.stdout or result.stderr
            return result.returncode == 0, output.strip() or "Ausgeführt"
        except subprocess.TimeoutExpired:
            return False, "Timeout"
        except Exception as e:
            return False, f"Fehler: {e}"
    
    def _exec_set_preference(self, action: Action) -> Tuple[bool, str]:
        key = action.target
        value = action.options.get("value", "")
        
        if key and value:
            self.cache.set_preference(key, value)
            return True, f"✅ {key} = {value}"
        
        return False, "Ungültige Einstellung"
    
    def _exec_switch_model(self, action: Action) -> Tuple[bool, str]:
        query = action.target
        role = action.options.get("role", "default")
        
        if not query:
            return False, "Welches Modell?"
        
        model = self.models.find_model(query)
        if model:
            self.cache.set_model_for_role(role, model)
            return True, f"✅ {role} Modell: {model}"
        
        # List available
        available = "\n".join([f"  - {m}" for m in self.models.available_models])
        return False, f"Modell '{query}' nicht gefunden.\n\nVerfügbar:\n{available}"
    
    def _exec_start_service(self, action: Action) -> Tuple[bool, str]:
        service = action.target
        if not service:
            return False, "Welcher Service?"
        
        if service.lower() in ['searxng', 'searx', 'search']:
            try:
                import requests
                requests.get("http://localhost:8888", timeout=2)
                return True, "SearXNG läuft bereits"
            except:
                self.state.pending_action = Action(
                    type=ActionType.RUN_COMMAND,
                    target="docker run -d -p 8888:8080 --name searxng searxng/searxng"
                )
                return True, "SearXNG starten? (y/n)"
        
        return False, f"Unbekannter Service: {service}"
    
    def _exec_restart(self, action: Action) -> Tuple[bool, str]:
        target = action.target
        
        if target == "all" or target == "ryx":
            self.state.pending_action = Action(
                type=ActionType.RUN_COMMAND,
                target="systemctl --user restart ryx 2>/dev/null || echo 'Ryx neugestartet'"
            )
            return True, "Alle Ryx-Dienste neustarten? (y/n)"
        
        return False, f"Neustart von '{target}' nicht unterstützt"
    
    def _exec_get_date(self, action: Action) -> Tuple[bool, str]:
        now = datetime.now()
        if self.state.language == 'de':
            return True, now.strftime("%A, %d. %B %Y - %H:%M Uhr")
        return True, now.strftime("%A, %B %d, %Y - %H:%M")
    
    def _exec_list_models(self, action: Action) -> Tuple[bool, str]:
        categorized = self.models.get_categorized_models()
        
        lines = ["📊 Verfügbare Modelle:\n"]
        
        for category, models in categorized.items():
            if models:
                lines.append(f"\n{category.upper()}:")
                for m in models:
                    lines.append(f"  • {m['name']}")
        
        # Show current defaults
        lines.append("\n\n⚙️ Aktuelle Einstellungen:")
        for role in ["default", "chatting", "precision", "fast"]:
            model = self.cache.get_model_for_role(role)
            if model:
                lines.append(f"  {role}: {model}")
        
        return True, "\n".join(lines)
    
    def _exec_create_document(self, action: Action) -> Tuple[bool, str]:
        """Create a study sheet or document"""
        topic = action.target
        doc_type = action.options.get("type", "lernzettel")
        
        if not topic:
            return False, "Welches Thema?"
        
        # This is a complex task - use precision model
        model = self.models.get_model("precision", precision_mode=True)
        
        prompt = f"""Erstelle einen {doc_type} über: {topic}

Format:
- Klare Überschriften
- Stichpunkte, keine langen Sätze
- Wichtige Begriffe hervorheben
- Prüfungsrelevante Punkte markieren
- Beispiele wenn hilfreich
- Maximal 2 Seiten Inhalt

Sprache: Deutsch
Ziel: Prüfungsvorbereitung"""

        response = self.ollama.generate(
            prompt=prompt,
            model=model,
            system="Du bist ein Experte für Lernmaterialien. Erstelle präzise, gut strukturierte Zusammenfassungen.",
            max_tokens=2000,
            temperature=0.3
        )
        
        if response.error:
            return False, f"Fehler: {response.error}"
        
        # Save document
        docs_dir = get_data_dir() / "notes"
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        safe_topic = re.sub(r'[^\w\-_]', '_', topic)[:30]
        doc_file = docs_dir / f"{doc_type}_{safe_topic}_{datetime.now().strftime('%Y%m%d')}.md"
        
        with open(doc_file, 'w') as f:
            f.write(f"# {doc_type.title()}: {topic}\n\n")
            f.write(f"Erstellt: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n")
            f.write(response.response)
        
        self.state.last_result = str(doc_file)
        
        return True, f"✅ {doc_type.title()} erstellt:\n{doc_file}\n\nSoll ich es öffnen? (y/n)"
    
    def get_smarter(self) -> str:
        """Self-improvement: analyze and fix knowledge"""
        self.cache.cleanup_bad_entries()
        
        # Use larger model for self-improvement
        model = self.models.get_model("precision", precision_mode=True)
        
        # Analyze current knowledge
        updates = []
        
        # Check config paths
        for name, path in list(self.kb.arch_linux.get("config_paths", {}).items()):
            expanded = os.path.expanduser(path)
            if not os.path.exists(expanded):
                try:
                    result = subprocess.run(
                        ["find", os.path.expanduser("~/.config"), "-name", f"*{name}*", "-type", "f"],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.stdout.strip():
                        found = result.stdout.strip().split('\n')[0]
                        self.kb.arch_linux["config_paths"][name] = found
                        updates.append(f"Fixed: {name} → {found}")
                except:
                    pass
        
        if updates:
            self.kb.save_knowledge()
        
        return f"🧠 Self-improvement abgeschlossen\n" + "\n".join(updates) if updates else "Wissensbasis ist aktuell."


# Global instance
_brain_v3: Optional[RyxBrainV3] = None

def get_brain_v3(ollama_client=None) -> RyxBrainV3:
    global _brain_v3
    if _brain_v3 is None:
        if ollama_client is None:
            from core.ollama_client import OllamaClient
            from core.model_router import ModelRouter
            router = ModelRouter()
            ollama_client = OllamaClient(base_url=router.get_ollama_url())
        _brain_v3 = RyxBrainV3(ollama_client)
    return _brain_v3
