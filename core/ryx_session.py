"""
Ryx Session - Copilot CLI Style Interactive Mode
================================================

Slash commands (only in session mode):
/help       - Show help
/clear      - Clear conversation
/usage      - Show token/usage stats
/models     - List available models
/tier       - Switch model tier
/scrape     - Scrape a URL
/learn      - Learn from scraped data
/search     - Web search
/smarter    - Self-improvement
/export     - Export session
/quit       - Exit

@ references:
@path/to/file - Include file contents in context

! shell commands:
!git status   - Run shell command directly
"""

import os
import sys
import json
import subprocess
import signal
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from core.ryx_engine import RyxEngine, get_engine, Action, ActionType
from core.ui import RyxUI, Color, Emoji
from core.paths import get_data_dir, get_project_root
from core.model_router import ModelRouter, ModelTier


class SessionStats:
    """Track session statistics"""
    
    def __init__(self):
        self.started_at = datetime.now()
        self.prompts = 0
        self.actions = 0
        self.files_opened = 0
        self.urls_opened = 0
        self.searches = 0
        self.scrapes = 0
        self.llm_calls = 0
        self.cache_hits = 0
    
    def to_dict(self) -> Dict:
        return {
            "started_at": self.started_at.isoformat(),
            "duration_minutes": (datetime.now() - self.started_at).seconds // 60,
            "prompts": self.prompts,
            "actions": self.actions,
            "files_opened": self.files_opened,
            "urls_opened": self.urls_opened,
            "searches": self.searches,
            "scrapes": self.scrapes,
            "llm_calls": self.llm_calls,
            "cache_hits": self.cache_hits,
        }


class RyxSession:
    """
    Interactive Ryx session - Copilot CLI style
    """
    
    def __init__(self, safety_mode: str = "normal"):
        self.ui = RyxUI()
        self.engine = get_engine()
        self.router = ModelRouter()
        
        # Session state
        self.running = True
        self.safety_mode = safety_mode
        self.stats = SessionStats()
        self.conversation: List[Dict[str, str]] = []
        self.context_files: Dict[str, str] = {}  # @ file references
        
        # Session persistence
        self.session_dir = get_data_dir() / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Signal handlers
        signal.signal(signal.SIGINT, self._handle_interrupt)
    
    def _handle_interrupt(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print()
        self.ui.warning("Session interrupted (Ctrl+C)")
        self._save_session()
        self.ui.info("Session saved. Run 'ryx' to continue.")
        sys.exit(0)
    
    # ─────────────────────────────────────────────────────────────
    # Main Loop
    # ─────────────────────────────────────────────────────────────
    
    def run(self):
        """Main session loop"""
        self._show_header()
        self._load_last_session()
        
        while self.running:
            try:
                user_input = self.ui.prompt()
                
                if not user_input:
                    continue
                
                self._process_input(user_input)
                
            except EOFError:
                break
            except KeyboardInterrupt:
                continue
        
        self._save_session()
        self.ui.info("Goodbye!")
    
    def _show_header(self):
        """Show session header"""
        self.ui.header(
            tier="balanced",
            repo=str(get_project_root()),
            safety=self.safety_mode
        )
        self.ui.info("Type naturally. Use /help for commands, @ for files, ! for shell.")
    
    def _process_input(self, user_input: str) -> None:
        """Process user input"""
        self.stats.prompts += 1
        
        # ─────────────────────────────────────────────────────────
        # Slash commands
        # ─────────────────────────────────────────────────────────
        
        if user_input.startswith("/"):
            self._handle_slash_command(user_input)
            return
        
        # ─────────────────────────────────────────────────────────
        # Shell commands (!)
        # ─────────────────────────────────────────────────────────
        
        if user_input.startswith("!"):
            self._run_shell_command(user_input[1:].strip())
            return
        
        # ─────────────────────────────────────────────────────────
        # @ file references
        # ─────────────────────────────────────────────────────────
        
        user_input, files = self._extract_file_refs(user_input)
        if files:
            for f in files:
                self._load_file_context(f)
        
        # ─────────────────────────────────────────────────────────
        # Check for new terminal flag
        # ─────────────────────────────────────────────────────────
        
        new_terminal = any(x in user_input.lower() for x in [
            "new terminal", "new term", "external terminal", "separate terminal"
        ])
        
        # Clean up the input
        for phrase in ["new terminal", "new term", "external terminal", "separate terminal",
                      "same terminal", "this terminal", "current terminal", "in terminal"]:
            user_input = user_input.lower().replace(phrase, "").strip()
        
        # ─────────────────────────────────────────────────────────
        # Process with engine
        # ─────────────────────────────────────────────────────────
        
        action = self.engine.process(user_input, new_terminal=new_terminal)
        
        # Track stats
        if action.source == "cache":
            self.stats.cache_hits += 1
        else:
            self.stats.llm_calls += 1
        
        # Execute and show result
        self._execute_action(action)
    
    # ─────────────────────────────────────────────────────────────
    # Slash Commands
    # ─────────────────────────────────────────────────────────────
    
    def _handle_slash_command(self, cmd: str):
        """Handle slash commands"""
        parts = cmd[1:].split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        commands = {
            "help": self._cmd_help,
            "h": self._cmd_help,
            "?": self._cmd_help,
            "quit": self._cmd_quit,
            "q": self._cmd_quit,
            "exit": self._cmd_quit,
            "clear": self._cmd_clear,
            "c": self._cmd_clear,
            "usage": self._cmd_usage,
            "u": self._cmd_usage,
            "models": self._cmd_models,
            "m": self._cmd_models,
            "tier": self._cmd_tier,
            "t": self._cmd_tier,
            "scrape": self._cmd_scrape,
            "s": self._cmd_scrape,
            "learn": self._cmd_learn,
            "l": self._cmd_learn,
            "search": self._cmd_search,
            "smarter": self._cmd_smarter,
            "export": self._cmd_export,
            "e": self._cmd_export,
        }
        
        handler = commands.get(command)
        if handler:
            handler(args)
        else:
            self.ui.error(f"Unknown command: /{command}")
            self.ui.info("Use /help to see available commands")
    
    def _cmd_help(self, args: str):
        """Show help"""
        print(f"""
{Color.PURPLE_BOLD}Ryx Commands:{Color.RESET}

{Color.CYAN}Slash Commands (session mode only):{Color.RESET}
  /help, /h, /?     Show this help
  /quit, /q         Exit session
  /clear, /c        Clear conversation history
  /usage, /u        Show session statistics
  /models, /m       List available models
  /tier <name>      Switch model tier (fast/balanced/smart)
  /scrape <url>     Scrape webpage content
  /learn            Learn from last scrape
  /search <query>   Web search via SearXNG
  /smarter          Self-improvement mode
  /export           Export session to markdown

{Color.CYAN}Special Syntax:{Color.RESET}
  @path/to/file     Include file contents in context
  !command          Run shell command directly

{Color.CYAN}Natural Commands:{Color.RESET}
  open youtube      Open website in browser
  hyprland config   Open config in editor
  find great wave   Search for files
  scrape arch wiki  Scrape and save content

{Color.CYAN}Flags:{Color.RESET}
  "new terminal"    Open in new terminal window
  "same terminal"   Open in current terminal
""")
    
    def _cmd_quit(self, args: str):
        """Exit session"""
        self.running = False
    
    def _cmd_clear(self, args: str):
        """Clear conversation"""
        self.conversation = []
        self.context_files = {}
        self.ui.success("Conversation cleared")
    
    def _cmd_usage(self, args: str):
        """Show usage statistics"""
        stats = self.stats.to_dict()
        print(f"""
{Color.PURPLE_BOLD}Session Statistics:{Color.RESET}
  Duration:     {stats['duration_minutes']} minutes
  Prompts:      {stats['prompts']}
  Actions:      {stats['actions']}
  Cache hits:   {stats['cache_hits']}
  LLM calls:    {stats['llm_calls']}
  Files opened: {stats['files_opened']}
  URLs opened:  {stats['urls_opened']}
  Searches:     {stats['searches']}
  Scrapes:      {stats['scrapes']}
""")
    
    def _cmd_models(self, args: str):
        """List available models"""
        print(f"\n{Color.PURPLE_BOLD}Available Models:{Color.RESET}")
        print(f"  {Color.CYAN}tiny{Color.RESET}     qwen2.5:1.5b    - Cached lookups")
        print(f"  {Color.CYAN}fast{Color.RESET}     qwen2.5:3b      - Simple tasks")
        print(f"  {Color.CYAN}balanced{Color.RESET} qwen2.5:7b      - General use")
        print(f"  {Color.CYAN}smart{Color.RESET}    qwen2.5-coder:14b - Complex tasks")
        print()
    
    def _cmd_tier(self, args: str):
        """Switch model tier"""
        if not args:
            self.ui.info("Usage: /tier <fast|balanced|smart>")
            return
        
        tier = args.lower().strip()
        if tier in ["fast", "balanced", "smart", "tiny"]:
            self.ui.success(f"Switched to {tier} tier")
        else:
            self.ui.error(f"Unknown tier: {tier}")
    
    def _cmd_scrape(self, args: str):
        """Scrape a URL"""
        if not args:
            self.ui.info("Usage: /scrape <url>")
            return
        
        self.ui.status(Emoji.SEARCH, "Scraping...", Color.CYAN)
        
        result = self.engine.scraper.scrape(args)
        
        if "error" in result:
            self.ui.error(f"Scrape failed: {result['error']}")
        else:
            self.ui.success(f"Scraped: {result.get('title', 'Unknown')}")
            self.ui.info(f"Text: {len(result.get('text', ''))} chars")
            self.ui.info(f"Saved to: {self.engine.scraper.data_dir}")
            
            # Store for /learn
            self._last_scrape = result
        
        self.stats.scrapes += 1
    
    def _cmd_learn(self, args: str):
        """Learn from last scrape"""
        if not hasattr(self, '_last_scrape') or not self._last_scrape:
            self.ui.error("No scrape data. Use /scrape <url> first.")
            return
        
        self.ui.status(Emoji.BRAIN, "Learning...", Color.PURPLE)
        result = self.engine.learn_from_scrape(self._last_scrape)
        print(result)
    
    def _cmd_search(self, args: str):
        """Web search"""
        if not args:
            self.ui.info("Usage: /search <query>")
            return
        
        if not self.engine.searcher.enabled:
            self.ui.error("SearXNG not running. Start with:")
            print("  docker run -d -p 8888:8080 searxng/searxng")
            return
        
        self.ui.status(Emoji.SEARCH, "Searching...", Color.CYAN)
        
        results = self.engine.searcher.search(args)
        
        if not results:
            self.ui.error("No results found")
            return
        
        print(f"\n{Color.PURPLE_BOLD}Search Results:{Color.RESET}")
        for i, r in enumerate(results, 1):
            print(f"\n{Color.CYAN}{i}. {r['title']}{Color.RESET}")
            print(f"   {Color.GRAY}{r['url']}{Color.RESET}")
            print(f"   {r['content'][:150]}...")
        print()
        
        self.stats.searches += 1
    
    def _cmd_smarter(self, args: str):
        """Self-improvement"""
        self.ui.status(Emoji.BRAIN, "Self-improving...", Color.PURPLE)
        result = self.engine.get_smarter()
        print(result)
    
    def _cmd_export(self, args: str):
        """Export session to markdown"""
        filename = args or f"session_{self.session_id}.md"
        
        content = f"# Ryx Session - {self.session_id}\n\n"
        content += f"Started: {self.stats.started_at.isoformat()}\n\n"
        
        content += "## Conversation\n\n"
        for msg in self.conversation:
            role = msg.get("role", "user")
            text = msg.get("content", "")
            content += f"**{role.title()}**: {text}\n\n"
        
        content += "## Statistics\n\n"
        for k, v in self.stats.to_dict().items():
            content += f"- {k}: {v}\n"
        
        # Save
        export_path = get_data_dir() / "exports"
        export_path.mkdir(exist_ok=True)
        (export_path / filename).write_text(content)
        
        self.ui.success(f"Exported to: {export_path / filename}")
    
    # ─────────────────────────────────────────────────────────────
    # Shell Commands
    # ─────────────────────────────────────────────────────────────
    
    def _run_shell_command(self, cmd: str):
        """Run a shell command directly"""
        if not cmd:
            return
        
        self.ui.info(f"Running: {cmd}")
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(f"{Color.RED}{result.stderr}{Color.RESET}")
            
            if result.returncode != 0:
                self.ui.warning(f"Exit code: {result.returncode}")
                
        except subprocess.TimeoutExpired:
            self.ui.error("Command timed out (30s)")
        except Exception as e:
            self.ui.error(f"Command failed: {e}")
    
    # ─────────────────────────────────────────────────────────────
    # File References
    # ─────────────────────────────────────────────────────────────
    
    def _extract_file_refs(self, text: str) -> tuple:
        """Extract @file references from text"""
        import re
        
        files = []
        pattern = r'@([\w\-_./~]+)'
        
        for match in re.finditer(pattern, text):
            files.append(match.group(1))
        
        # Remove @ references from text
        clean_text = re.sub(pattern, '', text).strip()
        
        return clean_text, files
    
    def _load_file_context(self, path: str):
        """Load file contents into context"""
        # Expand path
        if path.startswith("~"):
            path = str(Path.home() / path[2:])
        elif not path.startswith("/"):
            path = str(Path.cwd() / path)
        
        try:
            content = Path(path).read_text()
            self.context_files[path] = content[:5000]  # Limit size
            self.ui.info(f"Loaded: {path} ({len(content)} chars)")
        except Exception as e:
            self.ui.error(f"Cannot read {path}: {e}")
    
    # ─────────────────────────────────────────────────────────────
    # Action Execution
    # ─────────────────────────────────────────────────────────────
    
    def _execute_action(self, action: Action):
        """Execute an action and display result"""
        self.stats.actions += 1
        
        # Track by type
        if action.type == ActionType.OPEN_FILE:
            self.stats.files_opened += 1
        elif action.type == ActionType.OPEN_URL:
            self.stats.urls_opened += 1
        elif action.type == ActionType.SEARCH_WEB:
            self.stats.searches += 1
        
        # Execute
        result = self.engine.execute(action)
        
        # Display based on type
        if action.type in [ActionType.CLARIFY, ActionType.REFUSE]:
            self.ui.assistant_message(result)
        elif action.type == ActionType.ANSWER:
            self.ui.assistant_message(result)
        elif result.startswith("✅") or result.startswith("❌"):
            print(result)
        else:
            print(result)
        
        # Add to conversation
        self.conversation.append({
            "role": "assistant",
            "content": result,
            "action": action.type.value,
            "source": action.source
        })
    
    # ─────────────────────────────────────────────────────────────
    # Session Persistence
    # ─────────────────────────────────────────────────────────────
    
    def _save_session(self):
        """Save session state"""
        state = {
            "id": self.session_id,
            "conversation": self.conversation,
            "stats": self.stats.to_dict(),
            "context_files": list(self.context_files.keys()),
        }
        
        path = self.session_dir / f"{self.session_id}.json"
        path.write_text(json.dumps(state, indent=2))
    
    def _load_last_session(self):
        """Load most recent session"""
        sessions = sorted(self.session_dir.glob("*.json"), reverse=True)
        
        if sessions:
            try:
                state = json.loads(sessions[0].read_text())
                self.conversation = state.get("conversation", [])[-10:]  # Last 10 messages
                self.ui.info(f"Resumed session with {len(self.conversation)} messages")
            except:
                pass


def run_session(safety_mode: str = "normal"):
    """Entry point for interactive session"""
    session = RyxSession(safety_mode=safety_mode)
    session.run()


def run_oneshot(prompt: str, new_terminal: bool = False) -> str:
    """Run a single command without interactive session"""
    engine = get_engine()
    
    # Process the prompt
    action = engine.process(prompt, new_terminal=new_terminal)
    
    # Execute and return result
    return engine.execute(action)
