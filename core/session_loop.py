"""
Ryx AI - Session Loop
Main interactive session for the CLI
"""

import sys
import signal
import json
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

from core.ui import RyxUI, get_ui
from core.model_router_v2 import ModelRouter
from core.intent_classifier import IntentClassifier, IntentType
from core.workflow_orchestrator import WorkflowOrchestrator
from core.tool_registry import get_tool_registry
from core.rag_system import RAGSystem
from core.paths import get_project_root, get_data_dir


class SessionLoop:
    """
    Main interactive session for Ryx CLI
    
    Features:
    - Natural language input
    - Automatic intent detection
    - Model tier selection
    - Workflow execution
    - Session persistence
    - Purple-themed UI
    """
    
    def __init__(self):
        """Initialize session"""
        self.ui = get_ui()
        self.router = ModelRouter()
        self.classifier = IntentClassifier()
        self.orchestrator = WorkflowOrchestrator(self.router)
        self.tools = get_tool_registry()
        self.rag = RAGSystem()
        
        self.running = True
        self.conversation_history: List[Dict] = []
        self.session_file = Path.home() / ".ryx" / "session_state.json"
        self.current_tier = "balanced"
        
        # Install signal handler
        signal.signal(signal.SIGINT, self._handle_interrupt)
        
        # Try to restore previous session
        self._restore_session()
    
    def _handle_interrupt(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print("\n")
        self.ui.print_warning("Session interrupted (Ctrl+C)")
        self._save_session()
        
        if self.conversation_history:
            self.ui.print_status(f"Saved {len(self.conversation_history)} messages")
        
        print(f"\n{self.ui.colors.DIM}Resume with: ryx{self.ui.colors.RESET}")
        print("Goodbye! 👋")
        sys.exit(0)
    
    def _save_session(self):
        """Save session state"""
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        
        state = {
            'saved_at': datetime.now().isoformat(),
            'conversation_history': self.conversation_history[-50:],
            'current_tier': self.current_tier
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
            
            self.conversation_history = state.get('conversation_history', [])
            self.current_tier = state.get('current_tier', 'balanced')
            
            if self.conversation_history:
                self.ui.print_status(
                    f"Restored {len(self.conversation_history)} messages from previous session",
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
            tier=self.current_tier,
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
                
                # Process the request
                self._process_request(prompt)
                
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
        
        elif cmd == '/clear':
            self.conversation_history = []
            self.ui.print_success("Conversation cleared")
        
        elif cmd == '/save':
            filename = args[0] if args else f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            self._save_conversation(filename)
        
        elif cmd == '/models':
            self._show_models()
        
        else:
            self.ui.print_error(f"Unknown command: {cmd}")
            print(f"  {self.ui.colors.DIM}Type /help for available commands{self.ui.colors.RESET}")
    
    def _process_request(self, prompt: str):
        """Process a user request"""
        # Add to history
        self.conversation_history.append({
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now().isoformat()
        })
        
        # Check cache first
        cached = self.rag.query_cache(prompt)
        if cached:
            self.ui.print_cached()
            self.ui.print_response_header()
            print(self.ui.format_response(cached))
            
            self.conversation_history.append({
                "role": "assistant",
                "content": cached,
                "timestamp": datetime.now().isoformat(),
                "from_cache": True
            })
            return
        
        # Classify intent
        intent = self.classifier.classify(prompt, self.router.ollama)
        
        # Handle tier override
        if intent.tier_override:
            self._switch_tier(intent.tier_override)
            return
        
        # Show thinking indicator
        self.ui.print_thinking()
        
        # Process based on intent
        if intent.intent_type in [IntentType.CODE_EDIT, IntentType.CONFIG_EDIT, 
                                  IntentType.SYSTEM_TASK] and intent.complexity >= 0.5:
            # Use workflow for complex tasks
            self.ui.clear_thinking()
            response = self.orchestrator.process_request(
                prompt, 
                stream_output=lambda x: print(x, end="", flush=True)
            )
        else:
            # Simple query
            tier = self.router.get_tier_for_intent(intent.intent_type.value)
            
            # Build context from conversation
            context = self._build_context()
            
            result = self.router.query(prompt, tier=tier, system_context=context)
            
            self.ui.clear_thinking()
            self.ui.print_response_header()
            
            if result.error:
                self.ui.print_error(result.error_message)
                return
            
            response = result.response
            print(self.ui.format_response(response))
        
        # Add to history
        self.conversation_history.append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Cache response if useful
        self.rag.cache_response(prompt, response, self.router.current_tier)
    
    def _build_context(self) -> str:
        """Build context from conversation history"""
        # Keep last 6 messages (3 exchanges)
        recent = self.conversation_history[-6:]
        
        context_lines = []
        for msg in recent:
            role = "User" if msg["role"] == "user" else "Assistant"
            context_lines.append(f"{role}: {msg['content'][:500]}")
        
        return "\n".join(context_lines) if context_lines else ""
    
    def _switch_tier(self, tier: str):
        """Switch model tier"""
        tier = tier.lower()
        
        if self.router.set_tier(tier):
            self.current_tier = tier
            model = self._get_current_model()
            self.ui.print_success(f"Switched to {tier} tier ({model})")
            
            # Show uncensored warning
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
            current = " (current)" if name == self.current_tier else ""
            print(f"  {self.ui.colors.CYAN}{name}{self.ui.colors.RESET}: {model} - {desc}{current}")
        
        print(f"\n{self.ui.colors.DIM}Switch with: /tier <name>{self.ui.colors.RESET}")
    
    def _show_status(self):
        """Show session status"""
        status = self.router.get_status()
        
        print(f"\n{self.ui.icons.SUCCESS} {self.ui.colors.BOLD}Session Status{self.ui.colors.RESET}")
        print(f"  Messages: {len(self.conversation_history)}")
        print(f"  Current tier: {self.current_tier}")
        
        # Show model availability
        print(f"\n{self.ui.colors.BOLD}Model Status:{self.ui.colors.RESET}")
        for tier_name, tier_info in status.get('tiers', {}).items():
            available = tier_info.get('available', False)
            icon = self.ui.icons.DONE if available else self.ui.icons.ERROR
            print(f"  {icon} {tier_name}: {tier_info.get('model', 'unknown')}")
        
        # Show RAG stats
        try:
            rag_stats = self.rag.get_stats()
            print(f"\n{self.ui.colors.BOLD}Cache:{self.ui.colors.RESET}")
            print(f"  Cached responses: {rag_stats.get('cached_responses', 0)}")
            print(f"  Cache hits: {rag_stats.get('total_cache_hits', 0)}")
        except:
            pass
        
        print()
    
    def _show_models(self):
        """Show available models"""
        status = self.router.get_status()
        self.ui.print_model_status(status)
    
    def _save_conversation(self, filename: str):
        """Save conversation to file"""
        output_dir = get_data_dir() / "history"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename
        
        with open(output_path, 'w') as f:
            f.write(f"# Ryx AI Conversation\n")
            f.write(f"# Saved: {datetime.now().isoformat()}\n\n")
            
            for msg in self.conversation_history:
                role = msg["role"].title()
                content = msg["content"]
                f.write(f"## {role}\n\n{content}\n\n")
        
        self.ui.print_success(f"Saved to: {output_path}")
    
    def _get_current_model(self) -> str:
        """Get current model name"""
        try:
            return self.router.select_model(self.current_tier)
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
