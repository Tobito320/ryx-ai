"""
Ryx AI - Session Loop: Interactive Session

Copilot CLI / Claude Code style session.

Features:
- @ for files, ! for shell
- /commands for control
- Minimal output
- Token streaming with stats
"""

import os
import sys
import json
import readline
import signal
from datetime import datetime
from typing import Optional

from core.paths import get_data_dir
from core.ryx_brain import RyxBrain, Plan, Intent, get_brain
from core.ollama_client import OllamaClient
from core.model_router import ModelRouter

# Use new CLI UI (try modern first, fall back to legacy)
try:
    from core.cli_ui import get_ui, get_cli, get_modern_cli, CLI
except ImportError:
    from core.rich_ui import get_ui, RyxUI as CLI
    get_cli = get_ui
    get_modern_cli = get_ui


class SessionLoop:
    """
    Copilot CLI style interactive session.
    """
    
    def __init__(self, safety_mode: str = "normal"):
        self.safety_mode = safety_mode
        # Try modern CLI with fixed input box, fall back to legacy
        self.cli = get_modern_cli(cwd=os.getcwd()) or get_cli()
        self.router = ModelRouter()
        self.ollama = OllamaClient(base_url=self.router.get_ollama_url())
        self.brain = get_brain(self.ollama)
        
        self.running = True
        self.session_start = datetime.now()
        self.history = []
        
        self.stats = {
            'prompts': 0,
            'actions': 0,
            'files': 0,
            'urls': 0,
            'searches': 0,
            'scrapes': 0
        }
        
        self._setup_readline()
        self._setup_signals()
    
    def _setup_readline(self):
        history_file = get_data_dir() / "history" / "session"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            readline.read_history_file(history_file)
        except FileNotFoundError:
            pass
        
        readline.set_history_length(1000)
        import atexit
        atexit.register(readline.write_history_file, history_file)
    
    def _setup_signals(self):
        def handler(sig, frame):
            print()
            self._save()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, handler)
    
    def run(self):
        """Main loop - with bottom bar layout"""
        self._show_welcome()
        self._health_check()
        self._restore()
        
        while self.running:
            try:
                user_input = self.cli.prompt()
                
                if not user_input.strip():
                    continue
                
                self._process(user_input.strip())
                # Single footer (bottom hints) after handling input
                self.cli.footer(msgs=len(self.history))
                
            except KeyboardInterrupt:
                print()
                self._save()
                break
            except Exception as e:
                self.cli.error(str(e))
    
    def _health_check(self):
        """Quick health check"""
        health = self.brain.health_check()
        
        if not health["ollama"]:
            self.cli.error("Ollama not running. Start: systemctl start ollama")
            return
        
        if not health["models"]:
            self.cli.warn("No models. Run: ollama pull qwen2.5:3b")
    
    def _show_welcome(self):
        """Show welcome - Copilot CLI style"""
        import subprocess
        from core.model_router import select_model
        
        model = select_model("hi").name
        
        # Get git branch
        branch = ""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True, text=True, timeout=1
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
        except:
            pass
        
        self.cli.welcome(model=model, branch=branch, cwd=os.getcwd())
    
    def _process(self, user_input: str):
        """Process user input"""
        self.stats['prompts'] += 1
        self.history.append({'role': 'user', 'content': user_input, 'ts': datetime.now().isoformat()})
        self.brain.add_message('user', user_input)
        
        # Slash commands
        if user_input.startswith('/'):
            self._slash_command(user_input)
            return
        
        # @ = file include
        if user_input.startswith('@'):
            self._file_include(user_input[1:])
            return
        
        # ! = shell command
        if user_input.startswith('!'):
            self._shell_command(user_input[1:])
            return
        
        # Understand the input (no box needed - it's fast)
        plan = self.brain.understand(user_input)
        
        # Update status if modern CLI
        if hasattr(self.cli, 'update_status'):
            self.cli.update_status("Executing...")
        
        # Execute
        success, result = self.brain.execute(plan)
        
        # Clear the processing box
        if hasattr(self.cli, 'finish_processing'):
            self.cli.finish_processing()
        
        # Track stats
        self.stats['actions'] += 1
        if plan.intent == Intent.OPEN_FILE:
            self.stats['files'] += 1
        elif plan.intent == Intent.OPEN_URL:
            self.stats['urls'] += 1
        elif plan.intent == Intent.SEARCH_WEB:
            self.stats['searches'] += 1
        elif plan.intent in [Intent.SCRAPE, Intent.SCRAPE_HTML]:
            self.stats['scrapes'] += 1
        
        # Show result (skip if streamed)
        if result and result != "__STREAMED__":
            if success:
                # For ModernCLI, just add to content (will show on next prompt)
                if hasattr(self.cli, 'add_content'):
                    if any(result.startswith(c) for c in ['✅', '✓', '📊', '●', '✗']):
                        self.cli.add_content(result, "step")
                    else:
                        self.cli.add_content(result, "reply")
                else:
                    # Legacy CLI
                    if any(result.startswith(c) for c in ['✅', '✓', '📊', '●', '✗']):
                        self.cli.console.print(f"\n{result}")
                    else:
                        self.cli.assistant(result)
            else:
                if hasattr(self.cli, 'add_content'):
                    self.cli.add_content(f"✗ {result}", "error")
                else:
                    self.cli.error(result)
        
        # Store for history
        history_result = result if result != "__STREAMED__" else "(streamed)"
        self.history.append({'role': 'assistant', 'content': history_result, 'ts': datetime.now().isoformat()})
        
        if history_result and history_result != "(streamed)":
            self.brain.add_message('assistant', history_result[:500])
    
    def _slash_command(self, cmd: str):
        """Handle /commands"""
        parts = cmd[1:].split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        cmds = {
            'help': self._help, 'h': self._help, '?': self._help,
            'quit': self._quit, 'exit': self._quit, 'q': self._quit,
            'clear': self._clear, 'c': self._clear,
            'status': self._status, 's': self._status,
            'models': self._models, 'm': self._models, 'model': self._models,
            'precision': lambda: self._precision(args),
            'browsing': lambda: self._browsing(args),
            'scrape': lambda: self._scrape(args),
            'search': lambda: self._search(args),
            'tools': self._tools,
            'undo': lambda: self._undo(args),
            'checkpoints': self._checkpoints, 'cp': self._checkpoints,
        }
        
        handler = cmds.get(command)
        if handler:
            handler()
        else:
            self.cli.warn(f"Unknown: {command}")
    
    def _help(self):
        """Show help"""
        self.cli.help_box()
    
    def _quit(self):
        self._save()
        self.running = False
        self.cli.muted("Goodbye")
    
    def _clear(self):
        self.history = []
        self.brain.ctx = type(self.brain.ctx)()
        self.cli.success("Cleared")
    
    def _status(self):
        duration = datetime.now() - self.session_start
        minutes = int(duration.total_seconds() / 60)
        
        precision = "ON" if self.brain.precision_mode else "OFF"
        browsing = "ON" if self.brain.browsing_enabled else "OFF"
        
        self.cli.console.print(f"""
[accent bold]Status[/]
  Precision: {precision}
  Browsing: {browsing}
  Messages: {len(self.history)}
  Duration: {minutes}min
  Prompts: {self.stats['prompts']}
  Searches: {self.stats['searches']}
""")
    
    def _models(self):
        plan = Plan(intent=Intent.LIST_MODELS)
        _, result = self.brain.execute(plan)
        print(result)
    
    def _precision(self, args: str):
        if args.lower() in ['on', '1', 'true']:
            self.brain.precision_mode = True
            self.cli.success("Precision ON")
        elif args.lower() in ['off', '0', 'false']:
            self.brain.precision_mode = False
            self.cli.success("Precision OFF")
        else:
            self.cli.info(f"Precision: {'ON' if self.brain.precision_mode else 'OFF'}")
    
    def _browsing(self, args: str):
        if args.lower() in ['on', '1', 'true']:
            self.brain.browsing_enabled = True
            self.cli.success("Browsing ON")
        elif args.lower() in ['off', '0', 'false']:
            self.brain.browsing_enabled = False
            self.cli.success("Browsing OFF")
        else:
            self.cli.info(f"Browsing: {'ON' if self.brain.browsing_enabled else 'OFF'}")
    
    def _scrape(self, args: str):
        if not args:
            self.cli.error("Usage: /scrape <url>")
            return
        
        with self.cli.spinner("Scraping"):
            plan = Plan(intent=Intent.SCRAPE, target=args.strip())
            success, result = self.brain.execute(plan)
        
        if success:
            print(result)
        else:
            self.cli.error(result)
    
    def _search(self, args: str):
        if not args:
            self.cli.error("Usage: /search <query>")
            return
        
        plan = Plan(intent=Intent.SEARCH_WEB, target=args)
        success, result = self.brain.execute(plan)
        
        if success:
            print(result)
        else:
            self.cli.error(result)
    
    def _tools(self):
        """List tools"""
        self.cli.console.print("\n[accent bold]Tools[/]")
        tools = [("web_search", True), ("scrape", True), ("file_ops", True), ("shell", True)]
        for name, enabled in tools:
            status = "[success]ON[/]" if enabled else "[error]OFF[/]"
            self.cli.console.print(f"  {status} {name}")
    
    def _undo(self, args: str):
        """Undo checkpoints"""
        from core.checkpoints import get_checkpoint_manager
        
        cp_mgr = get_checkpoint_manager()
        
        if not cp_mgr.has_checkpoints():
            self.cli.warn("No checkpoints")
            return
        
        count = int(args) if args and args.isdigit() else 1
        results = cp_mgr.undo(count)
        
        for name, success, msg in results:
            if success:
                self.cli.success(f"Undone: {name}")
            else:
                self.cli.error(f"Failed: {name}")
    
    def _checkpoints(self):
        """List checkpoints"""
        from core.checkpoints import get_checkpoint_manager
        
        cp_mgr = get_checkpoint_manager()
        checkpoints = cp_mgr.list_checkpoints(limit=10)
        
        if not checkpoints:
            self.cli.info("No checkpoints")
            return
        
        self.cli.console.print("\n[accent bold]Checkpoints[/]")
        for cp in checkpoints:
            time_str = cp['timestamp'].split('T')[1][:5] if 'T' in cp['timestamp'] else ""
            self.cli.console.print(f"  [dim]{cp['id'][:8]}[/] {cp['name']} [{time_str}]")
    
    def _file_include(self, path: str):
        """Include file contents with @"""
        path = os.path.expanduser(path.strip())
        
        if not os.path.exists(path):
            self.cli.error(f"Not found: {path}")
            return
        
        try:
            with open(path, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            preview = '\n'.join(lines[:15])
            if len(lines) > 15:
                preview += f"\n... ({len(lines) - 15} more lines)"
            
            self.cli.console.print(f"\n[dim]─ {path}[/]")
            self.cli.console.print(preview)
            
            self.brain.ctx.last_path = path
            
        except Exception as e:
            self.cli.error(str(e))
    
    def _shell_command(self, cmd: str):
        """Run shell command with !"""
        import subprocess
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                self.cli.console.print(f"[warning]{result.stderr}[/]")
            
            if result.returncode != 0:
                self.cli.warn(f"Exit: {result.returncode}")
                
        except subprocess.TimeoutExpired:
            self.cli.error("Timeout")
        except Exception as e:
            self.cli.error(str(e))
    
    def _save(self):
        state_file = get_data_dir() / "session_state.json"
        
        context_data = {
            'last_path': self.brain.ctx.last_path,
            'last_result': self.brain.ctx.last_result[:500] if self.brain.ctx.last_result else "",
            'last_intent': self.brain.ctx.last_intent.value if self.brain.ctx.last_intent else None,
            'created_files': getattr(self.brain.ctx, 'created_files', []),
        }
        
        state = {
            'history': self.history[-50:],
            'stats': self.stats,
            'precision_mode': self.brain.precision_mode,
            'browsing_enabled': self.brain.browsing_enabled,
            'context': context_data,
            'saved_at': datetime.now().isoformat()
        }
        
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _restore(self):
        state_file = get_data_dir() / "session_state.json"
        
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                
                self.history = state.get('history', [])
                self.brain.precision_mode = state.get('precision_mode', False)
                self.brain.browsing_enabled = state.get('browsing_enabled', True)
                
                ctx = state.get('context', {})
                if ctx:
                    self.brain.ctx.last_path = ctx.get('last_path', '')
                    self.brain.ctx.last_result = ctx.get('last_result', '')
                    if ctx.get('last_intent'):
                        try:
                            self.brain.ctx.last_intent = Intent(ctx['last_intent'])
                        except:
                            pass
                    self.brain.ctx.created_files = ctx.get('created_files', [])
                
                if self.history:
                    self.cli.muted(f"Restored ({len(self.history)} messages)")
                    
            except Exception:
                pass


def main():
    session = SessionLoop()
    session.run()


if __name__ == "__main__":
    main()
