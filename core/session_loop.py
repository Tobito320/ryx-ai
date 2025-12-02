"""
Ryx AI - Session Loop
Main interactive session for the Ryx AI CLI
"""

import sys
import signal
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from core.intelligent_agent import get_agent, IntelligentAgent, ActionType, Action
from core.model_router import ModelRouter, ModelTier
from core.ollama_client import OllamaClient
from core.ui import RyxUI, Color, Emoji
from core.paths import get_project_root, get_data_dir
from core.memory import get_memory, RyxMemory


class SessionLoop:
    """
    Main interactive session loop for Ryx AI

    Features:
    - Intelligent AI-based understanding (no hardcoded patterns)
    - Knowledge-backed responses (no hallucination)
    - Clarification when ambiguous
    - Action-biased (does things, doesn't explain)
    """

    def __init__(self, safety_mode: str = "normal"):
        self.ui = RyxUI()
        self.router = ModelRouter()
        self.ollama = OllamaClient(base_url=self.router.get_ollama_url())
        
        # Intelligent agent - the brain
        self.agent = get_agent(self.ollama)
        
        # Memory system
        self.memory = get_memory()

        # Session state
        self.running = True
        self.current_tier: Optional[ModelTier] = None
        self.conversation_history: List[Dict[str, str]] = []
        self.context: Dict[str, Any] = {}
        self.safety_mode = safety_mode
        self.awaiting_confirmation: Optional[Action] = None

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
        self.ui.header(
            tier=self.current_tier.value if self.current_tier else "balanced",
            repo=str(get_project_root()),
            safety=self.safety_mode
        )
        self.ui.info("Type naturally. Ask me to do things.")

        while self.running:
            try:
                user_input = self.ui.prompt()
                if not user_input:
                    continue
                self._process_input(user_input)
            except KeyboardInterrupt:
                print()
                continue
            except EOFError:
                break

        self._save_session()
        self.ui.info("Goodbye!")

    def _process_input(self, user_input: str):
        """Process user input using intelligent agent"""
        user_lower = user_input.lower().strip()
        
        # Handle pending confirmation
        if self.awaiting_confirmation:
            self._handle_confirmation(user_input)
            return
        
        # Handle slash commands
        if user_input.startswith('/'):
            self._handle_slash_command(user_input)
            return
        
        # Handle simple responses
        if user_lower in ['y', 'yes', 'n', 'no', 'ok', 'okay']:
            # No pending confirmation, treat as chat
            self.ui.assistant_message("What would you like me to do?")
            return
        
        # Handle greetings instantly
        if self._is_greeting(user_lower):
            self._handle_greeting(user_lower)
            return
        
        # Handle "get smarter" / "improve yourself" commands
        if any(x in user_lower for x in ['get smart', 'improve', 'learn more', 'fix your', 'update knowledge']):
            self._handle_self_improvement()
            return
        
        # Use intelligent agent to understand and act
        self.ui.thinking()
        action = self.agent.understand(user_input)
        self.ui.clear_thinking()
        
        # Handle the action
        self._handle_action(action, user_input)

    def _handle_action(self, action: Action, original_input: str):
        """Handle an action from the intelligent agent"""
        
        # Clarification needed
        if action.type == ActionType.CLARIFY:
            self.ui.assistant_message(action.question or "Could you be more specific?")
            return
        
        # Just an answer
        if action.type == ActionType.ANSWER:
            self.ui.assistant_message(action.target or "I'm not sure how to help.")
            return
        
        # Action that needs confirmation for dangerous operations
        if action.type == ActionType.RUN_COMMAND:
            self.ui.assistant_message(f"Run: {action.target}? (y/n)")
            self.awaiting_confirmation = action
            return
        
        # Execute the action
        success, result = self.agent.execute(action)
        
        if success:
            if action.type == ActionType.OPEN_FILE:
                self.ui.success(f"Opened: {action.target}")
            elif action.type == ActionType.OPEN_URL:
                self.ui.success(f"Opened in browser")
            elif action.type == ActionType.FIND_FILE:
                if result:
                    # Just print the paths, no extra text
                    print(f"\n{Color.CYAN}{result}{Color.RESET}\n")
                else:
                    self.ui.info("No files found")
            else:
                self.ui.assistant_message(result)
        else:
            self.ui.error(result)
            
            # If file not found, offer to search
            if "not found" in result.lower() and action.type == ActionType.OPEN_FILE:
                self.ui.assistant_message("Want me to search for it? (y/n)")
                self.awaiting_confirmation = Action(
                    type=ActionType.FIND_FILE,
                    target=action.target
                )

    def _handle_confirmation(self, response: str):
        """Handle yes/no confirmation"""
        response_lower = response.lower().strip()
        action = self.awaiting_confirmation
        self.awaiting_confirmation = None
        
        if response_lower in ['y', 'yes', 'ok', 'okay', 'sure', 'do it']:
            success, result = self.agent.execute(action)
            if success:
                if result:
                    print(f"\n{Color.CYAN}{result}{Color.RESET}\n")
                else:
                    self.ui.success("Done")
            else:
                self.ui.error(result)
        else:
            self.ui.info("Cancelled")

    def _handle_slash_command(self, cmd: str):
        """Handle slash commands"""
        parts = cmd[1:].split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if command in ['help', 'h', '?']:
            self.ui.help()
        elif command in ['quit', 'exit', 'q']:
            self.running = False
        elif command in ['clear', 'c']:
            self.conversation_history = []
            self.context = {}
            self.ui.success("Context cleared")
        elif command in ['tier', 't']:
            self._set_tier(args)
        elif command in ['models', 'm']:
            models = self.router.list_models()
            self.ui.models_list(models)
        elif command in ['status', 's']:
            self._show_status()
        elif command == 'smarter':
            self._handle_self_improvement()
        else:
            self.ui.warning(f"Unknown command: {command}")

    def _set_tier(self, tier_name: str):
        """Set the model tier"""
        if not tier_name:
            self.ui.info("Available: fast, balanced, powerful, ultra")
            return
        
        tier = self.router.get_tier_by_name(tier_name)
        if tier:
            self.current_tier = tier
            model = self.router.get_model(tier)
            self.ui.success(f"Switched to {tier.value} ({model.name})")
        else:
            self.ui.error(f"Unknown tier: {tier_name}")

    def _show_status(self):
        """Show current status"""
        print(f"\n{Color.PURPLE}=== Ryx Status ==={Color.RESET}")
        print(f"  Tier: {self.current_tier.value if self.current_tier else 'balanced'}")
        print(f"  Context: {len(self.conversation_history)} messages")
        print(f"  Safety: {self.safety_mode}")
        print()

    def _is_greeting(self, text: str) -> bool:
        """Check if input is a simple greeting"""
        greetings = {'hi', 'hello', 'hey', 'yo', 'sup', 'hola', 'hallo', 
                    'howdy', 'greetings', 'whatsup', 'whats up'}
        clean = text.rstrip('!.,?').replace("'", "").replace(" ", "")
        return clean in greetings

    def _handle_greeting(self, text: str):
        """Handle greetings without AI"""
        responses = {
            'hi': 'Hi! What do you need?',
            'hello': 'Hello! How can I help?',
            'hey': 'Hey! Ready.',
            'yo': 'Yo! What can I do?',
            'sup': "What's up!",
            'hola': 'Hola!',
            'hallo': 'Hallo!',
        }
