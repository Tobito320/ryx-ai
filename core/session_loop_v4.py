"""
Ryx AI - Session Loop V4: Copilot-Style Interactive Session

Features:
- True conversational flow with context
- Quick y/n responses (instant, no LLM)
- Slash commands for power users
- Multi-language (German/English)
- NEVER says "Could you be more specific?"
- Precision mode for learning tasks
"""

import os
import sys
import json
import readline
import signal
from datetime import datetime
from typing import Optional

from core.paths import get_data_dir
from core.ryx_brain_v4 import RyxBrainV4, get_brain_v4, Plan, Intent
from core.ollama_client import OllamaClient
from core.model_router import ModelRouter


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
        print(f"{Color.DIM}ℹ️ {msg}{Color.RESET}")
    
    @staticmethod
    def assistant(msg: str):
        print(f"\n{Color.PURPLE}Ryx:{Color.RESET} {msg}")
    
    @staticmethod
    def prompt() -> str:
        try:
            return input(f"\n{Color.CYAN}>{Color.RESET} ")
        except EOFError:
            return "/quit"


class SessionLoopV4:
    """
    Main interactive session - Copilot-style.
    """
    
    def __init__(self, safety_mode: str = "normal"):
        self.safety_mode = safety_mode
        self.router = ModelRouter()
        self.ollama = OllamaClient(base_url=self.router.get_ollama_url())
        self.brain = get_brain_v4(self.ollama)
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
        history_file = get_data_dir() / "history" / "session_v4"
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
        self._restore()
        
        while self.running:
            try:
                user_input = self.ui.prompt()
                
                if not user_input.strip():
                    continue
                
                self._process(user_input.strip())
                
            except KeyboardInterrupt:
                print()
                self.ui.warning("Session unterbrochen")
                self._save()
                break
            except Exception as e:
                self.ui.error(f"Fehler: {e}")
    
    def _show_banner(self):
        mode = "PRECISION" if self.brain.precision_mode else "normal"
        model = self.brain.models.get("default", self.brain.precision_mode)
        browsing = "ON" if self.brain.browsing_enabled else "OFF"
        
        print(f"""
{Color.PURPLE}╭────────────────────────────────────────────────────────────╮
│ 🟣 ryx v4 – Local AI Agent                                  │
│                                                            │
│ Mode: {mode:<12} Model: {model:<22}│
│ Browsing: {browsing:<8}                                        │
╰────────────────────────────────────────────────────────────╯{Color.RESET}

{Color.DIM}Natürlich sprechen. /help für Befehle.{Color.RESET}
""")
    
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
        
        # Let brain understand and act
        plan = self.brain.understand(user_input)
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
        }
        
        handler = cmds.get(command)
        if handler:
            handler()
        else:
            self.ui.warning(f"Unbekannter Befehl: {command}")
    
    def _help(self):
        print(f"""
{Color.PURPLE}╭─────────────────────────────────────────────────────────────╮
│ 🟣 Ryx v4 - Befehle                                          │
╰─────────────────────────────────────────────────────────────╯{Color.RESET}

{Color.CYAN}SLASH-BEFEHLE:{Color.RESET}
  /help, /hilfe       Diese Hilfe
  /quit, /beenden     Session beenden
  /clear, /neu        Kontext löschen
  /status             Statistiken
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
  youtube                         Website öffnen
  hyprland config                 Config in Editor öffnen
  hyprlock config new terminal    Config in neuem Terminal
  where is .zshrc                 Pfad anzeigen
  find great wave                 Datei suchen
  scrape arch wiki                Webseite scrapen
  set zen as default browser      Einstellung speichern
  use gpt 20b as default          Modell wechseln
  mach mir einen lernzettel       Dokument erstellen

{Color.CYAN}SCHNELLE ANTWORTEN:{Color.RESET}
  y/n/ja/nein         Bestätigung
  1, 2, 3...          Aus Liste wählen
  "open it"           Letztes Ergebnis öffnen
""")
    
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
        state_file = get_data_dir() / "session_state_v4.json"
        
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
        state_file = get_data_dir() / "session_state_v4.json"
        
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
    session = SessionLoopV4()
    session.run()


if __name__ == "__main__":
    main()
