"""
Ryx AI - Session Mode
Interactive Gemini CLI-like experience with graceful interrupts and state persistence
"""

import sys
import signal
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from core.ai_engine_v2 import AIEngineV2
from core.ai_engine import ResponseFormatter
from core.rag_system import RAGSystem, FileFinder
from core.permissions import PermissionManager, CommandExecutor, InteractiveConfirm
from core.task_manager import InterruptionHandler, Task, TaskStatus
from core.paths import get_project_root, get_data_dir, get_config_dir, get_runtime_dir

class SessionMode:
    """Interactive session mode with graceful interrupts and state persistence"""

    def __init__(self) -> None:
        """Initialize session mode with AI engine and state management"""
        self.ai = AIEngineV2()
        self.rag = RAGSystem()
        self.file_finder = FileFinder(self.rag)
        self.perm_manager = PermissionManager()
        self.executor = CommandExecutor(self.perm_manager)
        self.formatter = ResponseFormatter()
        self.meta_learner = self.ai.meta_learner

        self.conversation_history = []
        self.pending_commands = []
        self.running = True
        self.session_file = Path.home() / ".ryx" / "session_state.json"
        self.model_override = None  # For forced model selection

        # Install graceful interrupt handler
        self.interrupt_handler = InterruptionHandler(self.ai.task_manager)
        signal.signal(signal.SIGINT, self._handle_interrupt)

        # Try to restore previous session
        self._restore_session()

    def _handle_interrupt(self, signum, frame):
        """Handle Ctrl+C gracefully with state save"""
        print("\n\n⏸️  Session interrupted (Ctrl+C)")
        print("Saving state...")

        # Save conversation and current task
        self._save_session()

        # Save any current task in task manager
        if self.ai.task_manager.current_task:
            task = self.ai.task_manager.current_task
            self.ai.task_manager.pause_task(task)
            print(f"✓ Paused task: {task.description}")

        # Show summary
        if self.conversation_history:
            print(f"✓ Saved {len(self.conversation_history)} messages")

        print("\n\033[1;33mResume options:\033[0m")
        print("  • ryx ::session     - Continue chat session")
        print("  • ryx ::resume      - Resume paused task")
        print("\nGoodbye!")
        sys.exit(0)

    def _save_session(self):
        """Save session state to file"""
        self.session_file.parent.mkdir(parents=True, exist_ok=True)

        state = {
            'saved_at': datetime.now().isoformat(),
            'conversation_history': self.conversation_history[-50:],  # Keep last 50
            'pending_commands': self.pending_commands
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
            self.pending_commands = state.get('pending_commands', [])

            if self.conversation_history:
                print(f"\033[1;33m▸\033[0m Restored {len(self.conversation_history)} messages from previous session")

        except Exception:
            pass  # Ignore errors in restoration

    def run(self):
        """Main session loop"""
        self.show_header()

        while self.running:
            try:
                # Get user input
                prompt = input("\n\033[1;32mYou:\033[0m ").strip()

                if not prompt:
                    continue

                # Check for session commands
                if prompt.startswith('/'):
                    self.handle_session_command(prompt)
                    continue

                # Check for special :: commands (V2)
                if prompt.startswith('::'):
                    self.handle_v2_command(prompt)
                    continue

                # Check for natural language model switching
                model_switch_detected = self._detect_model_switch_request(prompt)
                if model_switch_detected:
                    continue

                # Add to conversation
                self.conversation_history.append({
                    "role": "user",
                    "content": prompt
                })

                # Build context from conversation
                context = self.build_conversation_context()
                context += "\n" + self.rag.get_context(prompt)

                # Query AI with V2 engine
                print("\033[1;34mRyx:\033[0m ", end="")
                sys.stdout.flush()

                result = self.ai.query(prompt, context=context, use_cache=True, learn_preferences=True, model_override=self.model_override)

                if result.error:
                    print(f"\n\033[1;31m✗\033[0m {result.error_message}")
                    continue

                ai_text = result.response

                # Show if cached
                if result.from_cache:
                    print("\033[2m[cached]\033[0m ", end="")
                    sys.stdout.flush()
                
                # Display response
                self.display_response(ai_text)
                
                # Add to conversation
                self.conversation_history.append({
                    "role": "assistant",
                    "content": ai_text
                })
                
                # Cache response
                self.rag.cache_response(prompt, ai_text, response["model"])
                
                # Parse commands
                commands = self.executor.parse_commands(ai_text)
                
                if commands:
                    self.pending_commands = commands
                    self.show_pending_commands()
                
            except KeyboardInterrupt:
                print("\n\n\033[1;33mUse /quit to exit\033[0m")
                continue
            except EOFError:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\n\033[1;31m✗ Error:\033[0m {str(e)}")
    
    def show_header(self):
        """Show session header"""
        print()
        print("\033[1;36m╭──────────────────────────────────────────╮\033[0m")
        print("\033[1;36m│  Ryx AI - Interactive Session           │\033[0m")
        print("\033[1;36m╰──────────────────────────────────────────╯\033[0m")
        print()
        print("\033[2mCommands: /help /quit /clear /exec /undo\033[0m")
        print("\033[2mJust type naturally - I'm here to help\033[0m")
    
    def display_response(self, response: str):
        """Display AI response with formatting"""
        formatted = self.formatter.format_cli(response)
        print(formatted)
    
    def build_conversation_context(self) -> str:
        """Build context from recent conversation"""
        # Keep last 6 messages (3 exchanges)
        recent = self.conversation_history[-6:]
        
        context_lines = []
        for msg in recent:
            role = "User" if msg["role"] == "user" else "Assistant"
            context_lines.append(f"{role}: {msg['content']}")
        
        return "\n".join(context_lines)
    
    def show_pending_commands(self):
        """Show commands ready to execute"""
        print()
        print("\033[1;33m⚡ Detected Actions:\033[0m")
        
        for i, cmd_info in enumerate(self.pending_commands, 1):
            cmd = cmd_info["command"]
            level = cmd_info["level"].value
            
            if cmd_info["auto_approve"]:
                marker = "\033[1;32m✓\033[0m"
            else:
                marker = "\033[1;33m?\033[0m"
            
            print(f"  {marker} [{i}] {cmd}")
            print(f"      \033[2m{cmd_info['reason']}\033[0m")
        
        print()
        print("\033[2mRun with: /exec [number] or /exec all\033[0m")
    
    def handle_session_command(self, command: str):
        """Handle session-specific commands"""
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd in ['/quit', '/exit', '/q']:
            print("\nGoodbye! 👋")
            self.running = False
        
        elif cmd == '/clear':
            self.conversation_history = []
            self.pending_commands = []
            print("\n\033[1;32m✓\033[0m Conversation cleared")
        
        elif cmd == '/help':
            self.show_session_help()
        
        elif cmd == '/exec':
            self.execute_pending(parts[1] if len(parts) > 1 else "all")
        
        elif cmd == '/undo':
            if self.conversation_history:
                self.conversation_history.pop()
                if self.conversation_history:
                    self.conversation_history.pop()  # Remove AI response too
                print("\033[1;32m✓\033[0m Last exchange undone")
            else:
                print("\033[1;33m○\033[0m Nothing to undo")
        
        elif cmd == '/status':
            self.show_session_status()
        
        elif cmd == '/save':
            filename = parts[1] if len(parts) > 1 else "conversation.txt"
            self.save_conversation(filename)
        
        else:
            print(f"\033[1;31m✗\033[0m Unknown command: {cmd}")
            print("  Type /help for available commands")
    
    def execute_pending(self, which: str = "all"):
        """Execute pending commands"""
        if not self.pending_commands:
            print("\033[1;33m○\033[0m No pending commands")
            return
        
        to_execute = []
        
        if which == "all":
            to_execute = self.pending_commands
        elif which.isdigit():
            idx = int(which) - 1
            if 0 <= idx < len(self.pending_commands):
                to_execute = [self.pending_commands[idx]]
            else:
                print(f"\033[1;31m✗\033[0m Invalid command number: {which}")
                return
        else:
            print(f"\033[1;31m✗\033[0m Usage: /exec [number|all]")
            return
        
        print()
        for cmd_info in to_execute:
            cmd = cmd_info["command"]
            
            # Check if confirmation needed
            if not cmd_info["auto_approve"]:
                if not InteractiveConfirm.confirm(
                    cmd, 
                    cmd_info["level"], 
                    cmd_info["reason"]
                ):
                    print("\033[1;33m○\033[0m Skipped")
                    continue
            
            # Execute
            print(f"\033[1;32m▸\033[0m {cmd}")
            result = self.executor.execute(cmd, confirm=True)
            
            if result["success"]:
                print("\033[1;32m✓\033[0m Done")
                if result["stdout"]:
                    print(f"\033[2m{result['stdout']}\033[0m")
            else:
                print(f"\033[1;31m✗\033[0m {result['stderr']}")
        
        self.pending_commands = []
    
    def show_session_help(self):
        """Show session help"""
        print()
        print("\033[1;36m╭─────────────────────────────────────╮\033[0m")
        print("\033[1;36m│  Session Commands                   │\033[0m")
        print("\033[1;36m╰─────────────────────────────────────╯\033[0m")
        print()
        
        commands = [
            ("/quit, /exit, /q", "Exit session"),
            ("/clear", "Clear conversation history"),
            ("/help", "Show this help"),
            ("/exec [number|all]", "Execute pending commands"),
            ("/undo", "Undo last exchange"),
            ("/status", "Show session status"),
            ("/save [filename]", "Save conversation to file"),
        ]
        
        for cmd, desc in commands:
            print(f"  \033[1;37m{cmd:<25}\033[0m {desc}")
        print()
    
    def show_session_status(self):
        """Show current session status"""
        print()
        print(f"\033[1;36mSession Status:\033[0m")
        print(f"  Messages: {len(self.conversation_history)}")
        print(f"  Pending commands: {len(self.pending_commands)}")
        
        # Get cache stats
        stats = self.rag.get_stats()
        print(f"  Cache hits: {stats['total_cache_hits']}")
        print()
    
    def save_conversation(self, filename: str):
        """Save conversation to file"""
        from datetime import datetime
        from pathlib import Path

        output_path = get_project_root() / "data" / "history" / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            f.write(f"# Ryx AI Conversation\n")
            f.write(f"# Saved: {datetime.now().isoformat()}\n\n")

            for msg in self.conversation_history:
                role = msg["role"].title()
                content = msg["content"]
                f.write(f"## {role}\n\n{content}\n\n")

        print(f"\033[1;32m✓\033[0m Saved to: {output_path}")

    def handle_v2_command(self, command: str):
        """Handle V2 system commands (::)"""
        cmd = command.strip().lower()

        if cmd == '::resume':
            self.handle_resume()
        elif cmd == '::health':
            self.handle_health()
        elif cmd == '::status':
            self.handle_status()
        elif cmd == '::models':
            self.handle_models()
        elif cmd == '::preferences' or cmd == '::prefs':
            self.handle_preferences()
        elif cmd in ['::use-fast', '::use-1.5b', '::use-small']:
            self.handle_model_switch("qwen2.5:1.5b", "ultra-fast")
        elif cmd in ['::use-balanced', '::use-6.7b', '::use-deepseek']:
            self.handle_model_switch("deepseek-coder:6.7b", "balanced")
        elif cmd in ['::use-powerful', '::use-14b', '::use-big']:
            self.handle_model_switch("qwen2.5-coder:14b", "powerful")
        elif cmd in ['::use-auto', '::auto']:
            self.handle_model_switch(None, "automatic")
        else:
            print(f"\033[1;31m✗\033[0m Unknown V2 command: {cmd}")
            print("  Available: ::resume ::health ::status ::models ::preferences")
            print("  Model switching: ::use-fast ::use-balanced ::use-powerful ::use-auto")

    def handle_resume(self):
        """Resume last paused task"""
        result = self.ai.resume_task()

        if result["success"]:
            print(f"\033[1;32m✓\033[0m Resumed task: {result['description']}")
            print(f"  Step {result['current_step'] + 1} of {result['total_steps']}")
        else:
            print(f"\033[1;33m○\033[0m {result['message']}")

    def handle_health(self):
        """Show system health"""
        health = self.ai.get_health()

        print()
        print(f"\033[1;36m╭─────────────────────────────────────╮\033[0m")
        print(f"\033[1;36m│  System Health                      │\033[0m")
        print(f"\033[1;36m╰─────────────────────────────────────╯\033[0m")
        print()

        # Overall status
        status = health["overall_status"]
        if status == "healthy":
            status_icon = "\033[1;32m●\033[0m"
        elif status == "degraded":
            status_icon = "\033[1;33m●\033[0m"
        else:
            status_icon = "\033[1;31m●\033[0m"

        print(f"  Overall: {status_icon} {status.title()}")
        print()

        # Components
        print("  \033[1;37mComponents:\033[0m")
        for name, component in health["components"].items():
            comp_status = component["status"]
            if comp_status == "healthy":
                icon = "\033[1;32m✓\033[0m"
            elif comp_status == "degraded":
                icon = "\033[1;33m○\033[0m"
            else:
                icon = "\033[1;31m✗\033[0m"

            print(f"    {icon} {name}: {component['message']}")

        # Recent incidents
        if health["recent_incidents"]:
            print()
            print(f"  \033[1;33mRecent Incidents: {len(health['recent_incidents'])}\033[0m")

        print()

    def handle_status(self):
        """Show comprehensive status"""
        status = self.ai.get_status()

        print()
        print(f"\033[1;36m╭─────────────────────────────────────╮\033[0m")
        print(f"\033[1;36m│  Ryx AI V2 Status                   │\033[0m")
        print(f"\033[1;36m╰─────────────────────────────────────╯\033[0m")
        print()

        # Health
        health_status = status["health"]["overall_status"]
        print(f"  Health: {health_status}")

        # Loaded models
        loaded = status["orchestrator"]["loaded_models"]
        print(f"  Loaded Models: {', '.join(loaded) if loaded else 'None'}")

        # Performance
        print()
        print("  \033[1;37mModel Performance:\033[0m")
        for model, perf in status["orchestrator"]["performance"].items():
            success_rate = perf["success_rate"] * 100
            print(f"    {model}:")
            print(f"      Queries: {perf['total_queries']}, Success: {success_rate:.1f}%, Latency: {perf['avg_latency_ms']:.0f}ms")

        # Cache stats
        cache = status["cache"]
        print()
        print(f"  Cache: {cache['cached_responses']} responses, {cache['total_cache_hits']} hits")

        # Learning
        prefs = status["learning"]["preferences"]
        if prefs:
            print(f"  Preferences: {len(prefs)} learned")

        print()

    def handle_models(self):
        """Show model information"""
        status = self.ai.orchestrator.get_status()

        print()
        print(f"\033[1;36m╭─────────────────────────────────────╮\033[0m")
        print(f"\033[1;36m│  AI Models                          │\033[0m")
        print(f"\033[1;36m╰─────────────────────────────────────╯\033[0m")
        print()

        # Base model
        base = self.ai.orchestrator.base_model_name
        print(f"  \033[1;32m●\033[0m Base (Always Loaded): {base}")

        # Loaded models
        loaded = status["loaded_models"]
        if len(loaded) > 1:
            print()
            print("  \033[1;37mCurrently Loaded:\033[0m")
            for model in loaded:
                if model != base:
                    print(f"    ● {model}")

        # Model tiers
        print()
        print("  \033[1;37mAvailable Tiers:\033[0m")
        for tier_name, tier in self.ai.orchestrator.model_tiers.items():
            print(f"    {tier.tier_level}. {tier_name}: {tier.name}")
            print(f"       VRAM: {tier.vram_mb}MB, Latency: ~{tier.typical_latency_ms}ms")

        print()

    def handle_preferences(self):
        """Show learned preferences"""
        prefs_data = self.ai.get_preferences()

        print()
        print(f"\033[1;36m╭─────────────────────────────────────╮\033[0m")
        print(f"\033[1;36m│  Learned Preferences                │\033[0m")
        print(f"\033[1;36m╰─────────────────────────────────────╯\033[0m")
        print()

        preferences = prefs_data["preferences"]

        if not preferences:
            print("  \033[2mNo preferences learned yet\033[0m")
            print()
            print("  \033[2mTip: Tell me your preferences like:\033[0m")
            print("  \033[2m  - 'use nvim not nano'\033[0m")
            print("  \033[2m  - 'prefer zsh shell'\033[0m")
        else:
            for category, pref in preferences.items():
                print(f"  {category}: \033[1;37m{pref['value']}\033[0m")
                print(f"    Confidence: {pref['confidence']:.1%}, Applied: {pref['times_applied']} times")

        # Suggestions
        suggestions = prefs_data["suggestions"]
        if suggestions:
            print()
            print("  \033[1;33mOptimization Suggestions:\033[0m")
            for suggestion in suggestions:
                print(f"    • {suggestion}")

        print()

    def _detect_model_switch_request(self, prompt: str) -> bool:
        """Detect natural language model switching requests"""
        prompt_lower = prompt.lower()

        # Patterns for model switching
        patterns = {
            "deepseek": ["deepseek", "balanced", "6.7b", "bigger model", "better model"],
            "fast": ["fast", "small", "quick", "1.5b", "smaller model"],
            "powerful": ["powerful", "big", "14b", "largest", "best model"],
            "auto": ["automatic", "auto select", "choose for me"]
        }

        # Check if this is a model switch request
        is_switch_request = any([
            "switch to" in prompt_lower,
            "use" in prompt_lower and "model" in prompt_lower,
            "talk to" in prompt_lower,
            "change to" in prompt_lower,
            "i want" in prompt_lower and "model" in prompt_lower,
            "i wanna" in prompt_lower
        ])

        if not is_switch_request:
            return False

        # Detect which model
        for model_type, keywords in patterns.items():
            if any(keyword in prompt_lower for keyword in keywords):
                if model_type == "deepseek":
                    self.handle_model_switch("deepseek-coder:6.7b", "balanced")
                elif model_type == "fast":
                    self.handle_model_switch("qwen2.5:1.5b", "ultra-fast")
                elif model_type == "powerful":
                    self.handle_model_switch("qwen2.5-coder:14b", "powerful")
                elif model_type == "auto":
                    self.handle_model_switch(None, "automatic")
                return True

        # If switch request detected but no specific model, show options
        print()
        print("\033[1;36m▸\033[0m Available models:")
        print("  ::use-fast       - Ultra-fast model (qwen2.5:1.5b)")
        print("  ::use-deepseek   - Balanced model (deepseek-coder:6.7b)")
        print("  ::use-powerful   - Powerful model (qwen2.5-coder:14b)")
        print("  ::use-auto       - Automatic selection")
        print()
        return True

    def handle_model_switch(self, model_name: Optional[str], tier_name: str):
        """Switch to a specific model or automatic mode"""
        if model_name is None:
            self.model_override = None
            print()
            print(f"\033[1;32m✓\033[0m Switched to automatic model selection")
            print(f"  Models will be selected based on query complexity")
            print()
        else:
            # Check if model is available
            import subprocess
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
            available_models = [line.split()[0] for line in result.stdout.split('\n')[1:] if line.strip()]

            if model_name not in available_models:
                print()
                print(f"\033[1;33m⚠\033[0m  Model {model_name} not found")
                print(f"  Available models: {', '.join(available_models)}")
                print()
                print(f"\033[1;36m▸\033[0m To download: \033[1;37mollama pull {model_name}\033[0m")
                print()

                # Ask if user wants to download
                response = input(f"Download {model_name} now? [y/N]: ").strip().lower()
                if response in ['y', 'yes']:
                    print(f"\033[1;36m▸\033[0m Downloading {model_name}...")
                    subprocess.run(['ollama', 'pull', model_name])
                    print()
                    print(f"\033[1;32m✓\033[0m Downloaded {model_name}")
                    self.model_override = model_name
                    print(f"\033[1;32m✓\033[0m Switched to {tier_name} model ({model_name})")
                    print()
                else:
                    print(f"\033[1;33m○\033[0m Keeping current model selection")
                    print()
                return

            self.model_override = model_name
            print()
            print(f"\033[1;32m✓\033[0m Switched to {tier_name} model ({model_name})")
            print(f"  All queries will use this model until you run ::use-auto")
            print()


def main():
    """Entry point for session mode"""
    session = SessionMode()
    session.run()