"""
Ryx AI - Intelligent Agent Core

This is the brain of Ryx. It uses AI to understand prompts and execute actions.
NO hardcoded patterns. Pure semantic understanding backed by knowledge.

Principles:
1. Understand, don't pattern match
2. Ask when ambiguous, don't guess
3. Act, don't explain (unless asked)
4. Never hallucinate - only return verified data
5. Use knowledge base for accuracy
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum

from core.paths import get_data_dir, get_project_root
from core.ollama_client import OllamaClient


class ActionType(Enum):
    """What Ryx should do"""
    OPEN_FILE = "open_file"           # Open file in editor
    OPEN_URL = "open_url"             # Open URL in browser
    FIND_FILE = "find_file"           # Search for file, return path
    RUN_COMMAND = "run_command"       # Execute shell command
    ANSWER = "answer"                 # Just answer a question
    CLARIFY = "clarify"               # Need more info from user
    LEARN = "learn"                   # Add to knowledge base


@dataclass
class Action:
    """A planned action"""
    type: ActionType
    target: Optional[str] = None      # File path, URL, command, etc.
    options: Dict[str, Any] = None    # Additional options
    question: Optional[str] = None    # Clarification question if needed
    confidence: float = 1.0           # How sure we are


class KnowledgeBase:
    """
    Pre-loaded knowledge for accurate responses.
    Loaded once at startup for instant access.
    """
    
    def __init__(self):
        self.knowledge_dir = get_data_dir() / "knowledge"
        self.arch_linux: Dict = {}
        self.file_system: Dict = {}
        self.user_learned: Dict = {}
        self._load_knowledge()
    
    def _load_knowledge(self):
        """Load all knowledge files"""
        # Load Arch Linux knowledge
        arch_file = self.knowledge_dir / "arch_linux.json"
        if arch_file.exists():
            with open(arch_file) as f:
                self.arch_linux = json.load(f)
        
        # Load file system knowledge
        fs_file = self.knowledge_dir / "file_system.json"
        if fs_file.exists():
            with open(fs_file) as f:
                self.file_system = json.load(f)
        
        # Load user-specific learned knowledge
        learned_file = get_data_dir() / "user_knowledge.json"
        if learned_file.exists():
            with open(learned_file) as f:
                self.user_learned = json.load(f)
    
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
            return os.path.expanduser(path)
        return None
    
    def get_website_url(self, name: str) -> Optional[str]:
        """Get website URL from knowledge base"""
        name_lower = name.lower().strip()
        websites = self.arch_linux.get("websites", {})
        return websites.get(name_lower)
    
    def get_default_browser(self) -> str:
        """Get default browser"""
        return self.arch_linux.get("default_browser", "firefox")
    
    def get_default_editor(self) -> str:
        """Get default editor"""
        return os.environ.get("EDITOR", self.arch_linux.get("default_editor", "nvim"))
    
    def get_default_terminal(self) -> str:
        """Get default terminal"""
        return self.arch_linux.get("default_terminal", "kitty")
    
    def save_learned(self, key: str, value: Any):
        """Save user-learned knowledge"""
        self.user_learned[key] = value
        learned_file = get_data_dir() / "user_knowledge.json"
        with open(learned_file, 'w') as f:
            json.dump(self.user_learned, f, indent=2)


class IntelligentAgent:
    """
    The intelligent core of Ryx.
    Uses LLM for understanding, knowledge base for accuracy.
    """
    
    def __init__(self, ollama_client: OllamaClient):
        self.ollama = ollama_client
        self.kb = KnowledgeBase()
        self.model = "qwen2.5:3b"  # Fast model for understanding
        self.smart_model = "qwen2.5-coder:14b"  # Smart model for complex tasks
    
    def understand(self, prompt: str) -> Action:
        """
        Understand what the user wants and return an action.
        This is the main entry point.
        """
        prompt_lower = prompt.lower().strip()
        
        # Quick knowledge-based resolution (no LLM needed)
        action = self._try_knowledge_resolution(prompt_lower)
        if action:
            return action
        
        # Use LLM to understand the intent
        return self._llm_understand(prompt)
    
    def _try_knowledge_resolution(self, prompt: str) -> Optional[Action]:
        """
        Try to resolve using knowledge base without LLM.
        Handles common patterns instantly.
        """
        prompt_clean = prompt.lower().strip()
        
        # Remove common prefixes and suffixes
        target = prompt_clean
        
        # Remove action words
        for prefix in ["open ", "edit ", "show ", "open the ", "edit the "]:
            if target.startswith(prefix):
                target = target[len(prefix):]
        
        # Handle "X in browser" pattern
        if " in browser" in target:
            url_target = target.replace(" in browser", "").strip()
            url = self.kb.get_website_url(url_target)
            if url:
                return Action(
                    type=ActionType.OPEN_URL,
                    target=url,
                    options={"browser": self.kb.get_default_browser()}
                )
        
        # Handle "X in new terminal" pattern
        new_terminal = False
        if " in new terminal" in target:
            target = target.replace(" in new terminal", "").strip()
            new_terminal = True
        
        # Remove common words that don't add meaning
        for word in ["the", "my", "a", "please", "can you", "could you", "for me"]:
            target = target.replace(f" {word} ", " ").replace(f"{word} ", "").replace(f" {word}", "").strip()
        
        target = target.strip()
        
        # Check if it's a known website
        url = self.kb.get_website_url(target)
        if url:
            return Action(
                type=ActionType.OPEN_URL,
                target=url,
                options={"browser": self.kb.get_default_browser()}
            )
        
        # Check if it's a known config (try with and without "config" suffix)
        config_path = self.kb.get_config_path(target)
        if not config_path and target.endswith(" config"):
            config_path = self.kb.get_config_path(target.replace(" config", ""))
        if not config_path:
            config_path = self.kb.get_config_path(target + " config")
            
        if config_path and os.path.exists(config_path):
            return Action(
                type=ActionType.OPEN_FILE,
                target=config_path,
                options={"editor": self.kb.get_default_editor(), "new_terminal": new_terminal}
            )
        
        # Pattern: "find X" or "where is X" or "locate X"
        for prefix in ["find ", "where is ", "locate ", "search for ", "look for "]:
            if prompt_clean.startswith(prefix):
                query = prompt_clean[len(prefix):].strip()
                # Clean query
                for word in ["a file", "file", "called", "named", "the"]:
                    query = query.replace(word, "").strip()
                return Action(
                    type=ActionType.FIND_FILE,
                    target=query
                )
        
        return None
    
    def _llm_understand(self, prompt: str) -> Action:
        """Use LLM to understand ambiguous prompts"""
        
        # Build context with knowledge
        knowledge_context = self._build_knowledge_context()
        
        system_prompt = f"""You are Ryx's brain. Analyze the user's prompt and decide what action to take.

KNOWLEDGE BASE:
{knowledge_context}

RULES:
1. If the user wants to OPEN something:
   - If it's a website/URL -> action: open_url
   - If it's a file/config -> action: open_file
   - If unclear which -> action: clarify

2. If the user wants to FIND something:
   - action: find_file
   - NEVER make up paths. Say you'll search.

3. If it's a QUESTION:
   - action: answer
   - Be brief (1-2 sentences max)

4. If AMBIGUOUS:
   - action: clarify
   - Ask a simple yes/no or choice question

RESPOND IN JSON ONLY:
{{"action": "open_file|open_url|find_file|run_command|answer|clarify", "target": "path/url/command/answer", "question": "clarification question if action=clarify", "confidence": 0.0-1.0}}
"""

        response = self.ollama.generate(
            prompt=f"User prompt: {prompt}",
            model=self.model,
            system=system_prompt,
            max_tokens=200,
            temperature=0.1
        )
        
        if response.error:
            return Action(type=ActionType.ANSWER, target=f"Error: {response.error}")
        
        # Parse the JSON response
        try:
            # Extract JSON from response
            text = response.response.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            data = json.loads(text)
            action_type = ActionType(data.get("action", "answer"))
            
            return Action(
                type=action_type,
                target=data.get("target"),
                question=data.get("question"),
                confidence=data.get("confidence", 0.8)
            )
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback: treat as answer
            return Action(type=ActionType.ANSWER, target=response.response)
    
    def _build_knowledge_context(self) -> str:
        """Build knowledge context for LLM"""
        lines = []
        
        # Config paths
        lines.append("Config file paths:")
        for name, path in list(self.kb.arch_linux.get("config_paths", {}).items())[:15]:
            lines.append(f"  {name}: {path}")
        
        # Websites
        lines.append("\nKnown websites:")
        for name, url in list(self.kb.arch_linux.get("websites", {}).items())[:10]:
            lines.append(f"  {name}: {url}")
        
        # Defaults
        lines.append(f"\nDefaults: browser={self.kb.get_default_browser()}, editor={self.kb.get_default_editor()}, terminal={self.kb.get_default_terminal()}")
        
        return "\n".join(lines)
    
    def execute(self, action: Action) -> Tuple[bool, str]:
        """Execute an action and return (success, result)"""
        
        if action.type == ActionType.CLARIFY:
            return True, action.question or "Could you clarify what you want?"
        
        if action.type == ActionType.ANSWER:
            return True, action.target or "I'm not sure how to help with that."
        
        if action.type == ActionType.OPEN_FILE:
            return self._execute_open_file(action)
        
        if action.type == ActionType.OPEN_URL:
            return self._execute_open_url(action)
        
        if action.type == ActionType.FIND_FILE:
            return self._execute_find_file(action)
        
        if action.type == ActionType.RUN_COMMAND:
            return self._execute_command(action)
        
        return False, "Unknown action type"
    
    def _execute_open_file(self, action: Action) -> Tuple[bool, str]:
        """Open a file in editor"""
        path = action.target
        if not path:
            return False, "No file path specified"
        
        # Expand ~ to home
        path = os.path.expanduser(path)
        
        # Check if file exists
        if not os.path.exists(path):
            return False, f"File not found: {path}"
        
        editor = action.options.get("editor") if action.options else None
        editor = editor or self.kb.get_default_editor()
        
        # Check if we should open in new terminal
        new_terminal = action.options.get("new_terminal", False) if action.options else False
        
        try:
            if new_terminal:
                terminal = self.kb.get_default_terminal()
                subprocess.Popen([terminal, "-e", editor, path], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
            else:
                subprocess.run([editor, path])
            return True, f"Opened {path} in {editor}"
        except Exception as e:
            return False, f"Failed to open: {e}"
    
    def _execute_open_url(self, action: Action) -> Tuple[bool, str]:
        """Open a URL in browser"""
        url = action.target
        if not url:
            return False, "No URL specified"
        
        # Add https if missing
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        
        browser = action.options.get("browser") if action.options else None
        browser = browser or self.kb.get_default_browser()
        
        try:
            subprocess.Popen([browser, url],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
            return True, f"Opened {url}"
        except Exception as e:
            return False, f"Failed to open URL: {e}"
    
    def _execute_find_file(self, action: Action) -> Tuple[bool, str]:
        """Find a file and return its path"""
        query = action.target
        if not query:
            return False, "No search query specified"
        
        # Build search patterns
        patterns = []
        query_clean = query.lower().replace(" ", "*")
        patterns.append(f"*{query_clean}*")
        
        # Search common locations
        search_dirs = [
            os.path.expanduser("~"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Pictures"),
        ]
        
        found_files = []
        for search_dir in search_dirs:
            if not os.path.exists(search_dir):
                continue
            
            for pattern in patterns:
                try:
                    result = subprocess.run(
                        ["find", search_dir, "-maxdepth", "4", "-iname", pattern, "-type", "f"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.stdout.strip():
                        found_files.extend(result.stdout.strip().split("\n"))
                except:
                    pass
        
        if found_files:
            # Return just the paths, no extra text
            unique = list(set(found_files))[:5]
            return True, "\n".join(unique)
        
        return False, f"No files found matching '{query}'"
    
    def _execute_command(self, action: Action) -> Tuple[bool, str]:
        """Execute a shell command"""
        command = action.target
        if not command:
            return False, "No command specified"
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout or result.stderr
            return result.returncode == 0, output.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, f"Command failed: {e}"
    
    def get_smarter(self) -> str:
        """
        Self-improvement: Review and optimize knowledge.
        Uses a powerful model to analyze and improve the knowledge base.
        """
        # Get current knowledge
        knowledge = {
            "arch_linux": self.kb.arch_linux,
            "user_learned": self.kb.user_learned
        }
        
        # Discover system info
        system_info = self._discover_system()
        
        system_prompt = """You are analyzing and improving Ryx's knowledge base.

Current knowledge:
{knowledge}

Discovered system info:
{system_info}

Tasks:
1. Identify any outdated or incorrect config paths
2. Add any missing common configs based on what's installed
3. Update defaults based on actual system
4. Remove any unnecessary entries

Return a JSON with improvements:
{{"updates": {{"config_paths": {{}}, "websites": {{}}, "defaults": {{}}}}, "removals": [], "summary": "what was improved"}}
"""
        
        response = self.ollama.generate(
            prompt="Analyze and improve the knowledge base",
            model=self.smart_model,
            system=system_prompt.format(
                knowledge=json.dumps(knowledge, indent=2)[:2000],
                system_info=json.dumps(system_info, indent=2)
            ),
            max_tokens=1000,
            temperature=0.2
        )
        
        if response.error:
            return f"Failed to improve: {response.error}"
        
        try:
            # Parse and apply improvements
            text = response.response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            
            improvements = json.loads(text)
            
            # Apply updates
            updates = improvements.get("updates", {})
            if "config_paths" in updates:
                self.kb.arch_linux["config_paths"].update(updates["config_paths"])
            if "websites" in updates:
                self.kb.arch_linux["websites"].update(updates["websites"])
            
            # Save updated knowledge
            arch_file = self.kb.knowledge_dir / "arch_linux.json"
            with open(arch_file, 'w') as f:
                json.dump(self.kb.arch_linux, f, indent=2)
            
            return improvements.get("summary", "Knowledge base improved")
            
        except Exception as e:
            return f"Improvement analysis completed but couldn't apply: {e}"
    
    def _discover_system(self) -> Dict:
        """Discover actual system configuration"""
        info = {}
        
        # Check which configs actually exist
        existing_configs = {}
        for name, path in self.kb.arch_linux.get("config_paths", {}).items():
            expanded = os.path.expanduser(path)
            if os.path.exists(expanded):
                existing_configs[name] = expanded
        info["existing_configs"] = existing_configs
        
        # Check installed packages
        try:
            result = subprocess.run(
                ["pacman", "-Q"],
                capture_output=True,
                text=True,
                timeout=5
            )
            packages = [line.split()[0] for line in result.stdout.strip().split("\n")[:50]]
            info["installed_packages"] = packages
        except:
            pass
        
        # Get actual defaults
        info["env"] = {
            "EDITOR": os.environ.get("EDITOR", "not set"),
            "BROWSER": os.environ.get("BROWSER", "not set"),
            "TERMINAL": os.environ.get("TERMINAL", "not set"),
            "SHELL": os.environ.get("SHELL", "not set"),
        }
        
        return info


# Global instance
_agent: Optional[IntelligentAgent] = None

def get_agent(ollama_client: OllamaClient = None) -> IntelligentAgent:
    """Get or create the intelligent agent"""
    global _agent
    if _agent is None:
        if ollama_client is None:
            from core.model_router import ModelRouter
            router = ModelRouter()
            ollama_client = OllamaClient(base_url=router.get_ollama_url())
        _agent = IntelligentAgent(ollama_client)
    return _agent
