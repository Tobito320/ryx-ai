"""
Ryx AI - Session Loop v2
Copilot-style interactive session with intelligent understanding.
Now using RyxBrainV2 for true AI understanding.
"""

import sys
import signal
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from core.ryx_brain_v2 import get_brain_v2, RyxBrainV2, ActionType, Action
from core.model_router import ModelRouter, ModelTier
from core.ollama_client import OllamaClient
from core.ui import RyxUI, Color
from core.paths import get_project_root, get_data_dir


class SessionLoopV2:
    """
    Copilot-style interactive session.
    
    Features:
    - AI understands prompts (no hardcoded patterns)
    - Knowledge-backed (no hallucinations)
    - Asks when uncertain
    - Does things instead of explaining
    - Learns from interactions
    - Supports follow-up questions
    - Multi-action support
    """

    def __init__(self, safety_mode: str = "normal"):
        self.ui = RyxUI()
        self.router = ModelRouter()
        self.ollama = OllamaClient(base_url=self.router.get_ollama_url())
        
        # The brain v2 - intelligent core with full AI understanding
        self.brain = get_brain_v2(self.ollama)
        
        # Session state
        self.running = True
        self.current_tier: Optional[ModelTier] = None
        self.conversation_history: List[Dict[str, str]] = []
        self.safety_mode = safety_mode
        self.session_start = datetime.now()
        
        # Stats
        self.stats = {
            "prompts": 0,
            "actions": 0,
            "cache_hits": 0,
            "llm_calls": 0,
            "files_opened": 0,
            "urls_opened": 0,
            "searches": 0,
            "scrapes": 0
        }
        
        # Session persistence
        self.session_file = get_data_dir() / "session_state.json"
        
        # Signal handlers
        signal.signal(signal.SIGINT, self._handle_interrupt)
        
        # Restore previous session
        self._restore_session()

    def _handle_interrupt(self, signum, frame):
        """Handle Ctrl+C"""
        print()
        self.ui.warning("Session interrupted (Ctrl+C)")
        self._save_session()
        self.ui.info("Session saved. Run 'ryx' to continue.")
        sys.exit(0)

    def _save_session(self):
        """Save session state"""
        try:
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            state = {
                'saved_at': datetime.now().isoformat(),
                'conversation_history': self.conversation_history[-50:],
                'current_tier': self.current_tier.value if self.current_tier else None,
                'stats': self.stats
            }
            with open(self.session_file, 'w') as f:
                json.dump(state, f, indent=2)
        except:
            pass

    def _restore_session(self):
        """Restore previous session"""
        try:
            if self.session_file.exists():
                with open(self.session_file) as f:
                    state = json.load(f)
                self.conversation_history = state.get('conversation_history', [])
                tier_name = state.get('current_tier')
                if tier_name:
                    self.current_tier = ModelTier(tier_name)
        except:
            pass

    def run(self):
        """Main session loop"""
        # Header
        tier_name = self.current_tier.value if self.current_tier else "balanced"
        model = self.router.get_model(ModelTier.BALANCED if not self.current_tier else self.current_tier)
        
        self.ui.header(
            tier=tier_name,
            repo=str(get_project_root()),
            safety=self.safety_mode
        )
        
        # Help text
        self.ui.info("Type naturally. Use /help for commands, @ for files, ! for shell.")
        
        if self.conversation_history:
            self.ui.info(f"Resumed session with {len(self.conversation_history)} messages")

        while self.running:
            try:
                user_input = self.ui.prompt()
                if not user_input:
                    continue
                
                self.stats["prompts"] += 1
                self._process_input(user_input)
                
            except KeyboardInterrupt:
                print()
                continue
            except EOFError:
                break

        self._save_session()
        self.ui.info("Goodbye!")

    def _process_input(self, user_input: str):
        """Process user input"""
        user_input = user_input.strip()
        
        # Slash commands
        if user_input.startswith('/'):
            self._handle_slash_command(user_input)
            return
        
        # Direct file reference
        if user_input.startswith('@'):
            self._handle_file_reference(user_input)
            return
        
        # Direct shell command
        if user_input.startswith('!'):
            self._handle_shell_command(user_input[1:])
            return
        
        # Handle with brain
        self._handle_natural_input(user_input)

    def _handle_natural_input(self, user_input: str):
        """Process natural language input with the brain"""
        
        # Save to history
        self.conversation_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })
        
        # Get action from brain
        action = self.brain.understand(user_input)
        
        # Handle clarification
        if action.type == ActionType.CLARIFY:
            self.ui.assistant_message(action.question or "Could you be more specific?")
            return
        
        # Handle answer
        if action.type == ActionType.ANSWER:
            response = action.target or "I'm not sure how to help."
            self.ui.assistant_message(response)
            self.conversation_history.append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().isoformat()
            })
            return
        
        # Execute action
        success, result = self.brain.execute(action)
        
        # Update stats
        self.stats["actions"] += 1
        if action.type == ActionType.OPEN_FILE:
            self.stats["files_opened"] += 1
        elif action.type == ActionType.OPEN_URL:
            self.stats["urls_opened"] += 1
        elif action.type == ActionType.SEARCH_WEB:
            self.stats["searches"] += 1
        elif action.type == ActionType.SCRAPE_URL:
            self.stats["scrapes"] += 1
        
        # Show result
        if success:
            if action.type == ActionType.OPEN_FILE:
                self.ui.success(f"Opened: {result}")
            elif action.type == ActionType.OPEN_URL:
                self.ui.success("Opened in browser")
            elif action.type == ActionType.FIND_FILE:
                if "Found multiple" in result or "Which one" in result:
                    self.ui.assistant_message(result)
                else:
                    # Single result
                    print(f"\n{Color.CYAN}{result}{Color.RESET}\n")
            elif action.type == ActionType.SEARCH_WEB:
                self.ui.assistant_message(result)
            elif action.type == ActionType.GET_DATE:
                self.ui.assistant_message(result)
            elif action.type == ActionType.SET_PREFERENCE:
                self.ui.success(result)
            elif action.type == ActionType.SWITCH_MODEL:
                self.ui.success(result)
            else:
                if result:
                    self.ui.assistant_message(result)
                else:
                    self.ui.success("Done")
        else:
            self.ui.error(result)
            
            # Offer help based on error
            if "not found" in result.lower() and action.type == ActionType.OPEN_FILE:
                self.ui.assistant_message("Want me to search for it? (y/n)")
                self.brain.context.last_action = Action(
                    type=ActionType.FIND_FILE,
                    target=action.target
                )
            elif "searxng" in result.lower():
                self.ui.assistant_message("Should I start SearXNG? (y/n)")
                self.brain.context.last_action = Action(
                    type=ActionType.START_SERVICE,
                    target="searxng"
                )
        
        # Save to history
        self.conversation_history.append({
            "role": "assistant",
            "content": result if result else "Done",
            "action": action.type.value,
            "timestamp": datetime.now().isoformat()
        })

    def _handle_slash_command(self, cmd: str):
        """Handle slash commands"""
        parts = cmd[1:].split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        commands = {
            'help': self._cmd_help,
            'h': self._cmd_help,
            '?': self._cmd_help,
            'quit': lambda a: setattr(self, 'running', False),
            'q': lambda a: setattr(self, 'running', False),
            'exit': lambda a: setattr(self, 'running', False),
            'clear': self._cmd_clear,
            'c': self._cmd_clear,
            'usage': self._cmd_usage,
            'u': self._cmd_usage,
            'models': self._cmd_models,
            'm': self._cmd_models,
            'tier': self._cmd_tier,
            't': self._cmd_tier,
            'scrape': self._cmd_scrape,
            'learn': self._cmd_learn,
            'search': self._cmd_search,
            'smarter': self._cmd_smarter,
            'export': self._cmd_export,
            'learning': self._cmd_learning_mode,
        }
        
        handler = commands.get(command)
        if handler:
            handler(args)
        else:
            self.ui.warning(f"Unknown command: {command}")

    def _handle_file_reference(self, ref: str):
        """Handle @file references"""
        path = ref[1:].strip()
        path = os.path.expanduser(path)
        
        if os.path.exists(path):
            try:
                with open(path) as f:
                    content = f.read()
                print(f"\n{Color.DIM}--- {path} ---{Color.RESET}")
                print(content[:2000])
                if len(content) > 2000:
                    print(f"\n{Color.DIM}... ({len(content)} chars total){Color.RESET}")
            except Exception as e:
                self.ui.error(f"Cannot read {path}: {e}")
        else:
            self.ui.error(f"File not found: {path}")

    def _handle_shell_command(self, cmd: str):
        """Handle !shell commands"""
        import subprocess
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(f"{Color.YELLOW}{result.stderr}{Color.RESET}")
        except subprocess.TimeoutExpired:
            self.ui.error("Command timed out")
        except Exception as e:
            self.ui.error(f"Command failed: {e}")

    # === Slash Command Handlers ===

    def _cmd_help(self, args: str):
        """Show help"""
        help_text = """
[bold purple]Ryx Commands[/bold purple]

[cyan]Slash Commands (session mode only):[/cyan]
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
  /learning on/off  Toggle learning mode (uses higher models)
  /export           Export session to markdown

[cyan]Special Syntax:[/cyan]
  @path/to/file     Include file contents in context
  !command          Run shell command directly

[cyan]Natural Commands:[/cyan]
  open youtube              Open website in browser
  open youtube with brave   Open with specific browser
  hyprland config           Open config in editor
  hyprland config new terminal  Open in new terminal
  find great wave           Search for files
  scrape arch wiki          Scrape and save content
  set zen as default browser  Set preference
  switch to mistral model   Change model
  what is the date today    Get current date

[cyan]Preferences:[/cyan]
  set <browser/editor/terminal> as default <value>

[cyan]After finding multiple results:[/cyan]
  Enter a number (1, 2, 3...) to select
  "the first one" / "the second one"
"""
        self.ui.panel(help_text, title="Help")

    def _cmd_clear(self, args: str):
        """Clear history"""
        self.conversation_history = []
        self.brain.context.last_query = None
        self.brain.context.last_result = None
        self.brain.context.pending_items = []
        self.ui.success("Context cleared")

    def _cmd_usage(self, args: str):
        """Show usage stats"""
        duration = datetime.now() - self.session_start
        minutes = int(duration.total_seconds() / 60)
        
        print(f"""
{Color.PURPLE}Session Statistics:{Color.RESET}
  Duration:     {minutes} minutes
  Prompts:      {self.stats['prompts']}
  Actions:      {self.stats['actions']}
  Cache hits:   {self.stats['cache_hits']}
  LLM calls:    {self.stats['llm_calls']}
  Files opened: {self.stats['files_opened']}
  URLs opened:  {self.stats['urls_opened']}
  Searches:     {self.stats['searches']}
  Scrapes:      {self.stats['scrapes']}
""")

    def _cmd_models(self, args: str):
        """List models"""
        models = self.router.list_models()
        self.ui.models_list(models)

    def _cmd_tier(self, args: str):
        """Switch tier"""
        if not args:
            self.ui.info("Available: fast, balanced, powerful, ultra")
            return
        
        tier = self.router.get_tier_by_name(args)
        if tier:
            self.current_tier = tier
            model = self.router.get_model(tier)
            self.ui.success(f"Switched to {tier.value} ({model.name})")
        else:
            self.ui.error(f"Unknown tier: {args}")

    def _cmd_scrape(self, args: str):
        """Scrape a URL"""
        if not args:
            self.ui.error("Usage: /scrape <url>")
            return
        
        url = args.strip()
        
        # Handle shorthand
        if not url.startswith('http'):
            # Check if it's a known site
            known_url = self.brain.kb.get_website_url(url.replace(' ', ''))
            if known_url:
                url = known_url
            else:
                url = f"https://{url.replace(' ', '')}"
        
        self.ui.info("Scraping...")
        
        action = Action(type=ActionType.SCRAPE_URL, target=url)
        success, result = self.brain.execute(action)
        
        if success:
            self.ui.success(f"Scraped: {result.split(chr(10))[0] if result else 'OK'}")
            if result:
                for line in result.split('\n')[1:]:
                    self.ui.info(line)
        else:
            self.ui.error(f"Scrape failed: {result}")

    def _cmd_learn(self, args: str):
        """Learn from scraped content"""
        scrape_dir = get_data_dir() / "scrape"
        
        if not scrape_dir.exists():
            self.ui.error("No scrape data. Use /scrape <url> first.")
            return
        
        # Find most recent scrape
        scrapes = list(scrape_dir.glob("*.json"))
        if not scrapes:
            self.ui.error("No scrape data. Use /scrape <url> first.")
            return
        
        latest = max(scrapes, key=lambda p: p.stat().st_mtime)
        
        self.ui.info("Learning...")
        
        try:
            with open(latest) as f:
                data = json.load(f)
            
            text = data.get('text', '')
            domain = data.get('domain', 'unknown')
            
            # Use LLM to summarize
            response = self.ollama.generate(
                prompt=f"Summarize this content in 3-5 bullet points:\n\n{text[:3000]}",
                model=self.brain.balanced_model,
                system="You are a summarizer. Be concise and extract key facts.",
                max_tokens=500
            )
            
            if response.response:
                # Save summary
                summary_file = scrape_dir / f"{domain.replace('.', '_')}_summary.md"
                with open(summary_file, 'w') as f:
                    f.write(f"# {domain}\n\n")
                    f.write(f"Source: {data.get('url', 'unknown')}\n")
                    f.write(f"Scraped: {data.get('scraped_at', 'unknown')}\n\n")
                    f.write("## Summary\n\n")
                    f.write(response.response)
                
                self.ui.success(f"Learned about: {domain}")
                self.ui.info(f"Saved to: {summary_file}")
            else:
                self.ui.error("Failed to process content")
                
        except Exception as e:
            self.ui.error(f"Learn failed: {e}")

    def _cmd_search(self, args: str):
        """Web search"""
        if not args:
            self.ui.error("Usage: /search <query>")
            return
        
        action = Action(type=ActionType.SEARCH_WEB, target=args)
        success, result = self.brain.execute(action)
        
        if success:
            self.ui.assistant_message(result)
        else:
            self.ui.error(result)

    def _cmd_smarter(self, args: str):
        """Self-improvement"""
        self.ui.info("Self-improving...")
        result = self.brain.get_smarter()
        self.ui.success("Self-improvement complete")
        print(result)

    def _cmd_learning_mode(self, args: str):
        """Toggle learning mode"""
        if args.lower() in ['on', 'true', '1', 'yes']:
            self.brain.set_learning_mode(True)
            self.ui.success("Learning mode ON - using higher models for precision")
        elif args.lower() in ['off', 'false', '0', 'no']:
            self.brain.set_learning_mode(False)
            self.ui.success("Learning mode OFF - using fast models")
        else:
            current = "ON" if self.brain.learning_mode else "OFF"
            self.ui.info(f"Learning mode is {current}. Use /learning on or /learning off")

    def _cmd_export(self, args: str):
        """Export session to markdown"""
        export_dir = get_data_dir() / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_file = export_dir / f"session_{timestamp}.md"
        
        with open(export_file, 'w') as f:
            f.write(f"# Ryx Session Export\n\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(f"## Conversation\n\n")
            
            for msg in self.conversation_history:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                f.write(f"**{role.title()}**: {content}\n\n")
        
        self.ui.success(f"Exported to: {export_file}")


# Entry point
def main():
    """Start the session loop"""
    session = SessionLoopV2()
    session.run()


if __name__ == "__main__":
    main()
