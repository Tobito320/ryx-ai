"""
Ryx AI - Brain Core
The intelligent heart of Ryx. Copilot-style architecture.

Key principles:
1. AI understands prompts - NO hardcoded patterns
2. Knowledge-backed responses - NO hallucinations
3. Ask when uncertain - NEVER guess
4. Do things - DON'T explain how to do them
5. Learn from interactions - GET SMARTER over time
6. Multi-action support - Handle complex requests
7. Conversation context - Understand follow-ups
"""

import os
import re
import json
import subprocess
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

from core.paths import get_data_dir, get_project_root


class ActionType(Enum):
    """What Ryx should do"""
    OPEN_FILE = "open_file"
    OPEN_URL = "open_url"
    FIND_FILE = "find_file"
    SEARCH_WEB = "search_web"
    SCRAPE_URL = "scrape_url"
    RUN_COMMAND = "run_command"
    ANSWER = "answer"
    CLARIFY = "clarify"
    MULTI = "multi"  # Multiple actions
    SET_PREFERENCE = "set_preference"
    START_SERVICE = "start_service"
    GET_DATE = "get_date"
    SWITCH_MODEL = "switch_model"


@dataclass
class Action:
    """A planned action"""
    type: ActionType
    target: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)
    question: Optional[str] = None
    confidence: float = 1.0
    sub_actions: List['Action'] = field(default_factory=list)


@dataclass
class ConversationContext:
    """Track conversation for follow-ups"""
    last_action: Optional[Action] = None
    last_result: Optional[str] = None
    last_query: Optional[str] = None
    pending_items: List[Dict] = field(default_factory=list)  # For "which one?" scenarios


class SmartCache:
    """
    SQLite-based cache for instant lookups.
    Stores successful resolutions to skip LLM calls.
    """
    
    def __init__(self):
        self.db_path = get_data_dir() / "smart_cache.db"
        self._init_db()
    
    def _init_db(self):
        """Initialize the cache database"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                query_hash TEXT PRIMARY KEY,
                query TEXT,
                action_type TEXT,
                target TEXT,
                options TEXT,
                success_count INTEGER DEFAULT 1,
                fail_count INTEGER DEFAULT 0,
                last_used TEXT,
                created TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learned_urls (
                name TEXT PRIMARY KEY,
                url TEXT,
                source TEXT,
                created TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def _hash_query(self, query: str) -> str:
        """Create a normalized hash for a query"""
        import hashlib
        normalized = query.lower().strip()
        # Remove common filler words for better matching
        for word in ['please', 'can you', 'could you', 'the', 'a', 'my']:
            normalized = normalized.replace(word, '').strip()
        normalized = ' '.join(normalized.split())  # Normalize whitespace
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def lookup(self, query: str) -> Optional[Action]:
        """Look up a cached action for a query"""
        query_hash = self._hash_query(query)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT action_type, target, options, success_count, fail_count FROM cache WHERE query_hash = ?",
            (query_hash,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            action_type, target, options_json, success, fail = row
            # Only return if success rate > 70%
            if success > 0 and success / (success + fail) > 0.7:
                try:
                    options = json.loads(options_json) if options_json else {}
                    return Action(
                        type=ActionType(action_type),
                        target=target,
                        options=options,
                        confidence=0.95
                    )
                except:
                    pass
        return None
    
    def store(self, query: str, action: Action, success: bool = True):
        """Store a successful resolution"""
        query_hash = self._hash_query(query)
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        
        try:
            cursor = conn.execute(
                "SELECT success_count, fail_count FROM cache WHERE query_hash = ?",
                (query_hash,)
            )
            existing = cursor.fetchone()
            
            if existing:
                success_count, fail_count = existing
                if success:
                    success_count += 1
                else:
                    fail_count += 1
                conn.execute(
                    "UPDATE cache SET success_count = ?, fail_count = ?, last_used = ? WHERE query_hash = ?",
                    (success_count, fail_count, now, query_hash)
                )
            else:
                conn.execute(
                    """INSERT INTO cache (query_hash, query, action_type, target, options, success_count, fail_count, last_used, created)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (query_hash, query.lower().strip(), action.type.value, action.target,
                     json.dumps(action.options), 1 if success else 0, 0 if success else 1, now, now)
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
        """Learn a new URL"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO learned_urls (name, url, source, created) VALUES (?, ?, ?, ?)",
            (name.lower(), url, source, datetime.now().isoformat())
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
    
    def cleanup_bad_entries(self):
        """Remove entries with high fail rates"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            DELETE FROM cache 
            WHERE fail_count > success_count 
            AND (success_count + fail_count) > 3
        """)
        conn.commit()
        conn.close()


class KnowledgeBase:
    """
    Pre-loaded knowledge for accurate responses.
    No hallucinations - only verified data.
    """
    
    def __init__(self):
        self.knowledge_dir = get_data_dir() / "knowledge"
        self.arch_linux: Dict = {}
        self.websites: Dict = {}
        self.file_system: Dict = {}
        self._load_knowledge()
    
    def _load_knowledge(self):
        """Load all knowledge files"""
        # Load Arch Linux knowledge
        arch_file = self.knowledge_dir / "arch_linux.json"
        if arch_file.exists():
            with open(arch_file) as f:
                self.arch_linux = json.load(f)
        
        # Build combined websites dict
        self.websites = self.arch_linux.get("websites", {}).copy()
        
        # Load additional websites
        websites_file = self.knowledge_dir / "websites.json"
        if websites_file.exists():
            with open(websites_file) as f:
                self.websites.update(json.load(f))
    
    def get_config_path(self, name: str) -> Optional[str]:
        """Get config file path from knowledge base"""
        name_lower = name.lower().strip()
        
        # Check aliases first
        aliases = self.arch_linux.get("aliases", {})
        if name_lower in aliases:
            name_lower = aliases[name_lower]
        
        # Get from config paths
        paths = self.arch_linux.get("config_paths", {})
        path = paths.get(name_lower)
        
        if path:
            expanded = os.path.expanduser(path)
            if os.path.exists(expanded):
                return expanded
        return None
    
    def get_website_url(self, name: str) -> Optional[str]:
        """Get website URL from knowledge base"""
        name_lower = name.lower().strip()
        return self.websites.get(name_lower)
    
    def get_default(self, key: str) -> str:
        """Get a default value"""
        defaults = {
            "browser": self.arch_linux.get("default_browser", "firefox"),
            "editor": os.environ.get("EDITOR", self.arch_linux.get("default_editor", "nvim")),
            "terminal": self.arch_linux.get("default_terminal", "kitty"),
        }
        return defaults.get(key, "")
    
    def save_knowledge(self):
        """Save updated knowledge"""
        arch_file = self.knowledge_dir / "arch_linux.json"
        with open(arch_file, 'w') as f:
            json.dump(self.arch_linux, f, indent=2)


class RyxBrain:
    """
    The intelligent core of Ryx.
    Copilot-style: AI-driven understanding, knowledge-backed accuracy.
    """
    
    def __init__(self, ollama_client):
        self.ollama = ollama_client
        self.kb = KnowledgeBase()
        self.cache = SmartCache()
        self.context = ConversationContext()
        
        # Model configuration - NO coding models for general tasks
        self.tiny_model = "qwen2.5:1.5b"      # Cached hits only
        self.fast_model = "qwen2.5:3b"        # Simple understanding
        self.balanced_model = "mistral:7b"    # General tasks (NOT coding)
        self.smart_model = "gpt-oss:20b"      # Complex reasoning (NOT coding)
        
        self.learning_mode = False
        self.fail_count = 0
        self.max_fails_before_upgrade = 2
    
    def set_learning_mode(self, enabled: bool):
        """Toggle learning mode (uses higher models)"""
        self.learning_mode = enabled
    
    def understand(self, prompt: str) -> Action:
        """
        Main entry point: understand what the user wants.
        Returns an Action to execute.
        """
        prompt_clean = prompt.strip()
        prompt_lower = prompt_clean.lower()
        
        # Store query for caching
        self.context.last_query = prompt_clean
        
        # Handle follow-up responses (y/n, numbers)
        if self._is_followup_response(prompt_lower):
            return self._handle_followup(prompt_lower)
        
        # Handle "open it" - reference to last result
        if prompt_lower in ['open it', 'open that', 'edit it', 'edit that']:
            if self.context.last_result and os.path.exists(self.context.last_result):
                return Action(
                    type=ActionType.OPEN_FILE,
                    target=self.context.last_result,
                    options={"editor": self.cache.get_preference("editor") or self.kb.get_default("editor")}
                )
        
        # Check cache first (instant, no LLM)
        if not self.learning_mode:
            cached = self.cache.lookup(prompt_clean)
            if cached:
                return cached
        
        # Try knowledge-based resolution (no LLM needed)
        action = self._try_knowledge_resolution(prompt_clean)
        if action:
            return action
        
        # Use LLM to understand
        model = self._select_model(prompt_clean)
        return self._llm_understand(prompt_clean, model)
    
    def _is_followup_response(self, prompt: str) -> bool:
        """Check if this is a follow-up response to a question"""
        if prompt in ['y', 'yes', 'n', 'no', 'ok', 'okay', 'sure']:
            return True
        if prompt.isdigit():
            return True
        if prompt.startswith('the first') or prompt.startswith('the second'):
            return True
        return False
    
    def _handle_followup(self, prompt: str) -> Action:
        """Handle follow-up responses"""
        # If we have pending items (from a "which one?" question)
        if self.context.pending_items:
            if prompt.isdigit():
                idx = int(prompt) - 1
                if 0 <= idx < len(self.context.pending_items):
                    item = self.context.pending_items[idx]
                    self.context.pending_items = []
                    # Return action based on item type
                    if 'url' in item:
                        return Action(type=ActionType.OPEN_URL, target=item['url'])
                    elif 'path' in item:
                        return Action(type=ActionType.OPEN_FILE, target=item['path'])
            elif 'first' in prompt:
                if self.context.pending_items:
                    item = self.context.pending_items[0]
                    self.context.pending_items = []
                    if 'url' in item:
                        return Action(type=ActionType.OPEN_URL, target=item['url'])
        
        # If we have a pending action
        if self.context.last_action:
            if prompt in ['y', 'yes', 'ok', 'sure']:
                action = self.context.last_action
                self.context.last_action = None
                return action
            elif prompt in ['n', 'no']:
                self.context.last_action = None
                return Action(type=ActionType.ANSWER, target="Cancelled.")
        
        return Action(type=ActionType.CLARIFY, question="What would you like me to do?")
    
    def _try_knowledge_resolution(self, prompt: str) -> Optional[Action]:
        """
        Try to resolve using knowledge base without LLM.
        Fast path for common patterns.
        """
        prompt_lower = prompt.lower().strip()
        
        # Handle "set X as default" preferences
        if 'set ' in prompt_lower and ' as default' in prompt_lower:
            match = re.search(r'set (\w+) as default (\w+)', prompt_lower)
            if match:
                value, key = match.groups()
                return Action(
                    type=ActionType.SET_PREFERENCE,
                    target=key,
                    options={"value": value}
                )
        
        # Handle "switch to X model" 
        if 'switch to' in prompt_lower and 'model' in prompt_lower:
            # Extract model name - look for size patterns
            model_match = re.search(r'(\w+[:\-]?\d*b?)', prompt_lower)
            if model_match:
                return Action(
                    type=ActionType.SWITCH_MODEL,
                    target=model_match.group(1)
                )
        
        # Handle date/time queries
        if any(x in prompt_lower for x in ['what is the date', 'what day is', "today's date", 'what time']):
            return Action(type=ActionType.GET_DATE)
        
        # Handle "start X" for services
        if prompt_lower.startswith('start '):
            service = prompt_lower[6:].strip()
            if service in ['searxng', 'searx']:
                return Action(
                    type=ActionType.START_SERVICE,
                    target="searxng",
                    question="Should I start SearXNG? (docker run -d -p 8888:8080 searxng/searxng) y/n"
                )
        
        # Special handling for "where is X" - return path as answer, not open
        is_where_query = prompt_lower.startswith('where is ') or prompt_lower.startswith('where\'s ')
        
        # Extract the target from the prompt
        target = prompt_lower
        new_terminal = False
        same_terminal = True
        with_browser = None
        
        # Handle terminal flags
        if ' in new terminal' in target or ' new terminal' in target:
            target = target.replace(' in new terminal', '').replace(' new terminal', '')
            new_terminal = True
            same_terminal = False
        elif ' in same terminal' in target or ' same terminal' in target:
            target = target.replace(' in same terminal', '').replace(' same terminal', '')
        
        # Handle browser flags
        browser_match = re.search(r'with (\w+)( browser)?', target)
        if browser_match:
            with_browser = browser_match.group(1)
            target = re.sub(r'with \w+( browser)?', '', target)
        
        # Remove common prefixes
        for prefix in ['open ', 'edit ', 'show ', 'find ', 'where is ', 'where\'s ',
                       'search for ', 'open the ', 'edit the ', 'can you ', 'please ', 'could you ']:
            if target.startswith(prefix):
                target = target[len(prefix):]
        
        # Remove "config" suffix for config lookups but remember it
        is_config_request = 'config' in target
        target = target.replace(' config', '').replace('config', '').strip()
        
        # Remove common filler words
        for word in ['the', 'my', 'a', 'for me', 'please']:
            target = target.replace(f' {word} ', ' ').strip()
        
        target = target.strip()
        
        if not target:
            return None
        
        # Check cache for learned URLs
        learned_url = self.cache.get_learned_url(target)
        if learned_url:
            browser = with_browser or self.cache.get_preference("browser") or self.kb.get_default("browser")
            return Action(
                type=ActionType.OPEN_URL,
                target=learned_url,
                options={"browser": browser}
            )
        
        # Check if it's a known website
        url = self.kb.get_website_url(target)
        if url:
            browser = with_browser or self.cache.get_preference("browser") or self.kb.get_default("browser")
            return Action(
                type=ActionType.OPEN_URL,
                target=url,
                options={"browser": browser}
            )
        
        # Check if it looks like a website (has .com, .org, etc or "website" in prompt)
        if 'website' in prompt_lower or any(tld in target for tld in ['.com', '.org', '.net', '.io', '.dev']):
            # Try to find it online
            clean_name = target.replace(' website', '').strip()
            return Action(
                type=ActionType.SEARCH_WEB,
                target=f"{clean_name} official website",
                options={"intent": "find_url", "name": clean_name}
            )
        
        # Check if it's a config file
        config_path = self.kb.get_config_path(target)
        if config_path:
            # If "where is" query, just return the path as an answer
            if is_where_query:
                return Action(
                    type=ActionType.ANSWER,
                    target=config_path
                )
            
            editor = self.cache.get_preference("editor") or self.kb.get_default("editor")
            terminal = self.cache.get_preference("terminal") or self.kb.get_default("terminal")
            return Action(
                type=ActionType.OPEN_FILE,
                target=config_path,
                options={
                    "editor": editor,
                    "terminal": terminal,
                    "new_terminal": new_terminal
                }
            )
        
        # Check for file finding patterns
        if any(x in prompt_lower for x in ['find ', 'where is ', 'locate ', 'search for ', 'look for ']):
            return Action(
                type=ActionType.FIND_FILE,
                target=target
            )
        
        return None
    
    def _select_model(self, prompt: str) -> str:
        """Select appropriate model based on task complexity"""
        if self.learning_mode:
            return self.smart_model
        
        # If we've failed multiple times, upgrade
        if self.fail_count >= self.max_fails_before_upgrade:
            return self.smart_model
        
        prompt_lower = prompt.lower()
        
        # Complex tasks need smarter model
        if any(x in prompt_lower for x in ['explain', 'why', 'how does', 'analyze', 'compare']):
            return self.balanced_model
        
        # Web/scraping tasks
        if any(x in prompt_lower for x in ['scrape', 'search for', 'look up', 'find online']):
            return self.balanced_model
        
        return self.fast_model
    
    def _llm_understand(self, prompt: str, model: str) -> Action:
        """Use LLM to understand the prompt"""
        
        # Build context
        context_parts = []
        
        # Add last interaction for follow-up understanding
        if self.context.last_query:
            context_parts.append(f"Previous query: {self.context.last_query}")
            if self.context.last_result:
                context_parts.append(f"Previous result: {self.context.last_result[:200]}")
        
        context_str = "\n".join(context_parts) if context_parts else "No prior context."
        
        # Get preferences
        prefs = []
        browser = self.cache.get_preference("browser")
        if browser:
            prefs.append(f"Browser: {browser}")
        editor = self.cache.get_preference("editor")
        if editor:
            prefs.append(f"Editor: {editor}")
        prefs_str = ", ".join(prefs) if prefs else "Using defaults"
        
        system_prompt = f"""You are Ryx's brain. Analyze user intent and return a structured action.

CONTEXT:
{context_str}

USER PREFERENCES: {prefs_str}

KNOWN CONFIG PATHS: hyprland (~/.config/hypr/hyprland.conf), waybar, kitty, nvim, zsh (~/.zshrc)

RULES:
1. For opening websites/URLs → {{"action": "open_url", "target": "https://..."}}
2. For opening files/configs → {{"action": "open_file", "target": "/path/to/file", "new_terminal": true/false}}
3. For finding files → {{"action": "find_file", "target": "search query"}}
4. For web searches → {{"action": "search_web", "target": "query"}}
5. For questions you can answer → {{"action": "answer", "target": "brief answer"}}
6. If UNCERTAIN → {{"action": "clarify", "question": "specific yes/no question"}}
7. For multiple actions → {{"action": "multi", "actions": [...]}}

IMPORTANT:
- Be BRIEF in answers (1-2 sentences max)
- NEVER make up file paths - use find_file if unsure
- For unknown websites, use search_web to find them
- If user says "open it" after finding something, refer to context

RESPOND ONLY WITH JSON:
"""

        response = self.ollama.generate(
            prompt=f"User: {prompt}",
            model=model,
            system=system_prompt,
            max_tokens=300,
            temperature=0.1
        )
        
        if response.error:
            self.fail_count += 1
            return Action(type=ActionType.ANSWER, target=f"Error: {response.error}")
        
        # Parse JSON response
        try:
            text = response.response.strip()
            
            # Extract JSON
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            # Find JSON object
            json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if json_match:
                text = json_match.group()
            
            data = json.loads(text)
            action_type = ActionType(data.get("action", "answer"))
            
            action = Action(
                type=action_type,
                target=data.get("target"),
                question=data.get("question"),
                options=data.get("options", {}),
                confidence=data.get("confidence", 0.8)
            )
            
            # Store context
            self.context.last_query = prompt
            
            # Reset fail count on success
            self.fail_count = 0
            
            return action
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            self.fail_count += 1
            # Try to extract useful info from response
            return Action(
                type=ActionType.CLARIFY,
                question="I'm not sure what you want. Can you rephrase?"
            )
    
    def execute(self, action: Action) -> Tuple[bool, str]:
        """Execute an action and return (success, result)"""
        
        handlers = {
            ActionType.OPEN_FILE: self._exec_open_file,
            ActionType.OPEN_URL: self._exec_open_url,
            ActionType.FIND_FILE: self._exec_find_file,
            ActionType.SEARCH_WEB: self._exec_search_web,
            ActionType.SCRAPE_URL: self._exec_scrape,
            ActionType.RUN_COMMAND: self._exec_command,
            ActionType.SET_PREFERENCE: self._exec_set_preference,
            ActionType.START_SERVICE: self._exec_start_service,
            ActionType.GET_DATE: self._exec_get_date,
            ActionType.SWITCH_MODEL: self._exec_switch_model,
            ActionType.CLARIFY: lambda a: (True, a.question or "Could you clarify?"),
            ActionType.ANSWER: lambda a: (True, a.target or "I don't know."),
        }
        
        handler = handlers.get(action.type)
        if handler:
            success, result = handler(action)
            self.context.last_result = result
            
            # Cache successful resolutions
            if success and self.context.last_query:
                self.cache.store(self.context.last_query, action, success)
            
            return success, result
        
        return False, "Unknown action type"
    
    def _exec_open_file(self, action: Action) -> Tuple[bool, str]:
        """Open a file in editor"""
        path = action.target
        if not path:
            return False, "No file specified"
        
        path = os.path.expanduser(path)
        
        if not os.path.exists(path):
            return False, f"File not found: {path}"
        
        editor = action.options.get("editor") or self.cache.get_preference("editor") or self.kb.get_default("editor")
        new_terminal = action.options.get("new_terminal", False)
        
        try:
            if new_terminal:
                terminal = action.options.get("terminal") or self.cache.get_preference("terminal") or self.kb.get_default("terminal")
                subprocess.Popen([terminal, "-e", editor, path],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run([editor, path])
            return True, path
        except Exception as e:
            return False, f"Failed to open: {e}"
    
    def _exec_open_url(self, action: Action) -> Tuple[bool, str]:
        """Open URL in browser"""
        url = action.target
        if not url:
            return False, "No URL specified"
        
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        
        browser = action.options.get("browser") or self.cache.get_preference("browser") or self.kb.get_default("browser")
        
        try:
            subprocess.Popen([browser, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, url
        except Exception as e:
            return False, f"Failed to open URL: {e}"
    
    def _exec_find_file(self, action: Action) -> Tuple[bool, str]:
        """Find files matching query"""
        query = action.target
        if not query:
            return False, "No search query"
        
        # Build search patterns
        patterns = []
        query_clean = query.lower().replace(" ", "*")
        patterns.append(f"*{query_clean}*")
        
        # Add extension patterns
        for ext in ['.conf', '.json', '.toml', '.yaml', '.yml']:
            patterns.append(f"*{query_clean}*{ext}")
        
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
                return True, unique[0]
            else:
                # Store as pending items for follow-up
                self.context.pending_items = [{"path": p, "name": os.path.basename(p)} for p in unique]
                result_lines = [f"{i+1}. {os.path.basename(p)}: {p}" for i, p in enumerate(unique)]
                return True, "Found multiple:\n" + "\n".join(result_lines) + "\n\nWhich one? (enter number)"
        
        return False, f"No files found matching '{query}'"
    
    def _exec_search_web(self, action: Action) -> Tuple[bool, str]:
        """Search the web"""
        query = action.target
        intent = action.options.get("intent", "search")
        name = action.options.get("name", "")
        
        # Try SearXNG
        try:
            from core.tool_registry import ToolRegistry
            registry = ToolRegistry()
            result = registry.execute_tool('web_search', {'query': query, 'num_results': 5})
            
            if result.success and result.output:
                if intent == "find_url" and name:
                    # Looking for a specific website
                    for item in result.output:
                        url = item.get('url', '')
                        title = item.get('title', '').lower()
                        # Match if name appears in title
                        if name.lower() in title or name.lower() in url.lower():
                            # Learn this URL
                            self.cache.learn_url(name, url, "search")
                            return True, url
                
                # Return search results
                lines = []
                for i, item in enumerate(result.output[:5]):
                    lines.append(f"{i+1}. {item.get('title', 'No title')}")
                    lines.append(f"   {item.get('url', '')}")
                    if item.get('snippet'):
                        lines.append(f"   {item.get('snippet', '')[:100]}...")
                    lines.append("")
                
                # Store as pending
                self.context.pending_items = [{"url": item.get('url')} for item in result.output[:5]]
                
                return True, "\n".join(lines) + "\nWhich one? (enter number)"
            
            return False, result.error or "Search failed"
            
        except Exception as e:
            return False, f"Search error: {e}. Is SearXNG running?"
    
    def _exec_scrape(self, action: Action) -> Tuple[bool, str]:
        """Scrape a webpage"""
        url = action.target
        if not url:
            return False, "No URL to scrape"
        
        try:
            from core.tool_registry import ToolRegistry
            registry = ToolRegistry()
            result = registry.execute_tool('scrape_page', {'url': url})
            
            if result.success and result.output:
                text = result.output.get('text', '')
                domain = result.output.get('domain', '')
                
                # Save scraped content
                scrape_dir = get_data_dir() / "scrape"
                scrape_dir.mkdir(parents=True, exist_ok=True)
                
                safe_name = re.sub(r'[^\w\-_.]', '_', domain)[:50]
                scrape_file = scrape_dir / f"{safe_name}.json"
                
                with open(scrape_file, 'w') as f:
                    json.dump({
                        "url": url,
                        "domain": domain,
                        "text": text,
                        "scraped_at": datetime.now().isoformat()
                    }, f, indent=2)
                
                return True, f"Scraped {domain}\nSaved to: {scrape_file}\nText length: {len(text)} chars"
        except Exception as e:
            return False, f"Scrape failed: {e}"
        
        return False, "Scrape failed"
    
    def _exec_command(self, action: Action) -> Tuple[bool, str]:
        """Execute a shell command"""
        cmd = action.target
        if not cmd:
            return False, "No command"
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            output = result.stdout or result.stderr
            return result.returncode == 0, output.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, f"Command failed: {e}"
    
    def _exec_set_preference(self, action: Action) -> Tuple[bool, str]:
        """Set a user preference"""
        key = action.target
        value = action.options.get("value", "")
        
        if key and value:
            self.cache.set_preference(key, value)
            return True, f"Set {key} = {value}"
        
        return False, "Invalid preference"
    
    def _exec_start_service(self, action: Action) -> Tuple[bool, str]:
        """Start a service"""
        service = action.target
        
        if service == "searxng":
            # Check if already running
            try:
                import requests
                requests.get("http://localhost:8888", timeout=2)
                return True, "SearXNG is already running"
            except:
                pass
            
            # Need confirmation
            if action.question:
                self.context.last_action = Action(
                    type=ActionType.RUN_COMMAND,
                    target="docker run -d -p 8888:8080 --name searxng searxng/searxng"
                )
                return True, action.question
        
        return False, f"Unknown service: {service}"
    
    def _exec_get_date(self, action: Action) -> Tuple[bool, str]:
        """Get current date/time"""
        now = datetime.now()
        return True, now.strftime("%A, %B %d, %Y - %H:%M")
    
    def _exec_switch_model(self, action: Action) -> Tuple[bool, str]:
        """Switch to a different model"""
        model_query = action.target
        if not model_query:
            return False, "No model specified"
        
        # List available models
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=10
            )
            available = result.stdout.lower()
            
            # Try to find matching model
            if model_query.lower() in available:
                self.balanced_model = model_query
                return True, f"Switched to {model_query}"
            
            # Fuzzy match
            for line in result.stdout.strip().split('\n')[1:]:
                model_name = line.split()[0]
                if model_query.lower() in model_name.lower():
                    self.balanced_model = model_name
                    return True, f"Switched to {model_name}"
            
            return False, f"Model '{model_query}' not found. Available:\n{result.stdout}"
            
        except Exception as e:
            return False, f"Failed to switch model: {e}"
    
    def get_smarter(self) -> str:
        """Self-improvement: analyze and improve knowledge"""
        # Clean bad cache entries
        self.cache.cleanup_bad_entries()
        
        # Discover system and update knowledge
        updates = []
        
        # Check which configs actually exist
        for name, path in list(self.kb.arch_linux.get("config_paths", {}).items()):
            expanded = os.path.expanduser(path)
            if not os.path.exists(expanded):
                # Try to find the correct path
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
        
        # Save updated knowledge
        if updates:
            self.kb.save_knowledge()
        
        return f"Cleaned cache, verified {len(self.kb.arch_linux.get('config_paths', {}))} config paths.\n" + "\n".join(updates) if updates else "Knowledge base is up to date."


# Global instance
_brain: Optional[RyxBrain] = None

def get_brain(ollama_client=None) -> RyxBrain:
    """Get or create the brain instance"""
    global _brain
    if _brain is None:
        if ollama_client is None:
            from core.ollama_client import OllamaClient
            from core.model_router import ModelRouter
            router = ModelRouter()
            ollama_client = OllamaClient(base_url=router.get_ollama_url())
        _brain = RyxBrain(ollama_client)
    return _brain
