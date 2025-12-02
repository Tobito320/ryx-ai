"""
Ryx AI - Session Loop V3: Copilot-Style Interactive Session

Features:
- True conversational flow with context
- Quick y/n responses
- Slash commands for power users
- Multi-language (German/English)
- No verbose "Could you be more specific?" messages
"""

import os
import sys
import json
import readline
from datetime import datetime
from typing import Optional, Dict

from core.paths import get_data_dir
from core.ryx_brain_v3 import RyxBrainV3, get_brain_v3, Action, ActionType
from core.ollama_client import OllamaClient
from core.model_router import ModelRouter


class Color:
    """ANSI colors"""
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


class SessionUI:
    """Minimal, clean output"""
    
    @staticmethod
    def success(msg: str):
        print(f"{Color.GREEN}{msg}{Color.RESET}")
    
    @staticmethod
    def error(msg: str):
        print(f"{Color.RED}❌ {msg}{Color.RESET}")
    
    @staticmethod
    def warning(msg: str):
        print(f"{Color.YELLOW}⚠️ {msg}{Color.RESET}")
    
    @staticmethod
    def info(msg: str):
        print(f"{Color.DIM}{msg}{Color.RESET}")
    
    @staticmethod
    def assistant(msg: str):
        print(f"\n{Color.PURPLE}Ryx:{Color.RESET} {msg}")
    
    @staticmethod
    def prompt() -> str:
        try:
            return input(f"\n{Color.CYAN}>{Color.RESET} ")
        except EOFError:
            return "/quit"


class SessionLoopV3:
    """
    Main interactive session.
    Copilot-style: natural language with slash commands.
    """
    
    def __init__(self, safety_mode: str = "normal"):
        self.safety_mode = safety_mode
        self.router = ModelRouter()
        self.ollama = OllamaClient(base_url=self.router.get_ollama_url())
        self.brain = get_brain_v3(self.ollama)
        self.ui = SessionUI()
        
        self.running = True
        self.session_start = datetime.now()
        self.conversation_history = []
        
        # Stats
        self.stats = {
            'prompts': 0,
            'actions': 0,
            'files_opened': 0,
            'urls_opened': 0,
            'searches': 0,
            'scrapes': 0
        }
        
        # Setup history
        self._setup_readline()
    
    def _setup_readline(self):
        """Setup command history"""
        history_file = get_data_dir() / "history" / "session_history"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            readline.read_history_file(history_file)
        except FileNotFoundError:
            pass
        
        readline.set_history_length(1000)
        import atexit
        atexit.register(readline.write_history_file, history_file)
    
    def run(self):
        """Main session loop"""
        self._show_banner()
        self._restore_session()
        
        while self.running:
            try:
                user_input = self.ui.prompt()
                
                if not user_input.strip():
                    continue
                
                self._process_input(user_input.strip())
                
            except KeyboardInterrupt:
                print()
                self.ui.warning("Session unterbrochen (Ctrl+C)")
                self._save_session()
                self.ui.info("Session gespeichert. 'ryx' zum Fortsetzen.")
                break
            except Exception as e:
                self.ui.error(f"Fehler: {e}")
    
    def _show_banner(self):
        """Show startup banner"""
        tier = "precision" if self.brain.precision_mode else "normal"
        model = self.brain.models.get_model("default", self.brain.precision_mode)
        
        print(f"""
{Color.PURPLE}╭────────────────────────────────────────────────────────────╮
│ 🟣 ryx v3 – Local AI Agent                                  │
│                                                            │
│ Mode: {tier:<10} Model: {model:<25}│
│ Browsing: {'ON' if self.brain.browsing_enabled else 'OFF':<8}                                        │
╰────────────────────────────────────────────────────────────╯{Color.RESET}

{Color.DIM}Natürlich sprechen. /help für Befehle.{Color.RESET}
""")
    
    def _process_input(self, user_input: str):
        """Process user input"""
        self.stats['prompts'] += 1
        
        # Add to conversation history
        self.conversation_history.append({
            'role': 'user',
            'content': user_input,
            'timestamp': datetime.now().isoformat()
        })
        
        # Handle slash commands
        if user_input.startswith('/'):
            self._handle_slash_command(user_input)
            return
        
        # Handle special syntax
        if user_input.startswith('@'):
            self._handle_file_include(user_input[1:])
            return
        
        if user_input.startswith('!'):
            self._handle_shell_command(user_input[1:])
            return
        
        # Let brain understand and act
        action = self.brain.understand(user_input)
        success, result = self.brain.execute(action)
        
        # Track stats
        self.stats['actions'] += 1
        if action.type == ActionType.OPEN_FILE:
            self.stats['files_opened'] += 1
        elif action.type == ActionType.OPEN_URL:
            self.stats['urls_opened'] += 1
        elif action.type == ActionType.SEARCH_WEB:
            self.stats['searches'] += 1
        elif action.type in [ActionType.SCRAPE_URL, ActionType.SCRAPE_HTML]:
            self.stats['scrapes'] += 1
        
        # Show result
        if result:
            if success:
                # Don't prefix with "Ryx:" for simple confirmations
                if result.startswith('✅') or result.startswith('📊'):
                    print(f"\n{result}")
                else:
                    self.ui.assistant(result)
            else:
                self.ui.error(result)
        
        # Add to history
        self.conversation_history.append({
            'role': 'assistant',
            'content': result,
            'timestamp': datetime.now().isoformat()
        })
    
    def _handle_slash_command(self, cmd: str):
        """Handle slash commands"""
        parts = cmd[1:].split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        handlers = {
            'help': self._cmd_help,
            'h': self._cmd_help,
            '?': self._cmd_help,
            'hilfe': self._cmd_help,
            
            'quit': self._cmd_quit,
            'exit': self._cmd_quit,
            'q': self._cmd_quit,
            'beenden': self._cmd_quit,
            
            'clear': self._cmd_clear,
            'c': self._cmd_clear,
            'neu': self._cmd_clear,
            
            'status': self._cmd_status,
            's': self._cmd_status,
            'usage': self._cmd_status,
            'u': self._cmd_status,
            
            'models': self._cmd_models,
            'm': self._cmd_models,
            'modelle': self._cmd_models,
            
            'tier': lambda a: self._cmd_tier(a),
            't': lambda a: self._cmd_tier(a),
            
            'precision': lambda a: self._cmd_precision(a),
            'präzision': lambda a: self._cmd_precision(a),
            
            'browsing': lambda a: self._cmd_browsing(a),
            
            'scrape': lambda a: self._cmd_scrape(a),
            'search': lambda a: self._cmd_search(a),
            'suche': lambda a: self._cmd_search(a),
            
            'learn': self._cmd_learn,
            'lerne': self._cmd_learn,
            'digest': self._cmd_learn,
            
            'smarter': self._cmd_smarter,
            'verbessern': self._cmd_smarter,
            
            'export': self._cmd_export,
            
            'restart': lambda a: self._cmd_restart(a),
            'neustart': lambda a: self._cmd_restart(a),
        }
        
        handler = handlers.get(command)
        if handler:
            if callable(handler):
                # Check if handler takes args
                import inspect
                sig = inspect.signature(handler)
                if len(sig.parameters) > 0:
                    handler(args)
                else:
                    handler()
            else:
                handler()
        else:
            self.ui.warning(f"Unbekannter Befehl: {command}")
    
    def _cmd_help(self):
        """Show help"""
        print(f"""
{Color.PURPLE}╭─────────────────────────────────────────────────────────────╮
│ 🟣 Ryx v3 - Befehle                                          │
╰─────────────────────────────────────────────────────────────╯{Color.RESET}

{Color.CYAN}SLASH-BEFEHLE:{Color.RESET}
  /help, /hilfe       Diese Hilfe
  /quit, /beenden     Session beenden
  /clear, /neu        Kontext löschen
  /status, /usage     Statistiken
  /models, /modelle   Verfügbare Modelle
  /precision on/off   Präzisionsmodus (größere Modelle)
  /browsing on/off    Web-Browsing aktivieren/deaktivieren
  /scrape <url>       Webseite scrapen
  /search <query>     Web-Suche
  /learn, /digest     Aus gescraptem Inhalt lernen
  /smarter            Selbstverbesserung
  /restart all        Ryx neustarten
  /export             Session exportieren

{Color.CYAN}SPEZIAL-SYNTAX:{Color.RESET}
  @pfad/zur/datei     Datei-Inhalt einbinden
  !befehl             Shell-Befehl ausführen

{Color.CYAN}NATÜRLICHE BEFEHLE:{Color.RESET}
  open youtube                    Website öffnen
  hyprland config new terminal    Config in neuem Terminal öffnen
  where is .zshrc                 Datei-Pfad finden
  scrape arch wiki                Webseite scrapen
  search for IPv6                 Web-Suche
  set zen as default browser      Einstellung speichern
  use gpt 20b as default          Modell wechseln
  mach mir einen lernzettel       Dokument erstellen

{Color.CYAN}SCHNELLE ANTWORTEN:{Color.RESET}
  y/n                 Bestätigung
  1, 2, 3...         Aus Liste wählen
  "open it"           Letztes Ergebnis öffnen
""")
    
    def _cmd_quit(self):
        """Exit session"""
        self._save_session()
        self.running = False
        self.ui.info("Auf Wiedersehen!")
    
    def _cmd_clear(self):
        """Clear context"""
        self.conversation_history = []
        self.brain.state = type(self.brain.state)()
        self.ui.success("Kontext gelöscht")
    
    def _cmd_status(self):
        """Show status"""
        duration = datetime.now() - self.session_start
        minutes = int(duration.total_seconds() / 60)
        
        precision = "EIN" if self.brain.precision_mode else "AUS"
        browsing = "EIN" if self.brain.browsing_enabled else "AUS"
        
        print(f"""
{Color.PURPLE}=== Ryx Status ==={Color.RESET}
  Precision Mode: {precision}
  Browsing: {browsing}
  Kontext: {len(self.conversation_history)} Nachrichten
  Dauer: {minutes} Minuten

{Color.CYAN}Statistiken:{Color.RESET}
  Prompts: {self.stats['prompts']}
  Aktionen: {self.stats['actions']}
  Dateien: {self.stats['files_opened']}
  URLs: {self.stats['urls_opened']}
  Suchen: {self.stats['searches']}
  Scrapes: {self.stats['scrapes']}
""")
    
    def _cmd_models(self):
        """List models"""
        action = Action(type=ActionType.LIST_MODELS)
        _, result = self.brain.execute(action)
        print(result)
    
    def _cmd_tier(self, args: str):
        """Set model tier"""
        if not args:
            self.ui.info("Nutzung: /tier <fast|balanced|precision>")
            return
        
        args_lower = args.lower()
        if args_lower in ['precision', 'smart', 'präzision']:
            self.brain.toggle_precision_mode(True)
            self.ui.success("Präzisionsmodus aktiviert")
        elif args_lower in ['fast', 'schnell']:
            self.brain.toggle_precision_mode(False)
            self.ui.success("Schnellmodus aktiviert")
        else:
            self.ui.warning(f"Unbekannte Stufe: {args}")
    
    def _cmd_precision(self, args: str):
        """Toggle precision mode"""
        if args.lower() in ['on', 'ein', '1', 'true']:
            self.brain.toggle_precision_mode(True)
            self.ui.success("Präzisionsmodus EIN - nutzt größere Modelle")
        elif args.lower() in ['off', 'aus', '0', 'false']:
            self.brain.toggle_precision_mode(False)
            self.ui.success("Präzisionsmodus AUS")
        else:
            current = "EIN" if self.brain.precision_mode else "AUS"
            self.ui.info(f"Präzisionsmodus: {current}")
    
    def _cmd_browsing(self, args: str):
        """Toggle browsing"""
        if args.lower() in ['on', 'ein', '1', 'true']:
            self.brain.toggle_browsing(True)
            self.ui.success("Browsing aktiviert")
        elif args.lower() in ['off', 'aus', '0', 'false']:
            self.brain.toggle_browsing(False)
            self.ui.success("Browsing deaktiviert")
        else:
            current = "EIN" if self.brain.browsing_enabled else "AUS"
            self.ui.info(f"Browsing: {current}")
    
    def _cmd_scrape(self, args: str):
        """Scrape URL"""
        if not args:
            self.ui.error("Nutzung: /scrape <url>")
            return
        
        self.ui.info("Scraping...")
        action = Action(type=ActionType.SCRAPE_URL, target=args.strip())
        success, result = self.brain.execute(action)
        
        if success:
            print(result)
        else:
            self.ui.error(result)
    
    def _cmd_search(self, args: str):
        """Web search"""
        if not args:
            self.ui.error("Nutzung: /search <query>")
            return
        
        action = Action(type=ActionType.SEARCH_WEB, target=args)
        success, result = self.brain.execute(action)
        
        if success:
            print(result)
        else:
            self.ui.error(result)
    
    def _cmd_learn(self):
        """Learn from scraped content"""
        if not self.brain.state.last_scraped_content:
            # Try to load latest scrape
            scrape_dir = get_data_dir() / "scrape"
            if scrape_dir.exists():
                json_files = list(scrape_dir.glob("*.json"))
                if json_files:
                    latest = max(json_files, key=lambda p: p.stat().st_mtime)
                    with open(latest) as f:
                        self.brain.state.last_scraped_content = json.load(f)
        
        if not self.brain.state.last_scraped_content:
            self.ui.error("Kein Scrape-Inhalt vorhanden. Nutze erst /scrape <url>")
            return
        
        content = self.brain.state.last_scraped_content
        title = content.get('title', content.get('domain', 'Unbekannt'))
        text = content.get('text', '')[:5000]
        
        self.ui.info(f"Lerne aus: {title}")
        
        # Use precision model for learning
        model = self.brain.models.get_model("precision", precision_mode=True)
        
        response = self.brain.ollama.generate(
            prompt=f"Fasse diesen Inhalt in klaren Stichpunkten zusammen:\n\n{text}",
            model=model,
            system="Extrahiere die wichtigsten Fakten. Kurz und präzise.",
            max_tokens=1000
        )
        
        if response.error:
            self.ui.error(f"Fehler: {response.error}")
            return
        
        # Save summary
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
                metadata={
                    "source": content.get('url', 'scrape'),
                    "title": title,
                    "type": "learned"
                }
            )
            self.ui.success("Zur RAG-Wissensbasis hinzugefügt")
        except Exception as e:
            self.ui.warning(f"RAG nicht verfügbar: {e}")
    
    def _cmd_smarter(self):
        """Self-improvement"""
        self.ui.info("Selbstverbesserung läuft...")
        result = self.brain.get_smarter()
        print(result)
    
    def _cmd_export(self):
        """Export session"""
        export_dir = get_data_dir() / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_file = export_dir / f"session_{timestamp}.md"
        
        with open(export_file, 'w') as f:
            f.write(f"# Ryx Session\n\nDatum: {datetime.now()}\n\n")
            for msg in self.conversation_history:
                role = msg.get('role', 'unknown').title()
                f.write(f"**{role}**: {msg.get('content', '')}\n\n")
        
        self.ui.success(f"Exportiert: {export_file}")
    
    def _cmd_restart(self, args: str):
        """Restart services"""
        if 'all' in args.lower() or not args:
            action = Action(
                type=ActionType.RESTART_SERVICE,
                target="all",
                requires_confirmation=True,
                question="Alle Ryx-Dienste neustarten? (y/n)"
            )
            _, result = self.brain.execute(action)
            print(result)
        else:
            self.ui.info("Nutzung: /restart all")
    
    def _handle_file_include(self, path: str):
        """Include file contents"""
        path = os.path.expanduser(path.strip())
        
        if not os.path.exists(path):
            self.ui.error(f"Datei nicht gefunden: {path}")
            return
        
        try:
            with open(path, 'r') as f:
                content = f.read()
            
            # Show preview
            lines = content.split('\n')
            preview = '\n'.join(lines[:20])
            if len(lines) > 20:
                preview += f"\n... ({len(lines) - 20} weitere Zeilen)"
            
            print(f"\n{Color.DIM}--- {path} ---{Color.RESET}")
            print(preview)
            print(f"{Color.DIM}--- Ende ---{Color.RESET}")
            
            # Add to context
            self.brain.state.last_result = path
            
        except Exception as e:
            self.ui.error(f"Fehler beim Lesen: {e}")
    
    def _handle_shell_command(self, cmd: str):
        """Execute shell command"""
        import subprocess
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            
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
    
    def _save_session(self):
        """Save session state"""
        state_file = get_data_dir() / "session_state.json"
        
        state = {
            'history': self.conversation_history[-50:],  # Last 50 messages
            'stats': self.stats,
            'precision_mode': self.brain.precision_mode,
            'browsing_enabled': self.brain.browsing_enabled,
            'saved_at': datetime.now().isoformat()
        }
        
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _restore_session(self):
        """Restore previous session if exists"""
        state_file = get_data_dir() / "session_state.json"
        
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                
                self.conversation_history = state.get('history', [])
                self.brain.precision_mode = state.get('precision_mode', False)
                self.brain.browsing_enabled = state.get('browsing_enabled', True)
                
                if self.conversation_history:
                    self.ui.info(f"Session wiederhergestellt ({len(self.conversation_history)} Nachrichten)")
                    
            except Exception:
                pass


def main():
    """Entry point"""
    session = SessionLoopV3()
    session.run()


if __name__ == "__main__":
    main()
