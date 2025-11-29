"""
Ryx AI - Session Loop
Main interactive session for the CLI

This is a thin wrapper around RyxAgent, handling only terminal I/O.
The core logic is in RyxAgent, making it easy to add other frontends
(TUI, speech, web) in the future.
"""

import sys
import signal
import json
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

from core.ui import RyxUI, get_ui
from core.ryx_agent import RyxAgent, AgentState, AgentResponse
from core.paths import get_project_root, get_data_dir


class SessionLoop:
    """
    Terminal interface for RyxAgent
    
    This is intentionally thin - just handles terminal I/O.
    All intelligence is in RyxAgent.
    
    Future frontends (TUI popup, speech, web) can call RyxAgent directly.
    """
    
    def __init__(self):
        """Initialize session"""
        self.ui = get_ui()
        self.agent = RyxAgent()
        
        # Wire up agent callbacks for UI
        self.agent.on_state_change = self._on_state_change
        self.agent.on_progress = self._on_progress
        
        self.running = True
        self.session_file = Path.home() / ".ryx" / "session_state.json"
        
        # Install signal handler
        signal.signal(signal.SIGINT, self._handle_interrupt)
        
        # Try to restore previous session
        self._restore_session()
    
    def _on_state_change(self, state: AgentState, message: str):
        """Handle agent state changes"""
        state_icons = {
            AgentState.THINKING: "💭",
            AgentState.PLANNING: "📋",
            AgentState.EXECUTING: "⚡",
            AgentState.SEARCHING: "🔍",
            AgentState.EDITING: "🛠️",
            AgentState.DONE: "✅",
            AgentState.ERROR: "❌"
        }
        
        if state != AgentState.IDLE and message:
            icon = state_icons.get(state, "•")
            print(f"\r{self.ui.colors.DIM}{icon} {message}{self.ui.colors.RESET}    ")
    
    def _on_progress(self, message: str):
        """Handle progress updates from agent"""
        print(f"{self.ui.colors.DIM}{message}{self.ui.colors.RESET}")
    
    def _handle_interrupt(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print("\n")
        self.ui.print_warning("Session interrupted (Ctrl+C)")
        self._save_session()
        
        if self.agent.conversation_history:
            self.ui.print_status(f"Saved {len(self.agent.conversation_history)} messages")
        
        print(f"\n{self.ui.colors.DIM}Resume with: ryx{self.ui.colors.RESET}")
        print("Goodbye! 👋")
        sys.exit(0)
    
    def _save_session(self):
        """Save session state"""
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        
        state = {
            'saved_at': datetime.now().isoformat(),
            'conversation_history': self.agent.conversation_history[-50:],
            'current_tier': self.agent.current_tier
        }
        
        with open(self.session_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _restore_session(self):
        """Restore previous session if exists"""
        if not self.session_file.exists():
            return
        
        try:
            with open(self.session_file, 'r') as f:
                state = json.load(f)
            
            self.agent.conversation_history = state.get('conversation_history', [])
            tier = state.get('current_tier', 'balanced')
            self.agent.set_tier(tier)
            
            if self.agent.conversation_history:
                self.ui.print_status(
                    f"Restored {len(self.agent.conversation_history)} messages from previous session",
                    color=self.ui.colors.DIM
                )
        except Exception:
            pass
    
    def run(self):
        """Main session loop"""
        # Get current model info
        model = self._get_current_model()
        repo = self._get_current_repo()
        
        # Show header
        self.ui.print_header(
            model=model,
            tier=self.agent.current_tier,
            repo=repo,
            safety="normal"
        )
        
        while self.running:
            try:
                # Get user input
                self.ui.print_prompt()
                prompt = input().strip()
                
                if not prompt:
                    continue
                
                # Handle slash commands
                if prompt.startswith('/'):
                    self._handle_slash_command(prompt)
                    continue
                
                # Process through agent
                self.ui.print_thinking()
                response = self.agent.process(prompt)
                self.ui.clear_thinking()
                
                # Display response
                self.ui.print_response_header()
                print(self.ui.format_response(response.content))
                
            except KeyboardInterrupt:
                print(f"\n\n{self.ui.colors.YELLOW}Use /quit to exit{self.ui.colors.RESET}")
                continue
            except EOFError:
                print("\nGoodbye!")
                break
            except Exception as e:
                self.ui.print_error(f"Error: {str(e)}")
    
    def _handle_slash_command(self, command: str):
        """Handle slash commands"""
        parts = command.split()
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        if cmd in ['/quit', '/exit', '/q']:
            self.ui.print_success("Goodbye! 👋")
            self._save_session()
            self.running = False
        
        elif cmd == '/help':
            self.ui.print_help()
        
        elif cmd == '/status':
            self._show_status()
        
        elif cmd == '/tier':
            if args:
                self._switch_tier(args[0])
            else:
                self._show_tiers()
        
        elif cmd == '/experience':
            self._show_experience()
        
        elif cmd == '/clear':
            self.agent.clear_history()
            self.ui.print_success("Conversation cleared")
        
        elif cmd == '/save':
            filename = args[0] if args else f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            self._save_conversation(filename)
        
        elif cmd == '/models':
            self._show_models()
        
        else:
            self.ui.print_error(f"Unknown command: {cmd}")
            print(f"  {self.ui.colors.DIM}Type /help for available commands{self.ui.colors.RESET}")
    
    def _switch_tier(self, tier: str):
        """Switch model tier"""
        tier = tier.lower()
        
        if self.agent.set_tier(tier):
            model = self._get_current_model()
            self.ui.print_success(f"Switched to {tier} tier ({model})")
            
            if tier == 'uncensored':
                self.ui.print_uncensored_warning()
        else:
            self.ui.print_error(f"Unknown tier: {tier}")
            self._show_tiers()
    
    def _show_tiers(self):
        """Show available tiers"""
        print(f"\n{self.ui.colors.BOLD}Available tiers:{self.ui.colors.RESET}")
        
        tiers = {
            'fast': ('mistral:7b', 'Quick responses'),
            'balanced': ('qwen2.5-coder:14b', 'Default coding'),
            'powerful': ('deepseek-coder-v2:16b', 'Complex tasks'),
            'ultra': ('Qwen3-Coder:30B', 'Heavy reasoning'),
            'uncensored': ('gpt-oss:20b', 'Personal chat')
        }
        
        for name, (model, desc) in tiers.items():
            current = " (current)" if name == self.agent.current_tier else ""
            print(f"  {self.ui.colors.CYAN}{name}{self.ui.colors.RESET}: {model} - {desc}{current}")
        
        print(f"\n{self.ui.colors.DIM}Switch with: /tier <name>{self.ui.colors.RESET}")
    
    def _show_status(self):
        """Show session status"""
        status = self.agent.get_status()
        
        print(f"\n{self.ui.icons.SUCCESS} {self.ui.colors.BOLD}Session Status{self.ui.colors.RESET}")
        print(f"  Messages: {status['conversation_length']}")
        print(f"  Current tier: {status['current_tier']}")
        print(f"  Agent state: {status['state']}")
        
        # Show model availability
        router_status = status.get('router_status', {})
        print(f"\n{self.ui.colors.BOLD}Model Status:{self.ui.colors.RESET}")
        for tier_name, tier_info in router_status.get('tiers', {}).items():
            available = tier_info.get('available', False)
            icon = self.ui.icons.DONE if available else self.ui.icons.ERROR
            print(f"  {icon} {tier_name}: {tier_info.get('model', 'unknown')}")
        
        # Show experience stats
        exp_stats = status.get('experience_stats', {})
        print(f"\n{self.ui.colors.BOLD}Experience Cache:{self.ui.colors.RESET}")
        print(f"  Total experiences: {exp_stats.get('total_experiences', 0)}")
        print(f"  Successful: {exp_stats.get('successful', 0)}")
        
        print()
    
    def _show_experience(self):
        """Show experience cache statistics"""
        stats = self.agent.experience.get_stats()
        
        print(f"\n{self.ui.colors.BOLD}🧠 Experience Cache{self.ui.colors.RESET}")
        print(f"  Total experiences: {stats['total_experiences']}")
        print(f"  Successful: {stats['successful']}")
        
        if stats.get('by_intent'):
            print(f"\n{self.ui.colors.BOLD}By Intent Type:{self.ui.colors.RESET}")
            for intent, count in stats['by_intent'].items():
                print(f"  • {intent}: {count}")
        
        print(f"\n{self.ui.colors.DIM}The more I learn, the better I get at helping you.{self.ui.colors.RESET}")
        print()
    
    def _show_models(self):
        """Show available models"""
        status = self.agent.get_status()
        self.ui.print_model_status(status.get('router_status', {}))
    
    def _save_conversation(self, filename: str):
        """Save conversation to file"""
        output_dir = get_data_dir() / "history"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename
        
        with open(output_path, 'w') as f:
            f.write(f"# Ryx AI Conversation (Tobi's Technical Partner)\n")
            f.write(f"# Saved: {datetime.now().isoformat()}\n\n")
            
            for msg in self.agent.conversation_history:
                role = "Tobi" if msg["role"] == "user" else "Ryx"
                content = msg["content"]
                f.write(f"## {role}\n\n{content}\n\n")
        
        self.ui.print_success(f"Saved to: {output_path}")
    
    def _get_current_model(self) -> str:
        """Get current model name"""
        try:
            status = self.agent.get_status()
            router = status.get('router_status', {})
            tier = self.agent.current_tier
            tier_info = router.get('tiers', {}).get(tier, {})
            return tier_info.get('model', 'unknown')
        except:
            return "unknown"
    
    def _get_current_repo(self) -> str:
        """Get current repo path"""
        import os
        cwd = os.getcwd()
        home = str(Path.home())
        if cwd.startswith(home):
            return "~" + cwd[len(home):]
        return cwd


def main():
    """Entry point for session mode"""
    session = SessionLoop()
    session.run()


if __name__ == "__main__":
    main()
