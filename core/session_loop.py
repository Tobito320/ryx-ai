"""
Ryx AI - Session Loop: Interactive Session

Features:
- True conversational flow with context
- Quick y/n responses (instant, no LLM)
- Slash commands for power users
- Multi-language (German/English)
- NEVER says "Could you be more specific?"
- Precision mode for learning tasks
- Modern Claude CLI-style UI with Rich
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

# Use new CLI UI
try:
    from core.cli_ui import get_ui, get_cli, CLI
except ImportError:
    from core.rich_ui import get_ui, RyxUI as CLI
    get_cli = get_ui


class SessionUI:
    """Simplified UI wrapper"""
    
    def __init__(self):
        self.cli = get_cli()
    
    @staticmethod
    def success(msg: str):
        get_cli().success(msg)
    
    @staticmethod
    def error(msg: str):
        get_cli().error(msg)
    
    @staticmethod
    def warning(msg: str):
        get_cli().warn(msg)
    
    @staticmethod
    def info(msg: str):
        get_cli().info(msg)
    
    @staticmethod
    def assistant(msg: str):
        get_cli().assistant(msg)
    
    @staticmethod
    def prompt() -> str:
        return get_cli().prompt()


class SessionLoop:
    """
    Main interactive session with Claude CLI-style UI.
    """
    
    def __init__(self, safety_mode: str = "normal"):
        self.safety_mode = safety_mode
        self.cli = get_cli()
        self.router = ModelRouter()
        self.ollama = OllamaClient(base_url=self.router.get_ollama_url())
        self.brain = get_brain(self.ollama)
        self.ui = SessionUI()
        
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
        
        # Token stats for status bar
        self.last_tok_s = 0.0
        
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
            self.cli.warning("Session unterbrochen (Ctrl+C)")
            self._save()
            self.cli.info("Session gespeichert. 'ryx' zum Fortsetzen.")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, handler)
    
    def run(self):
        """Main loop with Claude CLI-style UI"""
        self._show_banner()
        self._health_check()
        self._restore()
        
        # Show hint on first run
        self.cli.muted("Type naturally. @ for files. /help for commands.")
        
        while self.running:
            try:
                # Get current model based on precision mode
                if self.brain.precision_mode:
                    current_model = "deepseek-r1:14b"
                else:
                    from core.model_router import select_model
                    current_model = select_model("chat").name
                
                # Footer before prompt
                self.cli.footer(
                    model=current_model,
                    msgs=len(self.history),
                    precision=self.brain.precision_mode
                )
                user_input = self.ui.prompt()
                
                if not user_input.strip():
                    continue
                
                self._process(user_input.strip())
                
            except KeyboardInterrupt:
                print()
                self.cli.warn("Session interrupted")
                self._save()
                break
            except Exception as e:
                self.cli.err(f"Error: {e}")
    
    def _health_check(self):
        """Check system health on startup"""
        health = self.brain.health_check()
        
        if not health["ollama"]:
            self.ui.error("Ollama not reachable. Start with: systemctl start ollama")
            return
        
        if not health["models"]:
            self.ui.warning("No models installed. Run: ollama pull qwen2.5:3b")
            return
        
        if health["errors"]:
            for err in health["errors"]:
                self.ui.warning(err)
    
    def _show_banner(self):
        """Show modern status bar instead of banner box"""
        from core.model_router import select_model
        import subprocess
        
        model_config = select_model("hi")
        model = model_config.name
        
        # Get git branch if in repo
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
        
        # Show header like Claude CLI
        self.cli.header(
            model=model,
            branch=branch,
            cwd=os.getcwd()
        )
    
    def _process(self, user_input: str):
        """Process user input"""
        self.stats['prompts'] += 1
        self.history.append({'role': 'user', 'content': user_input, 'ts': datetime.now().isoformat()})
        
        # Add to brain's context for follow-up handling
        self.brain.add_message('user', user_input)
        
        # Slash commands
        if user_input.startswith('/'):
            self._slash_command(user_input)
            return
        
        # Special syntax
        if user_input.startswith('@'):
            self._file_include(user_input[1:])
            return
        
        if user_input.startswith('!'):
            self._shell_command(user_input[1:])
            return
        
        # Show thinking spinner - NO verbose intent output
        self.cli.thinking("Thinking")
        
        # Let brain understand
        plan = self.brain.understand(user_input)
        
        # Stop spinner - don't show intent (too noisy)
        self.cli.thinking_done()
        
        # Execute
        success, result = self.brain.execute(plan)
        
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
        
        # Show result (skip if already streamed)
        if result and result != "__STREAMED__":
            if success:
                if result.startswith('✅') or result.startswith('✓') or result.startswith('📊'):
                    self.cli.console.print(f"\n{result}")
                else:
                    self.ui.assistant(result)
            else:
                self.cli.err(result)
        
        # Store actual result for history (not the marker)
        history_result = result if result != "__STREAMED__" else "(streamed response)"
        self.history.append({'role': 'assistant', 'content': history_result, 'ts': datetime.now().isoformat()})
        
        # Also add to brain's context for follow-ups
        if history_result and history_result != "(streamed response)":
            self.brain.add_message('assistant', history_result[:500])
    
    def _slash_command(self, cmd: str):
        """Handle slash commands"""
        parts = cmd[1:].split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        cmds = {
            'help': self._help, 'h': self._help, '?': self._help, 'hilfe': self._help,
            'quit': self._quit, 'exit': self._quit, 'q': self._quit, 'beenden': self._quit,
            'clear': self._clear, 'c': self._clear, 'neu': self._clear,
            'status': self._status, 's': self._status, 'u': self._status,
            'models': self._models, 'm': self._models, 'modelle': self._models,
            'precision': lambda: self._precision(args), 'präzision': lambda: self._precision(args),
            'browsing': lambda: self._browsing(args),
            'scrape': lambda: self._scrape(args),
            'search': lambda: self._search(args), 'suche': lambda: self._search(args),
            'learn': self._learn, 'lerne': self._learn, 'digest': self._learn,
            'smarter': self._smarter, 'verbessern': self._smarter,
            'export': self._export,
            'restart': lambda: self._restart(args), 'neustart': lambda: self._restart(args),
            # New UI commands
            'tools': self._tools,
            'tool': lambda: self._tool(args),
            'theme': lambda: self._theme(args), 'themes': self._themes,
            # Agent system
            'agents': lambda: self._agents(args),
            # Checkpoint commands (undo/rollback)
            'undo': lambda: self._undo(args), 'rückgängig': lambda: self._undo(args),
            'rollback': lambda: self._rollback(args),
            'checkpoints': self._checkpoints, 'cp': self._checkpoints,
        }
        
        handler = cmds.get(command)
        if handler:
            handler()
        else:
            self.ui.warning(f"Unbekannter Befehl: {command}")
    
    def _help(self):
        """Show help with Rich UI"""
        help_text = """[accent bold]COMMANDS:[/]
  /help            Show this help
  /quit            Exit session
  /clear           Clear context
  /status          Show statistics
  /models          Available models
  /precision on/off  Precision mode (larger models)
  /browsing on/off   Web browsing toggle
  /agents on/off   Agent system (supervisor/operator)

[accent bold]UNDO/ROLLBACK:[/]
  /undo [N]        Undo last N changes
  /rollback <id>   Rollback to checkpoint
  /checkpoints     List checkpoints

[accent bold]TOOLS:[/]
  /tools           List available tools
  /tool <name> on/off  Toggle tool
  /theme <name>    Change theme
  /themes          List themes

[accent bold]SCRAPING:[/]
  /scrape <url>    Scrape webpage
  /search <query>  Web search
  /learn           Learn from scraped content

[accent bold]SPECIAL:[/]
  @file            Include file contents
  !command         Run shell command
  y/n              Quick confirmation"""
        
        from rich.panel import Panel
        self.cli.console.print(Panel(help_text, title="🟣 Ryx - Help", border_style="border"))
    
    def _quit(self):
        self._save()
        self.running = False
        self.ui.info("Auf Wiedersehen!")
    
    def _clear(self):
        self.history = []
        self.brain.ctx = type(self.brain.ctx)()
        self.ui.success("Kontext gelöscht")
    
    def _status(self):
        duration = datetime.now() - self.session_start
        minutes = int(duration.total_seconds() / 60)
        
        precision = "[green]ON[/]" if self.brain.precision_mode else "[red]OFF[/]"
        browsing = "[green]ON[/]" if self.brain.browsing_enabled else "[red]OFF[/]"
        
        self.cli.console.print(f"""
[accent bold]=== Ryx Status ===[/]
  Precision Mode: {precision}
  Browsing: {browsing}
  Context: [cyan]{len(self.history)}[/] messages
  Duration: [cyan]{minutes}[/] minutes

[ryx.info bold]Statistics:[/]
  Prompts: {self.stats['prompts']}
  Actions: {self.stats['actions']}
  Files: {self.stats['files']}
  URLs: {self.stats['urls']}
  Searches: {self.stats['searches']}
  Scrapes: {self.stats['scrapes']}
""")
    
    def _models(self):
        plan = Plan(intent=Intent.LIST_MODELS)
        _, result = self.brain.execute(plan)
        print(result)
    
    def _precision(self, args: str):
        if args.lower() in ['on', 'ein', '1', 'true']:
            self.brain.precision_mode = True
            self.ui.success("Präzisionsmodus EIN - nutzt größere Modelle")
        elif args.lower() in ['off', 'aus', '0', 'false']:
            self.brain.precision_mode = False
            self.ui.success("Präzisionsmodus AUS")
        else:
            current = "EIN" if self.brain.precision_mode else "AUS"
            self.ui.info(f"Präzisionsmodus: {current}")
    
    def _browsing(self, args: str):
        if args.lower() in ['on', 'ein', '1', 'true']:
            self.brain.browsing_enabled = True
            self.ui.success("Browsing aktiviert")
        elif args.lower() in ['off', 'aus', '0', 'false']:
            self.brain.browsing_enabled = False
            self.ui.success("Browsing deaktiviert")
        else:
            current = "EIN" if self.brain.browsing_enabled else "AUS"
            self.ui.info(f"Browsing: {current}")
    
    def _scrape(self, args: str):
        if not args:
            self.ui.error("Nutzung: /scrape <url>")
            return
        
        self.ui.info("Scraping...")
        plan = Plan(intent=Intent.SCRAPE, target=args.strip())
        success, result = self.brain.execute(plan)
        
        if success:
            print(result)
        else:
            self.ui.error(result)
    
    def _search(self, args: str):
        if not args:
            self.ui.error("Nutzung: /search <query>")
            return
        
        plan = Plan(intent=Intent.SEARCH_WEB, target=args)
        success, result = self.brain.execute(plan)
        
        if success:
            print(result)
        else:
            self.ui.error(result)
    
    def _learn(self):
        if not self.brain.ctx.last_scraped:
            scrape_dir = get_data_dir() / "scrape"
            if scrape_dir.exists():
                json_files = list(scrape_dir.glob("*.json"))
                if json_files:
                    latest = max(json_files, key=lambda p: p.stat().st_mtime)
                    with open(latest) as f:
                        self.brain.ctx.last_scraped = json.load(f)
        
        if not self.brain.ctx.last_scraped:
            self.ui.error("Kein Scrape-Inhalt vorhanden. Nutze erst /scrape <url>")
            return
        
        content = self.brain.ctx.last_scraped
        title = content.get('title', content.get('domain', 'Unbekannt'))
        text = content.get('text', '')[:5000]
        
        self.ui.info(f"Lerne aus: {title}")
        
        model = self.brain.models.get("precision", True)
        
        response = self.brain.ollama.generate(
            prompt=f"Fasse diesen Inhalt in klaren Stichpunkten zusammen:\n\n{text}",
            model=model,
            system="Extrahiere die wichtigsten Fakten. Kurz und präzise.",
            max_tokens=1000
        )
        
        if response.error:
            self.ui.error(f"Fehler: {response.error}")
            return
        
        scrape_dir = get_data_dir() / "scrape"
        safe_name = "".join(c if c.isalnum() or c in ' -_' else '_' for c in title[:50])
        summary_file = scrape_dir / f"{safe_name}_summary.md"
        
        with open(summary_file, 'w') as f:
            f.write(f"# {title}\n\n")
            f.write(f"Quelle: {content.get('url', 'Unbekannt')}\n")
            f.write(f"Gelernt: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n")
            f.write(response.response)
        
        self.ui.success(f"Gelernt und gespeichert: {summary_file}")
        print(f"\n{response.response}")
        
        # Add to RAG
        self.ui.info("Füge zur Wissensbasis hinzu...")
        try:
            from core.rag_system import get_rag_system
            rag = get_rag_system()
            rag.add_document(
                content=response.response,
                metadata={"source": content.get('url', 'scrape'), "title": title, "type": "learned"}
            )
            self.ui.success("Zur RAG-Wissensbasis hinzugefügt")
        except Exception as e:
            self.ui.warning(f"RAG nicht verfügbar: {e}")
    
    def _smarter(self):
        self.ui.info("Selbstverbesserung läuft...")
        result = self.brain.get_smarter()
        print(result)
    
    def _export(self):
        export_dir = get_data_dir() / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_file = export_dir / f"session_{timestamp}.md"
        
        with open(export_file, 'w') as f:
            f.write(f"# Ryx Session\n\nDatum: {datetime.now()}\n\n")
            for msg in self.history:
                role = msg.get('role', 'unknown').title()
                f.write(f"**{role}**: {msg.get('content', '')}\n\n")
        
        self.ui.success(f"Exportiert: {export_file}")
    
    def _restart(self, args: str):
        if 'all' in args.lower() or not args:
            plan = Plan(
                intent=Intent.RESTART,
                target="all",
                requires_confirmation=True,
                question="Alle Ryx-Dienste neustarten? (y/n)"
            )
            _, result = self.brain.execute(plan)
            print(result)
        else:
            self.ui.info("Nutzung: /restart all")
    
    def _tools(self):
        """List all available tools with their status"""
        self.cli.console.print("\n[accent bold]Available Tools:[/]")
        
        tools = [
            ("web_search", "Search the web", True),
            ("scrape", "Scrape webpages", True),
            ("file_ops", "File operations", True),
            ("shell", "Shell commands", True),
            ("code_edit", "Code editing", True),
        ]
        
        for name, desc, enabled in tools:
            status = "[green]ON[/]" if enabled else "[red]OFF[/]"
            self.cli.console.print(f"  {status} {name}: [dim]{desc}[/]")
    
    def _tool(self, args: str):
        """Toggle a tool on/off"""
        parts = args.split()
        if len(parts) < 2:
            self.ui.error("Usage: /tool <name> on|off")
            self._tools()
            return
        
        name = parts[0].lower()
        state = parts[1].lower()
        
        if state in ['on', 'ein', '1', 'true']:
            enabled = True
        elif state in ['off', 'aus', '0', 'false']:
            enabled = False
        else:
            self.ui.error("State must be: on or off")
            return
        
        # TODO: Actually toggle tool state
        status = "enabled" if enabled else "disabled"
        self.ui.success(f"Tool '{name}' {status}")
    
    def _themes(self):
        """List available themes"""
        themes = ['dracula', 'nord', 'catppuccin']
        current = 'nord'  # TODO: Get from config
        
        self.cli.console.print("\n[accent bold]Available Themes:[/]")
        for t in themes:
            marker = " (current)" if t == current else ""
            self.cli.console.print(f"  [step]{t}[/]{marker}")
        self.cli.console.print("\n[dim]Switch: /theme <name>[/]")
    
    def _theme(self, args: str):
        """Switch theme"""
        if not args:
            self._themes()
            return
        
        name = args.strip().lower()
        valid_themes = ['dracula', 'nord', 'catppuccin']
        
        if name in valid_themes:
            # TODO: Actually switch theme
            self.ui.success(f"Theme switched to: {name}")
        else:
            self.ui.error(f"Unknown theme: {name}")
            self._themes()
    
    def _agents(self, args: str):
        """Toggle new agent system"""
        if not args:
            status = "ON" if self.brain.use_new_agents else "OFF"
            self.ui.info(f"Agent system: {status}")
            self.ui.info("Usage: /agents on|off")
            return
        
        state = args.strip().lower()
        if state in ['on', 'ein', '1', 'true']:
            self.brain.enable_new_agents(True)
            self.ui.success("Agent system enabled (supervisor/operator)")
        elif state in ['off', 'aus', '0', 'false']:
            self.brain.enable_new_agents(False)
            self.ui.success("Agent system disabled (classic mode)")
        else:
            self.ui.error("Usage: /agents on|off")
    
    def _undo(self, args: str):
        """Undo last N checkpoints"""
        from core.checkpoints import get_checkpoint_manager
        
        cp_mgr = get_checkpoint_manager()
        
        if not cp_mgr.has_checkpoints():
            self.ui.warning("No checkpoints to undo")
            return
        
        count = 1
        if args and args.isdigit():
            count = int(args)
        
        results = cp_mgr.undo(count)
        
        for name, success, msg in results:
            if success:
                self.ui.success(f"Undone: {name}")
                self.cli.substep(msg)
            else:
                self.ui.error(f"Failed: {name} - {msg}")
    
    def _rollback(self, args: str):
        """Rollback to a specific checkpoint"""
        from core.checkpoints import get_checkpoint_manager
        
        cp_mgr = get_checkpoint_manager()
        
        if not args:
            # Show checkpoints to choose from
            self._checkpoints()
            self.ui.info("Usage: /rollback <checkpoint_id>")
            return
        
        success, msg, changes = cp_mgr.rollback(args.strip())
        
        if success:
            self.ui.success(msg)
            self.cli.substep(f"{changes} changes reverted")
        else:
            self.ui.error(msg)
    
    def _checkpoints(self):
        """List recent checkpoints"""
        from core.checkpoints import get_checkpoint_manager
        
        cp_mgr = get_checkpoint_manager()
        checkpoints = cp_mgr.list_checkpoints(limit=10)
        
        if not checkpoints:
            self.ui.info("No checkpoints yet. Checkpoints are created when Ryx modifies files.")
            return
        
        self.cli.console.print("\n[accent bold]Recent Checkpoints:[/]")
        
        for cp in checkpoints:
            # Format: ID | Name | Changes | Time
            time_str = cp['timestamp'].split('T')[1][:5] if 'T' in cp['timestamp'] else cp['timestamp']
            files_preview = ", ".join(os.path.basename(f) for f in cp['files'][:2])
            if len(cp['files']) > 2:
                files_preview += f" +{len(cp['files']) - 2}"
            
            self.cli.console.print(
                f"  [dim]{cp['id'][:12]}[/] │ [step]{cp['name']}[/] │ "
                f"[dim]{cp['changes']} changes[/] │ [dim]{time_str}[/]"
            )
            if files_preview:
                self.cli.console.print(f"    └─ [dim]{files_preview}[/]")
        
        self.cli.console.print("\n[dim]Undo: /undo  |  Rollback: /rollback <id>[/]")
    
    def _file_include(self, path: str):
        path = os.path.expanduser(path.strip())
        
        if not os.path.exists(path):
            self.ui.error(f"Datei nicht gefunden: {path}")
            return
        
        try:
            with open(path, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            preview = '\n'.join(lines[:20])
            if len(lines) > 20:
                preview += f"\n... ({len(lines) - 20} more lines)"
            
            self.cli.console.print(f"\n[dim]--- {path} ---[/]")
            self.cli.console.print(preview)
            self.cli.console.print("[dim]--- End ---[/]")
            
            self.brain.ctx.last_path = path
            
        except Exception as e:
            self.ui.error(f"Error reading: {e}")
    
    def _shell_command(self, cmd: str):
        import subprocess
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                self.cli.console.print(f"[yellow]{result.stderr}[/]")
            
            if result.returncode != 0:
                self.ui.warning(f"Exit code: {result.returncode}")
                
        except subprocess.TimeoutExpired:
            self.ui.error("Timeout")
        except Exception as e:
            self.ui.error(f"Fehler: {e}")
    
    def _save(self):
        state_file = get_data_dir() / "session_state.json"
        
        # Include context for continuity
        context_data = {
            'last_path': self.brain.ctx.last_path,
            'last_result': self.brain.ctx.last_result[:500] if self.brain.ctx.last_result else "",
            'last_intent': self.brain.ctx.last_intent.value if self.brain.ctx.last_intent else None,
            'created_files': getattr(self.brain.ctx, 'created_files', []),
            'last_task_files': getattr(self.brain.ctx, 'last_task_files', []),
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
                
                # Restore context
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
                    self.brain.ctx.last_task_files = ctx.get('last_task_files', [])
                
                if self.history:
                    self.ui.info(f"Session wiederhergestellt ({len(self.history)} Nachrichten)")
                    
            except Exception:
                pass


def main():
    session = SessionLoop()
    session.run()


if __name__ == "__main__":
    main()
