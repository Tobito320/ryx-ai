"""
Ryx AI - Session Loop
Main interactive session for the Ryx AI CLI

This is the main entry point - uses ryx_brain_v2 for intelligent processing.
"""

import sys
import signal
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

# Use the v2 brain for full AI understanding
from core.ryx_brain_v2 import get_brain_v2, RyxBrainV2, ActionType, Action
from core.model_router import ModelRouter, ModelTier
from core.ollama_client import OllamaClient
from core.ui import RyxUI, Color
from core.paths import get_project_root, get_data_dir

try:
    from core.memory import get_memory, RyxMemory
except ImportError:
    get_memory = None
    RyxMemory = None


class SessionLoop:
    """
    Main interactive session loop for Ryx AI

    Features:
    - Intelligent AI-based understanding (no hardcoded patterns)
    - Knowledge-backed responses (no hallucination)
    - Clarification when ambiguous
    - Action-biased (does things, doesn't explain)
    - Conversational context and follow-ups
    - Multi-language support (German/English)
    """

    def __init__(self, safety_mode: str = "normal"):
        self.ui = RyxUI()
        self.router = ModelRouter()
        self.ollama = OllamaClient(base_url=self.router.get_ollama_url())
        
        # Use the v2 brain for full AI understanding
        self.brain = get_brain_v2(self.ollama)
        
        # Memory system (optional)
        self.memory = get_memory() if get_memory else None

        # Session state
        self.running = True
        self.current_tier: Optional[ModelTier] = None
        self.conversation_history: List[Dict[str, str]] = []
        self.context: Dict[str, Any] = {}
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

        # Session file for persistence
        self.session_file = get_data_dir() / "session_state.json"

        # Install signal handlers
        signal.signal(signal.SIGINT, self._handle_interrupt)

        # Try to restore previous session
        self._restore_session()

    def _handle_interrupt(self, signum, frame):
        """Handle Ctrl+C gracefully"""
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
                'context': self.context
            }
            with open(self.session_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            pass  # Silent fail

    def _restore_session(self):
        """Restore previous session if exists"""
        try:
            if self.session_file.exists():
                with open(self.session_file) as f:
                    state = json.load(f)
                self.conversation_history = state.get('conversation_history', [])
                tier_name = state.get('current_tier')
                if tier_name:
                    self.current_tier = ModelTier(tier_name)
                self.context = state.get('context', {})
        except:
            pass

    def run(self):
        """Main session loop"""
        # Show header with precision mode indicator
        mode_str = "PRECISION" if self.brain.precision_mode else "balanced"
        self.ui.header(
            tier=mode_str,
            repo=str(get_project_root()),
            safety=self.safety_mode
        )
        self.ui.info("Type naturally. Use /help for commands, @ for files, ! for shell.")
        
        if self.conversation_history:
            self.ui.info(f"Resumed session with {len(self.conversation_history)} messages")

        while self.running:
            try:
                # Custom prompt based on brain state
                custom_prompt = None
                if self.brain.state.awaiting_confirmation:
                    custom_prompt = "[y/n]"
                elif self.brain.state.pending_items:
                    custom_prompt = "[#]"
                
                user_input = self.ui.prompt(custom_prompt=custom_prompt)
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
        """Process user input using the brain"""
        user_input = user_input.strip()
        
        # Handle slash commands
        if user_input.startswith('/'):
            self._handle_slash_command(user_input)
            return
        
        # Handle @ file references
        if user_input.startswith('@'):
            self._handle_file_reference(user_input)
            return
        
        # Handle ! shell commands
        if user_input.startswith('!'):
            self._handle_shell_command(user_input[1:])
            return
        
        # Handle greetings instantly
        if self._is_greeting(user_input.lower()):
            self._handle_greeting(user_input.lower())
            return
        
        # Handle "get smarter" / "improve yourself" commands
        if any(x in user_input.lower() for x in ['get smart', 'improve', 'learn more', 'fix your', 'update knowledge']):
            self._handle_self_improvement()
            return
        
        # Use the brain to understand and act
        action = self.brain.understand(user_input)
        
        # Save to history
        self.conversation_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })
        
        # Handle the action
        self._handle_action(action, user_input)

    def _handle_file_reference(self, ref: str):
        """Handle @file references"""
        import os
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

    def _handle_action(self, action: Action, original_input: str):
        """Handle an action from the brain"""
        
        # Clarification needed
        if action.type == ActionType.CLARIFY:
            self.ui.assistant_message(action.question or "Was genau meinst du?")
            return
        
        # Just an answer - still need to execute to store context
        if action.type == ActionType.ANSWER:
            response = action.target or ""
            if response:
                self.ui.assistant_message(response)
                # Store result for follow-ups (e.g., "open it" after "where is X")
                self.brain.state.last_result = response
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response,
                    "timestamp": datetime.now().isoformat()
                })
            return
        
        # Execute the action
        success, result = self.brain.execute(action)
        
        # Update stats
        self.stats["actions"] += 1
        if action.type == ActionType.OPEN_FILE:
            self.stats["files_opened"] += 1
        elif action.type == ActionType.OPEN_URL:
            self.stats["urls_opened"] += 1
        elif action.type == ActionType.SEARCH_WEB:
            self.stats["searches"] += 1
        elif action.type in [ActionType.SCRAPE_URL, ActionType.SCRAPE_HTML_CSS]:
            self.stats["scrapes"] += 1
        
        if success:
            if action.type == ActionType.OPEN_FILE:
                self.ui.success(f"Geöffnet: {result}")
            elif action.type == ActionType.OPEN_URL:
                self.ui.success("Im Browser geöffnet")
            elif action.type == ActionType.FIND_FILE:
                if "Mehrere" in str(result) or "Welche" in str(result):
                    self.ui.assistant_message(result)
                elif result:
                    print(f"\n{Color.CYAN}{result}{Color.RESET}\n")
                else:
                    self.ui.info("Keine Dateien gefunden")
            elif action.type == ActionType.GET_DATE:
                self.ui.assistant_message(result)
            elif action.type in [ActionType.SET_PREFERENCE, ActionType.SWITCH_MODEL, ActionType.TOGGLE_MODE]:
                self.ui.success(result)
            elif action.type == ActionType.SEARCH_WEB:
                self.ui.assistant_message(result)
            elif action.type in [ActionType.SCRAPE_URL, ActionType.SCRAPE_HTML_CSS]:
                self.ui.success(result)
            else:
                if result:
                    self.ui.assistant_message(result)
                else:
                    self.ui.success("Erledigt")
        else:
            self.ui.error(result)
            
            # Offer contextual help
            if "nicht gefunden" in result.lower() and action.type == ActionType.OPEN_FILE:
                self.ui.assistant_message("Soll ich danach suchen? (y/n)")
                self.brain.state.awaiting_confirmation = True
                self.brain.state.pending_question = "Soll ich danach suchen? (y/n)"
                self.brain.state.last_action = Action(
                    type=ActionType.FIND_FILE,
                    target=action.target
                )
            elif "searxng" in result.lower():
                self.ui.assistant_message("SearXNG starten? (y/n)")
                self.brain.state.awaiting_confirmation = True
                self.brain.state.pending_question = "SearXNG starten? (y/n)"
                self.brain.state.last_action = Action(
                    type=ActionType.START_SERVICE,
                    target="searxng"
                )
        
        # Save to history
        self.conversation_history.append({
            "role": "assistant", 
            "content": result if result else "Erledigt",
            "action": action.type.value,
            "timestamp": datetime.now().isoformat()
        })

    def _handle_slash_command(self, cmd: str):
        """Handle slash commands"""
        parts = cmd[1:].split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if command in ['help', 'h', '?', 'hilfe']:
            self._cmd_help()
        elif command in ['quit', 'exit', 'q', 'beenden']:
            self.running = False
        elif command in ['clear', 'c', 'neu']:
            self.conversation_history = []
            self.context = {}
            self.brain.state = type(self.brain.state)()  # Reset state
            self.ui.success("Kontext gelöscht")
        elif command in ['tier', 't', 'modell']:
            self._set_tier(args)
        elif command in ['models', 'm', 'modelle']:
            models = self.router.list_models()
            self.ui.models_list(models)
        elif command in ['status', 's', 'usage', 'u']:
            self._show_status()
        elif command in ['smarter', 'verbessern']:
            self._handle_self_improvement()
        elif command == 'scrape':
            self._cmd_scrape(args)
        elif command in ['learn', 'lerne']:
            self._cmd_learn(args)
        elif command in ['search', 'suche']:
            self._cmd_search(args)
        elif command == 'export':
            self._cmd_export()
        elif command in ['precision', 'präzision', 'genau']:
            self._cmd_precision_mode(args)
        elif command in ['restart', 'neustart']:
            self._cmd_restart(args)
        else:
            self.ui.warning(f"Unbekannter Befehl: {command}")
    
    def _cmd_help(self):
        """Show comprehensive help"""
        help_text = """
╭─────────────────────────────────────────────────────────────╮
│ 🟣 Ryx v2 - Befehle                                          │
╰─────────────────────────────────────────────────────────────╯

SLASH-BEFEHLE (nur in Session):
  /help, /hilfe       Diese Hilfe
  /quit, /beenden     Session beenden
  /clear, /neu        Kontext löschen
  /status, /usage     Statistiken
  /models, /modelle   Verfügbare Modelle
  /precision on/off   Präzisionsmodus (größere Modelle)
  /scrape <url>       Webseite scrapen
  /search <query>     Web-Suche via SearXNG
  /learn              Aus letztem Scrape lernen
  /smarter            Selbstverbesserung
  /restart all        Alle Ryx-Dienste neustarten
  /export             Session exportieren

SPEZIAL-SYNTAX:
  @pfad/zur/datei     Datei-Inhalt anzeigen
  !befehl             Shell-Befehl ausführen

NATÜRLICHE BEFEHLE (Beispiele):
  open youtube                    Website öffnen
  hyprland config new terminal    Config in neuem Terminal
  where is .zshrc                 Datei-Pfad finden
  scrape arch wiki                Webseite scrapen
  search for python tutorials     Web-Suche
  set zen as default browser      Einstellung speichern
  mach mir einen lernzettel       Dokument erstellen

INTERAKTION:
  y/n                 Schnelle Bestätigung
  1, 2, 3...         Aus Liste auswählen
  "open it"           Letzte Datei/URL öffnen
  "the first one"     Ersten Eintrag wählen
"""
        print(help_text)
    
    def _cmd_precision_mode(self, args: str):
        """Toggle precision mode"""
        if args.lower() in ['on', 'ein', 'true', '1']:
            self.brain.toggle_precision_mode(True)
            self.ui.success("Präzisionsmodus EIN - nutzt größere Modelle")
        elif args.lower() in ['off', 'aus', 'false', '0']:
            self.brain.toggle_precision_mode(False)
            self.ui.success("Präzisionsmodus AUS")
        else:
            current = "EIN" if self.brain.precision_mode else "AUS"
            self.ui.info(f"Präzisionsmodus: {current}. Nutze /precision on oder /precision off")
    
    def _cmd_restart(self, args: str):
        """Restart services"""
        if 'all' in args.lower() or 'alles' in args.lower():
            action = Action(
                type=ActionType.RESTART_SERVICE,
                target="ryx",
                requires_confirmation=True,
                question="Alle Ryx-Dienste neustarten? (y/n)"
            )
            success, result = self.brain.execute(action)
            self.ui.assistant_message(result)
        else:
            self.ui.info("Nutzung: /restart all")

    def _cmd_scrape(self, args: str):
        """Scrape a URL"""
        if not args:
            self.ui.error("Nutzung: /scrape <url oder name>")
            return
        
        self.ui.info("Scraping...")
        action = Action(type=ActionType.SCRAPE_URL, target=args.strip())
        success, result = self.brain.execute(action)
        
        if success:
            self.ui.success(result)
        else:
            self.ui.error(f"Scrape fehlgeschlagen: {result}")

    def _cmd_learn(self, args: str):
        """Learn from scraped content"""
        if not self.brain.state.last_scraped_content:
            scrape_dir = get_data_dir() / "scrape"
            if not scrape_dir.exists() or not list(scrape_dir.glob("*.json")):
                self.ui.error("Kein Scrape-Inhalt. Nutze erst /scrape <url>")
                return
            
            # Load latest scrape
            latest = max(scrape_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
            with open(latest) as f:
                data = json.load(f)
            self.brain.state.last_scraped_content = data
        
        content = self.brain.state.last_scraped_content
        self.ui.info(f"Lerne aus: {content.get('title', content.get('domain', 'Unbekannt'))}")
        
        try:
            response = self.ollama.generate(
                prompt=f"Fasse diesen Inhalt in 3-5 Stichpunkten zusammen:\n\n{content.get('text', '')[:3000]}",
                model=self.brain.models['balanced'],
                system="Sei präzise. Extrahiere die wichtigsten Fakten.",
                max_tokens=500
            )
            
            if response.response:
                scrape_dir = get_data_dir() / "scrape"
                title = content.get('title', content.get('domain', 'unknown'))
                safe_name = "".join(c if c.isalnum() or c in ' -_' else '_' for c in title[:50])
                summary_file = scrape_dir / f"{safe_name}_summary.md"
                
                with open(summary_file, 'w') as f:
                    f.write(f"# {title}\n\n{response.response}")
                
                self.ui.success(f"Gelernt und gespeichert: {summary_file}")
                print(response.response)
        except Exception as e:
            self.ui.error(f"Lernen fehlgeschlagen: {e}")

    def _cmd_search(self, args: str):
        """Web search"""
        if not args:
            self.ui.error("Nutzung: /search <suchanfrage>")
            return
        
        action = Action(type=ActionType.SEARCH_WEB, target=args)
        success, result = self.brain.execute(action)
        
        if success:
            self.ui.assistant_message(result)
        else:
            self.ui.error(result)

    def _cmd_export(self):
        """Export session"""
        export_dir = get_data_dir() / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_file = export_dir / f"session_{timestamp}.md"
        
        with open(export_file, 'w') as f:
            f.write(f"# Ryx Session\n\nDatum: {datetime.now()}\n\n")
            for msg in self.conversation_history:
                role = msg.get('role', 'unbekannt').title()
                f.write(f"**{role}**: {msg.get('content', '')}\n\n")
        
        self.ui.success(f"Exportiert: {export_file}")

    def _set_tier(self, tier_name: str):
        """Set the model tier"""
        if not tier_name:
            self.ui.info("Verfügbar: fast, balanced, powerful, ultra")
            return
        
        tier = self.router.get_tier_by_name(tier_name)
        if tier:
            self.current_tier = tier
            model = self.router.get_model(tier)
            self.ui.success(f"Gewechselt zu {tier.value} ({model.name})")
        else:
            self.ui.error(f"Unbekannte Stufe: {tier_name}")

    def _show_status(self):
        """Show current status with stats"""
        duration = datetime.now() - self.session_start
        minutes = int(duration.total_seconds() / 60)
        
        precision = "EIN" if self.brain.precision_mode else "AUS"
        
        print(f"""
{Color.PURPLE}=== Ryx Status ==={Color.RESET}
  Modus: {'PRECISION' if self.brain.precision_mode else 'Normal'}
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

    def _is_greeting(self, text: str) -> bool:
        """Check if input is a simple greeting"""
        greetings = {'hi', 'hello', 'hey', 'yo', 'sup', 'hallo', 'moin', 'servus', 
                    'howdy', 'greetings', 'whatsup', 'whats up', 'guten tag'}
        clean = text.rstrip('!.,?').replace("'", "").replace(" ", "").lower()
        return clean in greetings

    def _handle_greeting(self, text: str):
        """Handle greetings without AI"""
        responses = {
            'hi': 'Hi! Was kann ich tun?',
            'hello': 'Hallo! Wie kann ich helfen?',
            'hey': 'Hey! Bereit.',
            'yo': 'Yo! Was gibts?',
            'sup': "Was geht!",
            'hallo': 'Hallo! Was brauchst du?',
            'moin': 'Moin! Was steht an?',
            'servus': 'Servus! Wie kann ich helfen?',
        }
        clean = text.rstrip('!.,?').replace("'", "").replace(" ", "").lower()
        response = responses.get(clean, "Hallo! Bereit.")
        self.ui.assistant_message(response)

    def _handle_self_improvement(self):
        """Run self-improvement"""
        self.ui.info("Selbstverbesserung läuft...")
        result = self.brain.get_smarter()
        print(result)

