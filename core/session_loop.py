"""
Ryx AI - Session Loop: Interactive Session

Features:
- True conversational flow with context
- Quick y/n responses (instant, no LLM)
- Slash commands for power users
- Multi-language (German/English)
- NEVER says "Could you be more specific?"
- Precision mode for learning tasks
- Modern themed UI
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
from core.printer import get_printer, RyxPrinter, StepStatus
from core.progress import Spinner


class Color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


class SessionUI:
    """Legacy UI wrapper - delegates to new printer"""
    
    def __init__(self):
        self.printer = get_printer()
    
    @staticmethod
    def success(msg: str):
        get_printer().success(msg)
    
    @staticmethod
    def error(msg: str):
        get_printer().error(msg)
    
    @staticmethod
    def warning(msg: str):
        get_printer().warning(msg)
    
    @staticmethod
    def info(msg: str):
        get_printer().info(msg)
    
    @staticmethod
    def assistant(msg: str):
        get_printer().assistant(msg)
    
    @staticmethod
    def prompt() -> str:
        return get_printer().prompt()


class SessionLoop:
    """
    Main interactive session with modern UI.
    """
    
    def __init__(self, safety_mode: str = "normal"):
        self.safety_mode = safety_mode
        self.printer = get_printer()
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
            self.ui.warning("Session unterbrochen (Ctrl+C)")
            self._save()
            self.ui.info("Session gespeichert. 'ryx' zum Fortsetzen.")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, handler)
    
    def run(self):
        """Main loop"""
        self._show_banner()
        self._health_check()
        self._restore()
        
        while self.running:
            try:
                user_input = self.ui.prompt()
                
                if not user_input.strip():
                    continue
                
                self._process(user_input.strip())
                
            except KeyboardInterrupt:
                print()
                self.ui.warning("Session interrupted")
                self._save()
                break
            except Exception as e:
                self.ui.error(f"Error: {e}")
    
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
        mode = "PRECISION" if self.brain.precision_mode else "normal"
        # Use new router to get the default model
        from core.model_router import select_model
        model_config = select_model("hi")  # Get default chat model
        model = model_config.name
        browsing = self.brain.browsing_enabled
        
        self.printer.print_banner(mode=mode, model=model, browsing=browsing)
    
    def _process(self, user_input: str):
        """Process user input"""
        self.stats['prompts'] += 1
        self.history.append({'role': 'user', 'content': user_input, 'ts': datetime.now().isoformat()})
        
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
        
        # Show thinking indicator
        self.printer.thinking("Understanding request...")
        
        # Let brain understand
        plan = self.brain.understand(user_input)
        
        # Show what we understood
        intent_name = plan.intent.value.replace('_', ' ')
        if plan.target:
            self.printer.step(f"Intent: {intent_name}", f"→ {plan.target[:50]}")
        else:
            self.printer.step(f"Intent: {intent_name}")
        
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
        
        # Show result
        if result:
            if success:
                if result.startswith('✅') or result.startswith('📊'):
                    print(f"\n{result}")
                else:
                    self.ui.assistant(result)
            else:
                self.ui.error(result)
        
        self.history.append({'role': 'assistant', 'content': result, 'ts': datetime.now().isoformat()})
    
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
        }
        
        handler = cmds.get(command)
        if handler:
            handler()
        else:
            self.ui.warning(f"Unbekannter Befehl: {command}")
    
    def _help(self):
        t = self.printer.theme
        self.printer.print_box("""COMMANDS:
  /help            Show this help
  /quit            Exit session
  /clear           Clear context
  /status          Show statistics
  /models          Available models
  /precision on/off  Precision mode (larger models)
  /browsing on/off   Web browsing toggle
  /agents on/off   New agent system (supervisor/operator)

TOOLS:
  /tools           List available tools
  /tool <name> on/off  Toggle tool
  /theme <name>    Change theme
  /themes          List themes

SCRAPING:
  /scrape <url>    Scrape webpage
  /search <query>  Web search
  /learn           Learn from scraped content

SPECIAL:
  @file            Include file contents
  !command         Run shell command
  y/n              Quick confirmation""", title="🟣 Ryx - Help")
    
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
        
        precision = "EIN" if self.brain.precision_mode else "AUS"
        browsing = "EIN" if self.brain.browsing_enabled else "AUS"
        
        print(f"""
{Color.PURPLE}=== Ryx Status ==={Color.RESET}
  Precision Mode: {precision}
  Browsing: {browsing}
  Kontext: {len(self.history)} Nachrichten
  Dauer: {minutes} Minuten

{Color.CYAN}Statistiken:{Color.RESET}
  Prompts: {self.stats['prompts']}
  Aktionen: {self.stats['actions']}
  Dateien: {self.stats['files']}
  URLs: {self.stats['urls']}
  Suchen: {self.stats['searches']}
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
        self.printer.print_tools()
    
    def _tool(self, args: str):
        """Toggle a tool on/off"""
        parts = args.split()
        if len(parts) < 2:
            self.ui.error("Usage: /tool <name> on|off")
            self.printer.print_tools()
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
        
        if self.printer.set_tool_state(name, enabled):
            status = "enabled" if enabled else "disabled"
            self.ui.success(f"Tool '{name}' {status}")
        else:
            self.ui.error(f"Unknown tool: {name}")
            self.printer.print_tools()
    
    def _themes(self):
        """List available themes"""
        self.printer.print_themes()
    
    def _theme(self, args: str):
        """Switch theme"""
        if not args:
            self.printer.print_themes()
            return
        
        name = args.strip().lower()
        if self.printer.set_theme(name):
            self.ui.success(f"Theme switched to: {name}")
        else:
            self.ui.error(f"Unknown theme: {name}")
            self.printer.print_themes()
    
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
                preview += f"\n... ({len(lines) - 20} weitere Zeilen)"
            
            print(f"\n{Color.DIM}--- {path} ---{Color.RESET}")
            print(preview)
            print(f"{Color.DIM}--- Ende ---{Color.RESET}")
            
            self.brain.ctx.last_path = path
            
        except Exception as e:
            self.ui.error(f"Fehler beim Lesen: {e}")
    
    def _shell_command(self, cmd: str):
        import subprocess
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(f"{Color.YELLOW}{result.stderr}{Color.RESET}")
            
            if result.returncode != 0:
                self.ui.warning(f"Exit code: {result.returncode}")
                
        except subprocess.TimeoutExpired:
            self.ui.error("Timeout")
        except Exception as e:
            self.ui.error(f"Fehler: {e}")
    
    def _save(self):
        state_file = get_data_dir() / "session_state.json"
        
        state = {
            'history': self.history[-50:],
            'stats': self.stats,
            'precision_mode': self.brain.precision_mode,
            'browsing_enabled': self.brain.browsing_enabled,
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
                
                if self.history:
                    self.ui.info(f"Session wiederhergestellt ({len(self.history)} Nachrichten)")
                    
            except Exception:
                pass


def main():
    session = SessionLoop()
    session.run()


if __name__ == "__main__":
    main()
